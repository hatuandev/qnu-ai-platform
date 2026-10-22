"""Conflicting source-applicability judgments are reconciled before latching."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.modules.rag.evidence_passages import passage_catalog
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest
from app.modules.rag.source_dependency_review import DependencyReview, SourceDependency
from tests.test_source_answer_scope_575 import block, bound


@pytest.mark.asyncio
@pytest.mark.parametrize('decision', ['required', 'not_required', 'unresolved'])
async def test_disputed_new_dependency_needs_independent_branch_decision(decision):
    from app.core.exceptions import AppException
    from app.modules.rag.source_dependency_agreement import reconcile_dependencies

    body = block('body', 'Thiếu dữ liệu thì ghi trạng thái chưa đủ.')
    definition = block('definition', 'Điểm tổng hợp sử dụng thang chuẩn.', 100)
    req = AskRequest(collection_id='c', question='Thiếu dữ liệu thì ghi gì?')
    initial = SimpleNamespace(source_conditions=[SourceDependency(clause_id='e2.c0', required=False)])
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e2.c0', required=True, governs=['claim'])])
    calls = []

    async def call(db, request, contract, instruction, payload, **kwargs):
        calls.append(payload)
        assert payload['bodies'][0]['text'] == body.text
        assert 'previous_verdict' not in payload and 'draft' not in payload
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'decision': decision,
            'relation': 'definition', 'evidence_ids': ['claim']}]})

    async def run():
        return await reconcile_dependencies(None, req, QueryPlan(query=req.question), [bound(body)],
            [body, definition], {'e2.c0': definition.text}, passage_catalog([body, definition]), initial, proposed, call)

    if decision == 'unresolved':
        with pytest.raises(AppException) as error:
            await run()
        assert error.value.code == 'SOURCE_DEPENDENCY_CONFLICT'
    else:
        result = await run()
        assert result.conditions[0].required is (decision == 'required')
        assert (await run()).model_dump() == result.model_dump()
        assert len(calls) == 1


@pytest.mark.asyncio
async def test_agreed_dependencies_do_not_add_a_call_or_erase_prior_obligations():
    from app.modules.rag.source_dependency_agreement import reconcile_dependencies

    body = block('body', 'Chỉ được thay thế khi đủ hồ sơ.')
    req = AskRequest(collection_id='c', question='Khi nào được thay?')
    prior = {'sentinel': 'must remain'}
    req._source_obligations['prior'] = prior
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e1.c0', required=True, governs=['claim'])])

    async def call(*args, **kwargs):
        raise AssertionError('No disputed new dependency')

    result = await reconcile_dependencies(None, req, QueryPlan(query=req.question), [bound(body)], [body],
        {'e1.c0': body.text}, passage_catalog([body]), proposed, proposed, call)
    assert result is proposed and req._source_obligations['prior'] is prior


@pytest.mark.asyncio
async def test_confirmation_cannot_use_a_different_revision_or_missing_link_proof():
    from app.core.exceptions import AppException
    from app.modules.rag.source_dependency_agreement import reconcile_dependencies

    body = block('body', 'Được thay thế khi đủ căn cứ.', revision='new')
    other = block('other', 'Điều kiện ở revision khác.', 100, revision='old')
    req = AskRequest(collection_id='c', question='Điều kiện nào?')
    indexed = SimpleNamespace(source_conditions=[])
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e2.c0', required=True, governs=['claim'])])

    async def call(db, request, contract, instruction, payload, **kwargs):
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'decision': 'required',
            'relation': 'prerequisite', 'evidence_ids': ['claim']}]})

    with pytest.raises(AppException) as error:
        await reconcile_dependencies(None, req, QueryPlan(query=req.question), [bound(body)], [body, other],
            {'e2.c0': other.text}, passage_catalog([body, other]), indexed, proposed, call)
    assert error.value.code == 'SOURCE_DEPENDENCY_SCOPE_INVALID'


@pytest.mark.asyncio
@pytest.mark.parametrize('basis', [[], ['claim', 'claim']])
async def test_confirmed_dependency_requires_nonempty_unique_target_proof(basis):
    from app.core.exceptions import AppException
    from app.modules.rag.source_dependency_agreement import (
        DependencyDecision,
        reconcile_dependencies,
    )

    body = block('body', 'Được thay thế bằng xác nhận trực tuyến.')
    rule = block('rule', 'Chỉ hồ sơ có nhật ký được thay thế.', 100)
    req = AskRequest(collection_id='c', question='Thay thế bằng gì?')
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e2.c0', required=True, governs=['claim'])])

    async def call(db, request, contract, instruction, payload, **kwargs):
        # A malformed adapter must not bypass server checks even if it skips schema validation.
        return contract.model_construct(conditions=[DependencyDecision.model_construct(
            clause_id='e2.c0', decision='required', relation='prerequisite', evidence_ids=basis)])

    with pytest.raises(AppException) as error:
        await reconcile_dependencies(None, req, QueryPlan(query=req.question), [bound(body)], [body, rule],
            {'e2.c0': rule.text}, passage_catalog([body, rule]), SimpleNamespace(source_conditions=[]), proposed, call)
    assert error.value.code == 'SOURCE_DEPENDENCY_AGREEMENT_INVALID'
    attempt = req._retrieval_diagnostics['source_dependency_agreements'][0]
    assert attempt['status'] == 'rejected' and attempt['checks'][0]['evidence_ids'] == basis


@pytest.mark.asyncio
async def test_reconciliation_has_one_request_budget_and_preserves_existing_latched_rule():
    from app.core.exceptions import AppException
    from app.modules.rag.evidence_obligations import missing_conditions, remember_conditions
    from app.modules.rag.source_dependency_agreement import reconcile_dependencies

    body = block('body', 'Được gia hạn khi đủ căn cứ.')
    rule = block('rule', 'Phải có quyết định cùng kỳ.', 100)
    req = AskRequest(collection_id='c', question='Được gia hạn không?')
    plan = QueryPlan(query=req.question)
    catalog = passage_catalog([body, rule])
    clauses = {'e2.c0': rule.text}
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e2.c0', required=True, governs=['claim'])])
    remember_conditions(req, plan, proposed, None, clauses, catalog, [body, rule])

    async def call(db, request, contract, instruction, payload, **kwargs):
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0', 'decision': 'not_required',
            'relation': 'unrelated', 'evidence_ids': ['claim']}]})

    await reconcile_dependencies(None, req, plan, [bound(body)], [body, rule], clauses, catalog,
        SimpleNamespace(source_conditions=[]), proposed, call)
    missing, _ = missing_conditions(req, plan, [bound(body)], [body, rule])
    assert [m.quote for m in missing] == [rule.text]  # Prior confirmed obligation is immutable.
    with pytest.raises(AppException) as error:
        await reconcile_dependencies(None, req, plan.model_copy(update={'attribute': 'different facet'}),
            [bound(body)], [body, rule], clauses, catalog, SimpleNamespace(source_conditions=[]), proposed, call)
    assert error.value.code == 'SOURCE_DEPENDENCY_CONFLICT'


@pytest.mark.asyncio
@pytest.mark.parametrize('needed', [True, False])
async def test_verification_latches_only_reconciled_new_conditions(needed):
    from app.modules.rag.evidence_verification import verify_bound_answer
    from tests.test_source_dependency_repair_597 import verifier

    body = block('body', 'Thiếu dữ liệu thì giữ trạng thái chưa đủ.', parent='rule')
    context = block('definition', 'Điểm tổng hợp dùng một thang chuẩn.', 100, parent='rule')
    req = AskRequest(collection_id='c', question='Khi thiếu dữ liệu thì ghi gì?')
    plan = QueryPlan(query=req.question, requested_topics=['requested'])

    async def call(db, request, contract, instruction, payload, **kwargs):
        if contract.__name__ == 'SourceDependencyReview':
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
                'required': True, 'governs': ['claim']} for c in payload['conditions']]})
        if contract.__name__ == 'SourceDependencyAgreement':
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
                'decision': 'required' if needed else 'not_required', 'relation': 'definition',
                'evidence_ids': ['claim']}
                for c in payload['conditions']]})
        if 'claims' not in contract.model_fields:
            return verifier(contract, payload)
        return contract.model_validate({'claims': [{'claim_id': 'claim', 'all_assertions_supported': True}],
            'complete': True, 'source_conditions': [{'clause_id': key, 'required': False}
                for key in payload.get('source_conditions', {})]})

    with patch('app.modules.rag.evidence_verification.structured_call', side_effect=call):
        result = await verify_bound_answer(None, req, {}, [bound(body)], [body, context], plan, [])
    assert result.complete is (not needed)
    assert [q.block_id for q in result.source_qualifier_gaps] == ([context.id] if needed else [])


@pytest.mark.asyncio
@pytest.mark.parametrize('clause,target', [('e9.c0', 'claim'), ('e2.c0', 'unknown')])
async def test_agreement_contract_rejects_unknown_clause_or_evidence_id_before_latching(clause, target):
    from pydantic import ValidationError

    from app.modules.rag.source_dependency_agreement import reconcile_dependencies

    body = block('body', 'Thiếu dữ liệu thì chưa đủ.')
    rule = block('rule', 'Định nghĩa của thang đo.', 100)
    req = AskRequest(collection_id='c', question='Thiếu dữ liệu thì sao?')
    proposed = DependencyReview(conditions=[SourceDependency(clause_id='e2.c0', required=True, governs=['claim'])])

    async def call(db, request, contract, instruction, payload, **kwargs):
        return contract.model_validate({'conditions': [{'clause_id': clause, 'decision': 'required',
            'relation': 'prerequisite', 'evidence_ids': [target]}]})

    with pytest.raises(ValidationError):
        await reconcile_dependencies(None, req, QueryPlan(query=req.question), [bound(body)], [body, rule],
            {'e2.c0': rule.text}, passage_catalog([body, rule]), SimpleNamespace(source_conditions=[]), proposed, call)
    assert not req._source_obligations and not req._source_dependency_reviews


@pytest.mark.asyncio
@pytest.mark.parametrize('changed_body', [False, True])
async def test_source_proof_survives_added_claim_but_never_changed_target(changed_body):
    from app.core.exceptions import AppException
    from app.modules.rag.source_dependency_agreement import reconcile_dependencies

    body = block('body', 'Thiếu dữ liệu thì chưa đủ.')
    rule = block('rule', 'Phải giữ nguyên trạng thái. Ngoại lệ được xác nhận riêng.', 100)
    req = AskRequest(collection_id='c', question='Thiếu dữ liệu thì sao?')
    plan = QueryPlan(query=req.question)
    blocks = [body, rule]
    catalog = passage_catalog(blocks)
    clauses = {'e2.c0': 'Phải giữ nguyên trạng thái.', 'e2.c1': 'Ngoại lệ được xác nhận riêng.'}
    first = DependencyReview(conditions=[SourceDependency(clause_id=key, required=key.endswith('c0'),
        governs=['claim'] if key.endswith('c0') else []) for key in clauses])
    calls = []

    async def call(db, request, contract, instruction, payload, **kwargs):
        calls.append(payload)
        return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
            'decision': 'not_required', 'relation': 'unrelated', 'evidence_ids': ['claim']}
            for c in payload['conditions']]})

    args = (None, req, plan)
    await reconcile_dependencies(*args, [bound(body)], blocks, clauses, catalog,
        SimpleNamespace(source_conditions=[]), first, call)
    assert len(calls[0]['conditions']) == 2  # Evaluate candidates once, before new disputes.
    later = DependencyReview(conditions=[SourceDependency(clause_id='e2.c1', required=True, governs=['claim'])])
    target = bound(body)
    if changed_body:
        target['references'][0]['quote'] = 'Unevaluated source text'
    claims = [target, {**bound(rule), 'id': 'new'}]
    if changed_body:
        with pytest.raises(AppException) as error:
            await reconcile_dependencies(*args, claims, blocks, clauses, catalog,
                SimpleNamespace(source_conditions=[]), later, call)
        assert error.value.code == 'SOURCE_DEPENDENCY_CONFLICT'
    else:
        result = await reconcile_dependencies(*args, claims, blocks, clauses, catalog,
            SimpleNamespace(source_conditions=[]), later, call)
        assert not result.conditions[0].required
    assert len(calls) == 1
