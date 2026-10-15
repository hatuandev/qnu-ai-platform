"""FastAPI router for Dev Access Gate authentication."""

from __future__ import annotations

import hmac
from datetime import timedelta

from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import create_access_token
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.dev_access import (
    dev_gate_allowed,
    enforce_login_rate_limit,
    production_session_token,
    validate_browser_origin,
)
from app.modules.auth.schemas import AuthActor, AuthStatusResponse, DevLoginRequest

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication & Access Gate"])


@router.post("/login", response_model=AuthStatusResponse, summary="Đăng nhập Dev Access Gate bằng mật khẩu môi trường")
async def login(req: DevLoginRequest, response: Response, request: Request) -> AuthStatusResponse:
    """Verify dev access key and issue a secure HttpOnly session cookie."""
    current_settings = get_settings()
    is_prod = current_settings.ENVIRONMENT.lower() in ("production", "prod")
    if not dev_gate_allowed(current_settings):
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
    validate_browser_origin(request, current_settings)
    await enforce_login_rate_limit(request, current_settings)
    if not hmac.compare_digest(req.access_key.strip().encode("utf-8"), expected_password.strip().encode("utf-8")):
        raise AppException(
            "Mật khẩu truy cập Dev không chính xác.",
            code="invalid_credentials",
            status_code=401,
        )

    actor = AuthActor(
        actor_id="act_admin_qnu",
        username="admin",
        display_name="Cán bộ Quản trị QNU",
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
            "role": actor.role,
            "session_version": actor.session_version,
        },
        expires_delta=timedelta(minutes=current_settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    lifetime = current_settings.ACCESS_TOKEN_EXPIRE_MINUTES
    if is_prod:
        token, lifetime = production_session_token(current_settings, actor)
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key="qnu_session",
        value=token,
        max_age=lifetime * 60,
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
async def logout(response: Response, request: Request) -> dict[str, str]:
    """Clear session cookie."""
    current_settings = get_settings()
    validate_browser_origin(request, current_settings)
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(key="qnu_session", secure=current_settings.ENVIRONMENT.lower() in ("production", "prod"), httponly=True, samesite="lax")
    return {"status": "logged_out", "message": "Đã kết thúc phiên làm việc."}


@router.get("/me", response_model=AuthStatusResponse, summary="Kiểm tra trạng thái phiên làm việc hiện tại")
async def get_current_user(request: Request) -> AuthStatusResponse:
    """Check current authentication status from QNU SSO Bearer token or Dev session cookie."""
    current_settings = get_settings()
    is_dev_gate_allowed = dev_gate_allowed(current_settings)

    token: str | None = None

    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if not token and is_dev_gate_allowed:
        token = request.cookies.get("qnu_session")

    if token:
        try:
            actor = await get_current_actor(request)
            return AuthStatusResponse(authenticated=True, actor=actor)
        except AppException:
            return AuthStatusResponse(authenticated=False, actor=None, message="Phiên làm việc không hợp lệ")

    return AuthStatusResponse(authenticated=False, actor=None, message="Chưa đăng nhập")
