"""Real admin API + DB + diagnostic HTTP adapter, with fake upstream only."""

import os

import httpx
import pytest

if not os.environ.get("TEST_DATABASE_URL", "").strip():
    pytest.skip("NOT RUN: isolated PostgreSQL required", allow_module_level=True)

from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient
from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.diagnostics.router import get_diagnostic_client
from qnu.main import app

API = "/platform/v1alpha1/modelops"
SECRET = "sk-test-diagnostic-private"
ADMIN = AuthActor(username="admin", actor_id="admin", roles=["AI.Admin"])
MEMBER = AuthActor(
    username="member", actor_id="member", roles=["staff"], permissions=["ai.models.view"]
)


@pytest.fixture
def upstream():
    requests = []
    response = {"status": 200, "body": {"data": [{"id": "listed-model"}]}, "headers": {}}

    def handle(request):
        requests.append(request)
        return httpx.Response(
            response["status"], json=response["body"], headers=response["headers"]
        )

    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(handle)
    )
    yield requests, response
    app.dependency_overrides.pop(get_diagnostic_client, None)


def setup_provider(client):
    app.dependency_overrides[get_actor] = lambda: ADMIN
    result = client.post(
        API + "/providers",
        json={
            "name": "Diagnostic provider",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.example/v1",
            "model_name": "configured-model",
            "capabilities": ["chat"],
        },
    )
    assert result.status_code == 201, result.text
    pid = result.json()["id"]
    key = client.post(API + f"/providers/{pid}/keys", json={"name": "test-key", "secret": SECRET})
    assert key.status_code == 201
    return pid, key.json()["id"]


def test_discovery_persists_a_safe_observation_without_changing_model(client, upstream):
    pid, _ = setup_provider(client)
    result = client.post(API + f"/providers/{pid}/discover")
    assert result.status_code == 200, result.text
    check = result.json()
    assert check["models"] == ["listed-model"] and check["outcome"] == "ok"
    assert SECRET not in result.text
    current = client.get(API + f"/providers/{pid}").json()
    assert current["model_name"] == "configured-model" and current["capacity_status"] == "unknown"
    history = client.get(API + f"/providers/{pid}/diagnostics")
    assert history.json()["checks"][0]["id"] == check["id"]
    assert "identity" not in history.text and SECRET not in history.text
    events = client.get(API + "/events").json()
    assert events[0]["action"] == "provider.diagnostic.discovery"
    assert upstream[0][0].headers["authorization"] == "Bearer " + SECRET


@pytest.mark.parametrize(
    "path,method", [("diagnostics", "get"), ("discover", "post"), ("probe", "post")]
)
def test_view_permission_cannot_read_or_run_admin_diagnostics(client, upstream, path, method):
    pid, _ = setup_provider(client)
    app.dependency_overrides[get_actor] = lambda: MEMBER
    options = {"json": {"capability": "chat"}} if path == "probe" else {}
    result = getattr(client, method)(API + f"/providers/{pid}/{path}", **options)
    assert result.status_code == 403
    assert upstream[0] == []


def test_upstream_auth_and_rate_limit_remain_failures_with_safe_retry_time(client, upstream):
    pid, _ = setup_provider(client)
    upstream[1].update(status=401, body={"error": {"message": SECRET}})
    auth = client.post(API + f"/providers/{pid}/probe", json={"capability": "chat"})
    assert auth.json()["outcome"] == "failed" and auth.json()["http_status"] == 401
    assert SECRET not in auth.text
    upstream[1].update(status=429, headers={"Retry-After": "15"})
    limited = client.post(API + f"/providers/{pid}/probe", json={"capability": "chat"})
    assert limited.json()["retry_after"] is not None
    assert len(upstream[0]) == 2


def test_configuration_and_key_rotation_invalidate_previous_results(client, upstream):
    pid, kid = setup_provider(client)
    client.post(API + f"/providers/{pid}/discover")
    client.patch(API + f"/providers/{pid}", json={"model_name": "new-model"})
    checks = client.get(API + f"/providers/{pid}/diagnostics").json()["checks"]
    assert checks[0]["configuration_status"] == "stale"
    client.post(API + f"/providers/{pid}/discover")
    rotated = client.post(
        API + f"/providers/{pid}/keys/{kid}/rotate",
        json={
            "name": "replacement",
            "secret": "sk-test-replacement-secret",
        },
    )
    assert rotated.status_code == 200
    assert all(
        c["configuration_status"] == "stale"
        for c in client.get(API + f"/providers/{pid}/diagnostics").json()["checks"]
    )


def test_disabled_and_wrong_capability_do_not_call_upstream(client, upstream):
    pid, _ = setup_provider(client)
    mismatch = client.post(API + f"/providers/{pid}/probe", json={"capability": "embedding"})
    assert mismatch.status_code == 409
    client.patch(API + f"/providers/{pid}", json={"is_active": False})
    disabled = client.post(API + f"/providers/{pid}/discover")
    assert disabled.status_code == 409 and upstream[0] == []


def test_missing_credentials_are_visible_and_not_verified(client, upstream):
    pid, kid = setup_provider(client)
    client.post(API + f"/providers/{pid}/keys/{kid}/revoke", json={})
    check = client.post(API + f"/providers/{pid}/probe", json={"capability": "chat"}).json()
    assert check["outcome"] == "failed" and check["code"] == "credentials_missing"
    assert upstream[0] == []


def test_changed_target_during_inference_does_not_get_a_current_success(client, upstream):
    from sqlalchemy import update

    from qnu.domains.modelops.models import Provider
    from qnu.platform.database import AsyncSessionFactory

    pid, _ = setup_provider(client)

    async def changed(request):
        async with AsyncSessionFactory() as db:
            await db.execute(
                update(Provider).where(Provider.id == pid).values(model_name="changed")
            )
            await db.commit()
        return httpx.Response(200, json={"data": [{"id": "old-target"}]})

    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(changed)
    )
    response = client.post(API + f"/providers/{pid}/discover")
    assert (
        response.status_code == 409
        and response.json()["code"] == "diagnostic_configuration_changed"
    )
    assert client.get(API + f"/providers/{pid}/diagnostics").json()["checks"] == []
