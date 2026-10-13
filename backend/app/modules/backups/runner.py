"""Independent process entrypoint; passwords enter through stdin, never argv/catalogue."""

import asyncio
import logging
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from cryptography.exceptions import InvalidTag

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.backups.archive import extract_verified, write_archive
from app.modules.backups.capture import capture_all
from app.modules.backups.catalogue import (
    backup_root,
    load_record,
    record_path,
    save_record,
    sha256_file,
)
from app.modules.backups.coordination import exclusive_access
from app.modules.backups.drill import run_drill
from app.modules.backups.errors import BackupIntegrityError
from app.modules.backups.locks import catalogue_lock
from app.modules.backups.models import BackupOperation
from app.modules.backups.offload import finish_thread
from app.modules.backups.policy import load_policy
from app.modules.backups.remote import transfer

logger = logging.getLogger(__name__)


def recovery_secrets() -> dict:
    # Key escrow stays INSIDE the encrypted archive; no plaintext .env copies.
    names = (
        "SECRET_KEY",
        "PROVIDER_ENCRYPTION_KEY",
        "OLD_PROVIDER_ENCRYPTION_KEYS",
        "INTERNAL_API_KEY",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "QDRANT_API_KEY",
    )
    return {name: getattr(settings, name) for name in names}


async def execute(record, password: str) -> None:
    def update(stage: str, progress: int):
        record.stage, record.progress = stage, progress
        record.stage_started_at = datetime.now(UTC)
        record.processed_bytes = record.total_bytes = 0
        save_record(record)

    async def heartbeat():
        while True:
            await asyncio.sleep(5)
            save_record(record)

    record.status, record.pid = "running", os.getpid()
    save_record(record)
    pulse = asyncio.create_task(heartbeat())
    try:
        root = backup_root()
        if shutil.disk_usage(root).free < settings.BACKUP_MIN_FREE_BYTES:
            raise AppException("Không đủ dung lượng trống cho sao lưu.", code="BACKUP_DISK_FULL")
        with tempfile.TemporaryDirectory(prefix=".backup-scratch-", dir=root) as temporary:
            scratch = Path(temporary)
            if record.operation == "create":
                update("Chờ API và worker về điểm an toàn", 5)
                async with exclusive_access() as conn:
                    files, manifest = await capture_all(conn, scratch, update)
                    manifest.update(
                        {
                            "backup_id": record.id,
                            "created_at": record.created_at.isoformat(),
                            "app_version": "0.1.0",
                            "release": os.environ.get("APP_IMAGE_TAG", "development"),
                            "requires": "Restore with matching application source/migrations; external AI/SSO services are not included",
                        }
                    )
                    update("Mã hóa bản sao lưu", 75)
                    output = record_path(record.id, ".qnubak.partial")
                    await finish_thread(
                        write_archive, output, password, files, manifest, recovery_secrets()
                    )
                    # Keep the barrier while reading source files and validating the final archive.
                    verify_dir = scratch / "verify"
                    verify_dir.mkdir(mode=0o700)
                    update("Giải mã kiểm tra bản vừa tạo", 88)
                    await finish_thread(
                        extract_verified, output, verify_dir, password, shutil.disk_usage(root).free
                    )
                    await conn.fetchval(
                        "SELECT 1"
                    )  # A lost maintenance connection invalidates the capture.
                    destination = record_path(record.id, ".qnubak")
                    await asyncio.to_thread(os.replace, output, destination)
                    record.sha256 = await asyncio.to_thread(sha256_file, destination)
                    record.size_bytes = destination.stat().st_size
                    record.components = {
                        "tables": len(manifest["database"]["tables"]),
                        "objects": len(manifest["s3"]["objects"]),
                        "local_files": sum(name.startswith("local/") for name in files),
                        "vector_collections": len(manifest["qdrant"]["collections"]),
                    }
                    record.verified_at = datetime.now(UTC)
            elif record.operation != "copy":
                update("Giải mã và kiểm tra toàn vẹn", 15)
                path = record_path(record.id, ".qnubak")
                if await asyncio.to_thread(sha256_file, path) != record.sha256:
                    raise BackupIntegrityError("Checksum bản sao lưu không khớp catalogue.")
                manifest = await finish_thread(
                    extract_verified, path, scratch, password, shutil.disk_usage(root).free
                )
                record.components["archive"] = {
                    "format": manifest.get("format"),
                    "release": manifest.get("release"),
                    "app_version": manifest.get("app_version"),
                    "schema": manifest.get("database", {}).get("schema"),
                    "note": "Toàn vẹn không chứng minh tương thích release hoặc chất lượng chatbot.",
                }
                record.verified_at = datetime.now(UTC)
                if record.operation == "drill":
                    record.components["drill"] = await run_drill(manifest, scratch, update)
                    record.drill_at = datetime.now(UTC)
        policy = await asyncio.to_thread(load_policy)
        if record.operation == "copy" or (record.operation == "create" and policy.remote_enabled):
            await transfer(record, policy)
        record.status, record.error = "completed", None
        final_stage = "Khôi phục thử đạt" if record.operation == "drill" else "Đã kiểm tra toàn vẹn"
        if record.remote_status == "failed":
            final_stage = "Bản local hoàn tất; chuyển S3 thất bại"
        update(final_stage, 100)
    finally:
        pulse.cancel()
        await asyncio.gather(pulse, return_exceptions=True)


async def main(backup_id: str, password: str):
    record = load_record(backup_id)
    try:
        async with catalogue_lock("operation"):
            await asyncio.wait_for(execute(record, password), settings.BACKUP_TIMEOUT_SECONDS)
    except Exception as exc:
        record.status = "failed"
        record.stage = "Thất bại ở bước: " + record.stage
        if isinstance(exc, AppException):
            record.error = exc.message
            record.error_code = exc.code
        elif isinstance(exc, InvalidTag):
            record.error = "Mật khẩu không đúng hoặc bản sao lưu bị thay đổi."
        elif isinstance(exc, TimeoutError):
            record.error = "Thao tác quá hạn; khóa bảo trì đã được giải phóng."
        elif isinstance(exc, BackupIntegrityError):
            record.error = str(exc)
        else:
            record.error = (
                f"Lỗi {type(exc).__name__}; kiểm tra quyền công cụ/kết nối/dung lượng máy chủ."
            )
        # Do not persist raw exception messages: drivers can include connection credentials.
        logger.error(
            "backup_failed id=%s operation=%s correlation_id=%s error_type=%s",
            record.id,
            record.operation,
            record.correlation_id,
            type(exc).__name__,
        )
        save_record(record)

    finally:
        if record.operation == "create" and record.status == "completed":
            from app.modules.backups.management import apply_retention

            try:
                policy = await asyncio.to_thread(load_policy)
                if policy.retention_enabled and (
                    not policy.remote_enabled or record.remote_status == "verified"
                ):
                    await apply_retention(policy)
            except Exception as exc:
                record.components["retention_notice"] = (
                    "Chưa dọn được bản cũ: " + type(exc).__name__
                )
        record.history.append(
            BackupOperation(
                timestamp=datetime.now(UTC),
                operation=record.operation,
                status=record.status,
                actor_id=record.actor_id,
                correlation_id=record.correlation_id,
                error=record.error,
            )
        )
        save_record(record)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    secret = sys.stdin.buffer.readline().decode("utf-8").rstrip("\r\n")
    asyncio.run(main(sys.argv[1], secret))
