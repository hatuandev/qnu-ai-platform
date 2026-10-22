"""Derived facts are not canonical character spans; source branches remain explicit."""
from types import SimpleNamespace

import pytest

from app.modules.rag.evidence_schemas import QueryPlan, QuoteReference
from app.modules.rag.evidence_validation import bind_quote
from app.modules.rag.schemas import AskRequest
from tests.test_source_answer_scope_575 import block, bound


def derived():
    return block('fact', 'Nhóm Delta\nThời hạn: 9 ngày', kind='paragraph', parent='table').model_copy(
        update={'origin': 'reviewed_fact', 'fact_id': 'f', 'start': -1, 'end': -1})


def test_derived_fact_without_character_offsets_is_not_a_literal_canonical_owner():
    from app.modules.rag.evidence_audit import literal_condition_retained

    fact = derived()
    ref = bind_quote(QuoteReference(block_id=fact.id, quote=fact.text), {fact.id: fact})
    assert ref['start'] is None and ref['end'] is None
    assert not literal_condition_retained(ref, [], 'value_constraint', [])


@pytest.mark.parametrize('offsets', [(None, None), (0, 1000)])
def test_missing_or_synthetic_offsets_on_claim_reference_cannot_prove_canonical_clause(offsets):
    from app.modules.rag.evidence_audit import literal_condition_retained

    source = block('canonical', 'Chỉ áp dụng khi có xác nhận.')
    claim = bound(source)
    ref = claim['references'][0]
    claim = dict(claim, references=[dict(ref, start=offsets[0], end=offsets[1], origin='reviewed_fact', fact_id='f')])
    assert not literal_condition_retained(ref, [claim], 'value_constraint', [])


def test_audit_source_clauses_exclude_derived_fact_siblings_but_keep_canonical_rule():
    from app.modules.rag.evidence_indexed_audit import audit_payload

    row = block('row', '| ZX-04 | 9 ngày |', kind='table', parent='table')
    condition = block('rule', 'Chỉ khi có văn bản cùng kỳ.', 100, parent='table')
    payload, _ = audit_payload({'claims': [bound(row)]}, [row, derived(), condition])
    assert list(payload['source_conditions'].values()) == [condition.text]


def test_obligation_cannot_latch_synthetic_text_as_an_original_source_span():
    from app.core.exceptions import AppException
    from app.modules.rag.evidence_obligations import remember_conditions
    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.source_scope_audit import SourceConditionCheck

    fact = derived()
    req = AskRequest(collection_id='c', question='Điều kiện nào?')
    checked = SimpleNamespace(source_conditions=[SourceConditionCheck(clause_id='e1.c0', required=True)])
    with pytest.raises(AppException) as caught:
        remember_conditions(req, QueryPlan(query=req.question), checked, None,
            {'e1.c0': fact.text}, passage_catalog([fact]), [fact])
    assert caught.value.code == 'SOURCE_CONDITION_PROVENANCE_INVALID'


@pytest.mark.asyncio
async def test_source_review_uses_queried_proof_not_draft_and_cache_tracks_branch():
    import json

    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.source_dependency_review import review_dependencies

    source = block('body', 'Có đủ dữ liệu thì tính. Nếu thiếu dữ liệu thì ghi Chưa đủ điều kiện.')
    definition = block('definition', 'Định nghĩa của dữ liệu được thu thập.', 100)
    blocks = [source, definition]
    req = AskRequest(collection_id='c', question='Khi thiếu dữ liệu thì ghi trạng thái gì?')
    plan = QueryPlan(query=req.question)
    calls = []

    async def call(db, request, contract, instruction, payload, **kwargs):
        calls.append(payload)
        assert 'untrusted_draft' not in json.dumps(payload)
        assert payload['bodies'][0]['text'] in source.text
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'required': False, 'governs': []}]})

    for quote in ('Có đủ dữ liệu thì tính.', 'Nếu thiếu dữ liệu thì ghi Chưa đủ điều kiện.'):
        claim = bound(source, quote) | {'text': 'untrusted_draft'}
        await review_dependencies(None, req, plan, [claim], blocks, {'e2.c0': definition.text}, passage_catalog(blocks), call)
    assert len(calls) == 2
    assert calls[0]['bodies'][0]['text'] != calls[1]['bodies'][0]['text']


def test_date_coordination_does_not_fragment_a_literal_table_row():
    from app.modules.rag.evidence_passages import passage_catalog

    row = block('row', '| ZX-04 | Từ 01/02/2033 và kết thúc 03/04/2033. |', kind='table', parent='table')
    assert all(ref.quote == row.text for ref in passage_catalog([row]).values())


@pytest.mark.asyncio
@pytest.mark.parametrize('quote', ['Có đủ dữ liệu thì tính.', 'Thiếu dữ liệu thì giữ trạng thái chưa đủ.'])
async def test_source_dependency_target_is_the_bound_excerpt_not_its_entire_block(quote):
    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.source_dependency_review import review_dependencies

    source = block('body', 'Có đủ dữ liệu thì tính. Thiếu dữ liệu thì giữ trạng thái chưa đủ.')
    condition = block('definition', 'Định nghĩa dùng cho nhánh tính toán.', 100)
    req = AskRequest(collection_id='c', question='Trạng thái khi thiếu dữ liệu?')

    async def call(db, request, contract, instruction, payload, **kwargs):
        target = payload['bodies'][0]
        assert target['text'] == quote
        assert target['id'] == 'claim' and target['source_block_id'] == source.id
        assert payload['source_context'][source.id] == source.text
        assert 'untrusted_draft' not in str(payload)
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'required': False}]})

    await review_dependencies(None, req, QueryPlan(query=req.question),
        [bound(source, quote) | {'text': 'untrusted_draft'}], [source, condition],
        {'e2.c0': condition.text}, passage_catalog([source, condition]), call)


@pytest.mark.asyncio
async def test_distinct_source_excerpts_in_one_block_keep_separate_dependency_targets():
    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.source_dependency_review import review_dependencies

    source = block('body', 'Đủ dữ liệu thì thực hiện. Thiếu dữ liệu thì chờ bổ sung.')
    condition = block('condition', 'Điều kiện cho nhánh đang hỏi.', 100)
    req = AskRequest(collection_id='c', question='Trạng thái nào?')
    quotes = ['Đủ dữ liệu thì thực hiện.', 'Thiếu dữ liệu thì chờ bổ sung.']
    claims = [bound(source, quote) | {'id': key} for key, quote in zip(['success', 'missing'], quotes)]

    async def call(db, request, contract, instruction, payload, **kwargs):
        assert len(payload['bodies']) == 2
        assert [body['id'] for body in payload['bodies']] == ['success', 'missing']
        assert [body['text'] for body in payload['bodies']] == quotes
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'required': True,
            'governs': ['missing']}]})

    result = await review_dependencies(None, req, QueryPlan(query=req.question), claims, [source, condition],
        {'e2.c0': condition.text}, passage_catalog([source, condition]), call)
    assert result.conditions[0].governs == ['missing']


@pytest.mark.asyncio
async def test_whole_block_id_cannot_replace_a_precise_dependency_target():
    from pydantic import ValidationError

    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.source_dependency_review import review_dependencies

    source = block('body', 'Thiếu dữ liệu thì chờ bổ sung.')
    condition = block('condition', 'Phải giữ trạng thái chưa rõ.', 100)
    req = AskRequest(collection_id='c', question='Trạng thái nào?')

    async def call(db, request, contract, instruction, payload, **kwargs):
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'required': True,
            'governs': ['body']}]})

    with pytest.raises(ValidationError):
        await review_dependencies(None, req, QueryPlan(query=req.question), [bound(source)], [source, condition],
            {'e2.c0': condition.text}, passage_catalog([source, condition]), call)
