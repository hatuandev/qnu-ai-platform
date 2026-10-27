"""Controlled published corpus for scope/window checks, never a semantic model benchmark."""

import json
import re

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.index_support import FakeEmbedding, execute_index
from tests.integration.knowledge_support import EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.publication_review_support import acknowledgement
from tests.integration.test_index_api_647 import embedding_provider


class ParagraphChat(FakeChat):
    def _respond(self, index):
        status, raw = super()._respond(index)
        body = json.loads(raw)
        draft = json.loads(body["choices"][0]["message"]["content"])
        original = draft["sections"][0]["paragraphs"][0]
        draft["sections"][0]["paragraphs"] = [dict(original) for _ in range(4)]
        draft["sections"].append({"heading": "Mục khác", "paragraphs": [dict(original)]})
        body["choices"][0]["message"]["content"] = json.dumps(draft)
        return status, json.dumps(body).encode()


def prepared(client):
    data = processed_input(client, code="rag-scope")
    with ParagraphChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run = request_compile(client, data).json()["run"]["id"]
        assert execute_compile(client, run) == "completed"
    content = client.get(data["url"] + "/" + run + "/draft").json()
    table = content["source_tables"][0]
    run_prefix = table["citation"].split(":", 1)[0]
    proofs = {}
    for row in table["table"]["rows"]:
        for cell in row:
            year = re.search(r"\b(20\d{2})\b", cell["text"])
            if year:
                proofs[int(year.group(1))] = {
                    "citation": run_prefix + ":" + cell["evidence_id"],
                    "quote": cell["text"],
                }
    annotations = [
        {
            "target": f"paragraph:0:{position}",
            "values": {"data_year": year},
            "evidence": [proofs[year]],
        }
        for position, year in enumerate((2024, 2024, 2023))
    ]
    base = data["url"].removesuffix("/compilation-runs")
    return {**data, "run": run, "annotations": annotations, "base": base}


def register(client, data, annotations=None):
    return client.post(
        data["base"] + "/compiled-documents",
        headers={"Idempotency-Key": "register-metadata"},
        json={
            "document_key": "scope",
            "title": "Controlled scope fixture",
            "compilation_run_id": data["run"],
            "retrieval_metadata": data["annotations"] if annotations is None else annotations,
        },
    )


@pytest.fixture
def metadata_index(client):
    data = prepared(client)
    created = register(client, data)
    assert created.status_code == 201, created.text
    data["compiled"] = created.json()
    version_url = (
        data["base"]
        + "/compiled-documents/"
        + created.json()["document"]["id"]
        + "/versions/"
        + created.json()["version"]["id"]
    )
    data["version_url"] = version_url
    as_actor(PLATFORM)
    for action in ("approve", "publish"):
        request = {"action": action, "reason": "Controlled scope fixture review."}
        if action == "approve":
            request["review_ack"] = acknowledgement(client, version_url)
            request["review_ack"]["retrieval_metadata_sha256"] = created.json()["version"][
                "retrieval_metadata_sha256"
            ]
        preview = client.post(version_url + "/decision-preview", json=request)
        assert preview.status_code == 200, preview.text
        result = client.post(
            version_url + "/decisions",
            headers={"Idempotency-Key": action},
            json={
                "preview_id": preview.json()["id"],
                "preview_sha256": preview.json()["preview_sha256"],
            },
        )
        assert result.status_code == 200, result.text
    as_actor(EDITOR)
    with FakeEmbedding() as embedding:
        provider = embedding_provider(client, data, embedding.base_url)
        requested = client.post(
            data["base"] + "/indexing-runs", headers={"Idempotency-Key": "index"}, json={}
        )
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_index(client, run_id) == "completed"
        try:
            yield {
                **data,
                "index_run_id": run_id,
                "embedding": embedding,
                "embedding_provider": provider,
            }
        finally:
            from qnu.domains.knowledge.index.models import IndexRun
            from qnu.main import app
            from qnu.platform.database import AsyncSessionFactory

            async def cleanup():
                async with AsyncSessionFactory() as db:
                    row = await db.get(IndexRun, run_id)
                    name = row.vector_collection
                await app.state.container.vector_store.delete_collection(name)

            client.portal.call(cleanup)
