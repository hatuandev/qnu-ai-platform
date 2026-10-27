"""Backup workers use scoped snapshots, observed hashes and existing storage/queue ports."""

import asyncio
import hashlib
import uuid
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.operations import service as access
from qnu.domains.operations.backups.archive import MAX_BYTES, MAX_FILES, pack, verify
from qnu.domains.operations.backups.snapshot import freeze
from qnu.domains.operations.jobs.actions import require_action, state_hash
from qnu.domains.operations.models import EvidenceBackup, OperationAction
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, PayloadTooLarge
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore

logger = get_logger(__name__)
LEASE_SECONDS = 900


async def execute(db: AsyncSession, blob: BlobStore, backup_id: str, worker_id: str) -> str:
    now, token = utcnow(), worker_id[:80] + ":" + uuid.uuid4().hex
    claimed = await db.scalar(
        update(EvidenceBackup)
        .where(
            EvidenceBackup.id == backup_id,
            (EvidenceBackup.status == "queued")
            | ((EvidenceBackup.status == "running") & (EvidenceBackup.lease_expires_at < now)),
        )
        .values(
            status="running",
            worker_id=token,
            started_at=func.coalesce(EvidenceBackup.started_at, now),
            lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
        )
        .returning(EvidenceBackup.id)
    )
    await db.commit()
    if not claimed:
        return "not_claimed"
    row = await db.get(EvidenceBackup, backup_id)
    workspace_id, creator = row.workspace_id, row.created_by
    await db.commit()
    actor = access.background_actor(creator)
    try:
        # One MVCC snapshot across all scoped tables; providers/credentials are excluded.
        await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        await access.authorize(db, actor, workspace_id, admin=True)
        snapshot, references = await freeze(db, workspace_id)
        snapshot["captured_at"] = utcnow().isoformat()
        await db.commit()
        objects, total = [], 0
        if len(references) > MAX_FILES:
            raise PayloadTooLarge("Quá nhiều tệp sao lưu.", code="backup_limit_exceeded")
        for key, expected in sorted(references.items()):
            if expected is None and not await blob.exists(key):
                continue
            payload = await blob.get_bytes(key)
            total += len(payload)
            if total > MAX_BYTES:
                raise PayloadTooLarge("Bản sao lưu vượt giới hạn.", code="backup_limit_exceeded")
            objects.append((key, payload, expected))
        payload, manifest = await asyncio.to_thread(pack, snapshot, objects)
        sha = hashlib.sha256(payload).hexdigest()
        await asyncio.to_thread(verify, payload, sha)
        key = f"v1/workspaces/{workspace_id}/backups/{backup_id}/{sha}.zip"
        await blob.put_bytes(key, payload, "application/zip")
        await asyncio.to_thread(verify, await blob.get_bytes(key), sha)
        await access.authorize(db, actor, workspace_id, admin=True, lock=True)
        completed = await db.scalar(
            update(EvidenceBackup)
            .where(
                EvidenceBackup.id == backup_id,
                EvidenceBackup.status == "running",
                EvidenceBackup.worker_id == token,
                EvidenceBackup.lease_expires_at > utcnow(),
            )
            .values(
                status="completed",
                finished_at=utcnow(),
                lease_expires_at=None,
                blob_key=key,
                sha256=sha,
                size_bytes=len(payload),
                manifest=manifest,
                error_code=None,
            )
            .returning(EvidenceBackup.id)
        )
        if not completed:
            raise Conflict("Worker sao lưu mất ownership.", code="backup_claim_lost")
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="backup.completed",
            detail={"backup_id": backup_id, "sha256": sha, "objects": len(objects)},
        )
        await db.commit()
        return "completed"
    except (Exception, asyncio.CancelledError) as exc:
        await db.rollback()
        code = exc.code if isinstance(exc, AppException) else "backup_interrupted"
        status = "failed" if isinstance(exc, AppException) else "uncertain"
        await db.execute(
            update(EvidenceBackup)
            .where(
                EvidenceBackup.id == backup_id,
                EvidenceBackup.worker_id == token,
                EvidenceBackup.status == "running",
            )
            .values(status=status, error_code=code, lease_expires_at=None, finished_at=utcnow())
        )
        await db.commit()
        logger.warning("backup_stopped", backup_id=backup_id, error_code=code)
        if isinstance(exc, asyncio.CancelledError):
            raise
        return status


async def delete(db: AsyncSession, blob: BlobStore, backup_id: str, action_id: str) -> str:
    action = await db.get(OperationAction, action_id)
    if (
        action is None
        or action.job_id != backup_id
        or action.action != "delete_backup"
        or action.status not in {"pending", "dispatched"}
    ):
        return "not_approved"
    actor = access.background_actor(action.actor_ref)
    await access.authorize(db, actor, action.workspace_id, admin=True, lock=True)
    row = await db.scalar(
        select(EvidenceBackup)
        .where(EvidenceBackup.id == backup_id, EvidenceBackup.workspace_id == action.workspace_id)
        .with_for_update()
    )
    if row is None:
        return "not_found"
    if row.status == "deleted" and row.delete_action_id == action_id:
        return "deleted"
    require_action("backup", row, "delete_backup")
    if row.status == "completed" and state_hash(row) != action.state_sha256:
        raise Conflict("Bản sao lưu đã thay đổi.", code="operation_preview_stale")
    if row.status == "deleting" and row.delete_action_id != action_id:
        raise Conflict("Bản sao lưu đang có thao tác khác.", code="operation_preview_stale")
    if not row.blob_key or not row.blob_key.startswith(
        f"v1/workspaces/{row.workspace_id}/backups/{row.id}/"
    ):
        raise Conflict("Đích xóa không phải bản sao lưu.", code="backup_delete_target_invalid")
    row.status, row.delete_action_id = "deleting", action_id
    row.lease_expires_at = utcnow() + timedelta(seconds=LEASE_SECONDS)
    key, workspace_id = row.blob_key, row.workspace_id
    await db.commit()
    try:
        await blob.delete(key)
    except Exception as exc:
        logger.warning("backup_delete_pending", backup_id=backup_id)
        raise AppException(
            "Chưa xóa được bản sao lưu; giữ biên nhận để phục hồi.",
            code="backup_delete_pending",
            status_code=503,
        ) from exc
    await access.authorize(db, actor, workspace_id, admin=True, lock=True)
    await db.refresh(row, with_for_update=True)
    if row.status == "deleted":
        return "deleted"
    row.status, row.lease_expires_at = "deleted", None
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="backup.deleted",
        detail={"backup_id": backup_id, "action_id": action_id},
    )
    await db.commit()
    return "deleted"
