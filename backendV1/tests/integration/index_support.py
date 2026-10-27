"""Synthetic publication/index setup, no external corpus or inference."""

import hashlib
import json

from tests.integration.ocr_support import FakeNemotron


class FakeEmbedding(FakeNemotron):
    """Deterministic numeric vectors for transport tests, not a quality benchmark."""

    def _respond(self, index):
        request = self.requests[index]["body"]
        texts = request["input"]
        if self.mode == "http_error":
            return 503, b'{"error":"unavailable"}'
        if self.mode == "auth_error":
            return 401, b'{"error":"unauthorized"}'
        if self.mode == "malformed":
            return 200, b'{"data":[]}'
        data = []
        for i, text in enumerate(texts):
            raw = hashlib.sha256(text.encode()).digest()
            vector = [(raw[k] + 1) / 256 for k in range(4)]
            if self.mode == "wrong_dimension":
                vector = vector[:2]
            data.append({"index": i, "embedding": vector})
        return 200, json.dumps(
            {"model": request["model"], "data": data, "usage": {"total_tokens": len(texts) * 25}}
        ).encode()


def execute_index(client, run_id, *, model=None, vectors=None):
    from qnu.domains.knowledge.index.execution import execute_run
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    async def execute():
        async with AsyncSessionFactory() as db:
            return await execute_run(
                db,
                app.state.container.blob_store,
                run_id,
                worker_id="index-test",
                model=model or app.state.container.embedding_model,
                vectors=vectors or app.state.container.vector_store,
            )

    return client.portal.call(execute)


from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeJobQueue, use_queue


def published_input(client):
    data = processed_input(client, code="index-input")
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run = request_compile(client, data).json()["run"]["id"]
        assert execute_compile(client, run) == "completed"
    base = f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
    result = client.post(
        base + "/compiled-documents",
        headers={"Idempotency-Key": "register"},
        json={
            "document_key": "chi-tieu",
            "title": "Chỉ tiêu",
            "compilation_run_id": run,
        },
    )
    assert result.status_code == 201, result.text
    data["compiled"] = result.json()
    data["base"] = base
    url = base + "/compiled-documents/" + data["compiled"]["document"]["id"]
    data["document_url"] = url
    data["version_url"] = url + "/versions/" + data["compiled"]["version"]["id"]
    as_actor(PLATFORM)
    for action in ("approve", "publish"):
        from tests.integration.publication_review_support import acknowledgement

        payload = {"action": action, "reason": "Synthetic fixture review."}
        if action == "approve":
            payload["review_ack"] = acknowledgement(client, data["version_url"])
        preview = client.post(
            data["version_url"] + "/decision-preview",
            json=payload,
        )
        assert preview.status_code == 200, preview.text
        body = preview.json()
        result = client.post(
            data["version_url"] + "/decisions",
            headers={"Idempotency-Key": action},
            json={
                "preview_id": body["id"],
                "preview_sha256": body["preview_sha256"],
            },
        )
        assert result.status_code == 200, result.text
    as_actor(EDITOR)
    return data
