"""Scope coverage and Boolean predicates must survive the routing boundary."""
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.rag.conversation_resolution import (
    FollowupResolution,
    _valid_contextual_query,
    resolve_followup,
)
from app.modules.rag.conversation_router import route_turn
from app.modules.rag.intent_contracts import ContextReferent
from app.modules.rag.schemas import AskRequest


def proposal(question, refs):
    return FollowupResolution(mode='followup', intent='KNOWLEDGE_FOLLOWUP', antecedent_id=0,
        question=question, referents=[ContextReferent(field=field, value=value, source_turn=turn,
            quote=value) for field, value, turn in refs])


BASE = 'Học phí ngành Delta tại trường Sigma trong tài liệu Atlas, Bảng 4 năm 2030?'
REFS = [('program', 'Delta', 0), ('institution', 'Sigma', 0),
        ('source_locator', 'Bảng 4', 0), ('calendar_year', '2030', 0)]


@pytest.mark.parametrize('old,current,query,refs', [
    (['Học phí ngành Delta năm 2030?'], 'Còn thời gian đào tạo?',
     'Thời gian đào tạo ngành Epsilon năm 2030?', [('calendar_year', '2030', 0)]),
    (['Học phí ngành Delta năm 2030?'], 'Còn thời gian đào tạo?',
     'Thời gian đào tạo ngành Delta năm 2030?', [('calendar_year', '2030', 0)]),
    (['Học phí ngành Delta tại trường Sigma năm 2030?'], 'Còn học phí?',
     'Học phí ngành Delta tại trường Tau năm 2030?', REFS[:1] + REFS[-1:]),
    (['Học phí ngành Delta tại trường Sigma năm 2030?'], 'Còn học phí?',
     'Học phí ngành Delta năm 2030?', REFS[:1] + REFS[-1:]),
    (['Trong tài liệu Atlas, Bảng 4: học phí ngành Delta năm 2030?'], 'Còn học phí?',
     'Trong tài liệu Boreal, Bảng 4: học phí ngành Delta năm 2030?', REFS[:1] + REFS[2:]),
    (['Trong Bảng 4: học phí ngành Delta năm 2030?'], 'Còn học phí?',
     'Học phí ngành Delta năm 2030?', REFS[:1] + REFS[-1:]),
    (['Học phí ngành Delta năm 2030?', 'Học phí ngành Epsilon năm 2030?'], 'Còn học phí?',
     'Học phí ngành Delta năm 2030?', REFS[:1] + REFS[-1:]),
    (['Học phí ngành Delta năm 2030?'], 'Còn học phí, không tính nhóm A?',
     'Học phí ngành Delta năm 2030, không tính nhóm B?', REFS[:1] + REFS[-1:]),
    (['Học phí ngành Delta năm 2030, chỉ hệ chính quy và không tính cơ sở X?'], 'Còn số SV ghi nhận?',
     'Số SV ghi nhận ngành Delta năm 2030?', REFS[:1] + REFS[-1:]),
    (['Học phí ngành Delta năm 2030, chỉ hệ chính quy?', 'Còn năm 2031?'], 'Còn số SV ghi nhận?',
     'Số SV ghi nhận ngành Delta năm 2031?', [('program', 'Delta', 0), ('calendar_year', '2031', 1)]),
    (['Học phí ngành Delta năm 2030 nếu thuộc nhóm A và nhóm B?'], 'Còn học phí?',
     'Học phí ngành Delta năm 2030 nếu thuộc nhóm A hoặc nhóm B?', REFS[:1] + REFS[-1:]),
    (['Học phí ngành Delta năm 2030 nếu không thuộc nhóm A?'], 'Còn học phí?',
     'Học phí ngành Delta năm 2030 nếu thuộc nhóm A?', REFS[:1] + REFS[-1:]),
    (['Học phí ngành Delta năm 2030, không tính nhóm A?'], 'Còn học phí?',
     'Học phí ngành Delta năm 2030, không tính nhóm Alphabet?', REFS[:1] + REFS[-1:]),
    (['Tuition for program Delta in 2030, excluding campus X?'], 'What about tuition?',
     'Tuition for program Delta in 2030, excluding campus Y?', REFS[:1] + REFS[-1:]),
], ids=['invented-subject', 'omitted-proof', 'changed-institution', 'omitted-institution',
        'changed-source', 'omitted-locator', 'stale-subject', 'swapped-exclusion',
        'lost-inherited-filters', 'lost-multiturn-filter', 'changed-and-or',
        'lost-nested-negation', 'substring-target', 'english-exclusion'])
def test_unproven_scope_is_rejected(old, current, query, refs):
    assert not _valid_contextual_query(proposal(query, refs), current, old)


@pytest.mark.parametrize('condition', [
    'chỉ hệ chính quy và không tính cơ sở X',
    'nếu thuộc nhóm A hoặc nhóm B',
    'nếu không thuộc nhóm A',
    'ngoại trừ nhóm A và nhóm B',
    'không phải không tính nhóm A',
    'chỉ tính khi điểm lớn hơn 10',
])
def test_complete_predicates_can_be_inherited_verbatim(condition):
    old = [f'Học phí ngành Delta năm 2030, {condition}?']
    query = f'Số SV ghi nhận ngành Delta năm 2030, {condition}?'
    assert _valid_contextual_query(proposal(query, REFS[:1] + REFS[-1:]), 'Còn số SV ghi nhận?', old)


@pytest.mark.asyncio
async def test_invalid_scope_never_becomes_a_retrieval_request_after_repair():
    old = 'Học phí ngành Delta năm 2030, chỉ hệ chính quy và không tính cơ sở X?'
    current = 'Còn số SV ghi nhận?'
    req = AskRequest(question=current, collection_id='fixture', assistant_code='fixture',
        history=[{'role': 'user', 'content': old},
                 {'role': 'assistant', 'content': 'Untrusted: ngành Epsilon, không tính cơ sở Y.'}])
    bad = proposal('Số SV ghi nhận ngành Delta năm 2030?', REFS[:1] + REFS[-1:])
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock(return_value=bad)) as model:
        effective, resolution, direct = await route_turn(AsyncMock(), req)
    assert resolution == {'mode': 'clarify', 'reason': 'CONTEXT_SCOPE_UNPROVEN'}
    assert not req._intent_trace['requires_rag'] and effective.question == current and direct is None
    assert model.await_count == 2


@pytest.mark.asyncio
async def test_repair_restores_complete_scope_using_only_user_turns():
    old = 'Học phí ngành Delta năm 2030, chỉ hệ chính quy và không tính cơ sở X?'
    req = AskRequest(question='Còn số SV ghi nhận?', collection_id='fixture', assistant_code='fixture',
        history=[{'role': 'user', 'content': old}])
    bad = proposal('Số SV ghi nhận ngành Delta năm 2030?', REFS[:1] + REFS[-1:])
    good = bad.model_copy(update={'question': 'Số SV ghi nhận ngành Delta năm 2030, chỉ hệ chính quy và không tính cơ sở X?'})
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock(side_effect=[bad, good])) as model:
        effective, resolution, _ = await route_turn(AsyncMock(), req)
    assert resolution['mode'] == 'followup' and good.question in effective.question
    assert model.await_count == 2 and req._intent_trace['reference_repair']['accepted']
    assert 'CONDITION_NOT_PRESERVED' in str(req._intent_trace['reference_repair']['initial_issues'])


@pytest.mark.parametrize('current,query', [
    ('Còn học phí? Bỏ điều kiện "không tính cơ sở X".', 'Học phí ngành Delta năm 2030?'),
    ('Còn học phí? Thay điều kiện "không tính cơ sở X" bằng "không tính cơ sở Y".',
     'Học phí ngành Delta năm 2030, không tính cơ sở Y?'),
    ('Còn học phí? Bỏ điều kiện "chỉ tính khi điểm lớn hơn 10".', 'Học phí ngành Delta năm 2030?'),
])
def test_explicit_literal_condition_edits_are_allowed(current, query):
    condition = 'chỉ tính khi điểm lớn hơn 10' if '10' in current else 'không tính cơ sở X'
    old = [f'Học phí ngành Delta năm 2030, {condition}?']
    assert _valid_contextual_query(proposal(query, REFS[:1] + REFS[-1:]), current, old)


@pytest.mark.parametrize('current', [
    'Còn học phí? Bỏ điều kiện "không tính cơ sở Y".',
    'Còn học phí? Thay điều kiện "không tính cơ sở X".',
    'Còn học phí? Bỏ điều kiện "không tính cơ sở X" bằng "không tính cơ sở Y".',
    'Còn học phí? Bỏ điều kiện đó.',
])
def test_ambiguous_or_unproven_condition_removal_clarifies(current):
    old = ['Học phí ngành Delta năm 2030, không tính cơ sở X?']
    assert not _valid_contextual_query(proposal('Học phí ngành Delta năm 2030?', REFS[:1] + REFS[-1:]), current, old)


@pytest.mark.parametrize('condition', [
    'đối với nhóm A', 'áp dụng cho hệ Z', 'từ ngày 10/01/2030',
    'đến ngày 20/12/2030', 'tối thiểu 10 SV', 'subject to condition X',
])
def test_non_negative_predicates_cannot_disappear(condition):
    old = [f'Học phí ngành Delta năm 2030, {condition}?']
    assert not _valid_contextual_query(proposal('Học phí ngành Delta năm 2030?', REFS[:1] + REFS[-1:]),
        'Còn học phí?', old)


def test_same_locator_in_two_documents_needs_proof_from_active_document():
    old = ['Tài liệu Atlas, Bảng 4: học phí ngành Delta năm 2030?',
           'Tài liệu Boreal, Bảng 4: học phí ngành Delta năm 2030?']
    refs = [('source', 'Boreal', 1), ('program', 'Delta', 1),
            ('calendar_year', '2030', 1), ('source_locator', 'Bảng 4', 0)]
    query = 'Tài liệu Boreal, Bảng 4: học phí ngành Delta năm 2030?'
    assert not _valid_contextual_query(proposal(query, refs), 'Còn học phí?', old)
    refs[-1] = ('source_locator', 'Bảng 4', 1)
    assert _valid_contextual_query(proposal(query, refs), 'Còn học phí?', old)


def test_complete_quoted_document_title_and_scope_proof_are_preserved():
    old = ['Trong tài liệu "Learning in Context: Phase 4", Bảng 4: học phí ngành Delta năm 2030?']
    query = 'Trong tài liệu "Learning in Context: Phase 4", Bảng 4: số SV ghi nhận ngành Delta năm 2030?'
    refs = [*REFS[:1], *REFS[2:], ('source', 'Learning in Context: Phase 4', 0)]
    assert _valid_contextual_query(proposal(query, refs), 'Còn số SV ghi nhận?', old)


def test_later_year_turn_keeps_all_previous_conditions_without_using_assistant_prose():
    old = ['Học phí ngành Delta năm 2030, không tính cơ sở X?', 'Còn năm 2031?']
    refs = [('program', 'Delta', 0), ('calendar_year', '2031', 1)]
    query = 'Số SV ghi nhận ngành Delta năm 2031, không tính cơ sở X?'
    assert _valid_contextual_query(proposal(query, refs), 'Còn số SV ghi nhận?', old)


def test_prior_literal_removal_persists_into_later_metric_turn():
    old = ['Học phí ngành Delta năm 2030, không tính cơ sở X?',
           'Còn học phí? Bỏ điều kiện "không tính cơ sở X".']
    assert _valid_contextual_query(proposal('Số SV ghi nhận ngành Delta năm 2030?', REFS[:1] + REFS[-1:]),
        'Còn số SV ghi nhận?', old)


@pytest.mark.asyncio
async def test_explicit_removal_is_not_reintroduced_into_the_retrieval_query():
    old = 'Học phí ngành Delta năm 2030, không tính cơ sở X?'
    current = 'Còn học phí? Bỏ điều kiện "không tính cơ sở X".'
    req = AskRequest(question=current, collection_id='fixture', assistant_code='fixture',
        history=[{'role': 'user', 'content': old}])
    good = proposal('Học phí ngành Delta năm 2030?', REFS[:1] + REFS[-1:])
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock(return_value=good)):
        effective, resolution, _ = await route_turn(AsyncMock(), req)
    assert resolution['mode'] == 'followup' and 'cơ sở X' not in effective.question
    assert req.question == current and resolution['current_question'] == current


@pytest.mark.asyncio
async def test_legacy_rewrite_cannot_bypass_named_scope_or_predicates():
    req = AskRequest(question='Thời gian đào tạo?', collection_id='fixture', assistant_code='fixture',
        history=[{'role': 'user', 'content': 'Học phí ngành Delta năm 2030, không tính cơ sở X?'}])
    bad = proposal('Thời gian đào tạo ngành Epsilon năm 2030?', [])
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock(return_value=bad)):
        effective, resolution = await resolve_followup(AsyncMock(), req)
    assert resolution == {'mode': 'clarify', 'reason': 'CONTEXT_SCOPE_UNPROVEN'}
    assert effective.question == req.question


def test_repeated_same_subject_does_not_silently_drop_its_code():
    old = ['Học phí ngành Delta mã UX-0405 năm 2030?', 'Học phí ngành Delta năm 2030?']
    refs = [('program', 'Delta', 1), ('calendar_year', '2030', 1)]
    assert not _valid_contextual_query(proposal('Học phí ngành Delta năm 2030?', refs), 'Còn học phí?', old)


@pytest.mark.asyncio
async def test_literal_year_shortcut_cannot_skip_a_later_condition_turn():
    req = AskRequest(question='Còn năm 2031?', collection_id='fixture', assistant_code='fixture',
        history=[{'role': 'user', 'content': 'Chỉ tiêu SV mã UX-0405 năm 2030?'},
                 {'role': 'user', 'content': 'Không tính cơ sở X.'}])
    bad = proposal('Chỉ tiêu SV mã UX-0405 năm 2031?',
        [('program_code', 'UX-0405', 0), ('calendar_year', '2031', -1)])
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock(return_value=bad)) as model:
        _, resolution, _ = await route_turn(AsyncMock(), req)
    assert resolution['mode'] == 'clarify' and model.await_count == 2
    assert not req._intent_trace.get('literal_year_change')


def test_separate_new_condition_preserves_the_inherited_exclusion():
    old = ['Học phí ngành Delta năm 2030, không tính cơ sở X?']
    query = 'Học phí ngành Delta năm 2030, không tính cơ sở X; nếu thuộc nhóm B?'
    assert _valid_contextual_query(proposal(query, REFS[:1] + REFS[-1:]), 'Còn học phí nếu thuộc nhóm B?', old)


def test_unproven_or_between_independent_conditions_is_rejected():
    old = ['Học phí ngành Delta năm 2030, không tính cơ sở X?']
    query = 'Học phí ngành Delta năm 2030, không tính cơ sở X hoặc nếu thuộc nhóm B?'
    assert not _valid_contextual_query(proposal(query, REFS[:1] + REFS[-1:]), 'Còn học phí nếu thuộc nhóm B?', old)


@pytest.mark.parametrize('command', [
    'Đừng bỏ điều kiện "không tính cơ sở X".',
    'Không bỏ điều kiện "không tính cơ sở X".',
    'Cụm từ "Bỏ điều kiện không tính cơ sở X" nghĩa là gì?',
])
def test_negated_or_quoted_removal_is_not_permission_to_drop_a_filter(command):
    old = ['Học phí ngành Delta năm 2030, không tính cơ sở X?']
    assert not _valid_contextual_query(proposal('Học phí ngành Delta năm 2030?', REFS[:1] + REFS[-1:]),
        'Còn học phí? ' + command, old)


def test_quoted_source_title_is_not_a_boolean_predicate():
    old = ['Tài liệu "Only Learning", Bảng 4: học phí ngành Delta năm 2030?']
    refs = [*REFS[:1], *REFS[2:], ('source', 'Only Learning', 0)]
    query = 'Tài liệu "Only Learning", Bảng 4: số SV ghi nhận ngành Delta năm 2030?'
    assert _valid_contextual_query(proposal(query, refs), 'Còn số SV ghi nhận?', old)


def test_shared_url_scheme_is_not_proof_of_document_identity():
    old = ['Tài liệu https://example.test/a.pdf: học phí ngành Delta năm 2030?']
    refs = [*REFS[:1], *REFS[-1:], ('source', 'https', 0)]
    query = 'Tài liệu https://other.test/b.pdf: học phí ngành Delta năm 2030?'
    assert not _valid_contextual_query(proposal(query, refs), 'Còn học phí?', old)


def test_complete_document_url_can_be_inherited():
    old = ['Tài liệu https://example.test/a.pdf: học phí ngành Delta năm 2030?']
    refs = [*REFS[:1], *REFS[-1:], ('source', 'https://example.test/a.pdf', 0)]
    query = 'Tài liệu https://example.test/a.pdf: học phí ngành Delta năm 2030?'
    assert _valid_contextual_query(proposal(query, refs), 'Còn học phí?', old)


@pytest.mark.parametrize('tail', ['hoặc nhóm B', 'or campus Y', 'và nhóm B', 'and campus Y'])
def test_unproven_boolean_tail_after_separator_is_rejected(tail):
    old = ['Học phí ngành Delta năm 2030, không tính cơ sở X?']
    query = f'Học phí ngành Delta năm 2030, không tính cơ sở X; {tail}?'
    assert not _valid_contextual_query(proposal(query, REFS[:1] + REFS[-1:]), 'Còn học phí?', old)


def test_original_boolean_expression_crossing_a_separator_is_preserved():
    old = ['Học phí ngành Delta năm 2030, nếu thuộc nhóm A; hoặc thuộc nhóm B?']
    good = 'Học phí ngành Delta năm 2030, nếu thuộc nhóm A; hoặc thuộc nhóm B?'
    bad = good.replace('; hoặc', '; và')
    assert _valid_contextual_query(proposal(good, REFS[:1] + REFS[-1:]), 'Còn học phí?', old)
    assert not _valid_contextual_query(proposal(bad, REFS[:1] + REFS[-1:]), 'Còn học phí?', old)
