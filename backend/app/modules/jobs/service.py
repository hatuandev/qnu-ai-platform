"""Jobs Service — Enqueue, Track, Cancel & Retry ARQ Background Jobs."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import delete, func, select
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
    "document_revision_parse": "task_document_revision_parse",
    "knowledge_index_build": "task_knowledge_index_build",
    "knowledge_garbage_collection": "task_knowledge_garbage_collection",
}

TERMINAL_STATUSES = ("completed", "failed", "cancelled")


async def enqueue_arq_job(
    function_name: str,
    *args,
    broker_job_id: str | None = None,
) -> str | None:
    """Enqueue an ARQ job; returns the broker job id (None when Redis is down)."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        try:
            job = await pool.enqueue_job(
                function_name,
                *args,
                _job_id=broker_job_id,
            )
            # ARQ returns None when the deterministic ID already exists. That is a
            # successful idempotent dispatch, not an infrastructure failure.
            return job.job_id if job else broker_job_id
        finally:
            await pool.aclose()
    except Exception as exc:
        logger.warning("ARQ enqueue failed for %s (worker may be offline): %s", function_name, exc)
        return None


async def is_job_cancelled(job_id: str, db: AsyncSession | None = None) -> bool:
    """Reliably check whether a job has been cancelled by querying PostgreSQL directly.

    If an active db session is passed, reuses it with populate_existing=True.
    Otherwise uses a fresh short-lived session to avoid stale identity-map caching.
    """
    if not job_id:
        return False

    stmt = (
        select(JobRecord.status, JobRecord.cancel_requested)
        .where(JobRecord.id == job_id)
        .execution_options(populate_existing=True)
    )

    def _extract_cancellation_state(row: Any) -> bool:
        if row is None:
            return True
        if hasattr(row, "status"):
            status = getattr(row, "status", None)
            cancel_requested = bool(getattr(row, "cancel_requested", False))
        elif isinstance(row, (tuple, list)):
            status = row[0]
            cancel_requested = bool(row[1]) if len(row) > 1 else False
        else:
            status = getattr(row, "status", None)
            cancel_requested = bool(getattr(row, "cancel_requested", False))
        return status == "cancelled" or bool(cancel_requested)

    if db is not None:
        res = await db.execute(stmt)
        row = res.first()
        return _extract_cancellation_state(row)

    from app.core.database import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        res = await session.execute(stmt)
        row = res.first()
        return _extract_cancellation_state(row)


class JobsService:
    """Service managing persistent background job records and ARQ dispatch."""

    @staticmethod
    def _broker_job_id(job: JobRecord) -> str:
        return f"{job.id}:attempt:{job.attempt or 0}"

    async def enqueue_job(
        self,
        db: AsyncSession,
        job_type: str,
        collection_id: str | None = None,
        document_id: str | None = None,
        params: dict | None = None,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        idempotency_key: str | None = None,
        request_hash: str | None = None,
        correlation_id: str | None = None,
        actor: Any | None = None,
    ) -> JobRecord:
        if job_type not in ARQ_FUNCTIONS:
            raise AppException(
                f"Loại job '{job_type}' không được hỗ trợ.",
                code="job_type_unsupported",
                status_code=400,
                details={"supported": sorted(ARQ_FUNCTIONS)},
            )
        resolved_tenant_id = (
            getattr(actor, "tenant_id", None)
            or tenant_id
            or "default"
        )
        resolved_workspace_id = (
            getattr(actor, "workspace_id", None)
            or workspace_id
            or "default"
        )
        record = JobRecord(
            job_type=job_type,
            status="queued",
            collection_id=collection_id,
            document_id=document_id,
            payload=dict(params or {}),
            tenant_id=resolved_tenant_id,
            workspace_id=resolved_workspace_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            correlation_id=correlation_id,
            dispatch_status="pending",
        )
        db.add(record)
        await db.commit()

        arq_job_id = await enqueue_arq_job(
            ARQ_FUNCTIONS[job_type],
            record.id,
            broker_job_id=self._broker_job_id(record),
        )
        if arq_job_id:
            record.arq_job_id = arq_job_id
            record.dispatch_status = "dispatched"
            record.error = None
        else:
            record.dispatch_status = "pending"
            record.error = "Worker offline — job chờ worker khởi động để thực thi."

        await db.commit()
        await db.refresh(record)
        logger.info(
            "Enqueued job id=%s type=%s arq=%s tenant=%s",
            record.id,
            job_type,
            arq_job_id,
            resolved_tenant_id,
        )
        return record

    async def list_jobs(
        self,
        db: AsyncSession,
        status: str | None = None,
        limit: int = 50,
        actor: Any | None = None,
    ) -> list[JobRecord]:
        query = select(JobRecord).order_by(JobRecord.created_at.desc()).limit(limit)
        if actor and getattr(actor, "tenant_id", None):
            query = query.where(JobRecord.tenant_id == actor.tenant_id)
            if getattr(actor, "workspace_id", None):
                query = query.where(JobRecord.workspace_id == actor.workspace_id)
        if status:
            query = query.where(JobRecord.status == status)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_job(
        self,
        db: AsyncSession,
        job_id: str,
        actor: Any | None = None,
    ) -> JobRecord:
        query = select(JobRecord).where(JobRecord.id == job_id)
        if actor and getattr(actor, "tenant_id", None):
            query = query.where(JobRecord.tenant_id == actor.tenant_id)
            if getattr(actor, "workspace_id", None):
                query = query.where(JobRecord.workspace_id == actor.workspace_id)
        res = await db.execute(query)
        job = res.scalar_one_or_none()
        if not job:
            raise EntityNotFoundError(
                f"Job '{job_id}' không tồn tại.", details={"job_id": job_id}
            )
        return job

    async def get_stats(
        self,
        db: AsyncSession,
        actor: Any | None = None,
    ) -> dict[str, int]:
        stmt = select(JobRecord.status, func.count(JobRecord.id))
        if actor and getattr(actor, "tenant_id", None):
            stmt = stmt.where(JobRecord.tenant_id == actor.tenant_id)
            if getattr(actor, "workspace_id", None):
                stmt = stmt.where(JobRecord.workspace_id == actor.workspace_id)
        stmt = stmt.group_by(JobRecord.status)
        res = await db.execute(stmt)
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

    async def cancel_job(
        self,
        db: AsyncSession,
        job_id: str,
        actor: Any | None = None,
    ) -> JobRecord:
        job = await self.get_job(db, job_id, actor=actor)
        if job.status == "cancelled":
            return job
        if job.status in TERMINAL_STATUSES:
            raise AppException(
                f"Job '{job_id}' đã kết thúc ({job.status}), không thể hủy.",
                code="job_already_terminal",
                status_code=409,
            )
        job.status = "cancelled"
        job.cancel_requested = True
        job.error = "Đã hủy bởi người dùng (cooperative cancel)."
        await db.commit()
        await db.refresh(job)
        return job

    async def delete_job(
        self,
        db: AsyncSession,
        job_id: str,
        actor: Any | None = None,
    ) -> bool:
        """Xóa vĩnh viễn bản ghi job khỏi CSDL (theo phạm vi tenant, chỉ cho phép terminal jobs)."""
        job = await self.get_job(db, job_id, actor=actor)
        if job.status not in TERMINAL_STATUSES:
            raise AppException(
                f"Không thể xóa job đang chạy hoặc đang chờ (hiện tại: {job.status}). Hãy hủy job trước khi xóa.",
                code="job_not_terminal",
                status_code=409,
            )
        await db.delete(job)
        await db.commit()
        logger.info("Deleted job id=%s", job_id)
        return True

    async def cleanup_jobs(
        self,
        db: AsyncSession,
        collection_id: str | None = None,
        statuses: list[str] | None = None,
        actor: Any | None = None,
    ) -> int:
        """Dọn dẹp hàng loạt các jobs đã kết thúc (terminal: completed, cancelled, failed) trong tenant."""
        target_statuses = statuses or ["completed", "cancelled", "failed"]
        for s in target_statuses:
            if s not in TERMINAL_STATUSES:
                raise AppException(
                    f"Trạng thái '{s}' không hợp lệ cho cleanup. Chỉ được xóa các job terminal ({', '.join(TERMINAL_STATUSES)}).",
                    code="INVALID_CLEANUP_STATUS",
                    status_code=400,
                )
        stmt = delete(JobRecord).where(JobRecord.status.in_(target_statuses))
        if actor and getattr(actor, "tenant_id", None):
            stmt = stmt.where(JobRecord.tenant_id == actor.tenant_id)
            if getattr(actor, "workspace_id", None):
                stmt = stmt.where(JobRecord.workspace_id == actor.workspace_id)
        if collection_id:
            stmt = stmt.where(JobRecord.collection_id == collection_id)
        res = await db.execute(stmt)
        await db.commit()
        count = int(res.rowcount or 0)
        logger.info(
            "Cleaned up %d jobs (collection=%s, statuses=%s, tenant=%s)",
            count,
            collection_id,
            target_statuses,
            getattr(actor, "tenant_id", None),
        )
        return count

    async def retry_job(
        self,
        db: AsyncSession,
        job_id: str,
        actor: Any | None = None,
    ) -> JobRecord:
        job = await self.get_job(db, job_id, actor=actor)
        if job.status not in ("failed", "cancelled"):
            raise AppException(
                f"Chỉ retry job failed/cancelled (hiện tại: {job.status}).",
                code="job_not_retryable",
                status_code=409,
            )
        job.status = "queued"
        job.cancel_requested = False
        job.progress = 0.0
        job.error = None
        job.result = {}
        job.heartbeat_at = None
        job.attempt = (job.attempt or 0) + 1
        job.dispatch_status = "pending"
        await db.commit()
        arq_job_id = await enqueue_arq_job(
            ARQ_FUNCTIONS[job.job_type],
            job.id,
            broker_job_id=self._broker_job_id(job),
        )
        if arq_job_id:
            job.arq_job_id = arq_job_id
            job.dispatch_status = "dispatched"
        await db.commit()
        await db.refresh(job)
        return job

    async def reconcile_pending_dispatches(
        self,
        db: AsyncSession,
        limit: int = 100,
    ) -> int:
        """Redispatch durable queued jobs that were persisted while the broker was unavailable."""
        stmt = (
            select(JobRecord)
            .where(
                JobRecord.status == "queued",
                JobRecord.dispatch_status == "pending",
                JobRecord.cancel_requested.is_(False),
            )
            .order_by(JobRecord.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        records = list((await db.execute(stmt)).scalars().all())
        dispatched = 0
        for record in records:
            function_name = ARQ_FUNCTIONS.get(record.job_type)
            if not function_name:
                record.status = "failed"
                record.dispatch_status = "failed"
                record.error = f"Loại job không còn được hỗ trợ: {record.job_type}"
                continue

            arq_job_id = await enqueue_arq_job(
                function_name,
                record.id,
                broker_job_id=self._broker_job_id(record),
            )
            if arq_job_id:
                record.arq_job_id = arq_job_id
                record.dispatch_status = "dispatched"
                record.error = None
                dispatched += 1
            else:
                record.error = "Redis/worker chưa sẵn sàng; sẽ tự động phát lại."

        await db.commit()
        return dispatched


jobs_service = JobsService()
