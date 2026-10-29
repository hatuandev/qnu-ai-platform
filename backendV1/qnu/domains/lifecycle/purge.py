"""Durable source purge on the existing lifecycle receipt and V1 worker queue."""

import hashlib
from datetime import timedelta

from sqlalchemy import select

from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexRun
from qnu.domains.lifecycle import effects
from qnu.domains.lifecycle.models import LifecycleAction, ResourceState
from qnu.domains.lifecycle.purge_graph import graph_for_source, graph_plan, delete_rows, selected, table
from qnu.domains.operations.jobs.catalog import SPECS
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.database import AsyncSessionFactory, Base
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger

logger = get_logger(__name__)
TASK = "source_purge_job"


def is_source_delete(row):
    return row.kind == "source" and row.action == "delete"


async def inspect_source(db, source, blob):
    graph = await graph_for_source(db, source.workspace_id, source.id)
    plan = graph_plan(graph)
    return plan, {
        "permanent": True, "originals_and_raw_evidence": "permanently_deleted",
        "restore_available": False, "files_to_delete": len(plan["objects"]),
        "compiled_versions_to_delete": len(plan["rows"].get("kb_compiled_versions", [])),
        "backups_retained": True, "blob_target_hash": blob.target_hash,
    }


async def require_not_pending(db, workspace_id, kind, resource_id):
    if kind != "source":
        return
    pending = await db.scalar(select(LifecycleAction.id).where(
        LifecycleAction.workspace_id == workspace_id, LifecycleAction.kind == "source",
        LifecycleAction.resource_id == resource_id, LifecycleAction.action == "delete",
        LifecycleAction.status == "pending",
    ).limit(1))
    if pending:
        raise Conflict("Tài liệu đang được xóa vĩnh viễn.", code="source_purge_pending")


async def _cancel(db, graph):
    running = False
    for kind in ("ocr", "compiler", "review", "auto_review", "spelling", "turn"):
        spec = SPECS[kind]
        keys = graph.get(spec.model.__tablename__, {})
        if not keys:
            continue
        rows = (await db.scalars(select(spec.model).where(
            selected(spec.model.__table__, list(keys.values())),
            spec.model.status.in_(("queued", "running")),
        ).with_for_update())).all()
        for job in rows:
            running |= job.status == "running"
            await effects.cancel_job(db, kind, job)
    # Only builders containing affected inputs are cancelled; unrelated jobs remain untouched.
    ids = {row["run_id"] for row in graph.get("kb_index_inputs", {}).values()}
    for run in (await db.scalars(select(IndexRun).where(
        IndexRun.id.in_(ids), IndexRun.status.in_(("queued", "running")),
    ).with_for_update())).all():
        running |= run.status == "running"
        await effects.cancel_job(db, "index", run)
    return running


async def prepare(db, blob, vectors, actor, row, source):
    graph = await graph_for_source(db, row.workspace_id, source.id)
    running = await _cancel(db, graph)
    resource = await db.get(ResourceState, (row.workspace_id, "source", source.id))
    if resource is None:
        db.add(ResourceState(workspace_id=row.workspace_id, kind="source", resource_id=source.id, status="deleted"))
    else:
        resource.status, resource.revision = "deleted", resource.revision + 1
    await db.flush()
    # Capture post-cancellation rows. Workers cannot create more source-derived work.
    plan = graph_plan(await graph_for_source(db, row.workspace_id, source.id))
    plan["blob_target_hash"], plan["vector_target_hash"] = blob.target_hash, vectors.target_hash
    row.result = {"permanent": True, "phase": "queued", "_purge_plan": plan,
        "not_before": (utcnow() + timedelta(seconds=1800 if running else 0)).isoformat()}
    await record_workspace_event(db, workspace_id=row.workspace_id, actor=actor,
        action="source.purge_accepted", detail={"action_id": row.id, "source_id": source.id})


async def dispatch(row, queue):
    if queue is None:
        return False
    try:
        return await queue.enqueue(TASK, row.id, job_id=f"qnu:v1:purge:{row.id}:{int(utcnow().timestamp()) // 60}")
    except Exception:
        logger.warning("source_purge_dispatch_failed", action_id=row.id)
        return False


async def _delete_objects(blob, plan, workspace_id):
    for key, expected in plan["objects"].items():
        if not key.startswith((f"v1/workspaces/{workspace_id}/", f"ocr-text/{workspace_id}/", f"ocr-spelling/{workspace_id}/")):
            raise Conflict("Object ngoài phạm vi xóa.", code="purge_scope_invalid")
        if await blob.exists(key) and expected:
            if hashlib.sha256(await blob.get_bytes(key)).hexdigest() != expected:
                raise Conflict("Object đã thay đổi so với lúc xác nhận.", code="purge_object_changed")
        await blob.purge(key)
        if await blob.exists(key):
            raise Conflict("Object vẫn còn trong storage.", code="purge_storage_failed")


async def _delete_vectors(db, vectors, graph):
    groups = {}
    for chunk in graph.get("kb_index_chunks", {}).values():
        groups.setdefault(chunk["run_id"], []).append(chunk["point_id"])
    for run_id, ids in groups.items():
        run = await db.get(IndexRun, run_id)
        if run.config.get("vector_target_hash") != vectors.target_hash:
            raise Conflict("Vector target đã đổi; chưa xóa.", code="purge_target_changed")
        for offset in range(0, len(ids), 256):
            await vectors.delete_points(run.vector_collection, ids[offset:offset + 256])


async def execute(db, blob, vectors, action_id):
    initial = await db.get(LifecycleAction, action_id)
    if initial is None or not is_source_delete(initial) or initial.status != "pending":
        return "not_pending"
    workspace_id, actor = initial.workspace_id, background_actor(initial.actor_ref)
    try:
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",), for_update=True)
        row = await db.scalar(select(LifecycleAction).where(LifecycleAction.id == action_id).with_for_update().execution_options(populate_existing=True))
        if row.status != "pending":
            return row.status
        from datetime import datetime

        if datetime.fromisoformat(row.result["not_before"]) > utcnow():
            return "waiting_for_cancelled_work"
        plan = row.result["_purge_plan"]
        if blob.target_hash != plan["blob_target_hash"] or vectors.target_hash != plan["vector_target_hash"]:
            raise Conflict("Storage/vector target đã đổi; chưa xóa.", code="purge_target_changed")
        graph = await graph_for_source(db, workspace_id, row.resource_id)
        if graph_plan(graph)["graph_sha256"] != plan["graph_sha256"]:
            raise Conflict("Dữ liệu phụ thuộc đã đổi; cần đối soát lượt xóa.", code="purge_dependency_changed")
        await _assert_exclusive_blobs(db, plan)
        await _delete_vectors(db, vectors, graph)
        await _delete_objects(blob, plan, workspace_id)
        await delete_rows(db, plan, workspace_id)
        row.status, row.finished_at, row.error_code = "completed", utcnow(), None
        row.result = {"permanent": True, "originals_retained": False, "restore_available": False,
            "files_deleted": len(plan["objects"]), "backups_retained": True}
        await record_workspace_event(db, workspace_id=workspace_id, actor=actor,
            action="source.purged", detail={"action_id": row.id, "source_id": row.resource_id})
        await db.commit()
        return "completed"
    except Exception as exc:
        await db.rollback()
        row = await db.get(LifecycleAction, action_id, populate_existing=True)
        if row and row.status == "pending":
            row.error_code = exc.code if isinstance(exc, AppException) else "source_purge_failed"
            await db.commit()
        logger.warning("source_purge_incomplete", action_id=action_id, error_type=type(exc).__name__)
        return "pending"


async def _assert_exclusive_blobs(db, plan):
    for name, fields in {
        "kb_source_revisions": ("storage_key",), "ocr_run_artifacts": ("blob_key",),
        "kb_compilation_artifacts": ("blob_key",), "kb_compilation_review_artifacts": ("blob_key",),
        "ocr_text_versions": ("document_key", "markdown_key"),
    }.items():
        target = table(name)
        for field in fields:
            if await db.scalar(select(target.c[field]).where(
                target.c[field].in_(list(plan["objects"])),
                ~selected(target, plan["rows"].get(name, [])),
            ).limit(1)):
                raise Conflict("Object còn được tài liệu khác tham chiếu.", code="purge_shared_object")


async def source_purge_job(ctx, action_id):
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        return await execute(db, container.blob_store, container.vector_store, action_id)


async def reconcile(ctx):
    async with AsyncSessionFactory() as db:
        rows = (await db.scalars(select(LifecycleAction).where(
            LifecycleAction.kind == "source", LifecycleAction.action == "delete",
            LifecycleAction.status == "pending",
        ).order_by(LifecycleAction.created_at).limit(50))).all()
        return sum([int(await dispatch(row, ctx["container"].job_queue)) for row in rows if (row.result or {}).get("permanent")])
