from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.modules.modelops.models import ProviderApiKey
from app.modules.modelops.services.provider_key_rotation_service import (
    LeasedProviderKey,
    provider_key_rotation_service,
)


@pytest.mark.asyncio
async def test_database_failure_does_not_bypass_managed_pool() -> None:
    db = AsyncMock()
    db.execute.side_effect = SQLAlchemyError("database unavailable")
    with pytest.raises(SQLAlchemyError):
        await provider_key_rotation_service.acquire(db, "provider-1")
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_renew_checks_current_lease_ownership() -> None:
    db = AsyncMock()
    result = MagicMock()
    db.execute.return_value = result
    lease = LeasedProviderKey("key-1", "provider-1", "Key", "secret", None, "ownership-token")
    result.rowcount = 1
    assert await provider_key_rotation_service.renew(db, lease, 150)
    result.rowcount = 0
    assert not await provider_key_rotation_service.renew(db, lease, 150)


def _result(*, scalar: object = None, scalar_one_or_none: object = None) -> MagicMock:
    result = MagicMock()
    result.scalar_one.return_value = scalar
    result.scalar_one_or_none.return_value = scalar_one_or_none
    return result


@pytest.mark.asyncio
async def test_acquire_sets_a_lease_and_success_updates_usage() -> None:
    key = ProviderApiKey(
        id="key-1",
        provider_id="provider-1",
        name="Key 1",
        api_key_encrypted="secret-1",
        api_key_masked="••••••••",
        priority=1,
        is_active=True,
        status="active",
        usage_tokens=0,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [
        _result(scalar=1),
        _result(),
        _result(),
        _result(scalar_one_or_none=key),
    ]

    acquired = await provider_key_rotation_service.acquire(db, "provider-1", estimated_tokens=100)

    assert acquired.managed is True
    assert acquired.lease is not None
    assert acquired.lease.id == "key-1"
    assert key.lease_token == acquired.lease.lease_token
    assert key.lease_until is not None

    db.execute.side_effect = [_result(scalar_one_or_none=key)]
    completed = await provider_key_rotation_service.complete_success(
        db, acquired.lease, total_tokens=42
    )

    assert completed is True
    assert key.usage_tokens == 42
    assert key.lease_token is None
    assert key.status == "active"
    assert [call.args[0].event_type for call in db.add.call_args_list] == ["selected", "success"]
    assert db.add.call_args_list[-1].args[0].tokens == 42


@pytest.mark.asyncio
async def test_rate_limit_failure_cools_down_the_leased_key() -> None:
    key = ProviderApiKey(
        id="key-2",
        provider_id="provider-1",
        name="Key 2",
        api_key_encrypted="secret-2",
        api_key_masked="••••••••",
        priority=1,
        is_active=True,
        status="active",
        usage_tokens=0,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [
        _result(scalar=1),
        _result(),
        _result(),
        _result(scalar_one_or_none=key),
    ]
    acquired = await provider_key_rotation_service.acquire(db, "provider-1")
    assert acquired.lease is not None

    response = httpx.Response(
        429,
        headers={"Retry-After": "9"},
        request=httpx.Request("POST", "https://provider.example/v1"),
    )
    error = httpx.HTTPStatusError("rate limited", request=response.request, response=response)
    db.execute.side_effect = [_result(scalar_one_or_none=key)]
    failure = await provider_key_rotation_service.complete_failure(db, acquired.lease, error)

    assert failure.state == "rate_limited"
    assert key.status == "rate_limited"
    assert key.cooldown_until is not None
    assert key.lease_token is None

    event = db.add.call_args_list[-1].args[0]
    assert event.event_type == "rate_limited"
    assert event.reason == failure.reason
    assert "secret" not in event.reason
