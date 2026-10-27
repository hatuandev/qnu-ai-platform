"""Explicit cleanup of old, unreferenced derived files owned by terminal v1 jobs."""

import hashlib
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.ocr.ids import new_id
from qnu.domains.operations import service
from qnu.domains.operations.backups.snapshot import freeze
from qnu.domains.operations.jobs.catalog import SPECS, job_union
from qnu.domains.operations.models import StorageCleanupAction
from qnu.domains.operations.schemas import ActionAccept
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobObject, BlobStore


class CleanupPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=1, max_length=2000)
    min_age_hours: int = Field(24, strict=True, ge=24, le=8760)


KINDS = {
    "ocr": ("ocr", {"canonical_json", "markdown", "manifest", "page_image"}),
    "compilation": ("compiler", {"input_snapshot", "draft_json", "markdown"}),
    "compilation-review": ("review", {"input_snapshot", "report_json", "markdown"}),
    "index": ("index", {"manifest"}),
}


async def references(db: AsyncSession, workspace_id: str) -> dict[str, str | None]:
    jobs = job_union(workspace_id, None, None, None)
    if await db.scalar(
        select(jobs.c.id).where(jobs.c.status.in_(("queued", "running", "deleting"))).limit(1)
    ):
        raise Conflict(
            "Còn tác vụ đang xử lý; chưa thể chứng minh tệp mồ côi.", code="storage_cleanup_busy"
        )
    _, refs = await freeze(db, workspace_id)
    return refs


async def eligible(db: AsyncSession, workspace_id: str, key: str) -> bool:
    prefix = f"v1/workspaces/{workspace_id}/"
    if key.startswith(prefix):
        parts = key[len(prefix) :].split("/")
        if len(parts) < 4 or parts[0] not in KINDS:
            return False
        job_kind, allowed = KINDS[parts[0]]
        if parts[2] not in allowed:
            return False
        job_id = parts[1]
    elif key.startswith(f"ocr-text/{workspace_id}/"):
        parts = key.split("/")
        if len(parts) != 5:
            return False
        job_kind, job_id = "ocr", parts[2]
    else:
        return False  # Originals, raw responses, backups and unknown namespaces are retained.
    spec = SPECS[job_kind]
    row = await db.scalar(
        select(spec.model).where(
            getattr(spec.model, spec.id_field) == job_id, spec.model.workspace_id == workspace_id
        )
    )
    return row is not None and row.status not in {"queued", "running"}


def signature(row: StorageCleanupAction) -> str:
    return digest(
        {
            "id": row.id,
            "actor": row.actor_ref,
            "workspace": row.workspace_id,
            "target": row.target_hash,
            "reason": row.reason,
            "candidates": row.candidates,
            "expires_at": row.expires_at.isoformat(),
        }
    )


def response(row: StorageCleanupAction) -> dict:
    return {
        "id": row.id,
        "status": row.status,
        "preview_sha256": row.preview_sha256,
        "expires_at": row.expires_at,
        "files": [
            {"id": digest(item["key"]), "bytes": item["size"], "modified_at": item["modified_at"]}
            for item in row.candidates
        ],
        "total_bytes": sum(item["size"] for item in row.candidates),
        "result": row.result,
    }


async def preview(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, workspace_id: str, body: CleanupPreview
) -> dict:
    await service.authorize(db, actor, workspace_id, admin=True, lock=True)
    refs = await references(db, workspace_id)
    cutoff, candidates, size = utcnow() - timedelta(hours=body.min_age_hours), [], 0
    for prefix in [f"v1/workspaces/{workspace_id}/", f"ocr-text/{workspace_id}/"]:
        for item in await blob.list_objects(prefix):
            if (
                item.key in refs
                or item.modified_at >= cutoff
                or not await eligible(db, workspace_id, item.key)
            ):
                continue
            size += item.size
            if len(candidates) >= 500 or size > 256 * 1024 * 1024:
                raise Conflict(
                    "Quá nhiều tệp cần dọn; chưa tạo bản xem trước thiếu.",
                    code="storage_cleanup_limit",
                )
            payload = await blob.get_bytes(item.key)
            candidates.append(
                {
                    "key": item.key,
                    "size": item.size,
                    "modified_at": item.modified_at.isoformat(),
                    "version": item.version,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    row = StorageCleanupAction(
        id=new_id("gc"),
        workspace_id=workspace_id,
        actor_ref=actor_ref(actor),
        status="preview",
        reason=body.reason,
        target_hash=blob.target_hash,
        candidates=sorted(candidates, key=lambda item: item["key"]),
        expires_at=utcnow() + timedelta(minutes=5),
    )
    row.preview_sha256 = signature(row)
    db.add(row)
    await audit(db, actor, row, "previewed")
    await db.commit()
    return response(row)


async def load(
    db: AsyncSession, actor: AuthActor, workspace_id: str, action_id: str
) -> StorageCleanupAction:
    await service.authorize(db, actor, workspace_id, admin=True, lock=True)
    row = await db.scalar(
        select(StorageCleanupAction)
        .where(
            StorageCleanupAction.id == action_id,
            StorageCleanupAction.workspace_id == workspace_id,
            StorageCleanupAction.actor_ref == actor_ref(actor),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy bản xem trước của bạn.", code="storage_cleanup_not_found"
        )
    return row


async def accept(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    body: ActionAccept,
    key: str,
) -> dict:
    row = await load(db, actor, workspace_id, body.preview_id)
    fingerprint = digest(body.model_dump())
    previous = await db.scalar(
        select(StorageCleanupAction).where(
            StorageCleanupAction.workspace_id == workspace_id,
            StorageCleanupAction.actor_ref == actor_ref(actor),
            StorageCleanupAction.idempotency_key == key,
        )
    )
    if previous and (previous.id != row.id or previous.request_hash != fingerprint):
        raise Conflict("Khóa đã dùng cho thao tác khác.", code="idempotency_conflict")
    if row.idempotency_key is not None and row.idempotency_key != key:
        raise Conflict("Dùng lại khóa của thao tác đã nhận.", code="idempotency_conflict")
    if row.status == "completed":
        return response(row)
    if (
        row.preview_sha256 != body.preview_sha256
        or row.preview_sha256 != signature(row)
        or row.target_hash != blob.target_hash
        or (row.status == "preview" and row.expires_at <= utcnow())
    ):
        raise Conflict(
            "Bản xem trước đã cũ hoặc đích lưu trữ đã đổi.", code="storage_cleanup_stale"
        )
    refs = await references(db, workspace_id)
    for item in row.candidates:
        if item["key"] in refs or not await eligible(db, workspace_id, item["key"]):
            raise Conflict("Tệp đã được tham chiếu; cần xem lại.", code="storage_cleanup_stale")
    if row.status == "preview":
        row.status, row.idempotency_key, row.request_hash = "pending", key, fingerprint
        await audit(db, actor, row, "accepted")
        await db.commit()  # Persist approved intent before external deletion.
        row = await load(db, actor, workspace_id, row.id)
        refs = await references(db, workspace_id)
    outcomes = []
    for item in row.candidates:
        if item["key"] in refs:
            raise Conflict("Tệp đã được dùng lại.", code="storage_cleanup_stale")
        obj = BlobObject(
            item["key"], item["size"], datetime.fromisoformat(item["modified_at"]), item["version"]
        )
        outcome = await blob.delete_if_unchanged(obj, item["sha256"])
        if outcome not in {"deleted", "absent"}:
            raise Conflict("Tệp đã đổi; chưa xóa nội dung mới.", code="storage_cleanup_stale")
        outcomes.append({"id": digest(item["key"]), "outcome": outcome})
    row.status, row.result = "completed", {"files": outcomes, "originals_and_raw_retained": True}
    await audit(db, actor, row, "completed")
    await db.commit()
    return response(row)


async def audit(db: AsyncSession, actor: AuthActor, row: StorageCleanupAction, phase: str) -> None:
    await record_workspace_event(
        db,
        workspace_id=row.workspace_id,
        actor=actor,
        action="storage_cleanup." + phase,
        detail={"action_id": row.id, "file_count": len(row.candidates)},
    )
