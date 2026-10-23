"""An audited obligation discovered at a new owner must survive reselection."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.modules.rag.evidence_schemas import QueryPlan, QuoteReference, VerificationResult
from app.modules.rag.evidence_verification import VerifiedAnswer
from app.modules.rag.prose_fallback import answer_from_prose
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from tests.test_source_answer_scope_575 import block, bound


@pytest.mark.asyncio
@pytest.mark.parametrize('independent_verdict', [True, False])
async def test_reselection_cannot_drop_new_source_obligation(independent_verdict):
    body = block('body', 'Được gia hạn trong chín ngày.', parent='rule')
    condition = block('condition', 'Phải có quyết định được ký.', 100, parent='rule')
    exclusion = block('exclude', 'Không thay đổi số lượng người học.', 200, parent='rule')
    req = AskRequest(collection_id='c', question='Gia hạn thế nào, có thay đổi số lượng không?', reranker_policy={'enabled': False})
    plan = QueryPlan(query=req.question, requested_topics=['Thời hạn', 'Số lượng'])
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    first, retained = bound(body), bound(condition)
    def verdict(claims, missing=None, complete=False):
        return VerifiedAnswer(claims, complete, [] if complete else ['source obligation'], [],
            VerificationResult(complete=complete, topic_coverage={'Thời hạn': True, 'Số lượng': True}), None, [],
            source_qualifier_gaps=[QuoteReference(block_id=missing.id, quote=missing.text)] if missing else [])
    calls = []
    async def verify(db, request, payload, claims, blocks, query, rules):
        calls.append(claims)
        if len(calls) == 1:
            return verdict([first], condition)
        if len(calls) == 2:
            return verdict([first, retained], exclusion)
        texts = {c['text'] for c in claims}
        return verdict(claims, None, complete=independent_verdict and exclusion.text in texts)
    # Deliberately omit the new restriction in the second model draft.
    propose = AsyncMock(return_value=(SimpleNamespace(status='supported'), [first], [], False))
    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[body, condition, exclusion])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=plan)),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', propose),
          patch('app.modules.rag.prose_fallback.verify_bound_answer', verify)):
        result = await answer_from_prose(None, req, snap, EvidencePolicy(), 'VISIBLE_ANSWER_NOT_SUPPORTED')
    assert propose.await_count == 2 and len(calls) == 3
    assert {c['text'] for c in calls[-1]} >= {body.text, condition.text, exclusion.text}
    assert (result is not None) is independent_verdict


def test_same_words_in_a_different_block_do_not_satisfy_a_recovered_obligation():
    from app.modules.rag.evidence_recovery import retain_recovered_conditions
    first = block('note-one', 'Only the preceding table is covered.', 0)
    second = block('note-two', first.text, 200)
    result = retain_recovered_conditions([bound(first)], [bound(second)])
    assert len(result) == 2
    assert len({c['id'] for c in result}) == 2
    assert {c['references'][0]['block_id'] for c in result} == {'note-one', 'note-two'}


@pytest.mark.asyncio
@pytest.mark.parametrize('question,years', [('năm2024–2026', [2024, 2025, 2026]),
                                          ('năm2024/2025', [2024, 2025]), ('mã AM-2024', [])])
async def test_prose_recovery_uses_the_same_literal_years_as_plan_validation(question, years):
    async def plan(db, req, original, observed):
        assert observed == years
        raise RuntimeError('stop before inference')
    req = AskRequest(collection_id='c', question=question)
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[block('b', 'Nguồn kiểm thử.')])),
          patch('app.modules.rag.prose_fallback.recovery_plan', plan),
          pytest.raises(RuntimeError, match='stop before inference')):
        await answer_from_prose(None, req, snap, EvidencePolicy(), 'VISIBLE_ANSWER_NOT_SUPPORTED')
