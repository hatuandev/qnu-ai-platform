"""Database ownership fence and heartbeat for one Compiler job."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger

logger = get_logger(__name__)


class ClaimLost(Exception):
    """A worker whose lease expired must not send or commit another request."""


async def claim(
    db: AsyncSession, run_id: str, worker_id: str, seconds: int
) -> CompilationRun | None:
    now = utcnow()
    token = f"{worker_id[:80]}:{uuid.uuid4().hex}"
    claimed = await db.scalar(
        update(CompilationRun)
        .where(
            CompilationRun.id == run_id,
            (CompilationRun.status == "queued")
            | ((CompilationRun.status == "running") & (CompilationRun.lease_expires_at < now)),
        )
        .values(
            status="running",
            worker_id=token,
            lease_expires_at=now + timedelta(seconds=seconds),
            started_at=func.coalesce(CompilationRun.started_at, now),
            attempt_count=CompilationRun.attempt_count + 1,
        )
        .returning(CompilationRun.id)
    )
    await db.commit()
    return await db.get(CompilationRun, claimed, populate_existing=True) if claimed else None


async def assert_claim(db: AsyncSession, run: CompilationRun) -> None:
    with db.no_autoflush:
        owner = await db.scalar(
            select(CompilationRun.id)
            .where(
                CompilationRun.id == run.id,
                CompilationRun.worker_id == run.worker_id,
                CompilationRun.status == "running",
                CompilationRun.lease_expires_at > utcnow(),
            )
            .with_for_update()
        )
    if owner is None:
        raise ClaimLost()


async def commit_owned(db: AsyncSession, run: CompilationRun) -> None:
    await assert_claim(db, run)
    await db.commit()


@asynccontextmanager
async def heartbeat(run: CompilationRun, seconds: int):
    run_id, token = run.id, run.worker_id

    async def pulse():
        while True:
            await asyncio.sleep(seconds / 3)
            try:
                async with AsyncSessionFactory() as db:
                    now = utcnow()
                    result = await db.scalar(
                        update(CompilationRun)
                        .where(
                            CompilationRun.id == run_id,
                            CompilationRun.worker_id == token,
                            CompilationRun.status == "running",
                            CompilationRun.lease_expires_at > now,
                        )
                        .values(lease_expires_at=now + timedelta(seconds=seconds))
                        .returning(CompilationRun.id)
                    )
                    await db.commit()
                    if result is None:
                        return
            except Exception:
                logger.warning("compilation_heartbeat_failed", run_id=run_id)
                return

    task = asyncio.create_task(pulse())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
