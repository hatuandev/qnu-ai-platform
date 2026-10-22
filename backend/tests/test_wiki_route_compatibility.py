"""Routing regressions exercised before changing the service integration."""
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.modules.rag.schemas import AskRequest, AskResponse, RetrievalSnapshot
from app.modules.rag.service import RagService


@pytest.mark.asyncio
@pytest.mark.parametrize('wiki', [False, True])
async def test_wiki_preserves_verified_cell_decision(wiki):
    from tests.test_rag_followup_and_year_488 import QUESTION, unknown_fact
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(collection_metadata={})
    snap = RetrievalSnapshot(snapshot_id='snapshot', collection_id='collection',
        binding_revisions={'binding': 'index'}, knowledge_wiki_enabled=wiki)
    req = AskRequest(question=QUESTION, collection_id='collection')
    expected = AskResponse(status='answered', answer='Source-bound row answer',
        answer_decision={'cells': [{'value': '(Toán, Lý, Hóa)'}]})
    with (patch('app.modules.rag.evidence_runtime.resolve_evidence_request', AsyncMock(return_value=(req, EvidencePolicy(enabled=False)))),
          patch('app.modules.rag.score_conversion_chat.maybe_convert_score', AsyncMock(return_value=None)),
          patch('app.modules.rag.source_fact_resolution.resolve_fact_scope', AsyncMock(return_value=None)),
          patch('app.modules.rag.service.fact_layer.lookup_facts', AsyncMock(return_value=[unknown_fact()])),
          patch('app.modules.rag.snapshot_fact_evidence.load_snapshot_table_evidence', AsyncMock(return_value=[])),
          patch('app.modules.rag.service.load_row_anchors', AsyncMock(return_value=[object()])),
          patch('app.modules.rag.service.answer_from_rows', AsyncMock(return_value=expected)) as rows,
          patch('app.modules.rag.evidence_pipeline.answer_with_evidence', AsyncMock(return_value=AskResponse(status='answered',answer='General prose'))) as prose):
        result = await RagService()._ask(db, req, candidate_snapshot=snap)
    assert result.answer_decision == expected.answer_decision
    rows.assert_awaited_once()
    prose.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('enabled', [False, True])
async def test_narrative_wiki_and_explicit_evidence_policy_keep_bound_evidence_path(enabled):
    req = AskRequest(question='Giải thích quy trình kiểm định tài liệu.', collection_id='c')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b':'i'}, knowledge_wiki_enabled=True)
    expected = AskResponse(status='answered', answer='Evidence bound explanation')
    with (patch('app.modules.rag.evidence_runtime.resolve_evidence_request', AsyncMock(return_value=(req, EvidencePolicy(enabled=enabled)))),
          patch('app.modules.rag.score_conversion_chat.maybe_convert_score', AsyncMock(return_value=None)),
          patch('app.modules.rag.evidence_pipeline.answer_with_evidence', AsyncMock(return_value=expected)) as prose):
        result = await RagService()._ask(AsyncMock(), req, candidate_snapshot=snap)
    assert result.answer == expected.answer
    prose.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_source_read_can_use_existing_canonical_prose_verification_within_deadline():
    req = AskRequest(question='Tài liệu này có giá trị áp dụng thực tế không?', collection_id='c')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', knowledge_wiki_enabled=True)
    missing = AskResponse(status='insufficient_context', answer='Unverified', answer_decision={
        'status':'missing','reason':'INVALID_OR_EMPTY_CLAIMS','requested':{'question_scope':'source_content'},
        'claim_bindings':[], 'binding_rejections':[]})
    expected = AskResponse(status='answered', answer='Exact source declaration')
    with patch('app.modules.rag.evidence_runtime.resolve_evidence_request', AsyncMock(return_value=(req,EvidencePolicy(enabled=False)))), \
         patch('app.modules.rag.score_conversion_chat.maybe_convert_score', AsyncMock(return_value=None)), \
         patch('app.modules.rag.evidence_pipeline.answer_with_evidence', AsyncMock(return_value=missing)), \
         patch('app.modules.rag.prose_fallback.answer_from_prose', AsyncMock(return_value=expected)) as recover:
        result = await RagService()._ask(AsyncMock(), req, candidate_snapshot=snap)
    assert result.answer == expected.answer
    recover.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('problem', ['explicit_policy', 'partial', 'binding_rejection', 'wrong_scope', 'expired'])
async def test_source_recovery_never_overrides_existing_safety_decisions(problem):
    from app.modules.rag.prose_fallback import recover_empty_source_read

    req = AskRequest(question='Read source.', collection_id='c')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', knowledge_wiki_enabled=True)
    decision = {'status':'missing','reason':'INVALID_OR_EMPTY_CLAIMS',
                'requested':{'question_scope':'source_content'},'binding_rejections':[]}
    if problem == 'partial':
        decision['status'] = 'partial'
    if problem == 'binding_rejection':
        decision['binding_rejections'] = [{'reason':'source mismatch'}]
    if problem == 'wrong_scope':
        decision['requested']['question_scope'] = 'applicability'
    response = AskResponse(status='insufficient_context', answer='Preserved', answer_decision=decision)
    started = time.perf_counter() - (1000 if problem == 'expired' else 0)
    with patch('app.modules.rag.prose_fallback.answer_from_prose', AsyncMock()) as recover:
        result = await recover_empty_source_read(None, req, snap, EvidencePolicy(enabled=problem=='explicit_policy'),
            response, started=started, candidate_mode=True)
    assert result is response
    recover.assert_not_awaited()
