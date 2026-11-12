"""Observed output ceilings persist through the admin API without changing capacity."""

import json
import os

import httpx
import pytest

if not os.environ.get("TEST_DATABASE_URL", "").strip():
    pytest.skip("NOT RUN: isolated PostgreSQL required", allow_module_level=True)

from qnu.adapters.providers.openai_compatible import OpenAICompatibleChatModel
from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.resilience.execution import ManagedChatModel
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from qnu.ports.chat_model import ChatMessage

API = "/platform/v1alpha1"
ADMIN = AuthActor(username="observed-admin", actor_id="observed-admin", roles=["AI.Admin"])
MESSAGES = [ChatMessage("user", "synthetic test")]


def setup(client, *, max_output=8192):
    app.dependency_overrides[get_actor] = lambda: ADMIN
    ws = client.post(
        API + "/workspaces", json={"code": "observed-limit", "name": "Observed limit"}
    ).json()["id"]
    provider = client.post(
        API + "/modelops/providers",
        json={
            "name": "Observed provider",
            "provider_type": "local",
            "base_url": "https://provider.example/v1",
            "model_name": "observed-model",
            "capabilities": ["chat"],
            "token_limits": {
                "context_window_tokens": 32768,
                "max_input_tokens": 20000,
                "max_output_tokens": max_output,
            },
        },
    )
    assert provider.status_code == 201, provider.text
    pid = provider.json()["id"]
    assert (
        client.post(
            API + f"/modelops/providers/{pid}/keys",
            json={"name": "Runtime key", "secret": "observed-limit-test-secret"},
        ).status_code
        == 201
    )
    granted = client.put(
        API + f"/workspaces/{ws}/allowed-providers",
        json={"provider_ids": [pid], "defaults": {"chat": pid}},
    )
    assert granted.status_code == 200, granted.text
    client.put(API + f"/workspaces/{ws}/quota", json={"monthly_token_limit": 1000000})
    return ws, pid


def prepare(client, ws, pid):
    async def call():
        async with AsyncSessionFactory() as db:
            return await prepare_chat_request(
                db, ADMIN, ws, MESSAGES, provider_id=pid, max_output_tokens=None
            )

    return client.portal.call(call)


def chat(client, prepared, calls):
    def upstream(request):
        body = json.loads(request.content)
        calls.append(body["max_tokens"])
        if body["max_tokens"] > 4096:
            return httpx.Response(
                422,
                json={"error": {"code": "max_output_tokens_exceeded", "max_output_tokens": 4096}},
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 3},
            },
        )

    async def call():
        model = ManagedChatModel(OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream)))
        return await model.complete(MESSAGES, prepared)

    return client.portal.call(call)


def diagnostics(client, pid):
    response = client.get(API + f"/modelops/providers/{pid}/diagnostics")
    assert response.status_code == 200, response.text
    return response.json()["observed_output_limits"]


def test_observed_limit_is_visible_and_survives_a_new_runtime(client):
    ws, pid = setup(client)
    _, prepared, _ = prepare(client, ws, pid)
    assert prepared.max_output_tokens == 8192 and prepared.automatic_output_budget

    calls = []
    result = chat(client, prepared, calls)
    assert calls == [8192, 4096]
    assert result.content == "ok"
    assert result.budget_trace["output_limit_source"] == "observed_runtime"
    assert result.budget_trace["observed_output_limit"] == 4096

    current = client.get(API + f"/modelops/providers/{pid}").json()
    assert current["token_limits"]["max_output_tokens"] == 8192
    assert current["capacity_basis"] == "operator_configured"
    assert current["capacity_status"] == "configured"

    rows = diagnostics(client, pid)
    assert len(rows) == 1
    assert rows[0]["max_output_tokens"] == 4096
    assert rows[0]["source"] == "observed"
    assert rows[0]["configuration_status"] == "current"
    assert rows[0]["model_name"] == "observed-model"

    restarted_calls = []
    restarted = chat(client, prepared, restarted_calls)
    assert restarted_calls == [4096]
    assert restarted.budget_trace["output_limit_source"] == "observed_diagnostics"
    assert len(diagnostics(client, pid)) == 1


def test_changed_declared_capacity_marks_the_observation_stale(client):
    ws, pid = setup(client)
    _, prepared, _ = prepare(client, ws, pid)
    chat(client, prepared, [])
    assert diagnostics(client, pid)[0]["configuration_status"] == "current"

    patched = client.patch(
        API + f"/modelops/providers/{pid}",
        json={
            "token_limits": {
                "context_window_tokens": 32768,
                "max_input_tokens": 20000,
                "max_output_tokens": 16384,
            }
        },
    )
    assert patched.status_code == 200, patched.text
    assert diagnostics(client, pid)[0]["configuration_status"] == "stale"

    _, changed, _ = prepare(client, ws, pid)
    assert changed.max_output_tokens == 16384
    calls = []
    result = chat(client, changed, calls)
    assert calls == [16384, 4096]
    assert result.budget_trace["output_limit_source"] == "observed_runtime"
    rows = diagnostics(client, pid)
    assert [row["configuration_status"] for row in rows] == ["current", "stale"]
