"""Authentication dependencies for securing API endpoints via QNU SSO & Dev Access Gate."""

from __future__ import annotations

from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.modules.auth.schemas import AuthActor
from app.modules.auth.sso_validator import validate_sso_token

settings = get_settings()


async def get_current_actor(request: Request) -> AuthActor:
    """Extract authenticated actor from Authorization header (Bearer QNU SSO) or HttpOnly session cookie."""
    current_settings = get_settings()

    token: str | None = None

    # 1. Check Authorization Bearer header (Chuẩn OIDC từ QNU SSO)
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    # 2. Check HttpOnly cookie (Dev Access Gate session)
    if not token:
        token = request.cookies.get("qnu_session")

    if token:
        # Step A: Thử xác thực qua QNU SSO (OIDC OpenIddict)
        sso_actor = await validate_sso_token(token)
        if sso_actor:
            return sso_actor

        # Step B: Fallback xác thực qua Dev Access Gate local JWT
        try:
            payload = decode_access_token(token)
            return AuthActor(
                actor_id=str(payload.get("actor_id", "act_admin_qnu")),
                username=str(payload.get("sub", "admin")),
                display_name=str(payload.get("display_name", "Cán bộ Quản trị QNU")),
                email=str(payload.get("email", "admin@qnu.edu.vn")),
                user_type=str(payload.get("user_type", "admin")),
                tenant_id=str(payload.get("tenant_id", "tenant_qnu")),
                workspace_id=str(payload.get("workspace_id", "workspace_qnu")),
                role=str(payload.get("role", "admin")),
                roles=["admin"],
                permissions=["*"],
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

    # In development or test mode without explicit auth enforcement, provide default dev admin actor
    if not current_settings.DEV_AUTH_ENABLED or (
        current_settings.ENVIRONMENT in ("development", "test") and not enforce_auth
    ):
        return AuthActor(
            actor_id="act_admin_qnu",
            username="admin",
            display_name="Cán bộ Quản trị QNU",
            email="admin@qnu.edu.vn",
            user_type="admin",
            tenant_id="tenant_qnu",
            workspace_id="workspace_qnu",
            role="admin",
            roles=["admin"],
            permissions=["*"],
            authenticated=True,
            session_version="v1",
        )

    raise AppException(
        "Chưa đăng nhập hoặc phiên làm việc đã hết hạn. Vui lòng đăng nhập qua QNU Single Sign-On.",
        code="unauthorized",
        status_code=401,
    )


def require_permission(permission: str):
    """Dependency factory checking whether current actor holds specified permission."""

    async def _permission_dependency(
        actor: AuthActor = Depends(get_current_actor),
    ) -> AuthActor:
        if not actor.has_permission(permission):
            raise AppException(
                f"Tài khoản '{actor.username}' không có quyền '{permission}' để thực hiện hành động này.",
                code="forbidden",
                status_code=403,
            )
        return actor

    return _permission_dependency
