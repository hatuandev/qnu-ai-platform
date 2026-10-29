"""Development access gate (disabled in production)."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta

import jwt

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.dev_accounts import resolve_seed_actor
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException

ALGORITHM = "HS256"
DEV_ADMIN_ACTOR_ID = "act_dev_admin"


def dev_admin_actor() -> AuthActor:
    return AuthActor(
        username="dev.admin",
        actor_id=DEV_ADMIN_ACTOR_ID,
        display_name="Quản trị dev",
        email="dev@qnu.edu.vn",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
    )


def dev_gate_enabled() -> bool:
    settings = get_settings()
    return bool(settings.DEV_AUTH_ENABLED and not settings.is_production)


def issue_dev_token(access_key: str) -> tuple[str, AuthActor]:
    settings = get_settings()
    if not dev_gate_enabled():
        raise AppException("Dev access gate đang tắt.", code="dev_gate_disabled", status_code=403)
    if len(settings.SECRET_KEY.encode()) < 32:
        raise AppException(
            "Cần cấu hình SECRET_KEY ít nhất 32 byte.", code="SIGNING_KEY_MISSING", status_code=503
        )
    is_admin_key = bool(settings.DEV_ACCESS_PASSWORD) and hmac.compare_digest(
        access_key.encode(), settings.DEV_ACCESS_PASSWORD.encode()
    )
    actor = None if is_admin_key else resolve_seed_actor(access_key)
    if not is_admin_key and actor is None:
        raise AppException(
            "Mật khẩu truy cập dev không đúng.", code="invalid_credentials", status_code=401
        )

    actor = actor or dev_admin_actor()
    now = datetime.now(UTC)
    payload = {
        "sub": actor.username,
        "actor_id": actor.actor_id,
        "display_name": actor.display_name,
        "email": actor.email,
        "roles": actor.roles,
        "permissions": actor.permissions,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=8)).timestamp()),
        "aud": "qnu-dev-access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM), actor


def decode_dev_token(token: str) -> AuthActor:
    if not dev_gate_enabled():
        raise AppException("Token dev không được phép.", code="dev_gate_disabled", status_code=401)
    settings = get_settings()
    if len(settings.SECRET_KEY.encode()) < 32:
        raise AppException("Thiếu khóa xác thực.", code="SIGNING_KEY_MISSING", status_code=503)
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            audience="qnu-dev-access",
            options={"require": ["sub", "actor_id", "iat", "exp"]},
        )
        if not isinstance(payload["actor_id"], str) or not payload["actor_id"].strip():
            raise jwt.InvalidTokenError("Missing actor identity")
        for field in ("roles", "permissions"):
            if not isinstance(payload.get(field, []), list) or not all(
                isinstance(value, str) for value in payload.get(field, [])
            ):
                raise jwt.InvalidTokenError("Malformed privilege claims")
    except jwt.PyJWTError as exc:
        raise AppException(
            "Phiên dev không hợp lệ hoặc đã hết hạn.", code="invalid_token", status_code=401
        ) from exc
    return AuthActor(
        username=payload["sub"],
        actor_id=payload["actor_id"],
        display_name=payload.get("display_name", "Người dùng"),
        email=payload.get("email"),
        roles=list(payload.get("roles") or []),
        permissions=list(payload.get("permissions") or []),
    )
