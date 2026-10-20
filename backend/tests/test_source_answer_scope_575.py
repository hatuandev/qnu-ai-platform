"""General source-scope regressions, independent of benchmark entities and values."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.core.evidence_policy import EvidencePolicy
from app.modules.rag.evidence_schemas import (
    EvidenceBlock,
    QueryPlan,
    QuoteReference,
    VerificationResult,
)
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def block(key, text, start=0, kind='paragraph', parent=None, revision='r'):
    return EvidenceBlock(id=key, unit_id=key, text=text, start=start, end=start + len(text),
        binding_id='b', index_revision_id='i', source_revision_id=revision, canonical_hash='h', title='Fixture',
        parent_id=parent, fact_context={'source_kind': kind, 'context_unit_ids': []})


def bound(b, quote=None):
    from app.modules.rag.evidence_validation import bind_quote

    quote = quote or b.text
    return {'id': 'claim', 'text': quote, 'references': [bind_quote(QuoteReference(block_id=b.id, quote=quote), {b.id: b})]}


@pytest.mark.parametrize('marker', ['1.', '2)', 'a)'])
def test_extracting_part_of_list_item_retains_its_own_limit_but_not_next_item(marker):
    from app.modules.rag.evidence_passages import source_grounded_claims

    first = marker + ' Ưu tiên dữ liệu đã xác nhận. Bản tổng hợp không thay thế bản gốc.'
    b = block('list', first + '\n3. Hồ sơ thuộc nhóm khác cần đối soát.', kind='list')
    claims = source_grounded_claims([bound(b, marker + ' Ưu tiên dữ liệu đã xác nhận.')], [b], primary_only=True)
    assert len(claims) == 1 and claims[0]['text'] == first
    assert claims[0]['references'][0]['quote'] == first


def test_audit_catalog_checks_unselected_same_source_rule_not_just_chosen_sentence():
    from app.modules.rag.evidence_indexed_audit import audit_payload

    permission = block('allow', 'Được phép gia hạn trong phạm vi hồ sơ đã nêu.', parent='rule')
    condition = block('condition', 'Cần văn bản kiểm tra và quyết định có chữ ký.', 100, parent='rule')
    payload, _ = audit_payload({'claims': [bound(permission)]}, [permission, condition])
    assert condition.text in payload['source_conditions'].values()


def test_unrelated_owner_or_revision_cannot_invent_conditions_for_a_selected_rule():
    from app.modules.rag.evidence_indexed_audit import audit_payload

    body = block('rule', 'Hồ sơ đã được xác nhận.', parent='section')
    other = block('other', 'Ngày hết hạn của chương trình khác: 02/04/2040.', 100, parent='another')
    foreign = block('foreign', 'Cần duyệt theo revision khác.', 200, parent='section', revision='foreign')
    payload, _ = audit_payload({'claims': [bound(body)]}, [body, other, foreign])
    assert not payload.get('source_conditions')


@pytest.mark.asyncio
async def test_rule_recovery_keeps_both_literal_anchor_and_full_applicable_rule():
    from app.modules.rag.prose_fallback import answer_from_prose

    caption = block('cap', 'Bảng 23. Tóm tắt các giới hạn', 10)
    header = block('t:header', '| Mã | Giới hạn | Phạm vi |\n| --- | --- | --- |', 60, 'table', 't')
    row = block('row', '| ZX-0042 | 9 ngày | Không thay đổi chỉ tiêu. |', 160, 'table', 't')
    row.header_context = header.text
    rule = block('rule', 'Gia hạn cần văn bản kiểm tra và quyết định trong cùng kỳ.', 260)
    req = AskRequest(question='Ngoại lệ ZX-0042 có điều kiện gì, thay đổi chỉ tiêu không?', collection_id='c', reranker_policy={'enabled': False})
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    seen = {}

    async def propose(db, req, payload, selected):
        seen['ids'] = {b.id for b in selected}
        return SimpleNamespace(status='missing'), [], [], False

    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[caption, header, row, rule])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=QueryPlan(query=req.question))),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(side_effect=propose))):
        assert await answer_from_prose(None, req, snap, EvidencePolicy(), 'ROW_RULE_REQUIRES_CONTEXT') is None
    assert {'row', 'rule'} <= seen['ids']


@pytest.mark.parametrize('answer,retained', [
    ('Ngày tiếp nhận là 02/04/2040.', True),
    ('Ngày tiếp nhận: 02/04/2040.', True),
    ('Ngày tiếp nhận không phải 02/04/2040.', False),
    ('Ngày kết thúc là 02/04/2040.', False),
    ('Ngày tiếp nhận là 03/04/2040.', False),
    ('Ngày tiếp nhận là 02/04/20401.', False),
    ('Ngày tiếp nhận là 02/04/2040X.', False),
    ('Không đúng rằng ngày tiếp nhận là 02/04/2040.', False),
])
def test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format(answer, retained):
    from app.modules.rag.source_scope_audit import SourceConditionCheck, condition_gaps

    clauses = {'e.c0': 'Ngày tiếp nhận: 02/04/2040.'}
    checks = [SourceConditionCheck(clause_id='e.c0', required=True, retained_by=['a'])]
    assert (not condition_gaps(clauses, checks, {'a': answer})) is retained


@pytest.mark.parametrize('join', [' và ', '; '])
def test_distinct_date_roles_are_separate_source_conditions(join):
    from app.modules.rag.source_scope_audit import source_clauses

    clauses = source_clauses({'e': 'Bắt đầu áp dụng từ 03/02/2034' + join + 'kết thúc đánh giá vào 04/06/2035.'})
    assert any('03/02/2034' in v and '04/06/2035' not in v for v in clauses.values())
    assert any('04/06/2035' in v and '03/02/2034' not in v for v in clauses.values())


def test_source_conditions_keep_decimal_and_negative_requirement():
    from app.modules.rag.source_scope_audit import source_clauses

    text = 'Mức tối thiểu là 18.75; không được bỏ xác nhận an toàn.'
    clauses = list(source_clauses({'e': text}).values())
    assert any('18.75' in v for v in clauses) and any('không được bỏ xác nhận an toàn' in v for v in clauses)


def test_explicit_appendix_expands_descendants_without_cross_revision_or_next_appendix():
    from app.modules.rag.source_locators import referenced_sections

    root = block('app', '## PHỤ LỤC IV. Quy định bổ sung', kind='heading')
    child = block('sub', '### IV.1. Thiết bị', 50, 'heading', 'app')
    rule = block('rule', 'Chỉ áp dụng với hồ sơ cùng kỳ.', 100, parent='sub')
    foreign = block('foreign', 'Không thuộc revision này.', 130, parent='sub', revision='x')
    outside = block('out', 'Một phụ lục khác.', 180, parent='app2')
    assert [b.id for b in referenced_sections([root, child, rule, foreign, outside], 'Điều kiện tại Phụ lục IV?')] == ['rule']


@pytest.mark.parametrize('flags', [(False, True), (True, False)])
def test_selected_identity_schema_cannot_silently_have_non_identity_or_subset_flags(flags):
    from app.modules.rag.source_identity_enumeration import IdentityTableChoice

    with pytest.raises(ValidationError):
        IdentityTableChoice(status='selected', table_id='t0', all_rows=flags[0], identity_only=flags[1])


@pytest.mark.asyncio
async def test_rule_question_leaves_coordinate_route_before_it_can_claim_complete():
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import build_catalog
    from app.modules.rag.source_rows import source_rows
    from tests.test_rag_rows_stage3 import fixture_source

    question = 'Mã ZX-0042 được gia hạn theo điều kiện nào?'
    md = '| Mã | Đối tượng | Hạn |\n| --- | --- | --- |\n| ZX-0042 | Hồ sơ thiết bị | 8 ngày |'
    rows = source_rows(*fixture_source(md), question)
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='cc', binding_revisions={'binding_a': 'index_a'})
    catalog = build_catalog(rows, snap, question)
    headers = list(catalog.contexts)
    req = AskRequest(question=question, collection_id='cc')

    async def reader(db, req, contract, instruction, payload, **kwargs):
        return contract.model_validate({'context_ids': headers, 'answer_mode': 'rules'})

    with patch('app.modules.rag.row_answer.structured_call', AsyncMock(side_effect=reader)) as model:
        response = await answer_from_rows(None, req, snap, rows)
    assert response.answer_decision['reason'] == 'ROW_RULE_REQUIRES_CONTEXT'
    assert response.status == 'insufficient_context' and not response.citations and model.await_count == 1


def test_rule_recovery_is_eligible_but_conflict_and_partial_are_not():
    from app.modules.rag.prose_fallback import can_check_prose

    assert can_check_prose({'status': 'missing', 'reason': 'ROW_RULE_REQUIRES_CONTEXT'})
    assert not can_check_prose({'status': 'conflict', 'reason': 'ROW_RULE_REQUIRES_CONTEXT'})
    assert not can_check_prose({'status': 'missing', 'reason': 'ROW_RULE_REQUIRES_CONTEXT', 'cells': [{'id': 'x'}]})


@pytest.mark.asyncio
@pytest.mark.parametrize('second_complete', [False, True])
async def test_semantic_repair_is_once_on_same_evidence_then_reverified(second_complete):
    from app.modules.rag.prose_fallback import answer_from_prose

    b = block('meaning', 'Nguồn chưa quy định ký hiệu ~; giữ nguyên ký hiệu khi lưu.')
    req = AskRequest(question='Ký hiệu ~ có giá trị số nào và lưu thế nào?', collection_id='c', reranker_policy={'enabled': False})
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    claim = bound(b)
    incomplete = SimpleNamespace(complete=False, claims=[claim], verifier=VerificationResult(complete=False),
                                 missing=['Thiếu cách bảo toàn ký hiệu.'], errors=[], audit=None)
    final = SimpleNamespace(complete=second_complete, claims=[claim], verifier=VerificationResult(complete=second_complete),
                            missing=[] if second_complete else incomplete.missing, errors=[], audit=None)
    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[b])) as load,
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=QueryPlan(query=req.question))),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(return_value=(SimpleNamespace(status='supported'), [claim], [], False))) as propose,
          patch('app.modules.rag.prose_fallback.verify_bound_answer', AsyncMock(side_effect=[incomplete, final])) as verify):
        response = await answer_from_prose(None, req, snap, EvidencePolicy(), 'METRIC_UNVERIFIED')
    assert load.await_count == 1 and propose.await_count == verify.await_count == 2
    assert [b.id for b in propose.await_args_list[0].args[3]] == [b.id for b in propose.await_args_list[1].args[3]]
    assert propose.await_args_list[1].args[2]['coverage_repair']['missing_constraints'] == incomplete.missing
    assert (response is not None) is second_complete
    assert req._retrieval_diagnostics['prose_fallback']['semantic_repair_attempted']


@pytest.mark.parametrize('invalid', [[], ['0042'], ['', 'Mục chưa rõ'], ['0042', ''], ['0042', 'Một mục']])
def test_identity_enumeration_never_throws_or_hides_malformed_or_duplicate_rows(invalid):
    from app.modules.rag.source_identity_enumeration import identity_entries

    table = {'rows': [['0042', 'Mục đầu'], invalid], 'row_unit_ids': ['a', 'b']}
    assert identity_entries(table, 0, 1) is None


def test_unlocated_heading_cannot_expand_every_unparented_block():
    from app.modules.rag.source_locators import referenced_sections

    heading = block('h', '## PHỤ LỤC V. Phần bổ sung', kind='heading').model_copy(update={'unit_id': None})
    unrelated = block('p', 'Quy định không thuộc mục này.', 50)
    assert not referenced_sections([heading, unrelated], 'Theo Phụ lục V?')


@pytest.mark.parametrize('value', ['0', 'Chưa công bố', 'Không áp dụng'])
@pytest.mark.asyncio
async def test_literal_and_own_row_description_are_returned_together_without_new_meaning(value):
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import (
        MetricScope,
        RowAudit,
        RowSelection,
        build_catalog,
    )
    from app.modules.rag.source_rows import source_rows
    from tests.test_rag_rows_stage3 import fixture_source

    question = 'Mã ZX-0042 có giá trị và mô tả gì?'
    md = '| Mã | Giá trị | Mô tả |\n| --- | --- | --- |\n| ZX-0042 | ' + value + ' | Phạm vi ghi nguyên văn. |'
    rows = source_rows(*fixture_source(md), question)
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='cc', binding_revisions={'binding_a': 'index_a'})
    catalog = build_catalog(rows, snap, question)
    headers, cells = list(catalog.contexts), list(catalog.cells)
    req = AskRequest(question=question, collection_id='cc')
    with patch('app.modules.rag.row_answer.structured_call', AsyncMock(side_effect=[
            MetricScope(context_ids=headers), RowSelection(status='selected', cell_ids=cells, scope_ids=headers),
            RowAudit(compatible=True, scope_supported=True, complete=True, required_cell_ids=cells, required_context_ids=headers)])):
        response = await answer_from_rows(None, req, snap, rows)
    assert response.status == 'answered' and value in response.answer and 'Phạm vi ghi nguyên văn.' in response.answer
    assert [c['value'] for c in response.answer_decision['cells']] == [value, 'Phạm vi ghi nguyên văn.']
    assert all(c.source_revision_id == 'source_a' and c.canonical_hash for c in response.citations)


@pytest.mark.parametrize('quote', ['Số là 12.75.', 'Mã phiên bản là v2.10.', 'Không được bỏ bước đối soát.'])
def test_ordinary_source_paragraph_is_not_lost_by_clause_segmentation(quote):
    from app.modules.rag.source_scope_audit import source_clauses

    assert quote in source_clauses({'e': quote}).values()


@pytest.mark.asyncio
async def test_conflicting_evidence_is_not_sent_through_semantic_repair():
    from app.modules.rag.prose_fallback import answer_from_prose

    b = block('p', 'Hai phạm vi đang có kết quả mâu thuẫn.')
    req = AskRequest(question='Có thể chốt kết quả chưa?', collection_id='c', reranker_policy={'enabled': False})
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    conflict = SimpleNamespace(complete=False, claims=[bound(b)], verifier=VerificationResult(complete=False, conflict=True),
                               missing=[], errors=[], audit=None)
    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[b])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=QueryPlan(query=req.question))),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(return_value=(SimpleNamespace(status='supported'), [bound(b)], [], False))) as propose,
          patch('app.modules.rag.prose_fallback.verify_bound_answer', AsyncMock(return_value=conflict))):
        assert await answer_from_prose(None, req, snap, EvidencePolicy(), 'METRIC_UNVERIFIED') is None
    assert propose.await_count == 1 and not req._retrieval_diagnostics['prose_fallback']['semantic_repair_attempted']


def test_condition_scope_follows_reverse_order_links_without_crossing_revision():
    from app.modules.rag.evidence_indexed_audit import audit_payload

    last = block('last', 'Cần xác nhận cuối cùng.', 0)
    middle = block('middle', 'Điều kiện trung gian.', 100)
    root = block('root', 'Quy tắc được hỏi.', 200)
    root.fact_context['context_unit_ids'] = ['middle']
    middle.fact_context['context_unit_ids'] = ['last']
    foreign = block('last', 'Điều kiện revision khác.', 0, revision='foreign').model_copy(update={'id': 'foreign'})
    payload, _ = audit_payload({'claims': [bound(root)]}, [last, middle, root, foreign])
    assert last.text in payload['source_conditions'].values()
    assert foreign.text not in payload['source_conditions'].values()


@pytest.mark.asyncio
async def test_literal_anchor_is_not_demoted_by_the_packers_section_priority_mask():
    from app.modules.rag.prose_fallback import answer_from_prose

    heading = block('app', '## PHỤ LỤC VII. Điều kiện', kind='heading')
    rule = block('rule', 'Gia hạn cần xác nhận cùng kỳ.', 50, parent='app')
    extras = [block(f'other{i}', f'Nội dung bổ sung thứ {i}.', 100 + 40*i, parent='app') for i in range(5)]
    caption = block('caption', 'Bảng 23. Các trường hợp', 350)
    header = block('t:header', '| Mã | Phạm vi |\n| --- | --- |', 400, 'table', 't')
    row = block('row', '| ZX-0042 | Không thay đổi chỉ tiêu. |', 450, 'table', 't')
    row.header_context = header.text
    req = AskRequest(question='Phụ lục VII cho ZX-0042 gia hạn theo điều kiện nào, thay đổi chỉ tiêu không?', collection_id='c', reranker_policy={'enabled': False})
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    seen = {}

    async def propose(db, req, payload, selected):
        seen['ids'] = {b.id for b in selected}
        return SimpleNamespace(status='missing'), [], [], False

    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[heading, rule, *extras, caption, header, row])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=QueryPlan(query=req.question))),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(side_effect=propose))):
        assert await answer_from_prose(None, req, snap, EvidencePolicy(context_limit=3), 'ROW_RULE_REQUIRES_CONTEXT') is None
    assert {'rule', 'row'} <= seen['ids']


@pytest.mark.parametrize('conditions', [
    {'foreign.c0': 'Điều kiện ngoài nguồn.'},
    {'e9.c0': 'Điều kiện ngoài nguồn.'},
    {'e1.c0': 'Tự đổi ngưỡng thành 99.'},
])
def test_condition_completion_rejects_unknown_ids_and_non_source_text(conditions):
    from app.modules.rag.evidence_claims import restore_condition_claims

    b = block('rule', 'Chỉ áp dụng khi có xác nhận.')
    with pytest.raises(ValueError):
        restore_condition_claims(conditions, [b])


@pytest.mark.asyncio
@pytest.mark.parametrize('reverified', [True, False])
async def test_missing_source_clause_is_copied_exactly_and_never_auto_approved(reverified):
    from app.modules.rag.prose_fallback import answer_from_prose

    b = block('rule', 'Được dùng trong cùng kỳ. Không miễn xác nhận an toàn.')
    claim = bound(b, 'Được dùng trong cùng kỳ.')
    gap = 'Không miễn xác nhận an toàn.'
    req = AskRequest(question='Có được dùng trong cùng kỳ không?', collection_id='c', reranker_policy={'enabled': False})
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    initial = SimpleNamespace(complete=False, claims=[claim], verifier=VerificationResult(complete=True),
        missing=['Thiếu điều kiện nguồn e1.c1.'], errors=[], audit=SimpleNamespace(complete=False),
        source_condition_gaps={'e1.c1': gap})

    async def verify(db, req, payload, claims, blocks, plan, rules):
        if 'coverage_repair' not in payload:
            return initial
        restored = [c for c in claims if c['id'].startswith('__source_condition_')]
        assert len(restored) == 1 and restored[0]['text'] == gap
        assert restored[0]['references'][0]['quote'] == gap
        assert restored[0]['references'][0]['canonical_hash'] == 'h'
        return SimpleNamespace(complete=reverified, claims=claims, verifier=VerificationResult(complete=reverified),
            missing=[], errors=[], audit=None)

    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[b])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=QueryPlan(query=req.question))),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(return_value=(SimpleNamespace(status='supported'), [claim], [], False))) as propose,
          patch('app.modules.rag.prose_fallback.verify_bound_answer', AsyncMock(side_effect=verify)) as audit):
        response = await answer_from_prose(None, req, snap, EvidencePolicy(), 'METRIC_UNVERIFIED')
    assert propose.await_count == 1 and audit.await_count == 2
    assert (response is not None) is reverified


@pytest.mark.parametrize('label', ['ZR-0042', 'ZR-0402'])
def test_exact_row_identity_survives_a_positional_heading_about_a_different_group(label):
    from app.modules.rag.evidence_context import compact_claim_context, model_context
    from app.modules.rag.evidence_passages import passage_catalog, passage_payload

    b = block('row', f'| {label} | Thiết bị nhóm Alpha | Không đổi số người học. |', kind='table', parent='t')
    b.header_context = 'Mục về nhóm Beta\n| Mã | Đối tượng | Giới hạn |\n| --- | --- | --- |'
    b.section = 'Phụ lục / Mục về nhóm Beta'
    claim = bound(b)
    proof = claim['references'][0]['table_row']
    assert proof['cells'][0] == label and proof['cells'][1] == 'Thiết bị nhóm Alpha'
    assert proof['headers'] == ['Mã', 'Đối tượng', 'Giới hạn'] and proof['section_role'] == 'document_position'
    assert model_context([b])['evidence'][0]['table_row'] == proof
    assert passage_payload([b], passage_catalog([b]))[0]['table_row'] == proof
    refs = compact_claim_context({}, [claim])['reference_catalog']
    assert refs['ref0']['table_row'] == proof and refs['ref0']['document_position']['section'] == b.section
    assert 'section' not in refs['ref0'] and refs['ref0']['document_position']['role'] == 'location_only'
    assert claim['references'][0]['section'] == b.section  # Raw provenance is preserved server-side.
    assert b.text == claim['references'][0]['quote']


@pytest.mark.parametrize('kind,header,body', [
    ('paragraph', '| Mã | Giá trị |\n| --- | --- |', '| ZR-0042 | 0 |'),
    ('table', '', '| ZR-0042 | 0 |'),
    ('table', '| Mã | Giá trị |\n| --- | --- |', '| ZR-0042 | 0 | thừa |'),
    ('table', '| Mã | Giá trị |\n| --- | --- |', '| ZR-0042 | 0 |\n| ZR-0402 | 7 |'),
])
def test_table_identity_is_not_fabricated_for_missing_or_inconsistent_coordinates(kind, header, body):
    from app.modules.rag.source_row_context import table_row_context

    b = block('row', body, kind=kind)
    b.header_context = header
    assert not table_row_context(b)


def test_explicit_note_identifier_gets_an_anchor_without_partial_code_matching():
    from app.modules.rag.source_locators import addressed_prose

    generic = block('generic', 'Mã ZX-0402 xuất hiện ở bảng này.')
    note = block('note', 'Ghi chú NOTE-ZX-0042: chỉ hồ sơ đã khóa, không áp ZX-0402.', 100)
    row = block('row', '| ZX-0402 | 12 |', 200, 'table')
    assert [b.id for b in addressed_prose([generic, note, row], 'Ghi chú NOTE-ZX-0042 áp dụng cho ZX-0402 không?')] == ['note']
    assert not addressed_prose([note], 'Ghi chú NOTE-ZX-042 có ý nghĩa gì?')


@pytest.mark.parametrize('foreign,unknown_id,complete', [(False, False, True), (True, False, False), (False, True, False)])
def test_verbatim_prose_qualifier_requires_same_source_span_and_no_foreign_public_id(foreign, unknown_id, complete):
    from app.modules.rag.evidence_audit import (
        AtomicCheck,
        RequiredQualifier,
        SemanticAudit,
        audit_coverage,
    )

    b = block('p', 'Ngưỡng áp dụng trong kỳ; không phải kết quả đo.')
    claim = bound(b)
    if foreign:
        claim['references'][0]['source_revision_id'] = 'other'
    audit = SemanticAudit(atomic_checks=[AtomicCheck(claim_id='claim', claim_quote=b.text, supporting_quote=b.text, entailed=True)],
        required_qualifiers=[RequiredQualifier(requirement='Giữ phạm vi ngưỡng',
            reference=QuoteReference(block_id=b.id, quote='không phải kết quả đo.'), retained_by=['foreign'] if unknown_id else [])],
        complete=True, missing_constraints=[])
    _accepted, _errors, missing, final = audit_coverage(audit, [claim], [b], [])
    assert final is complete
    if not complete:
        assert missing


@pytest.mark.asyncio
@pytest.mark.parametrize('reverified', [True, False])
async def test_missing_scoped_qualifier_is_restored_then_independently_rechecked(reverified):
    from app.modules.rag.prose_fallback import answer_from_prose

    b = block('rule', 'Chỉ hồ sơ của nhóm Delta trong kỳ này. Cần quyết định có chữ ký.')
    claim = bound(b, 'Cần quyết định có chữ ký.')
    req = AskRequest(question='Hồ sơ cần điều kiện nào?', collection_id='c', reranker_policy={'enabled': False})
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    initial = SimpleNamespace(complete=False, claims=[claim], verifier=VerificationResult(complete=True),
        missing=['Thiếu phạm vi đối tượng.'], errors=[], audit=SimpleNamespace(complete=True), source_condition_gaps={},
        source_qualifier_gaps=[QuoteReference(block_id=b.id, quote='Chỉ hồ sơ của nhóm Delta trong kỳ này.')])

    async def verify(db, req, payload, claims, blocks, plan, rules):
        if 'coverage_repair' not in payload:
            return initial
        assert any(c['text'] == 'Chỉ hồ sơ của nhóm Delta trong kỳ này.' for c in claims)
        return SimpleNamespace(complete=reverified, claims=claims, verifier=VerificationResult(complete=reverified),
            missing=[], errors=[], audit=None)

    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[b])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=QueryPlan(query=req.question))),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(return_value=(SimpleNamespace(status='supported'), [claim], [], False))) as propose,
          patch('app.modules.rag.prose_fallback.verify_bound_answer', AsyncMock(side_effect=verify)) as audit):
        response = await answer_from_prose(None, req, snap, EvidencePolicy(), 'METRIC_UNVERIFIED')
    assert propose.await_count == 1 and audit.await_count == 2
    assert (response is not None) is reverified


@pytest.mark.parametrize('role', ['data_year', 'document_year', 'event_year'])
def test_verbatim_text_cannot_establish_a_different_requested_year(role):
    from app.modules.rag.evidence_audit import (
        AtomicCheck,
        RequiredQualifier,
        SemanticAudit,
        audit_coverage,
    )

    b = block('p', 'Năm 2024, tổng số là 17.')
    claim = bound(b)
    audit = SemanticAudit(atomic_checks=[AtomicCheck(claim_id='claim', claim_quote=b.text,
        supporting_quote=b.text, entailed=True)], required_qualifiers=[RequiredQualifier(
        requirement='Đúng năm được hỏi', role=role, reference=QuoteReference(block_id=b.id, quote=b.text),
        retained_by=[])], complete=True, missing_constraints=[])
    _accepted, _errors, missing, complete = audit_coverage(audit, [claim], [b], [2028])
    assert not complete and missing == ['Đúng năm được hỏi']


@pytest.mark.parametrize('role,text,years,complete', [
    ('data_year', 'Kế hoạch năm 2030 chỉ dành cho hồ sơ thiết bị.', [], True),
    ('data_year', 'Kế hoạch năm 2030 chỉ dành cho hồ sơ thiết bị.', [2030], True),
    ('data_year', 'Kế hoạch năm 2030 chỉ dành cho hồ sơ thiết bị.', [2031], False),
    ('data_year', 'Ngày ban hành: 02/04/2030.', [2030], False),
    ('document_year', 'Ngày ban hành: 02/04/2030.', [], True),
    ('event_year', 'Sự kiện tổ chức ngày 02/04/2030.', [], True),
    ('event_year', 'Sự kiện tổ chức ngày 02/04/2030.', [2031], False),
])
def test_literal_own_claim_keeps_year_role_without_borrowing_another_claim(role, text, years, complete):
    from app.modules.rag.evidence_audit import (
        AtomicCheck,
        RequiredQualifier,
        SemanticAudit,
        audit_coverage,
    )

    b = block('year', text)
    claim = bound(b)
    unrelated = bound(block('other', 'Một điều kiện khác không ghi năm.', 200))
    unrelated['id'] = 'other'
    claims = [claim, unrelated]
    audit = SemanticAudit(atomic_checks=[AtomicCheck(claim_id=c['id'], claim_quote=c['text'],
        supporting_quote=c['text'], entailed=True) for c in claims],
        required_qualifiers=[RequiredQualifier(requirement='Giữ đúng phạm vi năm', role=role,
            reference=QuoteReference(block_id=b.id, quote=text), retained_by=[])],
        complete=True, missing_constraints=[])
    assert audit_coverage(audit, claims, [b, block('other', unrelated['text'], 200)], years)[3] is complete


def test_literal_year_does_not_override_conflicting_verified_temporal_scope():
    from app.modules.rag.evidence_audit import (
        AtomicCheck,
        RequiredQualifier,
        SemanticAudit,
        audit_coverage,
    )

    b = block('year', 'Kế hoạch năm 2030 chỉ dành cho hồ sơ thiết bị.')
    claim = bound(b)
    claim['references'][0]['temporal_scope'] = {'status': 'verified', 'role': 'data', 'data_years': [2029]}
    audit = SemanticAudit(atomic_checks=[AtomicCheck(claim_id='claim', claim_quote=b.text,
        supporting_quote=b.text, entailed=True)], required_qualifiers=[RequiredQualifier(
        requirement='Đúng năm áp dụng', role='data_year', reference=QuoteReference(block_id=b.id, quote=b.text),
        retained_by=[])], complete=True, missing_constraints=[])
    assert not audit_coverage(audit, [claim], [b], [2030])[3]
