"""Apply reversible changes in one transaction; cleanup touches only an owned inactive index."""

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.lifecycle.models import LifecycleAction, ResourceState
from qnu.domains.lifecycle.targets import related_jobs
from qnu.domains.ocr.models import OcrRunPage
from qnu.platform.database import Base
from qnu.platform.errors import Conflict
from qnu.ports.vector_store import VectorStore


async def cancel_job(db: AsyncSession, kind: str, job: Base) -> None:
    job.status, job.error_code = "cancelled", "operation_cancelled"
    if hasattr(job, "finished_at"):
        job.finished_at = utcnow()
    if hasattr(job, "lease_expires_at"):
        job.lease_expires_at = utcnow() if kind == "turn" else None
    if kind == "ocr":
        await db.execute(
            update(OcrRunPage)
            .where(OcrRunPage.run_id == job.id, OcrRunPage.status == "in_flight")
            .values(status="uncertain")
        )
    if kind == "auto_review":
        from qnu.domains.knowledge.compilation.review.models import CompilationReview

        for review in (
            await db.scalars(
                select(CompilationReview)
                .where(
                    CompilationReview.compilation_run_id == job.compilation_run_id,
                    CompilationReview.idempotency_key == "auto:" + job.compilation_run_id,
                    CompilationReview.status == "running",
                )
                .with_for_update()
            )
        ).all():
            await cancel_job(db, "review", review)
    if kind == "index":
        from qnu.domains.lifecycle.replacement import fail_replacement

        await fail_replacement(db, job, "operation_cancelled")
    # Unknown billing remains reserved; cancellation never claims that an upstream call was free.


async def cancel_related_jobs(db: AsyncSession, workspace_id: str, kind: str, row: Base) -> int:
    """Caller holds the workspace lock and commits cancellation with the state change."""
    jobs = await related_jobs(db, workspace_id, kind, row)
    for job_kind, job in jobs:
        await cancel_job(db, job_kind, job)
    return len(jobs)


async def apply(db: AsyncSession, action: LifecycleAction, row: Base) -> dict:
    if action.action == "cancel":
        await cancel_job(db, action.parameters["job_kind"], row)
        return {"job_status": "cancelled", "upstream_abort_guaranteed": False}
    if action.action in {"archive", "delete", "pause"}:
        await cancel_related_jobs(db, action.workspace_id, action.kind, row)
    if action.action in {"pause", "resume"}:
        row.is_active = action.action == "resume"
        row.updated_at = utcnow()
        return {"is_active": row.is_active, "conversation_revision_preserved": True}
    status = {"archive": "archived", "delete": "deleted", "restore": "active"}[action.action]
    key = (action.workspace_id, action.kind, action.resource_id)
    resource = await db.get(ResourceState, key)
    if resource is None:
        db.add(ResourceState(workspace_id=key[0], kind=key[1], resource_id=key[2], status=status))
    else:
        resource.status, resource.revision, resource.updated_at = (
            status,
            resource.revision + 1,
            utcnow(),
        )
    if action.kind == "assistant":
        row.is_active = False
    if action.kind == "conversation":
        row.status = "active" if status == "active" else "archived"
    if action.kind in {"source", "document", "collection"}:
        from qnu.domains.identity.background import background_actor
        from qnu.domains.knowledge.index.sync import mark_pending

        collection_id = row.id if action.kind == "collection" else row.collection_id
        await mark_pending(
            db, background_actor(action.actor_ref), action.workspace_id, collection_id
        )
    return {
        "resource_status": status,
        "originals_retained": True,
        "restore_available": status != "active",
    }


async def cleanup(
    db: AsyncSession, vectors: VectorStore, action: LifecycleAction, run: IndexRun
) -> dict:
    if run.is_active or run.status in {"queued", "running"}:
        raise Conflict("Generation còn đang sử dụng.", code="lifecycle_index_in_use")
    if vectors.target_hash != run.config.get("vector_target_hash"):
        raise Conflict("Vector target đã đổi.", code="index_configuration_changed")
    await vectors.delete_collection(run.vector_collection)
    deleted = await db.execute(delete(IndexChunk).where(IndexChunk.run_id == run.id))
    # Keep the immutable manifest, raw model receipts and publication inputs as audit evidence.
    return {
        "vector_collection_deleted": True,
        "chunks_deleted": deleted.rowcount,
        "raw_evidence_retained": True,
    }
