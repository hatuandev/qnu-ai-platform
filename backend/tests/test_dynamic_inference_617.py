"""Exercise the ModelOps dispatcher, including leases, quota and exact fallback payload."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.providers.base import LLMResponse
from app.modules.modelops.schemas import LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.modelops.services import capacity_discovery, inference_service
from app.modules.modelops.services.provider_key_rotation_service import KeyAcquireResult


@pytest.fixture
def runtime(monkeypatch):
    configs={name:ModelProviderConfig(id=name,name='617-'+name,provider_type='custom',model_name=name,
        is_active=True,api_base_url='https://'+name+'.example/v1',timeout_seconds=30,extra_config={}) for name in ('primary','fallback')}
    providers=[{'id':c.id,'name':c.name,'provider_type':c.provider_type,'model_name':c.model_name,
        'models':[c.model_name],'api_base_url':c.api_base_url,'api_key':'test-protected-key',
        'timeout_seconds':30} for c in configs.values()]
    db=AsyncMock()
    async def execute(statement):
        provider=statement.compile().params['id_1']
        row=MagicMock();row.scalar_one_or_none.return_value=configs[provider]
        return row
    db.execute.side_effect=execute
    quota=AsyncMock()
    acquire=AsyncMock(return_value=KeyAcquireResult(False,None))
    monkeypatch.setattr(modelops_service,'check_quota_available',quota)
    monkeypatch.setattr(modelops_service,'get_active_providers',AsyncMock(return_value=providers))
    monkeypatch.setattr(modelops_service,'record_usage_log',AsyncMock())
    monkeypatch.setattr(modelops_service._inference,'_record_key_success',AsyncMock())
    monkeypatch.setattr(modelops_service._inference,'_record_key_failure',AsyncMock(return_value=None))
    monkeypatch.setattr(inference_service.provider_key_rotation_service,'acquire',acquire)
    monkeypatch.setattr(inference_service,'save_chat_capabilities',AsyncMock())
    monkeypatch.setattr(inference_service.circuit_breaker_registry,'get',lambda _:MagicMock())
    async def discover(config,model,db):
        return {'context_window_tokens':128000 if model=='primary' else 12000,'max_output_tokens':None,
            'tokenizer_encoding':'o200k_harmony','chat_overhead_tokens':2075,'basis':'provider_reported',
            'calibrated_roles':['system','user'],'capacity_verified_by_inference':False}
    discovery=AsyncMock(side_effect=discover)
    monkeypatch.setattr(capacity_discovery,'discover',discovery)
    calls=[]
    class Adapter:
        def __init__(self,model):self.model=model
        async def generate(self,**kwargs):
            calls.append((self.model,kwargs))
            if self.model=='primary' and state['fail_primary']:
                raise RuntimeError('Unavailable primary')
            return LLMResponse('Result','custom',self.model,2100,20,2120,finish_reason='stop')
    state={'fail_primary':False}
    monkeypatch.setattr('app.modules.modelops.service.get_llm_adapter',lambda **kw:Adapter(kw['model_name']))
    return db,calls,state,acquire,quota,discovery


def request(text='Synthetic request',**overrides):
    return LLMGenerateRequest(automatic_output_budget=True,preferred_provider_id='primary',preferred_model_name='primary',
        fallback_provider_id='fallback',fallback_model_name='fallback',
        messages=[{'role':'system','content':'Return a short answer.'},{'role':'user','content':text}],**overrides)


@pytest.mark.asyncio
async def test_primary_receives_its_own_dynamic_capacity_without_default_2000_or_fallback_ceiling(runtime):
    db,calls,_,acquire,_,discover=runtime
    result=await modelops_service.generate(db,request())
    assert len(calls)==1 and calls[0][0]=='primary'
    assert calls[0][1]['max_tokens']>12000 and not result.is_fallback
    assert result.attempt_trace[-1]['request_budget']['total_reserved']==128000
    assert discover.await_count==1 and acquire.await_count==1


@pytest.mark.asyncio
async def test_fallback_recalculates_its_budget_and_preserves_all_original_messages(runtime):
    db,calls,state,acquire,_,_=runtime
    state['fail_primary']=True
    req=request()
    result=await modelops_service.generate(db,req)
    assert result.is_fallback and len(calls)==2
    assert calls[0][1]['max_tokens']>calls[1][1]['max_tokens']
    assert calls[0][1]['messages']==calls[1][1]['messages']==req.messages
    assert acquire.await_count==2


@pytest.mark.asyncio
async def test_a_smaller_fallback_is_rejected_before_key_lease_without_trimming_the_prompt(runtime):
    db,calls,state,acquire,_,_=runtime
    state['fail_primary']=True
    req=request(' x'*15000)
    with pytest.raises(AppException):
        await modelops_service.generate(db,req)
    assert len(calls)==1 and calls[0][0]=='primary'
    assert acquire.await_count==1 and req.messages[-1].content==' x'*15000


@pytest.mark.asyncio
async def test_actual_dynamic_budget_is_checked_against_quota_before_key_lease(runtime):
    db,calls,_,acquire,quota,_=runtime
    quota.side_effect=[None,AppException('Quota exhausted',code='QUOTA_EXCEEDED',status_code=429)]
    with pytest.raises(AppException) as exc:
        await modelops_service.generate(db,request())
    assert exc.value.code=='QUOTA_EXCEEDED' and not calls and acquire.await_count==0


@pytest.mark.asyncio
async def test_an_explicit_request_output_limit_is_still_respected(runtime):
    db,calls,_,_,_,_=runtime
    await modelops_service.generate(db,request(max_tokens=10000))
    assert calls[0][1]['max_tokens']==10000


@pytest.mark.asyncio
async def test_uncounted_template_roles_are_not_sent_as_if_calibrated(runtime):
    db,calls,_,acquire,_,_=runtime
    req=request();req.messages.append(req.messages[-1])
    with pytest.raises(AppException) as exc:
        await modelops_service.generate(db,req)
    assert exc.value.code=='MODEL_TOKEN_ENVELOPE_UNVERIFIED'
    assert not calls and acquire.await_count==0


@pytest.mark.asyncio
async def test_explicit_output_limit_cannot_undercut_the_minimum_contract(runtime):
    db,calls,_,acquire,_,_=runtime
    with pytest.raises(AppException) as exc:
        await modelops_service.generate(db,request(max_tokens=50,minimum_output_tokens=100))
    assert exc.value.code=='MODEL_OUTPUT_LIMIT_TOO_SMALL' and not calls and acquire.await_count==0
