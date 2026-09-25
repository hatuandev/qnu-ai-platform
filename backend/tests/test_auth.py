"""Tests for Dev Access Gate Authentication endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app

settings = get_settings()


@pytest.mark.asyncio
async def test_auth_login_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/platform/v1alpha1/auth/login",
            json={"access_key": settings.DEV_ACCESS_PASSWORD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["actor"]["role"] == "admin"
        assert "qnu_session" in resp.cookies

        # Test /me with cookie
        me_resp = await client.get("/platform/v1alpha1/auth/me")
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["authenticated"] is True
        assert me_data["actor"]["username"] == "admin"

        # Test /logout
        logout_resp = await client.post("/platform/v1alpha1/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["status"] == "logged_out"

        # Verify /me after logout is unauthenticated
        after_logout_me = await client.get("/platform/v1alpha1/auth/me")
        assert after_logout_me.status_code == 200
        assert after_logout_me.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_auth_login_invalid_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/platform/v1alpha1/auth/login",
            json={"access_key": "wrong_password_123"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "Mật khẩu truy cập Dev" in data["detail"]


@pytest.mark.asyncio
async def test_auth_login_rejects_when_password_unconfigured():
    """Login must fail closed (503) instead of comparing against an empty password."""
    from unittest.mock import patch

    import app.modules.auth.router as auth_router

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(auth_router.settings, "DEV_ACCESS_PASSWORD", ""):
            resp = await client.post(
                "/platform/v1alpha1/auth/login",
                json={"access_key": "   "},
            )
            assert resp.status_code == 503
            assert resp.json().get("code") == "auth_not_configured"




@pytest.mark.asyncio
async def test_api_protection_rejects_unauthenticated_request_with_enforced_auth():
    """Admin APIs must return 401 when unauthenticated and auth enforcement is requested."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/platform/v1alpha1/assistants",
            headers={"x-enforce-auth": "true"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data.get("code") == "unauthorized"


@pytest.mark.asyncio
async def test_api_protection_rejects_malformed_token():
    """Admin APIs must return 401 when given an invalid Bearer token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/platform/v1alpha1/assistants",
            headers={"authorization": "Bearer invalid_tampered_token_xyz"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data.get("code") == "invalid_token"



@pytest.mark.asyncio
async def test_api_protection_allows_authenticated_session():
    """Admin APIs succeed when authenticated via Dev Access Gate session cookie."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Login
            login_resp = await client.post(
                "/platform/v1alpha1/auth/login",
                json={"access_key": settings.DEV_ACCESS_PASSWORD},
            )
            assert login_resp.status_code == 200
            token = login_resp.cookies.get("qnu_session")

            # Step 2: Access admin API with session cookie
            resp = await client.get(
                "/platform/v1alpha1/assistants",
                headers={
                    "x-enforce-auth": "true",
                    "Cookie": f"qnu_session={token}",
                },
            )
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_assistant_chat_endpoint_is_public():
    """Chat endpoint must remain public for candidates/students and widget embeds."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Sending a chat request with x-enforce-auth must NOT fail with 401 Unauthorized
            resp = await client.post(
                "/platform/v1alpha1/assistants/qnu_admissions/chat",
                headers={"x-enforce-auth": "true"},
                json={"message": "Xin chào trường Đại học Quy Nhơn", "stream": False},
            )
            # Must not be 401 Unauthorized (it may be 404 because assistant is not in DB)
            assert resp.status_code != 401
    finally:
        app.dependency_overrides.pop(get_db, None)


