"""Real API/DB policy boundaries; upstream HTTP is synthetic and has no retries."""

import json

import httpx
import pytest

from qnu.adapters.providers.openai_compatible import OpenAICompatibleChatModel
from qnu.domains.modelops import rerank
from qnu.domains.modelops.embedding.runtime import resolve_embedding_runtime
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.usage.service import usage_service
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage
from tests.integration.test_capacity_discovery_733 import add, discover
from tests.integration.test_capacity_discovery_733 import setup as _connection_setup
from tests.integration.test_workspace_model_boundaries import setup_policy
from tests.integration.test_workspaces_modelops_api import API, MEMBER_A, OUTSIDER, PLATFORM, _as

URL = API + "/modelops/providers"


connected = _connection_setup


def test_model_without_limits_imports_current_metadata_without_requiring_check_id(
    client, connected
):
    cid, _, requests = connected
    discover(client, cid)
    model = add(client, cid, "qwen3.8-27b-q4", ["chat"])
    assert model["capacity_basis"] == "server_reported"
    assert model["token_limits"]["context_window_tokens"] == 131072
    assert model["operational_budgets"]["chat"]["status"] == "declared"
    assert len(requests) == 1  # Current metadata is reused.


def test_custom_model_is_saved_provisionally_after_optional_discovery(client, connected):
    cid, _, requests = connected
    model = add(client, cid, "new-model", ["chat", "rerank"])
    assert model["capacity_status"] == "unknown" and model["token_limits"] is None
    assert model["operational_budgets"]["chat"]["status"] == "provisional"
    assert model["operational_budgets"]["rerank"]["token_limits"]["max_input_tokens"] == 2048
    assert "test-only-capacity-secret" not in str(model)
    assert len(requests) == 1 and requests[0].method == "GET"


def test_manual_values_are_not_overwritten_by_cached_discovery(client, connected):
    cid, _, requests = connected
    discover(client, cid)
    model = add(client, cid, "qwen3.8-27b-q4", ["chat"], token_limits={"max_input_tokens": 7000})
    assert model["capacity_basis"] == "operator_configured"
    assert model["token_limits"]["context_window_tokens"] is None
    assert model["token_limits"]["max_input_tokens"] == 7000
    assert model["operational_budgets"]["chat"]["sources"] == {
        "max_input_tokens": "operator_configured",
        "max_output_tokens": "application_default",
    }
    assert len(requests) == 1


def test_rotated_key_invalidates_cached_metadata_before_automatic_import(client, connected):
    cid, key, requests = connected
    discover(client, cid)
    assert client.post(URL + f"/{cid}/keys/{key}/revoke", json={}).status_code == 200
    assert (
        client.post(
            URL + f"/{cid}/keys", json={"name": "New test key", "secret": "other-test-secret-791"}
        ).status_code
        == 201
    )
    model = add(client, cid, "qwen3.8-27b-q4", ["chat"])
    assert model["capacity_basis"] == "server_reported"
    assert model["token_limits"]["context_window_tokens"] == 131072
    assert len(requests) == 2
    assert requests[-1].headers["authorization"] == "Bearer other-test-secret-791"


def test_latest_failed_discovery_is_not_replaced_by_an_older_success(client, connected):
    from qnu.domains.modelops.diagnostics.router import get_diagnostic_client
    from qnu.main import app
    from qnu.ports.provider_diagnostics import DiagnosticResult

    cid, _, requests = connected
    discover(client, cid)

    class Rejected:
        async def check(self, *_):
            return DiagnosticResult("failed", "provider_auth_failed", "Synthetic rejection")

    app.dependency_overrides[get_diagnostic_client] = Rejected
    response = client.post(API + f"/modelops/providers/{cid}/discover", json={})
    assert response.status_code == 200 and response.json()["outcome"] == "failed"
    model = add(client, cid, "qwen3.8-27b-q4", ["chat"])
    assert model["token_limits"] is None
    assert model["operational_budgets"]["chat"]["status"] == "provisional"
    assert len(requests) == 1


def prepare(client, ws, provider, *, actor=MEMBER_A, text="Synthetic question", output=None):
    async def call():
        async with AsyncSessionFactory() as db:
            return await prepare_chat_request(
                db,
                actor,
                ws["id"],
                [ChatMessage("user", text)],
                provider_id=provider["id"],
                max_output_tokens=output,
            )

    return client.portal.call(call)


def chat_setup(client, limit=100000):
    ws, provider = setup_policy(client, limit=limit)
    _as(PLATFORM)
    assert (
        client.post(
            URL + f"/{provider['id']}/keys",
            json={"name": "Runtime test", "secret": "runtime-test-secret-791"},
        ).status_code
        == 201
    )
    return ws, provider


def test_unknown_chat_uses_bounded_http_payload_and_reserves_then_settles_real_usage(client):
    ws, provider = chat_setup(client)
    runtime, request, budget = prepare(client, ws, provider)
    assert runtime.capacity_status == "provisional"
    assert runtime.public_dict()["operational_budget"]["status"] == "provisional"
    assert request.max_output_tokens == 4096
    seen = []

    def respond(req):
        seen.append(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Synthetic answer"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
            },
        )

    async def call():
        async with AsyncSessionFactory() as db:
            usage = await usage_service.reserve(
                db,
                MEMBER_A,
                ws["id"],
                "chat",
                "auto-791",
                "a" * 64,
                budget.total_reserved_tokens,
                provider["id"],
            )
            result = await OpenAICompatibleChatModel(
                transport=httpx.MockTransport(respond)
            ).complete(
                [ChatMessage("user", "Synthetic question")],
                request,
            )
            await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)

    client.portal.call(call)
    assert len(seen) == 1 and seen[0]["max_tokens"] == 4096
    current = client.get(URL + f"/{provider['id']}").json()
    assert current["token_limits"] is None and current["capacity_status"] == "unknown"
    quota = client.get(API + f"/workspaces/{ws['id']}/quota").json()
    assert quota["tokens_used"] == 13 and quota["tokens_reserved"] == 0


def test_auto_policy_preserves_access_quota_and_explicit_request_boundaries(client):
    ws, provider = chat_setup(client, limit=10)
    with pytest.raises(AppException) as denied:
        prepare(client, ws, provider, actor=OUTSIDER)
    assert denied.value.status_code == 404
    for text, output, code in [
        ("small", 8192, "model_output_limit_exceeded"),
        ("X" * 40000, None, "model_context_limit_exceeded"),
    ]:
        with pytest.raises(AppException) as caught:
            prepare(client, ws, provider, text=text, output=output)
        assert caught.value.code == code
    _, _, budget = prepare(client, ws, provider)

    async def reserve():
        async with AsyncSessionFactory() as db:
            return await usage_service.reserve(
                db,
                MEMBER_A,
                ws["id"],
                "chat",
                "quota-791",
                "b" * 64,
                budget.total_reserved_tokens,
                provider["id"],
            )

    client.portal.call(reserve)
    assert client.patch(URL + f"/{provider['id']}", json={"is_active": False}).status_code == 200
    with pytest.raises(AppException) as disabled:
        prepare(client, ws, provider)
    assert disabled.value.code == "provider_inactive"


@pytest.mark.parametrize("capability", ["embedding", "rerank"])
def test_unknown_retrieval_models_use_same_policy_without_inventing_dimension(client, capability):
    ws, provider = chat_setup(client)
    assert (
        client.patch(
            URL + f"/{provider['id']}",
            json={
                "capabilities": [capability],
                **({"embedding_dimension": 3} if capability == "embedding" else {}),
            },
        ).status_code
        == 200
    )

    async def call():
        async with AsyncSessionFactory() as db:
            target = (
                await resolve_embedding_runtime(db, ws["id"], provider["id"])
                if capability == "embedding"
                else await rerank.resolve(db, ws["id"], provider["id"])
            )
            assert target.capacity_status == "provisional"
            size = (
                target.budget(["small"])
                if capability == "embedding"
                else rerank.budget(target, "q", ["small"])
            )
            assert 0 < size < 2048
            with pytest.raises(AppException) as large:
                target.budget(["X" * 3000]) if capability == "embedding" else rerank.budget(
                    target, "q", ["X" * 3000]
                )
            assert large.value.code == f"{capability}_input_limit_exceeded"

    client.portal.call(call)


def test_explicit_null_switches_to_auto_but_rename_preserves_declared_limits(client):
    ws, provider = chat_setup(client)
    url = URL + f"/{provider['id']}"
    limits = {"context_window_tokens": 163840, "max_output_tokens": 32768}
    assert client.patch(url, json={"token_limits": limits}).status_code == 200
    runtime, request, _ = prepare(client, ws, provider)
    assert request.max_output_tokens == 32768
    assert runtime.capacity_status == "configured"
    renamed = client.patch(url, json={"name": "Renamed test model"}).json()
    assert renamed["token_limits"]["max_output_tokens"] == 32768
    cleared = client.patch(url, json={"token_limits": None}).json()
    assert cleared["token_limits"] is None and cleared["capacity_status"] == "unknown"
    assert prepare(client, ws, provider)[1].max_output_tokens == 4096


def test_compiler_plans_bounded_parts_for_a_model_with_unknown_capacity(client):
    from tests.integration.compiler_support import chat_provider, processed_input, request_compile
    from tests.integration.knowledge_support import as_actor

    data = processed_input(client)
    model = chat_provider(client, data, "http://127.0.0.1:20128/v1")
    as_actor(PLATFORM)
    assert client.patch(URL + f"/{model['id']}", json={"token_limits": None}).status_code == 200
    result = request_compile(client, data)
    assert result.status_code == 201, result.text
    from qnu.domains.knowledge.compilation.models import CompilationRun

    async def read_config():
        async with AsyncSessionFactory() as db:
            run = await db.get(CompilationRun, result.json()["run"]["id"])
            return run.config

    config = client.portal.call(read_config)
    assert config["max_output_tokens"] <= 4096
    assert config["provider"]["operational_budget"]["status"] == "provisional"


def test_sync_records_server_fields_without_relabeling_manual_input(client, connected):
    from tests.integration.test_capacity_discovery_733 import sync

    cid, _, _ = connected
    add(client, cid, "qwen3.8-27b-q4", ["chat"], token_limits={"max_input_tokens": 7000})
    check = discover(client, cid)
    result = sync(client, cid, check["id"], ["qwen3.8-27b-q4"])
    assert result.status_code == 200, result.text
    sources = result.json()[0]["operational_budgets"]["chat"]["sources"]
    assert sources["max_input_tokens"] == "operator_configured"
    assert sources["context_window_tokens"] == "server_reported"
    assert sources["max_output_tokens"] == "server_reported"
