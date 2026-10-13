"""Restore gates are checked before creating any target container."""

import os

from app.core.exceptions import AppException


def check_restore_compatibility(manifest: dict) -> None:
    database, vector = manifest.get("database", {}), manifest.get("qdrant", {})
    if (
        manifest.get("format") != "qnu-backup-v1"
        or not isinstance(database.get("major"), int)
        or not database.get("schema")
        or not isinstance(vector.get("collections"), list)
    ):
        raise AppException(
            "Manifest thiếu thông tin để khôi phục an toàn.", code="BACKUP_MANIFEST_INVALID"
        )
    expected = os.environ.get("APP_IMAGE_TAG", "development")
    actual = manifest.get("release")
    if expected != "development" and actual != expected:
        raise AppException(
            "Release backup khác release đang vận hành. Dùng source/image tương ứng để khôi phục thử offline.",
            code="BACKUP_RELEASE_MISMATCH",
        )
