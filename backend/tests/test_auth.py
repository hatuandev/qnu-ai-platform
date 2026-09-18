"""Tests for Dev Access Gate Authentication endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
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
