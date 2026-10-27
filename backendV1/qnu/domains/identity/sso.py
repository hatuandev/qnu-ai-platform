"""Validate JWT signatures against server-configured SSO issuer, audience and JWKS."""

from __future__ import annotations

import asyncio
import time

import httpx
import jwt

from qnu.domains.identity.actor import AuthActor
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException

_cache: tuple[str, float, dict] = ("", 0.0, {})


async def _keys(url: str, force: bool = False) -> dict:
    global _cache
    if not force and _cache[0] == url and _cache[1] > time.monotonic():
        return _cache[2]
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        keys = {
            key["kid"]: key
            for key in data["keys"]
            if key.get("kty") == "RSA"
            and key.get("use", "sig") == "sig"
            and key.get("alg", "RS256") == "RS256"
            and isinstance(key.get("kid"), str)
        }
        if not keys:
            raise ValueError("Empty signing key set")
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise AppException(
            "Không tải được khóa xác thực SSO.", code="sso_unavailable", status_code=503
        ) from exc
    _cache = (url, time.monotonic() + get_settings().SSO_JWKS_CACHE_SECONDS, keys)
    return keys


def _extract_claims(payload: dict, *keys: str) -> list[str]:
    results: list[str] = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            for part in value.replace(",", " ").split():
                if part and part not in results:
                    results.append(part)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip() and item.strip() not in results:
                    results.append(item.strip())
    return results


async def validate_sso_token(token: str) -> AuthActor:
    settings = get_settings()
    if not settings.SSO_ENABLED or not settings.SSO_AUTHORITY or not settings.SSO_JWKS_URL:
        raise AppException(
            "SSO chưa được cấu hình đầy đủ.", code="sso_unconfigured", status_code=503
        )
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise jwt.InvalidTokenError("Unsupported signing algorithm")
        keys = await _keys(settings.SSO_JWKS_URL)
        if header["kid"] not in keys:
            keys = await _keys(settings.SSO_JWKS_URL, force=True)
        key = jwt.PyJWK.from_dict(keys[header["kid"]]).key
        payload = await asyncio.to_thread(
            jwt.decode,
            token,
            key,
            algorithms=["RS256"],
            audience=settings.SSO_AUDIENCE,
            issuer=settings.SSO_AUTHORITY,
            options={"require": ["sub", "iss", "aud", "exp"]},
        )
        if not isinstance(payload["sub"], str) or not payload["sub"].strip():
            raise jwt.InvalidTokenError("Missing subject")
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise AppException(
            "Token SSO không hợp lệ hoặc đã hết hạn.", code="invalid_token", status_code=401
        ) from exc

    roles = _extract_claims(payload, "roles", "role")
    permissions = _extract_claims(payload, "permissions", "permission")
    raw_user_type = payload.get("user_type") or payload.get("userType") or payload.get("usertype")
    user_type = str(raw_user_type).strip().lower() if raw_user_type else "staff"
    primary_role = roles[0] if roles else "staff"

    return AuthActor(
        actor_id=payload["sub"],
        username=payload.get("preferred_username") or payload["sub"],
        display_name=payload.get("name") or "Người dùng",
        email=payload.get("email"),
        user_type=user_type,
        role=primary_role,
        roles=roles if roles else [primary_role],
        permissions=permissions,
    )
