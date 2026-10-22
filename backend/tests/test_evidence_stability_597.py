"""Source obligations survive repair; extractive spans and referents retain roles."""
from unittest.mock import patch

import pytest

from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.intent_contracts import ContextReferent, referent_errors
from app.modules.rag.schemas import AskRequest
from tests.test_source_answer_scope_575 import block, bound


@pytest.mark.asyncio
async def test_corrective_answer_cannot_discard_previously_required_source_clause():
    from app.modules.rag.evidence_verification import verify_bound_answer

    permission = block('permit', 'Được gia hạn bằng biên bản trực tuyến.', parent='rule')
    condition = block('require', 'Chỉ áp dụng khi có nhật ký và xác nhận cùng kỳ.', 100, parent='rule')
    blocks = [permission, condition]
    claim = bound(permission)
    req = AskRequest(collection_id='c', question='Gia hạn bằng cách nào?')
    plan = QueryPlan(query=req.question, entity='Gia hạn', requested_topics=['Cách gia hạn'])
    audit_calls = 0

    async def call(db, request, contract, instruction, payload, **kwargs):
        nonlocal audit_calls
        if contract.__name__ == 'SourceDependencyReview':
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
                'required': False, 'governs': []} for c in payload['conditions']]})
        if 'claims' not in contract.model_fields:
            return contract.model_validate({'verdicts': [{'claim_id': claim['id'], 'entailed': True,
                'relevant': True, 'scope_compatible': True, 'reason': ''}], 'complete': True,
                'topic_coverage': {'Cách gia hạn': True}})
        audit_calls += 1
        return contract.model_validate({'claims': [{'claim_id': claim['id'], 'all_assertions_supported': True}],
            'complete': True, 'source_conditions': [{'clause_id': key, 'required': audit_calls == 1,
                'retained_by': []} for key in payload.get('source_conditions', {})]})

    with patch('app.modules.rag.evidence_verification.structured_call', side_effect=call):
        first = await verify_bound_answer(None, req, {}, [claim], blocks, plan, [])
        second = await verify_bound_answer(None, req, {}, [claim], blocks, plan, [])
    assert not first.complete
    assert not second.complete
    assert any(ref.block_id == condition.id for ref in second.source_qualifier_gaps)


@pytest.mark.parametrize('rewritten', ['Chỉ tiêu SV năm 2033', 'chỉ tiêu  SV năm 2033', 'CHỈ TIÊU SV năm 2033'])
def test_rewritten_natural_metric_accepts_presentation_only_changes(rewritten):
    ref = ContextReferent(field='metric', value='chỉ tiêu SV', source_turn=0, quote='chỉ tiêu SV')
    assert not referent_errors([ref], 'năm 2033', ['chỉ tiêu SV'], rewritten)


@pytest.mark.parametrize('field,value,rewritten', [
    ('metric', 'chỉ tiêu SV', 'số SV ghi nhận năm 2033'),
    ('program_code', 'ZX-0070', 'zx-0070 năm 2033'),
    ('program_code', 'ZX-0070', 'ZX-00701 năm 2033'),
    ('source', 'https://example.org/PlanA', 'https://example.org/plana'),
])
def test_rewritten_equivalence_does_not_change_metric_code_or_url(field, value, rewritten):
    ref = ContextReferent(field=field, value=value, source_turn=0, quote=value)
    assert referent_errors([ref], 'năm 2033', [value], rewritten)


def test_source_quotation_remains_exact_even_when_rewrite_is_case_insensitive():
    ref = ContextReferent(field='metric', value='chỉ tiêu SV', source_turn=0, quote='CHỈ TIÊU SV')
    assert referent_errors([ref], 'năm 2033', ['chỉ tiêu SV'], 'Chỉ tiêu SV năm 2033')


def test_source_definition_can_be_retained_collectively_with_exact_owning_spans():
    from app.modules.rag.evidence_audit import literal_condition_retained
    from app.modules.rag.evidence_schemas import QuoteReference
    from app.modules.rag.evidence_validation import bind_quote

    text = 'Q là điểm tổng hợp; A là chất lượng; B là tỷ lệ đúng hạn.'
    source = block('formula', text)
    clauses = [bound(source, quote) | {'id': str(i)} for i, quote in enumerate(
        ['Q là điểm tổng hợp;', 'A là chất lượng;', 'B là tỷ lệ đúng hạn.'])]
    reference = bind_quote(QuoteReference(block_id=source.id, quote=text), {source.id: source})
    assert literal_condition_retained(reference, clauses, 'value_constraint', [])
    assert not literal_condition_retained(reference, clauses[:-1], 'value_constraint', [])
    foreign = [dict(c, references=[dict(c['references'][0], canonical_hash='other')]) for c in clauses]
    assert not literal_condition_retained(reference, foreign, 'value_constraint', [])


def test_passage_ids_allow_narrow_date_role_without_including_end_date():
    from app.modules.rag.evidence_passages import passage_catalog

    source = block('dates', 'Áp dụng từ 02/03/2033 và kết thúc đánh giá vào 15/06/2033.')
    quotes = [r.quote for r in passage_catalog([source]).values()]
    assert 'Áp dụng từ 02/03/2033' in quotes
    assert source.text in quotes


def test_passage_split_preserves_coordinated_years_and_negation():
    from app.modules.rag.evidence_passages import passage_catalog

    source = block('scope', 'Không áp dụng cho năm 2033 và 2034.')
    assert all(r.quote == source.text for r in passage_catalog([source]).values())


def test_narrow_date_passages_do_not_split_a_semicolon_qualification():
    from app.modules.rag.evidence_passages import passage_catalog

    source = block('scope', 'Được gia hạn 9 ngày; chỉ áp dụng khi có xác nhận cùng kỳ.')
    assert all(r.quote == source.text for r in passage_catalog([source]).values())


@pytest.mark.parametrize('change', ['plan', 'revision', 'hash', 'missing', 'retained'])
def test_condition_obligations_are_scoped_and_cannot_repair_from_wrong_evidence(change):
    from types import SimpleNamespace

    from app.modules.rag.evidence_obligations import missing_conditions, remember_conditions
    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.source_scope_audit import SourceConditionCheck

    permission = block('permit', 'Được gia hạn.', parent='rule')
    condition = block('require', 'Phải có văn bản xác nhận.', 100, parent='rule')
    req = AskRequest(collection_id='c', question='Gia hạn thế nào?')
    plan = QueryPlan(query=req.question, entity='Delta')
    indexed = SimpleNamespace(source_conditions=[SourceConditionCheck(clause_id='e2.c0', required=True)])
    remember_conditions(req, plan, indexed, SimpleNamespace(required_qualifiers=[]),
        {'e2.c0': condition.text}, passage_catalog([permission, condition]), [permission, condition])
    claims = [bound(permission)]
    blocks = [permission, condition]
    if change == 'plan':
        plan = plan.model_copy(update={'entity': 'Epsilon'})
    if change == 'revision':
        other = permission.model_copy(update={'source_revision_id': 'other'})
        claims, blocks = [bound(other)], [other, condition]
    if change == 'hash':
        blocks = [permission, condition.model_copy(update={'canonical_hash': 'other'})]
    if change == 'missing':
        blocks = [permission]
    if change == 'retained':
        claims.append(bound(condition) | {'id': 'condition'})
    gaps, unavailable = missing_conditions(req, plan, claims, blocks)
    assert not gaps
    assert bool(unavailable) == (change in {'hash', 'missing'})
    assert '_source_obligations' not in req.model_dump()
    assert condition.text not in str(req._retrieval_diagnostics)
