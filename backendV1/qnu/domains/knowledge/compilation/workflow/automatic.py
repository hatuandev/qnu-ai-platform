"""Review outbox: completion and intent commit together; replay never resends a model call."""

import asyncio
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review.execution import execute
from qnu.domains.knowledge.compilation.review.models import CompilationReview
from qnu.domains.knowledge.compilation.review.schemas import ReviewRequest
from qnu.domains.knowledge.compilation.service import get_run
from qnu.domains.knowledge.compilation.workflow.models import AutoReviewJob
from qnu.platform.errors import AppException, EntityNotFound
from qnu.platform.logging import get_logger

logger = get_logger(__name__)
LEASE_SECONDS = 900


async def schedule(db: AsyncSession, run: CompilationRun) -> None:
    """No provider/queue I/O and no commit here: caller owns the completion transaction."""
    if not run.config.get("auto_review"):
        return
    await db.execute(
        insert(AutoReviewJob)
        .values(
            compilation_run_id=run.id,
            workspace_id=run.workspace_id,
            collection_id=run.collection_id,
            created_by=run.requested_by,
            config=run.config["review"],
            status="queued",
            created_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["compilation_run_id"])
    )


async def dispatch(db: AsyncSession, run_id: str, queue) -> bool:
    row = await db.get(AutoReviewJob, run_id)
    if row is None or row.status != "queued" or queue is None:
        return False
    try:
        await queue.enqueue(
            "compiler_review_job",
            run_id,
            job_id=f"qnu:v1:compiler-review:{run_id}:{int(utcnow().timestamp()) // 300}",
        )
    except Exception:
        logger.warning("compiler_review_dispatch_pending", run_id=run_id)
        return False
    await db.execute(
        update(AutoReviewJob)
        .where(AutoReviewJob.compilation_run_id == run_id, AutoReviewJob.status == "queued")
        .values(dispatched_at=utcnow())
    )
    await db.commit()
    return True


async def status(db, actor, workspace_id, collection_id, run_id):
    await get_run(db, actor, workspace_id, collection_id, run_id)
    row = await db.get(AutoReviewJob, run_id)
    if row is None:
        raise EntityNotFound(
            "Chưa có yêu cầu review tự động.", code="compilation_auto_review_not_found"
        )
    return row


async def execute_job(db: AsyncSession, blob, chat, run_id: str, worker_id: str) -> str:
    now, token = utcnow(), worker_id[:80] + ":" + uuid.uuid4().hex
    claimed = await db.scalar(
        update(AutoReviewJob)
        .where(
            AutoReviewJob.compilation_run_id == run_id,
            (AutoReviewJob.status == "queued")
            | ((AutoReviewJob.status == "running") & (AutoReviewJob.lease_expires_at < now)),
        )
        .values(
            status="running",
            worker_id=token,
            started_at=now,
            lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
        )
        .returning(AutoReviewJob.compilation_run_id)
    )
    await db.commit()
    if claimed is None:
        return "not_claimed"
    job = await db.get(AutoReviewJob, run_id, populate_existing=True)
    actor = AuthActor(username=job.created_by, actor_id=job.created_by, roles=[], permissions=[])
    result_status, error_code, review_id = "uncertain", None, None
    try:
        result = await execute(
            db,
            blob,
            chat,
            actor,
            job.workspace_id,
            job.collection_id,
            run_id,
            ReviewRequest(**job.config),
            "auto:" + run_id,
        )
        result_status, error_code, review_id = result.status, result.error_code, result.id
    except (Exception, asyncio.CancelledError) as exc:
        await db.rollback()
        review = await db.scalar(
            select(CompilationReview).where(
                CompilationReview.compilation_run_id == run_id,
                CompilationReview.created_by == actor.actor_id,
                CompilationReview.idempotency_key == "auto:" + run_id,
            )
        )
        error_code = exc.code if isinstance(exc, AppException) else "compilation_review_interrupted"
        result_status = (
            review.status
            if review
            else ("failed" if isinstance(exc, AppException) else "uncertain")
        )
        review_id = review.id if review else None
        if isinstance(exc, asyncio.CancelledError):
            await _finish(db, run_id, token, result_status, error_code, review_id)
            raise
    await _finish(db, run_id, token, result_status, error_code, review_id)
    return result_status


async def _finish(db, run_id, token, status, error_code, review_id):
    await db.execute(
        update(AutoReviewJob)
        .where(
            AutoReviewJob.compilation_run_id == run_id,
            AutoReviewJob.worker_id == token,
            AutoReviewJob.status == "running",
        )
        .values(
            status=status,
            review_id=review_id,
            error_code=error_code,
            finished_at=utcnow() if status != "running" else None,
            lease_expires_at=(utcnow() + timedelta(seconds=LEASE_SECONDS))
            if status == "running"
            else None,
        )
    )
    await db.commit()
