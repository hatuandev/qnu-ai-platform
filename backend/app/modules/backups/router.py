"""Installation admin only. No restore-to-live or arbitrary uploaded archive endpoint."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.backups import importing, management, scheduler, service
from app.modules.backups.models import BackupRecord
from app.modules.backups.policy import BackupPolicy, load_policy
from app.modules.backups.schemas import BackupCatalogue, BackupRequest, RecoveryRequest

router = APIRouter(prefix="/backups", tags=["Backups"])


async def installation_admin(
    request: Request, actor: AuthActor = Depends(get_current_actor)
) -> AuthActor:
    # No anonymous dev-admin convenience for archives containing all tenants/secrets.
    if not (request.cookies.get("qnu_session") or request.headers.get("authorization")):
        raise AppException(
            "Sao lưu yêu cầu phiên đăng nhập thực.", code="unauthorized", status_code=401
        )
    roles = {role.strip().lower() for role in actor.roles}
    if (
        not actor.authenticated
        or "ai.admin" not in roles
        or not actor.has_permission("ai.system.backup")
    ):
        raise AppException(
            "Chỉ quản trị hệ thống AI.Admin được sao lưu toàn bộ bản cài đặt.",
            code="forbidden",
            status_code=403,
        )
    return actor


@router.get("", response_model=BackupCatalogue, dependencies=[Depends(installation_admin)])
async def list_backups():
    return await service.catalogue()


@router.get("/policy", response_model=BackupPolicy, dependencies=[Depends(installation_admin)])
async def get_policy():
    import asyncio

    return await asyncio.to_thread(load_policy)


@router.put("/policy", response_model=BackupPolicy, dependencies=[Depends(installation_admin)])
async def put_policy(body: BackupPolicy):
    return await scheduler.configure_policy(body)


@router.post("/import", response_model=BackupRecord, status_code=201)
async def upload_archive(request: Request, actor: AuthActor = Depends(installation_admin)):
    return await importing.import_archive(
        request, actor.actor_id, getattr(request.state, "correlation_id", "unknown")
    )


@router.get("/{backup_id}", response_model=BackupRecord, dependencies=[Depends(installation_admin)])
async def get_backup(backup_id: str):
    import asyncio

    from app.modules.backups.catalogue import load_record

    return await asyncio.to_thread(load_record, backup_id)


@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: str, request: Request, actor: AuthActor = Depends(installation_admin)
):
    return await management.remove_backup(
        backup_id, actor.actor_id, getattr(request.state, "correlation_id", "unknown")
    )


@router.put(
    "/{backup_id}/pin", response_model=BackupRecord, dependencies=[Depends(installation_admin)]
)
async def pin_backup(backup_id: str, body: dict[str, bool]):
    if set(body) != {"pinned"}:
        raise AppException("Cần chỉ định trạng thái ghim.", code="BACKUP_PIN_INVALID")
    return await management.pin_backup(backup_id, body["pinned"])


@router.post("/{backup_id}/copy", response_model=BackupRecord, status_code=202)
async def copy_backup(
    backup_id: str, request: Request, actor: AuthActor = Depends(installation_admin)
):
    return await service.start_recovery(
        backup_id, "", "copy", actor.actor_id, getattr(request.state, "correlation_id", "unknown")
    )


@router.post("", response_model=BackupRecord, status_code=202)
async def create_backup(
    body: BackupRequest, request: Request, actor: AuthActor = Depends(installation_admin)
):
    return await service.start_backup(
        body.passphrase.get_secret_value(),
        actor.actor_id,
        getattr(request.state, "correlation_id", "unknown"),
    )


@router.post("/{backup_id}/verify", response_model=BackupRecord, status_code=202)
async def verify_backup(
    backup_id: str,
    body: RecoveryRequest,
    request: Request,
    actor: AuthActor = Depends(installation_admin),
):
    if body.confirmation != "VERIFY":
        raise AppException("Cần xác nhận kiểm tra.", code="BACKUP_CONFIRMATION_REQUIRED")
    return await service.start_recovery(
        backup_id,
        body.passphrase.get_secret_value(),
        "verify",
        actor.actor_id,
        getattr(request.state, "correlation_id", "unknown"),
    )


@router.post("/{backup_id}/drill", response_model=BackupRecord, status_code=202)
async def drill_backup(
    backup_id: str,
    body: RecoveryRequest,
    request: Request,
    actor: AuthActor = Depends(installation_admin),
):
    if body.confirmation != "ISOLATED DRILL":
        raise AppException(
            "Cần xác nhận khôi phục vào sandbox.", code="BACKUP_CONFIRMATION_REQUIRED"
        )
    return await service.start_recovery(
        backup_id,
        body.passphrase.get_secret_value(),
        "drill",
        actor.actor_id,
        getattr(request.state, "correlation_id", "unknown"),
    )


@router.post("/{backup_id}/download-ticket", dependencies=[Depends(installation_admin)])
async def download_ticket(backup_id: str, response: Response):
    await service.download(backup_id)
    path = settings.API_PREFIX + "/backups/" + backup_id + "/download"
    ticket = jwt.encode(
        {
            "backup_id": backup_id,
            "aud": "qnu-backup-download",
            "exp": datetime.now(UTC) + timedelta(seconds=90),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    response.set_cookie(
        "qnu_backup_download",
        ticket,
        max_age=90,
        httponly=True,
        secure=settings.ENVIRONMENT in ("production", "prod"),
        samesite="strict",
        path=path,
    )
    response.headers["Cache-Control"] = "no-store"
    return {"url": path}


@router.get("/{backup_id}/download")
async def download_backup(backup_id: str, request: Request):
    try:
        ticket = jwt.decode(
            request.cookies.get("qnu_backup_download", ""),
            settings.SECRET_KEY,
            algorithms=["HS256"],
            audience="qnu-backup-download",
        )
        if ticket["backup_id"] != backup_id:
            raise ValueError("Wrong archive")
    except (jwt.PyJWTError, ValueError, KeyError):
        raise AppException(
            "Quyền tải bản sao lưu hết hạn; hãy bấm Tải xuống lại.",
            code="unauthorized",
            status_code=401,
        ) from None
    return FileResponse(
        await service.download(backup_id),
        media_type="application/octet-stream",
        filename=backup_id + ".qnubak",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )
