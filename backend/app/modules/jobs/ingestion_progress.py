"""Durable, per-job milestone progress, never a timer-based estimate."""

from contextvars import ContextVar

from sqlalchemy import func, update

from app.core.database import AsyncSessionFactory
from app.core.exceptions import AppException
from app.modules.jobs.models import JobRecord

current_job: ContextVar[tuple[str, int] | None] = ContextVar("ingestion_job", default=None)


def item_progress(status: str, phase: str, progress: float = 0) -> float:
    if status == "succeeded":
        return 100
    if status == "queued":
        return 0
    return max(0, min(99, progress))


async def report_progress(phase: str, progress: float) -> None:
    identity = current_job.get()
    if not identity:
        return
    job_id, attempt = identity
    async with AsyncSessionFactory() as db:
        result = await db.execute(update(JobRecord).where(
            JobRecord.id == job_id, JobRecord.attempt == attempt,
            JobRecord.status == "running", JobRecord.cancel_requested.is_(False),
        ).values(phase=phase, progress=func.greatest(JobRecord.progress, min(progress, 99))))
        if result.rowcount != 1:
            await db.rollback()
            raise AppException("Lượt xử lý đã hết hiệu lực hoặc đã hủy.", code="JOB_LEASE_LOST", status_code=409)
        await db.commit()
