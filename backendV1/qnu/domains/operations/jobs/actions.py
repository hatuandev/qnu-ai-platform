"""Durable preview/accept outbox: delivery never resets failed/uncertain model state."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.ocr.ids import new_id
from qnu.domains.operations import service
from qnu.domains.operations.jobs.catalog import SPECS, load_job, recoverable
from qnu.domains.operations.models import OperationAction
from qnu.domains.operations.schemas import ActionAccept, RecoveryPreviewRequest
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.database import Base
from qnu.platform.errors import Conflict, EntityNotFound, Forbidden
from qnu.platform.logging import get_logger
from qnu.ports.job_queue import JobQueue

logger = get_logger(__name__)


def state_hash(row: Base) -> str:
    fields = (
        "status",
        "attempt_count",
        "lease_expires_at",
        "worker_id",
        "config",
        "config_fingerprint",
        "request_started_at",
        "input_sha256",
        "pending_batch",
        "sha256",
        "retain_until",
        "blob_key",
    )
    values = {k: getattr(row, k, None) for k in fields}
    return digest({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in values.items()})


def preview_hash(row: OperationAction) -> str:
    return digest(
        {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "actor": row.actor_ref,
            "kind": row.kind,
            "job_id": row.job_id,
            "action": row.action,
            "reason": row.reason,
            "state_sha256": row.state_sha256,
            "expires_at": row.expires_at.isoformat(),
        }
    )


def require_action(kind: str, target: Base, action: str) -> None:
    if action == "delete_backup":
        if (
            kind != "backup"
            or target.status not in {"completed", "deleting"}
            or not target.retain_until
            or target.retain_until > utcnow()
        ):
            raise Conflict("Bản sao lưu chưa đến hạn xóa.", code="backup_retention_protected")
        return
    allowed, reason = recoverable(kind, target)
    if not allowed:
        raise Conflict(reason, code="operation_recovery_not_allowed")


async def preview(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    kind: str,
    job_id: str,
    body: RecoveryPreviewRequest,
    action: str = "dispatch",
) -> OperationAction:
    await service.authorize(
        db, actor, workspace_id, write=True, admin=action == "delete_backup", lock=True
    )
    await service.authorize(
        db, service.background_actor(actor), workspace_id, write=True, admin=kind == "backup"
    )
    target = await load_job(db, workspace_id, kind, job_id, lock=True)
    require_action(kind, target, action)
    if action == "delete_backup" and target.status == "deleting":
        raise Conflict("Bản sao lưu đang được xóa.", code="backup_delete_in_progress")
    if not body.reason.strip():
        raise Conflict("Cần lý do thao tác.", code="operation_reason_required")
    row = OperationAction(
        id=new_id("opa"),
        workspace_id=workspace_id,
        actor_ref=actor_ref(actor),
        kind=kind,
        job_id=job_id,
        action=action,
        reason=body.reason.strip(),
        state_sha256=state_hash(target),
        status="preview",
        expires_at=utcnow() + timedelta(seconds=get_settings().PUBLICATION_PREVIEW_TTL_SECONDS),
    )
    row.preview_sha256 = preview_hash(row)
    db.add(row)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="operation.previewed",
        detail={"action_id": row.id, "kind": kind, "job_id": job_id, "action": action},
    )
    await db.commit()
    return row


async def accept(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    body: ActionAccept,
    key: str,
    queue: JobQueue | None,
) -> OperationAction:
    await service.authorize(db, actor, workspace_id, write=True, lock=True)
    fingerprint = digest(body.model_dump())
    previous = await db.scalar(
        select(OperationAction).where(
            OperationAction.workspace_id == workspace_id,
            OperationAction.actor_ref == actor_ref(actor),
            OperationAction.idempotency_key == key,
        )
    )
    if previous:
        if previous.request_hash != fingerprint:
            raise Conflict("Khóa thao tác đã dùng cho yêu cầu khác.", code="idempotency_conflict")
        await service.authorize(
            db, actor, workspace_id, admin=previous.kind == "backup", write=True
        )
        await db.commit()
        await dispatch(db, previous.id, queue)
        return previous
    row = await db.scalar(
        select(OperationAction)
        .where(
            OperationAction.id == body.preview_id,
            OperationAction.workspace_id == workspace_id,
            OperationAction.actor_ref == actor_ref(actor),
        )
        .with_for_update()
    )
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy bản xem trước của bạn.", code="operation_preview_not_found"
        )
    await service.authorize(db, actor, workspace_id, admin=row.kind == "backup", write=True)
    if (
        row.status != "preview"
        or row.expires_at <= utcnow()
        or row.preview_sha256 != body.preview_sha256
        or row.preview_sha256 != preview_hash(row)
    ):
        raise Conflict("Bản xem trước đã cũ hoặc không khớp.", code="operation_preview_stale")
    target = await load_job(db, workspace_id, row.kind, row.job_id, lock=True)
    if state_hash(target) != row.state_sha256:
        raise Conflict("Tác vụ đã thay đổi sau khi xem trước.", code="operation_preview_stale")
    require_action(row.kind, target, row.action)
    row.idempotency_key, row.request_hash, row.status = key, fingerprint, "pending"
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="operation.accepted",
        detail={"action_id": row.id, "job_id": row.job_id, "action": row.action},
    )
    await db.commit()
    await dispatch(db, row.id, queue)
    return row


async def dispatch(db: AsyncSession, action_id: str, queue: JobQueue | None) -> bool:
    row = await db.get(OperationAction, action_id)
    if row is None or row.status != "pending" or queue is None:
        return False
    try:
        await service.authorize(
            db,
            service.background_actor(row.actor_ref),
            row.workspace_id,
            write=True,
            admin=row.kind == "backup",
            lock=True,
        )
        target = await load_job(db, row.workspace_id, row.kind, row.job_id, lock=True)
        require_action(row.kind, target, row.action)
        if state_hash(target) != row.state_sha256:
            raise Conflict("Tác vụ đã đổi.", code="operation_preview_stale")
    except (Conflict, Forbidden, EntityNotFound):
        row.status = "superseded"
        await db.commit()
        return False
    task = "evidence_backup_delete" if row.action == "delete_backup" else SPECS[row.kind].task
    args = (row.job_id, row.id) if row.action == "delete_backup" else (row.job_id,)
    try:
        await queue.enqueue(task, *args, job_id="qnu:v1:operation:" + row.id)
    except Exception:
        logger.warning("operation_dispatch_pending", action_id=row.id)
        return False
    row.status, row.dispatched_at = "dispatched", utcnow()
    await db.commit()
    return True
