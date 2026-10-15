"""Historical information is useful, but must never become a current-year answer."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.core.exceptions import AppException
from app.modules.knowledge.normalization.retrieval_models import TemporalScope
from app.modules.rag.evidence_claims import bind_claims
from app.modules.rag.evidence_historical import (
    candidate_years,
    compose_reference,
    discover_reference_year,
    historical_claim_supported,
    reference_plan,
)
from app.modules.rag.evidence_pipeline import answer_with_evidence, decision_response
from app.modules.rag.evidence_schemas import (
    AnswerProposal,
    EvidenceBlock,
    EvidenceClaim,
    QueryPlan,
    QuoteReference,
    VerificationResult,
)
from app.modules.rag.evidence_validation import (
    temporal_references_supported,
    validate_decision_integrity,
)
from app.modules.rag.evidence_verification import VerifiedAnswer, verify_bound_answer
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def source(year=2025, text=None):
    text = text or f"Năm {year}, chương trình Alpha đào tạo 4 năm."
    return EvidenceBlock(id="source:0", binding_id="binding", index_revision_id="index",
        source_revision_id="source", title="Official handbook", text=text, start=0, end=len(text),
        temporal_scope=TemporalScope(status="verified", role="data", data_years=[year]))


def claims_for(block):
    proposal = AnswerProposal(status="supported", claims=[EvidenceClaim(id="claim", text=block.text,
        references=[QuoteReference(block_id=block.id, quote=block.text)])])
    claims, errors = bind_claims(proposal, [block])
    assert not errors
    claims = [{**claim, "verified": True} for claim in claims]
    return proposal, VerifiedAnswer(claims, True, [], [], VerificationResult(complete=True), None, [])


@pytest.mark.asyncio
async def test_missing_current_year_returns_labeled_historical_reference_not_no_answer():
    req = AskRequest(question="Năm 2026 chương trình Alpha đào tạo bao lâu?", collection_id="collection")
    snapshot = RetrievalSnapshot(snapshot_id="snapshot", collection_id="collection")
    plan = QueryPlan(query=req.question, years=[2026], entity="Alpha", attribute="thời gian đào tạo")
    original = decision_response(req, snapshot, "missing", "NO_COMPATIBLE_EVIDENCE", plan)
    block = source()
    proposal, verified = claims_for(block)
    with (patch("app.modules.rag.evidence_pipeline._answer", AsyncMock(return_value=original)),
          patch("app.modules.rag.evidence_blocks.load_published_blocks", AsyncMock(return_value=[block])),
          patch("app.modules.rag.evidence_facts.reviewed_fact_blocks", AsyncMock(return_value=[])),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(return_value=[block])),
          patch("app.modules.rag.evidence_claims.propose_bound_claims", AsyncMock(return_value=(proposal, verified.claims, [], False))),
          patch("app.modules.rag.evidence_verification.verify_bound_answer", AsyncMock(return_value=verified))):
        result = await answer_with_evidence(None, req, snapshot, EvidencePolicy(enabled=True))
    assert result.answer_decision["status"] == "partial"
    assert result.answer_decision["requested"]["years"] == [2026]
    assert result.answer_decision["historical_reference"]["reference_year"] == 2025
    assert "Thông tin năm 2025" in result.answer
    assert "năm 2026" in result.answer and "chưa" in result.answer.casefold()
    assert result.citations[0].quote == block.text
    assert result.status == "insufficient_context"


def test_unknown_metadata_cannot_put_explicit_old_data_under_new_year():
    block = source().model_copy(update={"temporal_scope": TemporalScope()})
    _, verified = claims_for(block)
    assert not temporal_references_supported(verified.claims[0], [2026])
    assert temporal_references_supported(verified.claims[0], [2025])


def test_issue_date_and_filename_are_not_a_historical_candidate():
    block = source(text="Văn bản số 35/TB-QNU ngày 12/03/2025. Chương trình Alpha đào tạo 4 năm.")
    block = block.model_copy(update={"title": "Handbook 2025", "temporal_scope": TemporalScope(issued_date="2025-03-12")})
    assert not candidate_years(block)
    _, verified = claims_for(block)
    assert not historical_claim_supported(verified.claims[0], 2025)


def test_historical_table_in_newer_document_keeps_its_verified_data_year():
    block = source().model_copy(update={"title": "Handbook 2026", "temporal_scope":
        TemporalScope(issued_date="2026-03-12", heading_years=[2026], data_years=[2025], role="data", status="verified")})
    assert candidate_years(block) == {2025}
    _, verified = claims_for(block)
    assert historical_claim_supported(verified.claims[0], 2025)
    assert not historical_claim_supported(verified.claims[0], 2026)


@pytest.mark.parametrize("update,status", [
    ({}, "supported"), ({}, "conflict"), ({}, "clarify"),
    ({"years": [2025, 2026]}, "missing"), ({"coverage": "comparison"}, "missing"),
    ({"document_years": [2026]}, "missing"), ({"event_years": [2026]}, "missing"),
    ({"historical_reference_allowed": False}, "missing"),
])
def test_reference_is_not_a_replacement_for_current_answer_or_other_year_roles(update, status):
    req = AskRequest(question="Alpha?", collection_id="c")
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c")
    plan = QueryPlan(query="Alpha?", years=[2026]).model_copy(update=update)
    original = decision_response(req, snapshot, status, "reason", plan)
    assert reference_plan(original, EvidencePolicy()) is None


def test_current_partial_claims_and_disabled_policy_are_not_replaced():
    req = AskRequest(question="Alpha?", collection_id="c")
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c")
    plan = QueryPlan(query="Alpha?", years=[2026])
    _, verified = claims_for(source(2026))
    original = decision_response(req, snapshot, "partial", "reason", plan, bindings=verified.claims)
    assert reference_plan(original, EvidencePolicy()) is None
    empty = decision_response(req, snapshot, "missing", "reason", plan)
    assert reference_plan(empty, EvidencePolicy(historical_reference_enabled=False)) is None


@pytest.mark.asyncio
async def test_discovery_uses_latest_earlier_data_year_not_future_or_issue_year():
    req = AskRequest(question="Năm 2026 chương trình Alpha đào tạo bao lâu?", collection_id="c")
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c")
    plan = QueryPlan(query=req.question, years=[2026], entity="Alpha", attribute="đào tạo")
    blocks = [source(year).model_copy(update={"id": str(year)}) for year in (2023, 2025, 2027)]
    with (patch("app.modules.rag.evidence_blocks.load_published_blocks", AsyncMock(return_value=blocks)),
          patch("app.modules.rag.evidence_facts.reviewed_fact_blocks", AsyncMock(return_value=[]))):
        assert await discover_reference_year(None, req, snapshot, plan, EvidencePolicy(), False) == 2025


def composed_response():
    req = AskRequest(question="Alpha năm 2026?", collection_id="c")
    snapshot = RetrievalSnapshot(snapshot_id="snap", collection_id="c")
    plan = QueryPlan(query=req.question, years=[2026])
    block = source()
    _, verified = claims_for(block)
    original = decision_response(req, snapshot, "missing", "NO_COMPATIBLE_EVIDENCE", plan)
    result = compose_reference(req, snapshot, original, plan, 2025, verified, [block], 0, decision_response)
    return result


def test_real_integrity_guard_accepts_labeled_reference_without_retagging_citations():
    result = composed_response()
    assert validate_decision_integrity(result.answer_decision, result.answer,
                                       [citation.model_dump() for citation in result.citations])
    assert result.citations[0].source_revision_id == "source"
    assert result.answer_decision["current_year_decision"]["status"] == "missing"


@pytest.mark.parametrize("mutation", ["supported", "remove_label", "future", "wrong_reference", "remove_metadata"])
def test_integrity_guard_rejects_relabeling_old_information_as_current(mutation):
    result = composed_response()
    decision = result.answer_decision
    if mutation == "supported":
        decision["status"] = "supported"
    elif mutation == "remove_label":
        result.answer = decision["answer"] = "Đối chiếu năm 2026: " + source().text
    elif mutation == "future":
        decision["historical_reference"]["reference_year"] = 2027
    elif mutation == "wrong_reference":
        decision["historical_reference"]["reference_year"] = 2024
    else:
        decision.pop("historical_reference")
    assert not validate_decision_integrity(decision, result.answer,
                                           [citation.model_dump() for citation in result.citations])


@pytest.mark.asyncio
async def test_service_error_does_not_become_missing_data_or_trigger_reference():
    error = AppException("Provider unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)
    with (patch("app.modules.rag.evidence_pipeline._answer", AsyncMock(side_effect=error)),
          patch("app.modules.rag.evidence_blocks.load_published_blocks", AsyncMock()) as load,
          pytest.raises(AppException) as failure):
        await answer_with_evidence(None, AskRequest(question="Alpha năm 2026?", collection_id="c"),
            RetrievalSnapshot(snapshot_id="snap", collection_id="c"), EvidencePolicy())
    assert failure.value.code == error.code and load.await_count == 0


@pytest.mark.asyncio
async def test_reference_source_db_failure_is_not_hidden_as_no_data():
    req = AskRequest(question="Alpha năm 2026?", collection_id="c")
    snap = RetrievalSnapshot(snapshot_id="snap", collection_id="c")
    original = decision_response(req, snap, "missing", "reason", QueryPlan(query=req.question, years=[2026]))
    error = AppException("Source unavailable", code="EVIDENCE_SOURCE_UNAVAILABLE", status_code=503)
    with (patch("app.modules.rag.evidence_pipeline._answer", AsyncMock(return_value=original)),
          patch("app.modules.rag.evidence_blocks.load_published_blocks", AsyncMock(side_effect=error)),
          pytest.raises(AppException) as failure):
        await answer_with_evidence(None, req, snap, EvidencePolicy())
    assert failure.value.code == error.code


@pytest.mark.parametrize("mode", ["empty", "irrelevant", "incomplete", "conflict", "unproven_year"])
@pytest.mark.asyncio
async def test_no_answer_remains_when_historical_evidence_is_not_verified(mode):
    req = AskRequest(question="Alpha năm 2026 đào tạo bao lâu?", collection_id="c")
    snap = RetrievalSnapshot(snapshot_id="snap", collection_id="c")
    plan = QueryPlan(query=req.question, years=[2026], entity="Alpha")
    original = decision_response(req, snap, "missing", "reason", plan)
    block = source()
    proposal, verified = claims_for(block)
    if mode == "irrelevant":
        verified.claims = []
        verified.complete = False
    elif mode == "incomplete":
        verified.verifier.complete = False
    elif mode == "conflict":
        verified.verifier.conflict = True
    elif mode == "unproven_year":
        block = source(text="Chương trình Alpha đào tạo 4 năm.").model_copy(update={"temporal_scope": TemporalScope()})
        proposal, verified = claims_for(block)
    with (patch("app.modules.rag.evidence_pipeline._answer", AsyncMock(return_value=original)),
          patch("app.modules.rag.evidence_blocks.load_published_blocks", AsyncMock(return_value=[source()])),
          patch("app.modules.rag.evidence_facts.reviewed_fact_blocks", AsyncMock(return_value=[])),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(return_value=[] if mode == "empty" else [block])),
          patch("app.modules.rag.evidence_claims.propose_bound_claims", AsyncMock(return_value=(proposal, verified.claims, [], False))),
          patch("app.modules.rag.evidence_verification.verify_bound_answer", AsyncMock(return_value=verified))):
        result = await answer_with_evidence(None, req, snap, EvidencePolicy())
    assert result is original and result.answer_decision["status"] == "missing"


@pytest.mark.parametrize("entailed", [True, False])
@pytest.mark.asyncio
async def test_real_verification_and_span_guard_preserve_only_relevant_historical_claims(entailed):
    block = source()
    _, bound = claims_for(block)
    req = AskRequest(question="Alpha năm 2025 đào tạo bao lâu?", collection_id="c")
    plan = QueryPlan(query=req.question, years=[2025], entity="Alpha")

    async def infer(_db, _req, contract, _instruction, _payload, **_kwargs):
        if contract is VerificationResult:
            return contract.model_validate({"complete": entailed, "verdicts": [{"claim_id": "claim",
                "entailed": entailed, "relevant": entailed, "scope_compatible": True, "reason": "Test verdict"}]})
        return contract.model_validate({"claims": [{"claim_id": "claim", "all_assertions_supported": True,
            "reason": "Source-bound"}], "complete": True})

    with patch("app.modules.rag.evidence_verification.structured_call", side_effect=infer):
        verified = await verify_bound_answer(None, req, {"question": req.question}, bound.claims, [block], plan, [])
    assert bool(verified.claims) is entailed
    assert verified.complete is entailed
    if entailed:
        assert verified.audit is not None and historical_claim_supported(verified.claims[0], 2025)
        assert verified.claims[0]["references"][0]["start"] == 0


def test_historical_reference_cannot_mix_two_years_in_one_claim():
    block = source(text="Năm 2025 đào tạo 4 năm; năm 2026 đào tạo 5 năm.")
    _, verified = claims_for(block)
    assert not historical_claim_supported(verified.claims[0], 2025)


@pytest.mark.asyncio
async def test_actual_same_source_heading_can_nominate_year_but_cannot_be_borrowed():
    block = source(text="Chương trình Alpha đào tạo 4 năm.").model_copy(update={"temporal_scope": TemporalScope()})
    header = block.model_copy(update={"id": "heading", "text": "# TUYỂN SINH 2025", "start": 0})
    req = AskRequest(question="Alpha năm 2026 đào tạo bao lâu?", collection_id="c")
    snap = RetrievalSnapshot(snapshot_id="snap", collection_id="c")
    plan = QueryPlan(query=req.question, years=[2026], entity="Alpha")
    for foreign, expected in [(False, 2025), (True, None)]:
        heading = header.model_copy(update={"source_revision_id": "foreign"}) if foreign else header
        with (patch("app.modules.rag.evidence_blocks.load_published_blocks", AsyncMock(return_value=[block, heading])),
              patch("app.modules.rag.evidence_facts.reviewed_fact_blocks", AsyncMock(return_value=[]))):
            assert await discover_reference_year(None, req, snap, plan, EvidencePolicy(), False) == expected
    proposal = AnswerProposal(status="supported", claims=[EvidenceClaim(id="claim", text=block.text,
        references=[QuoteReference(block_id=block.id, quote=block.text),
                    QuoteReference(block_id=header.id, quote=header.text)])])
    bound, errors = bind_claims(proposal, [block, header])
    assert not errors and historical_claim_supported(bound[0], 2025)


def test_unknown_historical_body_year_is_not_overridden_by_newer_heading_hint():
    block = source(text="Năm 2023 chương trình Alpha đào tạo 4 năm.").model_copy(update={
        "temporal_scope": TemporalScope(), "header_context": "# TUYỂN SINH 2026"})
    assert candidate_years(block) == {2023}
