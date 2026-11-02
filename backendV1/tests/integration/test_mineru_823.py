"""Real API/DB/worker boundaries with a deterministic MinerU HTTP transport."""

import hashlib
import json
from dataclasses import replace

import httpx
import pytest
from sqlalchemy import select

from qnu.adapters.providers.mineru import MineruOcrEngine
from qnu.domains.modelops.models import ModelUsageRecord
from qnu.domains.modelops.resilience.execution import ManagedOcrEngine
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.ocr.execution import read_artifact_bytes
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    PLATFORM,
    as_actor,
    workspace_with_editor,
)
from tests.integration.ocr_support import (
    execute_now,
    prepare_source,
    real_pdf,
    request_run,
    set_quota,
)
from tests.unit.test_mineru_823 import archive, page


class DocumentEngine:
    def __init__(self):
        self.calls = []
        self.mode = "ok"

    async def extract_document(self, pdf, request, **kwargs):
        def handler(req):
            self.calls.append(req.method)
            receipt = {
                "task_id": "task1",
                "status": "completed",
                "files": [{"file_id": "file1", "status": "completed"}],
            }
            if req.method == "POST":
                return httpx.Response(202, json=receipt)
            if req.method == "PUT":
                assert req.content == pdf
                return httpx.Response(200, json={})
            return (
                httpx.Response(200, content=archive([page(0), page(1)]))
                if req.url.path.endswith("/content")
                else httpx.Response(200, json=receipt)
            )

        # Exercise the production transport and checkpoint hooks; no key lease needed by this fake.
        return await MineruOcrEngine(transport=httpx.MockTransport(handler)).extract_document(
            pdf, replace(request, execution=None), **kwargs
        )


def setup(client, code, *, blocked=False):
    workspace = workspace_with_editor(client, code)
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/modelops/providers",
        json={
            "name": code,
            "provider_type": "mineru",
            "base_url": "https://mineru.example/mineru",
            "model_name": "mineru",
            "capabilities": ["ocr"],
            "timeout_seconds": 60,
        },
    )
    assert response.status_code == 201, response.text
    provider = response.json()
    assert (
        client.post(
            f"{API}/modelops/providers/{provider['id']}/keys",
            json={"name": "test", "secret": "protected-test-key"},
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"{API}/workspaces/{workspace['id']}/allowed-providers",
            json={"provider_ids": [provider["id"]], "defaults": {"ocr": provider["id"]}},
        ).status_code
        == 200
    )
    assert set_quota(client, workspace["id"], 0, blocked=blocked).status_code == 200
    as_actor(EDITOR)
    collection, source, revision = prepare_source(
        client, workspace["id"], code, payload=real_pdf(["PAGE ONE", "PAGE TWO"])
    )
    requested = request_run(client, workspace["id"], collection["id"], source["id"], revision["id"])
    assert requested.status_code == 201, requested.text
    return workspace, provider, requested.json()["run"]["id"]


def test_default_whole_document_pipeline_and_unknown_usage(client):
    workspace, provider, run_id = setup(client, "mineru-pipeline")
    engine = DocumentEngine()
    outcome = execute_now(client, run_id, engine=engine)
    assert outcome.status == "completed", outcome
    assert engine.calls == ["POST", "PUT", "GET", "GET"]

    async def inspect():
        async with AsyncSessionFactory() as db:
            run = await db.get(OcrProcessingRun, run_id)
            assert (
                run.provider_id == provider["id"]
                and run.pages_done == 2
                and run.usage_tokens is None
            )
            assert run.config["mineru_task"]["phase"] == "uploaded"
            record, raw = await read_artifact_bytes(
                db, client.app.state.container.blob_store, run, "provider_document", 0
            )
            assert record.sha256 == hashlib.sha256(raw).hexdigest()
            _, canonical = await read_artifact_bytes(
                db, client.app.state.container.blob_store, run, "canonical_json", 0
            )
            body = json.loads(canonical)
            assert body["pages"][0]["blocks"][0]["text"] == "Dữ liệu gốc 12,67"
            assert body["evidence"]["ev_p001_b001"]["artifact"] == "raw_response"
            usage = (
                await db.scalars(
                    select(ModelUsageRecord).where(ModelUsageRecord.workspace_id == workspace["id"])
                )
            ).one()
            assert (
                usage.status == "unknown"
                and usage.total_tokens is None
                and usage.reserved_tokens == 0
            )

    client.portal.call(inspect)
    assert execute_now(client, run_id, engine=engine).status == "not_claimed"
    assert len(engine.calls) == 4


@pytest.mark.parametrize("disabled,blocked", [(True, False), (False, True)])
def test_disabled_or_blocked_never_submits_pdf(client, disabled, blocked):
    _, provider, run_id = setup(client, f"mineru-blocked-{str(disabled).lower()}", blocked=blocked)
    if disabled:
        as_actor(PLATFORM)
        assert (
            client.patch(
                f"{API}/modelops/providers/{provider['id']}", json={"is_active": False}
            ).status_code
            == 200
        )
    engine = DocumentEngine()
    assert execute_now(client, run_id, engine=engine).status == "failed"
    assert engine.calls == []


def test_zero_reservation_cannot_bypass_token_based_models(client):
    workspace, _, _ = setup(client, "mineru-zero-budget")

    async def invoke():
        async with AsyncSessionFactory() as db:
            with pytest.raises(AppException) as caught:
                await usage_service.reserve(
                    db, EDITOR, workspace["id"], "ocr", "invalid-zero", "0" * 64, 0
                )
            assert caught.value.code == "usage_request_invalid"

    client.portal.call(invoke)


def test_managed_credentials_and_connection_contract(client):
    workspace, _, _ = setup(client, "mineru-connection")
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/modelops/connections",
        json={
            "name": "MinerU connection",
            "base_url": "https://ocr.example/mineru",
            "family": "custom",
            "api_type": "mineru",
            "timeout_seconds": 60,
        },
    )
    assert response.status_code == 201, response.text
    parent = response.json()
    assert (
        client.post(
            f"{API}/modelops/providers/{parent['id']}/keys",
            json={"name": "shared", "secret": "protected-test-key"},
        ).status_code
        == 201
    )
    result = client.post(
        f"{API}/modelops/connections/{parent['id']}/models",
        json={"model_name": "document-parser", "capabilities": ["ocr"]},
    )
    assert result.status_code == 201, result.text
    model = result.json()
    assert model["provider_type"] == "mineru" and model["operational_budgets"] == {}
    policy = client.put(
        f"{API}/modelops/providers/{model['id']}/resilience", json={"wait_for_completion": True}
    )
    assert policy.status_code == 200, policy.text
    assert (
        client.put(
            f"{API}/workspaces/{workspace['id']}/allowed-providers",
            json={"provider_ids": [model["id"]], "defaults": {"ocr": model["id"]}},
        ).status_code
        == 200
    )
    catalog = client.get(f"{API}/modelops/catalog", params={"workspace_id": workspace["id"]})
    assert catalog.status_code == 200
    assert catalog.json()[0]["provider_type"] == "mineru"
    as_actor(EDITOR)
    collection, source, revision = prepare_source(
        client, workspace["id"], "managed", payload=real_pdf(["PAGE ONE", "PAGE TWO"])
    )
    requested = request_run(client, workspace["id"], collection["id"], source["id"], revision["id"])
    assert requested.status_code == 201
    adapter = DocumentEngine()
    engine = ManagedOcrEngine(None, document_adapter=adapter)
    assert execute_now(client, requested.json()["run"]["id"], engine=engine).status == "completed"
    assert adapter.calls == ["POST", "PUT", "GET", "GET"]
