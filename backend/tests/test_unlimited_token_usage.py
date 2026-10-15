"""Unlimited internal budgets retain accounting and upstream safety checks."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import AppException
from app.modules.modelops.models import TenantQuota
from app.modules.modelops.services.key_rotation import classify_key_failure
from app.modules.modelops.services.usage_accounting_service import UsageAccountingService


@pytest.mark.asyncio
async def test_unlimited_month_accepts_usage_above_old_limit(monkeypatch):
    service = UsageAccountingService()
    quota = TenantQuota(
        tenant_id="unlimited", month_period="2026-10", monthly_token_limit=0,
        tokens_used=5_002_480, cost_used_usd=200, is_blocked=False,
    )
    monkeypatch.setattr(service, "get_or_create_quota", AsyncMock(return_value=quota))
    assert await service.check_quota_available(AsyncMock(), "unlimited", 1_000_000) is quota


@pytest.mark.asyncio
async def test_unlimited_still_records_real_usage(monkeypatch):
    service = UsageAccountingService()
    quota = TenantQuota(tokens_used=5_002_480, cost_used_usd=1, monthly_token_limit=0)
    monkeypatch.setattr(service, "get_or_create_quota", AsyncMock(return_value=quota))
    db = AsyncMock()
    db.add = MagicMock()
    log = await service.record_usage_log(db, model_name="fixture", prompt_tokens=200, completion_tokens=50)
    assert log.total_tokens == 250
    assert quota.tokens_used == 5_002_730
    assert quota.monthly_token_limit == 0
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unlimited_does_not_unlock_blocked_account(monkeypatch):
    service = UsageAccountingService()
    quota = TenantQuota(monthly_token_limit=0, is_blocked=True)
    monkeypatch.setattr(service, "get_or_create_quota", AsyncMock(return_value=quota))
    with pytest.raises(AppException) as error:
        await service.check_quota_available(AsyncMock(), "blocked")
    assert error.value.code == "TENANT_BLOCKED"


@pytest.mark.asyncio
async def test_usage_preflight_does_not_hide_database_failure(monkeypatch):
    service = UsageAccountingService()
    monkeypatch.setattr(service, "get_or_create_quota", AsyncMock(side_effect=ConnectionError("DB unavailable")))
    with pytest.raises(ConnectionError):
        await service.check_quota_available(AsyncMock(), "unlimited")


def test_new_month_defaults_are_unlimited():
    assert Settings.model_fields["DEFAULT_MONTHLY_TOKEN_QUOTA"].default == 0
    assert Settings.model_fields["DEFAULT_MONTHLY_COST_QUOTA_USD"].default == 0
    assert TenantQuota.__table__.c.monthly_token_limit.default.arg == 0
    assert TenantQuota.__table__.c.monthly_cost_limit_usd.default.arg == 0


def test_seeded_provider_keys_have_no_internal_cap():
    from app.modules.modelops.services.provider_service import STANDARD_QNU_PROVIDERS

    for provider in STANDARD_QNU_PROVIDERS:
        for key in provider.get("extra_config", {}).get("api_keys", []):
            assert key.get("quota_limit") is None


@pytest.mark.asyncio
async def test_api_reports_zero_limit_without_dividing_by_zero(monkeypatch):
    from app.modules.modelops.router import get_tenant_quota
    from app.modules.modelops.service import modelops_service

    quota = TenantQuota(
        tenant_id="unlimited", month_period="2026-10", monthly_token_limit=0,
        monthly_cost_limit_usd=0, tokens_used=5_002_480, cost_used_usd=1, is_blocked=False,
    )
    monkeypatch.setattr(modelops_service, "get_or_create_quota", AsyncMock(return_value=quota))
    response = await get_tenant_quota(AsyncMock())
    assert response.monthly_token_limit == 0
    assert response.usage_percent == 0
    assert response.tokens_used == 5_002_480


@pytest.mark.parametrize("status,payload,state", [
    (429, {"error": {"code": "rate_limit_exceeded"}}, "rate_limited"),
    (429, {"error": {"code": "insufficient_quota"}}, "exhausted"),
    (401, {"error": {"code": "invalid_api_key"}}, "invalid"),
])
def test_external_provider_limits_still_apply(status, payload, state):
    request = httpx.Request("POST", "https://fixture/chat")
    response = httpx.Response(status, request=request, json=payload)
    error = httpx.HTTPStatusError("Provider rejected request", request=request, response=response)
    assert classify_key_failure(error).state == state
