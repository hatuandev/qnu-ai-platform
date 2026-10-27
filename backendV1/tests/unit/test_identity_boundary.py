"""Authentication must reject disabled dev tokens and missing privilege claims."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from qnu.main import app
from qnu.platform.config import get_settings


@pytest.fixture(autouse=True)
def settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def token(**changes):
    now = datetime.now(UTC)
    payload = {
        "sub": "person",
        "actor_id": "Subject-A",
        "aud": "qnu-dev-access",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(changes)
    return jwt.encode(payload, get_settings().SECRET_KEY, algorithm="HS256")


def test_missing_token_does_not_implicitly_become_admin():
    with TestClient(app) as client:
        assert client.get("/platform/v1alpha1/auth/me").status_code == 401


@pytest.mark.parametrize("environment", ["development", "production"])
def test_disabled_dev_gate_rejects_previously_signed_token(monkeypatch, environment):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    signed = token(roles=["AI.Admin"], permissions=["ai.access.admin"])
    with TestClient(app) as client:
        response = client.get(
            "/platform/v1alpha1/auth/me", headers={"Authorization": f"Bearer {signed}"}
        )
    assert response.status_code == 401


def test_missing_roles_never_grants_admin():
    with TestClient(app) as client:
        response = client.get(
            "/platform/v1alpha1/auth/me", headers={"Authorization": f"Bearer {token()}"}
        )
    assert response.status_code == 200
    assert response.json()["actor"]["roles"] == []


def test_login_and_authenticated_identity(monkeypatch):
    monkeypatch.setenv("DEV_ACCESS_PASSWORD", "only-a-test-password")
    get_settings.cache_clear()
    with TestClient(app) as client:
        assert (
            client.post(
                "/platform/v1alpha1/auth/login", json={"access_key": "incorrect"}
            ).status_code
            == 401
        )
        logged_in = client.post(
            "/platform/v1alpha1/auth/login", json={"access_key": "only-a-test-password"}
        )
        assert logged_in.status_code == 200
        response = client.get(
            "/platform/v1alpha1/auth/me",
            headers={"Authorization": "Bearer " + logged_in.json()["access_token"]},
        )
        assert response.status_code == 200
