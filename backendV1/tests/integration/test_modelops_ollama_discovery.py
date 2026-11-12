"""Real admin API/DB; the Ollama host answers both OpenAI and native routes."""

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
SECRET = "ollama-native-test-secret"
ADMIN = AuthActor(username="admin", actor_id="admin", roles=["AI.Admin"])

CATALOG = {
    "data": [
        {"id": "qwen3:8b", "max_output_tokens": 8192},
        {"id": "bge-m3:latest", "embedding_dimension": 1024},
    ]
}


@pytest.fixture
def upstream():
    requests = []

    def handle(request):
        requests.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": "qwen3:8b"}, {"name": "bge-m3:latest"}]}
            )
        if request.url.path == "/api/show":
            info = (
                {"general.architecture": "qwen3", "qwen3.context_length": 40960}
                if b"qwen3" in request.content
                else {"bert.context_length": 8192}
            )
            return httpx.Response(200, json={"model_info": info})
        return httpx.Response(200, json=CATALOG)

    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(handle)
    )
    yield requests
    app.dependency_overrides.pop(get_diagnostic_client, None)


def setup_connection(client):
    app.dependency_overrides[get_actor] = lambda: ADMIN
    created = client.post(
        API + "/connections",
        json={
            "name": "Ollama local",
            "base_url": "http://127.0.0.1:11434/v1",
            "family": "custom",
        },
    )
    assert created.status_code == 201, created.text
    connection_id = created.json()["id"]
    key = client.post(
        API + f"/providers/{connection_id}/keys",
        json={"name": "local", "secret": SECRET},
    )
    assert key.status_code == 201
    return connection_id


def test_native_context_reaches_the_snapshot_and_the_imported_model(client, upstream):
    connection_id = setup_connection(client)
    tested = client.post(API + f"/connections/{connection_id}/test", json={})
    assert tested.status_code == 200, tested.text
    body = tested.json()
    assert body["ok"] is True and body["check_id"]
    assert SECRET not in tested.text
    assert [(row["id"], row["context_window_tokens"]) for row in body["model_metadata"]] == [
        ("qwen3:8b", 40960),
        ("bge-m3:latest", 8192),
    ]
    assert [(request.method, request.url.path) for request in upstream] == [
        ("GET", "/v1/models"),
        ("GET", "/api/tags"),
        ("POST", "/api/show"),
        ("POST", "/api/show"),
    ]

    added = client.post(
        API + f"/connections/{connection_id}/models",
        json={
            "model_name": "qwen3:8b",
            "capabilities": ["chat"],
            "discovery_check_id": body["check_id"],
        },
    )
    assert added.status_code == 201, added.text
    model = added.json()
    assert model["capacity_status"] == "configured"
    assert model["capacity_basis"] == "server_reported"
    assert model["token_limits"]["context_window_tokens"] == 40960
    assert model["token_limits"]["max_output_tokens"] == 8192
    assert model["field_sources"]["context_window_tokens"] == "server_reported"
    budget = model["operational_budgets"]["chat"]
    assert budget["status"] == "declared"
    assert budget["token_limits"]["context_window_tokens"] == 40960
    assert budget["token_limits"]["max_output_tokens"] == 8192
