"""Non-secret control plane outside the protected database; automation defaults off."""

import json
import os
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.paths import get_configs_dir
from app.modules.backups.catalogue import atomic_replace, backup_root


class BackupPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schedule_enabled: bool = False
    frequency: Literal["daily", "weekly"] = "daily"
    weekday: int = Field(default=6, ge=0, le=6)
    hour: int = Field(default=2, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    utc_offset_minutes: int = Field(default=420, ge=-720, le=840)
    next_run_at: datetime | None = None
    last_backup_id: str | None = None
    notice: str | None = None
    remote_enabled: bool = False
    endpoint: str = ""
    bucket: str = ""
    prefix: str = "qnu-backups"
    region: str = "us-east-1"
    retention_enabled: bool = False
    keep_daily: int = Field(default=7, ge=1, le=365)
    keep_weekly: int = Field(default=4, ge=1, le=104)
    keep_monthly: int = Field(default=12, ge=1, le=120)

    @model_validator(mode="after")
    def validate_destination(self):
        from app.modules.backups.archive import safe_name

        if self.endpoint:
            url = urlsplit(self.endpoint)
            if (
                url.scheme not in ("http", "https")
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
                or url.path not in ("", "/")
            ):
                raise ValueError("Endpoint S3 không hợp lệ hoặc chứa thông tin bí mật.")
        if self.prefix:
            safe_name(self.prefix)
        if self.remote_enabled and (not self.endpoint or not self.bucket):
            raise ValueError("Cần endpoint và bucket S3 riêng cho backup.")
        if self.bucket and (
            not 3 <= len(self.bucket) <= 63
            or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for c in self.bucket)
        ):
            raise ValueError("Tên bucket S3 không hợp lệ.")
        if (
            self.remote_enabled
            and self.bucket == settings.S3_BUCKET
            and self.endpoint.rstrip("/") == settings.S3_ENDPOINT.rstrip("/")
        ):
            raise ValueError("Không dùng cùng bucket dữ liệu nguồn để lưu backup.")
        return self


def load_policy() -> BackupPolicy:
    path = backup_root() / ".policy.json"
    if path.is_symlink():
        raise AppException("Cấu hình sao lưu không an toàn.", code="BACKUP_POLICY_INVALID")
    return (
        BackupPolicy.model_validate_json(path.read_text(encoding="utf-8"))
        if path.exists()
        else BackupPolicy()
    )


def save_policy(policy: BackupPolicy) -> None:
    root = backup_root()
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(policy.model_dump_json(indent=2))
    try:
        if (root / ".policy.json").is_symlink():
            raise AppException("Cấu hình sao lưu không an toàn.", code="BACKUP_POLICY_INVALID")
        atomic_replace(temporary, root / ".policy.json")
    finally:
        temporary.unlink(missing_ok=True)


def external_secret(path_value: str) -> str:
    """Read a provisioned secret, outside all captured prefixes/configs. Never echo it."""
    path = Path(path_value) if path_value else None
    if path is None or not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise AppException("Chưa cấp file bí mật bên ngoài hợp lệ.", code="BACKUP_SECRET_MISSING")
    resolved = path.resolve()
    protected = [
        backup_root(),
        Path(settings.LOCAL_STORAGE_PATH).resolve(),
        get_configs_dir().resolve(),
    ]
    if any(resolved.is_relative_to(root) for root in protected):
        raise AppException(
            "File bí mật phải nằm ngoài dữ liệu được sao lưu.", code="BACKUP_SECRET_UNSAFE"
        )
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 16384:
        raise AppException("File bí mật không hợp lệ.", code="BACKUP_SECRET_UNSAFE")
    if os.name != "nt" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise AppException(
            "File bí mật phải chỉ tài khoản chạy app được đọc.", code="BACKUP_SECRET_UNSAFE"
        )
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise AppException(
            "Không đọc được file bí mật.", code="BACKUP_SECRET_UNAVAILABLE"
        ) from None


def remote_credentials() -> dict:
    try:
        data = json.loads(external_secret(settings.BACKUP_REMOTE_CREDENTIALS_FILE))
        if not isinstance(data, dict) or not data.get("access_key") or not data.get("secret_key"):
            raise ValueError("Missing credentials")
        return {name: data.get(name) for name in ("access_key", "secret_key", "session_token")}
    except (ValueError, TypeError):
        raise AppException(
            "Nội dung bí mật S3 không hợp lệ.", code="BACKUP_SECRET_INVALID"
        ) from None
