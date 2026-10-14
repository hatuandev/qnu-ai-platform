"""Regression controls for constraints, dependency closure and corrective search."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.core.exceptions import AppException
from app.modules.rag.evidence_audit import (
    AtomicCheck,
    RequiredQualifier,
    SemanticAudit,
    audit_coverage,
)
from app.modules.rag.evidence_blocks import pack_context, split_source_blocks
from app.modules.rag.evidence_claims import bind_claims
from app.modules.rag.evidence_passages import source_grounded_claims
from app.modules.rag.evidence_pipeline import _answer, select_context
from app.modules.rag.evidence_schemas import (
    AnswerProposal,
    EvidenceClaim,
    QueryPlan,
    QuoteReference,
    VerificationResult,
)
from app.modules.rag.evidence_verification import VerifiedAnswer
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def corpus(text, source="s"):
    return split_source_blocks(text, binding_id="b", index_id="i", source_id=source, title="Official")


def bound(source, quote, label="c", references=None):
    proposal = AnswerProposal(status="supported", claims=[EvidenceClaim(id=label, text=quote,
        references=references or [QuoteReference(block_id=source[0].id, quote=quote)])])
    claims, errors = bind_claims(proposal, source)
    assert not errors
    return proposal, claims


def audit_for(claims, qualifier):
    return SemanticAudit(complete=True, missing_constraints=[], required_qualifiers=[qualifier],
        atomic_checks=[AtomicCheck(claim_id=c["id"], claim_quote=c["text"],
            supporting_quote=c["references"][0]["quote"], entailed=True, reason="Source-bound") for c in claims])


def test_year_qualifier_does_not_require_unrelated_document_date_and_old_total():
    source = corpus("# SEASON 2026\n\nTotal: 5.173\n\nThe total in 2026 is 5.173 per 1906/TB-QNU dated 31/05/2026, replacing 4.500 per 263/TB-QNU dated 12/02/2026.")
    _, claims = bound(source, "Total: 5.173", references=[
        QuoteReference(block_id=source[1].id, quote=source[1].text),
        QuoteReference(block_id=source[0].id, quote=source[0].text)])
    qualifier = RequiredQualifier(requirement="năm 2026", role="data_year",
        reference=QuoteReference(block_id=source[2].id, quote=source[2].text), retained_by=["c"])
    accepted, errors, missing, complete = audit_coverage(audit_for(claims, qualifier), claims, source, [2026])
    assert len(accepted) == 1 and not errors and not missing and complete


@pytest.mark.parametrize("condition,answer", [
    ("Threshold: 22.5 points", "Formula applies"),
    ("Deadline: 17:00 on 30/08/2026", "Deadline: 30/08/2026"),
    ("Minimum: 18.00 or graduation score 8.50", "Minimum: 18.00"),
])
def test_constraint_numbers_cannot_be_omitted_even_when_semantic_model_says_complete(condition, answer):
    source = corpus(condition)
    _, claims = bound(source, answer, references=[QuoteReference(block_id=source[0].id, quote=condition)])
    qualifier = RequiredQualifier(requirement="Mandatory condition", retained_by=["c"],
        reference=QuoteReference(block_id=source[0].id, quote=condition))
    assert not audit_coverage(audit_for(claims, qualifier), claims, source, [2026])[3]


def test_numbered_parent_and_letter_branches_pack_atomically_across_pages():
    source = corpus("2. Eligibility conditions:\n\n" +
        "a) Grade Good and 18.00 or graduation score 8.50;\n\n<!-- Page 2 -->\n" +
        "b) Special program: Grade Fair and 16.50 or graduation score 6.50;\n\n3. Different category")
    packed = pack_context(source, [source[1]], [], 3, 20000, atomic_lists=False)
    assert [b.id for b in packed] == [b.id for b in source[:3]]
    assert not pack_context(source, [source[1]], [], 2, 20000, atomic_lists=False)
    assert source[-1] not in packed


def test_span_containment_removes_repeated_sentence_but_not_other_revision():
    source = corpus("Formula applies from 22.5 points. Priority decreases above that threshold.")
    _, outer = bound(source, source[0].text, "outer")
    _, inner = bound(source, "Priority decreases above that threshold.", "inner")
    result = source_grounded_claims([*inner, *outer], source)
    assert len(result) == 1 and result[0]["text"] == source[0].text
    different = [source[0].model_copy(update={"id": "other", "index_revision_id": "other"})]
    _, other_claim = bound(different, different[0].text, "other")
    assert len(source_grounded_claims([*outer, *other_claim], [*source, *different])) == 2


@pytest.mark.parametrize("body", ["In 2025, total: 20", "Total per 31/05/2026: 20"])
def test_data_year_requires_applicability_not_a_date_or_wrong_historical_year(body):
    source = corpus(body)
    _, claims = bound(source, body)
    qualifier = RequiredQualifier(requirement="năm 2026", role="data_year",
        reference=QuoteReference(block_id=source[0].id, quote=body), retained_by=["c"])
    assert not audit_coverage(audit_for(claims, qualifier), claims, source, [2026])[3]


def test_current_metric_excludes_dated_comparison_but_not_a_requested_threshold():
    source = corpus("# SEASON 2026\n\nTotal: 5.173\n\nThe total in 2026 is 5.173 per 1906/TB-QNU dated 31/05/2026, replacing 4.500 per 263/TB-QNU dated 12/02/2026.")
    _, claims = bound(source, source[1].text, references=[
        QuoteReference(block_id=source[1].id, quote=source[1].text),
        QuoteReference(block_id=source[0].id, quote=source[0].text)])
    qualifier = RequiredQualifier(requirement="Current total", role="current_value",
        reference=QuoteReference(block_id=source[2].id, quote=source[2].text), retained_by=["c"])
    assert audit_coverage(audit_for(claims, qualifier), claims, source, [2026])[3]
    qualifier.role = "value_constraint"  # A requested comparison must keep both values.
    assert not audit_coverage(audit_for(claims, qualifier), claims, source, [2026])[3]


def test_method_alias_is_identity_not_a_numeric_threshold_or_an_exact_code_answer():
    source = corpus("Some programs use AB4 with result X.\n\nMethod 4 (AB4 - code 402B): uses result X.")
    _, claims = bound(source, source[0].text)
    qualifier = RequiredQualifier(requirement="Method identity", role="method_identity",
        reference=QuoteReference(block_id=source[1].id, quote=source[1].text), retained_by=["c"])
    assert audit_coverage(audit_for(claims, qualifier), claims, source, [])[3]
    qualifier.role = "value_constraint"  # If the exact code was asked, it must be present.
    assert not audit_coverage(audit_for(claims, qualifier), claims, source, [])[3]


@pytest.mark.asyncio
async def test_implicit_target_name_from_persona_is_not_fabricated_question_proof():
    from app.modules.rag.evidence_scope import InstitutionScope, resolve_institution_scope

    roles = InstitutionScope(target_institution="Organization A", exam_organizer=None,
        target_basis="question", target_quote="Eligibility of Organization A?")
    with patch("app.modules.rag.evidence_scope.structured_call", AsyncMock(return_value=roles)) as infer:
        resolved = await resolve_institution_scope(None, AskRequest(question="Eligibility?", collection_id="c", assistant_code="a"),
            {"persona": "Official assistant of Organization A"})
    assert resolved["target_basis"] == "assistant_scope" and resolved["target_quote"] is None
    assert infer.await_count == 1


def test_season_header_cannot_override_explicit_old_body_year_or_borrow_other_binding():
    from app.modules.rag.evidence_blocks import scope_headers

    source = corpus("# SEASON 2026\n\nIn 2025, total: 20")
    _, claims = bound(source, source[1].text, references=[
        QuoteReference(block_id=source[1].id, quote=source[1].text),
        QuoteReference(block_id=source[0].id, quote=source[0].text)])
    qualifier = RequiredQualifier(requirement="năm 2026", role="data_year",
        reference=QuoteReference(block_id=source[0].id, quote=source[0].text), retained_by=["c"])
    assert not audit_coverage(audit_for(claims, qualifier), claims, source, [2026])[3]
    other = source[1].model_copy(update={"id": "other", "binding_id": "other-binding"})
    assert not scope_headers([*source, other], [other], [2026])


def test_dependency_closure_never_crosses_index_or_next_heading():
    source = corpus("2. Conditions:\n\na) Alpha;\n\nb) Beta;\n\n## Other section\n\nc) Unrelated")
    foreign = source[2].model_copy(update={"id": "foreign", "index_revision_id": "other", "text": "c) Foreign"})
    packed = pack_context([*source, foreign], [source[1]], [], 10, 20000, atomic_lists=False)
    assert [b.id for b in packed] == [b.id for b in source[:3]]


def test_focused_bullet_member_keeps_intro_without_evicting_other_evidence():
    source = corpus("2. Available options:\n\n+ Option A\n\n+ Option B\n\n+ Option C\n\n3. Other section")
    packed = pack_context(source, [source[2]], [], 2, 20000, atomic_lists=False)
    assert [b.id for b in packed] == [source[0].id, source[2].id]
    # A question requesting the complete list still needs every member.
    assert not pack_context(source, [source[2]], [], 2, 20000, atomic_lists=True)


def test_projected_branch_attaches_and_displays_its_own_rule_scope():
    source = corpus("2. Method X eligibility, not ranking by score Y:\n\na) Grade Good and score 18.00;\n\nb) Exception: score 16.50;\n\n3. Different rule")
    _, claims = bound([source[1]], source[1].text)
    result = source_grounded_claims(claims, source)
    assert source[0].text in [claim["text"] for claim in result]
    branch = next(claim for claim in result if claim["text"] == source[1].text)
    assert source[0].text in [ref["quote"] for ref in branch["references"]]
    assert not any(source[-1].text == claim["text"] for claim in result)


def test_coverage_packing_reserves_new_query_facet_instead_of_similar_duplicates():
    source = corpus("Main attribute: Alpha\n\nMain attribute: Alpha again\n\nAdditional condition: Beta")
    packed = pack_context(source, source, [], 2, 20000, atomic_lists=False,
        coverage_goals=["Main attribute", "Additional condition"])
    assert {b.id for b in packed} == {source[0].id, source[2].id}


def test_hybrid_anchor_cannot_reintroduce_verified_wrong_year():
    from app.modules.knowledge.normalization.retrieval_models import TemporalScope
    from app.modules.rag.evidence_search import fuse_blocks
    from app.modules.rag.fusion import FusionCandidate

    source = corpus("Threshold: 20")
    source[0].temporal_scope = TemporalScope(data_years=[2025], status="verified", role="data")
    hit = FusionCandidate("chunk", "b", source[0].text, 1, binding_id="b", index_revision_id="i")
    assert not fuse_blocks(source, ["Threshold"], [[hit]], [2026], 10)


def test_variants_cannot_introduce_a_number_or_remove_resolved_scope():
    from app.modules.rag.evidence_search import search_queries

    plan = QueryPlan(query="Alpha eligibility", years=[2026], entity="Alpha", method="not using score M",
        attribute="apply", exam_organizer="Organization B", target_institution="Organization A",
        search_queries=["Enrollment for 2025", "Threshold 99", "Requirements for Alpha"])
    queries = search_queries("Alpha eligibility?", plan, ["Threshold 90"])
    assert len(queries) == 3
    assert all("not using score M" in q and "Organization B" in q and "2026" in q for q in queries)
    assert not any("2025" in q or "99" in q or "90" in q for q in queries)


@pytest.mark.asyncio
async def test_search_variants_reach_hybrid_not_only_corpus_bm25():
    source = corpus("Eligibility policy for group Alpha")
    req = AskRequest(question="Eligibility for Alpha?", collection_id="c", reranker_policy={"enabled": False})
    plan = QueryPlan(query="Eligibility for Alpha?", entity="Alpha", attribute="Eligibility",
        search_queries=["Alpha qualifying conditions", "Requirements for Alpha"])
    with (patch("app.modules.rag.evidence_pipeline.retrieve_anchors", AsyncMock(return_value=[])) as anchors,
          patch("app.modules.rag.evidence_pipeline.load_published_blocks", AsyncMock(return_value=source)),
          patch("app.modules.rag.evidence_pipeline.reviewed_fact_blocks", AsyncMock(return_value=[]))):
        await select_context(None, req, RetrievalSnapshot(snapshot_id="snap", collection_id="c"), plan,
            EvidencePolicy(), candidate_mode=False)
    assert anchors.await_count == 3
    assert all(call.kwargs["data_years"] == plan.years for call in anchors.call_args_list)


@pytest.mark.asyncio
async def test_missing_proposal_can_retrieve_once_and_answer_from_new_evidence():
    initial = corpus("Related background.")
    recovered = corpus("2. Eligibility:\n\na) Grade Good and score 18.00;\n\nb) Exception: score 16.50;")
    proposal, claims = bound([recovered[1]], recovered[1].text)
    missing = AnswerProposal(status="missing", missing_constraints=["Eligibility branches"])
    verified = VerifiedAnswer(claims, True, [], [], VerificationResult(complete=True), None, [])
    with (patch("app.modules.rag.evidence_pipeline.structured_call", AsyncMock(return_value=QueryPlan(query="Eligibility?"))),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(side_effect=[initial, recovered])) as search,
          patch("app.modules.rag.evidence_pipeline.propose_bound_claims", AsyncMock(side_effect=[
              (missing, [], [], False), (proposal, claims, [], False)])) as propose,
          patch("app.modules.rag.evidence_pipeline.verify_bound_answer", AsyncMock(return_value=verified))):
        result = await _answer(None, AskRequest(question="Eligibility?", collection_id="c"),
            RetrievalSnapshot(snapshot_id="snap", collection_id="c"), EvidencePolicy(), time.perf_counter(), False)
    assert result.status == "answered" and search.await_count == 2 and propose.await_count == 2
    assert result.answer_decision["corrective_retrieval_attempted"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["missing", "conflict", "clarify"])
async def test_unchanged_or_conflicting_context_does_not_regenerate_repeatedly(status):
    source = corpus("Related background.")
    proposal = AnswerProposal(status=status, missing_constraints=["Required condition"])
    with (patch("app.modules.rag.evidence_pipeline.structured_call", AsyncMock(return_value=QueryPlan(query="Eligibility?"))),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(return_value=source)) as search,
          patch("app.modules.rag.evidence_pipeline.propose_bound_claims", AsyncMock(return_value=(proposal, [], [], False))) as propose):
        result = await _answer(None, AskRequest(question="Eligibility?", collection_id="c"),
            RetrievalSnapshot(snapshot_id="snap", collection_id="c"), EvidencePolicy(), time.perf_counter(), False)
    assert not result.citations and result.status == "insufficient_context"
    assert search.await_count == (2 if status == "missing" else 1) and propose.await_count == 1


@pytest.mark.asyncio
async def test_empty_corpus_is_no_answer_but_corrective_database_failure_is_not():
    req = AskRequest(question="Eligibility?", collection_id="c")
    snap = RetrievalSnapshot(snapshot_id="snap", collection_id="c")
    missing = AnswerProposal(status="missing", missing_constraints=["Required condition"])
    with (patch("app.modules.rag.evidence_pipeline.structured_call", AsyncMock(return_value=QueryPlan(query="Eligibility?"))),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(return_value=[])) as search,
          patch("app.modules.rag.evidence_pipeline.propose_bound_claims", AsyncMock()) as propose):
        result = await _answer(None, req, snap, EvidencePolicy(), time.perf_counter(), False)
        assert result.answer_decision["reason"] == "NO_COMPATIBLE_EVIDENCE" and not result.citations
        assert search.await_count == 1 and propose.await_count == 0
    with (patch("app.modules.rag.evidence_pipeline.structured_call", AsyncMock(return_value=QueryPlan(query="Eligibility?"))),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(side_effect=[corpus("Background"),
              AppException("DB unavailable", code="EVIDENCE_SOURCE_UNAVAILABLE", status_code=503)])),
          patch("app.modules.rag.evidence_pipeline.propose_bound_claims", AsyncMock(return_value=(missing, [], [], False))),
          pytest.raises(AppException) as error):
        await _answer(None, req, snap, EvidencePolicy(), time.perf_counter(), False)
    assert error.value.code == "EVIDENCE_SOURCE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_corrective_proposal_provider_outage_remains_an_error_not_no_answer():
    missing = AnswerProposal(status="missing", missing_constraints=["Required condition"])
    with (patch("app.modules.rag.evidence_pipeline.structured_call", AsyncMock(return_value=QueryPlan(query="Eligibility?"))),
          patch("app.modules.rag.evidence_pipeline.select_context", AsyncMock(side_effect=[corpus("Background"), corpus("New proof")])),
          patch("app.modules.rag.evidence_pipeline.propose_bound_claims", AsyncMock(side_effect=[(missing, [], [], False),
              AppException("Unavailable", code="ALL_PROVIDERS_UNAVAILABLE", status_code=503)])),
          pytest.raises(AppException) as error):
        await _answer(None, AskRequest(question="Eligibility?", collection_id="c"),
            RetrievalSnapshot(snapshot_id="snap", collection_id="c"), EvidencePolicy(), time.perf_counter(), False)
    assert error.value.code == "ALL_PROVIDERS_UNAVAILABLE"


def test_safe_partial_merge_does_not_auto_verify_or_borrow_another_index():
    from app.modules.rag.evidence_repair import retain_safe_claims

    source = corpus("Verified condition: 18.00")
    _, claims = bound(source, source[0].text)
    retained = retain_safe_claims([], claims, source)
    assert retained and "verified" not in retained[0]
    changed = [source[0].model_copy(update={"index_revision_id": "different"})]
    assert not retain_safe_claims([], claims, changed)


def test_verified_old_data_is_not_overridden_by_attached_new_heading():
    from app.modules.knowledge.normalization.retrieval_models import TemporalScope

    source = corpus("# SEASON 2026\n\nTotal: 20")
    source[1].temporal_scope = TemporalScope(data_years=[2025], status="verified", role="data")
    _, claims = bound(source, source[1].text, references=[
        QuoteReference(block_id=source[1].id, quote=source[1].text),
        QuoteReference(block_id=source[0].id, quote=source[0].text)])
    qualifier = RequiredQualifier(requirement="năm 2026", role="data_year",
        reference=QuoteReference(block_id=source[0].id, quote=source[0].text), retained_by=["c"])
    assert not audit_coverage(audit_for(claims, qualifier), claims, source, [2026])[3]


@pytest.mark.asyncio
async def test_implicit_year_answer_attaches_a_real_same_source_season_span():
    from app.modules.rag.evidence_claims import propose_bound_claims
    from app.modules.rag.evidence_passages import PassageClaim, PassageProposal

    source = corpus("# SEASON 2026\n\nSome groups may use method AB4.")
    draft = PassageProposal(status="supported", claims=[PassageClaim(id="c", text="Conditional group policy",
        evidence_ids=["e2.1"])])
    with patch("app.modules.rag.evidence_claims.structured_call", AsyncMock(return_value=draft)):
        _, claims, errors, _ = await propose_bound_claims(None, AskRequest(question="Can groups use AB4?", collection_id="c"),
            {"requested": {"years": [2026]}}, source)
    assert not errors and len(claims) == 1
    assert source[0].text in [ref["quote"] for ref in claims[0]["references"]]


def test_default_year_is_valid_correction_feedback_but_an_answer_value_is_not():
    from app.modules.rag.evidence_repair import coverage_feedback

    assert coverage_feedback("Eligibility?", ["năm 2026", "Threshold 90"], [], [2026]) == ["năm 2026"]
