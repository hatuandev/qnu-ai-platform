"""Machine authentication, fresh authorization and fail-closed rate limits."""

import hashlib
import time
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.integration.models import AppApiKey, AppClient, utcnow
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.cache import get_redis, namespaced
from qnu.platform.errors import DependencyUnavailable, Forbidden


def openai_error(
    message: str,
    status_code: int = 400,
    code: str = "invalid_request_error",
    headers: dict[str, str] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        headers=headers,
        detail={
            "error": {
                "message": message,
                "type": "invalid_request_error" if status_code < 500 else "api_error",
                "param": None,
                "code": code,
            }
        },
    )


def get_redis_client() -> Redis:
    return get_redis()


async def check_access(
    db: AsyncSession, key_id: str, app_id: str, actor: AuthActor, workspace_id: str
) -> tuple[AppApiKey, AppClient]:
    # Sessions intentionally keep objects across commits; always reload authorization.
    result = (
        await db.execute(
            select(AppApiKey, AppClient)
            .join(AppClient, AppApiKey.app_id == AppClient.id)
            .where(
                AppApiKey.id == key_id,
                AppClient.id == app_id,
                AppApiKey.workspace_id == workspace_id,
                AppClient.workspace_id == workspace_id,
            )
            .execution_options(populate_existing=True)
        )
    ).first()
    if result is None:
        raise Forbidden("API key không còn hợp lệ.", code="invalid_api_key")
    key, app = result
    if key.status != "active" or app.status != "active":
        raise Forbidden("Khóa hoặc ứng dụng đã tạm dừng/thu hồi.", code="api_key_inactive")
    if key.expires_at and key.expires_at <= utcnow():
        raise openai_error("API key đã hết hạn.", 401, "api_key_expired")
    await resolve_workspace_access(db, actor, workspace_id)
    return key, app


async def enforce_limits(redis: Redis | None, key: AppApiKey) -> None:
    if redis is None:
        raise DependencyUnavailable(
            "Chưa thể kiểm tra hạn mức API.", code="rate_limiter_unavailable"
        )
    minute = int(time.time()) // 60
    day = datetime.now(UTC).strftime("%Y%m%d")
    rpm_key = namespaced(f"integrations:rpm:{key.id}:{minute}")
    rpd_key = namespaced(f"integrations:rpd:{key.id}:{day}")
    try:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(rpm_key)
            pipe.expire(rpm_key, 65)
            pipe.incr(rpd_key)
            pipe.expire(rpd_key, 86500)
            rpm, _, rpd, _ = await pipe.execute()
    except Exception as exc:
        raise DependencyUnavailable(
            "Chưa thể kiểm tra hạn mức API.", code="rate_limiter_unavailable"
        ) from exc
    if key.rate_limit_rpm and rpm > key.rate_limit_rpm:
        raise openai_error(
            "Vượt hạn mức yêu cầu mỗi phút.",
            429,
            "rate_limit_exceeded",
            {"Retry-After": str(60 - int(time.time()) % 60)},
        )
    if key.rate_limit_rpd and rpd > key.rate_limit_rpd:
        now = datetime.now(UTC)
        retry = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
        raise openai_error(
            "Vượt hạn mức yêu cầu mỗi ngày.",
            429,
            "daily_quota_exceeded",
            {"Retry-After": str(retry)},
        )


async def authenticate_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis | None = Depends(get_redis_client),
) -> tuple[AppApiKey, AppClient, AuthActor]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise openai_error("Cần Authorization: Bearer <key>.", 401, "unauthorized")
    token = authorization[7:].strip()
    if not token or len(token) > 256:
        raise openai_error("API key không hợp lệ.", 401, "invalid_api_key")
    key = await db.scalar(
        select(AppApiKey).where(AppApiKey.key_hash == hashlib.sha256(token.encode()).hexdigest())
    )
    if key is None:
        raise openai_error("API key không hợp lệ.", 401, "invalid_api_key")
    actor = AuthActor(
        username=f"app:{key.app_id}",
        actor_id=f"app:{key.app_id}",
        user_type="application",
        role="member",
        roles=["member"],
        permissions=[],
    )
    key, app = await check_access(db, key.id, key.app_id, actor, key.workspace_id)
    await db.commit()
    await enforce_limits(redis, key)
    return key, app, actor
