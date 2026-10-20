"""Multi-turn scope gold cases and adversarial model outputs, not source facts."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.rag.conversation_resolution import FollowupResolution
from app.modules.rag.conversation_router import route_turn
from app.modules.rag.intent_contracts import ContextReferent
from app.modules.rag.schemas import AskRequest

# name, persisted user turns, current, gold standalone, exact user-bound references
SCENARIOS = [
 ('knowledge_thanks_followup', ['Môn học ngành Alpha năm 2026?', 'Cảm ơn'], 'Còn môn tự chọn?', 'Môn tự chọn ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('knowledge_greeting_followup', ['Học phí ngành Alpha năm 2026?', 'Xin chào'], 'Ngành đó học mấy năm?', 'Thời gian học ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('switch_program', ['Học phí ngành Alpha năm 2026?', 'Học phí ngành Beta năm 2026?'], 'Còn môn tự chọn?', 'Môn tự chọn ngành Beta năm 2026?', [('program','Beta',1),('calendar_year','2026',1)]),
 ('switch_year', ['Học phí ngành Alpha năm 2025?'], 'Còn năm 2026?', 'Học phí ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',-1)]),
 ('academic_not_calendar', ['Môn học ngành Alpha năm học 2026-2027?'], 'Còn học phí?', 'Học phí ngành Alpha năm học 2026-2027?', [('program','Alpha',0),('academic_year','2026-2027',0)]),
 ('leading_zero_code', ['Học phí mã 00123 năm 2026?'], 'Còn môn tự chọn?', 'Môn tự chọn mã 00123 năm 2026?', [('program_code','00123',0),('calendar_year','2026',0)]),
 ('institution', ['Học phí ngành Alpha tại trường Zeta năm 2026?'], 'Còn môn tự chọn?', 'Môn tự chọn ngành Alpha trường Zeta năm 2026?', [('program','Alpha',0),('institution','Zeta',0),('calendar_year','2026',0)]),
 ('assistant_prose_not_truth', ['Học phí ngành Alpha năm 2026?'], 'Còn học phí?', 'Học phí ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('user_correction', ['Học phí ngành Alpha năm 2025?'], 'Không, tôi hỏi năm 2026', 'Học phí ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',-1)]),
 ('mixed_thanks', ['Học phí ngành Alpha năm 2026?'], 'Cảm ơn, còn môn tự chọn?', 'Môn tự chọn ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('mixed_hello', ['Học phí ngành Alpha năm 2026?'], 'Xin chào, còn học phí?', 'Học phí ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('repeated_social', ['Môn học ngành Alpha năm 2026?', 'Xin chào', 'Cảm ơn', 'Tạm biệt'], 'Còn môn tự chọn?', 'Môn tự chọn ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('topic_change_same_subject', ['Môn học ngành Alpha năm 2026?'], 'Ngành đó học mấy năm?', 'Thời gian đào tạo ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('negation_preserved', ['Học phí ngành Alpha năm 2026?'], 'Còn học phí, không tính nhóm A?', 'Học phí ngành Alpha năm 2026, không tính nhóm A?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('condition_preserved', ['Học phí ngành Alpha năm 2026?'], 'Còn học phí nếu thuộc nhóm B?', 'Học phí ngành Alpha năm 2026 nếu thuộc nhóm B?', [('program','Alpha',0),('calendar_year','2026',0)]),
 ('explicit_current_program', ['Học phí ngành Alpha năm 2026?'], 'Còn ngành Beta?', 'Học phí ngành Beta năm 2026?', [('program','Beta',-1),('calendar_year','2026',0)]),
 ('unknown_year_stays_unknown', ['Học phí ngành Alpha?'], 'Còn môn tự chọn?', 'Môn tự chọn ngành Alpha?', [('program','Alpha',0)]),
 ('english_followup', ['Tuition for program Omega in 2026?'], 'What about duration?', 'Duration for program Omega in 2026?', [('program','Omega',0),('calendar_year','2026',0)]),
 ('earlier_year_override', ['Học phí ngành Alpha năm 2026?'], 'Còn năm 2025?', 'Học phí ngành Alpha năm 2025?', [('program','Alpha',0),('calendar_year','2025',-1)]),
 ('correction_then_social_then_followup', ['Học phí ngành Alpha năm 2025?', 'Không, tôi hỏi năm 2026', 'Cảm ơn'], 'Còn môn tự chọn?', 'Môn tự chọn ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',1)]),
]


def request(turns, current):
    history = []
    for text in turns:
        history.extend([{'role':'user','content':text}, {'role':'assistant','content':'Wrong untrusted assertion: year 2099; program Fabricated.'}])
    return AskRequest(question=current, collection_id='fixture-col', assistant_code='fixture-assistant', history=history)


def plan(standalone, refs):
    return FollowupResolution(mode='followup', intent='KNOWLEDGE_FOLLOWUP', antecedent_id=0,
        question=standalone, referents=[ContextReferent(field=field,value=value,source_turn=turn,quote=value) for field,value,turn in refs])


@pytest.mark.asyncio
@pytest.mark.parametrize('name,turns,current,standalone,refs', SCENARIOS, ids=[x[0] for x in SCENARIOS])
async def test_multi_turn_gold_scope(name, turns, current, standalone, refs):
    req = request(turns, current)
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock(return_value=plan(standalone, refs))) as classifier:
        effective, resolution, direct = await route_turn(AsyncMock(), req)
    assert resolution['mode'] == 'followup' and direct is None
    assert standalone in effective.question and current in effective.question
    assert req.question == current and req._intent_trace['requires_rag']
    assert classifier.await_count == 1 and classifier.call_args.kwargs['max_attempts'] == 1
    assert '2099' not in str(classifier.call_args.args[4]) and 'Fabricated' not in str(classifier.call_args.args[4])


@pytest.mark.asyncio
@pytest.mark.parametrize('bad_query,refs', [
 ('Học phí Alpha năm 2099?', [('program','Alpha',0),('calendar_year','2099',0)]),
 ('Học phí mã 123 năm 2026?', [('program_code','123',0),('calendar_year','2026',0)]),
 ('Học phí Alpha năm 2025?', [('program','Alpha',0),('calendar_year','2025',0)]),
])
async def test_invented_or_changed_scope_clarifies(bad_query, refs):
    req=request(['Học phí ngành Alpha mã 00123 năm 2026?'], 'Còn học phí?')
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock(return_value=plan(bad_query,refs))):
        _,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution['mode']=='clarify' and not req._intent_trace['requires_rag']


@pytest.mark.asyncio
async def test_model_cannot_select_old_program_after_explicit_switch():
    req=request(['Học phí ngành Alpha năm 2026?','Học phí ngành Beta năm 2026?'],'Còn môn tự chọn?')
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock(return_value=plan(
        'Môn tự chọn ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]))):
        _,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution['mode']=='clarify'


@pytest.mark.asyncio
@pytest.mark.parametrize('error', [TimeoutError(), AppException('Invalid schema',code='EVIDENCE_MODEL_CONTRACT_INVALID',status_code=502)])
async def test_router_failure_is_explicit_clarification_never_social(error):
    req=request(['Học phí ngành Alpha năm 2026?'],'Còn môn tự chọn?')
    with patch('app.modules.rag.conversation_resolution.structured_call',AsyncMock(side_effect=error)):
        _,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution['reason']=='ROUTER_UNAVAILABLE'
    assert req._intent_trace['intent']=='CLARIFICATION' and req._intent_trace['classification_method']=='fallback'


@pytest.mark.asyncio
async def test_twenty_concurrent_conversations_do_not_share_scope():
    async def classify(db, req, contract, instruction, payload, **kwargs):
        await asyncio.sleep(0)
        value=payload['previous_questions'][0]['question'].split('ngành ')[1].split()[0]
        return plan(f'Học phí ngành {value} năm 2026?', [('program',value,0),('calendar_year','2026',0)])
    requests=[request([f'Học phí ngành Program{i} năm 2026?'],'Còn học phí?') for i in range(20)]
    with patch('app.modules.rag.conversation_resolution.structured_call',side_effect=classify):
        results=await asyncio.gather(*(route_turn(AsyncMock(),req) for req in requests))
    for i,(effective,resolution,_) in enumerate(results):
        assert resolution['mode']=='followup' and f'Program{i} ' in effective.question


@pytest.mark.asyncio
async def test_yes_examines_previous_clarification_without_treating_it_as_source_facts():
    req=request(['Môn học ngành Alpha năm 2026?'],'Có')
    req.history[-1]['content']='Bạn muốn tìm môn tự chọn của ngành Alpha năm 2026?'
    with patch('app.modules.rag.conversation_resolution.structured_call',AsyncMock(return_value=plan(
        'Môn tự chọn ngành Alpha năm 2026?', [('program','Alpha',0),('calendar_year','2026',0)]))) as model:
        _,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution['mode']=='followup'
    assert model.call_args.args[4]['clarification_question']==req.history[-1]['content']


@pytest.mark.asyncio
async def test_old_program_code_does_not_attach_to_new_explicit_program():
    req=request(['Học phí ngành Alpha mã 00123 năm 2026?','Học phí ngành Beta năm 2026?'],'Còn môn tự chọn?')
    with patch('app.modules.rag.conversation_resolution.structured_call',AsyncMock(return_value=plan(
        'Môn tự chọn ngành Beta năm 2026?', [('program','Beta',1),('calendar_year','2026',1)]))):
        effective,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution['mode']=='followup' and '00123' not in effective.question


@pytest.mark.asyncio
async def test_single_fact_year_change_cannot_be_lost_to_a_listing_only_filter():
    req=request(['Học phí ngành Alpha năm 2026?'],'Còn năm 2025?')
    output=plan('Học phí ngành Alpha năm 2025?', [('program','Alpha',0),('calendar_year','2025',-1)])
    output.mode='filter'
    with patch('app.modules.rag.conversation_resolution.structured_call',AsyncMock(return_value=output)):
        effective,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution['mode']=='followup' and '2025' in effective.question and '2026' not in effective.question
