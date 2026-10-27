"""Symmetric encryption for provider credentials."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from qnu.platform.config import get_settings
from qnu.platform.errors import AppException


def _fernet() -> Fernet:
    settings = get_settings()
    if not settings.PROVIDER_ENCRYPTION_KEY:
        raise AppException(
            "Chưa cấu hình PROVIDER_ENCRYPTION_KEY cho backendV1.",
            code="ENCRYPTION_KEY_MISSING",
            status_code=503,
        )
    digest = hashlib.sha256(settings.PROVIDER_ENCRYPTION_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return "enc:v1:" + _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: str) -> str:
    if not value.startswith("enc:v1:"):
        raise AppException("Giá trị không đúng định dạng mã hóa.", code="DECRYPT_FORMAT_INVALID", status_code=400)
    try:
        return _fernet().decrypt(value[len("enc:v1:"):].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise AppException("Không giải mã được credential.", code="DECRYPT_FAILED", status_code=400) from exc
