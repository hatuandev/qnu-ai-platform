"""QNU Single Sign-On (OpenIddict / OIDC) Token Validator."""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
import structlog
from jwt.algorithms import RSAAlgorithm

from app.core.config import get_settings
from app.modules.auth.schemas import AuthActor

logger = structlog.get_logger(__name__)
settings = get_settings()

# In-memory cache for QNU SSO JWKS public keys
_JWKS_CACHE: dict[str, Any] = {"keys": {}, "expires_at": 0.0}
_CACHE_TTL_SECONDS = 3600.0  # 1 hour


async def _get_jwks_keys() -> dict[str, Any]:
    """Fetch and cache public JSON Web Key Sets (JWKS) from QNU SSO."""
    now = time.time()
    if _JWKS_CACHE["keys"] and now < _JWKS_CACHE["expires_at"]:
        return _JWKS_CACHE["keys"]

    jwks_url = settings.sso_jwks_url
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(jwks_url)
            if res.status_code == 200:
                data = res.json()
                keys = data.get("keys", [])
                key_dict = {k.get("kid"): k for k in keys if k.get("kid")}
                _JWKS_CACHE["keys"] = key_dict
                _JWKS_CACHE["expires_at"] = now + _CACHE_TTL_SECONDS
                logger.info("sso_jwks_cached", key_count=len(key_dict), url=jwks_url)
                return key_dict
    except Exception as exc:
        logger.warning("sso_jwks_fetch_failed", error=str(exc), url=jwks_url)

    return _JWKS_CACHE.get("keys", {})


def parse_sso_claims(claims: dict[str, Any]) -> AuthActor:
    """Parse raw OIDC claims / UserInfo payload into typed AuthActor."""
    sub = str(claims.get("sub") or claims.get("nameid") or "sso_user")
    email = claims.get("email")
    name = claims.get("name") or claims.get("preferred_username") or (email.split("@")[0] if email else "Cán bộ QNU")
    username = claims.get("preferred_username") or (email.split("@")[0] if email else sub)

    # Resolve roles
    raw_roles = claims.get("role") or claims.get("roles") or []
    if isinstance(raw_roles, str):
        roles = [r.strip() for r in raw_roles.split(",") if r.strip()]
    elif isinstance(raw_roles, list):
        roles = [str(r).strip() for r in raw_roles if str(r).strip()]
    else:
        roles = []

    # Resolve permissions
    raw_perms = claims.get("permission") or claims.get("permissions") or []
    if isinstance(raw_perms, str):
        permissions = [p.strip() for p in raw_perms.split(",") if p.strip()]
    elif isinstance(raw_perms, list):
        permissions = [str(p).strip() for p in raw_perms if str(p).strip()]
    else:
        permissions = []

    # Resolve user_type
    raw_user_type = str(claims.get("user_type") or claims.get("userType") or "").lower()
    if not raw_user_type:
        if any("admin" in r.lower() for r in roles):
            raw_user_type = "admin"
        elif any("lecturer" in r.lower() for r in roles):
            raw_user_type = "lecturer"
        elif any("student" in r.lower() for r in roles):
            raw_user_type = "student"
        else:
            raw_user_type = "staff"

    student_id = claims.get("student_id") or claims.get("studentId")

    # Mặc định quyền nếu SSO chưa cấu hình fine-grained permissions
    if not permissions:
        if raw_user_type in ("admin", "super_admin") or any("admin" in r.lower() for r in roles):
            permissions = ["*"]
        elif raw_user_type == "student":
            permissions = ["ai.access.read", "ai.chat.access", "ai.chat.export"]
        else:
            permissions = [
                "ai.access.read",
                "ai.chat.access",
                "ai.chat.export",
                "ai.assistants.view",
                "ai.knowledge.view",
            ]

    primary_role = "admin" if (raw_user_type == "admin" or any("admin" in r.lower() for r in roles)) else raw_user_type

    return AuthActor(
        actor_id=sub,
        username=username,
        display_name=str(name),
        email=str(email) if email else None,
        user_type=raw_user_type,
        student_id=str(student_id) if student_id else None,
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        role=primary_role,
        roles=roles if roles else [primary_role],
        permissions=permissions,
        session_version="sso_v1",
        authenticated=True,
    )


async def validate_sso_token(token: str) -> AuthActor | None:
    """Validate Bearer access token issued by QNU SSO (OpenIddict).

    Tries 2 mechanisms:
    1. Local JWKS signature verification using cached public keys.
    2. Fallback to /connect/userinfo endpoint if token is opaque or encrypted.
    """
    if not token or not settings.SSO_ENABLED:
        return None

    # Step 1: Thử giải mã JWT header để kiểm tra xem có phải JWT từ SSO không
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg", "RS256")

        # Nếu là thuật toán bất đối xứng (RS256) từ QNU SSO
        if alg.startswith(("RS", "ES")):
            jwks_keys = await _get_jwks_keys()
            if kid and kid in jwks_keys:
                public_key = RSAAlgorithm.from_jwk(jwks_keys[kid])
                claims = jwt.decode(
                    token,
                    public_key,
                    algorithms=[alg],
                    options={"verify_aud": False},  # Audience có thể là ai.api hoặc client_id
                )
                return parse_sso_claims(claims)
    except Exception:
        # JWT header không hợp lệ hoặc không khớp JWKS, chuyển sang bước 2
        pass

    # Step 2: Fallback xác thực qua RFC OIDC UserInfo endpoint của QNU SSO
    userinfo_url = settings.sso_userinfo_url
    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            res = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if res.status_code == 200:
                profile = res.json()
                if profile and ("sub" in profile or "name" in profile or "email" in profile):
                    return parse_sso_claims(profile)
    except Exception as exc:
        logger.debug("sso_userinfo_check_failed", error=str(exc))

    return None
