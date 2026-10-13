"""Bounded raw upload; uploaded bytes are never trusted or extracted until verification."""

import asyncio
import os
import shutil
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.backups.catalogue import (
    backup_root,
    list_records,
    record_path,
    save_record,
    sha256_file,
)
from app.modules.backups.encryption import HEADER_SIZE, MAGIC
from app.modules.backups.locks import catalogue_lock
from app.modules.backups.models import BackupOperation, BackupRecord
from app.modules.backups.offload import finish_thread


async def import_archive(request: Request, actor_id: str, correlation_id: str) -> BackupRecord:
    async with catalogue_lock("reservation"), catalogue_lock("operation"):
        if any(r.status in ("queued", "running") for r in await asyncio.to_thread(list_records)):
            raise AppException(
                "Một thao tác sao lưu đang chạy.", code="BACKUP_BUSY", status_code=409
            )
        now = datetime.now(UTC)
        record = BackupRecord(
            id="bkp_" + uuid4().hex,
            created_at=now,
            updated_at=now,
            actor_id=actor_id,
            correlation_id=correlation_id,
            origin="import",
            pinned=True,
            operation="import",
            status="running",
            stage="Nhập file mã hóa",
            stage_started_at=now,
        )
        await asyncio.to_thread(save_record, record)
        partial = record_path(record.id, ".qnubak.partial")

        async def heartbeat():
            while True:
                await asyncio.sleep(5)
                await finish_thread(save_record, record)

        pulse = asyncio.create_task(heartbeat())
        try:
            await receive_bytes(request, partial, record)
            await finish_thread(os.replace, partial, record_path(record.id, ".qnubak"))
            record.sha256 = await asyncio.to_thread(sha256_file, record_path(record.id, ".qnubak"))
            record.size_bytes = record.processed_bytes
            record.status, record.stage, record.progress = (
                "unverified",
                "Đã nhập; cần kiểm tra bằng mật khẩu",
                100,
            )
        except BaseException:
            await asyncio.to_thread(partial.unlink, missing_ok=True)
            record.status, record.stage = "failed", "Nhập file thất bại"
            record.error = (
                "File không hợp lệ, thiếu dung lượng hoặc tải bị gián đoạn; chưa khôi phục dữ liệu."
            )
            raise
        finally:
            pulse.cancel()
            await asyncio.gather(pulse, return_exceptions=True)
            record.history.append(
                BackupOperation(
                    timestamp=datetime.now(UTC),
                    operation="import",
                    status=record.status,
                    actor_id=actor_id,
                    correlation_id=correlation_id,
                    error=record.error,
                )
            )
            await asyncio.to_thread(save_record, record)
        return record


async def receive_bytes(request: Request, path, record) -> None:
    root = backup_root()
    declared = request.headers.get("content-length")
    if declared and (not declared.isdecimal() or int(declared) > settings.BACKUP_IMPORT_MAX_BYTES):
        raise AppException(
            "File vượt giới hạn nhập backup.", code="BACKUP_IMPORT_TOO_LARGE", status_code=413
        )
    record.total_bytes = int(declared or 0)
    header = bytearray()
    stream = await asyncio.to_thread(path.open, "xb")
    reported_at = time.monotonic()
    try:
        async for block in request.stream():
            record.processed_bytes += len(block)
            if record.processed_bytes > settings.BACKUP_IMPORT_MAX_BYTES:
                raise AppException(
                    "File vượt giới hạn nhập backup.",
                    code="BACKUP_IMPORT_TOO_LARGE",
                    status_code=413,
                )
            free = await asyncio.to_thread(shutil.disk_usage, root)
            if free.free < len(block) + settings.BACKUP_MIN_FREE_BYTES:
                raise AppException("Không đủ dung lượng nhập file.", code="BACKUP_DISK_FULL")
            header.extend(block[: max(0, HEADER_SIZE - len(header))])
            await finish_thread(stream.write, block)
            if time.monotonic() - reported_at >= 1:
                await finish_thread(save_record, record)
                reported_at = time.monotonic()
    finally:
        await asyncio.to_thread(stream.close)
    if (
        len(header) != HEADER_SIZE
        or not header.startswith(MAGIC)
        or record.processed_bytes <= HEADER_SIZE + 20
    ):
        raise AppException(
            "Không phải file backup mã hóa được hỗ trợ.", code="BACKUP_IMPORT_INVALID"
        )
    if declared and record.processed_bytes != int(declared):
        raise AppException("File tải lên chưa đủ.", code="BACKUP_IMPORT_INCOMPLETE")
