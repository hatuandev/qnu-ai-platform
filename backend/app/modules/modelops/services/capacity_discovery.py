"""Endpoint evidence, never a model-name table, determines automatic capacity.

Catalogue limits are declarations. Usage proves only the successful lower bound;
an explicit runtime rejection can further restrict the declared context.
"""
import asyncio
import hashlib
import json
import re
import secrets
import time
from urllib.parse import quote

import httpx

from app.core.exceptions import AppException

PROTOCOL='endpoint-capacity-and-calibrated-request/v1'
_cache: dict[tuple,tuple[float,dict]]={}
_locks: dict[tuple,asyncio.Lock]={}
_observed_windows: dict[tuple,tuple[float,int]]={}
_CACHE_SECONDS=600  # Discovery freshness, not a token ceiling.


def identity(provider_id: str, endpoint: str, model: str) -> tuple:
    return provider_id,endpoint.rstrip('/'),model


def capacity_error(message: str, code: str='MODEL_TOKEN_CAPACITY_REQUIRED', status: int=422) -> AppException:
    return AppException(message,code=code,status_code=status)


def metadata_capacity(data: dict, model: str, provider_type: str='custom') -> dict:
    entries=data.get('data',data.get('models')) if isinstance(data,dict) else None
    if not isinstance(entries,list) or data.get('error') or data.get('errors') or data.get('success') is False:
        raise capacity_error('Danh mục capacity sai giao thức.','MODEL_CAPACITY_PROTOCOL_ERROR',502)
    def exact_model(entry):
        actual=entry.get('id',entry.get('name'))
        if provider_type=='gemini' and isinstance(actual,str):
            return actual.removeprefix('models/')==model.removeprefix('models/')
        return actual==model
    matching=[x for x in entries if isinstance(x,dict) and exact_model(x)]
    if len(matching)!=1:
        raise capacity_error('Danh mục không xác định duy nhất model cần đọc capacity.')
    entry=matching[0]
    top=entry.get('top_provider') or {}
    if not isinstance(top,dict):
        raise capacity_error('Metadata provider sai giao thức.','MODEL_CAPACITY_PROTOCOL_ERROR',502)
    windows=[entry[k] for k in ('context_length','context_window','max_model_len') if entry.get(k) is not None]
    if top.get('context_length') is not None:
        windows.append(top['context_length'])
    outputs=[entry[k] for k in ('max_output_tokens','max_completion_tokens') if entry.get(k) is not None]
    if top.get('max_completion_tokens') is not None:
        outputs.append(top['max_completion_tokens'])
    # Native APIs declare an input limit separately. Treating it as the shared
    # envelope is conservative; do not claim a larger window by adding output.
    native_input='inputTokenLimit' if provider_type=='gemini' else 'max_input_tokens' if provider_type=='claude' else None
    native_output='outputTokenLimit' if provider_type=='gemini' else 'max_tokens' if provider_type=='claude' else None
    if native_input and entry.get(native_input) is not None:
        windows.append(entry[native_input])
    if native_output and entry.get(native_output) is not None:
        outputs.append(entry[native_output])
    if (not windows or any(type(v) is not int or v<1024 for v in windows)
            or any(type(v) is not int or v<50 for v in outputs)):
        raise capacity_error('Provider chưa công bố context hợp lệ; không suy ra từ tên model.')
    return {'context_window_tokens':min(windows),'max_output_tokens':min(outputs) if outputs else None,
        'basis':'provider_reported','capacity_source':'configured_endpoint_models_metadata',
        'capacity_verified_by_inference':False,
        'window_semantics':'conservative_shared_envelope_from_input_limit' if native_input else 'declared_shared_context'}


def encoding_for_model(model: str) -> str | None:
    import tiktoken

    # Registry lookup chooses a tokenizer, never a model's context capacity.
    canonical=model.rsplit('/',1)[-1].replace(':','-')
    try:
        return tiktoken.encoding_name_for_model(canonical)
    except KeyError:
        return None


def metadata_request(adapter,model: str) -> tuple[str,dict,bool]:
    from app.modules.modelops.providers.openai_adapter import OpenAIAdapter

    base=(adapter.base_url or '').rstrip('/')
    if not base:
        raise capacity_error('Chưa có endpoint capacity.','MODEL_CAPACITY_PROTOCOL_UNSUPPORTED')
    if isinstance(adapter,OpenAIAdapter):
        return base+'/models',adapter._headers(),False
    if not adapter.api_key:
        raise capacity_error('Chưa có khóa hợp lệ để đọc capacity.','provider_key_missing',401)
    if adapter.provider_type=='gemini':
        return base+'/models/'+quote(model.removeprefix('models/'),safe=''),{'x-goog-api-key':adapter.api_key},True
    if adapter.provider_type=='claude':
        return base+'/models/'+quote(model,safe=''),adapter.headers(),True
    raise capacity_error('Endpoint chưa hỗ trợ giao thức khám phá capacity này.','MODEL_CAPACITY_PROTOCOL_UNSUPPORTED')


async def catalogue(config,db,model: str | None=None) -> dict:
    from app.core.crypto import decrypt_secret
    from app.modules.modelops.providers import get_llm_adapter
    from app.modules.modelops.services.probe_credentials import select_probe_credential

    encrypted,account=await select_probe_credential(db,config)
    key=decrypt_secret(encrypted) if encrypted else None
    adapter=get_llm_adapter(config.provider_type,'',api_key=key,base_url=config.api_base_url,
        timeout_seconds=config.timeout_seconds or 30,account_id=account)
    target,headers,detail=metadata_request(adapter,model or config.model_name or '')
    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds or 30,trust_env=False,follow_redirects=False) as client:
            response=await client.get(target,headers=headers)
            response.raise_for_status()
            data=response.json()
    except httpx.TimeoutException as exc:
        raise capacity_error('Hết thời gian đọc capacity provider.','MODEL_CAPACITY_TIMEOUT',504) from exc
    except httpx.HTTPStatusError as exc:
        raise AppException('Provider từ chối đọc capacity.',code='MODEL_CAPACITY_HTTP_ERROR',
            status_code=502,details={'upstream_status':exc.response.status_code}) from exc
    except httpx.RequestError as exc:
        raise capacity_error('Không kết nối được endpoint capacity.','MODEL_CAPACITY_UNAVAILABLE',502) from exc
    except (ValueError,TypeError) as exc:
        raise capacity_error('Metadata capacity sai giao thức.','MODEL_CAPACITY_PROTOCOL_ERROR',502) from exc
    if not isinstance(data,dict):
        raise capacity_error('Metadata capacity sai giao thức.','MODEL_CAPACITY_PROTOCOL_ERROR',502)
    return {'data':[data]} if detail else data


async def calibrate(config,model: str,encoding: str) -> dict:
    from app.core.database import AsyncSessionFactory
    from app.modules.modelops.schemas import LLMGenerateRequest
    from app.modules.modelops.service import modelops_service
    from app.modules.modelops.services.inference_policy import preserve_structured_output
    from app.modules.modelops.services.request_token_budget import input_tokens

    marker=secrets.token_hex(8)
    messages=[{'role':'system','content':'Return exactly the requested JSON object, without commentary.'},
              {'role':'user','content':'Return {"marker":"'+marker+'"}.'}]
    async with AsyncSessionFactory() as probe_db:
        with preserve_structured_output():
            result=await modelops_service.generate(probe_db,LLMGenerateRequest(
                preferred_provider_id=config.id,preferred_model_name=model,messages=messages,temperature=0))
    try:
        matches=json.loads(result.content.strip())=={'marker':marker}
    except (ValueError,TypeError):
        matches=False
    if (result.is_fallback or not matches or result.finish_reason!='stop'
            or result.provider_id!=config.id or result.requested_model!=model):
        raise capacity_error('Không xác minh được calibration đúng route.','MODEL_TOKEN_CALIBRATION_FAILED',502)
    content,_=await asyncio.to_thread(input_tokens,messages,encoding,0)
    if result.prompt_tokens<content:
        raise capacity_error('Usage không khớp tokenizer; chưa xác minh được template.','MODEL_TOKEN_CALIBRATION_FAILED',502)
    return {'chat_overhead_tokens':result.prompt_tokens-content,'calibrated_roles':['system','user'],
        'calibration_basis':'protected_modelops_observed_prompt_tokens_minus_tokenized_content'}


async def discover(config,model: str,db) -> dict:
    if config is None or not config.is_active:
        raise capacity_error('Provider không khả dụng để khám phá capacity.','MODEL_CAPACITY_PROVIDER_UNAVAILABLE',409)
    scope=identity(config.id,config.api_base_url or '',model)
    revision=hashlib.sha256(json.dumps([config.api_key_encrypted,config.extra_config],sort_keys=True,default=str).encode()).hexdigest()
    key=(*scope,revision)
    async with _locks.setdefault(key,asyncio.Lock()):
        cached=_cache.get(key)
        if cached and time.monotonic()-cached[0]<_CACHE_SECONDS:
            result=dict(cached[1])
        else:
            result=metadata_capacity(await catalogue(config,db,model),model,config.provider_type)
            encoding=encoding_for_model(model)
            result.update(tokenizer_encoding=encoding,chat_overhead_tokens=0,reasoning_in_output_budget=True)
            if encoding:
                result.update(await calibrate(config,model,encoding))
            _cache[key]=(time.monotonic(),dict(result))
        observed=_observed_windows.get(scope)
        if observed and time.monotonic()-observed[0]<_CACHE_SECONDS:
            result['context_window_tokens']=min(result['context_window_tokens'],observed[1])
            result['capacity_source']='provider_metadata_and_explicit_runtime_context_rejection'
        return result


def observe_context_error(provider_id: str,endpoint: str,model: str,exc: Exception) -> int | None:
    from app.modules.modelops.services.key_rotation import _extract_response

    response=_extract_response(exc)
    if response is None or response.status_code!=400:
        return None
    try:
        error=response.json()['error']
        message=error['message']
    except (KeyError,TypeError,ValueError):
        return None
    if not isinstance(error,dict) or not isinstance(message,str):
        return None
    if error.get('code')!='context_length_exceeded' and not message.startswith("This model's maximum context length"):
        return None
    match=re.search(r'maximum context length is (\d+) tokens',message)
    if not match or int(match[1])<1024:
        return None
    window=int(match[1])
    _observed_windows[identity(provider_id,endpoint,model)]=(time.monotonic(),window)
    return window
