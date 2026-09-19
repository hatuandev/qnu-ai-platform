"""Tests for ModelOps Usage Tracking, Pricing & Real Cost Observability."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.modelops.pricing import calculate_cost_usd
from app.modules.modelops.service import modelops_service


def test_pricing_calculation():
    # OpenAI gpt-4o-mini: $0.15/1M prompt, $0.60/1M completion
    cost_mini = calculate_cost_usd("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost_mini == 0.75

    # Gemini 1.5 Flash: $0.075/1M prompt, $0.30/1M completion
    cost_flash = calculate_cost_usd("gemini-1.5-flash", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost_flash == 0.375

    # Local BAAI BGE-M3: $0.0
    cost_local = calculate_cost_usd("bge-m3", prompt_tokens=10_000, completion_tokens=0)
    assert cost_local == 0.0

    # Mistral OCR: fixed 0.001
    cost_ocr = calculate_cost_usd("mistral-ocr-latest")
    assert cost_ocr == 0.001


@pytest.mark.asyncio
async def test_record_usage_log():
    db = AsyncMock()
    db.add = MagicMock()
    mock_quota = MagicMock()
    mock_quota.tokens_used = 100
    mock_quota.cost_used_usd = 0.05

    modelops_service.get_or_create_quota = AsyncMock(return_value=mock_quota)

    log = await modelops_service.record_usage_log(
        db,
        tenant_id="tenant_qnu",
        assistant_id="ast_admissions",
        conversation_id="conv_123",
        provider="openai",
        model_name="gpt-4o-mini",
        prompt_tokens=500,
        completion_tokens=200,
        latency_ms=450.0,
        status="success",
    )

    assert log.tenant_id == "tenant_qnu"
    assert log.assistant_id == "ast_admissions"
    assert log.total_tokens == 700
    assert log.cost_usd > 0
    assert log.latency_ms == 450.0
    assert mock_quota.tokens_used == 800
    db.add.assert_called_once()
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_get_usage_statistics_aggregation():
    db = AsyncMock()
    mock_res = MagicMock()

    mock_log1 = MagicMock()
    mock_log1.provider = "openai"
    mock_log1.model_name = "gpt-4o-mini"
    mock_log1.total_tokens = 1000
    mock_log1.cost_usd = 0.0005
    mock_log1.latency_ms = 300.0
    mock_log1.created_at = None

    mock_log2 = MagicMock()
    mock_log2.provider = "google"
    mock_log2.model_name = "gemini-1.5-flash"
    mock_log2.total_tokens = 2000
    mock_log2.cost_usd = 0.0008
    mock_log2.latency_ms = 250.0
    mock_log2.created_at = None

    mock_res.scalars.return_value.all.return_value = [mock_log1, mock_log2]
    db.execute.return_value = mock_res

    stats = await modelops_service.get_usage_statistics(db, days=7)

    assert stats.total_requests == 2
    assert stats.total_tokens == 3000
    assert stats.total_cost_usd == 0.0013
    assert stats.avg_latency_ms == 275.0
    assert len(stats.models_breakdown) == 2
    assert stats.models_breakdown[0].model_name == "gemini-1.5-flash"
    assert stats.models_breakdown[0].total_tokens == 2000


@pytest.mark.asyncio
async def test_api_usage_stats_endpoint():
    from app.core.database import get_db

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/platform/v1alpha1/modelops/usage-stats?days=30")
            assert resp.status_code == 200
            data = resp.json()
            assert "total_requests" in data
            assert "total_tokens" in data
            assert "total_cost_usd" in data
            assert "avg_latency_ms" in data
            assert "models_breakdown" in data
            assert "daily_usage" in data
    finally:
        app.dependency_overrides.pop(get_db, None)
