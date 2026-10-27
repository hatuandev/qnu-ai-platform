"""Heartbeat and database fencing for a single OCR execution claim."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.ocr.models import OcrProcessingRun, utcnow
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger

logger = get_logger(__name__)


class LeaseLost(Exception):
    """The old worker may no longer commit or start another provider request."""


async def assert_claim(db: AsyncSession, run: OcrProcessingRun) -> None:
    # Do not flush pending changes from an obsolete worker before checking ownership.
    with db.no_autoflush:
        owner = await db.scalar(
            select(OcrProcessingRun.worker_id)
            .where(
                OcrProcessingRun.id == run.id,
                OcrProcessingRun.worker_id == run.worker_id,
                OcrProcessingRun.status == "running",
                OcrProcessingRun.lease_expires_at > utcnow(),
            )
            .with_for_update()
        )
    if owner is None:
        raise LeaseLost()


async def commit_owned(db: AsyncSession, run: OcrProcessingRun) -> None:
    await assert_claim(db, run)
    await db.commit()


async def renew_claim(run_id: str, token: str, seconds: int) -> bool:
    now = utcnow()
    async with AsyncSessionFactory() as db:
        renewed = await db.scalar(
            update(OcrProcessingRun)
            .where(
                OcrProcessingRun.id == run_id,
                OcrProcessingRun.worker_id == token,
                OcrProcessingRun.status == "running",
                OcrProcessingRun.lease_expires_at > now,
            )
            .values(lease_expires_at=now + timedelta(seconds=seconds))
            .returning(OcrProcessingRun.id)
        )
        await db.commit()
        return renewed is not None


@asynccontextmanager
async def heartbeat(run: OcrProcessingRun, seconds: int):
    run_id, token = run.id, run.worker_id

    async def pulse():
        while True:
            await asyncio.sleep(max(0.1, seconds / 3))
            try:
                if not await renew_claim(run_id, token, seconds):
                    return
            except Exception:
                logger.warning("ocr_heartbeat_failed", run_id=run_id)
                return

    task = asyncio.create_task(pulse())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
