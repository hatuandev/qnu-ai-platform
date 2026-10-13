"""Atomic filesystem catalogue; no secret or raw process stderr is persisted here."""

import hashlib
import json
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.backups.models import BackupRecord

ID_PATTERN = re.compile(r"bkp_[a-f0-9]{32}\Z")


def backup_root() -> Path:
    root = Path(settings.BACKUP_DIRECTORY).resolve()
    storage = Path(settings.LOCAL_STORAGE_PATH).resolve()
    source_directories = [(storage / prefix).resolve() for prefix in settings.BACKUP_LOCAL_PREFIXES]
    if (
        root == Path(root.anchor)
        or root == Path.cwd().resolve()
        or root == storage
        or any(root.is_relative_to(source) for source in source_directories)
    ):
        raise AppException(
            "Thư mục sao lưu không được là thư mục gốc/workspace hoặc nằm trong thư mục dữ liệu cần sao lưu.",
            code="BACKUP_PATH_INVALID",
        )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def record_path(backup_id: str, suffix: str = ".json") -> Path:
    if not ID_PATTERN.fullmatch(backup_id):
        raise AppException("Mã sao lưu không hợp lệ.", code="BACKUP_NOT_FOUND", status_code=404)
    path = backup_root() / (backup_id + suffix)
    if path.is_symlink():
        raise AppException("Đường dẫn sao lưu không an toàn.", code="BACKUP_PATH_INVALID")
    return path


def save_record(record: BackupRecord) -> None:
    record.updated_at = datetime.now(UTC)
    destination = record_path(record.id)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, prefix=".catalogue-", delete=False
    ) as stream:
        stream.write(record.model_dump_json(indent=2))
        temporary = Path(stream.name)
    try:
        atomic_replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def load_record(backup_id: str) -> BackupRecord:
    path = record_path(backup_id)
    if not path.is_file():
        raise AppException("Không tìm thấy bản sao lưu.", code="BACKUP_NOT_FOUND", status_code=404)
    return BackupRecord.model_validate_json(path.read_text(encoding="utf-8"))


def atomic_replace(source: Path, destination: Path) -> None:
    # Windows readers may briefly deny FILE_SHARE_DELETE; POSIX replace is unaffected.
    for attempt in range(11):
        try:
            os.replace(source, destination)
            return
        except PermissionError as exc:
            if (
                os.name != "nt"
                or getattr(exc, "winerror", None) not in (5, 32, 33)
                or attempt == 10
            ):
                raise
            time.sleep(0.05)


def list_records() -> list[BackupRecord]:
    items = [load_record(path.stem) for path in backup_root().glob("bkp_*.json")]
    return sorted(items, key=lambda item: item.created_at, reverse=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
