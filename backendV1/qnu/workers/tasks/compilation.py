"""Compiler tasks on the existing v1 ARQ queue and lifecycle."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, update

from qnu.domains.knowledge.compilation.execution import execute_run
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review.execution import run_queued
from qnu.domains.knowledge.compilation.review.models import CompilationReview
from qnu.domains.knowledge.compilation.review.service import dispatch_review
from qnu.domains.knowledge.compilation.workflow import automatic
from qnu.domains.knowledge.compilation.workflow.models import AutoReviewJob
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger

logger = get_logger(__name__)


async def compile_run(ctx: dict, run_id: str) -> str:
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        status = await execute_run(
            db,
            container.blob_store,
            run_id,
            worker_id=ctx.get("worker_id", "arq"),
            model=container.chat_model,
        )
        if status in {"completed", "not_claimed"}:
            await automatic.dispatch(db, run_id, container.job_queue)
        return status


async def compiler_review_job(ctx: dict, run_id: str) -> str:
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        return await automatic.execute_job(
            db, container.blob_store, container.chat_model, run_id, ctx.get("worker_id", "arq")
        )


async def manual_compiler_review_job(ctx: dict, review_id: str) -> str:
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        return await run_queued(db, container.blob_store, container.chat_model, review_id)


async def compiler_review_reconcile(ctx: dict) -> int:
    container, now = ctx["container"], utcnow()
    cutoff = now - timedelta(seconds=automatic.LEASE_SECONDS)
    async with AsyncSessionFactory() as db:
        rows = list(
            (
                await db.scalars(
                    select(AutoReviewJob)
                    .where(
                        (
                            (AutoReviewJob.status == "queued")
                            & (
                                AutoReviewJob.dispatched_at.is_(None)
                                | (AutoReviewJob.dispatched_at < cutoff)
                            )
                        )
                        | (
                            (AutoReviewJob.status == "running")
                            & (AutoReviewJob.lease_expires_at < now)
                        )
                    )
                    .order_by(AutoReviewJob.created_at)
                    .limit(50)
                )
            ).all()
        )
        count = 0
        for row in rows:
            try:
                queued = await container.job_queue.enqueue(
                    "compiler_review_job",
                    row.compilation_run_id,
                    job_id=f"qnu:v1:compiler-review:{row.compilation_run_id}:{int(now.timestamp()) // 300}",
                )
            except Exception:
                logger.warning("compiler_review_reconcile_failed", run_id=row.compilation_run_id)
                continue
            if queued:
                row.dispatched_at = now
                count += 1
        await db.commit()
        manual_ids = list(
            await db.scalars(
                select(CompilationReview.id)
                .where(CompilationReview.status == "queued")
                .order_by(CompilationReview.created_at)
                .limit(50)
            )
        )
        for review_id in manual_ids:
            count += int(await dispatch_review(container.job_queue, review_id))
        return count


async def compilation_reconcile(ctx: dict) -> int:
    container = ctx["container"]
    now = utcnow()
    cutoff = now - timedelta(seconds=get_settings().COMPILER_LEASE_SECONDS)
    count = 0
    async with AsyncSessionFactory() as db:
        rows = (
            (
                await db.execute(
                    select(CompilationRun.id)
                    .where(
                        (
                            (CompilationRun.status == "queued")
                            & (
                                CompilationRun.dispatched_at.is_(None)
                                | (CompilationRun.dispatched_at < cutoff)
                            )
                        )
                        | (
                            (CompilationRun.status == "running")
                            & (CompilationRun.lease_expires_at < now)
                        ),
                    )
                    .order_by(CompilationRun.requested_at)
                    .limit(50)
                )
            )
            .scalars()
            .all()
        )
        for run_id in rows:
            try:
                queued = await container.job_queue.enqueue(
                    "compile_run",
                    run_id,
                    job_id=f"qnu:v1:compile:{run_id}:reconcile:{int(now.timestamp()) // 300}",
                )
            except Exception:
                logger.warning("compilation_reconcile_failed", run_id=run_id)
                continue
            if queued:
                await db.execute(
                    update(CompilationRun)
                    .where(CompilationRun.id == run_id)
                    .values(dispatched_at=now)
                )
                count += 1
        await db.commit()
    return count
