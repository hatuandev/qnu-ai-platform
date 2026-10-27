"""Saved OCR -> Compiler -> auto-review -> accepted edit -> publication -> real Qdrant search."""

import json

from tests.integration.compiler_support import (
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.index_support import FakeEmbedding, execute_index
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.test_compiler_review_652 import ReviewChat
from tests.integration.test_index_api_647 import embedding_provider
from tests.integration.test_ocr_text_review_651 import edit_body, review_url, save
from tests.integration.test_publication_646 import decision
from tests.integration.workflow_support import accept_edit, preview_edit, run_review


def test_corrected_source_survives_review_edit_publish_index_and_citations(client):
    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client, code="workflow-full")
    url = review_url(data)
    original = client.get(url).json()
    unit = next(u for u in original["units"] if u["text"] == "Chỉ tiêu tuyển sinh")
    saved = save(client, url, edit_body(original, unit, "Chỉ tiêu tuyển sinh đại học"))
    assert saved.status_code == 200, saved.text
    selected = saved.json()
    with ReviewChat() as chat:
        chat_provider(client, data, chat.base_url)
        requested = request_compile(client, data, text_versions={data["ocr_run_id"]: 1})
        assert requested.status_code == 201, requested.text
        data["run_id"] = requested.json()["run"]["id"]
        assert execute_compile(client, data["run_id"]) == "completed"
        assert run_review(client, data["run_id"]) == "completed"
        review_request = json.loads(chat.requests[-1]["body"]["messages"][-1]["content"])
        assert any(
            s["text"] == "Chỉ tiêu tuyển sinh đại học" for s in review_request["source_units"]
        )
        assert review_request["documents"][0]["text_version"]["id"] == selected["version_id"]
        preview, _ = preview_edit(client, data)
        accepted = accept_edit(client, data, preview)
        assert accepted.status_code == 201, accepted.text
        child = accepted.json()["run"]["id"]
        assert run_review(client, child) == "completed"
        base = f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
        registered = client.post(
            base + "/compiled-documents",
            headers={"Idempotency-Key": "register"},
            json={
                "document_key": "workflow",
                "title": "Tài liệu đã sửa",
                "compilation_run_id": child,
            },
        )
        assert registered.status_code == 201, registered.text
        registered = registered.json()
        provenance = registered["version"]["provenance"]
        assert provenance["origin"] == "user_edit" and provenance["parent_run_id"] == data["run_id"]
        assert provenance["sources"][0]["text_version"]["id"] == selected["version_id"]
        doc_url = base + "/compiled-documents/" + registered["document"]["id"]
        version_url = doc_url + "/versions/" + registered["version"]["id"]
        as_actor(PLATFORM)
        for action in ("approve", "publish"):
            result = decision(client, version_url, action)
            assert result.status_code == 200, result.text
        as_actor(EDITOR)
        with FakeEmbedding() as embedding:
            embedding_provider(client, data, embedding.base_url)
            requested = client.post(
                base + "/indexing-runs", json={}, headers={"Idempotency-Key": "index"}
            )
            assert requested.status_code == 201, requested.text
            run_id = requested.json()["run"]["id"]

            async def cleanup():
                async with AsyncSessionFactory() as db:
                    row = await db.get(IndexRun, run_id)
                    await app.state.container.vector_store.delete_collection(row.vector_collection)

            try:
                assert execute_index(client, run_id) == "completed"
                response = client.post(
                    base + "/search", json={"query": "Chỉ tiêu tuyển sinh đại học", "top_k": 10}
                )
                assert response.status_code == 200, response.text
                hits = response.json()["hits"]
                assert any("Chỉ tiêu tuyển sinh đại học" in hit["text"] for hit in hits)
                for hit in hits:
                    assert hit["version_id"] == registered["version"]["id"]
                    for citation in hit["citations"].values():
                        assert citation["text_version"]["id"] == selected["version_id"]
                        assert citation["original_canonical_sha256"] == original["canonical_sha256"]
            finally:
                client.portal.call(cleanup)
