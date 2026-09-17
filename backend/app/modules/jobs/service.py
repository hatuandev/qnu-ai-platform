"""Jobs Service — Enqueue, Track, Cancel & Retry ARQ Background Jobs."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.jobs.models import JobRecord

logger = logging.getLogger(__name__)
settings = get_settings()

ARQ_FUNCTIONS: dict[str, str] = {
    "ingestion": "task_document_ingestion",
    "reindex": "task_reindex_collection",
    "export": "task_export_document",
}

TERMINAL_STATUSES = ("completed", "failed", "cancelled")


async def enqueue_arq_job(function_name: str, *args) -> str | None:
    """Enqueue an ARQ job; returns the broker job id (None when Redis is down)."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        try:
            job = await pool.enqueue_job(function_name, *args)
            return job.job_id if job else None
        finally:
            await pool.close()
    except Exception as exc:
        logger.warning("ARQ enqueue failed for %s (worker may be offline): %s", function_name, exc)
        return None


class JobsService:
    """Service managing persistent background job records and ARQ dispatch."""

    async def enqueue_job(
        self,
        db: AsyncSession,
        job_type: str,
        collection_id: str | None = None,
        document_id: str | None = None,
        params: dict | None = None,
        tenant_id: str = "tenant_qnu",
    ) -> JobRecord:
        if job_type not in ARQ_FUNCTIONS:
            raise AppException(
                f"Loại job '{job_type}' không được hỗ trợ.",
                code="job_type_unsupported",
                status_code=400,
                details={"supported": sorted(ARQ_FUNCTIONS)},
            )
        record = JobRecord(
            job_type=job_type,
            status="queued",
            collection_id=collection_id,
            document_id=document_id,
            payload=dict(params or {}),
            tenant_id=tenant_id,
        )
        db.add(record)
        await db.flush()

        arq_job_id = await enqueue_arq_job(ARQ_FUNCTIONS[job_type], record.id)
        if arq_job_id:
            record.arq_job_id = arq_job_id
        else:
            record.error = "Worker offline — job chờ worker khởi động để thực thi."

        await db.commit()
        await db.refresh(record)
        logger.info("Enqueued job id=%s type=%s arq=%s", record.id, job_type, arq_job_id)
        return record

    async def list_jobs(
        self, db: AsyncSession, status: str | None = None, limit: int = 50
    ) -> list[JobRecord]:
        query = select(JobRecord).order_by(JobRecord.created_at.desc()).limit(limit)
        if status:
            query = query.where(JobRecord.status == status)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_job(self, db: AsyncSession, job_id: str) -> JobRecord:
        res = await db.execute(select(JobRecord).where(JobRecord.id == job_id))
        job = res.scalar_one_or_none()
        if not job:
            raise EntityNotFoundError(
                f"Job '{job_id}' không tồn tại.", details={"job_id": job_id}
            )
        return job

    async def get_stats(self, db: AsyncSession) -> dict[str, int]:
        res = await db.execute(
            select(JobRecord.status, func.count(JobRecord.id)).group_by(JobRecord.status)
        )
        counts: dict[str, int] = {row[0]: row[1] for row in res.all()}
        total = sum(counts.values())
        return {
            "total": total,
            "queued": counts.get("queued", 0),
            "running": counts.get("running", 0),
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "cancelled": counts.get("cancelled", 0),
        }

    async def cancel_job(self, db: AsyncSession, job_id: str) -> JobRecord:
        job = await self.get_job(db, job_id)
        if job.status in TERMINAL_STATUSES:
            raise AppException(
                f"Job '{job_id}' đã kết thúc ({job.status}), không thể hủy.",
                code="job_already_terminal",
                status_code=409,
            )
        job.status = "cancelled"
        job.error = "Đã hủy bởi người dùng (cooperative cancel)."
        await db.commit()
        await db.refresh(job)
        return job

    async def retry_job(self, db: AsyncSession, job_id: str) -> JobRecord:
        job = await self.get_job(db, job_id)
        if job.status not in ("failed", "cancelled"):
            raise AppException(
                f"Chỉ retry job failed/cancelled (hiện tại: {job.status}).",
                code="job_not_retryable",
                status_code=409,
            )
        job.status = "queued"
        job.progress = 0.0
        job.error = None
        job.result = {}
        await db.flush()
        arq_job_id = await enqueue_arq_job(ARQ_FUNCTIONS[job.job_type], job.id)
        if arq_job_id:
            job.arq_job_id = arq_job_id
        await db.commit()
        await db.refresh(job)
        return job


jobs_service = JobsService()
