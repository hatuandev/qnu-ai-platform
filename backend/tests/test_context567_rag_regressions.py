"""Source-grounded regressions, independent of the private benchmark questions."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import test_context565_entity_metric as source_fixtures

from app.modules.knowledge.entity_codes import code_candidates
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.temporal_answer import decide_table_answer

legacy_scope = source_fixtures.legacy_scope

MARKDOWN = """| Mã chương trình | Tên chương trình | 2030 / Chỉ tiêu (SV) | 2030 / Ghi nhận / Số lượng (SV) |
| --- | --- | --- | --- |
| UX-0405 | Chương trình thử Delta | 37 | 29 |
"""


@pytest.mark.parametrize('question', [
    'Bảng ghi nhận bao nhiêu SV của UX-0405 năm 2030?',
    'Số SV ghi nhận năm 2030 của mã UX-0405?',
    'Mã UX-0405 đã ghi nhận được mấy SV năm 2030?',
])
def test_recorded_quantity_paraphrases_preserve_metric(question):
    facts = build_source_artifact(MARKDOWN, 1, {})['facts']
    decision = decide_table_answer(question, facts)
    assert decision and decision['status'] == 'supported'
    assert [claim['value'] for claim in decision['claim_bindings']] == ['29']


def test_multiple_requested_metrics_are_complete():
    decision = decide_table_answer('Cho biết chỉ tiêu SV và số SV ghi nhận mã UX-0405 năm 2030.',
                                  build_source_artifact(MARKDOWN, 1, {})['facts'])
    assert decision and decision['status'] == 'supported'
    assert {claim['value'] for claim in decision['claim_bindings']} == {'37', '29'}


@pytest.mark.parametrize('unit', ['lớp', 'nhóm'])
def test_natural_requested_unit_is_not_replaced_by_source_unit(unit):
    decision = decide_table_answer(f'Chỉ tiêu tính theo {unit} của mã UX-0405 năm 2030?',
                                  build_source_artifact(MARKDOWN, 1, {})['facts'])
    assert decision and decision['status'] == 'missing' and not decision['claim_bindings']


def test_scalar_zero_is_not_an_unlabeled_identity():
    assert code_candidates('Mã UX-0405 có giá trị bằng 0 không?') == ['UX-0405']
    assert code_candidates('Giá trị của mã 0?') == ['0']


@pytest.mark.asyncio
async def test_source_name_selects_verified_coordinates_without_static_code(legacy_scope):
    from app.modules.rag.source_fact_resolution import FactScope

    original, record, state = legacy_scope
    name = next(iter(original.rows.values()))['name']
    scope = FactScope([], blocks=original.blocks)
    scope.question = f'Chỉ tiêu của chương trình {name} năm 2026?'
    scope.add_source(state.approved, state.index.id, state.source.id)
    assert scope.rows and scope.bind(record)['entity_code'] == '0012345'


@pytest.mark.asyncio
@pytest.mark.parametrize('ids,expected', [(['e0', 'e0'], True), (['e0', 'alien'], False)])
async def test_reusing_one_proof_is_valid_but_foreign_ids_stay_rejected(ids, expected):
    from app.modules.rag.response_audit import VisibleAnswerAudit, audit_visible_answer

    # Long evidence intentionally exercises the retained exact-subquote wire.
    text = 'Chương trình có hướng dẫn. Hồ sơ cần xác nhận. ' + 'Ngữ cảnh bổ sung. ' * 300
    answer = 'Chương trình có hướng dẫn.\nHồ sơ cần xác nhận.'
    candidate = FusionCandidate('chunk', 'doc', text, 1, binding_id='b', index_revision_id='i')
    req = AskRequest(question='Hướng dẫn và hồ sơ?', collection_id='c')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})

    async def audit(_db, _req, _contract, _instruction, payload, **kwargs):
        assertions = [SimpleNamespace(answer_span_id=k, evidence_id='e0',
            evidence_quote=value, entailed=True, relevant=True) for k, value in payload['answer_spans'].items()]
        # Use the same actual contract as the runtime, preserving all span checks.
        return _contract.model_validate({
            **VisibleAnswerAudit(all_assertions_supported=True, answers_original_question=True,
                essential_conditions_retained=True, conflict=False, evidence_ids=ids).model_dump(),
            'assertions': [vars(a) for a in assertions]})

    with patch('app.modules.rag.response_audit.structured_call', AsyncMock(side_effect=audit)):
        result = await audit_visible_answer(AsyncMock(), req, snap, answer, [candidate])
    assert result['accepted'] is expected


def test_source_query_does_not_invent_a_major_code_for_a_name():
    facts = build_source_artifact(MARKDOWN.replace('Chương trình thử Delta', 'Kỹ thuật phần mềm'), 1, {})['facts']
    decision = decide_table_answer('Chỉ tiêu chương trình Kỹ thuật phần mềm năm 2030?', facts)
    assert decision and decision['status'] == 'supported'
    assert [claim['value'] for claim in decision['claim_bindings']] == ['37']


@pytest.mark.parametrize('current', ['Thế năm 2031?', 'Còn năm 2031 thì sao?', 'Năm 2031?'])
def test_literal_year_correction_preserves_full_user_scope(current):
    from app.modules.rag.conversation_resolution import literal_year_change

    previous = ['Chỉ tiêu (SV) mã UX-0405 năm 2030 trong Bảng 9 tại trường Delta?']
    req = AskRequest(question=current, collection_id='c')
    effective, resolution = literal_year_change(req, previous)
    assert effective.question == previous[0].replace('2030', '2031')
    assert resolution['antecedent_question'] == previous[0]


@pytest.mark.parametrize('current,previous', [
    ('Thế năm 2031 cho nhóm khác?', ['Chỉ tiêu mã UX-0405 năm 2030?']),
    ('Thế năm 2031?', ['Chỉ tiêu mã UX-0405 và UX-0045 năm 2030?']),
    ('Thế năm 2031?', ['Chỉ tiêu mã UX-0405 năm 2029 và 2030?']),
    ('Thế năm 2031?', []),
])
def test_literal_year_resolver_declines_ambiguous_or_new_predicates(current, previous):
    from app.modules.rag.conversation_resolution import literal_year_change

    assert literal_year_change(AskRequest(question=current, collection_id='c'), previous) is None


def test_quote_address_repair_never_changes_scope_or_invents_a_value():
    from app.modules.rag.conversation_resolution import (
        FollowupResolution,
        normalize_user_references,
    )
    from app.modules.rag.intent_contracts import ContextReferent, validate_referents

    old = ['Chỉ tiêu mã UX-0405 năm 2030?']
    current = 'Đổi sang mã UX-0045.'
    resolution = FollowupResolution(mode='followup', antecedent_id=0,
        question='Chỉ tiêu mã UX-0045 năm 2030?', referents=[ContextReferent(
            field='program_code', value='UX-0045', source_turn=0, quote='mã UX-0045')])
    fixed = normalize_user_references(resolution, current, old)
    assert fixed.referents[0].source_turn == -1
    assert validate_referents(fixed.referents, current, old, fixed.question)
    fabricated = resolution.model_copy(update={'referents': [ContextReferent(
        field='program_code', value='UX-9999', source_turn=0, quote='mã UX-9999')]})
    fixed = normalize_user_references(fabricated, current, old)
    assert not validate_referents(fixed.referents, current, old, fixed.question)


def test_measure_label_precedes_unrelated_condition_in_literal_row_query():
    from app.modules.rag.source_labels import row_identity

    table = {'header_paths': [['Chỉ tiêu định lượng'], ['Ngưỡng'], ['Điều kiện']],
             'rows': [['Giờ thực hành cá nhân', '> 21', 'Người học đã có xác nhận đầy đủ.']]}
    result = row_identity(table['rows'][0], table, 'Giờ thực hành cá nhân có ngưỡng nào?')
    assert result[:3] == (0, 3, 'Giờ thực hành cá nhân')


@pytest.mark.parametrize('tail,valid', [
    (['Tổng dữ liệu (2 mục)', 'Tổng dữ liệu (2 mục)'], True),
    (['', ''], False),
    (['UX-0405', 'Trùng định danh'], False),
])
def test_exhaustive_identity_list_preserves_zero_and_never_drops_unresolved_rows(tail, valid):
    from app.modules.rag.source_identity_enumeration import identity_entries

    table = {'rows': [['00043', 'Mục thử Alpha'], ['UX-0405', 'Mục thử Beta'], tail],
             'row_unit_ids': ['a', 'b', 'c']}
    result = identity_entries(table, 0, 1)
    if valid:
        assert result == [('a', '00043', 'Mục thử Alpha'), ('b', 'UX-0405', 'Mục thử Beta')]
    else:
        assert result is None


@pytest.mark.parametrize('summary,entailed', [(False, True), (True, False)])
def test_contradictory_audit_summary_requires_repair_not_a_positive_override(summary, entailed):
    from pydantic import ValidationError

    from app.modules.rag.response_audit import span_audit_contract

    contract = span_audit_contract({'a0': 'Hồ sơ cần xác nhận.'}, {'e0': 'Hồ sơ cần xác nhận.'})
    with pytest.raises(ValidationError):
        contract.model_validate({'all_assertions_supported': summary, 'answers_original_question': True,
            'essential_conditions_retained': True, 'conflict': False, 'evidence_ids': ['e0'],
            'assertions': [{'answer_span_id': 'a0', 'evidence_id': 'e0', 'evidence_quote': 'Hồ sơ cần xác nhận.',
                            'entailed': entailed, 'relevant': True}]})


@pytest.mark.asyncio
@pytest.mark.parametrize('foreign,altered', [(False, False), (True, False), (False, True)])
async def test_search_prefix_is_not_a_canonical_quote_and_foreign_or_altered_body_is_rejected(foreign, altered):
    from app.modules.rag.canonical_candidates import bind_candidates, canonical_citation
    from app.modules.rag.evidence_schemas import EvidenceBlock

    body = 'Chú thích này chỉ thuộc bảng ngay trước.'
    source = EvidenceBlock(id='r:19:58', binding_id='b', index_revision_id='old' if foreign else 'i',
        source_revision_id='r', title='Source', text=body, start=19, end=19+len(body), canonical_hash='hash', unit_id='unit')
    candidate = FusionCandidate('chunk', 'document', 'Tiêu đề trang\n\n'+('Nội dung đã đổi' if altered else body), 1,
        binding_id='b', index_revision_id='i', metadata={'source_unit_id': 'unit', 'source_revision_id': 'r'})
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    with patch('app.modules.rag.canonical_candidates.load_published_blocks', AsyncMock(return_value=[source])):
        bound = await bind_candidates(AsyncMock(), snap, [candidate])
    if foreign or altered:
        assert not bound
    else:
        assert bound[0][0].content == body
        citation = canonical_citation(bound[0][1], candidate.document_id)
        assert citation.quote == body and citation.span_start == 19 and citation.canonical_hash == 'hash'
        assert citation.source_id == 'document'


def test_schema_identifier_is_not_a_spaced_natural_language_entity():
    from app.modules.rag.source_rows import _matches_row

    header = '| Trường | Kiểu lưu | Giá trị ví dụ |\n| --- | --- | --- |'
    row = '| trang_thai | Chuỗi ký tự | / |'
    assert not _matches_row(header, row, 'Trạng thái của hồ sơ thiếu dữ liệu là gì?')
    assert _matches_row(header, row, 'Trường trang_thai có kiểu lưu gì?')


def test_source_locators_and_given_scenario_inputs_are_not_answer_fact_demands():
    from app.modules.rag.prose_selection import answer_facets

    question = 'Theo Mục 3.2, Điều 4, Z=43, X=67, đủ 95% hồ sơ nhưng thiếu Y, năm 2030 thì kết luận thế nào?'
    assert answer_facets(['Mục 3.2', 'Điều 4', 'Z=43', 'X=67', '95% hồ sơ', 'thiếu Y', '2030'], question) == ['thiếu Y', '2030']
    assert answer_facets(['95% hồ sơ'], 'Có quy định 95% hồ sơ không?') == ['95% hồ sơ']


def test_unknown_table_cell_cannot_be_promoted_through_semantic_supplement():
    from app.modules.rag.evidence_schemas import EvidenceBlock
    from app.modules.rag.source_labels import supplemental_context

    block = EvidenceBlock(id='row', binding_id='b', index_revision_id='i', source_revision_id='r', title='Source',
        text='| UX-0405 | ? |', start=0, end=15, unit_id='row', parent_id='table',
        fact_context={'source_kind': 'table', 'unresolved_cell_columns': ['c02']})
    assert not supplemental_context([block], 'Giá trị UX-0405 được hiểu thế nào?', allow_tables=True)


@pytest.mark.asyncio
@pytest.mark.parametrize('final_supported', [True, False])
async def test_final_retained_claim_audit_is_authoritative_and_never_promotes_rejected_claims(final_supported):
    from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan, QuoteReference
    from app.modules.rag.evidence_validation import bind_quote
    from app.modules.rag.evidence_verification import verify_bound_answer

    text = 'Hồ sơ cần có xác nhận.'
    block = EvidenceBlock(id='body', binding_id='b', index_revision_id='i', source_revision_id='r', title='Source',
        text=text, start=0, end=len(text), canonical_hash='hash')
    claim = {'id': 'claim', 'text': text, 'references': [bind_quote(QuoteReference(block_id='body', quote=text), {'body': block})]}
    plan = QueryPlan(query='Hồ sơ có cần xác nhận không?', requested_topics=['xác nhận'])
    req = AskRequest(question=plan.query, collection_id='c')

    async def model(_db, _req, contract, instruction, payload, **kwargs):
        if 'verdicts' in contract.model_fields:
            return contract.model_validate({'complete': False, 'topic_coverage': {'xác nhận': True},
                'verdicts': [{'claim_id': 'claim', 'entailed': True, 'relevant': True, 'scope_compatible': True,
                              'reason': 'Own source quote supports the retained assertion.'}]})
        return contract.model_validate({'claims': [{'claim_id': 'claim', 'all_assertions_supported': final_supported}],
            'complete': final_supported, 'essential_conditions': [], 'missing_constraints': []})

    with patch('app.modules.rag.evidence_verification.structured_call', AsyncMock(side_effect=model)):
        result = await verify_bound_answer(AsyncMock(), req, {'question': req.question}, [claim], [block], plan, [])
    assert not result.verifier.complete
    assert result.complete is final_supported
    assert bool(result.claims) is final_supported


@pytest.mark.asyncio
@pytest.mark.parametrize(('entailed', 'relevant', 'accepted'), [(True, True, True), (False, True, False), (True, False, False)])
async def test_server_owned_source_proof_keeps_every_atomic_negative(entailed, relevant, accepted):
    from app.modules.rag.fusion import FusionCandidate
    from app.modules.rag.response_audit import audit_visible_answer
    from app.modules.rag.schemas import RetrievalSnapshot

    text = 'Hồ sơ chỉ được dùng khi có xác nhận.'
    candidate = FusionCandidate('chunk', 'b', text, 1, binding_id='b', index_revision_id='i')
    req = AskRequest(question='Hồ sơ được dùng khi nào?', collection_id='c')
    snapshot = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})

    async def reader(db, request, contract, instruction, payload, **kwargs):
        assert 'Do not emit evidence_quote' in instruction
        return contract.model_validate({'answers_original_question': True, 'essential_conditions_retained': True,
            'conflict': False, 'assertions': [{'answer_span_id': 'a0', 'evidence_id': 'e0',
                'entailed': entailed, 'relevant': relevant}], 'missing_constraints': []})

    with patch('app.modules.rag.response_audit.structured_call', AsyncMock(side_effect=reader)):
        result = await audit_visible_answer(AsyncMock(), req, snapshot, text, [candidate])
    assert result['accepted'] is accepted
    assert result['proof_binding'] == 'server_owned_body'
    assert result['quote_mismatch_count'] == 0 and result['evidence_ids'] == ['e0']


def test_indexed_reader_cannot_invent_proof_drop_span_or_override_atomic_summary():
    from pydantic import ValidationError

    from app.modules.rag.response_audit import indexed_audit_contract

    contract = indexed_audit_contract({'a0': 'Hồ sơ cần xác nhận.'}, {'e0': 'Hồ sơ cần xác nhận.'})
    valid = {'answers_original_question': True, 'essential_conditions_retained': True, 'conflict': False,
             'assertions': [{'answer_span_id': 'a0', 'evidence_id': 'e0', 'entailed': False, 'relevant': True}]}
    assert not contract.model_validate(valid).all_assertions_supported
    for bad in ({**valid, 'all_assertions_supported': True}, {**valid, 'evidence_ids': ['e0']},
                {**valid, 'assertions': []}, {**valid, 'assertions': [{**valid['assertions'][0], 'evidence_id': 'invented'}]}):
        with pytest.raises(ValidationError):
            contract.model_validate(bad)


def test_ranked_full_conditions_are_not_crowded_out_by_table_summary():
    from app.modules.rag.evidence_blocks import pack_context
    from app.modules.rag.evidence_schemas import EvidenceBlock
    from app.modules.rag.prose_selection import recovery_order

    def block(unit, text, start, kind='paragraph', refs=()):
        return EvidenceBlock(id=unit, unit_id=unit, text=text, start=start, end=start+len(text), title='Source',
            binding_id='b', index_revision_id='i', source_revision_id='r', canonical_hash='h',
            fact_context={'source_kind': kind, 'context_unit_ids': list(refs)})
    rule = block('rule', 'Hồ sơ cần đủ xác nhận; không miễn kiểm tra an toàn.', 100, refs=['condition', 'exception'])
    condition = block('condition', 'Có nhật ký cùng kỳ và quyết định hợp lệ.', 200)
    exception = block('exception', 'Ngoại lệ chỉ thuộc đúng nhóm được quy định.', 300)
    row = block('row', '| UE-99 | 7 ngày |', 400, kind='table', refs=['header', 'note'])
    header = block('header', '| Mã | Hạn |', 350, kind='table')
    note = block('note', 'Bảng này là tóm tắt, giữ đầy đủ điều kiện trong quy định.', 500)
    blocks = [rule, condition, exception, header, row, note]
    old = pack_context(blocks, [row, rule], [], 3, 36000, atomic_lists=False)
    assert 'rule' not in {b.id for b in old}
    ordered = recovery_order([rule, row], [row], [])
    packed = pack_context(blocks, ordered, [], 3, 36000, atomic_lists=False)
    assert {'rule', 'condition', 'exception'} <= {b.id for b in packed}
