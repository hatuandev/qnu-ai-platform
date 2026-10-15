"""Explicit production Dev Access Gate must never imply anonymous admin access."""

from datetime import timedelta
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core import security
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.modules.auth import dependencies, dev_access, router

ORIGIN = "https://demo.example.org"
PASSWORD = "test-only-long-password-not-for-deployment"


def production_settings(**overrides: object) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "test-signing-key-" * 4,
        "INTERNAL_API_KEY": "test-internal-key-" * 4,
        "PROVIDER_ENCRYPTION_KEY": "test-provider-key-" * 4,
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/isolated",
        "S3_SECRET_KEY": "test-storage-secret",
        "SSO_ENABLED": False,
        "DEV_AUTH_ENABLED": True,
        "DEV_AUTH_ALLOW_IN_PRODUCTION": True,
        "DEV_ACCESS_PASSWORD": PASSWORD,
        "ALLOWED_ORIGINS": [ORIGIN],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_explicit_production_password_gate_without_sso() -> None:
    assert production_settings().DEV_AUTH_ENABLED


def test_production_password_gate_requires_second_opt_in() -> None:
    with pytest.raises(ValueError):
        production_settings(
            DEV_AUTH_ALLOW_IN_PRODUCTION=False,
            SSO_ENABLED=True,
            SSO_AUTHORITY="https://sso.example.org",
        )


@pytest.mark.parametrize("field,value", [("SECRET_KEY", "too-short"), ("JWT_ALGORITHM", "HS384")])
def test_production_gate_requires_strong_signing_configuration(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        production_settings(**{field: value})


@pytest.mark.parametrize("password", ["", "   ", "short-password", "QNU@2026"])
def test_production_gate_rejects_weak_password(password: str) -> None:
    with pytest.raises(ValueError):
        production_settings(DEV_ACCESS_PASSWORD=password)


@pytest.mark.parametrize("origins", [["*"], [], ["http://demo.example.org"], [ORIGIN + "/path"]])
def test_production_gate_requires_exact_https_origins(origins: list[str]) -> None:
    with pytest.raises(ValueError):
        production_settings(ALLOWED_ORIGINS=origins)


@pytest.fixture
def auth_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    # Copy bypasses config validation to exercise the real HTTP path even before the fix.
    current = get_settings().model_copy(
        update={
            "ENVIRONMENT": "production",
            "DEV_AUTH_ENABLED": True,
            "DEV_AUTH_ALLOW_IN_PRODUCTION": True,
            "DEV_ACCESS_PASSWORD": PASSWORD,
            "SSO_ENABLED": False,
            "ALLOWED_ORIGINS": [ORIGIN],
        }
    )
    monkeypatch.setattr(router, "get_settings", lambda: current)
    monkeypatch.setattr(dependencies, "get_settings", lambda: current)
    monkeypatch.setattr(security, "settings", current)
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router.router)

    @application.api_route("/protected", methods=["GET", "POST"])
    async def protected(actor=Depends(dependencies.get_current_actor)) -> dict[str, str]:
        return {"actor": actor.username}

    return application


@pytest.mark.asyncio
async def test_production_login_cookie_and_protected_api(
    auth_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Only the external throttle store is stubbed; signing, decoding and auth are real.
    if hasattr(router, "enforce_login_rate_limit"):
        monkeypatch.setattr(router, "enforce_login_rate_limit", AsyncMock())
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url=ORIGIN) as client:
        assert (await client.get("/protected")).status_code == 401
        response = await client.post(
            "/auth/login", json={"access_key": PASSWORD}, headers={"Origin": ORIGIN}
        )
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
        assert (await client.get("/auth/me")).json()["authenticated"] is True
        assert (await client.get("/protected")).status_code == 200
        assert (
            await client.post("/protected", headers={"Origin": "https://evil.example"})
        ).status_code == 403
        assert (await client.post("/protected", headers={"Origin": ORIGIN})).status_code == 200
        logout = await client.post("/auth/logout", headers={"Origin": ORIGIN})
        assert logout.status_code == 200
        assert (await client.get("/protected")).status_code == 401


@pytest.mark.asyncio
async def test_arbitrary_signed_token_cannot_become_production_admin(auth_app: FastAPI) -> None:
    token = security.create_access_token("someone", {"role": "student"})
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url=ORIGIN) as client:
        response = await client.get("/protected", headers={"Cookie": f"qnu_session={token}"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_production_cookie_expiry_and_password_rotation(
    auth_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    if hasattr(router, "enforce_login_rate_limit"):
        monkeypatch.setattr(router, "enforce_login_rate_limit", AsyncMock())
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url=ORIGIN) as client:
        response = await client.post(
            "/auth/login", json={"access_key": PASSWORD}, headers={"Origin": ORIGIN}
        )
        assert response.status_code == 200
        token = response.cookies["qnu_session"]
        payload = jwt.decode(
            token, router.get_settings().SECRET_KEY, algorithms=["HS256"], audience="qnu-dev-access"
        )
        expired = security.create_access_token(
            "admin",
            {key: value for key, value in payload.items() if key not in ("exp", "iat")},
            timedelta(seconds=-5),
        )
        assert (
            await client.get("/protected", headers={"Authorization": f"Bearer {expired}"})
        ).status_code == 401
        monkeypatch.setattr(router.get_settings(), "DEV_ACCESS_PASSWORD", PASSWORD + "-rotated")
        assert (await client.get("/protected")).status_code == 401


@pytest.mark.asyncio
async def test_wrong_password_and_origin_are_rejected(
    auth_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    throttle = AsyncMock()
    monkeypatch.setattr(router, "enforce_login_rate_limit", throttle)
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url=ORIGIN) as client:
        for origin in (None, "https://evil.example"):
            headers = {"Origin": origin} if origin else {}
            response = await client.post(
                "/auth/login", json={"access_key": PASSWORD}, headers=headers
            )
            assert response.status_code == 403
        throttle.assert_not_awaited()
        response = await client.post(
            "/auth/login", json={"access_key": "wrong"}, headers={"Origin": ORIGIN}
        )
        assert response.status_code == 401
        assert "set-cookie" not in response.headers
        assert (await client.get("/auth/me")).json()["authenticated"] is False


@pytest.mark.asyncio
async def test_switching_off_gate_rejects_existing_cookie(
    auth_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(router, "enforce_login_rate_limit", AsyncMock())
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url=ORIGIN) as client:
        assert (
            await client.post(
                "/auth/login", json={"access_key": PASSWORD}, headers={"Origin": ORIGIN}
            )
        ).status_code == 200
        monkeypatch.setattr(router.get_settings(), "DEV_AUTH_ALLOW_IN_PRODUCTION", False)
        assert (await client.get("/protected")).status_code == 401
        assert (await client.get("/auth/me")).json()["authenticated"] is False
        assert (
            await client.post(
                "/auth/login", json={"access_key": PASSWORD}, headers={"Origin": ORIGIN}
            )
        ).status_code == 403


@pytest.mark.asyncio
async def test_redis_failure_blocks_login_without_cookie(
    auth_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    from redis.exceptions import ConnectionError

    client = AsyncMock()
    client.eval.side_effect = ConnectionError("isolated test failure")
    monkeypatch.setattr(dev_access, "get_redis_client", lambda: client)
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url=ORIGIN) as browser:
        response = await browser.post(
            "/auth/login", json={"access_key": PASSWORD}, headers={"Origin": ORIGIN}
        )
        assert response.status_code == 503
        assert response.json()["code"] == "auth_throttle_unavailable"
        assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    "claim,value",
    [
        ("iss", "other-service"),
        ("aud", "other-purpose"),
        ("token_use", "other-token"),
        ("sub", "student"),
        ("session_version", "stale"),
    ],
)
@pytest.mark.asyncio
async def test_wrong_scope_or_signature_is_rejected(
    auth_app: FastAPI, claim: str, value: str
) -> None:
    settings = router.get_settings()
    token, _ = dev_access.production_session_token(
        settings, dependencies.AuthActor(username="admin")
    )
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=["HS256"], audience="qnu-dev-access"
    )
    payload[claim] = value
    changed = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url=ORIGIN) as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {changed}"})
        assert response.status_code == 401
