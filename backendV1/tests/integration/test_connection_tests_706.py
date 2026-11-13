"""Saved-key diagnostics with real persistence, HTTP authorization and upstream contracts."""

from urllib.parse import urlsplit

import httpx
import pytest

from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient
from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.diagnostics.router import get_diagnostic_client
from qnu.main import app

API = "/platform/v1alpha1/modelops"
# OpenAI-compatible hosts also receive best-effort native context probes after discovery.
DISCOVERY_ROUTES = [("GET", "/v1/models"), ("GET", "/api/tags"), ("GET", "/props")]


@pytest.fixture
def setup(client):
    app.dependency_overrides[get_actor] = lambda: AuthActor(
        username="review", actor_id="review", roles=["AI.Admin"]
    )
    created = client.post(
        API + "/connections",
        json={
            "name": "Connection test",
            "base_url": "https://test.example/v1",
            "timeout_seconds": 120,
        },
    )
    assert created.status_code == 201, created.text
    cid = created.json()["id"]
    keys = []
    for name in ["first", "second"]:
        response = client.post(
            f"{API}/providers/{cid}/keys", json={"name": name, "secret": "synthetic-" + name}
        )
        assert response.status_code == 201, response.text
        keys.append(response.json()["id"])
    state = {"seen": [], "routes": [], "status": 200, "action": None}

    async def upstream(request):
        state["seen"].append(request.headers.get("authorization"))
        state["routes"].append((request.method, urlsplit(str(request.url)).path))
        if state["action"]:
            await state["action"]()
        return httpx.Response(state["status"], json={"data": [{"id": "test-model"}]})

    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(upstream)
    )
    yield cid, keys, state
    app.dependency_overrides.pop(get_diagnostic_client, None)


def test_exact_second_key_history_and_refresh(client, setup):
    cid, keys, state = setup
    for key_id in keys:
        result = client.post(f"{API}/connections/{cid}/test", json={"key_id": key_id})
        assert result.status_code == 200, result.text
        assert result.json()["key_id"] == key_id
        assert result.json()["ok"] is True
    assert state["seen"] == ["Bearer synthetic-first"] * 3 + ["Bearer synthetic-second"] * 3
    assert state["routes"] == DISCOVERY_ROUTES * 2
    checks = client.get(f"{API}/providers/{cid}/diagnostics").json()["checks"]
    assert [check["key_id"] for check in checks] == list(reversed(keys))
    assert all(check["configuration_status"] == "current" for check in checks)
    row = client.get(f"{API}/connections/{cid}").json()
    assert row["last_probe_status"] == "success" and row["last_probe_at"]
    assert "synthetic-" not in client.get(f"{API}/providers/{cid}/diagnostics").text


def test_other_connection_key_cannot_be_used(client, setup):
    _cid, keys, state = setup
    other = client.post(
        API + "/connections",
        json={"name": "Other connection", "base_url": "https://other.example/v1"},
    ).json()["id"]
    response = client.post(f"{API}/connections/{other}/test", json={"key_id": keys[1]})
    assert response.status_code == 404
    assert state["seen"] == []


def test_revoked_key_is_rejected_without_fallback(client, setup):
    cid, keys, state = setup
    assert (
        client.post(
            f"{API}/providers/{cid}/keys/{keys[1]}/revoke", json={"reason": "Regression test"}
        ).status_code
        == 200
    )
    response = client.post(f"{API}/connections/{cid}/test", json={"key_id": keys[1]})
    assert response.status_code == 409, response.text
    assert state["seen"] == []


def test_temporary_key_does_not_mark_saved_keys_verified(client, setup):
    cid, _, state = setup
    response = client.post(f"{API}/connections/{cid}/test", json={"api_key": "temporary-test-key"})
    assert response.status_code == 200 and response.json()["ok"]
    assert response.json()["check_id"] is None
    assert state["seen"] == ["Bearer temporary-test-key"] * 3
    assert state["routes"] == DISCOVERY_ROUTES
    assert client.get(f"{API}/providers/{cid}/diagnostics").json()["checks"] == []


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_failures_persist_as_failures(client, setup, status):
    cid, keys, state = setup
    state["status"] = status
    response = client.post(f"{API}/connections/{cid}/test", json={"key_id": keys[1]})
    assert response.status_code == 200 and response.json()["ok"] is False
    assert response.json()["http_status"] == status
    assert client.get(f"{API}/connections/{cid}").json()["last_probe_status"] == "failed"


def test_key_revocation_during_check_cannot_persist_success(client, setup):
    cid, keys, state = setup

    async def revoke():
        from qnu.domains.modelops.models import ProviderKey
        from qnu.platform.database import AsyncSessionFactory

        async with AsyncSessionFactory() as db:
            key = await db.get(ProviderKey, keys[1])
            key.status = "revoked"
            await db.commit()

    state["action"] = revoke
    response = client.post(f"{API}/connections/{cid}/test", json={"key_id": keys[1]})
    assert response.status_code == 409
    assert client.get(f"{API}/providers/{cid}/diagnostics").json()["checks"] == []


def test_non_admin_cannot_run_saved_or_temporary_key_test(client, setup):
    cid, keys, state = setup
    app.dependency_overrides[get_actor] = lambda: AuthActor(
        username="member", actor_id="member", roles=[], permissions=[]
    )
    for body in [{"key_id": keys[0]}, {"api_key": "test"}]:
        assert client.post(f"{API}/connections/{cid}/test", json=body).status_code == 403
    assert state["seen"] == []
