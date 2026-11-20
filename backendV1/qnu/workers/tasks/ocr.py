"""ARQ tasks for OCR processing. Only backendV1 jobs are consumed."""

from __future__ import annotations

import os
import socket
from datetime import timedelta

from sqlalchemy import exists, select, update

from qnu.api.wiring import build_container, close_container
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.preparation import service as preparation
from qnu.domains.ocr.execution import execute_run, job_id_for
from qnu.domains.ocr.models import OcrProcessingRun, utcnow
from qnu.domains.ocr.review import defaults
from qnu.domains.ocr.review.automatic import review_document
from qnu.domains.ocr.review.models import SpellingRun
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger
from qnu.workers import heartbeat

logger = get_logger(__name__)

RECONCILE_BATCH = 50
SPELLING_RECOVERY_BATCH = 20
SPELLING_RECOVERY_GRACE = timedelta(minutes=10)
SPELLING_RECOVERY_WINDOW = timedelta(hours=24)


TOTAL_SPELLING_PASSES = 2


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
        if outcome.status in {
            "completed",
            "completed_with_warnings",
            "failed",
            "uncertain",
            "cancelled",
        }:
            await preparation.notify_for_ocr_run(db, run_id, container.job_queue)
        if outcome.status in {"completed", "completed_with_warnings"} and container.job_queue:
            try:
                await container.job_queue.enqueue(
                    "spelling_check_job",
                    run_id,
                    0,
                    False,
                    True,
                    1,
                    None,
                    None,
                    job_id=f"qnu:v1:spelling:{run_id}:0:p1:auto",
                )
            except Exception:
                logger.warning("auto_spelling_enqueue_failed", run_id=run_id)
    return outcome.status


async def spelling_check_job(
    ctx: dict,
    run_id: str,
    version: int = 0,
    retry: bool = False,
    automatic: bool = False,
    pass_number: int = 1,
    parent_run_id: str | None = None,
    batch_group_id: str | None = None,
) -> str:
    """Automatic background spelling review with multi-pass chaining."""
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        run = await db.get(OcrProcessingRun, run_id)
        if run is None or run.status not in {"completed", "completed_with_warnings"}:
            return "run_not_ready"
        actor = background_actor(run.requested_by)
        policy = await defaults.read(db)
        total_passes = policy.total_passes
        try:
            status, check_id = await review_document(
                db,
                container.blob_store,
                container.chat_model,
                actor,
                run,
                version,
                retry=retry,
                automatic=automatic,
                pass_number=pass_number,
                total_passes=total_passes,
                parent_run_id=parent_run_id,
                batch_group_id=batch_group_id,
            )
            # Multi-pass chaining: when current pass finishes successfully and there is a next pass
            if (
                status in {"completed", "completed_with_warnings"}
                and automatic
                and pass_number < total_passes
                and check_id is not None
                and container.job_queue
            ):
                next_pass = pass_number + 1
                next_job_id = f"qnu:v1:spelling:{run_id}:{version}:p{next_pass}:auto"
                try:
                    await container.job_queue.enqueue(
                        "spelling_check_job",
                        run_id,
                        version,
                        False,
                        True,
                        next_pass,
                        check_id,
                        batch_group_id or check_id,
                        job_id=next_job_id,
                    )
                    logger.info(
                        "spelling_next_pass_enqueued",
                        run_id=run_id,
                        version=version,
                        next_pass=next_pass,
                        parent_check_id=check_id,
                    )
                except Exception:
                    logger.warning(
                        "spelling_next_pass_enqueue_failed",
                        run_id=run_id,
                        version=version,
                        next_pass=next_pass,
                    )
            return status
        except Exception as exc:
            logger.warning(
                "auto_spelling_job_failed",
                run_id=run_id,
                version=version,
                pass_number=pass_number,
                error=type(exc).__name__,
            )
            return "failed"


async def spelling_reconcile(ctx: dict) -> int:
    """Re-deliver an automatic check whose first delivery or next pass never completed."""
    container = ctx["container"]
    now = utcnow()
    requeued = 0
    bucket = int(now.timestamp()) // 300
    async with AsyncSessionFactory() as db:
        # 1. Runs completed without Pass 1
        has_pass1 = exists(
            select(SpellingRun.id).where(
                SpellingRun.run_id == OcrProcessingRun.id,
                SpellingRun.version == 0,
                SpellingRun.pass_number == 1,
                SpellingRun.idempotency_key.startswith("auto:spl:document:"),
            )
        )
        pass1_missing = (
            await db.scalars(
                select(OcrProcessingRun.id)
                .where(
                    OcrProcessingRun.status.in_(("completed", "completed_with_warnings")),
                    OcrProcessingRun.finished_at.is_not(None),
                    OcrProcessingRun.finished_at < now - SPELLING_RECOVERY_GRACE,
                    OcrProcessingRun.finished_at > now - SPELLING_RECOVERY_WINDOW,
                    ~has_pass1,
                )
                .order_by(OcrProcessingRun.finished_at)
                .limit(SPELLING_RECOVERY_BATCH)
            )
        ).all()
        for run_id in pass1_missing:
            try:
                queued = await container.job_queue.enqueue(
                    "spelling_check_job",
                    run_id,
                    0,
                    False,
                    True,
                    1,
                    None,
                    None,
                    job_id=f"qnu:v1:spelling:{run_id}:0:p1:recover:{bucket}",
                )
                if queued:
                    requeued += 1
            except Exception:
                logger.warning("spelling_reconcile_pass1_failed", run_id=run_id)

        # 2. Runs where Pass k completed, but Pass k+1 was never enqueued/created (k < total_passes)
        pass_completed = (
            await db.scalars(
                select(SpellingRun)
                .where(
                    SpellingRun.version == 0,
                    SpellingRun.pass_number < SpellingRun.total_passes,
                    SpellingRun.status.in_(("completed", "completed_with_warnings")),
                    SpellingRun.idempotency_key.startswith("auto:spl:document:"),
                    SpellingRun.created_at < now - SPELLING_RECOVERY_GRACE,
                    SpellingRun.created_at > now - SPELLING_RECOVERY_WINDOW,
                )
                .order_by(SpellingRun.created_at)
                .limit(SPELLING_RECOVERY_BATCH)
            )
        ).all()
        for pass_cur in pass_completed:
            next_pass_num = pass_cur.pass_number + 1
            has_next_pass = await db.scalar(
                select(SpellingRun.id).where(
                    SpellingRun.run_id == pass_cur.run_id,
                    SpellingRun.version == pass_cur.version,
                    SpellingRun.pass_number == next_pass_num,
                    SpellingRun.canonical_sha256 == pass_cur.canonical_sha256,
                )
            )
            if not has_next_pass:
                try:
                    queued = await container.job_queue.enqueue(
                        "spelling_check_job",
                        pass_cur.run_id,
                        pass_cur.version,
                        False,
                        True,
                        next_pass_num,
                        pass_cur.id,
                        pass_cur.batch_group_id or pass_cur.id,
                        job_id=f"qnu:v1:spelling:{pass_cur.run_id}:{pass_cur.version}:p{next_pass_num}:recover:{bucket}",
                    )
                    if queued:
                        requeued += 1
                except Exception:
                    logger.warning("spelling_reconcile_next_pass_failed", run_id=pass_cur.run_id, next_pass=next_pass_num)

    if requeued:
        logger.info("spelling_reconcile_requeued", count=requeued)
    return requeued


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
