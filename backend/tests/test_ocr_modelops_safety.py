"""Regression coverage for ModelOps safety and truthful OCR contracts."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.services.provider_service import ProviderService
from app.modules.ocr.adapters.paddleocr_adapter import PaddleOCRVLAdapter
from app.modules.ocr.service import OCRService


def test_unconfigured_paddle_is_not_available():
    assert not PaddleOCRVLAdapter().is_available()


@pytest.mark.asyncio
async def test_explicit_paddle_resolves_database_provider():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = ModelProviderConfig(
        id="configured", provider_type="paddleocr", api_base_url="http://configured.test",
        model_name="custom-layout", timeout_seconds=37,
    )
    db.execute.return_value = result
    service = OCRService()
    with patch.object(service, "_get_system_defaults", AsyncMock(return_value={})), \
            patch.object(service, "_extract_step_with_rotation", AsyncMock(return_value={"raw_text": "text"})) as extract, \
            patch.object(service, "_build_response", AsyncMock()):
        await service.extract_document(db, b"pdf", "file.pdf", engine_name="paddleocr")
    extract.assert_awaited_once_with(db, {"provider_id": "configured", "model_name": "custom-layout"}, b"pdf", "file.pdf")


@pytest.mark.asyncio
async def test_explicit_paddle_missing_provider_fails_without_fallback():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    service = OCRService()
    with patch.object(service, "_get_system_defaults", AsyncMock(return_value={})), \
            patch.object(service, "_extract_combo_chain", AsyncMock()) as fallback, \
            pytest.raises(AppException) as error:
        await service.extract_document(db, b"pdf", "file.pdf", engine_name="paddleocr")
    assert error.value.code == "OCR_PROVIDER_UNAVAILABLE"
    fallback.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{}, [], {"result": {"layoutParsingResults": []}},
    {"result": {"layoutParsingResults": [{"markdown": {"text": 123}}]}}])
async def test_invalid_ocr_response_is_not_success(body):
    response = httpx.Response(200, json=body)
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=response)), pytest.raises(AppException):
        await PaddleOCRVLAdapter(base_url="http://ocr.test").extract(b"pdf", "file.pdf")


@pytest.mark.asyncio
async def test_active_provider_uses_database_endpoint_model_and_timeout():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = ModelProviderConfig(
        id="paddle", provider_type="paddleocr", api_base_url="http://configured.test",
        model_name="configured-vision", timeout_seconds=37,
    )
    db.execute.return_value = result
    with patch("app.modules.ocr.service.PaddleOCRVLAdapter") as adapter:
        adapter.return_value.extract = AsyncMock(return_value={"raw_text": "text"})
        await OCRService()._extract_step_with_rotation(
            db, {"provider_id": "paddle", "model_name": "PaddleOCR-custom"}, b"pdf", "file.pdf",
        )
        adapter.assert_called_with(base_url="http://configured.test", model_name="PaddleOCR-custom", timeout=37)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [
    httpx.Response(200, text="not JSON"),
    httpx.Response(200, json={"result": {"layoutParsingResults": [{"markdown": {"text": " "}}]}}),
])
async def test_invalid_json_and_blank_document_fail(response):
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=response)), pytest.raises(AppException):
        await PaddleOCRVLAdapter(base_url="http://ocr.test").extract(b"pdf", "file.pdf")


@pytest.mark.asyncio
async def test_paddle_does_not_fabricate_confidence_or_shift_blank_page():
    response = httpx.Response(200, json={"result": {"layoutParsingResults": [
        {"markdown": {"text": ""}}, {"markdown": {"text": "Trang thứ hai"}},
    ]}})
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=response)):
        output = await PaddleOCRVLAdapter(base_url="http://ocr.test").extract(b"pdf", "file.pdf")
    assert output["confidence_source"] == "unavailable"
    assert output["overall_confidence"] == 0
    assert output["pages"][1]["page_number"] == 2
    assert "<!-- Trang 2 -->" in output["raw_text"]


@pytest.mark.asyncio
async def test_disabled_provider_never_calls_http():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    with patch("httpx.AsyncClient.post", AsyncMock()) as post:
        with pytest.raises(AppException):
            await OCRService()._extract_step_with_rotation(
                db, {"provider_id": "disabled", "model_name": "PaddleOCR-VL"}, b"pdf", "file.pdf",
            )
        post.assert_not_called()


@pytest.mark.asyncio
async def test_reseed_preserves_existing_provider_configuration():
    db = AsyncMock()
    existing = ModelProviderConfig(
        id="prov_rtx5090_vllm", name="Custom", provider_type="vllm", model_name="bge-m3",
        api_base_url="http://custom.test/v1", api_key_encrypted="encrypted-test-key",
        timeout_seconds=37, extra_config={"api_keys": [{"id": "test-key"}]},
    )
    result = MagicMock()
    legacy = ModelProviderConfig(id="prov_rtx5090_ollama", name="Existing Ollama", provider_type="ollama")
    result.scalars.return_value.all.return_value = [existing, legacy]
    db.execute.return_value = result
    with patch("app.modules.modelops.services.model_catalog_service.model_catalog_service.seed_system_model_defaults", AsyncMock()) as defaults:
        await ProviderService().seed_default_providers(db, overwrite=True)
        defaults.assert_awaited_once_with(db, overwrite=False)
    db.delete.assert_not_called()
    assert existing.api_key_encrypted == "encrypted-test-key"
    assert existing.api_base_url == "http://custom.test/v1"
    assert existing.timeout_seconds == 37
    assert existing.extra_config["api_keys"] == [{"id": "test-key"}]
