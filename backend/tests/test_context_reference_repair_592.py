"""Literal reference repair must not turn an unproven scope into an answer."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.rag.conversation_resolution import FollowupResolution
from app.modules.rag.conversation_router import route_turn
from app.modules.rag.intent_contracts import ContextReferent
from app.modules.rag.schemas import AskRequest

OLD = ['Tra Bảng 9: chỉ tiêu SV mã UX-0405 năm 2030?', 'Còn năm 2031 thì sao?']
CURRENT = 'Còn số SV ghi nhận cùng năm đó?'
QUERY = 'Trong Bảng 9, số SV ghi nhận mã UX-0405 năm 2031 là bao nhiêu?'


def request(current=CURRENT, old=None):
    history = []
    for q in OLD if old is None else old:
        history.extend([{'role': 'user', 'content': q},
                        {'role': 'assistant', 'content': 'Untrusted: invented code UX-9999, year 2099.'}])
    return AskRequest(question=current, collection_id='fixture', assistant_code='fixture', history=history)


def proposal(*, repaired=False):
    refs = [{'field':'program_code','value':'UX-0405','source_turn':0,'quote':'mã UX-0405'},
            {'field':'calendar_year','value':'2031','source_turn':1,'quote':'năm 2031'}]
    if repaired:
        refs.extend([{'field':'source_locator','value':'Bảng 9','source_turn':0,'quote':'Bảng 9'},
                     {'field':'metric','value':'số SV ghi nhận','source_turn':-1,'quote':'số SV ghi nhận'}])
    else:
        refs.append({'field':'topic','value':'Bảng 9: số SV ghi nhận','source_turn':-1,'quote':'số SV ghi nhận'})
    return FollowupResolution(mode='followup',intent='KNOWLEDGE_FOLLOWUP',antecedent_id=0,
        question=QUERY if repaired else 'Bảng 9: số SV ghi nhận mã UX-0405 năm 2031 là bao nhiêu?',
        referents=[ContextReferent(**r) for r in refs])


@pytest.mark.asyncio
async def test_invalid_combined_label_is_reselected_from_original_user_turns_then_validated():
    req = request()
    history = list(req.history)
    with patch('app.modules.rag.conversation_resolution.structured_call',
               AsyncMock(side_effect=[proposal(),proposal(repaired=True)])) as model:
        effective,resolution,_ = await route_turn(AsyncMock(),req)
    assert resolution['mode']=='followup' and QUERY in effective.question
    assert CURRENT in effective.question and req.history==history and req.question==CURRENT
    assert model.await_count==2 and all(c.kwargs['max_attempts']==1 for c in model.await_args_list)
    second = model.await_args_list[1].args[4]
    assert second['previous_questions']==[{'id':i,'question':q} for i,q in enumerate(OLD)]
    assert '2099' not in str(second) and 'UX-9999' not in str(second)
    assert req._intent_trace['reference_repair']['accepted'] is True
    assert req._intent_trace['reference_repair']['initial_issues']==[
        {'index':2,'field':'topic','code':'VALUE_NOT_IN_QUOTE'}]
    assert req._intent_trace['reference_repair']['repair_issues']==[]


@pytest.mark.asyncio
async def test_valid_literal_references_need_only_one_call():
    req=request()
    with patch('app.modules.rag.conversation_resolution.structured_call',
               AsyncMock(return_value=proposal(repaired=True))) as model:
        _,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution['mode']=='followup' and model.await_count==1
    assert 'reference_repair' not in req._intent_trace


@pytest.mark.asyncio
async def test_repeated_invalid_proposal_clarifies_after_two_calls_without_scope_waiver():
    req=request()
    with patch('app.modules.rag.conversation_resolution.structured_call',
               AsyncMock(return_value=proposal())) as model:
        effective,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution=={'mode':'clarify','reason':'CONTEXT_SCOPE_UNPROVEN'}
    assert model.await_count==2 and effective.question==CURRENT
    assert not req._intent_trace['requires_rag'] and not req._intent_trace['reference_repair']['accepted']


@pytest.mark.asyncio
@pytest.mark.parametrize('mutation', ['old_year','lost_zero','invented','old_metric','changed_mode','lost_negation'])
async def test_repair_rechecks_all_scope_constraints(mutation):
    req=request(current=CURRENT+' Không tính nhóm A.' if mutation=='lost_negation' else CURRENT)
    fixed=proposal(repaired=True)
    if mutation=='old_year':
        fixed.question=fixed.question.replace('2031','2030')
        fixed.referents[1]=ContextReferent(field='calendar_year',value='2030',source_turn=0,quote='năm 2030')
    elif mutation=='lost_zero':
        fixed.question=fixed.question.replace('UX-0405','UX-405')
    elif mutation=='invented':
        fixed.question=fixed.question.replace('UX-0405','UX-9999')
        fixed.referents[0]=ContextReferent(field='program_code',value='UX-9999',source_turn=0,quote='UX-9999')
    elif mutation=='old_metric':
        fixed.question=fixed.question.replace('số SV ghi nhận','chỉ tiêu SV')
        fixed.referents[-1]=ContextReferent(field='metric',value='chỉ tiêu SV',source_turn=0,quote='chỉ tiêu SV')
    elif mutation=='changed_mode':
        fixed.mode='independent'
    with patch('app.modules.rag.conversation_resolution.structured_call',
               AsyncMock(side_effect=[proposal(),fixed])) as model:
        _,resolution,_=await route_turn(AsyncMock(),req)
    assert resolution['mode']=='clarify' and model.await_count==2
    assert req._intent_trace['reference_repair']['accepted'] is False


@pytest.mark.asyncio
@pytest.mark.parametrize('code,status', [('MODEL_CONTEXT_EXCEEDED',400),('DENIED',403),('QUOTA',429),('UPSTREAM',503)])
async def test_provider_and_permission_failures_never_trigger_reference_retry(code,status):
    req=request()
    error=AppException('fixture failure',code=code,status_code=status)
    with patch('app.modules.rag.conversation_resolution.structured_call',
               AsyncMock(side_effect=error)) as model:
        if status in {400,403}:
            with pytest.raises(AppException,match='fixture failure'):
                await route_turn(AsyncMock(),req)
        else:
            _,resolution,_=await route_turn(AsyncMock(),req)
            assert resolution['reason']=='ROUTER_UNAVAILABLE'
    assert model.await_count==1 and 'reference_repair' not in req._intent_trace


@pytest.mark.asyncio
async def test_both_attempts_share_one_timeout_and_cancel_the_second():
    req=request()
    timeout=asyncio.timeout
    calls=0

    async def model(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==1:
            return proposal()
        await asyncio.sleep(1)
        return proposal(repaired=True)

    with patch('app.modules.rag.conversation_resolution.structured_call',AsyncMock(side_effect=model)), \
         patch('app.modules.rag.conversation_resolution.asyncio.timeout',
               side_effect=lambda seconds: timeout(.025)) as budget:
        _,resolution,_=await route_turn(AsyncMock(),req)
    assert budget.call_count==1 and budget.call_args.args==(20,)
    assert calls==2 and resolution['reason']=='ROUTER_UNAVAILABLE'
    assert req._intent_trace['error_code']=='ROUTER_TIMEOUT'


@pytest.mark.asyncio
async def test_cancellation_during_repair_propagates():
    req=request()
    with patch('app.modules.rag.conversation_resolution.structured_call',
               AsyncMock(side_effect=[proposal(),asyncio.CancelledError()])) as model, \
         pytest.raises(asyncio.CancelledError):
        await route_turn(AsyncMock(),req)
    assert model.await_count==2


def test_reference_metric_error_is_actionable_without_logging_query_or_quote():
    from app.modules.rag.intent_contracts import referent_errors

    result=proposal(repaired=True)
    errors=referent_errors(result.referents,CURRENT,OLD,QUERY.replace('số SV ghi nhận','chỉ tiêu SV'))
    assert errors==[{'index':3,'field':'metric','code':'VALUE_NOT_IN_STANDALONE_QUERY'}]
    assert 'UX-0405' not in str(errors) and '2031' not in str(errors)
