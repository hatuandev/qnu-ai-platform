"""Bound the durable backlog per tenant, serialized across collections."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.jobs.models import JobRecord


async def check_ingestion_capacity(db: AsyncSession, tenant_id: str, incoming: int) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:tenant, 376))"), {"tenant": tenant_id})
    pending = await db.scalar(select(func.count(JobRecord.id)).where(
        JobRecord.tenant_id == tenant_id,
        JobRecord.job_type == "knowledge_source_ingestion",
        JobRecord.status.in_(["queued", "running"]),
    )) or 0
    if pending + incoming > settings.INGESTION_MAX_PENDING_PER_TENANT:
        raise AppException("Hàng đợi nạp tài liệu đã đầy; vui lòng thử lại sau.",
                           code="INGESTION_QUEUE_FULL", status_code=429)
