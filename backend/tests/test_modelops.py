"""Unit & Integration Tests for ModelOps, LLM Adapters, Circuit Breaker, Fallbacks & Quotas."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import AppException
from app.main import app
from app.modules.modelops.circuit_breaker import CircuitBreaker, CircuitBreakerState
from app.modules.modelops.models import TenantQuota
from app.modules.modelops.providers import (
    GeminiAdapter,
    LocalVLLMAdapter,
    OpenAIAdapter,
    get_llm_adapter,
)
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service


def test_circuit_breaker_lifecycle():
    """Verify Circuit Breaker trips from CLOSED to OPEN after reaching failure threshold."""
    cb = CircuitBreaker("test-provider", failure_threshold=3, recovery_timeout_seconds=2.0)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 1st failure
    cb.record_failure(ValueError("Connection timeout"))
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 2nd failure
    cb.record_failure(ValueError("500 Internal Error"))
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 3rd failure -> Trips to OPEN
    cb.record_failure(ValueError("Rate limit 429"))
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.can_execute() is False

    # Simulate recovery timeout passing
    cb.last_failure_time -= 3.0  # simulate 3s passed
    assert cb.can_execute() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # Success restores to CLOSED
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0


def test_llm_adapter_factory():
    """Verify Adapter Factory constructs corresponding provider instances."""
    adapter_openai = get_llm_adapter("openai", "gpt-4o-mini", api_key="mock")
    assert isinstance(adapter_openai, OpenAIAdapter)
    assert adapter_openai.provider_type == "openai"

    adapter_gemini = get_llm_adapter("gemini", "gemini-1.5-flash", api_key="mock")
    assert isinstance(adapter_gemini, GeminiAdapter)
    assert adapter_gemini.provider_type == "gemini"

    adapter_local = get_llm_adapter("local_vllm", "qwen2.5-7b-instruct")
    assert isinstance(adapter_local, LocalVLLMAdapter)
    assert adapter_local.provider_type == "local_vllm"


@pytest.mark.asyncio
async def test_openai_adapter_mock_generation():
    """Verify OpenAI adapter returns valid LLMResponse in mock mode."""
    adapter = OpenAIAdapter(model_name="gpt-4o-mini", api_key="mock")
    messages = [
        ChatMessage(role="user", content="Điểm chuẩn ngành Công nghệ thông tin ĐH Quy Nhơn là gì?")
    ]
    resp = await adapter.generate(messages)
    assert resp.provider == "openai"
    assert resp.model == "gpt-4o-mini"
    assert len(resp.content) > 0
    assert resp.total_tokens > 0


@pytest.mark.asyncio
async def test_dynamic_fallback_when_primary_fails():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    req = LLMGenerateRequest(
        messages=[ChatMessage(role="user", content="Tư vấn tuyển sinh")],
        tenant_id="test-tenant",
    )

    # Patch quota check to return fresh quota
    mock_quota = TenantQuota(
        tenant_id="test-tenant",
        month_period="2026-09",
        monthly_token_limit=1_000_000,
        tokens_used=100,
    )

    with (
        patch.object(modelops_service, "check_quota_available", new_callable=AsyncMock) as mock_chk,
        patch(
            "app.modules.modelops.service.get_llm_adapter"
        ) as mock_factory,
    ):
        mock_chk.return_value = mock_quota

        # 1st call (Primary) fails, 2nd call (Secondary) succeeds
        primary_adapter = AsyncMock()
        primary_adapter.generate.side_effect = RuntimeError("OpenAI 503 Outage")

        secondary_adapter = AsyncMock()
        from app.modules.modelops.providers.base import LLMResponse

        secondary_adapter.generate.return_value = LLMResponse(
            content="Phản hồi từ mô hình dự phòng Gemini",
            provider="gemini",
            model="gemini-1.5-flash",
            prompt_tokens=20,
            completion_tokens=30,
            total_tokens=50,
        )

        mock_factory.side_effect = [primary_adapter, secondary_adapter]

        res = await modelops_service.generate(mock_db, req)

    assert res.provider == "gemini"
    assert res.is_fallback is True
    assert "Gemini" in res.content


@pytest.mark.asyncio
async def test_quota_exceeded_blocking():
    """Verify Quota Manager halts execution with HTTP 429 when tenant exceeds monthly token cap."""
    mock_db = AsyncMock()
    mock_quota = TenantQuota(
        tenant_id="overlimit-tenant",
        month_period="2026-09",
        monthly_token_limit=10_000,
        tokens_used=10_000,
    )

    with patch.object(modelops_service, "get_or_create_quota", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_quota

        with pytest.raises(AppException) as exc_info:
            await modelops_service.check_quota_available(
                mock_db, tenant_id="overlimit-tenant", estimated_tokens=500
            )

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "QUOTA_EXCEEDED"


@pytest.mark.asyncio
async def test_api_list_providers():
    """Verify GET /platform/v1alpha1/modelops/providers returns active provider cascade."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    )

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/platform/v1alpha1/modelops/providers")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    providers = response.json()
    assert len(providers) >= 3
    assert providers[0]["provider_type"] == "openai"
    assert providers[1]["provider_type"] == "gemini"
    assert providers[2]["provider_type"] == "local_vllm"


@pytest.mark.asyncio
async def test_api_modelops_generate():
    """Verify POST /platform/v1alpha1/modelops/generate invokes LLM successfully."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        mock_quota = TenantQuota(
            tenant_id="qnu-default",
            month_period="2026-09",
            monthly_token_limit=1_000_000,
            tokens_used=0,
        )
        with patch.object(modelops_service, "get_or_create_quota", new_callable=AsyncMock) as mock_q:
            mock_q.return_value = mock_quota

            payload = {
                "messages": [{"role": "user", "content": "Xin chào Trợ lý AI QNU!"}],
                "tenant_id": "qnu-default",
                "temperature": 0.2,
                "max_tokens": 500,
            }

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/platform/v1alpha1/modelops/generate", json=payload)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] in ("openai", "gemini", "local_vllm")
    assert len(data["content"]) > 0
    assert data["total_tokens"] > 0
