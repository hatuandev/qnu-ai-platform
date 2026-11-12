"""Real API, PostgreSQL and Qdrant checks for annotations and bounded context."""

import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.metadata import matches_metadata
from qnu.platform.database import AsyncSessionFactory
from tests.integration.knowledge_support import OUTSIDER, as_actor
from tests.integration.rag_support_672 import metadata_index as metadata_index_fixture
from tests.integration.rag_support_672 import prepared, register
from tests.integration.test_hybrid_655 import FakeRerank, setup_rerank

metadata_index = metadata_index_fixture


@pytest.mark.parametrize("case", ["quote", "target", "value", "global_data_year"])
def test_registration_rejects_untraceable_or_overbroad_metadata(client, case):
    data = prepared(client)
    annotations = copy.deepcopy(data["annotations"])
    if case == "quote":
        annotations[0]["evidence"][0]["quote"] = "invented"
    if case == "target":
        annotations[0]["target"] = "paragraph:99:0"
    if case == "value":
        annotations[0]["values"]["data_year"] = 2030
    if case == "global_data_year":
        annotations[0]["target"] = "document"
    result = register(client, data, annotations, key=f"invalid-{case}")
    assert result.status_code == 422, result.text
    expected_code = (
        "validation_error" if case == "global_data_year" else "retrieval_metadata_invalid"
    )
    assert result.json()["code"] == expected_code
    # The invalid request must not create a document or poison idempotency state.
    valid = register(client, data)
    assert valid.status_code == 201, valid.text


def test_scope_is_applied_before_topk_in_all_modes_on_same_snapshot(
    client, metadata_index, monkeypatch
):
    data = metadata_index

    async def labels():
        async with AsyncSessionFactory() as db:
            rows = list(
                (
                    await db.scalars(
                        select(IndexChunk).where(IndexChunk.run_id == data["index_run_id"])
                    )
                ).all()
            )
            return {
                c.id
                for c in rows
                if c.kind == "paragraph"
                and c.structure["context"]["parent"] == "section:0"
                and c.structure["context"]["position"] in (0, 1)
            }

    expected = client.portal.call(labels)
    assert len(expected) == 2
    from qnu.main import app

    vector_store = app.state.container.vector_store
    original_search = vector_store.search
    vector_scopes = []

    async def scoped_search(collection, vector, limit, scope):
        vector_scopes.append({"limit": limit, "scope": scope})
        return await original_search(collection, vector, limit, scope)

    monkeypatch.setattr(vector_store, "search", scoped_search)
    comparisons = []
    with FakeRerank() as rerank:
        provider = setup_rerank(client, data, rerank.base_url)
        for mode in ("dense", "hybrid", "hybrid_rerank"):
            options = {"rerank_provider_id": provider} if mode == "hybrid_rerank" else {}
            response = client.post(
                data["base"] + "/search",
                json={
                    "query": "Nguồn dữ liệu",
                    "mode": mode,
                    "top_k": 2,
                    "candidate_k": 10,
                    "metadata_filter": {"data_year": 2024},
                    **options,
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert {h["chunk_id"] for h in body["hits"]} == expected
            assert body["trace"]["metadata_eligible_chunks"] == 2
            assert body["index_run_id"] == data["index_run_id"]
            assert set(vector_scopes[-1]["scope"]["chunk_id"]) == expected
            assert vector_scopes[-1]["limit"] == (2 if mode == "dense" else 10)
            if mode != "dense":
                assert set(body["trace"]["lexical_ranked_ids"]) == expected
            comparisons.append(
                {
                    "mode": mode,
                    "ranked_ids": [h["chunk_id"] for h in body["hits"]],
                    "annotated_recall_at_2": len(expected & {h["chunk_id"] for h in body["hits"]})
                    / len(expected),
                    "generation": body["generation"],
                }
            )
        assert len(rerank.requests[-1]["body"]["documents"]) == 2
    requests = len(data["embedding"].requests)
    result = client.post(
        data["base"] + "/search",
        json={"query": "Nguồn", "metadata_filter": {"data_year": 2030}, "mode": "dense"},
    )
    assert result.status_code == 200 and result.json()["hits"] == []
    assert len(data["embedding"].requests) == requests
    artifact = Path("storage/context672/controlled-retrieval.json")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(
            {
                "kind": "controlled_functional_comparison",
                "quality_claim": False,
                "embedding": "synthetic_sha256_4d",
                "reranker": "synthetic_reverse_order",
                "index_run_id": data["index_run_id"],
                "gold_ids": sorted(expected),
                "scope": {"data_year": 2024},
                "comparisons": comparisons,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_context_stays_in_same_section_publication_and_metadata_scope(client, metadata_index):
    data = metadata_index
    from qnu.domains.knowledge.index.schemas import SearchRequest
    from qnu.domains.knowledge.index.search import search
    from qnu.domains.knowledge.index.validation import validate_results
    from qnu.domains.rag.answer.context import evidence_size, expand_context
    from qnu.domains.rag.answer.schemas import AnswerRequest
    from qnu.main import app
    from tests.integration.knowledge_support import EDITOR

    async def check():
        c = app.state.container
        async with AsyncSessionFactory() as db:
            req = AnswerRequest(
                question="Nguồn",
                top_k=1,
                metadata_filter={"data_year": 2024},
                context_window=1,
                context_max_bytes=32000,
            )
            original = await search(
                db,
                c.blob_store,
                c.embedding_model,
                c.vector_store,
                EDITOR,
                data["workspace"]["id"],
                data["collection"]["id"],
                SearchRequest(
                    query="Nguồn", top_k=1, metadata_filter=req.metadata_filter, mode="dense"
                ),
            )
            expanded, trace = await expand_context(
                db,
                c.blob_store,
                EDITOR,
                data["workspace"]["id"],
                data["collection"]["id"],
                original,
                req,
            )
            assert len(original.hits) == 1 and len(expanded.hits) == 2
            assert len(trace["added"]) == 1
            assert (
                len(
                    {
                        (
                            h.document_id,
                            h.version_id,
                            h.publication_decision_id,
                            h.structure["context"]["parent"],
                        )
                        for h in expanded.hits
                    }
                )
                == 1
            )
            assert all(matches_metadata(h.structure, req.metadata_filter) for h in expanded.hits)
            await validate_results(
                db,
                c.blob_store,
                c.vector_store,
                EDITOR,
                data["workspace"]["id"],
                data["collection"]["id"],
                expanded,
                None,
            )
            from qnu.platform.errors import AppException

            with pytest.raises(AppException) as error:
                await expand_context(
                    db,
                    c.blob_store,
                    EDITOR,
                    data["workspace"]["id"],
                    data["collection"]["id"],
                    original,
                    req.model_copy(
                        update={"context_max_bytes": evidence_size(original.hits[0]) + 1}
                    ),
                )
            assert error.value.code == "answer_context_budget_exceeded"

    client.portal.call(check)


def test_version_metadata_tampering_invalidates_published_receipt(client, metadata_index):
    from qnu.domains.knowledge.publication.models import CompiledVersion

    data = metadata_index

    async def tamper():
        async with AsyncSessionFactory() as db:
            row = await db.get(CompiledVersion, data["compiled"]["version"]["id"])
            changed = copy.deepcopy(row.retrieval_metadata)
            changed[0]["values"]["data_year"] = 2030
            row.retrieval_metadata = changed
            await db.commit()

    client.portal.call(tamper)
    result = client.post(data["base"] + "/search", json={"query": "Nguồn", "mode": "dense"})
    assert result.status_code in {409, 422}, result.text
    assert result.json()["code"] in {"publication_bundle_changed", "retrieval_metadata_invalid"}
    as_actor(OUTSIDER)
    assert (
        client.post(data["base"] + "/search", json={"query": "Nguồn", "mode": "dense"}).status_code
        == 404
    )


def test_metadata_requires_explicit_human_acknowledgement_of_its_hash(client):
    from tests.integration.knowledge_support import PLATFORM
    from tests.integration.publication_review_support import acknowledgement

    data = prepared(client)
    created = register(client, data)
    assert created.status_code == 201, created.text
    version = created.json()["version"]
    url = (
        data["base"]
        + "/compiled-documents/"
        + version["document_id"]
        + "/versions/"
        + version["id"]
    )
    as_actor(PLATFORM)
    ack = acknowledgement(client, url)
    payload = {"action": "approve", "reason": "Review controlled metadata.", "review_ack": ack}
    missing = client.post(url + "/decision-preview", json=payload)
    assert (
        missing.status_code == 409
        and missing.json()["code"] == "publication_metadata_review_required"
    )
    ack["retrieval_metadata_sha256"] = "0" * 64
    assert client.post(url + "/decision-preview", json=payload).status_code == 409
    ack["retrieval_metadata_sha256"] = version["retrieval_metadata_sha256"]
    assert client.post(url + "/decision-preview", json=payload).status_code == 200
