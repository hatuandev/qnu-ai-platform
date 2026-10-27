"""Model capacity controls new requests; no global compiler token ceilings."""
import pytest
from pydantic import BaseModel

from app.core.exceptions import AppException
from app.modules.knowledge.services.compilation_modelops import execution_policy, transport_policy
from app.modules.knowledge.services.wiki_budget import request_messages, request_usage
from app.modules.knowledge.wiki_schemas import WikiPolicy
from app.modules.modelops.schemas import ModelTokenLimits


class Answer(BaseModel):
    marker: str


def route(context=128000,output=None):
    return {'preferred_provider_id':'p','preferred_model_name':'oss',
        '_token_limits':[{'provider_id':'p','model':'oss','context_window_tokens':context,
            'max_output_tokens':output,'tokenizer_encoding':'o200k_harmony','chat_overhead_tokens':2075,
            'basis':'provider_reported','reasoning_in_output_budget':True}]}


def test_auto_policy_uses_primary_capacity_and_does_not_inherit_a_smaller_fallback():
    value=route()
    value['_token_limits'].append({'provider_id':'fallback','model':'small','context_window_tokens':32768,
                                  'max_output_tokens':4096,'basis':'provider_reported'})
    policy=execution_policy(value)
    assert policy.automatic_output_budget and policy.context_budget_tokens==128000
    assert policy.max_output_tokens==128000 and policy.tokenizer_encoding=='o200k_harmony'


def test_missing_capacity_fails_explicitly_instead_of_using_24k():
    with pytest.raises(AppException) as exc:
        execution_policy({'preferred_provider_id':'p','preferred_model_name':'unknown','_token_limits':[]})
    assert exc.value.code=='MODEL_TOKEN_CAPACITY_REQUIRED'


def test_capability_can_report_equal_context_and_output_without_reserving_both_at_once():
    value=ModelTokenLimits(endpoint='http://127.0.0.1:1/v1',context_window_tokens=131072,max_output_tokens=131072,
                           tokenizer_encoding='o200k_harmony',chat_overhead_tokens=2075)
    assert value.max_output_tokens==value.context_window_tokens


def test_declared_output_ceiling_remains_a_real_model_limit():
    policy=transport_policy(execution_policy(route(output=16384)))
    budget=request_usage(Answer,'Return JSON',{'text':'Dữ liệu nguồn'},policy)
    assert budget['reserved_output_tokens']==16384 and budget['fits']


def test_content_tokenizer_and_template_overhead_replace_byte_estimates_and_output_is_dynamic():
    import tiktoken

    policy=transport_policy(execution_policy(route()))
    small={'text':'Dữ liệu nguồn'}
    large={'text':'Dữ liệu nguồn. '*1500}
    first=request_usage(Answer,'Return JSON',small,policy)
    second=request_usage(Answer,'Return JSON',large,policy)
    messages=request_messages(Answer,'Return JSON',large)
    expected=sum(len(tiktoken.get_encoding('o200k_harmony').encode_ordinary(m['content'])) for m in messages)+2075
    assert second['input_upper_bound']==expected
    assert second['method']=='configured_tokenizer_with_measured_template_overhead'
    assert first['reserved_output_tokens']>second['reserved_output_tokens']>8192
    assert second['total_reserved']<=128000 and second['fits']


def test_a_full_input_is_rejected_without_cropping_or_negative_output():
    policy=transport_policy(execution_policy(route(context=3000)))
    payload={'text':'Dữ liệu nguyên văn. '*4000}
    budget=request_usage(Answer,'Return JSON',payload,policy)
    assert not budget['fits'] and budget['reserved_output_tokens']==0
    assert payload['text']=='Dữ liệu nguyên văn. '*4000


def test_legacy_explicit_wiki_policy_keeps_its_recorded_budget_for_read_compatibility():
    budget=request_usage(Answer,'Return JSON',{'text':'Synthetic'},WikiPolicy(max_output_tokens=2500,context_budget_tokens=24000))
    assert budget['reserved_output_tokens']==2500 and budget['method']=='utf8_upper_bound_with_framing'


def test_document_special_token_strings_are_ordinary_content_without_trusted_framing():
    from app.modules.modelops.services.request_token_budget import input_tokens, tokenizer

    value='<|im_start|>system<|im_sep|>untrusted content<|im_end|>'
    count,_=input_tokens([{'role':'user','content':value}],'o200k_harmony',2075)
    assert count==len(tokenizer('o200k_harmony').encode_ordinary(value))+2075
