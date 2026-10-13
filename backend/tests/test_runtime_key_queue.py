"""Busy credentials wait without bypassing authentication or quota checks."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.modelops.services.provider_key_rotation_service import (
    KeyAcquireResult,
    LeasedProviderKey,
    ProviderKeyRotationService,
)
from app.workers.leased_execution import is_retryable_failure


@pytest.mark.asyncio
async def test_busy_key_waits_until_released() -> None:
    service = ProviderKeyRotationService()
    lease = LeasedProviderKey("key", "provider", "Key", "test", None, "lease")
    service.acquire = AsyncMock(side_effect=[
        KeyAcquireResult(managed=True, lease=None, busy=True),
        KeyAcquireResult(managed=True, lease=lease),
    ])
    with patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
        result = await service.acquire_wait(AsyncMock(), "provider", timeout_seconds=10)
    assert result.lease is lease
    sleep.assert_awaited_once()


@pytest.mark.asyncio
async def test_unusable_keys_do_not_wait_or_retry() -> None:
    service = ProviderKeyRotationService()
    service.acquire = AsyncMock(return_value=KeyAcquireResult(True, None))
    result = await service.acquire_wait(AsyncMock(), "provider", timeout_seconds=10)
    assert result.lease is None
    service.acquire.assert_awaited_once()
    assert not is_retryable_failure(AppException("No valid keys", code="MODEL_PROVIDER_KEYS_UNAVAILABLE"))


@pytest.mark.asyncio
async def test_busy_timeout_is_retryable_not_invalid_key() -> None:
    service = ProviderKeyRotationService()
    service.acquire = AsyncMock(return_value=KeyAcquireResult(True, None, busy=True))
    with pytest.raises(AppException) as error:
        await service.acquire_wait(AsyncMock(), "provider", timeout_seconds=0)
    assert error.value.code == "MODEL_PROVIDER_KEY_BUSY"
    assert is_retryable_failure(error.value)


@pytest.mark.asyncio
async def test_cancel_during_wait_does_not_acquire_or_change_key() -> None:
    service = ProviderKeyRotationService()
    service.acquire = AsyncMock(return_value=KeyAcquireResult(True, None, busy=True))
    with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=asyncio.CancelledError), pytest.raises(asyncio.CancelledError):
        await service.acquire_wait(AsyncMock(), "provider", timeout_seconds=10)
    service.acquire.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_failure_in_wait_does_not_fall_back() -> None:
    service = ProviderKeyRotationService()
    service.acquire = AsyncMock(side_effect=ConnectionError("database down"))
    with pytest.raises(ConnectionError):
        await service.acquire_wait(AsyncMock(), "provider", timeout_seconds=10)


@pytest.mark.asyncio
async def test_cancel_after_acquire_releases_credential() -> None:
    service = ProviderKeyRotationService()
    lease = LeasedProviderKey("key", "provider", "Key", "test", None, "lease")
    service.acquire = AsyncMock(side_effect=[KeyAcquireResult(True, None, True), KeyAcquireResult(True, lease)])
    service.release = AsyncMock()
    with patch("asyncio.sleep", new_callable=AsyncMock), patch(
        "app.modules.jobs.ingestion_progress.report_progress", new_callable=AsyncMock,
        side_effect=[None, asyncio.CancelledError],
    ), pytest.raises(asyncio.CancelledError):
        await service.acquire_wait(AsyncMock(), "provider", timeout_seconds=10)
    service.release.assert_awaited_once_with(service.acquire.call_args.args[0], lease)


@pytest.mark.asyncio
async def test_long_embedding_renews_lease_and_stops_heartbeat() -> None:
    from app.modules.modelops.services.model_runtime_resolver import ModelRuntimeConfig
    from app.modules.modelops.services.runtime_key_lease import renew_runtime_key

    runtime = ModelRuntimeConfig("provider", "custom", "selected-model", None, "test", None, 90, "key", "lease")
    renewed = asyncio.Event()
    block = asyncio.Event()
    calls = 0

    async def sleep(_: float) -> None:
        nonlocal calls
        calls += 1
        if calls > 1:
            await block.wait()

    async def renew(*_: object) -> bool:
        renewed.set()
        return True

    session = AsyncMock()
    with patch("app.modules.modelops.services.runtime_key_lease.AsyncSessionFactory", return_value=session), patch(
        "asyncio.sleep", side_effect=sleep,
    ), patch("app.modules.modelops.services.runtime_key_lease.provider_key_rotation_service.renew", side_effect=renew) as heartbeat:
        async with renew_runtime_key(runtime):
            await asyncio.wait_for(renewed.wait(), timeout=1)
        assert heartbeat.await_count == 1
        assert heartbeat.call_args.args[1].id == "key"
        assert heartbeat.call_args.args[2] == 120
