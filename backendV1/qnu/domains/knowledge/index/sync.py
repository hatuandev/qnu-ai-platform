"""Durable publication outbox. Preparation never runs in the publication request."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexRun, IndexSync
from qnu.domains.knowledge.index.schemas import IndexRequest
from qnu.domains.knowledge.index.service import dispatch, request_index
from qnu.domains.knowledge.index.snapshots import current_snapshot, publication_identity
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.job_queue import JobQueue

if TYPE_CHECKING:
    from qnu.api.wiring import Container

logger = get_logger(__name__)


async def mark_pending(
    db: AsyncSession, actor: AuthActor, workspace_id: str, collection_id: str
) -> None:
    """Caller holds the authorized workspace lock; commit with the publication."""
    statement = insert(IndexSync).values(
        collection_id=collection_id,
        workspace_id=workspace_id,
        revision=1,
        run_revision=0,
        requested_by=actor_ref(actor),
        status="pending",
        retry_receipts={},
        updated_at=utcnow(),
    )
    await db.execute(
        statement.on_conflict_do_update(
            index_elements=[IndexSync.collection_id],
            set_={
                "revision": IndexSync.revision + 1,
                "requested_by": actor_ref(actor),
                "status": "pending",
                "error_code": None,
                "updated_at": utcnow(),
            },
        )
    )


async def wake(queue: JobQueue | None, collection_id: str) -> None:
    if queue is None:
        return
    from uuid import uuid4

    try:
        await queue.enqueue("index_sync", collection_id, job_id=f"qnu:v1:index-sync:{uuid4().hex}")
    except Exception:
        logger.warning("index_sync_dispatch_pending", collection_id=collection_id)


async def _synchronize(
    db: AsyncSession, container: Container, row: IndexSync, actor: AuthActor
) -> str:
    working = await db.scalar(
        select(IndexRun).where(
            IndexRun.collection_id == row.collection_id,
            IndexRun.status.in_(("queued", "running")),
        )
    )
    if working:
        # A newer publication waits until this run either activates or rejects its snapshot.
        row.status = "building"
        return row.status
    previous = await db.get(IndexRun, row.run_id) if row.run_id else None
    if (
        previous
        and row.run_revision == row.revision
        and previous.status in {"failed", "uncertain", "cancelled"}
    ):
        row.status = "uncertain" if previous.status == "uncertain" else "failed"
        row.error_code = previous.error_code
        return row.status
    try:
        published = await current_snapshot(
            db, container.blob_store, actor, row.workspace_id, row.collection_id
        )
    except AppException as exc:
        if exc.code != "index_no_published_documents":
            raise
        # No searchable content; existing eligibility gates exclude withdrawn versions.
        row.run_revision, row.run_id, row.status = row.revision, None, "ready"
        return row.status
    active = await db.scalar(
        select(IndexRun).where(
            IndexRun.collection_id == row.collection_id, IndexRun.is_active.is_(True)
        )
    )
    if active and active.input_sha256 == digest([publication_identity(p) for p in published]):
        row.run_id, row.run_revision, row.status = active.id, row.revision, "ready"
        row.error_code = None
        return row.status
    outcome = await request_index(
        db,
        container.blob_store,
        container.vector_store,
        actor,
        row.workspace_id,
        row.collection_id,
        IndexRequest(contextual_search=True),
        f"publication-sync:{row.collection_id}:{row.revision}",
        None,
        prepared_publications=published,
        commit=False,
    )
    row.run_id, row.run_revision, row.status = outcome.run.id, row.revision, "building"
    row.error_code = None
    return row.status


async def synchronize(db: AsyncSession, container: Container, collection_id: str) -> str:
    row = await db.get(IndexSync, collection_id)
    if row is None or row.status not in {"pending", "building"}:
        return "not_pending"
    workspace_id, requested_by, revision = row.workspace_id, row.requested_by, row.revision
    actor = background_actor(requested_by)
    previous_run_id = row.run_id
    try:
        # Same lock order as publication, retrieval and retirement.
        await authorize(db, actor, workspace_id, collection_id, write=True)
        row = await db.get(IndexSync, collection_id, populate_existing=True, with_for_update=True)
        if row is None or row.status not in {"pending", "building"}:
            return "not_pending"
        revision, previous_run_id = row.revision, row.run_id
        if row.requested_by != requested_by:
            await db.rollback()
            return "pending"
        status = await _synchronize(db, container, row, actor)
        row.updated_at = utcnow()
        await db.commit()
        if row.run_id:
            run = await db.get(IndexRun, row.run_id)
            if run and run.status == "queued" and run.dispatched_at is None:
                await dispatch(db, run, container.job_queue)
        return status
    except Exception as exc:
        await db.rollback()
        code = exc.code if isinstance(exc, AppException) else "index_sync_failed"
        # A failed delivery cannot overwrite a newer publication or worker binding.
        from sqlalchemy import update

        await db.execute(
            update(IndexSync)
            .where(
                IndexSync.collection_id == collection_id,
                IndexSync.revision == revision,
                IndexSync.requested_by == requested_by,
                IndexSync.status.in_(("pending", "building")),
                IndexSync.run_id.is_(None)
                if previous_run_id is None
                else IndexSync.run_id == previous_run_id,
            )
            .values(status="failed", error_code=code, updated_at=utcnow())
        )
        await db.commit()
        logger.warning("index_sync_stopped", collection_id=collection_id, error_code=code)
        return "failed"


async def readiness(
    db: AsyncSession, actor: AuthActor, workspace_id: str, collection_id: str
) -> dict:
    await authorize(db, actor, workspace_id, collection_id)
    row = await db.get(IndexSync, collection_id)
    if row is None:
        return {"status": "not_requested", "revision": 0, "error_code": None}
    return {"status": row.status, "revision": row.revision, "error_code": row.error_code}


async def retry(
    db: AsyncSession, actor: AuthActor, workspace_id: str, collection_id: str, key: str
) -> None:
    await authorize(db, actor, workspace_id, collection_id, write=True)
    row = await db.get(IndexSync, collection_id, populate_existing=True, with_for_update=True)
    receipt = digest({"actor": actor_ref(actor), "key": key})
    if row and receipt in row.retry_receipts:
        return
    if row and row.status not in {"failed", "uncertain"}:
        raise Conflict("Tác vụ đang xử lý hoặc đã sẵn sàng.", code="index_sync_not_failed")
    await mark_pending(db, actor, workspace_id, collection_id)
    row = await db.get(IndexSync, collection_id, populate_existing=True)
    row.retry_receipts = {**row.retry_receipts, receipt: row.revision}
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="index.sync_retry_requested",
        detail={"collection_id": collection_id, "revision": row.revision},
    )
    await db.commit()
