"""Opt-in concurrency check against PostgreSQL, without any inference calls."""

import asyncio
import os
import uuid

import pytest
from sqlalchemy import delete

from app.core.crypto import encrypt_secret
from app.core.database import AsyncSessionFactory, engine
from app.modules.modelops.models import ModelProviderConfig, ProviderApiKey
from app.modules.modelops.services.provider_key_rotation_service import ProviderKeyRotationService


@pytest.mark.skipif(os.getenv("QNU_TEST_KEY_QUEUE_DB") != "1", reason="Opt-in PostgreSQL concurrency test")
@pytest.mark.asyncio
async def test_twenty_jobs_share_one_key_without_overlap() -> None:
    provider_id = uuid.uuid4().hex
    key_id = uuid.uuid4().hex
    service = ProviderKeyRotationService()
    in_flight = 0
    peak = 0
    completed = 0
    await engine.dispose()
    try:
        async with AsyncSessionFactory() as db:
            db.add(ModelProviderConfig(id=provider_id, name="Queue regression only", provider_type="custom"))
            await db.flush()
            db.add(ProviderApiKey(
                id=key_id, provider_id=provider_id, name="Queue regression only",
                api_key_encrypted=encrypt_secret("non-network-test-credential"),
                api_key_masked="test", status="active", is_active=True,
            ))
            await db.commit()

        async def job() -> None:
            nonlocal in_flight, peak, completed
            async with AsyncSessionFactory() as db:
                acquired = await service.acquire_wait(db, provider_id, timeout_seconds=30)
                assert acquired.lease is not None
                in_flight += 1
                peak = max(peak, in_flight)
                try:
                    await asyncio.sleep(0.015)
                finally:
                    assert await service.complete_success(db, acquired.lease, total_tokens=1)
                    in_flight -= 1
                completed += 1

        await asyncio.gather(*(job() for _ in range(20)))
        assert peak == 1
        assert completed == 20
        async with AsyncSessionFactory() as db:
            key = await db.get(ProviderApiKey, key_id)
            assert key.usage_tokens == 20
            assert key.lease_until is None
            key.status = "invalid"
            await db.commit()
            assert (await service.acquire_wait(db, provider_id, timeout_seconds=30)).lease is None
    finally:
        async with AsyncSessionFactory() as db:
            await db.execute(delete(ModelProviderConfig).where(ModelProviderConfig.id == provider_id))
            await db.commit()
        await engine.dispose()
