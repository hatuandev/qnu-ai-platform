"""ModelOps must distinguish unauthenticated OCR from keyed vLLM."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.modules.modelops.services.provider_service import STANDARD_QNU_PROVIDERS, ProviderService


@pytest.mark.asyncio
async def test_paddle_health_uses_no_authorization():
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=httpx.Response(200, json={"healthy": True}))) as get:
        success, _, message = await ProviderService()._ping_provider_api("paddleocr", "http://ocr.local", None)
    assert success
    get.assert_awaited_once_with("http://ocr.local/health")
    assert "OCR" in message


@pytest.mark.asyncio
async def test_paddle_unreachable_is_not_success():
    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=httpx.ConnectError("offline"))):
        success, _, _ = await ProviderService()._ping_provider_api("paddleocr", "http://ocr.local", None)
    assert not success


@pytest.mark.asyncio
async def test_vllm_without_key_is_not_a_successful_model_test():
    with patch("httpx.AsyncClient.get", AsyncMock()) as get:
        result = await ProviderService()._ping_single_model("vllm", "configured-model", "http://vllm.local/v1", None)
    assert not result["success"]
    get.assert_not_awaited()


def test_seed_has_no_embedded_credentials():
    for provider in STANDARD_QNU_PROVIDERS:
        if provider["provider_type"] in {"paddleocr", "vllm"}:
            assert not provider["api_key"]
            assert provider["extra_config"]["api_keys"] == []


@pytest.mark.asyncio
async def test_paddle_model_check_is_health_only():
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=httpx.Response(503))) as get:
        result = await ProviderService()._ping_single_model("paddleocr", "custom-ocr", "http://ocr.local", None)
    assert not result["success"]
    assert result["model_name"] == "custom-ocr"
    get.assert_awaited_once_with("http://ocr.local/health")


@pytest.mark.asyncio
async def test_vllm_key_is_sent_and_unauthorized_is_not_success():
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=httpx.Response(401))) as get:
        success, _, _ = await ProviderService()._ping_provider_api("vllm", "http://vllm.local/v1", "test-only-secret")
    assert not success
    get.assert_awaited_once_with("http://vllm.local/v1/models", headers={"Authorization": "Bearer test-only-secret"})
