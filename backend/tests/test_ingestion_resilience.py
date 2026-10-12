"""Progress must reflect completed milestones; retry configuration must reach ARQ."""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from arq.worker import get_kwargs

from app.core.exceptions import AppException


def test_worker_uses_supported_retry_and_timeout_settings():
    from app.workers.arq_worker import WorkerSettings

    options = get_kwargs(WorkerSettings)
    assert options.get("max_tries") == 3
    assert options["job_timeout"] >= 900


def test_success_is_independent_of_other_items_and_failure_is_not_100():
    from app.modules.jobs.ingestion_progress import item_progress

    assert item_progress("succeeded", "completed", 90) == 100
    assert item_progress("processing", "parse", 20) == 20
    assert item_progress("failed", "failed", 70) == 70
    assert item_progress("queued", "snapshot", 90) == 0


def test_retry_classifies_wrapped_transport_failure_but_not_bad_content():
    from app.workers.leased_execution import is_retryable_failure

    outer = AppException("Index failed", code="VECTOR_INDEXING_FAILED", status_code=502)
    outer.__cause__ = TimeoutError("temporary transport failure")
    assert is_retryable_failure(outer)
    assert not is_retryable_failure(AppException("No text", code="EMPTY_EXTRACTED_TEXT", status_code=422))


@pytest.mark.asyncio
async def test_shared_capacity_bounds_twenty_simultaneous_requests():
    from redis.asyncio import Redis

    from app.core.config import settings
    from app.core.provider_capacity import provider_slot

    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    resource = f"test376-{uuid.uuid4().hex}"
    active, peak = 0, 0

    async def request():
        nonlocal active, peak
        async with provider_slot("ocr", resource, 10, redis=client):
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
    try:
        await asyncio.gather(*(request() for _ in range(20)))
        assert peak <= settings.OCR_MAX_CONCURRENT
        assert active == 0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_capacity_failure_never_bypasses_limit():
    from app.core.provider_capacity import provider_slot

    client = AsyncMock()
    client.eval.side_effect = OSError("Redis unavailable")
    with (
        patch("app.core.provider_capacity.get_redis_client", return_value=client),
        pytest.raises(AppException) as error,
    ):
        async with provider_slot("ocr", "test376-offline", 10):
            pytest.fail("Must not call AI without capacity coordination")
    assert error.value.code == "PROVIDER_CAPACITY_UNAVAILABLE"


@pytest.mark.asyncio
async def test_backlog_full_is_rejected_before_enqueue():
    from app.core.config import settings
    from app.modules.jobs.ingestion_admission import check_ingestion_capacity

    db = AsyncMock()
    db.scalar.return_value = settings.INGESTION_MAX_PENDING_PER_TENANT
    with pytest.raises(AppException) as error:
        await check_ingestion_capacity(db, "tenant", 1)
    assert error.value.code == "INGESTION_QUEUE_FULL"


@pytest.mark.asyncio
async def test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item():
    from datetime import UTC, datetime, timedelta

    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.core.config import settings
    from app.modules.jobs.ingestion_recovery import recover_ingestion_jobs
    from app.modules.jobs.models import JobRecord
    from app.modules.knowledge.models import (
        KnowledgeCollection,
        KnowledgeImportBatch,
        KnowledgeImportItem,
    )

    tenant = f"test376_{uuid.uuid4().hex[:12]}"
    engine = create_async_engine(settings.DATABASE_URL)
    redis = Redis.from_url(settings.REDIS_URL)
    lease_key = None
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False,
                                        join_transaction_mode="create_savepoint") as db:
                    col = KnowledgeCollection(name="Recovery fixture", module_code=tenant, tenant_id=tenant)
                    db.add(col)
                    await db.flush()
                    batch = KnowledgeImportBatch(collection_id=col.id, tenant_id=tenant, status="processing", total_count=3)
                    db.add(batch)
                    await db.flush()
                    jobs, items = [], []
                    for number in range(3):
                        item = KnowledgeImportItem(batch_id=batch.id, origin_document_id=f"fixture{number}",
                            origin_file_hash=f"fixture{number}", origin_title="Fixture", origin_file_name="fixture.pdf",
                            origin_file_type="pdf", status="succeeded" if number == 2 else "processing", phase="parse")
                        db.add(item)
                        await db.flush()
                        old = datetime.now(UTC) - timedelta(seconds=settings.WORKER_JOB_TIMEOUT_SECONDS + 200)
                        job = JobRecord(job_type="knowledge_source_ingestion", collection_id=col.id, tenant_id=tenant,
                            status="running", phase="parse", heartbeat_at=old, updated_at=old,
                            payload={"item_id": item.id, "batch_id": batch.id})
                        db.add(job)
                        jobs.append(job)
                        items.append(item)
                    await db.commit()
                    lease_key = f"qnu:job-execution:{jobs[1].id}"
                    await redis.set(lease_key, "test-owner", ex=60)
                    assert await recover_ingestion_jobs(db, redis, tenant_id=tenant) == 1
                    assert jobs[0].status == "queued"
                    assert jobs[0].attempt == 1
                    assert items[0].status == "queued"
                    assert jobs[1].status == "running"
                    assert items[1].status == "processing"
                    assert jobs[2].status == "completed"
                    assert items[2].status == "succeeded"
                    assert batch.succeeded_count == 1
                    assert batch.processing_count == 1
                    from contextlib import asynccontextmanager

                    from app.modules.jobs import ingestion_progress
                    from app.modules.knowledge.services.import_batch_service import (
                        import_batch_service,
                    )

                    @asynccontextmanager
                    async def fixture_session():
                        yield db
                    token = ingestion_progress.current_job.set((jobs[1].id, 0))
                    try:
                        with patch.object(ingestion_progress, "AsyncSessionFactory", fixture_session):
                            await ingestion_progress.report_progress("normalize", 65)
                            await ingestion_progress.report_progress("parse", 20)
                    finally:
                        ingestion_progress.current_job.reset(token)
                    loaded = await import_batch_service.get_import_batch(col.id, batch.id, tenant_id=tenant, db=db)
                    progress = {item.id: item.progress for item in loaded.items}
                    assert progress[items[0].id] == 0
                    assert progress[items[1].id] == 65
                    assert progress[items[2].id] == 100
                    token = ingestion_progress.current_job.set((jobs[0].id, 0))
                    try:
                        with (
                            patch.object(ingestion_progress, "AsyncSessionFactory", fixture_session),
                            pytest.raises(AppException) as stale,
                        ):
                            await ingestion_progress.report_progress("parse", 20)
                        assert stale.value.code == "JOB_LEASE_LOST"
                    finally:
                        ingestion_progress.current_job.reset(token)
            finally:
                await transaction.rollback()
    finally:
        if lease_key:
            await redis.delete(lease_key)
        await redis.aclose()
        await engine.dispose()
