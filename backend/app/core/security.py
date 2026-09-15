"""Security, Authentication & PII Data Protection Utilities."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


# ==============================================================================
# 1. Password & API Key Hashing (Native Bcrypt for Python 3.12 compatibility)
# ==============================================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using SHA-256 for secure database lookup."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


# ==============================================================================
# 2. JWT Authentication Tokens
# ==============================================================================
def create_access_token(
    subject: str,
    claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "iss": settings.SERVICE_NAME,
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid or expired token: {exc}") from exc


# ==============================================================================
# 3. PII Masking & Data Redaction (Bảo vệ Dữ liệu Nhạy cảm Sinh viên / Cán bộ)
# ==============================================================================
_PHONE_REGEX = re.compile(r"(?:\+?84|0)(?:3|5|7|8|9)\d{8}\b")
_CCCD_REGEX = re.compile(r"\b\d{12}\b|\b\d{9}\b")
_EMAIL_REGEX = re.compile(
    r"\b([A-Za-z0-9._%+-]{1,3})[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b"
)


def mask_phone(match: re.Match[str]) -> str:
    val = match.group(0)
    if len(val) >= 10:
        return val[:4] + "***" + val[-3:]
    return "***"


def mask_cccd(match: re.Match[str]) -> str:
    val = match.group(0)
    if len(val) >= 9:
        return val[:3] + "******" + val[-3:]
    return "******"


def mask_email(match: re.Match[str]) -> str:
    prefix = match.group(1)
    domain = match.group(2)
    return f"{prefix}***@{domain}"


def mask_pii(text: str) -> str:
    """Mask sensitive PII fields (phone numbers, citizen IDs, emails) before sending to LLMs."""
    if not text:
        return text
    masked = _PHONE_REGEX.sub(mask_phone, text)
    masked = _CCCD_REGEX.sub(mask_cccd, masked)
    masked = _EMAIL_REGEX.sub(mask_email, masked)
    return masked
