"""ARQ only ticks the schedule; the backup runner never holds the worker shared barrier."""

import asyncio
from datetime import UTC, datetime, timedelta, timezone

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.backups.coordination import database_connection
from app.modules.backups.locks import catalogue_lock
from app.modules.backups.policy import BackupPolicy, external_secret, load_policy, save_policy


def next_occurrence(policy: BackupPolicy, now: datetime) -> datetime:
    local = now.astimezone(timezone(timedelta(minutes=policy.utc_offset_minutes)))
    candidate = local.replace(hour=policy.hour, minute=policy.minute, second=0, microsecond=0)
    if policy.frequency == "weekly":
        candidate += timedelta(days=(policy.weekday - candidate.weekday()) % 7)
    if candidate <= local:
        candidate += timedelta(days=7 if policy.frequency == "weekly" else 1)
    return candidate.astimezone(UTC)


def read_schedule_password() -> str:
    password = external_secret(settings.BACKUP_SCHEDULE_SECRET_FILE).rstrip("\r\n")
    if not 12 <= len(password.strip()) <= 256 or "\n" in password or "\r" in password:
        raise AppException(
            "Bí mật lịch sao lưu cần 12–256 ký tự, một dòng.", code="BACKUP_SECRET_INVALID"
        )
    return password


async def configure_policy(policy: BackupPolicy) -> BackupPolicy:
    async with catalogue_lock("reservation"):
        if policy.schedule_enabled:
            await asyncio.to_thread(read_schedule_password)
            policy.next_run_at = next_occurrence(policy, datetime.now(UTC))
        else:
            policy.next_run_at = None
        if policy.remote_enabled:
            from app.modules.backups.policy import remote_credentials

            await asyncio.to_thread(remote_credentials)
        current = await asyncio.to_thread(load_policy)
        policy.last_backup_id, policy.notice = current.last_backup_id, None
        await asyncio.to_thread(save_policy, policy)
        return policy


async def task_backup_schedule(ctx=None) -> dict:
    from app.modules.backups.service import _start_backup_unlocked

    try:
        async with catalogue_lock("reservation"):
            policy = await asyncio.to_thread(load_policy)
            now = datetime.now(UTC)
            if not policy.schedule_enabled or not policy.next_run_at or policy.next_run_at > now:
                return {"scheduled": False}
            async with database_connection() as conn:
                pending = await conn.fetchval(
                    "SELECT count(*) FROM job_records WHERE status IN ('queued','running') OR (status='failed' AND result->>'retryable'='true')"
                )
                running = await conn.fetchval(
                    "SELECT count(*) FROM workflow_executions WHERE status='running'"
                )
            if pending or running:
                policy.notice = (
                    "Đã hoãn lịch: còn job/workflow chờ hoặc đang chạy. Không tự hủy tác vụ."
                )
                await asyncio.to_thread(save_policy, policy)
                return {"deferred": True}
            password = await asyncio.to_thread(read_schedule_password)
            record = await _start_backup_unlocked(
                password, "backup-schedule", "scheduled-backup", origin="schedule"
            )
            policy.last_backup_id, policy.next_run_at = record.id, next_occurrence(policy, now)
            policy.notice = "Đã gửi tác vụ theo lịch; theo dõi kết quả trong lịch sử."
            await asyncio.to_thread(save_policy, policy)
            return {"backup_id": record.id}
    except Exception as exc:
        # No credentials, connection strings or secrets in scheduler logs/notices.
        if isinstance(exc, AppException) and exc.code == "BACKUP_BUSY":
            return {"deferred": True}
        async with catalogue_lock("reservation"):
            policy = await asyncio.to_thread(load_policy)
            policy.notice = "Lịch chưa chạy được: " + (
                exc.code if isinstance(exc, AppException) else type(exc).__name__
            )
            await asyncio.to_thread(save_policy, policy)
        return {"failed": True}
