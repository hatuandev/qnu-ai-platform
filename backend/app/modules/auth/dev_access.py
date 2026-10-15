"""Explicit password gate for demo servers, isolated from local anonymous shortcuts."""

from __future__ import annotations

import hashlib
import hmac
from asyncio import timeout
from datetime import UTC, datetime, timedelta

import jwt
import structlog
from fastapi import Request
from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.redis import get_redis_client
from app.modules.auth.schemas import AuthActor

logger = structlog.get_logger(__name__)

# Atomic, bounded fixed windows shared by every API worker. No password/IP in Redis keys.
_LOGIN_WINDOW = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""


def is_production(settings: Settings) -> bool:
    return settings.ENVIRONMENT.lower() in ("production", "prod")


def dev_gate_allowed(settings: Settings) -> bool:
    return settings.DEV_AUTH_ENABLED and (
        not is_production(settings) or settings.DEV_AUTH_ALLOW_IN_PRODUCTION is True
    )


def validate_browser_origin(request: Request, settings: Settings) -> None:
    """Cookie-authenticated mutations and login must come from an approved browser origin."""
    if (
        is_production(settings)
        and request.method not in ("GET", "HEAD", "OPTIONS")
        and request.headers.get("origin") not in settings.ALLOWED_ORIGINS
    ):
        raise AppException(
            "Nguồn yêu cầu đăng nhập không được phép.",
            code="auth_origin_forbidden",
            status_code=403,
        )


async def enforce_login_rate_limit(request: Request, settings: Settings) -> None:
    """Fail closed if the shared production throttle cannot be reached."""
    if not is_production(settings):
        return
    peer = request.client.host if request.client else "unknown"
    namespace = hashlib.sha256(settings.SECRET_KEY.encode()).hexdigest()[:24]
    peer_hash = hashlib.sha256(peer.encode()).hexdigest()
    client = get_redis_client()
    try:
        async with timeout(3), client:
            for suffix, limit in ((peer_hash, 10), ("all", 100)):
                count = await client.eval(_LOGIN_WINDOW, 1, f"auth:dev:{namespace}:{suffix}", 300)
                if int(count) > limit:
                    raise AppException(
                        "Quá nhiều lần đăng nhập. Vui lòng thử lại sau 5 phút.",
                        code="auth_rate_limited",
                        status_code=429,
                    )
    except (RedisError, OSError, TimeoutError) as exc:
        logger.warning("dev_login_throttle_unavailable", error_type=type(exc).__name__)
        raise AppException(
            "Chưa thể kiểm tra giới hạn đăng nhập. Vui lòng thử lại sau.",
            code="auth_throttle_unavailable",
            status_code=503,
        ) from exc


def password_session_version(settings: Settings) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(), settings.DEV_ACCESS_PASSWORD.strip().encode(), hashlib.sha256
    ).hexdigest()


def production_session_token(settings: Settings, actor: AuthActor) -> tuple[str, int]:
    """Dedicated token purpose/issuer/audience; other app JWTs cannot grant admin."""
    lifetime = min(settings.ACCESS_TOKEN_EXPIRE_MINUTES, 60)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": actor.username,
            "iss": settings.SERVICE_NAME,
            "aud": "qnu-dev-access",
            "iat": now,
            "exp": now + timedelta(minutes=lifetime),
            "token_use": "dev_access",
            "session_version": password_session_version(settings),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return token, lifetime


def decode_production_actor(token: str, settings: Settings) -> AuthActor:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            issuer=settings.SERVICE_NAME,
            audience="qnu-dev-access",
            options={
                "require": ["exp", "sub", "iat", "iss", "aud", "token_use", "session_version"]
            },
        )
        if (
            payload["token_use"] != "dev_access"
            or payload["sub"] != "admin"
            or not isinstance(payload["session_version"], str)
            or not hmac.compare_digest(
                payload["session_version"], password_session_version(settings)
            )
        ):
            raise ValueError("Invalid password session scope")
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise AppException(
            "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.", code="invalid_token", status_code=401
        ) from exc
    return AuthActor(
        username="admin",
        role="AI.Admin",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
        session_version=payload["session_version"],
    )
