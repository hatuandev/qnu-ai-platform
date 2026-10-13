"""Opt-in real PostgreSQL unlimited accounting contract; all changes roll back."""

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.modules.modelops.models import LLMUsageLog, TenantQuota
from app.modules.modelops.services.usage_accounting_service import UsageAccountingService

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(os.getenv("QNU_TEST_UNLIMITED_DB") != "1", reason="Opt-in PostgreSQL rollback fixture"),
]


async def test_new_month_unlimited_records_usage_above_old_limit():
    engine = create_async_engine(settings.DATABASE_URL)
    tenant = f"test_unlimited_{uuid.uuid4().hex[:12]}"
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                async with AsyncSession(
                    bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint",
                ) as db:
                    service = UsageAccountingService()
                    quota = await service.get_or_create_quota(db, tenant)
                    assert quota.monthly_token_limit == 0
                    assert quota.monthly_cost_limit_usd == 0
                    quota.tokens_used = 5_002_480
                    await db.commit()
                    await service.check_quota_available(db, tenant, estimated_tokens=1_000_000)
                    log = await service.record_usage_log(
                        db, tenant_id=tenant, model_name="fixture", prompt_tokens=200, completion_tokens=50,
                    )
                    await db.refresh(quota)
                    assert quota.tokens_used == 5_002_730
                    assert quota.monthly_token_limit == 0
                    assert (await db.execute(select(LLMUsageLog.total_tokens).where(LLMUsageLog.id == log.id))).scalar_one() == 250
            finally:
                await outer.rollback()
        async with engine.connect() as connection:
            assert (await connection.execute(select(TenantQuota.id).where(TenantQuota.tenant_id == tenant))).first() is None
    finally:
        await engine.dispose()
