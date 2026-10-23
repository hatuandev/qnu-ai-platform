"""Complete draft rule selection without turning adjacency into approved meaning."""

from unittest.mock import patch

import pytest

from app.modules.rag.evidence_claims import propose_bound_claims
from app.modules.rag.evidence_rule_selection import offer_native_list_groups
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest
from tests.test_source_answer_scope_575 import block, bound


def rules():
    blocks = [block('eligibility', '1. Hồ sơ phải có nhật ký cùng kỳ.', parent='rule'),
        block('permission', '2. Được thay chữ ký bằng xác nhận trực tuyến.', 100, parent='rule'),
        block('exclusion', '3. Không miễn kiểm tra an toàn.', 200, parent='rule')]
    for b in blocks:
        b.fact_context.update(source_kind='list', qnu_block_id=b.id)
    return blocks


@pytest.mark.asyncio
async def test_native_rule_selection_offers_whole_source_group_before_independent_verification():
    blocks = rules()
    req = AskRequest(collection_id='c', question='Được thay chữ ký bằng gì?')
    calls = []

    async def select(db, req, contract, instruction, payload, **kwargs):
        calls.append(payload)
        return contract.model_validate({'status': 'supported', 'claims': [{'id': 'permission', 'text': 'source',
            'evidence_ids': ['e2'], 'context_ids': []}], 'missing_constraints': []})

    with patch('app.modules.rag.evidence_claims.structured_call', side_effect=select):
        _, claims, rejected, repaired = await propose_bound_claims(None, req,
            {'compact_passages': True, 'requested': {}}, blocks)
    assert not rejected and not repaired and len(calls) == 1
    assert {c['references'][0]['block_id'] for c in claims} == {b.id for b in blocks}
    assert all(c['text'] in {b.text for b in blocks} and not c.get('verified') for c in claims)


@pytest.mark.parametrize('change', ['parent', 'revision', 'hash', 'binding', 'index', 'legacy', 'container'])
def test_selection_does_not_cross_native_owner_or_source_boundary(change):
    blocks = rules()
    target = blocks[1]
    if change == 'legacy':
        target.fact_context.pop('qnu_block_id')
    elif change == 'container':
        target.is_container = True
    else:
        setattr(target, {'parent': 'parent_id', 'revision': 'source_revision_id', 'hash': 'canonical_hash',
            'binding': 'binding_id', 'index': 'index_revision_id'}[change], 'another')
    selected = [bound(target)]
    assert offer_native_list_groups(selected, blocks) == selected


@pytest.mark.parametrize('change', ['absent_parent', 'duplicate_native', 'oversized'])
def test_invalid_or_unbounded_group_is_not_partially_offered(change):
    blocks = rules()
    if change == 'absent_parent':
        for b in blocks:
            b.parent_id = None
    elif change == 'duplicate_native':
        blocks[0].fact_context['qnu_block_id'] = blocks[1].fact_context['qnu_block_id']
    else:
        blocks[0].text += 'x' * 4000
        blocks[0].end = len(blocks[0].text)
    selected = [bound(blocks[1])]
    assert offer_native_list_groups(selected, blocks) == selected


def test_all_or_none_selection_preserves_the_existing_twelve_claim_budget():
    blocks = rules()
    others = [block('other' + str(i), 'Unrelated source content.', 1000 + i * 100) for i in range(10)]
    selected = [bound(blocks[1]), *[{**bound(b), 'id': b.id} for b in others]]
    assert offer_native_list_groups(selected, [*blocks, *others]) == selected


def test_full_native_members_have_unique_ids_and_exact_bound_source_spans():
    blocks = rules()
    claims = offer_native_list_groups([bound(blocks[1])], blocks)
    assert len({c['id'] for c in claims}) == len(claims) == 3
    for claim, b in zip(claims, blocks, strict=True):
        ref = claim['references'][0]
        assert (ref['quote'], ref['start'], ref['end'], ref['canonical_hash']) == (b.text, b.start, b.end, b.canonical_hash)
    assert offer_native_list_groups(claims, blocks) == claims


@pytest.mark.asyncio
async def test_independent_verifier_can_reject_an_unrelated_offered_list_member():
    from app.modules.rag.evidence_verification import verify_bound_answer
    from tests.test_source_dependency_repair_597 import verifier

    blocks = rules()
    req = AskRequest(collection_id='c', question='Được thay chữ ký bằng gì?')
    claims = offer_native_list_groups([bound(blocks[1])], blocks)
    rejected_id = claims[2]['id']

    async def call(db, request, contract, instruction, payload, **kwargs):
        if contract.__name__ == 'SourceDependencyReview':
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'], 'required': False,
                'governs': []} for c in payload['conditions']]})
        if 'claims' not in contract.model_fields:
            result = verifier(contract, payload)
            return result.model_copy(update={'verdicts': [v.model_copy(update={'relevant': False})
                if v.claim_id == rejected_id else v for v in result.verdicts]})
        return contract.model_validate({'claims': [{'claim_id': c['id'], 'all_assertions_supported': True}
            for c in payload['claims']], 'complete': True, **({'source_conditions': [
                {'clause_id': key, 'required': False} for key in payload['source_conditions']]}
                if payload.get('source_conditions') else {})})

    with patch('app.modules.rag.evidence_verification.structured_call', side_effect=call):
        checked = await verify_bound_answer(None, req, {}, claims, blocks,
            QueryPlan(query=req.question, requested_topics=['requested']), [])
    assert checked.complete and rejected_id not in {c['id'] for c in checked.claims}
    assert all(c['verified'] for c in checked.claims)
