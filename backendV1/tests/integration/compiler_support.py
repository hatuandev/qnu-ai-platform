"""Synthetic OCR inputs and a loopback chat provider for Compiler v1 tests."""

from __future__ import annotations

import json

from tests.integration.knowledge_support import (
    API,
    EDITOR,
    PLATFORM,
    as_actor,
    workspace_with_editor,
)
from tests.integration.ocr_support import (
    TABLE_RESPONSE,
    FakeJobQueue,
    FakeNemotron,
    execute_now,
    prepare_source,
    request_run,
    setup_ocr_provider,
)


class FakeChat(FakeNemotron):
    """Real loopback HTTP; citations are derived from the request, never hardcoded IDs."""

    def __init__(self):
        super().__init__()
        self.last_raw = b""

    def _respond(self, index):
        request = self.requests[index]["body"]
        incoming = json.loads(request["messages"][-1]["content"])
        citation = incoming["allowed_citations"][0]
        draft = {
            "title": "Chỉ tiêu tuyển sinh",
            "sections": [
                {
                    "heading": "Nguồn dữ liệu",
                    "paragraphs": [
                        {"text": "Nguồn có bảng chỉ tiêu tuyển sinh.", "citations": [citation]}
                    ],
                }
            ],
            "unknowns": [],
        }
        if self.mode == "bad_citation":
            draft["sections"][0]["paragraphs"][0]["citations"] = ["unrelated:ev_p001_b000"]
        if self.mode == "bad_schema":
            draft = {"invented": "not a draft"}
        if self.mode == "http_error":
            status, body = 503, {"error": "provider unavailable"}
        else:
            status = 200
            body = {
                "model": "test-chat",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(draft, ensure_ascii=False),
                        },
                        "finish_reason": "length" if self.mode == "truncated" else "stop",
                    }
                ],
                "usage": {"prompt_tokens": 123, "completion_tokens": 50, "total_tokens": 173},
            }
        self.last_raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return status, self.last_raw


def execute_compile(client, run_id, *, model=None):
    from qnu.domains.knowledge.compilation.execution import execute_run
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    async def execute():
        async with AsyncSessionFactory() as db:
            return await execute_run(
                db,
                app.state.container.blob_store,
                run_id,
                worker_id="compiler-test",
                model=model or app.state.container.chat_model,
            )

    return client.portal.call(execute)


def compiler_url(workspace_id: str, collection_id: str) -> str:
    return f"{API}/workspaces/{workspace_id}/collections/{collection_id}/compilation-runs"


def processed_input(client, *, code="compiler-input") -> dict:
    workspace = workspace_with_editor(client, code)
    as_actor(EDITOR)
    with FakeNemotron() as provider:
        provider.responses = [TABLE_RESPONSE]
        ocr_provider = setup_ocr_provider(client, workspace["id"], provider.base_url)
        collection, source, revision = prepare_source(client, workspace["id"], "Compiler input")
        requested = request_run(
            client,
            workspace["id"],
            collection["id"],
            source["id"],
            revision["id"],
            queue=FakeJobQueue(),
        )
        assert requested.status_code == 201, requested.text
        ocr_run_id = requested.json()["run"]["id"]
        assert execute_now(client, ocr_run_id).status == "completed"
    return {
        "workspace": workspace,
        "collection": collection,
        "source": source,
        "revision": revision,
        "ocr_provider": ocr_provider,
        "ocr_run_id": ocr_run_id,
        "url": compiler_url(workspace["id"], collection["id"]),
    }


def chat_provider(client, data, base_url, *, secret="compiler-test-secret", model="test-chat"):
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "chat-" + data["workspace"]["id"],
            "provider_type": "openai_compatible",
            "base_url": base_url,
            "model_name": model,
            "capabilities": ["chat"],
            "timeout_seconds": 5,
            "token_limits": {"context_window_tokens": 131072, "max_output_tokens": 8192},
        },
    )
    assert response.status_code == 201, response.text
    provider = response.json()
    if secret is not None:
        response = client.post(
            f"{API}/modelops/providers/{provider['id']}/keys",
            json={
                "name": "chat-key",
                "secret": secret,
            },
        )
        assert response.status_code == 201, response.text
    response = client.put(
        f"{API}/workspaces/{data['workspace']['id']}/allowed-providers",
        json={
            "provider_ids": [data["ocr_provider"]["id"], provider["id"]],
            "defaults": {"ocr": data["ocr_provider"]["id"], "chat": provider["id"]},
        },
    )
    assert response.status_code == 200, response.text
    as_actor(EDITOR)
    return provider


def request_compile(client, data, *, key="compile-one", topic="Chỉ tiêu tuyển sinh", **options):
    return client.post(
        data["url"],
        headers={"Idempotency-Key": key},
        json={
            "topic": topic,
            "ocr_run_ids": [data["ocr_run_id"]],
            **options,
        },
    )
