"""Unit tests for QNU Single Sign-On (OIDC) integration, fail-closed validation & fine-grained RBAC."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.auth.sso_validator import (
    JwksCacheService,
    jwks_cache_service,
    parse_sso_claims,
    validate_sso_token,
)

# Generate an RSA test key pair for signed JWT tests
_TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()
_TEST_KID = "test-sso-key-2026"

_JWK_DICT = json.loads(RSAAlgorithm.to_jwk(_TEST_PUBLIC_KEY))
_JWK_DICT["kid"] = _TEST_KID

# Second RSA key for invalid signature tests
_ROGUE_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _create_test_jwt(
    claims: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    private_key=None,
    expires_in: int = 3600,
) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": "user_sso_001",
        "name": "Nguyễn Văn A",
        "preferred_username": "nguyenvana",
        "email": "nguyenvana@qnu.edu.vn",
        "iss": settings.clean_sso_authority,
        "aud": settings.SSO_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + expires_in,
        "role": ["AI.ContentManager"],
        "permission": [
            "ai.access.read",
            "ai.chat.access",
            "ai.assistants.view",
            "ai.assistants.create",
            "ai.assistants.update",
            "ai.knowledge.view",
            "ai.knowledge.create",
            "ai.knowledge.upload",
            "ai.knowledge.update",
            "ai.knowledge.sync",
            "ai.facts.manage",
        ],
    }
    if claims:
        payload.update(claims)

    jwt_headers = {"kid": _TEST_KID, "alg": "RS256"}
    if headers:
        jwt_headers.update(headers)

    pk = private_key or _TEST_PRIVATE_KEY
    return jwt.encode(payload, pk, algorithm="RS256", headers=jwt_headers)


@pytest.fixture(autouse=True)
def setup_jwks_cache():
    """Populate JWKS cache with test key for tests."""
    jwks_cache_service.reset()
    now = time.time()
    jwks_cache_service._keys = {_TEST_KID: _JWK_DICT}
    jwks_cache_service._fetched_at = now
    jwks_cache_service._expires_at = now + 3600.0
    jwks_cache_service._stale_until = now + 3900.0
    yield
    jwks_cache_service.reset()


# ==============================================================================
# 1. Parse Claims & Role/Permission Rules (Section 3)
# ==============================================================================


def test_parse_sso_claims_valid_content_manager():
    claims = {
        "sub": "user_cm_001",
        "email": "cm@qnu.edu.vn",
        "name": "Quản lý nội dung",
        "preferred_username": "cm_user",
        "role": ["AI.ContentManager"],
        "permission": ["ai.access.read", "ai.assistants.view", "ai.assistants.create"],
    }
    actor = parse_sso_claims(claims)
    assert actor.actor_id == "user_cm_001"
    assert actor.username == "cm_user"
    assert actor.role == "AI.ContentManager"
    assert "AI.ContentManager" in actor.roles
    assert actor.has_permission("ai.access.read") is True
    assert actor.has_permission("ai.assistants.view") is True
    assert actor.has_permission("ai.assistants.create") is True
    assert actor.has_permission("ai.assistants.delete") is False


def test_parse_sso_claims_rejects_missing_ai_role():
    """Users without an application-scoped role starting with 'AI.' must be rejected with 403."""
    claims = {
        "sub": "user_generic_001",
        "email": "user@qnu.edu.vn",
        "role": ["KTX.Staff", "CTSV.Officer"],
        "permission": ["ai.access.read"],
    }
    with pytest.raises(AppException) as exc_info:
        parse_sso_claims(claims)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "thiếu vai trò ứng dụng 'AI.*'" in exc_info.value.message


def test_parse_sso_claims_rejects_missing_read_permission():
    """Users without 'ai.access.read' permission must be rejected with 403."""
    claims = {
        "sub": "user_no_read_001",
        "email": "noread@qnu.edu.vn",
        "role": ["AI.User"],
        "permission": ["ai.chat.access"],  # missing ai.access.read
    }
    with pytest.raises(AppException) as exc_info:
        parse_sso_claims(claims)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "thiếu quyền 'ai.access.read'" in exc_info.value.message


def test_parse_sso_claims_strips_wildcard_permission():
    """Wildcard '*' from SSO token must not be accepted or grant wildcard access."""
    claims = {
        "sub": "user_wildcard_001",
        "email": "wildcard@qnu.edu.vn",
        "role": ["AI.User"],
        "permission": ["ai.access.read", "*"],
    }
    actor = parse_sso_claims(claims)
    assert "*" not in actor.permissions
    assert actor.has_permission("ai.access.read") is True
    assert actor.has_permission("ai.models.manage") is False


# ==============================================================================
# 2. RBAC Semantics (Section 4)
# ==============================================================================


def test_rbac_content_manager_cannot_call_models_manage():
    actor = AuthActor(
        username="cm",
        role="AI.ContentManager",
        roles=["AI.ContentManager"],
        permissions=[
            "ai.access.read",
            "ai.access.manage",
            "ai.assistants.view",
            "ai.assistants.create",
            "ai.assistants.update",
            "ai.assistants.publish",
            "ai.knowledge.view",
            "ai.knowledge.create",
            "ai.knowledge.upload",
            "ai.knowledge.update",
            "ai.knowledge.sync",
            "ai.facts.manage",
        ],
    )
    assert actor.has_permission("ai.models.manage") is False
    assert actor.has_permission("ai.models.view") is False
    assert actor.has_permission("ai.users.manage") is False
    assert actor.has_permission("ai.audit.view") is False


def test_rbac_content_manager_cannot_delete_assistant_without_explicit_permission():
    actor = AuthActor(
        username="cm",
        role="AI.ContentManager",
        roles=["AI.ContentManager"],
        permissions=["ai.access.read", "ai.access.manage", "ai.assistants.create", "ai.assistants.update"],
    )
    assert actor.has_permission("ai.assistants.delete") is False


def test_rbac_user_cannot_upload_update_delete():
    actor = AuthActor(
        username="basic_user",
        role="AI.User",
        roles=["AI.User"],
        permissions=["ai.access.read", "ai.chat.access", "ai.chat.export", "ai.assistants.view", "ai.knowledge.view"],
    )
    assert actor.has_permission("ai.knowledge.upload") is False
    assert actor.has_permission("ai.knowledge.update") is False
    assert actor.has_permission("ai.knowledge.delete") is False
    assert actor.has_permission("ai.assistants.create") is False


def test_rbac_modelops_admin_cannot_edit_or_delete_knowledge():
    actor = AuthActor(
        username="modelops",
        role="AI.ModelOpsAdmin",
        roles=["AI.ModelOpsAdmin"],
        permissions=["ai.access.read", "ai.dashboard.view", "ai.models.view", "ai.models.manage", "ai.audit.view"],
    )
    assert actor.has_permission("ai.models.manage") is True
    assert actor.has_permission("ai.knowledge.update") is False
    assert actor.has_permission("ai.knowledge.delete") is False
    assert actor.has_permission("ai.assistants.delete") is False


def test_rbac_ai_admin_allowed_all_ai_permissions():
    actor = AuthActor(
        username="admin",
        role="AI.Admin",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
    )
    assert actor.has_permission("ai.models.manage") is True
    assert actor.has_permission("ai.assistants.delete") is True
    assert actor.has_permission("ai.knowledge.delete") is True
    assert actor.has_permission("ai.users.manage") is True
    assert actor.has_permission("ai.audit.view") is True


def test_rbac_generic_admin_role_cannot_bypass_rbac():
    """Generic role names like 'admin', 'administrator', 'super_admin' must NOT bypass RBAC."""
    actor = AuthActor(
        username="fake_admin",
        role="admin",
        roles=["admin", "administrator", "super_admin"],
        permissions=["ai.access.read"],
    )
    assert actor.has_permission("ai.models.manage") is False
    assert actor.has_permission("ai.assistants.delete") is False
    assert actor.has_permission("ai.knowledge.delete") is False


def test_rbac_undeclared_permission_is_rejected():
    actor = AuthActor(
        username="staff_user",
        role="AI.User",
        roles=["AI.User"],
        permissions=["ai.access.read", "ai.chat.access"],
    )
    assert actor.has_permission("ai.undeclared.action") is False


# ==============================================================================
# 3. JWT Issuer and Audience Validation (Section 2)
# ==============================================================================


@pytest.mark.asyncio
async def test_validate_sso_token_valid_token_accepted():
    token = _create_test_jwt()
    actor = await validate_sso_token(token)
    assert actor.username == "nguyenvana"
    assert actor.role == "AI.ContentManager"
    assert actor.has_permission("ai.assistants.create") is True


@pytest.mark.asyncio
async def test_validate_sso_token_wrong_audience_rejected():
    """Token issued for KTX/E-Office audience must be rejected."""
    token = _create_test_jwt(claims={"aud": "ktx.api"})
    with pytest.raises(AppException) as exc_info:
        await validate_sso_token(token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_audience"


@pytest.mark.asyncio
async def test_validate_sso_token_wrong_issuer_rejected():
    token = _create_test_jwt(claims={"iss": "https://fake-issuer.com"})
    with pytest.raises(AppException) as exc_info:
        await validate_sso_token(token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_issuer"


@pytest.mark.asyncio
async def test_validate_sso_token_expired_rejected():
    token = _create_test_jwt(expires_in=-3600)
    with pytest.raises(AppException) as exc_info:
        await validate_sso_token(token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "token_expired"


@pytest.mark.asyncio
async def test_validate_sso_token_invalid_signature_no_userinfo_fallback():
    """JWT with invalid signature must fail-closed immediately without fallback to UserInfo."""
    token = _create_test_jwt(private_key=_ROGUE_PRIVATE_KEY)
    with patch("httpx.AsyncClient.get") as mock_userinfo:
        with pytest.raises(AppException) as exc_info:
            await validate_sso_token(token)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "invalid_signature"
        mock_userinfo.assert_not_called()


@pytest.mark.asyncio
async def test_validate_sso_token_missing_audience_rejected():
    """JWT missing the aud claim must be rejected."""
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": "user_sso_001",
        "iss": settings.clean_sso_authority,
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "role": ["AI.User"],
        "permission": ["ai.access.read"],
        # 'aud' is omitted intentionally
    }
    token = jwt.encode(payload, _TEST_PRIVATE_KEY, algorithm="RS256", headers={"kid": _TEST_KID})
    with pytest.raises(AppException) as exc_info:
        await validate_sso_token(token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.code in ("invalid_audience", "missing_claim")


# ==============================================================================
# 4. Production Security & Anonymous Admin Elimination (Section 1)
# ==============================================================================


@pytest.mark.asyncio
async def test_production_unauthenticated_request_returns_401():
    """In production, request without token must always return 401."""
    from fastapi import Request

    mock_request = AsyncMock(spec=Request)
    mock_request.headers = {}
    mock_request.cookies = {}

    with patch("app.modules.auth.dependencies.get_settings") as mock_settings:
        mock_settings.return_value.ENVIRONMENT = "production"
        mock_settings.return_value.DEV_AUTH_ENABLED = False
        mock_settings.return_value.SSO_ENABLED = True
        mock_settings.return_value.SSO_ALLOWED_ALGORITHMS = ["RS256"]

        with pytest.raises(AppException) as exc_info:
            await get_current_actor(mock_request)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "unauthorized"


@pytest.mark.asyncio
async def test_development_dev_auth_enabled_provides_dev_actor():
    """In development with DEV_AUTH_ENABLED=True, provide dev actor when not enforcing auth."""
    from fastapi import Request

    mock_request = AsyncMock(spec=Request)
    mock_request.headers = {}
    mock_request.cookies = {}

    with patch("app.modules.auth.dependencies.get_settings") as mock_settings:
        mock_settings.return_value.ENVIRONMENT = "development"
        mock_settings.return_value.DEV_AUTH_ENABLED = True

        actor = await get_current_actor(mock_request)
        assert actor.username == "admin"
        assert actor.role == "AI.Admin"
        assert "AI.Admin" in actor.roles
        assert actor.has_permission("ai.access.admin") is True


@pytest.mark.asyncio
async def test_production_rejects_local_dev_jwt():
    """Production must not accept local dev JWT session cookies or tokens."""
    from fastapi import Request

    from app.core.security import create_access_token

    local_jwt = create_access_token(
        subject="admin",
        claims={"actor_id": "act_admin", "role": "admin"},
    )

    mock_request = AsyncMock(spec=Request)
    mock_request.headers = {"Authorization": f"Bearer {local_jwt}"}
    mock_request.cookies = {"qnu_session": local_jwt}

    with patch("app.modules.auth.dependencies.get_settings") as mock_settings:
        mock_settings.return_value.ENVIRONMENT = "production"
        mock_settings.return_value.DEV_AUTH_ENABLED = False
        mock_settings.return_value.SSO_ENABLED = True
        mock_settings.return_value.SSO_ALLOWED_ALGORITHMS = ["RS256"]
        mock_settings.return_value.JWT_ALGORITHM = "HS256"

        with pytest.raises(AppException) as exc_info:
            await get_current_actor(mock_request)
        # In production, HS256 token must fail-closed as invalid algorithm / invalid token
        assert exc_info.value.status_code == 401


# ==============================================================================
# 5. Settings Fail-Fast Validation (Section 1)
# ==============================================================================


def test_settings_production_requires_sso_enabled():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="SSO_ENABLED must be True in production"):
        Settings(
            ENVIRONMENT="production",
            SSO_ENABLED=False,
            DEV_AUTH_ENABLED=False,
            SSO_AUTHORITY="https://sso.qnu.edu.vn",
            SSO_AUDIENCE="ai.api",
            SECRET_KEY="a" * 32,
            INTERNAL_API_KEY="b" * 32,
            DEV_ACCESS_PASSWORD="c" * 32,
            DATABASE_URL="postgresql+asyncpg://u:p@host:5432/db",
            S3_SECRET_KEY="d" * 32,
            PROVIDER_ENCRYPTION_KEY="e" * 32,
        )


def test_settings_production_requires_dev_auth_disabled():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="DEV_AUTH_ENABLED must be False in production"):
        Settings(
            ENVIRONMENT="production",
            SSO_ENABLED=True,
            DEV_AUTH_ENABLED=True,
            SSO_AUTHORITY="https://sso.qnu.edu.vn",
            SSO_AUDIENCE="ai.api",
            SECRET_KEY="a" * 32,
            INTERNAL_API_KEY="b" * 32,
            DEV_ACCESS_PASSWORD="c" * 32,
            DATABASE_URL="postgresql+asyncpg://u:p@host:5432/db",
            S3_SECRET_KEY="d" * 32,
            PROVIDER_ENCRYPTION_KEY="e" * 32,
        )


def test_settings_production_requires_https_sso_authority():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="SSO_AUTHORITY must be HTTPS in production"):
        Settings(
            ENVIRONMENT="production",
            SSO_ENABLED=True,
            DEV_AUTH_ENABLED=False,
            SSO_AUTHORITY="http://insecure-sso.qnu.edu.vn",
            SSO_AUDIENCE="ai.api",
            SECRET_KEY="a" * 32,
            INTERNAL_API_KEY="b" * 32,
            DEV_ACCESS_PASSWORD="c" * 32,
            DATABASE_URL="postgresql+asyncpg://u:p@host:5432/db",
            S3_SECRET_KEY="d" * 32,
            PROVIDER_ENCRYPTION_KEY="e" * 32,
        )


def test_settings_production_requires_non_empty_audience():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="SSO_AUDIENCE cannot be empty in production"):
        Settings(
            ENVIRONMENT="production",
            SSO_ENABLED=True,
            DEV_AUTH_ENABLED=False,
            SSO_AUTHORITY="https://sso.qnu.edu.vn",
            SSO_AUDIENCE="   ",
            SECRET_KEY="a" * 32,
            INTERNAL_API_KEY="b" * 32,
            DEV_ACCESS_PASSWORD="c" * 32,
            DATABASE_URL="postgresql+asyncpg://u:p@host:5432/db",
            S3_SECRET_KEY="d" * 32,
            PROVIDER_ENCRYPTION_KEY="e" * 32,
        )


# ==============================================================================
# 5. JWKS Cache Lifecycle & Stale Window Tests (Yêu cầu 3)
# ==============================================================================


def _mock_response(status_code: int = 200, json_data: Any = None):
    from unittest.mock import MagicMock
    resp = MagicMock()
    resp.status_code = status_code
    if isinstance(json_data, Exception):
        resp.json.side_effect = json_data
    else:
        resp.json.return_value = json_data
    return resp


@pytest.mark.asyncio
async def test_jwks_cache_valid_ttl_used_without_http():
    """1. Cache còn TTL được sử dụng mà không gọi HTTP."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
    cache._fetched_at = now
    cache._expires_at = now + 3600.0
    cache._stale_until = now + 3900.0

    with patch("httpx.AsyncClient.get") as mock_get:
        keys = await cache.get_keys(force_refresh=False, now=now + 500.0)
        assert keys == {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
        mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_jwks_cache_expired_refreshes_successfully_with_new_key():
    """2. Cache hết TTL, refresh thành công thì dùng key mới."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
    cache._fetched_at = now - 3700.0
    cache._expires_at = now - 100.0  # Expired
    cache._stale_until = now + 200.0

    new_keys_data = {"keys": [{"kid": "kid-2", "kty": "RSA"}]}

    with patch("httpx.AsyncClient.get", return_value=_mock_response(200, new_keys_data)) as mock_get:
        keys = await cache.get_keys(force_refresh=False, now=now)
        assert "kid-2" in keys
        assert cache._expires_at == now + 3600.0
        assert cache._stale_until == now + 3600.0 + 300.0
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_jwks_cache_expired_fetch_fails_uses_stale_key_within_stale_window():
    """3. Cache hết TTL, fetch lỗi nhưng còn stale window thì dùng tạm key cũ."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
    cache._fetched_at = now - 3650.0
    cache._expires_at = now - 50.0  # Expired
    cache._stale_until = now + 250.0  # Still within stale window (now <= 1250)

    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        keys = await cache.get_keys(force_refresh=False, now=now)
        assert keys == {"kid-1": {"kid": "kid-1", "kty": "RSA"}}


@pytest.mark.asyncio
async def test_jwks_cache_expired_beyond_stale_window_fails_closed():
    """4. Quá stale window và fetch lỗi thì fail-closed với sso_jwks_unavailable (503)."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
    cache._fetched_at = now - 4000.0
    cache._expires_at = now - 400.0
    cache._stale_until = now - 100.0  # Past stale window

    with patch("httpx.AsyncClient.get", side_effect=Exception("Network down")):
        with pytest.raises(AppException) as exc_info:
            await cache.get_keys(force_refresh=False, now=now)
        assert exc_info.value.status_code == 503
        assert exc_info.value.code == "sso_jwks_unavailable"


@pytest.mark.asyncio
async def test_jwks_empty_response_does_not_clear_good_cache():
    """5. JWKS response rỗng không xóa cache tốt."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
    cache._fetched_at = now - 3650.0
    cache._expires_at = now - 50.0
    cache._stale_until = now + 250.0  # In stale window

    with patch("httpx.AsyncClient.get", return_value=_mock_response(200, {"keys": []})):
        keys = await cache.get_keys(force_refresh=False, now=now)
        # Did not overwrite with empty keys, kept stale key
        assert keys == {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
        assert "kid-1" in cache.keys


@pytest.mark.asyncio
async def test_jwks_invalid_schema_does_not_clear_good_cache():
    """6. JWKS JSON sai schema không xóa cache tốt."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
    cache._fetched_at = now - 3650.0
    cache._expires_at = now - 50.0
    cache._stale_until = now + 250.0  # In stale window

    with patch("httpx.AsyncClient.get", return_value=_mock_response(200, {"error": "internal_error", "not_keys": True})):
        keys = await cache.get_keys(force_refresh=False, now=now)
        assert keys == {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
        assert "kid-1" in cache.keys


@pytest.mark.asyncio
async def test_unknown_kid_triggers_force_refresh_once():
    """7. Unknown kid trigger force refresh đúng một lần."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
    cache._fetched_at = now
    cache._expires_at = now + 3600.0
    cache._stale_until = now + 3900.0

    call_count = 0

    async def mock_get_impl(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # SSO still does not have the unknown kid
        return _mock_response(200, {"keys": [{"kid": "kid-1", "kty": "RSA"}]})

    with patch("httpx.AsyncClient.get", side_effect=mock_get_impl):
        with pytest.raises(AppException) as exc_info:
            await cache.get_key_for_kid("kid-unknown", now=now)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "invalid_key"
        # Exactly one force refresh call made
        assert call_count == 1


@pytest.mark.asyncio
async def test_revoked_key_not_used_after_stale_window():
    """8. Khóa bị thu hồi không được dùng sau stale window."""
    cache = JwksCacheService()
    now = 1000.0
    # Old revoked key in cache, now past stale window
    cache._keys = {"revoked-kid": {"kid": "revoked-kid", "kty": "RSA"}}
    cache._fetched_at = now - 5000.0
    cache._expires_at = now - 1400.0
    cache._stale_until = now - 1100.0  # Expired and beyond stale window

    # SSO server rotated keys, old key is gone, returns new active key
    with patch("httpx.AsyncClient.get", return_value=_mock_response(200, {"keys": [{"kid": "new-active-kid", "kty": "RSA"}]})):
        # Asking for the revoked kid should refresh, not find it, and fail closed with 401
        with pytest.raises(AppException) as exc_info:
            await cache.get_key_for_kid("revoked-kid", now=now)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "invalid_key"
        # And cache now contains the new active key only
        assert "revoked-kid" not in cache.keys
        assert "new-active-kid" in cache.keys


# ==============================================================================
# 6. Concurrent JWKS Stampede Protection Tests (Yêu cầu 3)
# ==============================================================================


@pytest.mark.asyncio
async def test_concurrent_10_requests_expired_ttl_triggers_exactly_one_http_call():
    """1. 10 request đồng thời khi cache hết TTL chỉ tạo đúng một HTTP call."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-old": {"kid": "kid-old", "kty": "RSA"}}
    cache._fetched_at = now - 4000.0
    cache._expires_at = now - 400.0  # Expired
    cache._stale_until = now + 500.0

    call_count = 0
    fetch_gate = asyncio.Event()

    async def mock_get_impl(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await fetch_gate.wait()
        return _mock_response(200, {"keys": [{"kid": "kid-new", "kty": "RSA"}]})

    start_barrier = asyncio.Event()

    async def worker():
        await start_barrier.wait()
        return await cache.get_keys(force_refresh=False, now=now)

    with patch("httpx.AsyncClient.get", side_effect=mock_get_impl):
        tasks = [asyncio.create_task(worker()) for _ in range(10)]

        # Let all workers reach the barrier
        start_barrier.set()
        await asyncio.sleep(0.01)

        # Release the leader's HTTP fetch
        fetch_gate.set()

        results = await asyncio.gather(*tasks)

        assert call_count == 1
        for res in results:
            assert res == {"kid-new": {"kid": "kid-new", "kty": "RSA"}}


@pytest.mark.asyncio
async def test_concurrent_10_requests_unknown_kid_triggers_one_force_refresh():
    """2. 10 request đồng thời gặp cùng unknown kid chỉ tạo một đợt force refresh."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
    cache._fetched_at = now
    cache._expires_at = now + 3600.0
    cache._stale_until = now + 3900.0

    call_count = 0
    fetch_gate = asyncio.Event()

    async def mock_get_impl(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await fetch_gate.wait()
        # Still does not contain unknown kid
        return _mock_response(200, {"keys": [{"kid": "kid-1", "kty": "RSA"}]})

    start_barrier = asyncio.Event()

    async def worker():
        await start_barrier.wait()
        return await cache.get_key_for_kid("kid-unknown-123", now=now)

    with patch("httpx.AsyncClient.get", side_effect=mock_get_impl):
        tasks = [asyncio.create_task(worker()) for _ in range(10)]

        start_barrier.set()
        await asyncio.sleep(0.01)

        fetch_gate.set()

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert call_count == 1
        for res in results:
            assert isinstance(res, AppException)
            assert res.status_code == 401
            assert res.code == "invalid_key"


@pytest.mark.asyncio
async def test_concurrent_refresh_fails_within_stale_window_all_receive_stale_cache():
    """3. Refresh lỗi trong stale window: mọi waiter nhận cache cũ."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-stale": {"kid": "kid-stale", "kty": "RSA"}}
    cache._fetched_at = now - 3650.0
    cache._expires_at = now - 50.0
    cache._stale_until = now + 250.0  # Within stale window

    call_count = 0

    async def mock_get_impl(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        raise RuntimeError("Temporary SSO outage")

    start_barrier = asyncio.Event()

    async def worker():
        await start_barrier.wait()
        return await cache.get_keys(force_refresh=False, now=now)

    with patch("httpx.AsyncClient.get", side_effect=mock_get_impl):
        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_barrier.set()
        results = await asyncio.gather(*tasks)

        assert call_count == 1
        for res in results:
            assert res == {"kid-stale": {"kid": "kid-stale", "kty": "RSA"}}


@pytest.mark.asyncio
async def test_concurrent_refresh_fails_beyond_stale_window_all_fail_closed_503():
    """4. Refresh lỗi quá stale window: mọi waiter fail-closed 503."""
    cache = JwksCacheService()
    now = 1000.0
    cache._keys = {"kid-dead": {"kid": "kid-dead", "kty": "RSA"}}
    cache._fetched_at = now - 4500.0
    cache._expires_at = now - 900.0
    cache._stale_until = now - 600.0  # Past stale window

    call_count = 0

    async def mock_get_impl(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        raise RuntimeError("Hard network failure")

    start_barrier = asyncio.Event()

    async def worker():
        await start_barrier.wait()
        return await cache.get_keys(force_refresh=False, now=now)

    with patch("httpx.AsyncClient.get", side_effect=mock_get_impl):
        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        start_barrier.set()
        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert call_count == 1
        for res in results:
            assert isinstance(res, AppException)
            assert res.status_code == 503
            assert res.code == "sso_jwks_unavailable"


# ==============================================================================
# 7. OIDC Issuer Strict Matching & Contract Tests (Yêu cầu 7)
# ==============================================================================


@pytest.mark.asyncio
async def test_oidc_issuer_exact_match_contract():
    """Token issuer thực tế của QNU SSO được chấp nhận, issuer gần giống hoặc khác trailing/path bị từ chối."""
    # 1. Exact valid issuer matches expected_issuer
    claims_valid = {
        "sub": "usr_test_exact",
        "iss": "https://sso.qnu.edu.vn",
        "aud": "ai.api",
        "exp": time.time() + 3600,
        "nbf": time.time() - 10,
        "role": ["AI.Admin"],
        "permission": ["ai.access.read", "ai.access.admin"],
    }
    token_valid = _create_test_jwt(claims=claims_valid, headers={"kid": _TEST_KID})

    with (
        patch("app.modules.auth.sso_validator.jwks_cache_service.get_key_for_kid", return_value=_JWK_DICT),
        patch("app.modules.auth.sso_validator.get_settings") as mock_settings,
    ):
        mock_settings.return_value.SSO_AUTHORITY = "https://sso.qnu.edu.vn"
        mock_settings.return_value.clean_sso_authority = "https://sso.qnu.edu.vn"
        mock_settings.return_value.SSO_AUDIENCE = "ai.api"
        mock_settings.return_value.SSO_ALLOWED_ALGORITHMS = ["RS256"]

        actor = await validate_sso_token(token_valid)
        assert actor.actor_id == "usr_test_exact"

    # 2. Trailing slash is rejected
    claims_trailing = dict(claims_valid, iss="https://sso.qnu.edu.vn/")
    token_trailing = _create_test_jwt(claims=claims_trailing, headers={"kid": _TEST_KID})

    with (
        patch("app.modules.auth.sso_validator.jwks_cache_service.get_key_for_kid", return_value=_JWK_DICT),
        patch("app.modules.auth.sso_validator.get_settings") as mock_settings,
    ):
        mock_settings.return_value.SSO_AUTHORITY = "https://sso.qnu.edu.vn"
        mock_settings.return_value.clean_sso_authority = "https://sso.qnu.edu.vn"
        mock_settings.return_value.SSO_AUDIENCE = "ai.api"
        mock_settings.return_value.SSO_ALLOWED_ALGORITHMS = ["RS256"]

        with pytest.raises(AppException) as exc:
            await validate_sso_token(token_trailing)
        assert exc.value.code == "invalid_issuer"
        assert exc.value.status_code == 401

    # 3. Subdomain / spoofed domain is rejected
    claims_spoof = dict(claims_valid, iss="https://sso.qnu.edu.vn.evil.com")
    token_spoof = _create_test_jwt(claims=claims_spoof, headers={"kid": _TEST_KID})

    with (
        patch("app.modules.auth.sso_validator.jwks_cache_service.get_key_for_kid", return_value=_JWK_DICT),
        patch("app.modules.auth.sso_validator.get_settings") as mock_settings,
    ):
        mock_settings.return_value.SSO_AUTHORITY = "https://sso.qnu.edu.vn"
        mock_settings.return_value.clean_sso_authority = "https://sso.qnu.edu.vn"
        mock_settings.return_value.SSO_AUDIENCE = "ai.api"
        mock_settings.return_value.SSO_ALLOWED_ALGORITHMS = ["RS256"]

        with pytest.raises(AppException) as exc:
            await validate_sso_token(token_spoof)
        assert exc.value.code == "invalid_issuer"
        assert exc.value.status_code == 401

    # 4. HTTP scheme is rejected
    claims_http = dict(claims_valid, iss="http://sso.qnu.edu.vn")
    token_http = _create_test_jwt(claims=claims_http, headers={"kid": _TEST_KID})

    with (
        patch("app.modules.auth.sso_validator.jwks_cache_service.get_key_for_kid", return_value=_JWK_DICT),
        patch("app.modules.auth.sso_validator.get_settings") as mock_settings,
    ):
        mock_settings.return_value.SSO_AUTHORITY = "https://sso.qnu.edu.vn"
        mock_settings.return_value.clean_sso_authority = "https://sso.qnu.edu.vn"
        mock_settings.return_value.SSO_AUDIENCE = "ai.api"
        mock_settings.return_value.SSO_ALLOWED_ALGORITHMS = ["RS256"]

        with pytest.raises(AppException) as exc:
            await validate_sso_token(token_http)
        assert exc.value.code == "invalid_issuer"
        assert exc.value.status_code == 401

