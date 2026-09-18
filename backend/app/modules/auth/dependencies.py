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
    token = request.cookies.get("qnu_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        try:
            payload = decode_access_token(token)
            return AuthActor(
                username=str(payload.get("sub", "admin")),
                tenant_id=str(payload.get("tenant_id", "tenant_qnu")),
                workspace_id=str(payload.get("workspace_id", "workspace_qnu")),
                role=str(payload.get("role", "admin")),
                authenticated=True,
            )
        except Exception:
            pass

    # If dev auth is disabled or in testing mode without auth header, provide default dev actor
    if not settings.DEV_AUTH_ENABLED or settings.ENVIRONMENT == "test":
        return AuthActor(
            username="admin",
            tenant_id="tenant_qnu",
            workspace_id="workspace_qnu",
            role="admin",
            authenticated=True,
        )

    raise AppException(
        "Chưa đăng nhập hoặc phiên làm việc đã hết hạn. Vui lòng xác thực qua Dev Access Gate.",
        code="unauthorized",
        status_code=401,
    )
