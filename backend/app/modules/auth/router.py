"""FastAPI router for Dev Access Gate authentication."""

from __future__ import annotations

import hmac
from datetime import timedelta

from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import create_access_token, decode_access_token
from app.modules.auth.schemas import AuthActor, AuthStatusResponse, DevLoginRequest

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication & Access Gate"])


@router.post("/login", response_model=AuthStatusResponse, summary="Đăng nhập Dev Access Gate bằng mật khẩu môi trường")
async def login(req: DevLoginRequest, response: Response) -> AuthStatusResponse:
    """Verify dev access key and issue a secure HttpOnly session cookie."""
    expected_password = settings.DEV_ACCESS_PASSWORD
    if not hmac.compare_digest(req.access_key.strip(), expected_password.strip()):
        raise AppException(
            "Mật khẩu truy cập Dev không chính xác.",
            code="invalid_credentials",
            status_code=401,
        )

    actor = AuthActor(
        username="admin",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        role="admin",
        authenticated=True,
    )
    token = create_access_token(
        subject=actor.username,
        claims={
            "tenant_id": actor.tenant_id,
            "workspace_id": actor.workspace_id,
            "role": actor.role,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response.set_cookie(
        key="qnu_session",
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT not in ("development", "test"),
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
    """Check current authentication status from session cookie or Authorization header."""
    token = request.cookies.get("qnu_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        try:
            payload = decode_access_token(token)
            actor = AuthActor(
                username=str(payload.get("sub", "admin")),
                tenant_id=str(payload.get("tenant_id", "tenant_qnu")),
                workspace_id=str(payload.get("workspace_id", "workspace_qnu")),
                role=str(payload.get("role", "admin")),
                authenticated=True,
            )
            return AuthStatusResponse(authenticated=True, actor=actor)
        except Exception:
            pass

    return AuthStatusResponse(authenticated=False, actor=None, message="Chưa đăng nhập")
