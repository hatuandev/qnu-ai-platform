"""HTTP-boundary review probes; fake credentials/upstream, no DB or live changes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qnu.api.dependencies import get_actor, get_db
from qnu.api.handlers import register_exception_handlers
from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.connections import service, testing
from qnu.domains.modelops.connections.router import router


@pytest.fixture
def probe(monkeypatch):
    state = SimpleNamespace(
        status=200,
        body={"data": [{"id": "sample-model"}]},
        raw=None,
        requests=[],
        options=[],
        active=True,
    )
    parent = SimpleNamespace(
        id="conn_review",
        base_url="https://provider.example/v1",
        extra_config={"connection_family": "custom"},
        timeout_seconds=37,
        is_active=True,
        model_name="",
        provider_type="openai_compatible",
        capabilities=[],
    )

    async def get_connection(*args, **kwargs):
        parent.is_active = state.active
        return parent

    monkeypatch.setattr(service, "get_connection", get_connection)
    monkeypatch.setattr(testing, "decrypt", lambda value: "synthetic-key-first")

    class FakeClient:
        def __init__(self, **kwargs):
            state.options.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, **kwargs):
            state.requests.append({"url": url, **kwargs})
            request = httpx.Request("GET", url)
            if state.raw is not None:
                return httpx.Response(state.status, content=state.raw, request=request)
            return httpx.Response(state.status, json=state.body, request=request)

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    key = SimpleNamespace(id="key-first", secret_encrypted="fake-encrypted", status="active")
    db = SimpleNamespace(
        scalars=AsyncMock(return_value=SimpleNamespace(first=lambda: key)),
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: parent)),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        add=Mock(),
    )
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_actor] = lambda: AuthActor(
        username="review-admin", actor_id="review-admin", roles=["AI.Admin"]
    )
    with TestClient(app) as client:
        yield client, state


def run(probe, body=None):
    client, _state = probe
    return client.post("/modelops/connections/conn_review/test", json=body or {})


@pytest.mark.parametrize("status", [404, 429, 500])
def test_http_error_is_not_reported_as_success(probe, status):
    probe[1].status = status
    response = run(probe)
    assert response.status_code == 200
    assert response.json()["ok"] is False


def test_non_json_200_is_not_a_verified_connection(probe):
    probe[1].raw = b"<html>Proxy sign in page</html>"
    assert run(probe).json()["ok"] is False


def test_malformed_model_list_is_not_success(probe):
    probe[1].body = {"error": "Backend unavailable"}
    assert run(probe).json()["ok"] is False


def test_tls_certificate_verification_is_enabled(probe):
    run(probe)
    assert probe[1].options[0].get("verify", True) is not False


def test_connection_timeout_configuration_is_used(probe):
    run(probe)
    assert probe[1].options[0]["timeout"] == 37


def test_disabled_connection_is_not_probed(probe):
    probe[1].active = False
    response = run(probe)
    assert response.status_code == 409
    assert probe[1].requests == []


@pytest.mark.parametrize("status,ok", [(200, True), (401, False), (403, False)])
def test_supported_basic_http_outcomes(probe, status, ok):
    probe[1].status = status
    assert run(probe).json()["ok"] is ok
