"""Recoverable removal and calendar-bucket retention; never deletes the last good archive."""

import asyncio
import os
from datetime import UTC, datetime

from app.core.exceptions import AppException
from app.modules.backups.catalogue import (
    backup_root,
    json_bytes,
    list_records,
    load_record,
    record_path,
    save_record,
)
from app.modules.backups.locks import catalogue_lock
from app.modules.backups.models import BackupRecord
from app.modules.backups.offload import finish_thread
from app.modules.backups.policy import BackupPolicy


def retention_candidates(
    records: list[BackupRecord], policy: BackupPolicy, now: datetime
) -> list[str]:
    if not policy.retention_enabled:
        return []
    valid = sorted(
        (
            r
            for r in records
            if r.verified_at and r.sha256 and r.status not in ("queued", "running")
        ),
        key=lambda r: r.created_at,
        reverse=True,
    )
    protected = {r.id for r in records if r.pinned}
    if valid:
        protected.add(valid[0].id)
    drilled = next((r for r in valid if r.drill_at), None)
    if drilled:
        protected.add(drilled.id)
    for count, key in (
        (policy.keep_daily, lambda d: d.date()),
        (policy.keep_weekly, lambda d: d.isocalendar()[:2]),
        (policy.keep_monthly, lambda d: (d.year, d.month)),
    ):
        groups = {}
        for r in valid:
            groups.setdefault(key(r.created_at), r.id)
        protected.update(list(groups.values())[:count])
    return [
        r.id
        for r in valid
        if r.id not in protected
        and (
            not policy.remote_enabled
            or (r.remote_status == "verified" and r.remote_sha256 == r.sha256)
        )
    ]


def move_to_trash(backup_id: str, actor_id: str, correlation_id: str) -> dict:
    records = list_records()
    if any(r.status in ("queued", "running") for r in records):
        raise AppException("Một thao tác sao lưu đang chạy.", code="BACKUP_BUSY", status_code=409)
    record = load_record(backup_id)
    good = [
        r for r in records if r.sha256 and r.verified_at and record_path(r.id, ".qnubak").is_file()
    ]
    if record.pinned:
        raise AppException(
            "Bỏ ghim trước khi xóa bản sao lưu.", code="BACKUP_PINNED", status_code=409
        )
    if record.verified_at and record.sha256 and len(good) <= 1:
        raise AppException(
            "Không xóa bản sao lưu tốt cuối cùng.", code="BACKUP_LAST_GOOD", status_code=409
        )
    root = backup_root()
    trash = root / ".trash"
    if trash.is_symlink():
        raise AppException("Thư mục phục hồi không an toàn.", code="BACKUP_PATH_INVALID")
    destination = trash / backup_id
    destination.mkdir(parents=True, mode=0o700)
    moved = []
    try:
        for suffix, name in (
            (".qnubak", "archive.qnubak"),
            (".qnubak.partial", "archive.partial"),
            (".json", "record.json"),
        ):
            source = record_path(backup_id, suffix)
            if source.exists():
                target = destination / name
                os.replace(source, target)
                moved.append((target, source))
        with (destination / "deletion.json").open("xb") as stream:
            stream.write(
                json_bytes(
                    {
                        "backup_id": backup_id,
                        "actor_id": actor_id,
                        "correlation_id": correlation_id,
                        "removed_at": datetime.now(UTC),
                        "recoverable": True,
                    }
                )
            )
    except BaseException:
        for target, source in reversed(moved):
            os.replace(target, source)
        raise
    return {"backup_id": backup_id, "recoverable": True}


async def remove_backup(backup_id: str, actor_id: str, correlation_id: str) -> dict:
    async with catalogue_lock("reservation"), catalogue_lock("operation"):
        return await finish_thread(move_to_trash, backup_id, actor_id, correlation_id)


async def pin_backup(backup_id: str, pinned: bool) -> BackupRecord:
    async with catalogue_lock("reservation"), catalogue_lock("operation"):
        if any(r.status in ("queued", "running") for r in await asyncio.to_thread(list_records)):
            raise AppException(
                "Một thao tác sao lưu đang chạy.", code="BACKUP_BUSY", status_code=409
            )
        record = await asyncio.to_thread(load_record, backup_id)
        record.pinned = pinned
        await asyncio.to_thread(save_record, record)
        return record


async def apply_retention(policy: BackupPolicy) -> int:
    async with catalogue_lock("reservation"), catalogue_lock("operation"):
        records = await asyncio.to_thread(list_records)
        candidates = retention_candidates(records, policy, datetime.now(UTC))
        for backup_id in candidates:
            await finish_thread(move_to_trash, backup_id, "backup-retention", "retention")
        return len(candidates)
