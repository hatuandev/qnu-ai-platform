"""Actor resolution for HTTP requests."""

from __future__ import annotations

import jwt
from fastapi import Request

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.dev_gate import decode_dev_token, dev_gate_enabled
from qnu.domains.identity.sso import validate_sso_token
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if header and header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


async def resolve_actor(request: Request) -> AuthActor:
    """Resolve the caller, failing closed when no valid path exists."""
    settings = get_settings()
    token = _bearer_token(request)

    if token:
        try:
            algorithm = jwt.get_unverified_header(token).get("alg")
        except jwt.PyJWTError as exc:
            raise AppException(
                "Token không hợp lệ.", code="invalid_token", status_code=401
            ) from exc
        if algorithm == "HS256" and dev_gate_enabled():
            return decode_dev_token(token)
        if settings.SSO_ENABLED:
            return await validate_sso_token(token)

    raise AppException(
        "Chưa đăng nhập. Vui lòng xác thực qua QNU Single Sign-On.",
        code="unauthorized",
        status_code=401,
    )
