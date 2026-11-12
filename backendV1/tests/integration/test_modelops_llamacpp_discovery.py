"""Real admin API/DB; a llama.cpp host answers OpenAI routes and native /props."""

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
SECRET = "llamacpp-native-test-secret"
ADMIN = AuthActor(username="admin", actor_id="admin", roles=["AI.Admin"])
MODEL_ID = "../models/Qwen3-8B-Q4_K_M.gguf"


@pytest.fixture
def upstream():
    requests = []

    def handle(request):
        requests.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(404, json={"error": "not found"})
        if request.url.path == "/props":
            return httpx.Response(
                200,
                json={
                    "default_generation_settings": {"n_ctx": 32768},
                    "total_slots": 4,
                    "model_path": MODEL_ID,
                },
            )
        return httpx.Response(200, json={"data": [{"id": MODEL_ID}]})

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
            "name": "llama.cpp local",
            "base_url": "http://127.0.0.1:8080/v1",
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


def test_props_context_reaches_the_snapshot_and_the_imported_model(client, upstream):
    connection_id = setup_connection(client)
    tested = client.post(API + f"/connections/{connection_id}/test", json={})
    assert tested.status_code == 200, tested.text
    body = tested.json()
    assert body["ok"] is True and body["check_id"]
    assert SECRET not in tested.text
    assert [(row["id"], row["context_window_tokens"]) for row in body["model_metadata"]] == [
        (MODEL_ID, 32768)
    ]
    assert [(request.method, request.url.path) for request in upstream] == [
        ("GET", "/v1/models"),
        ("GET", "/api/tags"),
        ("GET", "/props"),
    ]

    added = client.post(
        API + f"/connections/{connection_id}/models",
        json={
            "model_name": MODEL_ID,
            "capabilities": ["chat"],
            "discovery_check_id": body["check_id"],
        },
    )
    assert added.status_code == 201, added.text
    model = added.json()
    assert model["capacity_status"] == "configured"
    assert model["capacity_basis"] == "server_reported"
    assert model["token_limits"]["context_window_tokens"] == 32768
    assert model["token_limits"]["max_output_tokens"] is None
    assert model["field_sources"]["context_window_tokens"] == "server_reported"
    # The context is declared by the server; the output budget stays an application default.
    budget = model["operational_budgets"]["chat"]
    assert budget["status"] == "provisional"
    assert budget["token_limits"]["context_window_tokens"] == 32768
    assert budget["sources"]["max_output_tokens"] == "application_default"
