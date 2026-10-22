"""A repaired prerequisite must not hide a newly missing answer facet."""
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
@pytest.mark.parametrize('completed', [True, False])
@pytest.mark.parametrize('gap_kind', ['facet', 'qualifier'])
async def test_missing_facet_after_condition_completion_gets_bounded_source_reselection(completed, gap_kind):
    body = block('body', 'Được gia hạn trong chín ngày.', parent='rule')
    condition = block('condition', 'Phải có quyết định được ký.', 100, parent='rule')
    exclusion = block('exclude', 'Không thay đổi số lượng người học.', 200, parent='rule')
    req = AskRequest(collection_id='c', question='Gia hạn thế nào, có thay đổi số lượng không?',
                     reranker_policy={'enabled': False})
    plan = QueryPlan(query=req.question, requested_topics=['Thời hạn', 'Số lượng'])
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    first = bound(body)
    first['id'] = 'time'
    restored = bound(condition) | {'id': 'condition'}
    remaining = bound(exclusion) | {'id': 'exclusion'}

    def verdict(claims, topics, complete=False, qualifiers=None):
        return VerifiedAnswer(claims, complete, [] if complete else ['Chưa đủ phạm vi'], [],
            VerificationResult(complete=complete, topic_coverage=topics), None, [],
            source_qualifier_gaps=qualifiers or [])

    initial = verdict([first], {'Thời hạn': True, 'Số lượng': True},
        qualifiers=[QuoteReference(block_id=condition.id, quote=condition.text)])
    repaired = verdict([first, restored], {'Thời hạn': True, 'Số lượng': gap_kind == 'qualifier'},
        qualifiers=[QuoteReference(block_id=exclusion.id, quote=exclusion.text)] if gap_kind == 'qualifier' else [])
    final = verdict([first, restored, remaining], {'Thời hạn': True, 'Số lượng': completed}, complete=completed)
    propose = AsyncMock(side_effect=[(SimpleNamespace(status='supported'), [first], [], False),
                                    (SimpleNamespace(status='supported'), [remaining], [], False)])
    verify = AsyncMock(side_effect=[initial, repaired, final])
    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[body, condition, exclusion])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=plan)),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', propose),
          patch('app.modules.rag.prose_fallback.verify_bound_answer', verify)):
        result = await answer_from_prose(None, req, snap, EvidencePolicy(), 'VISIBLE_ANSWER_NOT_SUPPORTED')
    assert propose.await_count == 2 and verify.await_count == 3
    current_feedback = propose.await_args.args[2]['coverage_repair']
    assert current_feedback['topic_coverage']['Số lượng'] is (gap_kind == 'qualifier')
    assert {c['text'] for c in verify.await_args.args[3]} >= {body.text, condition.text, exclusion.text}
    assert (result is not None) is completed
    trace = req._retrieval_diagnostics['prose_fallback']
    assert trace['repair_stop_reason'] == ('complete' if completed else 'budget_exhausted')


@pytest.mark.asyncio
async def test_no_progress_stops_without_replaying_identical_selection():
    source = block('body', 'Phạm vi hồ sơ cần xác minh.')
    req = AskRequest(collection_id='c', question='Phạm vi hồ sơ cần điều kiện gì?', reranker_policy={'enabled': False})
    plan = QueryPlan(query=req.question, requested_topics=['Điều kiện'])
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    item = bound(source)
    state = VerifiedAnswer([item], False, ['Thiếu điều kiện'], [],
        VerificationResult(complete=False, topic_coverage={'Điều kiện': False}), None, [])
    with (patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[source])),
          patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=plan)),
          patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(
              return_value=(SimpleNamespace(status='supported'), [item], [], False))) as propose,
          patch('app.modules.rag.prose_fallback.verify_bound_answer', AsyncMock(return_value=state))):
        assert await answer_from_prose(None, req, snap, EvidencePolicy(), 'VISIBLE_ANSWER_NOT_SUPPORTED') is None
    assert propose.await_count == 2
    assert req._retrieval_diagnostics['prose_fallback']['repair_stop_reason'] == 'no_progress'
