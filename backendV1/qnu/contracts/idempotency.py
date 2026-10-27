"""Idempotency key contract for write endpoints."""

from __future__ import annotations

from hashlib import sha256

from fastapi import Header

from qnu.platform.errors import AppException


async def idempotency_key(
    x_idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str | None:
    """Accept an optional client key; reject obviously unbounded values."""
    if x_idempotency_key is None:
        return None
    value = x_idempotency_key.strip()
    if not 8 <= len(value) <= 128:
        raise AppException(
            "Idempotency-Key phải dài 8-128 ký tự.",
            code="idempotency_key_invalid",
            status_code=400,
        )
    return value


def fingerprint(payload: str) -> str:
    return sha256(payload.encode("utf-8")).hexdigest()
