"""Semantic coverage contracts and structural retrieval regression boundaries."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.modules.knowledge.normalization.retrieval_models import TemporalScope
from app.modules.rag.evidence_audit import (
    AtomicCheck,
    RequiredQualifier,
    SemanticAudit,
    audit_coverage,
)
from app.modules.rag.evidence_blocks import enumeration_neighbors, split_source_blocks
from app.modules.rag.evidence_bm25 import rank_blocks
from app.modules.rag.evidence_claims import bind_claims
from app.modules.rag.evidence_pipeline import _answer
from app.modules.rag.evidence_schemas import (
    AnswerProposal,
    ClaimVerdict,
    EvidenceClaim,
    QueryPlan,
    QuoteReference,
    VerificationResult,
)
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def corpus(text):
    return split_source_blocks(text, binding_id="b", index_id="i", source_id="s", title="Official")


def test_enumeration_expansion_respects_requested_subject():
    source = corpus("+ Delivery pathway 1: Alpha\n\n+ Delivery pathway 2: Beta\n\n+ Delivery pathway 3: Gamma")
    assert not enumeration_neighbors(source, [source[0]], 6, subject="Participating departments")
    assert len(enumeration_neighbors(source, [source[0]], 6, subject="Delivery pathways")) == 3


def test_heading_season_is_ranking_hint_not_hard_data_filter():
    current = corpus("Eligibility: condition A")[0]
    current.temporal_scope = TemporalScope(heading_years=[2026])
    old = current.model_copy(update={"id": "old", "source_revision_id": "old",
                                   "temporal_scope": TemporalScope(heading_years=[2025])})
    assert rank_blocks([current, old], ["Eligibility"], 2, [2026])[0] is current
    # Historical data inside a newer heading must keep priority for its data year.
    old.temporal_scope = TemporalScope(heading_years=[2026], data_years=[2025], role="data", status="verified")
    old.scope_years = [2025]
    assert rank_blocks([current, old], ["Eligibility"], 2, [2025])[0] is old


@pytest.mark.asyncio
async def test_rejected_irrelevant_extra_does_not_make_complete_answer_partial():
    source = corpus("Location: portal\n\nAddress: campus")
    proposal = AnswerProposal(status="supported", claims=[
        EvidenceClaim(id=label, text=block.text, references=[QuoteReference(block_id=block.id, quote=block.text)])
        for label, block in zip(["good", "extra"], source, strict=True)])
    claims, _ = bind_claims(proposal, source)
    verdict = VerificationResult(complete=True, verdicts=[
        ClaimVerdict(claim_id="good", entailed=True, relevant=True, scope_compatible=True, reason="Direct answer"),
        ClaimVerdict(claim_id="extra", entailed=False, relevant=False, scope_compatible=True, reason="Unrelated extra"),
    ])
    from app.modules.rag.evidence_indexed_audit import AuditedClaim, IndexedAudit

    audit = IndexedAudit(complete=True, missing_constraints=[], essential_conditions=[], claims=[
        AuditedClaim(claim_id="good", all_assertions_supported=True, reference_indexes=[0], reason="Exact")])
    with (patch("app.modules.rag.evidence_pipeline.structured_call", AsyncMock(return_value=QueryPlan(query="Location?"))),
          patch("app.modules.rag.evidence_verification.structured_call", AsyncMock(side_effect=[verdict, audit])),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(return_value=source)),
          patch("app.modules.rag.evidence_pipeline.propose_bound_claims", AsyncMock(return_value=(proposal, claims, [], False)))):
        result = await _answer(None, AskRequest(question="Location?", collection_id="c"),
            RetrievalSnapshot(snapshot_id="snap", collection_id="c"), EvidencePolicy(), time.perf_counter(), False)
    assert result.status == "answered"
    assert "Location: portal" in result.answer
    assert "phần còn lại" not in result.answer


def bound_claim(text, quote):
    source = corpus(quote)
    proposal = AnswerProposal(status="supported", claims=[EvidenceClaim(id="c", text=text,
        references=[QuoteReference(block_id=source[0].id, quote=quote)])])
    claims, _ = bind_claims(proposal, source)
    return source, claims


def test_unsupported_second_relation_rejects_whole_compound_claim():
    source, claims = bound_claim("Channel A uses exam B, suitable for result C", "Channel A uses exam B")
    audit = SemanticAudit(complete=True, missing_constraints=[], required_qualifiers=[], atomic_checks=[
        AtomicCheck(claim_id="c", claim_quote="Channel A uses exam B", supporting_quote=source[0].text, entailed=True, reason="Exact"),
        AtomicCheck(claim_id="c", claim_quote="suitable for result C", supporting_quote="", entailed=False, reason="Different result type")])
    accepted, errors, _, complete = audit_coverage(audit, claims, source, [])
    assert not accepted and errors and not complete


def test_audit_cannot_omit_an_unchecked_claim_clause_or_fabricate_proof():
    source, claims = bound_claim("Channel A uses exam B, suitable for result C", "Channel A uses exam B")
    audit = SemanticAudit(complete=True, missing_constraints=[], required_qualifiers=[], atomic_checks=[
        AtomicCheck(claim_id="c", claim_quote="Channel A uses exam B", supporting_quote=source[0].text, entailed=True, reason="Exact")])
    assert not audit_coverage(audit, claims, source, [])[0]
    audit.atomic_checks[0].claim_quote = claims[0]["text"]
    audit.atomic_checks[0].supporting_quote = "Invented proof"
    assert not audit_coverage(audit, claims, source, [])[0]


def test_numeric_qualifier_cannot_be_marked_retained_when_answer_omits_it():
    source, claims = bound_claim("Priority follows formula", "Formula applies from 22.5 points; priority decreases.")
    audit = SemanticAudit(complete=True, missing_constraints=[], atomic_checks=[
        AtomicCheck(claim_id="c", claim_quote=claims[0]["text"], supporting_quote=source[0].text, entailed=True, reason="Formula")],
        required_qualifiers=[RequiredQualifier(requirement="Ngưỡng áp dụng", retained_by=["c"],
            reference=QuoteReference(block_id=source[0].id, quote="applies from 22.5 points"))])
    _, _, missing, complete = audit_coverage(audit, claims, source, [])
    assert missing == ["Ngưỡng áp dụng"] and not complete


def test_qualifier_cannot_use_unknown_claim_or_another_source_span():
    source, claims = bound_claim("Valid content", "Valid content")
    audit = SemanticAudit(complete=True, missing_constraints=[], atomic_checks=[
        AtomicCheck(claim_id="c", claim_quote="Valid content", supporting_quote="Valid content", entailed=True, reason="Exact")],
        required_qualifiers=[RequiredQualifier(requirement="Condition", retained_by=["c"],
            reference=QuoteReference(block_id="unpublished", quote="Fabricated condition"))])
    assert not audit_coverage(audit, claims, source, [])[3]
    audit.required_qualifiers[0].reference = QuoteReference(block_id=source[0].id, quote="Valid content")
    audit.required_qualifiers[0].retained_by = ["unknown"]
    assert audit_coverage(audit, claims, source, [])[2] == ["Condition"]


def test_packing_reports_budget_drops_without_truncating_evidence():
    from app.modules.rag.evidence_blocks import pack_context

    source = corpus("Alpha content\n\nBeta content")
    diagnostics = {}
    packed = pack_context(source, source, [], 1, 10000, diagnostics=diagnostics)
    assert len(packed) == 1
    assert diagnostics["dropped"][0]["reason"] == "block_limit"
    assert packed[0].text == "Alpha content"


@pytest.mark.asyncio
async def test_scope_keeps_explicit_other_target_and_requires_question_proof():
    from app.core.exceptions import AppException
    from app.modules.rag.evidence_scope import InstitutionScope, resolve_institution_scope

    req = AskRequest(question="Does Institution B offer program X?", collection_id="c", assistant_code="a")
    roles = InstitutionScope(target_institution="Institution B", exam_organizer=None,
        target_basis="question", target_quote="Does Institution B offer program X?")
    with patch("app.modules.rag.evidence_scope.structured_call", AsyncMock(return_value=roles)):
        assert (await resolve_institution_scope(None, req, {"persona": "Institution A assistant"}))["target_institution"] == "Institution B"
        roles.target_quote = "Invented relation"
        with pytest.raises(AppException, match="Vai trò"):
            await resolve_institution_scope(None, req, {"persona": "Institution A assistant"})
