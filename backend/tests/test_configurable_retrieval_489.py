"""Configurable budgets against real retrieval/service code with controlled I/O."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.core.retrieval_policy import configured_policy
from app.modules.assistants.schemas import AssistantLifecycleConfig
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.retrieval_diagnostics import attach_diagnostics, pack_hybrid_context
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest, AskResponse, RetrievalSnapshot, SearchRequest
from app.modules.rag.service import RagService


def runtime(**changes):
    return {"knowledge_policy": {"retrieval_limit": 10, "retrieval_policy": {
        "profile": "configured", "dense_top_k": 7, "lexical_top_k": 9,
        "fusion_top_k": 4, "context_top_k": 2, **changes}}}


def snapshot():
    return RetrievalSnapshot(snapshot_id="snap", collection_id="c", binding_revisions={"b": "i"})


def hit(index):
    return {"chunk_id": str(index), "document_id": f"doc-{index % 2}", "content": f"Evidence {index}",
            "binding_id": "b", "index_revision_id": "i"}


def candidate(index, **kwargs):
    return FusionCandidate(str(index), "document", f"Evidence {index}", 0.1,
                           binding_id="b", index_revision_id="i", **kwargs)


@pytest.mark.parametrize("changes", [{"dense_top_k": 0}, {"lexical_top_k": 101},
    {"context_top_k": 5}, {"dense_top_k": True}, {"fusion_top_k": 3.5},
    {"max_context_chars": 999}, {"fusion": "unapproved_algorithm"}])
def test_policy_rejects_bad_numbers_and_unknown_fields(changes):
    with pytest.raises(ValidationError):
        configured_policy(runtime(**changes))


def test_legacy_and_compatibility_fallback_do_not_silently_activate():
    assert configured_policy({}) is None
    assert AssistantLifecycleConfig().knowledge_policy.retrieval_policy.profile == "legacy"
    p = configured_policy(runtime(dense_top_k=None, lexical_top_k=None))
    assert (p.dense_top_k, p.lexical_top_k) == (10, 10)


def test_cache_identity_includes_each_budget_not_client_diagnostics():
    req = AskRequest(question="Question", collection_id="c", runtime_policy=runtime())
    changed = req.model_copy(update={"runtime_policy": runtime(context_top_k=3)})
    assert req.policy_fingerprint() != changed.policy_fingerprint()
    assert "_retrieval_diagnostics" not in req.model_dump()
    before = req.policy_fingerprint()
    req._retrieval_diagnostics.update(secret_client_claim="ignored")
    assert req.policy_fingerprint() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled,configured", [(True, True), (False, True), (True, False), (False, False)])
async def test_retrieval_budgets_propagate_and_legacy_stays_unchanged(enabled, configured):
    p = configured_policy(runtime()) if configured else None
    trace = {}
    async def rerank(query, candidates, top_k, **kwargs):
        return candidates[:top_k]
    with (patch("app.modules.rag.retriever.vector_indexer.search_dense", AsyncMock(return_value=[hit(i) for i in range(7)])) as dense,
          patch.object(hybrid_retriever, "search_sparse_fts", AsyncMock(return_value=[hit(i) for i in range(3, 12)])) as sparse,
          patch("app.modules.rag.retriever.reranker_client.rerank", AsyncMock(side_effect=rerank)) as rank):
        snap = snapshot()
        result = await hybrid_retriever.retrieve(AsyncMock(), "c", "query", top_k=8, rerank_top_k=6,
            snapshot=snap, retrieval_policy=p, reranker_policy={"enabled": enabled, "top_k": 5}, diagnostics=trace)
    assert dense.call_args.kwargs["top_k"] == (7 if configured else 8)
    assert sparse.call_args.kwargs["top_k"] == (9 if configured else 8)
    assert dense.call_args.kwargs["snapshot"] is snap
    assert all(c.binding_id == "b" and c.index_revision_id == "i" for c in result)
    assert len(result) == (2 if configured else 5 if enabled else 6)
    assert trace["rerank_input"] == (4 if configured else 12)
    assert trace["returned_count"] == len(result) and trace["total_ms"] >= 0
    if enabled:
        assert len(rank.call_args.kwargs["candidates"]) == trace["rerank_input"]
    else:
        rank.assert_not_awaited()


@pytest.mark.asyncio
async def test_anchor_prefetch_keeps_fusion_candidates_before_final_context():
    with (patch("app.modules.rag.retriever.vector_indexer.search_dense", AsyncMock(return_value=[hit(i) for i in range(6)])),
          patch.object(hybrid_retriever, "search_sparse_fts", AsyncMock(return_value=[]))):
        result = await hybrid_retriever.retrieve(AsyncMock(), "c", "query", snapshot=snapshot(),
            retrieval_policy=configured_policy(runtime()), return_candidates=True, reranker_policy={"enabled": False})
    assert len(result) == 4


def test_atomic_table_header_and_neighbor_budget_never_slices_source():
    row = candidate(1, metadata={"row_context": [{"text": "footnote"}]})
    header = candidate(2, metadata={"context_only": True})
    tiny = len(row.content) + 2
    kept, texts, info = pack_hybrid_context([row, header], {}, "", tiny)
    assert not kept and not texts and info["dropped_candidates"] == 2
    kept, texts, info = pack_hybrid_context([row, header], {"1": ["footnote"]}, "facts", 200)
    assert kept == [row, header] and texts == [row.content, "footnote", header.content]
    assert info["packed_characters"] <= 200
    assert pack_hybrid_context([row], {}, "x" * 201, 200)[2]["budget_exceeded"]


def test_trace_does_not_invent_retrieval_for_structured_answers():
    req = AskRequest(question="question", collection_id="c")
    req._retrieval_diagnostics.update(profile="legacy")
    response = attach_diagnostics(req, AskResponse(status="answered", answer="Fact"))
    assert response.retrieval_diagnostics["retrieval_executed"] is False


@pytest.mark.asyncio
async def test_search_uses_persisted_assistant_policy_and_matching_collection():
    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(config={**runtime(),
        "knowledge_policy": {**runtime()["knowledge_policy"], "reranker_policy": {"top_k": 5}}})
    with (patch.object(hybrid_retriever, "resolve_retrieval_snapshot", AsyncMock(return_value=snapshot())),
          patch.object(hybrid_retriever, "retrieve", AsyncMock(return_value=[candidate(1)])) as retrieve):
        result = await RagService().search(db, SearchRequest(query="query", collection_id="c", assistant_code="bot"))
    assert retrieve.call_args.kwargs["retrieval_policy"].dense_top_k == 7
    assert result.total_found == 1
    sql = str(db.execute.call_args.args[0])
    assert "assistants.collection_id" in sql and "assistants.is_active IS true" in sql


@pytest.mark.asyncio
async def test_missing_or_foreign_assistant_cannot_choose_another_collection():
    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    with (patch.object(hybrid_retriever, "retrieve", AsyncMock()) as retrieve,
          pytest.raises(AppException) as error):
        await RagService().search(db, SearchRequest(query="query", collection_id="c", assistant_code="foreign"))
    assert error.value.status_code == 404
    retrieve.assert_not_awaited()


@pytest.mark.asyncio
async def test_evidence_context_uses_configured_limits_not_legacy_reranker():
    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_pipeline import select_context
    from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan

    block = EvidenceBlock(id="block", binding_id="b", index_revision_id="i", source_revision_id="s",
                          title="Source", text="Published evidence", start=0, end=18)
    req = AskRequest(question="query", collection_id="c", runtime_policy=runtime(context_top_k=1),
                     reranker_policy={"top_k": 5, "enabled": True})
    with (patch("app.modules.rag.evidence_pipeline.retrieve_anchors", AsyncMock(return_value=[])),
          patch("app.modules.rag.evidence_pipeline.load_published_blocks", AsyncMock(return_value=[block])),
          patch("app.modules.rag.evidence_pipeline.reviewed_fact_blocks", AsyncMock(return_value=[])),
          patch("app.modules.rag.evidence_pipeline.fuse_blocks", return_value=[block]),
          patch("app.modules.rag.evidence_pipeline.bounded_rerank", AsyncMock(return_value=[candidate("block")])) as rank):
        result = await select_context(AsyncMock(), req, snapshot(), QueryPlan(query="query"), EvidencePolicy(), candidate_mode=False)
    assert rank.call_args.args[2] == 1
    assert len(result) <= 1
    assert req._retrieval_diagnostics["context_stages"][0]["context_limit"] == 1
