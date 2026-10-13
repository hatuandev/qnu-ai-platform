"""Admin control plane; snapshots and recovery run in an independent process."""

import asyncio
import subprocess
from datetime import UTC, datetime
from uuid import uuid4

import structlog

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.backups.catalogue import (
    backup_root,
    list_records,
    load_record,
    record_path,
    save_record,
)
from app.modules.backups.launcher import spawn_runner
from app.modules.backups.locks import catalogue_lock
from app.modules.backups.models import BackupOperation, BackupRecord
from app.modules.backups.schemas import BackupCatalogue

logger = structlog.get_logger(__name__)
_waiters: set[asyncio.Task] = set()


async def catalogue() -> BackupCatalogue:
    items = await asyncio.to_thread(list_records)
    for record in items:
        if (
            record.status in ("running", "queued")
            and (datetime.now(UTC) - record.updated_at).total_seconds() > 60
        ):
            record.status = "failed"
            record.error = "Tiến trình sao lưu mất heartbeat. Kiểm tra máy chủ; không coi bản dở là thành công."
            record.stage = "Tiến trình bị gián đoạn"
            await asyncio.to_thread(save_record, record)
    return BackupCatalogue(
        items=items[:100], directory=str(backup_root()), drill_enabled=settings.BACKUP_DRILL_ENABLED
    )


async def launch(record: BackupRecord, password: str) -> BackupRecord:
    if record.operation != "copy" and (
        not 12 <= len(password.strip()) <= 256 or "\n" in password or "\r" in password
    ):
        raise AppException(
            "Mật khẩu cần 12–256 ký tự, không chứa ký tự xuống dòng.",
            code="BACKUP_PASSWORD_INVALID",
        )
    record.history.append(
        BackupOperation(
            timestamp=datetime.now(UTC),
            operation=record.operation,
            status="queued",
            actor_id=record.actor_id,
            correlation_id=record.correlation_id,
        )
    )
    await asyncio.to_thread(save_record, record)
    starting = asyncio.create_task(asyncio.to_thread(spawn_runner, record.id, password))
    try:
        proc = await asyncio.shield(starting)
    except asyncio.CancelledError:
        # A cancelled HTTP request cannot orphan a just-created subprocess.
        proc = await starting
        _track_runner(proc)
        raise
    except Exception as exc:
        record.status, record.error = "failed", "Không thể khởi động tiến trình sao lưu độc lập."
        error_type = type(exc).__name__
        record.error += f" ({error_type})"
        record.history.append(
            BackupOperation(
                timestamp=datetime.now(UTC),
                operation=record.operation,
                status="failed",
                actor_id=record.actor_id,
                correlation_id=record.correlation_id,
                error=record.error,
            )
        )
        await asyncio.to_thread(save_record, record)
        logger.error(
            "backup_launch_failed",
            backup_id=record.id,
            correlation_id=record.correlation_id,
            error_type=error_type,
        )
        raise AppException(record.error, code="BACKUP_LAUNCH_FAILED", status_code=503) from None
    _track_runner(proc)
    logger.info(
        "backup_operation_started",
        backup_id=record.id,
        operation=record.operation,
        actor_id=record.actor_id,
        correlation_id=record.correlation_id,
    )
    return record


def _track_runner(process: subprocess.Popen[bytes]) -> None:
    # Reap through a thread: SelectorEventLoop has no subprocess transports.
    waiter = asyncio.create_task(asyncio.to_thread(process.wait))
    _waiters.add(waiter)
    waiter.add_done_callback(_waiters.discard)


async def start_backup(password: str, actor_id: str, correlation_id: str) -> BackupRecord:
    async with catalogue_lock("reservation"):
        return await _start_backup_unlocked(password, actor_id, correlation_id)


async def _start_backup_unlocked(
    password: str, actor_id: str, correlation_id: str, *, origin="manual"
) -> BackupRecord:
    await catalogue()
    if any(item.status in ("queued", "running") for item in await asyncio.to_thread(list_records)):
        raise AppException("Một thao tác sao lưu đang chạy.", code="BACKUP_BUSY", status_code=409)
    now = datetime.now(UTC)
    record = BackupRecord(
        id="bkp_" + uuid4().hex,
        created_at=now,
        updated_at=now,
        actor_id=actor_id,
        correlation_id=correlation_id,
        origin=origin,
    )
    return await launch(record, password)


async def start_recovery(
    backup_id: str, password: str, operation: str, actor_id: str, correlation_id: str
) -> BackupRecord:
    async with catalogue_lock("reservation"):
        return await _start_recovery(backup_id, password, operation, actor_id, correlation_id)


async def _start_recovery(
    backup_id: str, password: str, operation: str, actor_id: str, correlation_id: str
) -> BackupRecord:
    await catalogue()
    if any(item.status in ("queued", "running") for item in await asyncio.to_thread(list_records)):
        raise AppException("Một thao tác sao lưu đang chạy.", code="BACKUP_BUSY", status_code=409)
    record = await asyncio.to_thread(load_record, backup_id)
    if not record.sha256 or not record_path(backup_id, ".qnubak").is_file():
        raise AppException("Bản sao lưu chưa hoàn tất.", code="BACKUP_INCOMPLETE", status_code=409)
    if operation == "drill" and not settings.BACKUP_DRILL_ENABLED:
        raise AppException(
            "Khôi phục thử chưa bật. Cần máy có Docker và BACKUP_DRILL_ENABLED=true.",
            code="BACKUP_DRILL_DISABLED",
            status_code=409,
        )
    if operation == "copy" and not record.verified_at:
        raise AppException(
            "Kiểm tra toàn vẹn trước khi chuyển S3.", code="BACKUP_UNVERIFIED", status_code=409
        )
    record.operation, record.status, record.progress = operation, "queued", 0
    record.actor_id, record.correlation_id, record.error = actor_id, correlation_id, None
    return await launch(record, password)


async def download(backup_id: str):
    record = await asyncio.to_thread(load_record, backup_id)
    path = record_path(backup_id, ".qnubak")
    if not record.sha256 or not path.is_file():
        raise AppException("Bản sao lưu chưa hoàn tất.", code="BACKUP_INCOMPLETE", status_code=409)
    return path
