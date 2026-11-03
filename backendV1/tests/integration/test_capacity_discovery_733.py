"""Discovery metadata reaches the audited admin API; secrets and absent limits do not."""

import os

import httpx
import pytest

if not os.environ.get("TEST_DATABASE_URL"):
    pytest.skip("Isolated PostgreSQL required", allow_module_level=True)

from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient
from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.diagnostics.router import get_diagnostic_client
from qnu.main import app

API = "/platform/v1alpha1/modelops"
ADMIN = AuthActor(username="capacity-admin", actor_id="capacity-admin", roles=["AI.Admin"])
ROWS = [
    {"id": "bge-m3", "max_model_len": 8192, "embedding_dimension": 1024},
    {"id": "bge-reranker-v2-m3", "max_model_len": 8192},
    {"id": "qwen3.8-27b-q4", "max_model_len": 131072, "max_output_tokens": 16384},
    {"id": "nemotron-parse", "max_model_len": 16384, "max_output_tokens": 8192},
]


@pytest.fixture
def setup(client):
    app.dependency_overrides[get_actor] = lambda: ADMIN
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"data": ROWS})

    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(respond)
    )
    result = client.post(
        API + "/connections",
        json={"name": "Capacity server", "family": "qnu", "base_url": "https://models.example/v1"},
    )
    assert result.status_code == 201
    cid = result.json()["id"]
    key = client.post(
        API + f"/providers/{cid}/keys",
        json={"name": "Test key", "secret": "test-only-capacity-secret"},
    )
    assert key.status_code == 201
    try:
        yield cid, key.json()["id"], requests
    finally:
        app.dependency_overrides.pop(get_diagnostic_client, None)


def discover(client, cid, path="discover"):
    suffix = f"/connections/{cid}/test" if path == "test" else f"/providers/{cid}/discover"
    response = client.post(API + suffix, json={})
    assert response.status_code == 200, response.text
    return response.json()


def add(client, cid, name, caps, **extra):
    r = client.post(
        API + f"/connections/{cid}/models", json={"model_name": name, "capabilities": caps, **extra}
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_add_model_fetches_metadata_without_capacity_fields(client, setup):
    cid, _, requests = setup
    model = add(client, cid, "qwen3.8-27b-q4", ["chat"])
    assert len(requests) == 1
    assert model["capacity_basis"] == "server_reported"
    assert model["token_limits"]["max_output_tokens"] == 16384
    assert model["token_limits"]["context_window_tokens"] == 131072


def test_unlisted_model_keeps_unknown_capacity_after_successful_discovery(client, setup):
    cid, _, requests = setup
    model = add(client, cid, "private-model", ["chat"])
    assert len(requests) == 1
    assert model["token_limits"] is None
    assert model["operational_budgets"]["chat"]["status"] == "provisional"


@pytest.mark.parametrize("status", [404, 503])
def test_optional_discovery_failure_still_allows_manual_model_id(client, setup, status):
    cid, _, _ = setup
    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(status))
    )
    model = add(client, cid, "unlisted-chat", ["chat"])
    assert model["token_limits"] is None
    assert model["operational_budgets"]["chat"]["status"] == "provisional"


def sync(client, cid, check, names):
    return client.post(
        API + f"/connections/{cid}/sync-capacity", json={"check_id": check, "model_names": names}
    )


@pytest.mark.parametrize("path", ["discover", "test"])
def test_discovery_preview_and_import_all_capacities(client, setup, path):
    cid, _, requests = setup
    check = discover(client, cid, path)
    check_id = check.get("check_id") or check["id"]
    assert check["model_metadata"][0] == {
        "id": "bge-m3",
        "context_window_tokens": 8192,
        "max_output_tokens": None,
        "embedding_dimension": 1024,
    }
    assert "test-only-capacity-secret" not in str(check)
    assert client.get(API + f"/connections/{cid}/models").json() == []
    for row, caps in zip(ROWS, [["embedding"], ["rerank"], ["chat"], ["ocr"]], strict=True):
        model = add(client, cid, row["id"], caps, discovery_check_id=check_id)
        assert model["capacity_basis"] == "server_reported"
        assert model["token_limits"]["context_window_tokens"] == row["max_model_len"]
        assert model["token_limits"]["max_input_tokens"] is None
        assert model["token_limits"]["max_output_tokens"] == row.get("max_output_tokens")
        assert model["token_limits"]["ocr_page_input"] is None
        assert model["embedding_dimension"] == row.get("embedding_dimension")
    assert len(requests) == 1 and requests[0].method == "GET"


def test_sync_preserves_ocr_input_overrides_and_is_idempotent(client, setup):
    cid, _, _ = setup
    ocr = {
        "max_image_width": 1664,
        "max_image_height": 2048,
        "input_tokens_upper_bound": 4096,
        "prompt_sha256": "a" * 64,
    }
    add(
        client,
        cid,
        "nemotron-parse",
        ["ocr"],
        token_limits={
            "context_window_tokens": 16384,
            "max_output_tokens": 4096,
            "ocr_page_input": ocr,
        },
    )
    add(client, cid, "bge-reranker-v2-m3", ["rerank"], token_limits={"max_input_tokens": 1024})
    check = discover(client, cid)
    for _ in range(2):
        response = sync(client, cid, check["id"], ["nemotron-parse", "bge-reranker-v2-m3"])
        assert response.status_code == 200, response.text
    models = {row["model_name"]: row for row in response.json()}
    assert models["nemotron-parse"]["token_limits"]["ocr_page_input"] == ocr
    assert models["nemotron-parse"]["token_limits"]["max_output_tokens"] == 8192
    assert models["bge-reranker-v2-m3"]["token_limits"]["max_input_tokens"] == 1024
    events = client.get(API + "/events").json()
    assert len([e for e in events if e["action"] == "provider.capacity.synced"]) == 2


def test_conflicting_capacity_rolls_back_the_whole_selection(client, setup):
    cid, _, _ = setup
    first = add(
        client,
        cid,
        "qwen3.8-27b-q4",
        ["chat"],
        token_limits={"context_window_tokens": 262144, "max_input_tokens": 200000},
    )
    other = add(
        client,
        cid,
        "nemotron-parse",
        ["ocr"],
        token_limits={"context_window_tokens": 16384, "max_output_tokens": 4096},
    )
    check = discover(client, cid)
    response = sync(client, cid, check["id"], ["nemotron-parse", "qwen3.8-27b-q4"])
    assert response.status_code == 409 and response.json()["code"] == "discovery_capacity_conflict"
    for model in [first, other]:
        current = client.get(API + f"/providers/{model['id']}").json()
        assert current["token_limits"] == model["token_limits"]


@pytest.mark.parametrize("change", ["endpoint", "key", "newer-check"])
def test_stale_discovery_cannot_be_applied(client, setup, change):
    cid, key_id, _ = setup
    model = add(client, cid, "qwen3.8-27b-q4", ["chat"])
    check = discover(client, cid)
    if change == "endpoint":
        assert client.delete(API + f"/connections/{cid}/models/{model['id']}").status_code == 204
        assert (
            client.patch(
                API + f"/connections/{cid}", json={"base_url": "https://other.example/v1"}
            ).status_code
            == 200
        )
    elif change == "key":
        assert (
            client.post(API + f"/providers/{cid}/keys/{key_id}/revoke", json={}).status_code == 200
        )
    else:
        discover(client, cid)
    response = sync(client, cid, check["id"], ["qwen3.8-27b-q4"])
    assert response.status_code == 409 and response.json()["code"] == "discovery_snapshot_stale"


def test_dimension_changes_require_review_and_foreign_snapshots_are_rejected(client, setup):
    cid, _, _ = setup
    add(client, cid, "bge-m3", ["embedding"], embedding_dimension=768)
    check = discover(client, cid)
    assert (
        sync(client, cid, check["id"], ["bge-m3"]).json()["code"] == "discovery_dimension_conflict"
    )
    assert sync(client, cid, check["id"], ["not-registered"]).status_code == 409
    assert sync(client, cid, "diag_foreign", ["bge-m3"]).status_code == 409


def test_sync_and_import_are_admin_only(client, setup):
    cid, _, _ = setup
    check = discover(client, cid)
    app.dependency_overrides[get_actor] = lambda: AuthActor(
        username="member", actor_id="member", roles=[]
    )
    assert sync(client, cid, check["id"], ["bge-m3"]).status_code == 403
    assert (
        client.post(
            API + f"/connections/{cid}/models",
            json={
                "model_name": "bge-m3",
                "capabilities": ["embedding"],
                "discovery_check_id": check["id"],
            },
        ).status_code
        == 403
    )


def test_same_snapshot_restores_a_cleared_dimension_with_audit(client, setup):
    cid, _, _ = setup
    check = discover(client, cid)
    model = add(client, cid, "bge-m3", ["embedding"], discovery_check_id=check["id"])
    assert (
        client.patch(
            API + f"/providers/{model['id']}", json={"embedding_dimension": None}
        ).status_code
        == 200
    )
    response = sync(client, cid, check["id"], ["bge-m3"])
    assert response.status_code == 200
    assert response.json()[0]["embedding_dimension"] == 1024
    events = client.get(API + "/events").json()
    assert len([e for e in events if e["action"] == "provider.capacity.synced"]) == 1
