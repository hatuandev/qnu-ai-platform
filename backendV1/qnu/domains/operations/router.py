"""Thin operations API: observed progress, explicit recovery, protected evidence backups."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.permissions import require_permission
from qnu.domains.operations import gc, readiness, reset, service, system_backup
from qnu.domains.operations.backups import service as backups
from qnu.domains.operations.jobs import actions
from qnu.domains.operations.schemas import (
    ActionAccept,
    ActionView,
    BackupRequest,
    BackupView,
    JobKind,
    JobView,
    RecoveryPreviewRequest,
    SystemResetRequest,
    SystemResetResponse,
)
from qnu.platform.errors import PayloadTooLarge
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/workspaces/{workspace_id}/operations",
    tags=["Operations"],
    dependencies=[Depends(no_store)],
)
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]
Queue = Annotated[JobQueue | None, Depends(get_job_queue)]
Key = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


@router.get("/jobs")
async def jobs(
    workspace_id: str,
    db: DB,
    actor: Actor,
    kind: JobKind | None = None,
    status: str | None = Query(None, min_length=1, max_length=16),
    collection_id: str | None = Query(None, max_length=64),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    return await service.list_jobs(
        db, actor, workspace_id, kind, status, collection_id, limit, offset
    )


@router.get("/summary")
async def summary(workspace_id: str, db: DB, actor: Actor) -> dict:
    return await service.summary(db, actor, workspace_id)


@router.get("/readiness")
async def readiness_status(workspace_id: str, db: DB, actor: Actor, request: Request):
    return await readiness.inspect(db, actor, workspace_id, request.app.state.container)


@router.get("/jobs/{kind}/{job_id}", response_model=JobView)
async def job(workspace_id: str, kind: JobKind, job_id: str, db: DB, actor: Actor):
    return await service.job_detail(db, actor, workspace_id, kind, job_id)


@router.post("/jobs/{kind}/{job_id}/recovery-preview", response_model=ActionView)
async def recovery_preview(
    workspace_id: str,
    kind: JobKind,
    job_id: str,
    body: RecoveryPreviewRequest,
    db: DB,
    actor: Actor,
):
    return await actions.preview(db, actor, workspace_id, kind, job_id, body)


@router.post("/actions", response_model=ActionView, status_code=202)
async def accept_action(
    workspace_id: str, body: ActionAccept, idempotency_key: Key, db: DB, actor: Actor, queue: Queue
):
    return await actions.accept(db, actor, workspace_id, body, idempotency_key, queue)


@router.get("/actions/{action_id}", response_model=ActionView)
async def action_status(workspace_id: str, action_id: str, db: DB, actor: Actor):
    return await service.action_status(db, actor, workspace_id, action_id)


@router.get("/backups")
async def backup_list(
    workspace_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    return await backups.list_backups(db, actor, workspace_id, limit, offset)


@router.post("/backups", response_model=BackupView, status_code=202)
async def backup_create(
    workspace_id: str, body: BackupRequest, idempotency_key: Key, db: DB, actor: Actor, queue: Queue
):
    return await backups.request(db, actor, workspace_id, body, idempotency_key, queue)


@router.get("/backups/{backup_id}", response_model=BackupView)
async def backup_status(workspace_id: str, backup_id: str, db: DB, actor: Actor):
    return await backups.get(db, actor, workspace_id, backup_id)


@router.get("/backups/{backup_id}/verify")
async def backup_verify(
    workspace_id: str, backup_id: str, db: DB, actor: Actor, blob: Blob
) -> dict:
    _, _, report = await backups.read(db, blob, actor, workspace_id, backup_id)
    return report


@router.get("/backups/{backup_id}/download")
async def backup_download(
    workspace_id: str, backup_id: str, db: DB, actor: Actor, blob: Blob
) -> Response:
    row, payload, _ = await backups.read(db, blob, actor, workspace_id, backup_id)
    return Response(
        payload,
        media_type="application/zip",
        headers={
            "ETag": f'"{row.sha256}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'attachment; filename="{row.id}.zip"',
        },
    )


@router.post("/backups/{backup_id}/delete-preview", response_model=ActionView)
async def backup_delete_preview(
    workspace_id: str, backup_id: str, body: RecoveryPreviewRequest, db: DB, actor: Actor
):
    return await actions.preview(
        db, actor, workspace_id, "backup", backup_id, body, "delete_backup"
    )


@router.get("/retention")
async def retention(workspace_id: str, db: DB, actor: Actor) -> dict:
    return await service.retention(db, actor, workspace_id)


@router.post("/storage-cleanups/previews")
async def storage_cleanup_preview(
    workspace_id: str, body: gc.CleanupPreview, db: DB, actor: Actor, blob: Blob
):
    return await gc.preview(db, blob, actor, workspace_id, body)


@router.post("/storage-cleanups/actions")
async def storage_cleanup_accept(
    workspace_id: str, body: ActionAccept, idempotency_key: Key, db: DB, actor: Actor, blob: Blob
):
    return await gc.accept(db, blob, actor, workspace_id, body, idempotency_key)


@router.get("/storage-cleanups/actions/{action_id}")
async def storage_cleanup_status(workspace_id: str, action_id: str, db: DB, actor: Actor):
    return gc.response(await gc.load(db, actor, workspace_id, action_id))


system_router = APIRouter(
    prefix="/operations",
    tags=["Operations · System"],
    dependencies=[Depends(no_store)],
)


@system_router.post("/system-reset-and-seed", response_model=SystemResetResponse)
async def system_reset_and_seed(
    body: SystemResetRequest,
    db: DB,
    actor: Annotated[AuthActor, Depends(require_permission("ai.admin"))],
    blob: Blob,
    request: Request,
):
    container = getattr(request.app.state, "container", None)
    vectors = getattr(container, "vector_store", None)
    return await reset.perform_system_reset_and_seed(
        db=db,
        actor=actor,
        blob=blob,
        vectors=vectors,
        request=body,
    )


@system_router.post("/system-backups/export")
async def system_backup_export(
    _actor: Annotated[AuthActor, Depends(require_permission("ai.admin"))],
    target: Literal["all", "postgres", "qdrant"] = Query("all"),
) -> Response:
    payload, filename, meta = await system_backup.export_system_backup(target=target)
    return Response(
        payload,
        media_type="application/gzip",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Backup-Sha256": str(meta.get("bundle_sha256") or ""),
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@system_router.post("/system-backups/restore")
async def system_backup_restore(
    _actor: Annotated[AuthActor, Depends(require_permission("ai.admin"))],
    file: UploadFile = File(...),
    target: Literal["all", "postgres", "qdrant"] = Form("all"),
    confirm: bool = Form(False),
) -> dict:
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > system_backup.MAX_UPLOAD_BYTES:
                raise PayloadTooLarge(
                    "Tệp sao lưu vượt giới hạn dung lượng (512 MB).",
                    code="backup_limit_exceeded",
                )
            chunks.append(chunk)
    finally:
        await file.close()
    payload = b"".join(chunks)
    return await system_backup.inspect_and_restore_system_backup(
        payload,
        file.filename or "backup.tar.gz",
        target=target,
        confirm=confirm,
    )

