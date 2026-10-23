"""A verdict cannot discard a dependency while affirming its governing role."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.modules.rag.evidence_passages import passage_catalog
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest
from app.modules.rag.source_dependency_agreement import reconcile_dependencies
from app.modules.rag.source_dependency_review import DependencyReview, SourceDependency
from tests.test_source_answer_scope_575 import block, bound


@pytest.mark.asyncio
@pytest.mark.parametrize('relation', ['scope', 'prerequisite', 'exception'])
async def test_negative_decision_cannot_erase_affirmed_governing_relation(relation):
    body = block('permission', 'Được sử dụng chứng nhận điện tử trong kỳ.', parent='rule')
    rule = block('eligibility', 'Chỉ hồ sơ có nhật ký và xác nhận cùng kỳ.', 100, parent='rule')
    req = AskRequest(collection_id='c', question='Được dùng chứng từ gì?')
    plan = QueryPlan(query=req.question)
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e2.c0', required=True, governs=['claim'])])
    calls = []

    async def call(db, request, contract, instruction, payload, **kwargs):
        calls.append(payload)
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'decision': 'not_required',
            'relation': relation, 'evidence_ids': ['claim']}]})

    async def verify(claims):
        return await reconcile_dependencies(None, req, plan, claims, [body, rule], {'e2.c0': rule.text},
            passage_catalog([body, rule]), SimpleNamespace(source_conditions=[]), proposed, call)

    initial = await verify([bound(body)])
    assert initial.conditions[0].required and initial.conditions[0].governs == ['claim']
    replay = await verify([bound(body), {**bound(rule), 'id': 'restored'}])
    assert replay.conditions[0].required and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('relation', ['definition', 'unrelated'])
async def test_non_governing_background_can_still_be_rejected(relation):
    body = block('denial', 'Thiếu dữ liệu thì chưa đủ điều kiện tính.')
    context = block('context', 'Thang đo và cách tổng hợp.', 100)
    req = AskRequest(collection_id='c', question='Thiếu dữ liệu có tính được không?')
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e2.c0', required=True, governs=['claim'])])

    async def call(db, request, contract, instruction, payload, **kwargs):
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'decision': 'not_required',
            'relation': relation, 'evidence_ids': ['claim']}]})

    result = await reconcile_dependencies(None, req, QueryPlan(query=req.question), [bound(body)], [body, context],
        {'e2.c0': context.text}, passage_catalog([body, context]), SimpleNamespace(source_conditions=[]), proposed, call)
    assert not result.conditions[0].required and not req._source_obligations


@pytest.mark.asyncio
@pytest.mark.parametrize('relation', ['scope', 'prerequisite', 'exception'])
async def test_conflicting_governing_verdict_cannot_borrow_another_revision(relation):
    from app.core.exceptions import AppException

    body = block('body', 'Được thay thế khi đủ căn cứ.', revision='new')
    other = block('other', 'Phải giữ điều kiện nguồn.', 100, revision='old')
    req = AskRequest(collection_id='c', question='Được thay thế thế nào?')
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e2.c0', required=True, governs=['claim'])])

    async def call(db, request, contract, instruction, payload, **kwargs):
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'decision': 'not_required',
            'relation': relation, 'evidence_ids': ['claim']}]})

    with pytest.raises(AppException) as error:
        await reconcile_dependencies(None, req, QueryPlan(query=req.question), [bound(body)], [body, other],
            {'e2.c0': other.text}, passage_catalog([body, other]), SimpleNamespace(source_conditions=[]), proposed, call)
    assert error.value.code == 'SOURCE_DEPENDENCY_SCOPE_INVALID'


@pytest.mark.asyncio
async def test_verification_preserves_eligibility_then_accepts_exact_source_repair():
    from app.modules.rag.evidence_verification import (
        complete_source_conditions,
        verify_bound_answer,
    )
    from tests.test_source_dependency_repair_597 import verifier

    body = block('permission', 'Được dùng chứng từ điện tử.', parent='rule')
    rule = block('eligibility', 'Hồ sơ phải có xác nhận và nhật ký cùng kỳ.', 100, parent='rule')
    req = AskRequest(collection_id='c', question='Được dùng chứng từ gì?')
    plan = QueryPlan(query=req.question, requested_topics=['requested'])

    async def call(db, request, contract, instruction, payload, **kwargs):
        if contract.__name__ == 'SourceDependencyReview':
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'], 'required': True,
                'governs': ['claim']} for c in payload['conditions']]})
        if contract.__name__ == 'SourceDependencyAgreement':
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'], 'decision': 'not_required',
                'relation': 'scope', 'evidence_ids': ['claim']} for c in payload['conditions']]})
        if 'claims' not in contract.model_fields:
            return verifier(contract, payload)
        return contract.model_validate({'claims': [{'claim_id': c['id'], 'all_assertions_supported': True}
            for c in payload['claims']], 'complete': True, **({'source_conditions': [
                {'clause_id': key, 'required': False} for key in payload['source_conditions']]}
                if payload.get('source_conditions') else {})})

    with patch('app.modules.rag.evidence_verification.structured_call', side_effect=call):
        initial = await verify_bound_answer(None, req, {}, [bound(body)], [body, rule], plan, [])
        assert not initial.complete and initial.source_qualifier_gaps[0].quote == rule.text
        final = await complete_source_conditions(None, req, {}, initial, [body, rule], plan, [])
    assert final.complete and any(rule.text in c['text'] for c in final.claims)
