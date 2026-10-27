"""Index claim fencing and heartbeat; late workers cannot activate a generation."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexRun
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger

logger = get_logger(__name__)


class ClaimLost(Exception):
    """The database lease no longer belongs to this worker."""


async def claim(db: AsyncSession, run_id: str, worker_id: str, seconds: int) -> IndexRun | None:
    now = utcnow()
    claimed = await db.scalar(
        update(IndexRun)
        .where(
            IndexRun.id == run_id,
            (IndexRun.status == "queued")
            | ((IndexRun.status == "running") & (IndexRun.lease_expires_at < now)),
        )
        .values(
            status="running",
            worker_id=f"{worker_id[:80]}:{uuid.uuid4().hex}",
            started_at=func.coalesce(IndexRun.started_at, now),
            lease_expires_at=now + timedelta(seconds=seconds),
            attempt_count=IndexRun.attempt_count + 1,
        )
        .returning(IndexRun.id)
    )
    await db.commit()
    return await db.get(IndexRun, claimed, populate_existing=True) if claimed else None


async def assert_claim(db: AsyncSession, run: IndexRun) -> None:
    with db.no_autoflush:
        owner = await db.scalar(
            select(IndexRun.id)
            .where(
                IndexRun.id == run.id,
                IndexRun.worker_id == run.worker_id,
                IndexRun.status == "running",
                IndexRun.lease_expires_at > utcnow(),
            )
            .with_for_update()
        )
    if owner is None:
        raise ClaimLost()


async def commit_owned(db: AsyncSession, run: IndexRun) -> None:
    await assert_claim(db, run)
    await db.commit()


@asynccontextmanager
async def heartbeat(run: IndexRun, seconds: int):
    run_id, token = run.id, run.worker_id

    async def pulse():
        while True:
            await asyncio.sleep(seconds / 3)
            try:
                async with AsyncSessionFactory() as db:
                    now = utcnow()
                    row = await db.scalar(
                        update(IndexRun)
                        .where(
                            IndexRun.id == run_id,
                            IndexRun.worker_id == token,
                            IndexRun.status == "running",
                            IndexRun.lease_expires_at > now,
                        )
                        .values(lease_expires_at=now + timedelta(seconds=seconds))
                        .returning(IndexRun.id)
                    )
                    await db.commit()
                    if row is None:
                        return
            except Exception:
                logger.warning("index_heartbeat_failed", run_id=run_id)
                return

    task = asyncio.create_task(pulse())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
