"""ARQ tasks for OCR processing. Only backendV1 jobs are consumed."""

from __future__ import annotations

import os
import socket
from datetime import timedelta

from sqlalchemy import select, update

from qnu.api.wiring import build_container, close_container
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.preparation import service as preparation
from qnu.domains.ocr.execution import execute_run, job_id_for
from qnu.domains.ocr.models import OcrProcessingRun, utcnow
from qnu.domains.ocr.review.automatic import review_document
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger
from qnu.workers import heartbeat

logger = get_logger(__name__)

RECONCILE_BATCH = 50


async def startup(ctx: dict) -> None:
    settings = get_settings()
    ctx["container"] = build_container(settings)
    ctx["worker_id"] = f"{socket.gethostname()}:{os.getpid()}"
    await heartbeat.start(ctx)


async def shutdown(ctx: dict) -> None:
    await heartbeat.stop(ctx)
    container = ctx.get("container")
    if container is not None:
        await close_container(container)


async def ocr_process_run(ctx: dict, run_id: str) -> str:
    """Run one claimed generation; every failure is recorded, never raised to ARQ."""
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        outcome = await execute_run(
            db,
            container.blob_store,
            run_id,
            worker_id=ctx.get("worker_id", "arq"),
            engine=container.ocr_engine,
            job_queue=container.job_queue,
        )
        if outcome.status in {"completed", "failed", "uncertain", "cancelled"}:
            await preparation.notify_for_ocr_run(db, run_id, container.job_queue)
        if outcome.status == "completed" and container.job_queue:
            try:
                await container.job_queue.enqueue(
                    "spelling_check_job",
                    run_id,
                    0,
                    job_id=f"qnu:v1:spelling:{run_id}:0",
                )
            except Exception:
                logger.warning("auto_spelling_enqueue_failed", run_id=run_id)
    return outcome.status


async def spelling_check_job(ctx: dict, run_id: str, version: int = 0) -> str:
    """Automatic background spelling review after successful OCR text extraction."""
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        run = await db.get(OcrProcessingRun, run_id)
        if run is None or run.status != "completed":
            return "run_not_ready"
        actor = background_actor(run.requested_by)
        try:
            return await review_document(
                db, container.blob_store, container.chat_model, actor, run, version
            )
        except Exception:
            logger.warning(
                "auto_spelling_job_failed",
                run_id=run_id,
                version=version,
            )
            return "failed"


async def ocr_reconcile_queued(ctx: dict) -> int:
    """Recover missing queue deliveries and runs whose owning worker expired."""
    container = ctx["container"]
    settings = get_settings()
    now = utcnow()
    stale_dispatch = now - timedelta(seconds=settings.OCR_LEASE_SECONDS)
    requeued = 0
    async with AsyncSessionFactory() as db:
        rows = (
            await db.execute(
                select(OcrProcessingRun.id, OcrProcessingRun.attempt_count)
                .where(
                    (
                        (OcrProcessingRun.status == "queued")
                        & (
                            (OcrProcessingRun.dispatched_at.is_(None))
                            | (OcrProcessingRun.dispatched_at < stale_dispatch)
                        )
                    )
                    | (
                        (OcrProcessingRun.status == "running")
                        & (OcrProcessingRun.lease_expires_at < now)
                    ),
                )
                .order_by(OcrProcessingRun.requested_at)
                .limit(RECONCILE_BATCH)
            )
        ).all()
        for run_id, attempt in rows:
            try:
                queued = await container.job_queue.enqueue(
                    "ocr_process_run",
                    run_id,
                    job_id=f"{job_id_for(run_id, attempt + 1)}:reconcile:{int(now.timestamp()) // 300}",
                )
            except Exception:
                logger.warning("ocr_reconcile_enqueue_failed", run_id=run_id)
                continue
            if queued:
                await db.execute(
                    update(OcrProcessingRun)
                    .where(OcrProcessingRun.id == run_id)
                    .values(dispatched_at=utcnow())
                )
                requeued += 1
        await db.commit()
    if requeued:
        logger.info("ocr_reconcile_requeued", count=requeued)
    return requeued
