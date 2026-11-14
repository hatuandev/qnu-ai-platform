"""Preview/accept authorization, optimistic state checks and idempotent lifecycle receipts."""

from datetime import timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.conversations.models import Conversation
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.lifecycle import effects, targets
from qnu.domains.lifecycle.models import LifecycleAction, ResourceState
from qnu.domains.lifecycle.schemas import AcceptRequest, PreviewRequest
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import (
    actor_ref,
    caller_workspace_role,
    resolve_workspace_access,
)
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue
from qnu.ports.vector_store import VectorStore


async def authorize(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    kind: str | None = None,
    action: str | None = None,
    parameters: dict | None = None,
) -> None:
    roles = None
    if kind != "conversation" and not (
        kind == "job" and (parameters or {}).get("job_kind") == "turn"
    ):
        roles = (
            ("admin",)
            if kind in {"assistant", "index"} or action in {"delete", "withdraw", "replace"}
            else ("admin", "editor")
        )
    await resolve_workspace_access(db, actor, workspace_id, required_roles=roles, for_update=True)


def preview_hash(row: LifecycleAction) -> str:
    return digest(
        {
            "id": row.id,
            "actor": row.actor_ref,
            "workspace_id": row.workspace_id,
            "kind": row.kind,
            "resource_id": row.resource_id,
            "action": row.action,
            "parameters": row.parameters,
            "reason": row.reason,
            "impact": row.impact,
            "state_sha256": row.state_sha256,
            "expires_at": row.expires_at.isoformat(),
        }
    )


async def inspect(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    kind: str,
    resource_id: str,
    action: str,
    parameters: dict,
) -> tuple[object, str, dict]:
    row = await targets.target(db, actor, workspace_id, kind, resource_id, parameters)
    from qnu.domains.lifecycle import purge

    await purge.require_not_pending(db, workspace_id, kind, resource_id)
    resource = await targets.state(db, workspace_id, kind, resource_id)
    if action == "restore" and resource and resource.status == "deleted" and kind != "conversation":
        await resolve_workspace_access(
            db, actor, workspace_id, required_roles=("admin",), for_update=True
        )
    targets.require_operation(kind, action, row, resource)
    if action == "withdraw":
        impact_note = {"withdraw_keeps_originals": True, "restore_available": True}
    else:
        impact_note = {}
    current, impact = await targets.snapshot(db, workspace_id, kind, row, parameters)
    impact.update(impact_note)
    if action == "delete" and kind in purge.PURGE_KINDS:
        plan, permanent_impact = await purge.inspect_purge(db, kind, row, blob)
        current["purge_graph_sha256"] = plan["graph_sha256"]
        impact.update(permanent_impact)
    if action == "replace":
        from qnu.domains.lifecycle.replacement import inspect_replacement

        current["replacement"], impact["replacement"] = await inspect_replacement(
            db, blob, actor, row, parameters
        )
    if action == "cleanup":
        if row.is_active:
            collection_state = await targets.state(
                db, workspace_id, "collection", row.collection_id
            )
            if not collection_state or collection_state.status == "active":
                from qnu.domains.knowledge.index.search import _eligible

                allowed, _ = await _eligible(db, blob, actor, row, None)
                if allowed:
                    raise Conflict(
                        "Chỉ mục còn nội dung đang phục vụ.", code="lifecycle_index_in_use"
                    )
        impact["retires_active_index"] = row.is_active
        impact["deleted_data"] = ["inactive_vector_collection", "index_chunks"]
        impact["restore_requires_new_index"] = True
    if action == "restore":
        impact["publication_resumes_if_still_current"] = kind in {
            "source",
            "collection",
            "document",
        }
        impact["cancelled_jobs_restart_automatically"] = False
    return row, digest({"state": current, "impact": impact}), impact


async def preview(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, workspace_id: str, body: PreviewRequest
) -> LifecycleAction:
    parameters = body.model_dump(
        exclude={"kind", "resource_id", "action", "reason"}, exclude_none=True
    )
    await authorize(db, actor, workspace_id, body.kind, body.action, parameters)
    _, state_hash, impact = await inspect(
        db, blob, actor, workspace_id, body.kind, body.resource_id, body.action, parameters
    )
    row = LifecycleAction(
        id=new_id("lca"),
        workspace_id=workspace_id,
        actor_ref=actor_ref(actor),
        kind=body.kind,
        resource_id=body.resource_id,
        action=body.action,
        reason=body.reason,
        parameters=parameters,
        impact=impact,
        state_sha256=state_hash,
        status="preview",
        expires_at=utcnow() + timedelta(seconds=get_settings().PUBLICATION_PREVIEW_TTL_SECONDS),
    )
    row.preview_sha256 = preview_hash(row)
    db.add(row)
    await event(db, actor, row, "previewed")
    await db.commit()
    return row


async def detail(
    db: AsyncSession, actor: AuthActor, workspace_id: str, action_id: str
) -> LifecycleAction:
    await resolve_workspace_access(db, actor, workspace_id, for_update=True)
    visible = LifecycleAction.actor_ref == actor_ref(actor)
    if await caller_workspace_role(db, actor, workspace_id) == "admin":
        # A workspace admin can resume a confirmed permanent source or collection
        # deletion that outlived its confirmer. Other receipts stay bound to their owner.
        visible = or_(
            visible,
            and_(
                LifecycleAction.kind.in_(("source", "collection")),
                LifecycleAction.action == "delete",
                LifecycleAction.status != "preview",
            ),
        )
    row = await db.scalar(
        select(LifecycleAction)
        .where(
            LifecycleAction.id == action_id,
            LifecycleAction.workspace_id == workspace_id,
            visible,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy bản xem trước của bạn.", code="lifecycle_action_not_found"
        )
    await authorize(db, actor, workspace_id, row.kind, row.action, row.parameters)
    return row


async def accept(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    queue: JobQueue | None,
    actor: AuthActor,
    workspace_id: str,
    body: AcceptRequest,
    key: str,
) -> LifecycleAction:
    await resolve_workspace_access(db, actor, workspace_id, for_update=True)
    request_hash = digest(body.model_dump())
    previous = await db.scalar(
        select(LifecycleAction).where(
            LifecycleAction.workspace_id == workspace_id,
            LifecycleAction.actor_ref == actor_ref(actor),
            LifecycleAction.idempotency_key == key,
        )
    )
    if previous:
        if previous.request_hash != request_hash:
            raise Conflict("Khóa thao tác đã dùng cho yêu cầu khác.", code="idempotency_conflict")
        row = await detail(db, actor, workspace_id, previous.id)
        if row.status == "pending" and (row.result or {}).get("permanent"):
            from qnu.domains.lifecycle.purge import dispatch

            await db.commit()
            await dispatch(row, queue)
            return row
        if row.status == "completed" or row.action == "replace":
            await db.commit()
            if row.action == "replace" and row.result:
                from qnu.domains.knowledge.index.models import IndexRun
                from qnu.domains.knowledge.index.service import dispatch

                run = await db.get(IndexRun, row.result["index_run_id"])
                if run.status == "queued":
                    await dispatch(db, run, queue)
            return row
    else:
        row = await detail(db, actor, workspace_id, body.preview_id)
        if (
            row.status != "preview"
            or row.expires_at <= utcnow()
            or row.preview_sha256 != body.preview_sha256
            or row.preview_sha256 != preview_hash(row)
        ):
            raise Conflict("Bản xem trước đã cũ hoặc không khớp.", code="lifecycle_preview_stale")
        target, current_hash, _ = await inspect(
            db, blob, actor, workspace_id, row.kind, row.resource_id, row.action, row.parameters
        )
        if current_hash != row.state_sha256:
            raise Conflict(
                "Tài nguyên đã thay đổi; cần xem trước lại.", code="lifecycle_preview_stale"
            )
        row.idempotency_key, row.request_hash, row.accepted_at = key, request_hash, utcnow()
        row.status = "pending"
        await event(db, actor, row, "accepted")
        if row.action == "replace":
            from qnu.domains.lifecycle.replacement import prepare_replacement

            return await prepare_replacement(db, blob, vectors, queue, actor, row, target)
        if row.action == "delete":
            from qnu.domains.lifecycle import purge

            if row.kind in purge.PURGE_KINDS:
                await purge.prepare(db, blob, vectors, actor, row, target)
                await db.commit()
                await purge.dispatch(row, queue)
                return row
        if row.action != "cleanup":
            row.result = await effects.apply(db, row, target)
            row.status, row.finished_at = "completed", utcnow()
            await event(db, actor, row, "completed")
            await db.commit()
            return row
        if target.is_active:
            target.is_active = False
            row.result = {"index_retired": True}
        await db.commit()  # Durable intent before external deletion, safe to retry by the same key.
        row = await detail(db, actor, workspace_id, row.id)
    target = await targets.target(
        db, actor, workspace_id, row.kind, row.resource_id, row.parameters
    )
    try:
        row.result = await effects.cleanup(db, vectors, row, target)
        row.status, row.finished_at, row.error_code = "completed", utcnow(), None
        await event(db, actor, row, "completed")
        await db.commit()
    except Exception as exc:
        row_id = row.id
        await db.rollback()
        row = await detail(db, actor, workspace_id, row_id)
        row.error_code = exc.code if isinstance(exc, AppException) else "lifecycle_cleanup_failed"
        await db.commit()
        raise
    return row


async def event(db: AsyncSession, actor: AuthActor, row: LifecycleAction, phase: str) -> None:
    await record_workspace_event(
        db,
        workspace_id=row.workspace_id,
        actor=actor,
        action="lifecycle." + phase,
        detail={
            "action_id": row.id,
            "kind": row.kind,
            "resource_id": row.resource_id,
            "operation": row.action,
        },
    )


async def resources(
    db: AsyncSession, actor: AuthActor, workspace_id: str, limit: int, offset: int
) -> dict:
    await resolve_workspace_access(db, actor, workspace_id)
    # Members see only their own conversation tombstones; other resource trash is editorial.
    from qnu.domains.workspaces.access import is_platform_admin

    statement = select(ResourceState).where(
        ResourceState.workspace_id == workspace_id, ResourceState.status != "active"
    )
    if not is_platform_admin(actor):
        from qnu.domains.workspaces.models import WorkspaceMember

        member = await db.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.actor_ref == actor_ref(actor),
            )
        )
        if member is None or member.role == "member":
            statement = statement.where(ResourceState.kind == "conversation")
    own = select(Conversation.id).where(
        Conversation.workspace_id == workspace_id, Conversation.owner_ref == actor_ref(actor)
    )
    statement = statement.where(
        (ResourceState.kind != "conversation") | ResourceState.resource_id.in_(own)
    )
    rows = (
        await db.scalars(
            statement.order_by(ResourceState.updated_at.desc(), ResourceState.resource_id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return {
        "items": [
            {
                "kind": r.kind,
                "resource_id": r.resource_id,
                "status": r.status,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
        "limit": limit,
        "offset": offset,
    }


async def pending_source_deletions(db, actor, workspace_id, collection_id):
    await authorize(db, actor, workspace_id, "source", "delete")
    return list(
        (
            await db.scalars(
                select(LifecycleAction)
                .where(
                    LifecycleAction.workspace_id == workspace_id,
                    LifecycleAction.actor_ref == actor_ref(actor),
                    LifecycleAction.kind == "source",
                    LifecycleAction.action == "delete",
                    LifecycleAction.status == "pending",
                    LifecycleAction.impact["collection_id"].as_string() == collection_id,
                )
                .order_by(LifecycleAction.created_at.desc())
                .limit(50)
            )
        ).all()
    )


async def active_source_deletions(db, actor, workspace_id, limit, offset):
    """Admin view of pending permanent deletions, including stuck receipts."""
    await resolve_workspace_access(
        db, actor, workspace_id, required_roles=("admin",), for_update=True
    )
    rows = (
        await db.scalars(
            select(LifecycleAction)
            .where(
                LifecycleAction.workspace_id == workspace_id,
                LifecycleAction.kind == "source",
                LifecycleAction.action == "delete",
                LifecycleAction.status == "pending",
            )
            .order_by(
                LifecycleAction.last_error_at.desc().nulls_last(),
                LifecycleAction.created_at,
            )
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(rows)


async def legacy_deleted_sources(db, actor, workspace_id, collection_id, limit, offset):
    """Surface old soft deletions for a new, explicit permanent-deletion preview."""
    from qnu.domains.knowledge.models import KBSource
    from qnu.domains.knowledge.policies.access import load_collection

    await authorize(db, actor, workspace_id, "source", "delete")
    await load_collection(db, workspace_id, collection_id)
    pending = (
        select(LifecycleAction.id)
        .where(
            LifecycleAction.workspace_id == workspace_id,
            LifecycleAction.kind == "source",
            LifecycleAction.resource_id == KBSource.id,
            LifecycleAction.action == "delete",
            LifecycleAction.status == "pending",
        )
        .exists()
    )
    statement = (
        select(KBSource.id.label("source_id"), KBSource.title)
        .join(
            ResourceState,
            (ResourceState.workspace_id == KBSource.workspace_id)
            & (ResourceState.kind == "source")
            & (ResourceState.resource_id == KBSource.id),
        )
        .where(
            KBSource.workspace_id == workspace_id,
            KBSource.collection_id == collection_id,
            ResourceState.status == "deleted",
            ~pending,
        )
    )
    total = await db.scalar(select(func.count()).select_from(statement.subquery()))
    items = (
        (
            await db.execute(
                statement.order_by(KBSource.created_at, KBSource.id).limit(limit).offset(offset)
            )
        )
        .mappings()
        .all()
    )
    return {"items": [dict(row) for row in items], "total": total, "limit": limit, "offset": offset}
