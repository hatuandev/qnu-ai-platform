"""Index work and expired-delivery recovery on the existing v1 queue."""

from datetime import timedelta

from sqlalchemy import select, update

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.execution import execute_run
from qnu.domains.knowledge.index.models import IndexRun
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger

logger = get_logger(__name__)


async def index_run(ctx: dict, run_id: str) -> str:
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        return await execute_run(
            db,
            container.blob_store,
            run_id,
            worker_id=ctx.get("worker_id", "arq"),
            model=container.embedding_model,
            vectors=container.vector_store,
        )


async def index_reconcile(ctx: dict) -> int:
    now = utcnow()
    cutoff = now - timedelta(seconds=get_settings().INDEX_LEASE_SECONDS)
    count = 0
    async with AsyncSessionFactory() as db:
        rows = list(
            (
                await db.scalars(
                    select(IndexRun.id)
                    .where(
                        (
                            (IndexRun.status == "queued")
                            & (IndexRun.dispatched_at.is_(None) | (IndexRun.dispatched_at < cutoff))
                        )
                        | ((IndexRun.status == "running") & (IndexRun.lease_expires_at < now))
                    )
                    .order_by(IndexRun.requested_at)
                    .limit(50)
                )
            ).all()
        )
        for run_id in rows:
            try:
                queued = await ctx["container"].job_queue.enqueue(
                    "index_run",
                    run_id,
                    job_id=f"qnu:v1:index:{run_id}:reconcile:{int(now.timestamp()) // 300}",
                )
            except Exception:
                logger.warning("index_reconcile_failed", run_id=run_id)
                continue
            if queued:
                await db.execute(
                    update(IndexRun).where(IndexRun.id == run_id).values(dispatched_at=now)
                )
                count += 1
        await db.commit()
    return count
