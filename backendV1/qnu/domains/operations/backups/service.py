"""Evidence backup creation/read through the existing storage and queue ports."""

import asyncio
import hashlib
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.ocr.ids import new_id
from qnu.domains.operations import service as access
from qnu.domains.operations.backups.archive import verify
from qnu.domains.operations.models import EvidenceBackup
from qnu.domains.operations.schemas import BackupRequest
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import Conflict, DependencyUnavailable, EntityNotFound
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

logger = get_logger(__name__)


async def list_backups(
    db: AsyncSession, actor: AuthActor, workspace_id: str, limit: int, offset: int
) -> dict:
    from qnu.domains.operations.schemas import BackupView

    await access.authorize(db, actor, workspace_id, admin=True)
    condition = EvidenceBackup.workspace_id == workspace_id
    total = await db.scalar(select(func.count()).select_from(EvidenceBackup).where(condition))
    rows = await db.scalars(
        select(EvidenceBackup)
        .where(condition)
        .order_by(EvidenceBackup.created_at.desc(), EvidenceBackup.id)
        .limit(limit)
        .offset(offset)
    )
    return {
        "items": [BackupView.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get(
    db: AsyncSession, actor: AuthActor, workspace_id: str, backup_id: str
) -> EvidenceBackup:
    await access.authorize(db, actor, workspace_id, admin=True)
    row = await db.scalar(
        select(EvidenceBackup).where(
            EvidenceBackup.id == backup_id, EvidenceBackup.workspace_id == workspace_id
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy bản sao lưu.", code="backup_not_found")
    return row


async def request(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    body: BackupRequest,
    key: str,
    queue: JobQueue | None,
) -> EvidenceBackup:
    await access.authorize(db, actor, workspace_id, admin=True, lock=True)
    await access.authorize(db, access.background_actor(actor), workspace_id, admin=True)
    fingerprint = digest(body.model_dump())
    old = await db.scalar(
        select(EvidenceBackup).where(
            EvidenceBackup.workspace_id == workspace_id,
            EvidenceBackup.created_by == actor_ref(actor),
            EvidenceBackup.idempotency_key == key,
        )
    )
    if old:
        if old.request_hash != fingerprint:
            raise Conflict("Khóa sao lưu đã dùng cho cấu hình khác.", code="idempotency_conflict")
        await db.commit()
        await dispatch(db, old, queue)
        return old
    row = EvidenceBackup(
        id=new_id("bak"),
        workspace_id=workspace_id,
        created_by=actor_ref(actor),
        idempotency_key=key,
        request_hash=fingerprint,
        status="queued",
        retain_until=utcnow() + timedelta(days=body.retention_days)
        if body.retention_days
        else None,
    )
    db.add(row)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="backup.requested",
        detail={"backup_id": row.id, "retention_days": body.retention_days},
    )
    await db.commit()
    await dispatch(db, row, queue)
    return row


async def dispatch(db: AsyncSession, row: EvidenceBackup, queue: JobQueue | None) -> bool:
    if row.status != "queued" or queue is None:
        return False
    try:
        await queue.enqueue("evidence_backup_job", row.id, job_id="qnu:v1:backup:" + row.id)
    except Exception:
        logger.warning("backup_dispatch_pending", backup_id=row.id)
        return False
    row.dispatched_at = utcnow()
    await db.commit()
    return True


async def read(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, workspace_id: str, backup_id: str
) -> tuple[EvidenceBackup, bytes, dict]:
    row = await get(db, actor, workspace_id, backup_id)
    if row.status != "completed" or not row.blob_key:
        raise Conflict("Bản sao lưu chưa sẵn sàng tải.", code="backup_not_completed")
    try:
        payload = await blob.get_bytes(row.blob_key)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được bản sao lưu.", code="backup_storage_unavailable"
        ) from exc
    if len(payload) != row.size_bytes or hashlib.sha256(payload).hexdigest() != row.sha256:
        raise Conflict("Bản sao lưu không khớp toàn vẹn.", code="backup_integrity_failed")
    report = await asyncio.to_thread(verify, payload, row.sha256)
    return row, payload, report
