"""Recover abandoned ingestion work only after its distributed lease is gone."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeImportBatch,
    KnowledgeImportItem,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.services.import_state_service import refresh_batch_counts


async def recover_ingestion_jobs(db: AsyncSession, redis, limit: int = 100, tenant_id: str | None = None) -> int:
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.WORKER_JOB_TIMEOUT_SECONDS + 120)
    statement = select(JobRecord).where(
        JobRecord.job_type.in_(["knowledge_source_ingestion", "knowledge_index_build"]),
        or_(
            (JobRecord.status == "running") & (JobRecord.updated_at < cutoff),
            (JobRecord.status == "failed") & (JobRecord.result["retryable"].astext == "true"),
            (JobRecord.status == "queued") & (JobRecord.dispatch_status == "dispatched") & (JobRecord.updated_at < cutoff),
        ),
        JobRecord.cancel_requested.is_(False),
    ).order_by(JobRecord.updated_at).limit(limit).with_for_update(skip_locked=True)
    if tenant_id:
        statement = statement.where(JobRecord.tenant_id == tenant_id)
    jobs = list((await db.scalars(statement)).all())
    recovered = 0
    batches: set[str] = set()
    for job in jobs:
        if await redis.exists(f"qnu:job-execution:{job.id}"):
            continue
        resource = job.document_id or (job.payload or {}).get("binding_id") or job.id
        if await redis.exists(f"qnu:source-execution:{job.tenant_id}:{job.workspace_id}:{job.collection_id}:{resource}"):
            continue
        stale = job.status == "running" and (job.heartbeat_at or job.updated_at) < cutoff
        missing_broker = job.status == "queued" and not await redis.exists(f"arq:job:{job.arq_job_id}")
        retryable = job.status == "failed" and (job.result or {}).get("retryable") is True
        if not stale and not retryable and not missing_broker:
            continue
        retry_after = (job.result or {}).get("retry_after")
        if retry_after and datetime.fromisoformat(retry_after) > datetime.now(UTC):
            continue
        if job.job_type == "knowledge_index_build":
            statement = select(KnowledgeIndexRevision).join(KnowledgeBinding).where(
                KnowledgeIndexRevision.binding_id == (job.payload or {}).get("binding_id"),
                KnowledgeBinding.collection_id == job.collection_id,
                KnowledgeBinding.tenant_id == job.tenant_id,
                KnowledgeBinding.workspace_id == job.workspace_id,
                or_(
                    KnowledgeIndexRevision.source_revision_v2_id == (job.payload or {}).get("source_revision_id"),
                    KnowledgeIndexRevision.source_revision_id == (job.payload or {}).get("source_revision_id"),
                ),
                KnowledgeIndexRevision.status.in_(["building", "validating"]),
            ).with_for_update(of=KnowledgeIndexRevision)
            if (job.payload or {}).get("generation_id"):
                statement = statement.where(KnowledgeIndexRevision.vector_generation_id == job.payload["generation_id"])
            revisions = list((await db.scalars(statement)).all())
            for revision in revisions:
                revision.status, revision.failure_code = "failed", "WORKER_INTERRUPTED"
                revision.failure_detail = "Worker bị gián đoạn; bản phục vụ được giữ nguyên."
            if job.attempt + 1 >= settings.WORKER_MAX_TRIES:
                job.status = "failed"
                job.result = {**(job.result or {}), "retryable": False}
                job.error = "Đã hết số lần tự phục hồi chỉ mục; hãy kiểm tra rồi thử lại."
            else:
                job.status, job.dispatch_status, job.phase = "queued", "pending", "retrying"
                job.attempt += 1
                job.progress, job.heartbeat_at, job.error, job.result = 0, None, None, {}
                recovered += 1
            continue
        item = await db.scalar(select(KnowledgeImportItem).where(
            KnowledgeImportItem.id == (job.payload or {}).get("item_id"),
        ).with_for_update())
        batch = await db.get(KnowledgeImportBatch, item.batch_id) if item else None
        if not batch or batch.tenant_id != job.tenant_id or batch.workspace_id != job.workspace_id or batch.collection_id != job.collection_id:
            job.status, job.error = "failed", "Không tìm thấy mục nạp đúng phạm vi."
            continue
        if batch.status == "cancelled":
            job.status = "cancelled"
            item.status = "skipped"
            batches.add(item.batch_id)
            continue
        if not item or item.status in ("succeeded", "skipped", "review_required"):
            job.status = "completed" if item and item.status != "skipped" else "cancelled"
            job.progress = 100 if item and item.status == "succeeded" else job.progress
            continue
        if job.attempt + 1 >= settings.WORKER_MAX_TRIES:
            job.status = "failed"
            job.error = "Đã hết số lần tự phục hồi; hãy kiểm tra rồi thử lại."
            job.result = {**(job.result or {}), "retryable": False}
            item.status, item.failure_code = "failed", "RECOVERY_EXHAUSTED"
            item.failure_detail = job.error
            batches.add(item.batch_id)
            continue
        item.status, item.phase = "queued", "snapshot"
        item.failure_code = item.failure_detail = None
        item.retry_count += 1
        job.status, job.dispatch_status, job.phase = "queued", "pending", "retrying"
        job.progress, job.heartbeat_at = 0, None
        job.attempt += 1
        job.error = None
        job.result = {}
        batches.add(item.batch_id)
        recovered += 1
    await db.commit()
    for batch_id in batches:
        await refresh_batch_counts(db, batch_id)
    return recovered
