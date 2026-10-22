"""Shared failure modes: navigation, limited cells, year scope and clause closure."""
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.core.exceptions import AppException
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


@pytest.mark.asyncio
async def test_reader_finishes_after_server_opens_exact_canonical_references():
    from app.modules.knowledge.wiki_schemas import WikiReadAction
    from app.modules.rag.wiki_context import read_wiki_context
    from tests.test_wiki_navigation import block, page

    req = AskRequest(collection_id='c', question='Source rule?')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', knowledge_wiki_enabled=True)
    call = AsyncMock(side_effect=[WikiReadAction(action='read_pages', page_ids=['page-a']),
                                 AssertionError('Unnecessary second navigation call')])
    with patch('app.modules.rag.wiki_context.load_wiki_pages', AsyncMock(return_value=[page()])), \
         patch('app.modules.rag.wiki_context.structured_call', call):
        result = await read_wiki_context(None, req, snap, QueryPlan(query=req.question), [block()], candidate_mode=True)
    assert result == [block()] and call.await_count == 1
    assert req._retrieval_diagnostics['knowledge_wiki']['calls'] == 1


@pytest.mark.asyncio
async def test_reader_repairs_shape_within_same_total_call_budget_and_records_attempt():
    from app.modules.rag.wiki_context import read_wiki_context
    from tests.test_wiki_navigation import block, page

    req = AskRequest(collection_id='c', question='Source rule?')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', knowledge_wiki_enabled=True)
    invalid = AppException('Invalid shape', code='KNOWLEDGE_WIKI_READ_INVALID', status_code=502,
        details={'validation_errors': [{'field': ['extra'], 'type': 'extra_forbidden'}]})
    from app.modules.knowledge.wiki_schemas import WikiReadAction
    call = AsyncMock(side_effect=[invalid, WikiReadAction(action='read_pages', page_ids=['page-a'])])
    with patch('app.modules.rag.wiki_context.load_wiki_pages', AsyncMock(return_value=[page()])), \
         patch('app.modules.rag.wiki_context.structured_call', call):
        result = await read_wiki_context(None, req, snap, QueryPlan(query=req.question), [block()], candidate_mode=True)
    assert result == [block()] and call.await_count == 2
    assert req._retrieval_diagnostics['knowledge_wiki']['calls'] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('code', ['ALL_PROVIDERS_UNAVAILABLE', 'KNOWLEDGE_WIKI_READ_SCOPE'])
async def test_reader_does_not_repair_provider_or_scope_errors(code):
    from app.modules.rag.wiki_context import read_wiki_context
    from tests.test_wiki_navigation import block, page

    req = AskRequest(collection_id='c', question='Source rule?')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', knowledge_wiki_enabled=True)
    failure = AppException('Failure', code=code, status_code=502)
    call = AsyncMock(side_effect=failure)
    with patch('app.modules.rag.wiki_context.load_wiki_pages', AsyncMock(return_value=[page()])), \
         patch('app.modules.rag.wiki_context.structured_call', call), pytest.raises(AppException) as caught:
        await read_wiki_context(None, req, snap, QueryPlan(query=req.question), [block()], candidate_mode=True)
    assert caught.value is failure and call.await_count == 1
    assert req._retrieval_diagnostics['knowledge_wiki']['calls'] == 1


@pytest.mark.asyncio
async def test_failed_model_contract_call_keeps_safe_diagnostics_without_prompt():
    from app.modules.knowledge.wiki_schemas import WikiReadAction
    from app.modules.rag.evidence_model import structured_call

    req = AskRequest(collection_id='c', question='private question')
    failure = AppException('private upstream body', code='MODEL_OUTPUT_BUDGET_EXHAUSTED', status_code=502)
    with patch('app.modules.rag.evidence_model.modelops_service.generate', AsyncMock(side_effect=failure)), \
         pytest.raises(AppException):
        await structured_call(None, req, WikiReadAction, 'private prompt', {'private': 'private data'}, max_tokens=600)
    trace = req._retrieval_diagnostics['model_contract_calls']
    assert trace[0]['error_code'] == failure.code and trace[0]['stage'] == 'WikiReadAction'
    assert 'private' not in json.dumps(trace)


@pytest.mark.parametrize('state', ['ambiguous', 'unreadable'])
def test_limited_cell_is_catalogued_but_cannot_become_quantitative_evidence(state):
    from app.modules.rag.row_answer_contract import RowSelection, build_catalog, validate_selection
    from tests.test_row_answer_contract import context

    rows, req, snap = context()
    row = rows[0]
    from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
    values = _split_gfm_row(row.metadata['source_unit']['text'])
    headers = _split_gfm_row(row.metadata['source_unit']['header_context'].splitlines()[0])
    row.metadata.update(cell_state_source='declared', row_columns=[{'header_path': [h]} for h in headers],
        row_fields=[{'raw': value, 'state': state if column == 3 else 'present', 'column_index': column,
                     'column_id': str(column), 'header_path': [headers[column]]} for column, value in enumerate(values)])
    catalog = build_catalog([row], snap, req.question, allow_descriptive=True)
    limited = next(key for key, cell in catalog.cells.items() if cell.state == state)
    with pytest.raises(ValueError):
        validate_selection(RowSelection(status='selected', cell_ids=[limited]), catalog, req.question)
    assert any(cell.state == 'present' for cell in catalog.cells.values())


@pytest.mark.asyncio
@pytest.mark.parametrize('question_scope,expected_reads', [('source_content', 1), ('applicability', 0)])
async def test_year_clarification_depends_on_question_scope_without_assuming_year(question_scope, expected_reads):
    from app.modules.rag import evidence_pipeline as pipeline

    plan = QueryPlan(query='Compare source thresholds.', requires_year=True, question_scope=question_scope)
    req = AskRequest(collection_id='c', question=plan.query)
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c')
    read = AsyncMock(return_value=[])
    with patch.object(pipeline, 'reference_year', return_value=None), \
         patch.object(pipeline, 'resolve_institution_scope', AsyncMock(return_value=None)), \
         patch.object(pipeline, 'structured_call', AsyncMock(return_value=plan)), \
         patch('app.modules.rag.glossary_expansion.resolve_glossary_queries', AsyncMock(return_value=([], {}))), \
         patch.object(pipeline, 'select_context', read):
        result = await pipeline._answer(None, req, snap, EvidencePolicy(), time.perf_counter(), True)
    assert read.await_count == expected_reads
    assert result.answer_decision['reason'] == ('NO_COMPATIBLE_EVIDENCE' if expected_reads else 'YEAR_REQUIRED')
    assert result.answer_decision['requested']['years'] == []


@pytest.mark.parametrize('text', [
    'Không áp dụng cho dữ liệu của 2031 và 2032.',
    'Không áp dụng cho dữ liệu của 2031 and 2032.',
    'Không áp dụng cho dữ liệu của 2031 và\n2032.',
    'Không áp dụng cho dữ liệu của 2031 và năm 2032.',
])
def test_coordinated_years_keep_their_negation_and_subject(text):
    from app.modules.rag.source_scope_audit import source_clauses

    assert list(source_clauses({'e': text}).values()) == [text]


@pytest.mark.asyncio
@pytest.mark.parametrize('resolved', [False, True])
async def test_late_source_condition_is_restored_and_independently_reverified(resolved):
    from app.modules.rag.evidence_schemas import QuoteReference
    from app.modules.rag.prose_fallback import answer_from_prose
    from tests.test_source_answer_scope_575 import block, bound

    b = block('rule', 'Chỉ được gia hạn khi có văn bản. Không áp dụng sang nhóm khác.', parent='rule-owner')
    claim = bound(b, 'Chỉ được gia hạn khi có văn bản.')
    def verified(complete=False, conditions=None, qualifiers=None):
        return SimpleNamespace(complete=complete, claims=[claim], missing=[] if complete else ['missing condition'],
            errors=[], verifier=SimpleNamespace(conflict=False, topic_coverage={'requested': True}, complete=True,
            model_dump=dict), audit=SimpleNamespace(complete=complete),
            source_condition_gaps=conditions or {}, source_qualifier_gaps=qualifiers or [])
    verifications = AsyncMock(side_effect=[
        verified(qualifiers=[QuoteReference(block_id=b.id, quote='Chỉ được gia hạn khi có văn bản.')]),
        verified(conditions={'e1.c1': 'Không áp dụng sang nhóm khác.'}), verified(resolved)])
    req = AskRequest(question='Quy định gia hạn có phạm vi nào?', collection_id='c', reranker_policy={'enabled': False})
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b': 'i'})
    with patch('app.modules.rag.prose_fallback.load_published_blocks', AsyncMock(return_value=[b])), \
         patch('app.modules.rag.prose_fallback.recovery_plan', AsyncMock(return_value=QueryPlan(query=req.question, requested_topics=['requested']))), \
         patch('app.modules.rag.prose_fallback.propose_bound_claims', AsyncMock(return_value=(SimpleNamespace(status='supported'), [claim], [], False))), \
         patch('app.modules.rag.prose_fallback.verify_bound_answer', verifications):
        response = await answer_from_prose(None, req, snap, EvidencePolicy(), 'ROW_RULE_REQUIRES_CONTEXT')
    assert (response is not None and response.status == 'answered') if resolved else response is None
    assert verifications.await_count == 3
    last_claims = verifications.await_args.args[3]
    assert any('Không áp dụng sang nhóm khác.' in c['text'] for c in last_claims)


@pytest.mark.parametrize('action', [
    {'action': 'done', 'page_ids': ['page-a']},
    {'action': 'read_pages', 'page_ids': []},
    {'action': 'read_pages', 'page_ids': ['page-a'], 'unit_ids': ['foreign']},
    {'action': 'search', 'query': ''},
])
def test_navigation_arguments_cannot_be_silently_ignored(action):
    from pydantic import ValidationError

    from app.modules.knowledge.wiki_schemas import WikiReadAction

    with pytest.raises(ValidationError):
        WikiReadAction.model_validate(action)


@pytest.mark.asyncio
async def test_repeated_invalid_navigation_stops_at_original_budget():
    from app.modules.rag.wiki_context import read_wiki_context
    from tests.test_wiki_navigation import block, page

    req = AskRequest(collection_id='c', question='Source rule?')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', knowledge_wiki_enabled=True)
    call = AsyncMock(side_effect=AppException('Bad shape', code='KNOWLEDGE_WIKI_READ_INVALID', status_code=502))
    with patch('app.modules.rag.wiki_context.load_wiki_pages', AsyncMock(return_value=[page()])), \
         patch('app.modules.rag.wiki_context.structured_call', call), pytest.raises(AppException):
        await read_wiki_context(None, req, snap, QueryPlan(query=req.question), [block()], candidate_mode=True)
    assert call.await_count == req._retrieval_diagnostics['knowledge_wiki']['calls'] == 2
    assert not req._wiki_context


@pytest.mark.asyncio
async def test_descriptive_row_route_reads_legend_while_strict_consumers_still_reject():
    from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import build_catalog
    from tests.test_row_answer_contract import context

    rows, req, snap = context()
    row = rows[0]
    values = _split_gfm_row(row.metadata['source_unit']['text'])
    headers = _split_gfm_row(row.metadata['source_unit']['header_context'].splitlines()[0])
    row.metadata.update(cell_state_source='declared', row_columns=[{'header_path': [h]} for h in headers],
        row_fields=[{'raw': value, 'state': 'ambiguous' if col == 3 else 'present',
                     'column_index': col, 'header_path': [headers[col]]} for col, value in enumerate(values)])
    with pytest.raises(AppException):
        build_catalog([row], snap, req.question)
    with patch('app.modules.rag.row_answer._metric_payload', AsyncMock(return_value={'answer_mode':'rules'})):
        result = await answer_from_rows(None, req, snap, [row])
    assert result.answer_decision['reason'] == 'ROW_RULE_REQUIRES_CONTEXT' and result.citations == []
    row.metadata['row_fields'][3]['raw'] = '999'
    with pytest.raises(AppException):
        build_catalog([row], snap, req.question, allow_descriptive=True)
