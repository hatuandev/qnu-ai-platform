"""Source-only applicability, precise restrictions and safe restoration regressions."""
from unittest.mock import patch

import pytest

from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest
from tests.test_source_answer_scope_575 import block, bound


def verifier(contract, payload):
    return contract.model_validate({'verdicts': [{'claim_id': c['id'], 'entailed': True,
        'relevant': True, 'scope_compatible': True, 'reason': ''} for c in payload['claims']],
        'complete': True, 'topic_coverage': {'requested': True}})


@pytest.mark.asyncio
async def test_source_only_review_catches_prerequisite_draft_audit_called_optional():
    from app.modules.rag.evidence_verification import verify_bound_answer

    permission = block('permit', 'Được thay văn bản giấy bằng biên bản trực tuyến.', parent='rule')
    condition = block('condition', 'Chỉ hồ sơ nhóm Delta có nhật ký cùng kỳ mới được thay thế.', 100, parent='rule')
    req = AskRequest(collection_id='c', question='Có thể thay văn bản bằng gì?')
    plan = QueryPlan(query=req.question, requested_topics=['requested'])
    seen = []

    async def call(db, request, contract, instruction, payload, **kwargs):
        if contract.__name__ == 'SourceDependencyAgreement':
            target = payload['bodies'][0]['id']
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
                'decision': 'required', 'relation': 'prerequisite',
                'evidence_ids': [target]} for c in payload['conditions']]})
        if contract.__name__ == 'SourceDependencyReview':
            seen.append(payload)
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
                'required': True, 'governs': [payload['bodies'][0]['id']]} for c in payload['conditions']]})
        if 'claims' not in contract.model_fields:
            return verifier(contract, payload)
        return contract.model_validate({'claims': [{'claim_id': c['id'], 'all_assertions_supported': True}
            for c in payload['claims']], 'complete': True,
            'source_conditions': [{'clause_id': key, 'required': False, 'retained_by': []}
                for key in payload.get('source_conditions', {})]})

    with patch('app.modules.rag.evidence_verification.structured_call', side_effect=call):
        result = await verify_bound_answer(None, req, {}, [bound(permission)], [permission, condition], plan, [])
    assert not result.complete
    assert [ref.block_id for ref in result.source_qualifier_gaps] == ['condition']
    assert len(seen) == 1
    assert 'claims' not in seen[0] and 'previous_proposal' not in seen[0]


@pytest.mark.asyncio
async def test_broad_qualifier_proof_is_not_a_mandate_to_publish_unrelated_sentences():
    from app.modules.rag.evidence_verification import verify_bound_answer

    source = block('rule', 'Được gia hạn 9 ngày. Tổ tổng hợp quản lý bản sao.', parent='rule')
    claim = bound(source, 'Được gia hạn 9 ngày.')
    req = AskRequest(collection_id='c', question='Gia hạn tối đa bao lâu?')
    plan = QueryPlan(query=req.question, requested_topics=['requested'])

    async def call(db, request, contract, instruction, payload, **kwargs):
        if contract.__name__ == 'SourceDependencyReview':
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
                'required': False, 'governs': []} for c in payload['conditions']]})
        if 'claims' not in contract.model_fields:
            return verifier(contract, payload)
        return contract.model_validate({'claims': [{'claim_id': claim['id'], 'all_assertions_supported': True}],
            'complete': True, 'essential_conditions': [{'requirement': 'Thời hạn tối đa 9 ngày',
                'role': 'value_constraint', 'evidence_id': 'e1', 'retained_by': [claim['id']]}],
            'source_conditions': [{'clause_id': key, 'required': False, 'retained_by': []}
                for key in payload.get('source_conditions', {})]})

    with patch('app.modules.rag.evidence_verification.structured_call', side_effect=call):
        result = await verify_bound_answer(None, req, {}, [claim], [source], plan, [])
    assert result.complete


@pytest.mark.asyncio
async def test_discarded_heading_does_not_prevent_exact_condition_restoration():
    from app.modules.rag.evidence_verification import (
        complete_source_conditions,
        verify_bound_answer,
    )

    permission = block('permit', 'Được gia hạn bằng biên bản.', parent='rule')
    condition = block('condition', 'Phải có quyết định trong cùng kỳ.', 100, parent='rule')
    heading = block('heading', '### Quy định', 200, 'heading', 'rule')
    claims = [bound(permission), bound(heading) | {'id': 'title'}]
    req = AskRequest(collection_id='c', question='Gia hạn bằng gì?')
    plan = QueryPlan(query=req.question, requested_topics=['requested'])

    async def call(db, request, contract, instruction, payload, **kwargs):
        if contract.__name__ == 'SourceDependencyReview':
            return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
                'required': True, 'governs': [payload['bodies'][0]['id']]} for c in payload['conditions']]})
        if 'claims' not in contract.model_fields:
            return verifier(contract, payload)
        return contract.model_validate({'claims': [{'claim_id': c['id'],
            'all_assertions_supported': c['id'] != 'title'} for c in payload['claims']], 'complete': True,
            **({'source_conditions': [{'clause_id': key, 'required': True, 'retained_by': []}
                for key in payload['source_conditions']]} if payload.get('source_conditions') else {})})

    with patch('app.modules.rag.evidence_verification.structured_call', side_effect=call):
        initial = await verify_bound_answer(None, req, {}, claims, [permission, condition, heading], plan, [])
        result = await complete_source_conditions(None, req, {}, initial, [permission, condition, heading], plan, [])
    assert result.complete
    assert any(condition.text == c['text'] for c in result.claims)
    assert all(c['id'] != 'title' for c in result.claims)


@pytest.mark.asyncio
async def test_independent_verification_never_sees_historical_repair_verdicts():
    from app.modules.rag.evidence_verification import verify_bound_answer

    source = block('rule', 'Giá trị nguồn đã được xác nhận.')
    req = AskRequest(collection_id='c', question='Giá trị nào?')
    plan = QueryPlan(query=req.question, requested_topics=['requested'])
    seen = []

    async def call(db, request, contract, instruction, payload, **kwargs):
        seen.append(payload)
        if 'claims' not in contract.model_fields:
            return verifier(contract, payload)
        return contract.model_validate({'claims': [{'claim_id': 'claim', 'all_assertions_supported': True}], 'complete': True})

    with patch('app.modules.rag.evidence_verification.structured_call', side_effect=call):
        await verify_bound_answer(None, req, {'coverage_repair': {'missing_constraints': ['private stale verdict']},
            'previous_proposal': {'private': 'stale draft'}}, [bound(source)], [source], plan, [])
    assert all('coverage_repair' not in payload and 'previous_proposal' not in payload for payload in seen)


def test_descriptive_rules_keep_exact_unresolved_row_without_promoting_numeric_usage():
    from app.modules.rag.source_labels import supplemental_context

    caption = block('cap', 'Bảng 23. Rà soát công việc', 10)
    header = block('t:header', '| Mã | Điều kiện |\n| --- | --- |', 60, 'table', 't')
    row = block('row', '| ZX-0042 | Theo đầy đủ điều kiện ở phụ lục. |', 160, 'table', 't')
    row.header_context = header.text
    row.fact_context['unresolved_cell_columns'] = ['condition']
    original = row.model_dump()
    blocks = [caption, header, row]
    question = 'Bảng 23 quy định điều kiện của ZX-0042 là gì?'
    assert row not in supplemental_context(blocks, question, allow_tables=True)
    assert row in supplemental_context(blocks, question, allow_tables=True, allow_descriptive_unresolved=True)
    assert row not in supplemental_context(blocks, question.replace('23', '24'),
        allow_tables=True, allow_descriptive_unresolved=True)
    assert row.model_dump() == original


def test_labeled_fields_have_narrow_ids_but_native_list_keeps_qualification():
    from app.modules.rag.evidence_passages import passage_catalog

    metadata = block('meta', 'Mốc ghi nhận: 02/03/2033\nMốc bắt đầu: 05/04/2033\nPhạm vi: 2032, 2033')
    quotes = {r.quote for r in passage_catalog([metadata]).values()}
    assert 'Mốc ghi nhận: 02/03/2033' in quotes
    assert 'Mốc bắt đầu: 05/04/2033' in quotes
    assert metadata.text in quotes
    rule = block('list', '1. Gia hạn đến 02/03/2033 và phải nộp xác nhận vào 03/03/2033.', kind='list')
    assert all(r.quote == rule.text for r in passage_catalog([rule]).values())


@pytest.mark.asyncio
async def test_source_review_cache_tracks_content_and_preserves_two_call_budget():
    import json

    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.source_dependency_review import review_dependencies

    body = block('body', 'Được nộp biên bản trực tuyến.')
    condition = block('condition', 'Ghi chú cho chương trình khác.', 100)
    req = AskRequest(collection_id='c', question='private_marker')
    plan = QueryPlan(query=req.question)
    calls = []

    async def call(db, request, contract, instruction, payload, **kwargs):
        calls.append(payload)
        return contract.model_validate({'conditions': [{'clause_id': c['clause_id'],
            'required': False, 'governs': []} for c in payload['conditions']]})

    async def read(current):
        blocks = [body, current]
        return await review_dependencies(None, req, plan, [bound(body)], blocks,
            {'e2.c0': current.text}, passage_catalog(blocks), call)

    assert await read(condition) is not None
    assert await read(condition) is not None
    changed = condition.model_copy(update={'text': 'Ghi chú đã thay đổi.', 'canonical_hash': 'new'})
    assert await read(changed) is not None
    assert len(calls) == 2
    assert await read(condition) is not None
    assert await read(changed.model_copy(update={'canonical_hash': 'third'})) is None
    assert len(calls) == 2
    assert 'private_marker' not in json.dumps(req._retrieval_diagnostics)
    assert '_source_dependency_reviews' not in req.model_dump()


@pytest.mark.asyncio
async def test_source_review_cannot_bind_condition_to_another_revision():
    from app.core.exceptions import AppException
    from app.modules.rag.evidence_passages import passage_catalog
    from app.modules.rag.source_dependency_review import review_dependencies

    body = block('body', 'Được nộp biên bản.', revision='new')
    condition = block('condition', 'Phải có chữ ký cùng kỳ.', 100, revision='old')
    req = AskRequest(collection_id='c', question='Nộp theo cách nào?')

    async def call(db, request, contract, instruction, payload, **kwargs):
        return contract.model_validate({'conditions': [{'clause_id': 'e2.c0',
            'required': True, 'governs': [payload['bodies'][0]['id']]}]})

    with pytest.raises(AppException) as caught:
        await review_dependencies(None, req, QueryPlan(query=req.question), [bound(body)], [body, condition],
            {'e2.c0': condition.text}, passage_catalog([body, condition]), call)
    assert caught.value.code == 'SOURCE_DEPENDENCY_SCOPE_INVALID'
