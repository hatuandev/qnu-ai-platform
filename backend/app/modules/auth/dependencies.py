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
    """Extract authenticated actor from Authorization header (Bearer QNU SSO) or HttpOnly session cookie.

    Enforces strict fail-closed security:
    - Production: Unauthenticated request always raises 401. Local dev JWT is rejected.
    - Development / Test: Default dev actor allowed ONLY when DEV_AUTH_ENABLED=True and not enforcing auth.
    """
    current_settings = get_settings()
    is_prod = current_settings.ENVIRONMENT.lower() in ("production", "prod")
    dev_gate_allowed = (not is_prod) and current_settings.DEV_AUTH_ENABLED

    token: str | None = None

    # 1. Check Authorization Bearer header
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    # 2. Check HttpOnly cookie (Dev Access Gate session) ONLY when Dev Gate is allowed
    if not token and dev_gate_allowed:
        token = request.cookies.get("qnu_session")

    if token:
        # Check if token is local dev JWT (HS256) vs SSO token (RS256)
        is_local_dev_token = False
        if dev_gate_allowed:
            try:
                import jwt

                unverified_header = jwt.get_unverified_header(token)
                if unverified_header.get("alg") == current_settings.JWT_ALGORITHM:
                    is_local_dev_token = True
            except Exception:
                pass

        if is_local_dev_token:
            # Decode local dev JWT
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
                    role="AI.Admin",
                    roles=["AI.Admin"],
                    permissions=["ai.access.admin"],
                    authenticated=True,
                    session_version=str(payload.get("session_version", "v1")),
                )
            except Exception:
                raise AppException(
                    "Mã xác thực phiên làm việc Dev không hợp lệ hoặc đã hết hạn.",
                    code="invalid_token",
                    status_code=401,
                )

        # Otherwise validate via QNU SSO (OpenIddict OIDC)
        # In production or when token is an SSO token, validate_sso_token enforces strict validation
        return await validate_sso_token(token)

    # If no token provided:
    # In production or when DEV_AUTH_ENABLED is False, fail-closed with 401
    if is_prod or not dev_gate_allowed:
        raise AppException(
            "Chưa đăng nhập hoặc phiên làm việc đã hết hạn. Vui lòng đăng nhập qua QNU Single Sign-On.",
            code="unauthorized",
            status_code=401,
        )

    # In development/test with DEV_AUTH_ENABLED=True:
    # Check if request specifically requests enforced auth
    enforce_auth = (
        request.headers.get("x-enforce-auth", "").lower() in ("true", "1")
        or request.headers.get("X-Enforce-Auth", "").lower() in ("true", "1")
    )
    if enforce_auth:
        raise AppException(
            "Yêu cầu xác thực tài khoản qua QNU Single Sign-On.",
            code="unauthorized",
            status_code=401,
        )

    # Return default dev admin actor for development/test convenience
    return AuthActor(
        actor_id="act_admin_qnu",
        username="admin",
        display_name="Cán bộ Quản trị QNU",
        email="admin@qnu.edu.vn",
        user_type="admin",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        role="AI.Admin",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
        authenticated=True,
        session_version="v1",
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
