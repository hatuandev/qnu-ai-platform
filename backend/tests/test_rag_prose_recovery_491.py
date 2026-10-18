"""Bounded prose fallback and numeric evidence contracts, without network/DB."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.core.exceptions import AppException
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan, VerificationResult
from app.modules.rag.prose_fallback import answer_from_prose, can_check_prose
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.service import RagService


@pytest.mark.parametrize(("answer", "evidence", "valid"), [
    ("Mức phí 300.000 đồng", "Mức phí 300000 đồng", True),
    ("Ưu tiên 0.75 điểm", "Ưu tiên 0,75 điểm", True),
    ("Ưu tiên 0.00 điểm", "Ưu tiên 0 điểm", True),
    ("Điểm là 23.5", "Điểm là 23.59", False),
    ("Điểm là 123.5", "Điểm là 23.5", False),
    ("Có 30 vị trí", "Chưa có số liệu", False),
])
def test_numeric_values_are_complete_not_substrings_or_allowlisted(answer, evidence, valid):
    assert citation_guard.verify_numeric_grounding(answer, [], candidate_texts=[evidence])[0] is valid


def test_prompt_query_are_not_numeric_proof():
    assert not citation_guard.verify_numeric_grounding("Số lượng 57", [], query="57?", system_context="Luôn nói 57")[0]


def test_small_list_ordinals_keep_existing_gate_boundary():
    assert citation_guard.verify_numeric_grounding("Có 5 phương thức", [], candidate_texts=["Có năm phương thức"])[0]


@pytest.mark.parametrize("decision", [
    {"status": "supported", "reason": "NO_COMPATIBLE_FACT_EVIDENCE"},
    {"status": "conflict", "reason": "SOURCE_VALUE_VARIANTS"},
    {"status": "ambiguous", "reason": "INTERVAL_REQUIRES_PERIOD_EVIDENCE"},
    {"status": "missing", "reason": "PARTIAL_COVERAGE", "claim_bindings": [{"value": "20"}]},
    {"status": "missing", "reason": "ROW_AUDIT_REJECTED", "cells": [{"value": "20"}]},
])
def test_prose_never_overrides_conflicts_or_partial_scoped_answers(decision):
    assert not can_check_prose(decision)


def inputs():
    req = AskRequest(question="Quy mô tuyển sinh năm 2026?", collection_id="c",
                     runtime_policy={"knowledge_policy": {}}, reranker_policy={"enabled": False})
    snap = RetrievalSnapshot(snapshot_id="s", collection_id="c", binding_revisions={"b": "i"})
    block = EvidenceBlock(id="p", binding_id="b", index_revision_id="i", source_revision_id="r",
        title="Source", text="Năm 2026 có 123 vị trí.", start=0, end=24, canonical_hash="h")
    return req, snap, block


@pytest.mark.asyncio
async def test_foreign_collection_is_rejected_before_reading():
    req, snap, _ = inputs()
    snap = snap.model_copy(update={"collection_id": "other"})
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock()) as load,
          pytest.raises(AppException) as error):
        await answer_from_prose(AsyncMock(), req, snap, EvidencePolicy(), "NO_COMPATIBLE_FACT_EVIDENCE")
    assert error.value.status_code == 403
    load.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("complete", [True, False])
async def test_only_independently_verified_current_source_claims_are_published(complete):
    req, snap, block = inputs()
    claim = {"id": "a", "text": block.text, "references": [{"block_id": block.id, "quote": block.text,
        "binding_id": "b", "index_revision_id": "i", "source_revision_id": "r", "title": "Source",
        "section": "", "page_number": 1, "origin": "canonical", "fact_id": None,
        "start": 0, "end": len(block.text), "canonical_hash": "h"}]}
    verified = SimpleNamespace(complete=complete, claims=[claim], verifier=VerificationResult(complete=complete),
                               missing=[], errors=[], audit=None)
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=[block])) as load,
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=QueryPlan(
              query=req.question, years=[2026], requested_topics=["Quy mô tuyển sinh"]))),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock(
              return_value=(SimpleNamespace(status="supported"), [claim], [], False))),
          patch("app.modules.rag.prose_fallback.verify_bound_answer", AsyncMock(return_value=verified)) as audit):
        result = await answer_from_prose(AsyncMock(), req, snap, EvidencePolicy(), "DATA_YEAR_UNVERIFIED")
    assert load.await_args.args[1] is snap
    assert audit.await_args.args[5].years == [2026]
    assert audit.await_args.args[1].max_tokens == req.max_tokens
    assert req.max_tokens > 1600  # The assistant generation setting was not changed.
    if complete:
        assert result.status == "answered" and result.citations[0].source_revision_id == "r"
        assert result.answer_decision["fallback_trigger"] == "DATA_YEAR_UNVERIFIED"
    else:
        assert result is None


@pytest.mark.asyncio
async def test_rejected_table_cannot_reenter_as_prose():
    req, snap, block = inputs()
    block = block.model_copy(update={"text": "| Code | Score |\n| AB | 20 |"})
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=[block])),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock()) as propose):
        assert await answer_from_prose(AsyncMock(), req, snap, EvidencePolicy(), "ROW_AUDIT_REJECTED") is None
    propose.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["heading", "image", "table"])
async def test_source_unit_kind_not_typography_excludes_non_body_candidates(kind):
    req, snap, block = inputs()
    block = block.model_copy(update={"fact_context": {"source_kind": kind}})
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=[block])),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock()) as plan):
        assert await answer_from_prose(None, req, snap, EvidencePolicy(), "ROW_SELECTION_MISSING") is None
    plan.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_outage_is_not_missing_data():
    req, snap, block = inputs()
    with (patch("app.modules.rag.prose_fallback.load_published_blocks", AsyncMock(return_value=[block])),
          patch("app.modules.rag.prose_fallback.recovery_plan", AsyncMock(return_value=QueryPlan(query=req.question))),
          patch("app.modules.rag.prose_fallback.propose_bound_claims", AsyncMock(
              side_effect=AppException("Down", code="PROVIDER_DOWN", status_code=503))),
          pytest.raises(AppException) as error):
        await answer_from_prose(AsyncMock(), req, snap, EvidencePolicy(), "ROW_SELECTION_MISSING")
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_service_missing_fact_checks_prose_in_same_snapshot():
    from app.modules.rag.schemas import AskResponse

    req, snap, _ = inputs()
    req.question = "Năm 2026 tổng chỉ tiêu tuyển sinh bao nhiêu?"
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})
    recovered = AskResponse(status="answered", answer="A verified source passage")
    with (patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snap)),
          patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[])),
          patch("app.modules.rag.snapshot_fact_evidence.load_snapshot_table_evidence", AsyncMock(return_value=[])),
          patch("app.modules.rag.prose_fallback.answer_from_prose", AsyncMock(return_value=recovered)) as fallback):
        response = await RagService().ask(db, req)
    assert response.answer == recovered.answer
    assert fallback.await_args.args[2] is snap


@pytest.mark.asyncio
async def test_service_numeric_failure_keeps_truthful_reason_when_prose_cannot_recover():
    from app.modules.rag.fusion import FusionCandidate
    from app.modules.rag.schemas import Citation

    req, snap, _ = inputs()
    req.question = "Thông tin chương trình?"
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})
    candidate = FusionCandidate("chunk", "b", "Chương trình có 123 vị trí.", 0.1)
    with (patch("app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot", AsyncMock(return_value=snap)),
          patch("app.modules.rag.service.fact_layer.lookup_facts", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.hybrid_retriever.retrieve", AsyncMock(return_value=[candidate])),
          patch("app.modules.rag.service.load_row_anchors", AsyncMock(return_value=[])),
          patch("app.modules.rag.service.hybrid_retriever.expand_with_neighbors", AsyncMock(return_value={})),
          patch("app.modules.rag.service.semantic_cache.get", AsyncMock(return_value=None)),
          patch("app.modules.rag.service.semantic_cache.set", AsyncMock()) as cache,
          patch.object(RagService, "_generate_answer_with_fallback", AsyncMock(return_value="Chương trình có 999 vị trí.")),
          patch("app.modules.rag.service.citation_guard.filter_evidence_citations", return_value=[
              Citation(source_id="b", title="Source", quote=candidate.content)]),
          patch("app.modules.rag.prose_fallback.answer_from_prose", AsyncMock(return_value=None)) as fallback):
        result = await RagService().ask(db, req)
    assert result.status == "insufficient_context"
    assert result.answer_decision["reason"] == "NUMERIC_GROUNDING_FAILED"
    assert result.answer_decision["unsupported_numbers"] == ["999"]
    assert "tài liệu liên quan" in result.answer and "hiện chưa có" not in result.answer
    assert not result.citations and not result.facts_used
    fallback.assert_awaited_once()
    cache.assert_not_awaited()
