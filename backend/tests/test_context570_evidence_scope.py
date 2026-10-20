"""Evidence scope regressions with independent source fixtures, never benchmark answer keys."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan, QuoteReference
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def block(key, text, start=0, kind='paragraph', parent=None, revision='r', refs=()):
    return EvidenceBlock(id=key, unit_id=key, text=text, start=start, end=start + len(text),
        binding_id='b', index_revision_id='i', source_revision_id=revision, canonical_hash='h', title='Fixture',
        parent_id=parent, section='Nguồn kiểm thử', fact_context={'source_kind': kind, 'context_unit_ids': list(refs)})


def table_blocks():
    return [block('caption', 'Bảng 17. Quy tắc lưu định danh', 10),
            block('t:header', '| Trường | Kiểu | Ví dụ | Quy tắc |\n| --- | --- | --- | --- |', 60, 'table', 't'),
            block('row', '| program_id | Chuỗi | ZX-0048 | Giữ nguyên dấu nối. |', 150, 'table', 't')]


@pytest.mark.parametrize('query,expected', [
    ('Theo Bảng 17, ZX-0048 phải được lưu thế nào?', True),
    ('Theo Bảng 71, ZX-0048 phải được lưu thế nào?', False),
    ('Không được dùng ZX-048 thay cho ZX-0048?', True),
    ('Không được dùng ZX0048?', False),
])
def test_literal_value_column_can_find_rule_row_without_rewriting_code(query, expected):
    from app.modules.rag.source_labels import supplemental_context

    selected = supplemental_context(table_blocks(), query, allow_tables=True)
    assert ('row' in {b.id for b in selected}) is expected


def test_caption_does_not_cross_source_or_intervening_body():
    from app.modules.rag.source_locators import table_captions

    blocks = table_blocks()
    assert [b.id for b in table_captions(blocks, 't')] == ['caption']
    assert not table_captions([blocks[0].model_copy(update={'source_revision_id': 'foreign'}), *blocks[1:]], 't')
    assert not table_captions([*blocks, block('unrelated', 'Một đoạn khác.', 45)], 't')


def test_unknown_cells_still_cannot_be_recovered_as_table_facts():
    from app.modules.rag.source_labels import supplemental_context

    blocks = table_blocks()
    blocks[-1].fact_context['unresolved_cell_columns'] = ['c03']
    assert not supplemental_context(blocks, 'Bảng 17 có ZX-0048?', allow_tables=True)


def test_a_numbered_rule_does_not_make_a_following_matrix_atomic():
    from app.modules.rag.evidence_dependencies import dependency_groups

    rule = block('rule', '1. Hồ sơ cần xác nhận trước khi gia hạn.', 0, 'list')
    blocks = [rule, *table_blocks()]
    group = dependency_groups(blocks).get('rule', [])
    assert not any(b.fact_context.get('source_kind') == 'table' for b in group)


def test_pack_keeps_later_direct_proof_after_numbered_rule_and_table():
    from app.modules.rag.evidence_blocks import pack_context

    rule = block('rule', '1. Quy định chung về hồ sơ.', 0, 'list')
    tables = table_blocks()
    rows = [block(f'row{n}', f'| M{n} | Nội dung |', 220 + n * 30, 'table', 't') for n in range(9)]
    direct = block('direct', 'Ngoại lệ chỉ áp dụng hồ sơ thiết bị, cần quyết định và không đổi số lượng.', 650)
    selected = pack_context([rule, *tables, *rows, direct], [rule, direct], [], 5, 36000,
                            atomic_lists=False, allow_first_whole_group=True)
    assert 'direct' in {b.id for b in selected}


def test_explicit_section_reference_keeps_formula_legend_in_same_revision():
    from app.modules.rag.source_locators import referenced_sections

    heading = block('section', '#### 22.4. Công thức', 0, 'heading')
    legend = block('legend', 'Thiếu biến đầu vào thì không tính.', 40, parent='section')
    foreign = block('foreign', 'Nội dung revision khác.', 90, parent='section', revision='other')
    assert [b.id for b in referenced_sections([heading, legend, foreign], 'Theo mục 22.4 thì sao?')] == ['legend']


@pytest.mark.parametrize('unit', ['lớp', 'nhóm'])
def test_unit_refusal_preserves_the_source_reason(unit):
    from app.modules.rag.temporal_answer import decide_table_answer

    md = '| Mã | Tên | Chỉ tiêu 2032 (SV) |\n| --- | --- | --- |\n| LT-0042 | Chương trình Delta | 57 |'
    facts = build_source_artifact(md, 1, {})['facts']
    frozen = deepcopy(facts)
    result = decide_table_answer(f'Chỉ tiêu tính theo {unit} mã LT-0042 năm 2032?', facts)
    assert result['reason'] == 'SOURCE_UNIT_MISMATCH'
    assert 'SV' in result['answer'] and unit in result['answer'] and not result['claim_bindings']
    assert facts == frozen


def test_forecast_cannot_be_answered_as_achieved_and_has_specific_reason():
    from app.modules.rag.temporal_answer import decide_table_answer

    md = '| Mã | Tên | 2033 / Ước tính (SV) |\n| --- | --- | --- |\n| LT-0042 | Chương trình Delta | 61 |'
    result = decide_table_answer('Số SV đã nghiệm thu mã LT-0042 năm 2033?', build_source_artifact(md, 1, {})['facts'])
    assert result['reason'] == 'SOURCE_METRIC_ROLE_MISMATCH'
    assert not result['claim_bindings'] and 'ước tính' in result['answer'] and 'nghiệm thu' in result['answer']


def test_another_entitys_forecast_is_not_a_reason_for_the_requested_entity():
    from app.modules.rag.temporal_answer import decide_table_answer

    md = '| Mã | Tên | 2033 / Ước tính (SV) |\n| --- | --- | --- |\n| LT-0042 | Chương trình Delta | 61 |'
    result = decide_table_answer('Số SV đã nghiệm thu mã LT-0098 năm 2033?', build_source_artifact(md, 1, {})['facts'])
    assert result['reason'] != 'SOURCE_METRIC_ROLE_MISMATCH' and not result['claim_bindings']


@pytest.mark.parametrize('dates,descending,expected', [
    (['18/03/2031', '02/04/2031', '01/01/2031'], False, True),
    (['01/01/2031', '18/03/2031', '02/04/2031'], False, False),
    (['02/04/2031', '18/03/2031'], True, False),
    (['18/03/2031', '02/04/2031'], True, True),
])
def test_explicit_date_order_is_checked_as_a_relationship(dates, descending, expected):
    from app.modules.rag.source_scope_audit import chronological_order_error

    answer = 'Các mốc ' + ('giảm dần' if descending else 'tăng dần') + ':\n' + '\n'.join('- **' + d + '**: Mốc.' for d in dates)
    assert chronological_order_error(answer) is expected


def test_unordered_date_comparison_does_not_invent_an_order_requirement():
    from app.modules.rag.source_scope_audit import chronological_order_error

    assert not chronological_order_error('- Ban hành: 02/04/2031.\n- Năm học: 01/01/2031.')


RULE = ('1. Hồ sơ chỉ được thay chữ ký khi cơ sở tạm đóng và có xác nhận cùng kỳ.\n'
        '2. Được dùng biên bản trực tuyến tối đa 24 ngày.\n'
        '3. Không áp dụng cho nhóm khác và không miễn kiểm tra an toàn.')


@pytest.mark.asyncio
@pytest.mark.parametrize('complete,atomic_positive', [(False, True), (True, True), (True, False)])
async def test_whole_answer_booleans_cannot_replace_source_condition_retention(complete, atomic_positive):
    from app.modules.rag.response_audit import audit_visible_answer

    answer = RULE if complete else 'Được dùng biên bản trực tuyến tối đa 24 ngày.'
    candidate = FusionCandidate('chunk', 'b', RULE, 1, binding_id='b', index_revision_id='i')
    request = AskRequest(question='Điều kiện thay chữ ký và thời hạn?', collection_id='c')
    snapshot = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})

    async def reader(db, req, contract, instruction, payload, **kwargs):
        checks = [{'answer_span_id': key, 'evidence_id': 'e0', 'entailed': atomic_positive, 'relevant': True}
                  for key in payload['answer_spans']]
        data = {'answers_original_question': True, 'essential_conditions_retained': True, 'conflict': False,
                'assertions': checks, 'missing_constraints': []}
        if 'source_conditions' in contract.model_fields:
            data['source_conditions'] = [{'clause_id': key, 'required': True, 'retained_by': list(payload['answer_spans'])}
                                         for key in payload['source_conditions']]
        return contract.model_validate(data)

    with patch('app.modules.rag.response_audit.structured_call', AsyncMock(side_effect=reader)):
        result = await audit_visible_answer(None, request, snapshot, answer, [candidate])
    assert result['accepted'] is (complete and atomic_positive), (
        result['atomic_spans_valid'], result['missing_source_condition_ids'], result['chronological_order_error'],
        result['quote_mismatch_count'], result['answer_span_mismatch_count'])
    if not complete:
        assert result['missing_source_condition_ids']


def test_source_condition_contract_rejects_missing_duplicate_and_invented_proof_ids():
    from app.modules.rag.response_audit import indexed_audit_contract
    from app.modules.rag.source_scope_audit import scope_audit_contract

    base = indexed_audit_contract({'a0': 'Được dùng.'}, {'e0': RULE})
    contract = scope_audit_contract(base, {'e0.c1': 'Điều kiện bắt buộc.'}, ('a0',))
    valid = {'answers_original_question': True, 'essential_conditions_retained': True, 'conflict': False,
             'assertions': [{'answer_span_id': 'a0', 'evidence_id': 'e0', 'entailed': True, 'relevant': True}],
             'source_conditions': [{'clause_id': 'e0.c1', 'required': True, 'retained_by': ['a0']}]}
    assert contract.model_validate(valid)
    for checks in ([], valid['source_conditions'] * 2, [{'clause_id': 'foreign', 'required': False, 'retained_by': []}]):
        with pytest.raises(ValidationError):
            contract.model_validate({**valid, 'source_conditions': checks})


@pytest.mark.asyncio
async def test_source_quote_answer_still_fails_if_a_required_condition_is_omitted():
    from app.modules.rag.evidence_indexed_audit import audit_contract, resolve_audit
    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.evidence_validation import bind_quote

    b = block('rule', RULE, 0, 'list')
    quote = 'Được dùng biên bản trực tuyến tối đa 24 ngày.'
    claim = {'id': 'c1', 'text': quote, 'references': [bind_quote(QuoteReference(block_id=b.id, quote=quote), {b.id: b})]}
    catalog = passage_catalog([b])
    contract = audit_contract([claim], catalog)
    data = {'claims': [{'claim_id': 'c1', 'all_assertions_supported': True}], 'complete': True,
            'essential_conditions': [], 'missing_constraints': []}
    if 'source_conditions' in contract.model_fields:
        from app.modules.rag.source_scope_audit import source_clauses

        data['source_conditions'] = [{'clause_id': key, 'required': True, 'retained_by': ['c1']}
                                     for key in source_clauses({'e1': RULE})]
    audit = resolve_audit(contract.model_validate(data), [claim], catalog)
    assert not audit.complete and audit.missing_constraints


@pytest.mark.asyncio
async def test_table_schema_selection_receives_canonical_caption_and_records_the_gate():
    from app.modules.rag.source_identity_enumeration import enumerate_source_identities

    blocks = table_blocks()
    artifact = {'tables': [{'id': 't', 'header_paths': [['Mã CT'], ['Tên chương trình']],
                            'rows': [['00048', 'Chương trình Delta']], 'row_unit_ids': ['row']}]}
    source = SimpleNamespace(id='r')
    db = AsyncMock()
    db.scalars.return_value = SimpleNamespace(all=lambda: [source])
    req = AskRequest(question='Liệt kê tất cả mã và tên ở Bảng 17.', collection_id='c')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})

    async def reader(db, req, contract, instruction, payload, **kwargs):
        assert payload['tables'][0]['captions'][0]['text'].startswith('Bảng 17.')
        return contract.model_validate({'status': 'not_applicable', 'all_rows': False, 'identity_only': False})

    with (patch('app.modules.rag.source_identity_enumeration.load_published_blocks', AsyncMock(return_value=blocks)),
          patch('app.modules.rag.source_identity_enumeration.get_source_artifact', return_value=artifact),
          patch('app.modules.rag.source_identity_enumeration.structured_call', AsyncMock(side_effect=reader))):
        assert await enumerate_source_identities(db, req, snap) is None
    assert req._retrieval_diagnostics['identity_selection']['stage'] == 'first_selection'


@pytest.mark.asyncio
async def test_named_rule_recovery_keeps_row_and_its_scope_after_a_missing_selector():
    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.prose_fallback import answer_from_prose

    blocks = table_blocks()
    body = block('intro', 'Không được tự thay đổi định danh.', 1)
    req = AskRequest(question='Bảng 17 yêu cầu gì với ZX-0048?', collection_id='c')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    seen = {}

    async def propose(db, req, payload, selected):
        seen['ids'] = {b.id for b in selected}
        return SimpleNamespace(status='missing'), [], [], False

    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[body, *blocks])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=QueryPlan(query=req.question, coverage='focused'))),
          patch('app.modules.rag.prose_fallback.bounded_rerank', AsyncMock(return_value=[])),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(side_effect=propose))):
        assert await answer_from_prose(None, req, snap, EvidencePolicy(), 'ROW_SELECTION_MISSING') is None
    assert 'row' in seen['ids']
    assert req._retrieval_diagnostics['prose_fallback']['table_recovery']
