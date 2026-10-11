"""Reconcile batch counters from durable items, serialized per batch."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeImportBatch, KnowledgeImportItem


async def refresh_batch_counts(db: AsyncSession, batch_id: str) -> None:
    batch = (await db.execute(
        select(KnowledgeImportBatch).where(KnowledgeImportBatch.id == batch_id)
        .with_for_update().execution_options(populate_existing=True)
    )).scalar_one()
    rows = (await db.execute(
        select(KnowledgeImportItem.status, func.count())
        .where(KnowledgeImportItem.batch_id == batch_id)
        .group_by(KnowledgeImportItem.status)
    )).all()
    counts = dict(rows)
    for state, field in (
        ("queued", "queued_count"), ("processing", "processing_count"),
        ("review_required", "review_required_count"), ("succeeded", "succeeded_count"),
        ("failed", "failed_count"), ("skipped", "skipped_count"),
    ):
        setattr(batch, field, counts.get(state, 0))
    if batch.status != "cancelled":
        if batch.processing_count or batch.queued_count:
            batch.status = "processing"
        elif batch.failed_count:
            batch.status = "partial_failed"
        elif batch.review_required_count:
            batch.status = "review_required"
        else:
            batch.status = "completed"
    await db.commit()
