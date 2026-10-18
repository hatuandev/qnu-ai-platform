"""Scope, claim and source-coordinate regressions; no live model or DB."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.rag.combination_enumeration import (
    EnumerationPlan,
    EnumerationScope,
    validated_scopes,
)
from app.modules.rag.enumeration_scope import ScopeAudit, audit_scope_candidates
from app.modules.rag.evidence_indexed_audit import AuditedClaim
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.response_audit import (
    VisibleAnswerAudit,
    VisibleAssertion,
    audit_visible_answer,
    validate_assertions,
)
from app.modules.rag.row_answer import agreed_selection, align_coordinate_aliases, audit_diagnostics
from app.modules.rag.row_answer_contract import RowAudit, RowCatalog, RowSelection, SourceCell
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.source_candidates import linked_candidates, reference_priority


def inputs():
    return AskRequest(question="Số lượng năm 2026?", collection_id="c"), RetrievalSnapshot(
        snapshot_id="s", collection_id="c", binding_revisions={"b": "i"})


def block(key, text, **updates):
    return EvidenceBlock(id=key, binding_id="b", index_revision_id="i", source_revision_id="r",
        title="Source", text=text, start=0, end=len(text), **updates)


@pytest.mark.parametrize("verdict", [
    {"all_assertions_supported": False}, {"answers_original_question": False},
    {"essential_conditions_retained": False}, {"conflict": True},
    {"evidence_ids": ["foreign"]}, {"evidence_ids": ["e0", "e0"]},
    {"missing_constraints": ["Điều kiện áp dụng"]},
])
@pytest.mark.asyncio
async def test_whole_answer_not_accepted_on_presence_of_numbers_alone(verdict):
    req, snap = inputs()
    audit = VisibleAnswerAudit(**{"all_assertions_supported": True, "answers_original_question": True,
        "essential_conditions_retained": True, "conflict": False, "evidence_ids": ["e0"], **verdict})
    candidate = FusionCandidate("x", "b", "Ngưỡng đầu vào là 20.", 1, binding_id="b", index_revision_id="i")
    with patch("app.modules.rag.response_audit.structured_call", AsyncMock(return_value=audit)):
        result = await audit_visible_answer(AsyncMock(), req, snap, "Chỉ tiêu là 20.", [candidate])
    assert result["accepted"] is False


@pytest.mark.asyncio
async def test_current_snapshot_required_and_provider_error_not_absence():
    req, snap = inputs()
    candidate = FusionCandidate("x", "b", "Text", 1, binding_id="b", index_revision_id="old")
    with patch("app.modules.rag.response_audit.structured_call", AsyncMock()) as call:
        assert not (await audit_visible_answer(None, req, snap, "Text", [candidate]))["accepted"]
        call.assert_not_awaited()
        candidate.index_revision_id = "i"
        call.side_effect = AppException("Provider unavailable", status_code=503, code="UPSTREAM")
        with pytest.raises(AppException):
            await audit_visible_answer(None, req, snap, "Text", [candidate])


@pytest.mark.asyncio
@pytest.mark.parametrize("applicable", [True, False])
async def test_prose_scope_requires_independent_data_applicability(applicable):
    req, _ = inputs()
    proof = block("p", "Danh sách chương trình tuyển sinh năm 2026 dưới đây.")
    catalog = [{"source_id": "r", "proofs": [{"id": "p", "text": proof.text}],
        "allowed_year_proofs": {}, "verified_years": [], "header_contexts": ["Danh sách"], "record_examples": ["Code/name"]}]
    plan = EnumerationPlan(enumerate_entities=True, scopes=[EnumerationScope(source_id="r", year=2026, proof_ids=["p"])])
    with patch("app.modules.rag.enumeration_scope.structured_call", AsyncMock(return_value=ScopeAudit(
            applies_to_all_records=applicable, data_year=2026, proof_ids=["p"]))):
        derived = await audit_scope_candidates(None, req, plan, catalog)
    assert catalog[0]["allowed_year_proofs"] == {}  # original evidence remains untouched
    if applicable:
        assert validated_scopes(plan, derived, {"p": proof}, req.question)["r"].year == 2026
    else:
        with pytest.raises(ValueError):
            validated_scopes(plan, derived, {"p": proof}, req.question)


def test_update_reference_is_search_candidate_not_newest_filename_rule():
    initial = block("old", "Tổng số chỉ tiêu tuyển sinh là 4300 theo thông báo 345.")
    update = block("update", "Tổng số chỉ tiêu tuyển sinh tăng từ 4.300 lên 5100, thay thông báo 345.")
    other = block("other", "Năm 2026 là thời gian công bố.")
    result = linked_candidates([initial, update, other], [initial, other], [2026], max_links=1)
    assert [b.id for b in result][:2] == ["old", "update"]
    assert update.scope_years == []  # never promoted to requested data year
    assert reference_priority(result)[:2] == [update, initial]


@pytest.mark.asyncio
async def test_visible_answer_positive_requires_all_atomic_spans_in_pinned_evidence():
    req, snap = inputs()
    text = "Năm 2026 có 123 vị trí."
    audit = VisibleAnswerAudit(all_assertions_supported=True, answers_original_question=True,
        essential_conditions_retained=True, conflict=False, evidence_ids=["e0"], assertions=[
            VisibleAssertion(answer_quote=text, evidence_id="e0", evidence_quote=text, entailed=True, relevant=True)])
    candidate = FusionCandidate("chunk", "b", text, 1, binding_id="b", index_revision_id="i")
    with patch("app.modules.rag.response_audit.structured_call", AsyncMock(return_value=audit)):
        result = await audit_visible_answer(None, req, snap, text, [candidate])
    assert result["accepted"] and result["candidate_ids"] == ["chunk"]
    assert "assertions" not in result  # no repeated corpus in diagnostics


@pytest.mark.asyncio
async def test_recovery_planner_carries_original_scope_and_enumeration_coverage():
    from app.modules.rag.prose_fallback import RecoveryIntent, recovery_plan

    req, _ = inputs()
    with patch("app.modules.rag.prose_fallback.structured_call", AsyncMock(return_value=RecoveryIntent(
            topic="Phương thức tuyển sinh", coverage="comparison",
            required_topics=["phương thức năm 2025", "phương thức năm 2026"],
            entity=None, intent="So sánh phương thức", event=None, round=None,
            scalar_update_lookup=False))) as call:
        plan = await recovery_plan(None, req, "So sánh các phương thức năm 2025 và 2026", [2025, 2026])
    assert plan.years == [2025, 2026] and plan.coverage == "comparison"
    assert len(plan.requested_topics) == 2
    assert call.await_args.args[4] == {"question": plan.query}


def test_verified_other_year_does_not_enter_requested_scope():
    initial = block("a", "Tổng số chỉ tiêu tuyển sinh là 4300 theo thông báo 345.")
    old = block("b", initial.text, scope_years=[2025])
    assert linked_candidates([initial, old], [initial], [2026]) == [initial]


def test_equal_value_not_equal_cell_coordinate():
    def cell(start):
        return SourceCell("r", "Entity", "Metric 2025", "20", [{"binding_id": "b", "index_revision_id": "i",
            "source_revision_id": "s", "canonical_hash": "h", "start": start, "end": start + 10}])
    catalog = RowCatalog(cells={"a": cell(0), "alias": cell(0), "different": cell(20)})
    selected = RowSelection(status="selected", cell_ids=["a"])
    audit = RowAudit(compatible=True, scope_supported=True, complete=True, required_cell_ids=["alias"])
    assert align_coordinate_aliases(selected, audit, catalog).required_cell_ids == ["a"]
    audit.required_cell_ids = ["different"]
    assert align_coordinate_aliases(selected, audit, catalog).required_cell_ids == ["different"]
    diagnostic = audit_diagnostics(selected, audit, catalog)
    assert diagnostic["selector_only_cell_ids"] == ["a"]
    assert diagnostic["auditor_only_cell_ids"] == ["different"]


def test_audit_diagnostic_reason_not_a_semantic_requirement():
    from app.modules.rag.evidence_indexed_audit import IndexedAudit, resolve_audit

    assert not AuditedClaim(claim_id="c", all_assertions_supported=False).all_assertions_supported
    assert len(AuditedClaim(claim_id="c", all_assertions_supported=False, reason="x" * 400).reason) == 400
    audit = IndexedAudit(claims=[AuditedClaim(claim_id="c", all_assertions_supported=False, reason="x" * 400)], complete=False)
    resolved = resolve_audit(audit, [{"id": "c", "text": "Claim", "references": [{"quote": "Proof"}]}], {})
    assert not resolved.atomic_checks[0].entailed
    assert len(resolved.atomic_checks[0].reason) == 400


@pytest.mark.asyncio
async def test_invalid_scope_followup_keeps_unknown_not_422():
    from app.modules.rag.conversation_acts import resolve_act_scopes

    req, snap = inputs()
    plan = EnumerationPlan(enumerate_entities=True, scopes=[EnumerationScope(source_id="r", year=2026)])
    catalog = [{"source_id": "r", "proofs": [], "allowed_year_proofs": {}, "verified_years": [],
        "header_contexts": [], "record_examples": []}]
    with (patch("app.modules.rag.conversation_acts.scope_catalog", return_value=catalog),
          patch("app.modules.rag.conversation_acts.structured_call", AsyncMock(return_value=plan))):
        scopes = await resolve_act_scopes(None, req, [], [], {}, snap)
    assert scopes["r"].year is None


@pytest.mark.parametrize(("answer", "quote", "valid"), [
    ("Mức ưu tiên là 0,75 điểm.", "Mức ưu tiên là 0,75 điểm.", True),
    ("Mức ưu tiên tối đa là 3 điểm.", "Điểm thưởng tối đa bằng 10% thang điểm 30.", False),
    ("Giá trị là 20.", "Giá trị là 200.", False),
])
def test_each_assertion_needs_its_own_exact_proof_and_numbers(answer, quote, valid):
    assertion = VisibleAssertion(answer_quote=answer, evidence_id="e0", evidence_quote=quote, entailed=True, relevant=True)
    assert validate_assertions(answer, {"e0": quote}, [assertion])[0] is valid


def test_a_supported_first_clause_cannot_hide_an_unsupported_extra():
    answer = "Giá trị là 20. Không có ngoại lệ."
    assertion = VisibleAssertion(answer_quote="Giá trị là 20.", evidence_id="e0",
        evidence_quote="Giá trị là 20.", entailed=True, relevant=True)
    assert not validate_assertions(answer, {"e0": assertion.evidence_quote}, [assertion])[0]
    assertion.evidence_quote = "Giá trị là 20."
    assert not validate_assertions("Giá trị là 20.", {"e0": "Giá trị là 200."}, [assertion])[0]


@pytest.mark.parametrize(("quote", "proof", "supported"), [
    ("Điểm chuẩn là 26,5.", "Điểm chuẩn\nlà   26,5.", True),
    ("Khu vực 1 được cộng 0,75 điểm.", "Khu vực 1 được cộng\n0,75 điểm.", True),
    ("Điểm chuẩn là 26,5.", "Điểm chuẩn là 25,85.", False),
    ("Điểm chuẩn là 26,5", "Ghi chú: Điểm chuẩn là 26,5 cho đợt 1.", True),
])
def test_quote_reflow_matches_but_words_and_numbers_stay_exact(quote, proof, supported):
    from app.modules.rag.response_audit import quote_supported

    assert quote_supported(quote, proof) is supported


def test_reflowed_quote_keeps_original_provenance_and_assertion_valid():
    answer = "Điểm chuẩn là 26,5."
    assertion = VisibleAssertion(answer_quote=answer, evidence_id="e0",
        evidence_quote="Điểm chuẩn\nlà 26,5.", entailed=True, relevant=True)
    valid, ids = validate_assertions(answer, {"e0": "Điểm chuẩn\nlà   26,5."}, [assertion])
    assert valid and ids == {"e0"}


def test_partial_coordinate_agreement_cannot_turn_into_complete_or_bypass_scope():
    def cell(key):
        return SourceCell("row", "Entity", key, "20", [])
    catalog = RowCatalog(cells={"a": cell("Metric 2024"), "b": cell("Metric 2025")},
        rows={"row": {"context_ids": [], "scope_candidates": [], "note_candidates": []}})
    selection = RowSelection(status="selected", cell_ids=["a", "b"])
    audit = RowAudit(compatible=True, scope_supported=True, complete=True, required_cell_ids=["a"])
    assert agreed_selection(selection, audit, catalog).cell_ids == ["a"]
    audit.required_cell_ids = ["a", "b"]
    assert agreed_selection(selection.model_copy(update={"cell_ids": ["a"]}), audit, catalog) is None
    audit.required_cell_ids = ["a"]
    audit.scope_supported = False
    assert agreed_selection(selection, audit, catalog) is None
    audit.scope_supported = True
    audit.required_context_ids = ["foreign"]
    assert agreed_selection(selection, audit, catalog) is None
