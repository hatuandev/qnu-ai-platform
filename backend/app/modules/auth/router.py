"""FastAPI router for Dev Access Gate authentication."""

from __future__ import annotations

import hmac
from datetime import timedelta

from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import create_access_token, decode_access_token
from app.modules.auth.schemas import AuthActor, AuthStatusResponse, DevLoginRequest
from app.modules.auth.sso_validator import validate_sso_token

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication & Access Gate"])


@router.post("/login", response_model=AuthStatusResponse, summary="Đăng nhập Dev Access Gate bằng mật khẩu môi trường")
async def login(req: DevLoginRequest, response: Response) -> AuthStatusResponse:
    """Verify dev access key and issue a secure HttpOnly session cookie."""
    current_settings = get_settings()
    is_prod = current_settings.ENVIRONMENT.lower() in ("production", "prod")
    if not current_settings.DEV_AUTH_ENABLED or is_prod:
        raise AppException(
            "Dev Access Gate bị vô hiệu hóa trong môi trường này.",
            code="dev_auth_disabled",
            status_code=403,
        )

    expected_password = current_settings.DEV_ACCESS_PASSWORD
    if not expected_password or not expected_password.strip():
        raise AppException(
            "Dev Access Gate chưa được cấu hình trên máy chủ.",
            code="auth_not_configured",
            status_code=503,
        )
    if not hmac.compare_digest(req.access_key.strip(), expected_password.strip()):
        raise AppException(
            "Mật khẩu truy cập Dev không chính xác.",
            code="invalid_credentials",
            status_code=401,
        )

    actor = AuthActor(
        actor_id="act_admin_qnu",
        username="admin",
        display_name="Cán bộ Quản trị QNU",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        role="AI.Admin",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
        authenticated=True,
        session_version="v1",
    )
    token = create_access_token(
        subject=actor.username,
        claims={
            "actor_id": actor.actor_id,
            "display_name": actor.display_name,
            "tenant_id": actor.tenant_id,
            "workspace_id": actor.workspace_id,
            "role": actor.role,
            "session_version": actor.session_version,
        },
        expires_delta=timedelta(minutes=current_settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response.set_cookie(
        key="qnu_session",
        value=token,
        max_age=current_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=is_prod,
    )
    return AuthStatusResponse(
        authenticated=True,
        actor=actor,
        message="Đăng nhập Dev Access Gate thành công.",
    )


@router.post("/logout", summary="Đăng xuất Dev Access Gate")
async def logout(response: Response) -> dict[str, str]:
    """Clear session cookie."""
    response.delete_cookie(key="qnu_session")
    return {"status": "logged_out", "message": "Đã kết thúc phiên làm việc."}


@router.get("/me", response_model=AuthStatusResponse, summary="Kiểm tra trạng thái phiên làm việc hiện tại")
async def get_current_user(request: Request) -> AuthStatusResponse:
    """Check current authentication status from QNU SSO Bearer token or Dev session cookie."""
    current_settings = get_settings()
    is_prod = current_settings.ENVIRONMENT.lower() in ("production", "prod")
    dev_gate_allowed = (not is_prod) and current_settings.DEV_AUTH_ENABLED

    token: str | None = None

    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if not token and dev_gate_allowed:
        token = request.cookies.get("qnu_session")

    if token:
        # Check if local dev token (HS256)
        is_local_dev = False
        if dev_gate_allowed:
            try:
                import jwt

                header = jwt.get_unverified_header(token)
                if header.get("alg") == current_settings.JWT_ALGORITHM:
                    is_local_dev = True
            except Exception:
                pass

        if is_local_dev:
            try:
                payload = decode_access_token(token)
                actor = AuthActor(
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
                return AuthStatusResponse(authenticated=True, actor=actor)
            except Exception:
                return AuthStatusResponse(authenticated=False, actor=None, message="Phiên làm việc không hợp lệ")

        # Validate SSO token
        try:
            sso_actor = await validate_sso_token(token)
            return AuthStatusResponse(authenticated=True, actor=sso_actor)
        except Exception:
            return AuthStatusResponse(authenticated=False, actor=None, message="Phiên làm việc không hợp lệ")

    return AuthStatusResponse(authenticated=False, actor=None, message="Chưa đăng nhập")
