"""Authentication dependencies for securing sensitive API endpoints."""

from __future__ import annotations

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.modules.auth.schemas import AuthActor

settings = get_settings()


async def get_current_actor(request: Request) -> AuthActor:
    """Extract authenticated actor from HttpOnly cookie or Authorization header."""
    current_settings = get_settings()

    token = request.cookies.get("qnu_session")
    if not token:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        try:
            payload = decode_access_token(token)
            return AuthActor(
                actor_id=str(payload.get("actor_id", "act_admin_qnu")),
                username=str(payload.get("sub", "admin")),
                display_name=str(payload.get("display_name", "Cán bộ Quản trị QNU")),
                tenant_id=str(payload.get("tenant_id", "tenant_qnu")),
                workspace_id=str(payload.get("workspace_id", "workspace_qnu")),
                role=str(payload.get("role", "admin")),
                authenticated=True,
                session_version=str(payload.get("session_version", "v1")),
            )
        except Exception:
            raise AppException(
                "Mã xác thực hoặc phiên làm việc không hợp lệ.",
                code="invalid_token",
                status_code=401,
            )

    enforce_auth = (
        request.headers.get("x-enforce-auth", "").lower() in ("true", "1")
        or request.headers.get("X-Enforce-Auth", "").lower() in ("true", "1")
    )

    # In test mode without explicit auth enforcement, provide default dev actor
    if not current_settings.DEV_AUTH_ENABLED or (
        current_settings.ENVIRONMENT == "test" and not enforce_auth
    ):
        return AuthActor(
            actor_id="act_admin_qnu",
            username="admin",
            display_name="Cán bộ Quản trị QNU",
            tenant_id="tenant_qnu",
            workspace_id="workspace_qnu",
            role="admin",
            authenticated=True,
            session_version="v1",
        )

    raise AppException(
        "Chưa đăng nhập hoặc phiên làm việc đã hết hạn. Vui lòng xác thực qua Dev Access Gate.",
        code="unauthorized",
        status_code=401,
    )


