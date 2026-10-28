"""Seed identities authenticate through HTTP without inheriting platform admin."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from qnu.domains.identity import dev_accounts
from qnu.main import app
from qnu.platform.config import get_settings


@pytest.fixture
def local_accounts(monkeypatch, tmp_path):
    path = tmp_path / "accounts.json"
    path.write_text(json.dumps({"ctsv.user": hashlib.sha256(b"local-user-key").hexdigest()}))
    monkeypatch.setattr(dev_accounts, "ACCOUNTS_PATH", path)
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()


def test_seed_login_has_no_platform_privileges(local_accounts):
    with TestClient(app) as client:
        login = client.post("/platform/v1alpha1/auth/login", json={"access_key": "local-user-key"})
        assert login.status_code == 200
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        actor = client.get("/platform/v1alpha1/auth/me", headers=headers).json()["actor"]
        assert actor["actor_id"] == "act_dev_ctsv_user"
        assert actor["display_name"] == "Người dùng CTSV (thử nghiệm)"
        assert actor["permissions"] == []
        assert "AI.Admin" not in actor["roles"]
        assert (
            client.get("/platform/v1alpha1/modelops/providers", headers=headers).status_code == 403
        )
        assert (
            client.post(
                "/platform/v1alpha1/workspaces",
                headers=headers,
                json={"code": "forbidden", "name": "Forbidden"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/platform/v1alpha1/auth/login", json={"access_key": "wrong-key"}
            ).status_code
            == 401
        )


def test_seed_accounts_are_disabled_in_production(local_accounts, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    with TestClient(app) as client:
        assert (
            client.post(
                "/platform/v1alpha1/auth/login", json={"access_key": "local-user-key"}
            ).status_code
            == 403
        )


def test_invalid_registry_is_reported_as_configuration_error(local_accounts):
    local_accounts.write_text("invalid json")
    with TestClient(app) as client:
        response = client.post(
            "/platform/v1alpha1/auth/login", json={"access_key": "local-user-key"}
        )
        assert response.status_code == 503
        assert response.json()["code"] == "dev_accounts_unavailable"
