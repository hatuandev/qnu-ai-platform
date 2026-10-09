"""QNU Single Sign-On (OpenIddict / OIDC) Token Validator."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import jwt
import structlog
from jwt.algorithms import RSAAlgorithm

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.modules.auth.schemas import AuthActor

logger = structlog.get_logger(__name__)


class JwksCacheService:
    """In-memory cache for QNU SSO JWKS public keys with single-flight stampede protection,
    stale-if-error resilience, and key rotation support.
    """

    def __init__(self) -> None:
        self._keys: dict[str, Any] = {}
        self._fetched_at: float = 0.0
        self._expires_at: float = 0.0
        self._stale_until: float = 0.0
        self._lock: asyncio.Lock | None = None
        self._refresh_count: int = 0
        self._last_error: AppException | None = None

    def reset(self) -> None:
        """Reset cache state for testing or reinitialization."""
        self._keys = {}
        self._fetched_at = 0.0
        self._expires_at = 0.0
        self._stale_until = 0.0
        self._lock = None
        self._refresh_count = 0
        self._last_error = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @property
    def keys(self) -> dict[str, Any]:
        return self._keys

    @property
    def fetched_at(self) -> float:
        return self._fetched_at

    @property
    def expires_at(self) -> float:
        return self._expires_at

    @property
    def stale_until(self) -> float:
        return self._stale_until

    async def get_keys(self, force_refresh: bool = False, now: float | None = None) -> dict[str, Any]:
        """Fetch and cache public JSON Web Key Sets (JWKS) from QNU SSO with key rotation support.

        Rules:
        1. Cache valid: now < expires_at and not force_refresh -> return cached keys immediately.
        2. Single-flight synchronization via asyncio.Lock:
           - Double-check after acquiring lock.
           - If a refresh completed while waiting for lock (refresh_count > snapshot), reuse result.
        3. Refresh policies:
           - On success with valid schema: update fetched_at, expires_at, stale_until, return new keys.
           - On failure:
             * If now <= stale_until and cached keys exist: log warning and return cached keys.
             * If now > stale_until or no cached keys: fail-closed with 503 sso_jwks_unavailable.
        """
        current_time = now if now is not None else time.time()
        current_settings = get_settings()
        ttl = float(getattr(current_settings, "SSO_JWKS_CACHE_TTL_SECONDS", 3600))
        stale_window = float(getattr(current_settings, "SSO_JWKS_STALE_IF_ERROR_SECONDS", 300))

        # 1. Fast path: cache is valid and no force refresh requested
        if not force_refresh and self._keys and current_time < self._expires_at:
            return self._keys

        snapshot_generation = self._refresh_count

        lock = self._get_lock()
        async with lock:
            current_time = now if now is not None else time.time()

            # Double-check after acquiring lock:
            if not force_refresh and self._keys and current_time < self._expires_at:
                return self._keys

            # If force_refresh or expired TTL, check if another task already refreshed while we waited:
            if self._refresh_count > snapshot_generation:
                if self._last_error is not None and (self._fetched_at == 0.0 or current_time > self._stale_until):
                    raise self._last_error
                if self._keys:
                    # New keys or acceptable stale keys are available from the concurrent refresh batch
                    return self._keys
                if self._last_error is not None:
                    raise self._last_error

            # This task is the designated leader for the refresh batch
            jwks_url = current_settings.sso_jwks_url
            fetch_succeeded = False
            parsed_keys: dict[str, Any] = {}
            failure_reason = ""

            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    res = await client.get(jwks_url)
                    if res.status_code == 200:
                        try:
                            data = res.json()
                        except Exception as json_err:
                            failure_reason = f"invalid_json: {json_err}"
                            data = None

                        if isinstance(data, dict):
                            raw_keys = data.get("keys")
                            if isinstance(raw_keys, list) and len(raw_keys) > 0:
                                parsed_keys = {
                                    k["kid"]: k
                                    for k in raw_keys
                                    if isinstance(k, dict) and k.get("kid")
                                }
                                if parsed_keys:
                                    fetch_succeeded = True
                                else:
                                    failure_reason = "empty_or_invalid_kids_in_keys"
                            else:
                                failure_reason = "empty_keys_or_invalid_schema"
                        else:
                            failure_reason = failure_reason or "jwks_not_dict"
                    else:
                        failure_reason = f"http_{res.status_code}"
            except Exception as exc:
                failure_reason = f"network_error: {type(exc).__name__}"

            self._refresh_count += 1

            if fetch_succeeded:
                self._keys = parsed_keys
                self._fetched_at = current_time
                self._expires_at = current_time + ttl
                self._stale_until = current_time + ttl + stale_window
                self._last_error = None
                logger.info("sso_jwks_cached", key_count=len(parsed_keys), url=jwks_url)
                return self._keys

            # Fetch failed or returned invalid/empty response. NEVER overwrite good cache with empty.
            cache_age = (current_time - self._fetched_at) if self._fetched_at > 0 else 0.0

            if self._keys and current_time <= self._stale_until:
                self._last_error = None
                logger.warning(
                    "sso_jwks_stale_fallback",
                    reason=failure_reason or "fetch_failed_using_stale_cache",
                    cache_age_seconds=round(cache_age, 2),
                    stale_fallback_used=True,
                    url=jwks_url,
                )
                return self._keys

            err = AppException(
                "Máy chủ xác thực SSO JWKS hiện không khả dụng.",
                code="sso_jwks_unavailable",
                status_code=503,
            )
            self._last_error = err

            logger.warning(
                "sso_jwks_unavailable",
                reason=failure_reason or "stale_window_exceeded",
                cache_age_seconds=round(cache_age, 2) if self._fetched_at > 0 else None,
                stale_fallback_used=False,
                url=jwks_url,
            )
            raise err

    async def get_key_for_kid(self, kid: str, now: float | None = None) -> dict[str, Any]:
        """Get JWK for kid with single-flight force refresh on unknown kid."""
        keys = await self.get_keys(force_refresh=False, now=now)
        if kid not in keys:
            # Key rotation: force refresh. Single-flight lock ensures concurrent requests
            # with the same unknown kid only trigger ONE HTTP refresh batch.
            keys = await self.get_keys(force_refresh=True, now=now)

        if kid not in keys:
            cache_age = ((now or time.time()) - self._fetched_at) if self._fetched_at > 0 else None
            logger.warning(
                "sso_jwt_validation_failed",
                reason="unknown_kid",
                kid=kid,
                cache_age_seconds=round(cache_age, 2) if cache_age is not None else None,
                stale_fallback_used=False,
            )
            raise AppException(
                "Không tìm thấy khóa công khai phù hợp trên máy chủ SSO.",
                code="invalid_key",
                status_code=401,
            )

        return keys[kid]


# Singleton instance for runtime usage
jwks_cache_service = JwksCacheService()


async def get_jwks_keys(force_refresh: bool = False) -> dict[str, Any]:
    """Fetch and cache public JSON Web Key Sets (JWKS) from QNU SSO with key rotation support."""
    return await jwks_cache_service.get_keys(force_refresh=force_refresh)


def parse_sso_claims(claims: dict[str, Any]) -> AuthActor:
    """Parse verified OIDC claims into typed AuthActor following least privilege and fail-closed rules."""
    sub = str(claims.get("sub") or claims.get("nameid") or "").strip()
    if not sub:
        raise AppException("Mã xác thực không chứa thông tin định danh người dùng.", code="invalid_claims", status_code=401)

    email = claims.get("email")
    name = claims.get("name") or claims.get("preferred_username") or (email.split("@")[0] if email else "Cán bộ QNU")
    username = claims.get("preferred_username") or (email.split("@")[0] if email else sub)

    # 1. Resolve application roles (MUST NOT contain generic substring elevation)
    raw_roles = claims.get("role") or claims.get("roles") or []
    if isinstance(raw_roles, str):
        roles = [r.strip() for r in raw_roles.split(",") if r.strip()]
    elif isinstance(raw_roles, list):
        roles = [str(r).strip() for r in raw_roles if str(r).strip()]
    else:
        roles = []

    # Application roles for QNU AI Platform MUST start with 'AI.'
    ai_roles = [r for r in roles if r.startswith("AI.")]
    if not ai_roles:
        logger.warning("sso_access_denied", reason="missing_ai_role", sub=sub)
        raise AppException(
            "Tài khoản chưa được phân quyền truy cập QNU AI Platform (thiếu vai trò ứng dụng 'AI.*').",
            code="forbidden",
            status_code=403,
        )

    # 2. Resolve fine-grained permissions (Never accept wildcard "*")
    raw_perms = claims.get("permission") or claims.get("permissions") or []
    if isinstance(raw_perms, str):
        permissions = [p.strip() for p in raw_perms.split(",") if p.strip()]
    elif isinstance(raw_perms, list):
        permissions = [str(p).strip() for p in raw_perms if str(p).strip()]
    else:
        permissions = []

    # Strip any wildcard '*' from SSO token
    clean_permissions = [p for p in permissions if p != "*"]

    # 3. User MUST have 'ai.access.read' permission (or ai.access.admin / AI.Admin)
    has_read_permission = (
        "ai.access.read" in clean_permissions
        or "ai.access.admin" in clean_permissions
        or "AI.Admin" in ai_roles
    )
    if not has_read_permission:
        logger.warning("sso_access_denied", reason="missing_read_permission", sub=sub)
        raise AppException(
            "Tài khoản chưa được cấp quyền truy cập cơ bản (thiếu quyền 'ai.access.read').",
            code="forbidden",
            status_code=403,
        )

    raw_user_type = str(claims.get("user_type") or claims.get("userType") or "staff").lower()
    student_id = claims.get("student_id") or claims.get("studentId")

    primary_role = "AI.Admin" if "AI.Admin" in ai_roles else ai_roles[0]

    return AuthActor(
        actor_id=sub,
        username=str(username),
        display_name=str(name),
        email=str(email) if email else None,
        user_type=raw_user_type,
        student_id=str(student_id) if student_id else None,
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        role=primary_role,
        roles=ai_roles,
        permissions=clean_permissions,
        session_version="sso_v1",
        authenticated=True,
    )


async def validate_sso_token(token: str) -> AuthActor:
    """Validate Bearer access token issued by QNU SSO (OpenIddict).

    Enforces strict fail-closed security:
    1. For JWT tokens (3 parts):
       - Header algorithm must match SSO_ALLOWED_ALGORITHMS (RS256).
       - Signature verified against QNU SSO JWKS (supports dynamic key rotation).
       - Claims verified: exp, nbf, iss == clean_sso_authority, aud == SSO_AUDIENCE (ai.api).
       - On any verification failure (signature, issuer, aud, exp): fails closed, NO UserInfo fallback.
    2. For opaque tokens (non-JWT):
       - Only used if token is NOT a compact 3-part JWT.
       - Validated against OIDC UserInfo endpoint.
       - MUST verify that the token was issued for the 'ai.api' resource scope.
    """
    if not token or not token.strip():
        raise AppException("Mã xác thực không được để trống.", code="unauthorized", status_code=401)

    current_settings = get_settings()
    if not current_settings.SSO_ENABLED:
        raise AppException("Dịch vụ xác thực QNU SSO đang tạm tắt.", code="sso_disabled", status_code=503)

    token = token.strip()
    parts = token.split(".")

    # --- PATH A: Signed Compact JWT (Header.Payload.Signature) ---
    if len(parts) == 3:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception:
            logger.warning("sso_jwt_validation_failed", reason="malformed_jwt_header")
            raise AppException("Cấu trúc mã xác thực JWT không hợp lệ.", code="invalid_token", status_code=401)

        alg = unverified_header.get("alg")
        allowed_algs = current_settings.SSO_ALLOWED_ALGORITHMS
        if alg not in allowed_algs:
            logger.warning("sso_jwt_validation_failed", reason="disallowed_algorithm", alg=alg)
            raise AppException(
                f"Thuật toán mã hóa '{alg}' không nằm trong danh sách được phép.",
                code="invalid_algorithm",
                status_code=401,
            )

        kid = unverified_header.get("kid")
        if not kid:
            logger.warning("sso_jwt_validation_failed", reason="missing_kid")
            raise AppException("Mã xác thực JWT thiếu khóa định danh 'kid'.", code="invalid_token", status_code=401)

        jwk_key = await jwks_cache_service.get_key_for_kid(kid)

        try:
            public_key = RSAAlgorithm.from_jwk(jwk_key)
        except Exception as exc:
            logger.warning("sso_jwt_validation_failed", reason="jwk_conversion_error", error=str(exc))
            raise AppException("Lỗi phân giải khóa công khai JWKS.", code="invalid_key", status_code=401)

        expected_issuer = current_settings.clean_sso_authority
        expected_audience = current_settings.SSO_AUDIENCE

        try:
            claims = jwt.decode(
                token,
                public_key,
                algorithms=allowed_algs,
                issuer=expected_issuer,
                audience=expected_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iss", "aud"],
                },
            )
        except jwt.ExpiredSignatureError:
            logger.warning("sso_jwt_validation_failed", reason="token_expired")
            raise AppException("Mã xác thực SSO đã hết hạn.", code="token_expired", status_code=401)
        except jwt.InvalidIssuerError:
            logger.warning("sso_jwt_validation_failed", reason="invalid_issuer")
            raise AppException("Đơn vị phát hành (issuer) của mã xác thực không hợp lệ.", code="invalid_issuer", status_code=401)
        except jwt.InvalidAudienceError:
            logger.warning("sso_jwt_validation_failed", reason="invalid_audience")
            raise AppException("Đối tượng sử dụng (audience) của mã xác thực không hợp lệ.", code="invalid_audience", status_code=401)
        except jwt.MissingRequiredClaimError as exc:
            logger.warning("sso_jwt_validation_failed", reason="missing_required_claim", claim=str(exc))
            raise AppException("Mã xác thực thiếu các trường thông tin bắt buộc.", code="missing_claim", status_code=401)
        except jwt.InvalidSignatureError:
            logger.warning("sso_jwt_validation_failed", reason="invalid_signature")
            raise AppException("Chữ ký của mã xác thực SSO không hợp lệ.", code="invalid_signature", status_code=401)
        except jwt.PyJWTError as exc:
            logger.warning("sso_jwt_validation_failed", reason="jwt_decode_error", error=type(exc).__name__)
            raise AppException("Mã xác thực SSO không hợp lệ.", code="invalid_token", status_code=401)

        return parse_sso_claims(claims)

    # --- PATH B: Opaque / Non-JWT Token Verification via UserInfo ---
    userinfo_url = current_settings.sso_userinfo_url
    expected_audience = current_settings.SSO_AUDIENCE
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if res.status_code == 200:
                profile = res.json()
                # Verify that opaque token belongs to ai.api resource
                scopes_raw = profile.get("scope") or profile.get("scopes") or []
                aud_raw = profile.get("aud") or profile.get("audience") or []
                scopes_set = set(scopes_raw.split() if isinstance(scopes_raw, str) else scopes_raw)
                aud_set = set([aud_raw] if isinstance(aud_raw, str) else aud_raw)

                if expected_audience not in scopes_set and expected_audience not in aud_set:
                    logger.warning("sso_opaque_validation_failed", reason="missing_resource_scope")
                    raise AppException(
                        f"Mã xác thực opaque không được cấp quyền cho tài nguyên '{expected_audience}'.",
                        code="invalid_scope",
                        status_code=401,
                    )
                return parse_sso_claims(profile)

            logger.warning("sso_opaque_validation_failed", reason="userinfo_rejected", status_code=res.status_code)
            raise AppException("Máy chủ SSO từ chối mã xác thực.", code="invalid_token", status_code=401)
    except AppException:
        raise
    except Exception as exc:
        logger.warning("sso_opaque_validation_failed", reason="userinfo_unreachable", error=str(exc))
        raise AppException("Không thể xác thực mã token với máy chủ SSO.", code="invalid_token", status_code=401)
