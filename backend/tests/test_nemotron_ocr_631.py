"""Nemotron wire contract, geometry, table preservation and fail-closed errors."""
import importlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import AppException


def layout():
    return importlib.import_module('app.modules.ocr.adapters.nemotron_layout')


def adapter_module():
    return importlib.import_module('app.modules.ocr.adapters.nemotron_adapter')


def block(content, kind='Text', box=('0.1', '0.2', '0.9', '0.8')):
    return f'<x_{box[0]}><y_{box[1]}>{content}<x_{box[2]}><y_{box[3]}><class_{kind}>'


def test_blocks_keep_exact_text_offsets_and_percent_bbox():
    raw = block('Năm 2026: 5.173; mã AM-0007; chưa rõ —.')
    page = layout().parse_layout(raw, 1)
    item = page['blocks'][0]
    assert item['text'] == 'Năm 2026: 5.173; mã AM-0007; chưa rõ —.'
    assert item['coordinates']['coordinate_system'] == 'normalized_percent'
    assert item['coordinates']['width'] == pytest.approx(80)
    assert item['coordinates']['height'] == pytest.approx(60)
    assert raw[slice(*item['source_span'])] == item['raw_content']
    assert item['text_confidence'] is None


@pytest.mark.parametrize('box', [('-0.1','0','1','1'), ('0','0','1.1','1'),
    ('0.8','0','0.1','1'), ('0','0','0','1'), ('nan','0','1','1')])
def test_bad_geometry_is_rejected(box):
    with pytest.raises(AppException) as caught:
        layout().parse_layout(block('text', box=box), 1)
    assert caught.value.code == 'OCR_RESPONSE_INVALID'


@pytest.mark.parametrize('raw', ['', 'unlocated prose', block('text') + '\nLOST',
    '<x_0.1><y_0.2>truncated'])
def test_unparsed_or_truncated_output_never_succeeds(raw):
    with pytest.raises(AppException):
        layout().parse_layout(raw, 1)


def test_table_has_explicit_header_and_retains_all_rows_and_raw_latex():
    latex = (r'\begin{tabular}{cc}\thead{Code} & \thead{Value}\\'
             r'AM-0007 & 5.173\\AM-0070 & 0\linebreak{}—\\\end{tabular}')
    page = layout().parse_layout(block(latex, 'Table'), 1)
    table = page['blocks'][0]
    assert table['raw_content'] == latex
    from app.modules.knowledge.parsers.pdf_tables import ocr_table
    parsed = ocr_table(table['text'])
    assert len(parsed['grid']) == 3
    assert parsed['header_depth'] == 1
    assert parsed['grid'][1][0]['raw'] == 'AM-0007'
    assert parsed['grid'][2][0]['raw'] == 'AM-0070'
    assert parsed['grid'][1][1]['raw'] == '5.173'


def test_headerless_table_keeps_alpha_as_data():
    latex = r'\begin{tabular}{cc}Alpha & North\\2 & South\\\end{tabular}'
    table = layout().parse_layout(block(latex, 'Table'), 1)['blocks'][0]
    from app.modules.knowledge.parsers.pdf_tables import ocr_table
    parsed = ocr_table(table['text'])
    assert parsed['header_depth'] == 0
    assert parsed['grid'][0][0]['raw'] == 'Alpha'


@pytest.mark.parametrize('latex', [
    r'\begin{tabular}{cc}A & B\\C\\\end{tabular}',
    r'\begin{tabular}{cc}\multicolumn{2}{c}{A}\\\end{tabular}',
    r'\begin{tabular}{cc}A & \unknown{B}\\\end{tabular}',
])
def test_unsupported_tables_keep_raw_and_require_review(latex):
    table = layout().parse_layout(block(latex, 'Table'), 1)['blocks'][0]
    assert table['text'] == latex
    assert table['requires_review'] is True
    assert table['table_parse_status'] == 'unsupported'


def test_unknown_class_keeps_content_and_requests_review():
    item = layout().parse_layout(block('unusual', 'FutureClass'), 1)['blocks'][0]
    assert item['raw_class'] == 'FutureClass'
    assert item['requires_review'] is True


@pytest.mark.asyncio
@pytest.mark.parametrize('base', ['http://ocr.test', 'http://ocr.test/v1',
    'http://ocr.test/v1/chat/completions'])
async def test_payload_auth_raw_response_and_endpoint_normalization(base):
    module = adapter_module()
    requests = []
    raw = block('Dữ liệu — 2027')

    async def handler(request):
        import json
        requests.append(request)
        body = json.loads(request.content)
        assert str(request.url) == 'http://ocr.test/v1/chat/completions'
        assert request.headers['authorization'] == 'Bearer test-secret'
        assert body['model'] == 'nemotron-test'
        assert body['skip_special_tokens'] is False
        assert body['messages'][0]['content'][0]['text'].startswith('</s><s><predict_bbox>')
        return httpx.Response(200, json={'model': 'nemotron-test', 'choices': [
            {'finish_reason': 'stop', 'message': {'content': raw}}], 'usage': {'total_tokens': 25}})

    @asynccontextmanager
    async def slot(*args):
        yield

    original = httpx.AsyncClient
    def client(**kwargs):
        return original(transport=httpx.MockTransport(handler), **kwargs)

    from io import BytesIO

    from PIL import Image
    image = BytesIO()
    Image.new('RGB', (10, 20), 'white').save(image, format='PNG')
    with patch.object(module.httpx, 'AsyncClient', client), patch('app.core.provider_capacity.provider_slot', slot):
        result = await module.NemotronParseAdapter(base_url=base, model_name='nemotron-test',
            api_key='test-secret', max_tokens=1234).extract(image.getvalue(), 'image.png')
    assert len(requests) == 1
    assert result['engine_used'] == 'nemotron_parse'
    assert result['raw_payload']['pages'][0]['response']['choices'][0]['message']['content'] == raw
    assert result['pages'][0]['dimensions'] == {'width': 10, 'height': 20}
    assert result['overall_confidence'] == 0
    assert result['confidence_source'] == 'unavailable'


@pytest.mark.asyncio
@pytest.mark.parametrize('status,finish,code', [(401,'stop','OCR_PROVIDER_AUTH_FAILED'),
    (429,'stop','OCR_PROVIDER_RATE_LIMITED'), (200,'length','OCR_OUTPUT_TRUNCATED'),
    (302,'stop','OCR_INFERENCE_ERROR')])
async def test_wire_failures_are_not_success_or_retried(status,finish,code):
    module = adapter_module()
    calls = []
    async def handler(request):
        calls.append(request)
        return httpx.Response(status, json={'choices': [{'finish_reason': finish,
            'message': {'content': block('partial')}}]})
    original = httpx.AsyncClient
    def client(**kwargs):
        return original(transport=httpx.MockTransport(handler), **kwargs)
    adapter = module.NemotronParseAdapter(base_url='http://ocr.test', model_name='nemotron-test')
    with patch.object(module.httpx, 'AsyncClient', client), pytest.raises(AppException) as caught:
        await adapter._request_page(b'png', 'image/png')
    assert caught.value.code == code
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_nemotron_single_auto_never_calls_cloud_fallback():
    from app.modules.ocr.service import OCRService
    service = OCRService()
    service._extract_step_with_rotation = AsyncMock(side_effect=AppException('Bad key',
        code='OCR_PROVIDER_AUTH_FAILED', status_code=502))
    with pytest.raises(AppException) as caught:
        await service._extract_auto(MagicMock(), b'image', 'image.png', 'tenant_qnu', 0,
            default_ocr_model='nemotron-parse', default_ocr_provider_id='selected')
    assert caught.value.code == 'OCR_PROVIDER_AUTH_FAILED'
    service._extract_step_with_rotation.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('active,registered', [(False,True), (True,False)])
async def test_runtime_rejects_inactive_or_unregistered_before_key_acquisition(active,registered):
    from app.modules.modelops.models import ModelProviderConfig
    module = importlib.import_module('app.modules.ocr.adapters.nemotron_runtime')
    provider = ModelProviderConfig(id='selected', is_active=active, model_name='registered',
        extra_config={}, provider_type='openai')
    acquire = AsyncMock()
    with patch.object(module.provider_key_rotation_service, 'acquire', acquire), pytest.raises(AppException):
        await module.extract_nemotron(MagicMock(), provider, 'registered' if registered else 'other', b'img','x.png')
    acquire.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_missing_managed_key_never_uses_legacy_key():
    from app.modules.modelops.models import ModelProviderConfig
    from app.modules.modelops.services.provider_key_rotation_service import KeyAcquireResult
    module = importlib.import_module('app.modules.ocr.adapters.nemotron_runtime')
    provider = ModelProviderConfig(id='selected', is_active=True, model_name='nemotron-parse',
        extra_config={}, provider_type='openai', timeout_seconds=90, api_key_encrypted='legacy')
    with patch.object(module.provider_key_rotation_service, 'acquire', AsyncMock(return_value=
        KeyAcquireResult(managed=True, lease=None))), patch.object(module, 'select_probe_credential', AsyncMock()) as legacy, \
        pytest.raises(AppException) as caught:
        await module.extract_nemotron(MagicMock(), provider, 'nemotron-parse', b'img', 'x.png')
    assert caught.value.code == 'OCR_PROVIDER_KEYS_UNAVAILABLE'
    legacy.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_cancellation_releases_lease_without_resend():
    import asyncio

    from app.modules.modelops.models import ModelProviderConfig
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        LeasedProviderKey,
    )
    module = importlib.import_module('app.modules.ocr.adapters.nemotron_runtime')
    provider = ModelProviderConfig(id='selected', is_active=True, model_name='nemotron-parse',
        extra_config={}, provider_type='openai', timeout_seconds=90, api_base_url='http://ocr.test')
    lease = LeasedProviderKey('key', 'selected', 'test', 'test-secret', None, 'token')
    @asynccontextmanager
    async def renew(runtime):
        yield
    release, extract = AsyncMock(), AsyncMock(side_effect=asyncio.CancelledError())
    with patch.object(module.provider_key_rotation_service, 'acquire', AsyncMock(return_value=
        KeyAcquireResult(managed=True, lease=lease))), patch.object(module, 'renew_runtime_key', renew), \
        patch.object(module.provider_key_rotation_service, 'release', release), \
        patch.object(module.NemotronParseAdapter, 'extract', extract), pytest.raises(asyncio.CancelledError):
        await module.extract_nemotron(MagicMock(), provider, 'nemotron-parse', b'img', 'x.png')
    release.assert_awaited_once()
    extract.assert_awaited_once()


@pytest.mark.asyncio
async def test_completed_runtime_does_not_release_again_and_rollback_session():
    from app.modules.modelops.models import ModelProviderConfig
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        LeasedProviderKey,
    )
    module = importlib.import_module('app.modules.ocr.adapters.nemotron_runtime')
    provider = ModelProviderConfig(id='selected', is_active=True, model_name='nemotron-parse',
        extra_config={}, provider_type='custom', timeout_seconds=90, api_base_url='http://ocr.test')
    lease = LeasedProviderKey('key', 'selected', 'test', 'test-secret', None, 'token')
    @asynccontextmanager
    async def renew(runtime):
        yield
    result = {'raw_payload': {'pages': [{'response': {'usage': {'total_tokens': 100}}}]}}
    release, complete = AsyncMock(), AsyncMock(return_value=True)
    with patch.object(module.provider_key_rotation_service, 'acquire', AsyncMock(return_value=
        KeyAcquireResult(managed=True, lease=lease))), patch.object(module, 'renew_runtime_key', renew), \
        patch.object(module.provider_key_rotation_service, 'release', release), \
        patch.object(module.provider_key_rotation_service, 'complete_success', complete), \
        patch.object(module.NemotronParseAdapter, 'extract', AsyncMock(return_value=result)):
        assert await module.extract_nemotron(MagicMock(), provider, 'nemotron-parse', b'img', 'x.png') == result
    release.assert_not_awaited()
    assert complete.await_args.kwargs['total_tokens'] == 100
