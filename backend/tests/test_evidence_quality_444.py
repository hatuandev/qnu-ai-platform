"""Regression controls for answer completeness, group scope and locator proof.

Covers the six residual quality groups: false-partial audits (counts and
enumeration), single-row answers to group questions, sentences cut across a
page boundary, formula sections needing their legend, and where-answers that
only point at another notice without quoting any path. Question IDs appear
only in these tests, never in runtime modules.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.knowledge.normalization.retrieval_models import TemporalScope
from app.modules.rag.evidence_audit import (
    AtomicCheck,
    RequiredQualifier,
    SemanticAudit,
    audit_coverage,
)
from app.modules.rag.evidence_blocks import pack_context, split_source_blocks
from app.modules.rag.evidence_claims import bind_claims
from app.modules.rag.evidence_constraints import location_pointer_gap
from app.modules.rag.evidence_dependencies import dependency_groups, sentence_continuations
from app.modules.rag.evidence_indexed_audit import AuditedClaim, IndexedAudit
from app.modules.rag.evidence_passages import source_grounded_claims
from app.modules.rag.evidence_schemas import (
    AnswerProposal,
    ClaimVerdict,
    EvidenceClaim,
    QueryPlan,
    QuoteReference,
    VerificationResult,
)
from app.modules.rag.evidence_validation import (
    formula_legend_gap,
    group_single_row_gap,
    temporal_references_supported,
)
from app.modules.rag.evidence_verification import verify_bound_answer
from app.modules.rag.schemas import AskRequest


def corpus(text, source="s"):
    return split_source_blocks(text, binding_id="b", index_id="i", source_id=source, title="Official")


def bound(source, quote, label="c", references=None):
    proposal = AnswerProposal(status="supported", claims=[EvidenceClaim(id=label, text=quote,
        references=references or [QuoteReference(block_id=source[0].id, quote=quote)])])
    claims, errors = bind_claims(proposal, source)
    assert not errors
    return proposal, claims


def audit_for(claims, qualifier, complete=False, missing=None):
    return SemanticAudit(complete=complete, missing_constraints=missing or [], required_qualifiers=[qualifier],
        atomic_checks=[AtomicCheck(claim_id=c["id"], claim_quote=c["text"],
            supporting_quote=c["references"][0]["quote"], entailed=True, reason="Source-bound") for c in claims])


def test_free_missing_over_only_quoted_numbers_is_advisory():
    source = corpus("Thông tin đầu mùa thể hiện 53 ngành; thông báo sau thể hiện 56 mã.\n\n"
                    "Ngày 22/08/2026, Trường thông báo xét bổ sung 28 ngành với tổng 456 chỉ tiêu.")
    _, first = bound(source, source[0].text, "c1",
        references=[QuoteReference(block_id=source[0].id, quote=source[0].text)])
    _, second = bound(source, source[1].text, "c2",
        references=[QuoteReference(block_id=source[1].id, quote=source[1].text)])
    claims = [*first, *second]
    qualifier = RequiredQualifier(requirement="53 ngành đầu mùa và 56 mã sau cập nhật",
        reference=QuoteReference(block_id=source[0].id, quote=source[0].text), retained_by=["c1"])
    audit = audit_for(claims, qualifier, complete=False,
        missing=["Cần làm rõ liệu tính cả 28 ngành bổ sung vào tổng số hay không"])
    accepted, errors, missing, complete = audit_coverage(
        audit, claims, source, [2026], question="Năm 2026 Trường có bao nhiêu ngành?")
    assert len(accepted) == 2 and not errors and not missing and complete


def test_free_missing_naming_unquoted_number_still_blocks():
    source = corpus("Thông tin đầu mùa thể hiện 53 ngành; thông báo sau thể hiện 56 mã.")
    _, claims = bound(source, source[0].text)
    qualifier = RequiredQualifier(requirement="53 ngành đầu mùa và 56 mã sau cập nhật",
        reference=QuoteReference(block_id=source[0].id, quote=source[0].text), retained_by=["c"])
    audit = audit_for(claims, qualifier, complete=False, missing=["Cần bổ sung 99 chỉ tiêu còn thiếu"])
    assert not audit_coverage(audit, claims, source, [2026], question="Năm 2026 có bao nhiêu ngành?")[3]


def test_free_missing_naming_question_number_stays_blocking():
    source = corpus("Thông tin đầu mùa thể hiện 53 ngành.\n\nĐợt bổ sung có 28 ngành.")
    _, first = bound(source, source[0].text, "c1",
        references=[QuoteReference(block_id=source[0].id, quote=source[0].text)])
    _, second = bound(source, source[1].text, "c2",
        references=[QuoteReference(block_id=source[1].id, quote=source[1].text)])
    claims = [*first, *second]
    qualifier = RequiredQualifier(requirement="53 ngành đầu mùa",
        reference=QuoteReference(block_id=source[0].id, quote=source[0].text), retained_by=["c1"])
    audit = audit_for(claims, qualifier, complete=False,
        missing=["Cần làm rõ 28 ngành bổ sung có tính vào tổng hay không"])
    _accepted, _errors, missing, complete = audit_coverage(
        audit, claims, source, [2026], question="Tính cả 28 ngành bổ sung thì tổng là bao nhiêu?")
    assert not complete and missing


def test_number_free_missing_still_blocks():
    source = corpus("Tổng số lượng tuyển sinh: 5.173 chỉ tiêu.")
    _, claims = bound(source, source[0].text)
    qualifier = RequiredQualifier(requirement="tổng chỉ tiêu", role="current_value",
        reference=QuoteReference(block_id=source[0].id, quote=source[0].text), retained_by=["c"])
    audit = audit_for(claims, qualifier, complete=False, missing=["Cần liệt kê điều kiện đi kèm"])
    assert not audit_coverage(audit, claims, source, [2026], question="Năm 2026 tuyển bao nhiêu chỉ tiêu?")[3]


def test_empty_retained_by_filled_when_union_covers_enumeration():
    source = corpus("PT1, mã 100, dùng điểm thi 2026. PT2, mã 200, dùng học bạ. PT3, mã 402A, dùng ĐGNL TP.HCM. "
                    "PT4, mã 402B, dùng ĐGNL Hà Nội. PT5, mã 405, kết hợp năng khiếu.")
    claims = []
    for label, part in enumerate(["PT1, mã 100, dùng điểm thi 2026.", "PT2, mã 200, dùng học bạ.",
                                  "PT3, mã 402A, dùng ĐGNL TP.HCM.", "PT4, mã 402B, dùng ĐGNL Hà Nội.",
                                  "PT5, mã 405, kết hợp năng khiếu."], 1):
        _, part_claims = bound(source, part, f"c{label}",
            references=[QuoteReference(block_id=source[0].id, quote=part)])
        claims.extend(part_claims)
    qualifier = RequiredQualifier(requirement="liệt kê các phương thức năm 2026", role="method_identity",
        reference=QuoteReference(block_id=source[0].id, quote=source[0].text), retained_by=[])
    audit = SemanticAudit(complete=True, missing_constraints=[], required_qualifiers=[qualifier],
        atomic_checks=[AtomicCheck(claim_id=c["id"], claim_quote=c["text"],
            supporting_quote=c["references"][0]["quote"], entailed=True, reason="Source-bound") for c in claims])
    accepted, errors, missing, complete = audit_coverage(
        audit, claims, source, [2026], question="Năm 2026 có những phương thức nào?")
    assert len(accepted) == 5 and not errors and not missing and complete


def test_missing_code_still_blocks_despite_empty_retained_by():
    source = corpus("PT1, mã 100, dùng điểm thi 2026.\n\nPT4, mã 402B, dùng ĐGNL Hà Nội.")
    _, claims = bound(source, source[0].text, references=[QuoteReference(
        block_id=source[0].id, quote=source[0].text)])
    qualifier = RequiredQualifier(requirement="mã 402B của phương thức", role="value_constraint",
        reference=QuoteReference(block_id=source[1].id, quote=source[1].text), retained_by=[])
    audit = audit_for(claims, qualifier, complete=True)
    assert not audit_coverage(audit, claims, source, [2026])[3]


def _fact_claims(entity="Sư phạm Tiếng Anh"):
    source = corpus(f"{entity}\nPhương thức ĐGNL ĐHSP HN: 20")
    fact = source[0].model_copy(update={"origin": "reviewed_fact",
        "fact_context": {"entity_name": entity}})
    blocks = [fact, *source[1:]]
    _, claims = bound(blocks, fact.text, references=[QuoteReference(block_id=fact.id, quote=fact.text)])
    return blocks, claims


def test_group_single_row_gap_needs_group_policy():
    _, claims = _fact_claims()
    assert group_single_row_gap(claims, "ngành sư phạm") == ["Sư phạm Tiếng Anh"]
    assert group_single_row_gap(claims, "Sư phạm Tiếng Anh") == []


def test_group_gap_cleared_by_canonical_policy_claim():
    _blocks, claims = _fact_claims()
    policy = corpus("Một số ngành phù hợp có thể sử dụng PT4. Riêng hai ngành đặc thù dùng PT5.")
    _, policy_claims = bound(policy, policy[0].text, "policy")
    assert group_single_row_gap([*policy_claims, *claims], "ngành sư phạm") == []


@pytest.mark.asyncio
async def test_row_only_group_answer_is_partial_not_supported():
    blocks, claims = _fact_claims()
    plan = QueryPlan(query="Ngành sư phạm có xét ĐGNL Hà Nội không?", entity="ngành sư phạm",
        target_institution="QNU", exam_organizer="Trường ĐHSP Hà Nội", intent="kiểm tra tính đủ điều kiện")
    verifier = VerificationResult(complete=True, verdicts=[ClaimVerdict(
        claim_id="c", entailed=True, relevant=True, scope_compatible=True, reason="Row proof")])
    indexed = IndexedAudit(complete=True, missing_constraints=[],
        claims=[AuditedClaim(claim_id="c", all_assertions_supported=True, reason="Row proof")],
        essential_conditions=[])
    with patch("app.modules.rag.evidence_verification.structured_call",
               AsyncMock(side_effect=[verifier, indexed])):
        verified = await verify_bound_answer(None, AskRequest(question=plan.query, collection_id="c"),
            {"question": plan.query}, claims, blocks, plan, [])
    assert not verified.complete and verified.missing


def test_sentence_continuation_across_page_boundary():
    source = corpus("Để đối chiếu phải dùng điểm đã xác định đúng theo quy định của\n\n"
                    "<!-- Trang 3 -->\nphương thức tương ứng, bao gồm cách xử lý điểm ưu tiên.")
    assert [b.id for b in sentence_continuations(source, source[0])] == [source[1].id]
    packed = pack_context(source, [source[0]], [], 3, 20000, atomic_lists=False)
    assert [b.id for b in packed] == [b.id for b in source]
    _, claims = bound(source, source[0].text)
    texts = [claim["text"] for claim in source_grounded_claims(claims, source)]
    assert source[0].text in texts and source[1].text in texts


@pytest.mark.parametrize("tail", ["## Mục khác", "Phương thức tương ứng", "- ghi chú", "2. Điều kiện:"])
def test_sentence_continuation_stops_at_headings_lists_and_uppercase(tail):
    source = corpus(f"Điểm đã xác định đúng theo quy định của\n\n{tail}")
    assert sentence_continuations(source, source[0]) == []


def test_numbered_parent_groups_formula_run_with_legend():
    source = corpus("3. Công thức quy đổi điểm\n\nY bằng nội suy tuyến tính giữa hai mốc liền kề.\n\n"
                    "Trong đó:\n\n- X là điểm nguồn\n\n- Y là điểm quy đổi\n\n4. Mục khác")
    groups = dependency_groups(source)
    assert [b.id for b in groups[source[2].id]] == [b.id for b in source[:5]]
    packed = pack_context(source, [source[1]], [], 10, 20000, atomic_lists=False)
    assert {b.id for b in source[:5]}.issubset({b.id for b in packed})
    assert source[-1] not in packed


def test_auto_retain_skips_number_free_url_reference():
    source = corpus("Đăng ký trực tuyến theo đường dẫn trong thông báo.\n\n"
                    "Địa chỉ công khai: https://tuyensinh.qnu.edu.vn")
    _, claims = bound(source, source[0].text, references=[QuoteReference(
        block_id=source[0].id, quote=source[0].text)])
    qualifier = RequiredQualifier(requirement="địa chỉ trang https://tuyensinh.qnu.edu.vn",
        role="current_value",
        reference=QuoteReference(block_id=source[1].id, quote=source[1].text), retained_by=[])
    audit = audit_for(claims, qualifier, complete=True)
    accepted, errors, missing, complete = audit_coverage(audit, claims, source, [2026])
    assert accepted and not errors and not complete and missing


def test_formula_legend_gap_requires_uncited_run_members():
    source = corpus("3. Công thức:\n\n𝒀 = 𝑿 + 1\n\nTrong đó:\n\n- 𝑿 là điểm nguồn\n\n- 𝒀 là điểm quy đổi\n\n4. Mục khác")
    _, desc = bound(source, source[0].text, "c1", references=[QuoteReference(
        block_id=source[0].id, quote=source[0].text)])
    _, formula = bound(source, source[1].text, "c2", references=[QuoteReference(
        block_id=source[1].id, quote=source[1].text)])
    claims = [*desc, *formula]
    assert formula_legend_gap(claims, source, "tìm công thức", "công thức quy đổi") is True
    assert formula_legend_gap(claims, source, "tra cứu điểm", "điểm") is False
    rest = []
    for label, block in enumerate(source[2:-1], 3):
        _, part = bound(source, block.text, f"c{label}", references=[QuoteReference(
            block_id=block.id, quote=block.text)])
        rest.extend(part)
    assert formula_legend_gap([*claims, *rest], source, "tìm công thức", None) is False


def test_formula_gap_ignores_bare_intro_line():
    source = corpus("3. Công thức:\n\n𝒀 = 𝑿 + 1\n\nTrong đó:\n\n- 𝑿 là điểm nguồn\n\n4. Mục khác")
    _, desc = bound(source, source[0].text, "c1", references=[QuoteReference(
        block_id=source[0].id, quote=source[0].text)])
    _, formula = bound(source, source[1].text, "c2", references=[QuoteReference(
        block_id=source[1].id, quote=source[1].text)])
    _, legend = bound(source, source[3].text, "c3", references=[QuoteReference(
        block_id=source[3].id, quote=source[3].text)])
    assert formula_legend_gap([*desc, *formula, *legend], source, "tìm công thức", None) is False


def test_location_pointer_without_url_is_incomplete():
    claims = [{"id": "c1", "text": "Đăng ký trực tuyến theo đường dẫn trong Thông báo 151/TB-HĐTS.",
               "references": [{"block_id": "b", "quote": "Đăng ký trực tuyến theo đường dẫn trong Thông báo 151/TB-HĐTS.",
                               "binding_id": "b", "index_revision_id": "i", "source_revision_id": "s",
                               "origin": "canonical"}]}]
    assert location_pointer_gap(claims, "location") is True
    with_url = [{"id": "c1", "text": "Đăng ký tại https://tuyensinh.qnu.edu.vn/bo-sung.",
                 "references": [{"block_id": "b", "quote": "Đăng ký tại https://tuyensinh.qnu.edu.vn/bo-sung.",
                                 "binding_id": "b", "index_revision_id": "i", "source_revision_id": "s",
                                 "origin": "canonical"}]}]
    assert location_pointer_gap(with_url, "location") is False
    assert location_pointer_gap(claims, "retrieve_contact") is False
    assert location_pointer_gap(claims, "tìm địa điểm đăng ký", "địa điểm") is True
    assert location_pointer_gap(claims, "information", "số lượng") is False


def test_verified_old_data_year_still_rejected_for_current_season():
    source = corpus("Tổng chỉ tiêu: 5.173")
    scoped = source[0].model_copy(update={"temporal_scope": TemporalScope(
        data_years=[2025], status="verified", role="data")})
    _, claims = bound([scoped], scoped.text)
    assert temporal_references_supported(claims[0], [2026]) is False
    assert temporal_references_supported(claims[0], [2025]) is True
