"""Verify real RSA JWT signatures against controlled JWKS; no live SSO calls."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from qnu.domains.identity import sso
from qnu.main import app
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException


@pytest.fixture
def signed(monkeypatch):
    monkeypatch.setenv("SSO_ENABLED", "true")
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    monkeypatch.setenv("SSO_AUTHORITY", "https://sso.example.test")
    monkeypatch.setenv("SSO_JWKS_URL", "https://sso.example.test/jwks")
    get_settings.cache_clear()
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    jwk["kid"] = "test-key"

    async def keys(*args, **kwargs):
        return {"test-key": jwk}

    monkeypatch.setattr(sso, "_keys", keys)

    def sign(**changes):
        payload = {
            "sub": "Subject-CaseSensitive",
            "iss": "https://sso.example.test",
            "aud": "ai.api",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "roles": ["staff"],
            "permissions": ["ai.workspaces.view"],
        }
        payload.update(changes)
        return jwt.encode(payload, private, algorithm="RS256", headers={"kid": "test-key"})

    yield sign
    get_settings.cache_clear()


def test_valid_sso_is_not_reinterpreted_as_dev_token(signed):
    with TestClient(app) as client:
        response = client.get(
            "/platform/v1alpha1/auth/me", headers={"Authorization": "Bearer " + signed()}
        )
    assert response.status_code == 200
    actor = response.json()["actor"]
    assert actor["actor_id"] == "Subject-CaseSensitive"
    assert actor["roles"] == ["staff"]


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "other-api"},
        {"iss": "https://attacker.test"},
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
    ],
)
def test_sso_invalid_claims_are_rejected(signed, claims):
    with TestClient(app) as client:
        response = client.get(
            "/platform/v1alpha1/auth/me", headers={"Authorization": "Bearer " + signed(**claims)}
        )
    assert response.status_code == 401


def test_sso_infrastructure_error_stays_503(signed, monkeypatch):
    async def unavailable(*args, **kwargs):
        raise AppException("SSO unavailable", code="sso_unavailable", status_code=503)

    monkeypatch.setattr(sso, "_keys", unavailable)
    with TestClient(app) as client:
        response = client.get(
            "/platform/v1alpha1/auth/me", headers={"Authorization": "Bearer " + signed()}
        )
    assert response.status_code == 503


def test_sso_singular_role_permission_and_user_type_mapping(signed):
    token = signed(
        sub="Student-12345",
        role="student",
        roles=None,
        permission="ai.chat.access",
        permissions=None,
        user_type="Student",
    )
    with TestClient(app) as client:
        response = client.get(
            "/platform/v1alpha1/auth/me", headers={"Authorization": "Bearer " + token}
        )
    assert response.status_code == 200
    actor = response.json()["actor"]
    assert actor["actor_id"] == "Student-12345"
    assert actor["user_type"] == "student"
    assert actor["role"] == "student"
    assert actor["roles"] == ["student"]
    assert actor["permissions"] == ["ai.chat.access"]


def test_sso_array_claims_and_admin_role_mapping(signed):
    token = signed(
        sub="Admin-Staff-99",
        roles=["AI.Admin", "staff"],
        permissions=["ai.workspaces.manage", "ai.models.manage"],
        user_type="Staff",
    )
    with TestClient(app) as client:
        response = client.get(
            "/platform/v1alpha1/auth/me", headers={"Authorization": "Bearer " + token}
        )
    assert response.status_code == 200
    actor = response.json()["actor"]
    assert actor["actor_id"] == "Admin-Staff-99"
    assert actor["user_type"] == "staff"
    assert actor["role"] == "AI.Admin"
    assert actor["roles"] == ["AI.Admin", "staff"]
    assert "ai.workspaces.manage" in actor["permissions"]
    assert "ai.models.manage" in actor["permissions"]
