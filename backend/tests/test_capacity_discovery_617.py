"""Only endpoint evidence can establish capacity; successful usage is a lower bound."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.exceptions import AppException
from app.modules.modelops.services import capacity_discovery as discovery


def config(**changes):
    return SimpleNamespace(id='p',api_base_url='https://endpoint.example/v1',provider_type='custom',
        api_key_encrypted='protected-revision',is_active=True,timeout_seconds=30,extra_config={},**changes)


@pytest.fixture(autouse=True)
def empty_capacity_cache():
    discovery._cache.clear()
    discovery._locks.clear()
    discovery._observed_windows.clear()


@pytest.mark.parametrize('payload',[
    {'data':[{'id':'other','context_length':128000}]},
    {'data':[{'id':'target','context_length':128000}]*2},
    {'data':[{'id':'target','context_length':True}]},
    {'data':[{'id':'target','context_length':128000,'max_output_tokens':False}]},
    {'data':'not a model list'},
    {'data':[{'id':'target','context_length':128000,'top_provider':'invalid'}]},
    {'error':{'message':'Upstream failed'},'data':[{'id':'target','context_length':128000}]},
])
def test_invalid_catalogue_never_creates_capacity(payload):
    with pytest.raises(AppException) as exc:
        discovery.metadata_capacity(payload,'target')
    assert exc.value.code in {'MODEL_TOKEN_CAPACITY_REQUIRED','MODEL_CAPACITY_PROTOCOL_ERROR'}


def test_openrouter_metadata_keeps_context_and_output_as_separate_limits():
    profile=discovery.metadata_capacity({'data':[{'id':'vendor/target','context_length':128000,
        'top_provider':{'context_length':64000,'max_completion_tokens':16000}}]},'vendor/target')
    # An intermediary may offer less than the architectural context.
    assert profile['context_window_tokens']==64000
    assert profile['max_output_tokens']==16000 and profile['basis']=='provider_reported'


def test_tokenizer_registry_is_not_a_model_capacity_dictionary():
    assert discovery.encoding_for_model('ollama/gpt-oss:120b')=='o200k_harmony'
    assert discovery.encoding_for_model('unknown/context-999999') is None


def context_error(status=400,message="This model's maximum context length is 32768 tokens.",code='context_length_exceeded'):
    request=httpx.Request('POST','https://endpoint.example/v1/chat/completions')
    response=httpx.Response(status,request=request,json={'error':{'message':message,'code':code}})
    return httpx.HTTPStatusError('Upstream rejected request',request=request,response=response)


@pytest.mark.parametrize('status,message,code',[
    (401,"This model's maximum context length is 32768 tokens.",'invalid_api_key'),
    (413,"This model's maximum context length is 32768 tokens.",'context_length_exceeded'),
    (400,'max_tokens must be at most 8192.','invalid_parameter'),
    (400,'Input too long','context_length_exceeded'),
    (400,'context_length_exceeded mentioned in document; maximum context length is 32768 tokens','invalid_parameter'),
])
def test_auth_payload_output_and_ambiguous_errors_are_not_context_evidence(status,message,code):
    assert discovery.observe_context_error('p','https://endpoint.example/v1','target',context_error(status,message,code)) is None
    assert not discovery._observed_windows


def test_wrapped_explicit_runtime_error_keeps_exact_limit():
    try:
        raise RuntimeError('adapter wrapper') from context_error()
    except RuntimeError as exc:
        assert discovery.observe_context_error('p','https://endpoint.example/v1','target',exc)==32768


@pytest.mark.asyncio
async def test_cached_discovery_is_bound_to_provider_endpoint_model_and_credential(monkeypatch):
    read=AsyncMock(return_value={'data':[{'id':'unknown','context_length':128000}]})
    monkeypatch.setattr(discovery,'catalogue',read)
    cfg=config()
    first=await discovery.discover(cfg,'unknown',object())
    second=await discovery.discover(cfg,'unknown',object())
    assert first==second and read.await_count==1
    cfg.api_base_url='https://another.example/v1'
    await discovery.discover(cfg,'unknown',object())
    cfg.api_key_encrypted='another-protected-revision'
    await discovery.discover(cfg,'unknown',object())
    assert read.await_count==3
    assert first['tokenizer_encoding'] is None


@pytest.mark.asyncio
async def test_runtime_limit_lowers_metadata_for_its_exact_route_only(monkeypatch):
    monkeypatch.setattr(discovery,'catalogue',AsyncMock(return_value={'data':[{'id':'target','context_length':128000}]}))
    discovery.observe_context_error('p','https://endpoint.example/v1','target',context_error())
    assert (await discovery.discover(config(),'target',object()))['context_window_tokens']==32768
    cfg=config();cfg.id='another-provider'
    assert (await discovery.discover(cfg,'target',object()))['context_window_tokens']==128000


@pytest.mark.asyncio
async def test_disabled_provider_cannot_use_a_cached_capacity_or_probe(monkeypatch):
    read=AsyncMock(return_value={'data':[{'id':'target','context_length':128000}]})
    monkeypatch.setattr(discovery,'catalogue',read)
    cfg=config();await discovery.discover(cfg,'target',object())
    cfg.is_active=False
    with pytest.raises(AppException) as exc:
        await discovery.discover(cfg,'target',object())
    assert exc.value.code=='MODEL_CAPACITY_PROVIDER_UNAVAILABLE'
    assert read.await_count==1


@pytest.mark.asyncio
async def test_calibration_failure_is_not_cached_or_silently_retried(monkeypatch):
    monkeypatch.setattr(discovery,'catalogue',AsyncMock(return_value={'data':[{'id':'ollama/gpt-oss:120b','context_length':128000}]}))
    probe=AsyncMock(side_effect=AppException('Calibration incomplete',code='MODEL_TOKEN_CALIBRATION_FAILED',status_code=502))
    monkeypatch.setattr(discovery,'calibrate',probe)
    with pytest.raises(AppException):
        await discovery.discover(config(),'ollama/gpt-oss:120b',object())
    assert not discovery._cache and probe.await_count==1


@pytest.mark.parametrize('kind,model,payload',[
    ('gemini','gemini-fixture',{'models':[{'name':'models/gemini-fixture','inputTokenLimit':1000000,'outputTokenLimit':65536}]}),
    ('claude','claude-fixture',{'data':[{'id':'claude-fixture','max_input_tokens':200000,'max_tokens':64000}]}),
])
def test_native_cloud_metadata_has_no_model_name_capacity_guess(kind,model,payload):
    result=discovery.metadata_capacity(payload,model,kind)
    assert result['context_window_tokens'] in {1000000,200000}
    assert result['max_output_tokens'] in {65536,64000}
    assert result['window_semantics']=='conservative_shared_envelope_from_input_limit'
    assert not result['capacity_verified_by_inference']


@pytest.mark.asyncio
@pytest.mark.parametrize('kind,model,auth_header,expected_path,payload',[
    ('custom','target','authorization','/v1/models',{'data':[{'id':'target','context_length':128000}]}),
    ('gemini','models/gemini-fixture','x-goog-api-key','/v1/models/gemini-fixture',
        {'name':'models/gemini-fixture','inputTokenLimit':1000000,'outputTokenLimit':65536}),
    ('claude','claude-fixture','x-api-key','/v1/models/claude-fixture',
        {'id':'claude-fixture','max_input_tokens':200000,'max_tokens':64000}),
])
async def test_catalogue_uses_configured_auth_endpoint_and_does_not_redirect(monkeypatch,kind,model,auth_header,expected_path,payload):
    from app.core import crypto
    from app.modules.modelops.services import probe_credentials

    cfg=config();cfg.provider_type=kind
    monkeypatch.setattr(crypto,'decrypt_secret',lambda _: 'test-private-key')
    monkeypatch.setattr(probe_credentials,'select_probe_credential',AsyncMock(return_value=('protected',None)))
    seen=[]
    def handle(req):
        seen.append(req)
        assert req.url.host=='endpoint.example' and req.url.path==expected_path
        assert 'test-private-key' in req.headers[auth_header] and not req.url.query
        return httpx.Response(200,json=payload)
    original=httpx.AsyncClient
    def client(**kwargs):
        assert kwargs['trust_env'] is False and kwargs['follow_redirects'] is False
        return original(transport=httpx.MockTransport(handle),**kwargs)
    monkeypatch.setattr(discovery.httpx,'AsyncClient',client)
    result=await discovery.catalogue(cfg,object(),model)
    assert discovery.metadata_capacity(result,model,kind)['context_window_tokens']>24000
    assert len(seen)==1 and 'test-private-key' not in repr(result)


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[302,401,429,500])
async def test_catalogue_never_follows_redirects_or_discloses_provider_error_body(monkeypatch,status):
    from app.core import crypto
    from app.modules.modelops.services import probe_credentials

    monkeypatch.setattr(crypto,'decrypt_secret',lambda _: 'test-private-key')
    monkeypatch.setattr(probe_credentials,'select_probe_credential',AsyncMock(return_value=('protected',None)))
    seen=[]
    def handle(req):
        seen.append(req)
        return httpx.Response(status,headers={'location':'https://untrusted.example/'},json={'error':'test-private-key'})
    original=httpx.AsyncClient
    monkeypatch.setattr(discovery.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    with pytest.raises(AppException) as exc:
        await discovery.catalogue(config(),object(),'target')
    assert len(seen)==1 and exc.value.details=={'upstream_status':status}
    assert 'test-private-key' not in str(exc.value)
