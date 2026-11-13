"""Real admin HTTP/DB and managed runtime; only the provider HTTP transport is fake."""

import asyncio
import os
from datetime import UTC, datetime, timedelta

import httpx
import pytest

if not os.environ.get("TEST_DATABASE_URL", "").strip():
    pytest.skip("NOT RUN: isolated PostgreSQL required", allow_module_level=True)

from qnu.adapters.providers.embedding import ModelOpsEmbeddingModel
from qnu.adapters.providers.nemotron import NemotronOcrEngine
from qnu.adapters.providers.openai_compatible import OpenAICompatibleChatModel
from qnu.adapters.providers.reranker import ModelOpsReranker
from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.models import Provider, ProviderKey
from qnu.domains.modelops.resilience.execution import (
    ManagedChatModel,
    ManagedEmbeddingModel,
    ManagedOcrEngine,
    ManagedReranker,
)
from qnu.domains.modelops.resilience.key_pool import acquire, finish
from qnu.domains.modelops.resilience.schemas import ResiliencePolicy
from qnu.domains.modelops.resilience.service import LEASES_KEY
from qnu.domains.modelops.usage.service import usage_service
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage, ChatRequest
from qnu.ports.embedding_model import EmbeddingRequest
from qnu.ports.ocr_engine import OcrRequest
from qnu.ports.provider_execution import ProviderExecution
from qnu.ports.reranker import RerankRequest

API = "/platform/v1alpha1"
ADMIN = AuthActor(username="admin", actor_id="admin", roles=["AI.Admin"])
OUTSIDER = AuthActor(username="outsider", actor_id="other", roles=["staff"])
SECRETS = ["test-key-first-private", "test-key-second-private"]
MESSAGES = [ChatMessage("user", "synthetic test")]


def setup(client, *, two_keys=True):
    app.dependency_overrides[get_actor] = lambda: ADMIN
    ws = client.post(API + "/workspaces", json={"code": "pool-test", "name": "Pool test"}).json()[
        "id"
    ]
    providers, keys = [], []
    for index in range(2):
        result = client.post(
            API + "/modelops/providers",
            json={
                "name": f"Provider {index}",
                "provider_type": "local",
                "base_url": f"https://provider{index}.example/v1",
                "model_name": f"model-{index}",
                "capabilities": ["chat"],
                "token_limits": {
                    "context_window_tokens": 20000,
                    "max_input_tokens": 15000,
                    "max_output_tokens": 1000,
                },
            },
        )
        assert result.status_code == 201, result.text
        pid = result.json()["id"]
        providers.append(pid)
        own = []
        for n in range(2 if two_keys and index == 0 else 1):
            key = client.post(
                API + f"/modelops/providers/{pid}/keys",
                json={
                    "name": f"Key {n}",
                    "secret": SECRETS[n],
                    "priority": n + 1,
                },
            )
            assert key.status_code == 201
            own.append(key.json()["id"])
        keys.append(own)
    granted = client.put(API + "/modelops/defaults", json={"chat_provider_id": providers[0]})
    assert granted.status_code == 200, granted.text
    client.put(API + f"/workspaces/{ws}/quota", json={"monthly_token_limit": 100000})
    policy = ResiliencePolicy(key_pool_enabled=True, max_key_attempts=2)
    result = client.put(
        API + f"/modelops/providers/{providers[0]}/resilience", json=policy.model_dump()
    )
    assert result.status_code == 200, result.text
    return ws, providers, keys


def request(ws, pid):
    return ChatRequest(
        "https://provider0.example/v1",
        "model-0",
        100,
        5,
        "stale-credential-must-not-be-used",
        execution=ProviderExecution(ws, pid),
    )


def ok():
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 7},
        },
    )


@pytest.mark.parametrize("status", [401, 429])
def test_definite_rejection_rotates_and_cools_only_that_key(client, status):
    ws, providers, keys = setup(client)
    calls = []

    def upstream(req):
        calls.append(req)
        return (
            httpx.Response(status, headers={"Retry-After": "900"}, json={"error": SECRETS[0]})
            if len(calls) == 1
            else ok()
        )

    async def run():
        model = ManagedChatModel(OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream)))
        return await model.complete(MESSAGES, request(ws, providers[0]))

    assert client.portal.call(run).total_tokens == 7
    assert [r.headers["authorization"] for r in calls] == ["Bearer " + s for s in SECRETS]
    response = client.get(API + f"/modelops/providers/{providers[0]}/keys")
    state = {k["id"]: k for k in response.json()}
    assert state[keys[0][0]]["consecutive_failures"] == 1
    assert datetime.fromisoformat(state[keys[0][0]]["cooldown_until"]) > datetime.now(
        UTC
    ) + timedelta(seconds=890)
    assert state[keys[0][1]]["lease_until"] is None
    events = client.get(API + "/modelops/events").text
    assert all(s not in events + response.text for s in SECRETS)
    assert "provider.execution" in events


@pytest.mark.parametrize("status", [400, 403, 422, 500, 503])
def test_input_permission_and_ambiguous_failures_never_rotate_or_punish_keys(client, status):
    ws, providers, _ = setup(client)
    calls = []

    def upstream(req):
        calls.append(req)
        return httpx.Response(status, json={"error": "synthetic"})

    async def run():
        model = ManagedChatModel(OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream)))
        with pytest.raises(AppException):
            await model.complete(MESSAGES, request(ws, providers[0]))

    client.portal.call(run)
    assert len(calls) == 1
    keys = client.get(API + f"/modelops/providers/{providers[0]}/keys").json()
    assert all(
        k["consecutive_failures"] == 0 and k["cooldown_until"] is None and k["lease_until"] is None
        for k in keys
    )


def test_concurrent_workers_cannot_share_key_and_expired_owner_cannot_release_new_lease(client):
    ws, providers, _ = setup(client, two_keys=False)

    async def run():
        scope = ProviderExecution(ws, providers[0])

        async def take():
            async with AsyncSessionFactory() as db:
                return await acquire(
                    db, scope, "chat", "https://provider0.example/v1", "model-0", 5, set()
                )

        results = await asyncio.gather(take(), take(), return_exceptions=True)
        old = next(r for r in results if not isinstance(r, BaseException))
        assert sum(isinstance(r, AppException) for r in results) == 1
        async with AsyncSessionFactory() as db:
            key = await db.get(ProviderKey, old.key_id)
            key.lease_until = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()
        current = await take()
        assert current.token != old.token
        async with AsyncSessionFactory() as db:
            await finish(db, old, call_id="old", capability="chat", code="ok", success=True)
        async with AsyncSessionFactory() as db:
            provider = await db.get(Provider, providers[0])
            assert provider.extra_config[LEASES_KEY][current.key_id]["token"] == current.token
            await finish(db, current, call_id="new", capability="chat", code="ok", success=True)

    client.portal.call(run)


@pytest.mark.parametrize("kind", ["timeout", "cancel"])
def test_uncertainty_and_cancellation_release_lease_without_retry(client, kind):
    ws, providers, _ = setup(client)
    calls = []

    async def upstream(req):
        calls.append(req)
        if kind == "timeout":
            raise httpx.ReadTimeout("test")
        raise asyncio.CancelledError()

    async def run():
        model = ManagedChatModel(OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream)))
        with pytest.raises(AppException if kind == "timeout" else asyncio.CancelledError):
            await model.complete(MESSAGES, request(ws, providers[0]))

    client.portal.call(run)
    assert len(calls) == 1
    assert all(
        k["lease_until"] is None
        for k in client.get(API + f"/modelops/providers/{providers[0]}/keys").json()
    )


def test_fallback_selects_once_before_budget_and_ledger_while_explicit_provider_is_pinned(client):
    ws, providers, _ = setup(client)
    policy = ResiliencePolicy(fallbacks={"compiler": [providers[1]], "answer": [providers[1]]})
    client.put(API + f"/modelops/providers/{providers[0]}/resilience", json=policy.model_dump())
    client.patch(API + f"/modelops/providers/{providers[0]}", json={"is_active": False})

    async def run():
        async with AsyncSessionFactory() as db:
            runtime, prepared, budget = await prepare_chat_request(
                db, ADMIN, ws, MESSAGES, provider_id=None, max_output_tokens=100, task="compiler"
            )
            assert runtime.provider_id == providers[1] and prepared.model == "model-1"
            assert runtime.routing_trace[0]["code"] == "provider_inactive"
            usage = await usage_service.reserve(
                db,
                ADMIN,
                ws,
                "chat",
                "fallback-test",
                "a" * 64,
                budget.total_reserved_tokens,
                runtime.provider_id,
            )
            assert usage.provider_id == providers[1] and usage.model_name == "model-1"
        async with AsyncSessionFactory() as db:
            with pytest.raises(AppException, match="đang tắt"):
                await prepare_chat_request(
                    db,
                    ADMIN,
                    ws,
                    MESSAGES,
                    provider_id=providers[0],
                    max_output_tokens=100,
                    task="compiler",
                )

    client.portal.call(run)


def test_fallback_requires_workspace_access_and_never_resurrects_inactive_providers(client):
    ws, providers, _ = setup(client)
    policy = ResiliencePolicy(fallbacks={"answer": [providers[1]]})
    client.put(API + f"/modelops/providers/{providers[0]}/resilience", json=policy.model_dump())
    client.patch(API + f"/modelops/providers/{providers[0]}", json={"is_active": False})

    async def run():
        async with AsyncSessionFactory() as db:
            with pytest.raises(AppException) as exc:
                await prepare_chat_request(
                    db,
                    OUTSIDER,
                    ws,
                    MESSAGES,
                    provider_id=None,
                    max_output_tokens=100,
                    task="answer",
                )
            assert exc.value.status_code == 404
        async with AsyncSessionFactory() as db:
            runtime, _, budget = await prepare_chat_request(
                db, ADMIN, ws, MESSAGES, provider_id=None, max_output_tokens=100, task="answer"
            )
            assert runtime.provider_id == providers[1]
            usage = await usage_service.reserve(
                db,
                ADMIN,
                ws,
                "chat",
                "fallback-access",
                "a" * 64,
                budget.total_reserved_tokens,
                runtime.provider_id,
            )
            assert usage.provider_id == providers[1]

    client.portal.call(run)
    client.patch(API + f"/modelops/providers/{providers[1]}", json={"is_active": False})

    async def denied():
        async with AsyncSessionFactory() as db:
            with pytest.raises(AppException) as exc:
                await prepare_chat_request(
                    db, ADMIN, ws, MESSAGES, provider_id=None, max_output_tokens=100, task="answer"
                )
            assert exc.value.code == "fallback_exhausted"

    client.portal.call(denied)


def test_policy_auth_validation_registry_and_stale_identity(client):
    _, providers, _ = setup(client)
    path = API + f"/modelops/providers/{providers[0]}/resilience"
    for body in [
        {"retry_owner": "gateway", "key_pool_enabled": True, "max_key_attempts": 2},
        {"fallbacks": {"embedding": [providers[1]]}},
        {"fallbacks": {"answer": [providers[0]]}},
    ]:
        assert client.put(path, json=body).status_code in (409, 422)
    registry = client.get(API + "/modelops/registry").json()
    assert next(r for r in registry if r["provider_type"] == "gemini")["protocols"] == {}
    assert all(not r["responses_api"] for r in registry)
    client.patch(API + f"/modelops/providers/{providers[0]}", json={"model_name": "changed"})
    assert client.get(path).json()["status"] == "stale"
    app.dependency_overrides[get_actor] = lambda: OUTSIDER
    assert client.get(path).status_code == 403
    assert client.put(path, json={}).status_code == 403
    assert client.get(API + "/modelops/registry").status_code == 403
    assert client.get(API + f"/modelops/providers/{providers[0]}/executions").status_code == 403


@pytest.mark.parametrize("capability", ["chat", "embedding", "rerank", "ocr"])
@pytest.mark.parametrize("observed_usage", [None, 9])
def test_all_runtime_ports_share_pool_but_never_retry_an_observed_charge(
    client, capability, observed_usage
):
    ws, providers, _ = setup(client)
    result = client.patch(
        API + f"/modelops/providers/{providers[0]}", json={"capabilities": [capability]}
    )
    assert result.status_code == 200
    calls = []

    def upstream(req):
        calls.append(req)
        return httpx.Response(
            429, json={"error": "synthetic", "usage": {"total_tokens": observed_usage}}
        )

    async def run():
        transport = httpx.MockTransport(upstream)
        scope = ProviderExecution(ws, providers[0])
        endpoint, model, secret = "https://provider0.example/v1", "model-0", "stale-key"
        if capability == "chat":
            call = ManagedChatModel(OpenAICompatibleChatModel(transport=transport)).complete(
                MESSAGES, request(ws, providers[0])
            )
        elif capability == "embedding":
            call = ManagedEmbeddingModel(ModelOpsEmbeddingModel(transport=transport)).embed(
                ["synthetic"], EmbeddingRequest(endpoint, model, 5, secret, 2, scope)
            )
        elif capability == "rerank":
            call = ManagedReranker(ModelOpsReranker(transport=transport)).rerank(
                "synthetic", ["candidate"], 1, RerankRequest(endpoint, model, 5, secret, scope)
            )
        else:
            call = ManagedOcrEngine(NemotronOcrEngine(transport=transport)).extract_page(
                b"synthetic",
                OcrRequest(endpoint, model, "synthetic", 100, 5, secret, execution=scope),
            )
        with pytest.raises(AppException):
            await call

    client.portal.call(run)
    assert len(calls) == (2 if observed_usage is None else 1)
    assert all(__import__("json").loads(r.content)["model"] == "model-0" for r in calls)


def test_gateway_has_one_attempt_and_operational_leases_do_not_stale_diagnostics(client):
    from qnu.domains.modelops.diagnostics.service import identity

    ws, providers, _ = setup(client)
    policy = ResiliencePolicy(key_pool_enabled=True, retry_owner="gateway")
    client.put(API + f"/modelops/providers/{providers[0]}/resilience", json=policy.model_dump())
    calls = []

    def upstream(req):
        calls.append(req)
        return httpx.Response(401)

    async def run():
        async with AsyncSessionFactory() as db:
            before = await identity(db, await db.get(Provider, providers[0]))
        model = ManagedChatModel(OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream)))
        with pytest.raises(AppException):
            await model.complete(MESSAGES, request(ws, providers[0]))
        async with AsyncSessionFactory() as db:
            after = await identity(db, await db.get(Provider, providers[0]))
        assert before == after

    client.portal.call(run)
    assert len(calls) == 1


def test_revalidation_before_key_retry_reports_config_change(client):
    ws, providers, _ = setup(client)
    calls = []

    async def upstream(req):
        calls.append(req)
        async with AsyncSessionFactory() as db:
            row = await db.get(Provider, providers[0])
            row.model_name = "changed"
            await db.commit()
        return httpx.Response(401)

    async def run():
        model = ManagedChatModel(OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream)))
        with pytest.raises(AppException) as caught:
            await model.complete(MESSAGES, request(ws, providers[0]))
        return caught.value.code

    assert client.portal.call(run) == "provider_execution_changed"
    assert len(calls) == 1


@pytest.mark.parametrize("action", ["revoke", "rotate"])
def test_key_lifecycle_locks_provider_before_key_to_avoid_lease_deadlock(client, action):
    from sqlalchemy import select, text
    from sqlalchemy.exc import DBAPIError

    from qnu.domains.modelops.keys.service import key_service
    from qnu.domains.modelops.schemas import KeyRotateRequest

    _, providers, keys = setup(client)

    async def run():
        async with (
            AsyncSessionFactory() as owner,
            AsyncSessionFactory() as lifecycle,
            AsyncSessionFactory() as observer,
        ):
            await owner.execute(
                select(Provider).where(Provider.id == providers[0]).with_for_update()
            )
            pid = await lifecycle.scalar(text("SELECT pg_backend_pid()"))
            if action == "revoke":
                pending = asyncio.create_task(
                    key_service.revoke_key(lifecycle, providers[0], keys[0][0], ADMIN, None)
                )
            else:
                pending = asyncio.create_task(
                    key_service.rotate_key(
                        lifecycle,
                        providers[0],
                        keys[0][0],
                        KeyRotateRequest(name="Rotated", secret="test-replacement-private"),
                        ADMIN,
                    )
                )
            locked_first = False
            try:
                async with asyncio.timeout(5):
                    while (
                        await observer.scalar(
                            text("SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid"),
                            {"pid": pid},
                        )
                        != "Lock"
                    ):
                        await observer.rollback()
                        await asyncio.sleep(0.01)
                await observer.rollback()
                try:
                    await observer.execute(
                        select(ProviderKey)
                        .where(ProviderKey.id == keys[0][0])
                        .with_for_update(nowait=True)
                    )
                    locked_first = True
                except DBAPIError:
                    pass
            finally:
                await observer.rollback()
                await owner.rollback()
                await pending
            return locked_first

    assert client.portal.call(run), (
        "Lifecycle held key before provider: distributed lease can deadlock"
    )


def test_runtime_attempt_links_to_reservation_and_cannot_replay_a_settled_call(client):
    from qnu.ports.provider_execution import bind_usage

    ws, providers, _ = setup(client)
    calls = []

    def upstream(req):
        calls.append(req)
        return ok()

    async def run():
        async with AsyncSessionFactory() as db:
            _, prepared, budget = await prepare_chat_request(
                db, ADMIN, ws, MESSAGES, provider_id=providers[0], max_output_tokens=100
            )
            usage = await usage_service.reserve(
                db,
                ADMIN,
                ws,
                "chat",
                "bound-runtime",
                "a" * 64,
                budget.total_reserved_tokens,
                providers[0],
            )
            prepared = bind_usage(prepared, usage.id)
            model = ManagedChatModel(
                OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream))
            )
            result = await model.complete(MESSAGES, prepared)
            await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
            with pytest.raises(AppException) as caught:
                await model.complete(MESSAGES, prepared)
            return usage.id, caught.value.code

    uid, code = client.portal.call(run)
    assert code == "provider_reservation_mismatch" and len(calls) == 1
    history = client.get(API + f"/modelops/providers/{providers[0]}/executions")
    assert history.status_code == 200, history.text
    assert history.json()[0]["usage_id"] == uid
    assert history.json()[0]["model_name"] == "model-0"
    assert history.json()[0]["total_tokens"] == 7


def test_one_total_deadline_stops_slow_transport_and_preserves_uncertainty_code(client):
    from dataclasses import replace

    ws, providers, _ = setup(client)
    calls = []

    async def upstream(req):
        calls.append(req)
        await asyncio.sleep(0.15)
        return ok()

    async def run():
        model = ManagedChatModel(OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream)))
        with pytest.raises(AppException) as caught:
            await model.complete(MESSAGES, replace(request(ws, providers[0]), timeout_seconds=0.08))
        return caught.value.code

    assert client.portal.call(run) == "chat_provider_uncertain"
    assert len(calls) == 1
    keys = client.get(API + f"/modelops/providers/{providers[0]}/keys").json()
    assert all(k["lease_until"] is None for k in keys)


def test_optional_auth_cannot_retry_the_same_anonymous_request(client):
    ws, providers, keys = setup(client)
    client.patch(API + f"/modelops/providers/{providers[0]}", json={"capabilities": ["ocr"]})
    for kid in keys[0]:
        client.post(API + f"/modelops/providers/{providers[0]}/keys/{kid}/revoke", json={})
    calls = []

    def upstream(req):
        calls.append(req)
        return httpx.Response(401)

    async def run():
        async with AsyncSessionFactory() as db:
            row = await db.get(Provider, providers[0])
            row.extra_config = {**row.extra_config, "ocr_auth_optional": True}
            await db.commit()
        engine = ManagedOcrEngine(NemotronOcrEngine(transport=httpx.MockTransport(upstream)))
        with pytest.raises(AppException):
            await engine.extract_page(
                b"synthetic",
                OcrRequest(
                    "https://provider0.example/v1",
                    "model-0",
                    "synthetic",
                    100,
                    5,
                    auth_optional=True,
                    execution=ProviderExecution(ws, providers[0]),
                ),
            )

    client.portal.call(run)
    assert len(calls) == 1 and "authorization" not in calls[0].headers


def test_cooling_keys_are_unavailable_instead_of_missing_credentials(client):
    ws, providers, keys = setup(client)

    async def run():
        async with AsyncSessionFactory() as db:
            for kid in keys[0]:
                row = await db.get(ProviderKey, kid)
                row.cooldown_until = datetime.now(UTC) + timedelta(minutes=5)
            await db.commit()
            with pytest.raises(AppException) as caught:
                await prepare_chat_request(
                    db, ADMIN, ws, MESSAGES, provider_id=providers[0], max_output_tokens=100
                )
            return caught.value.code

    assert client.portal.call(run) == "provider_keys_unavailable"


def test_ocr_fallback_result_is_reusable_while_primary_stays_disabled(client):
    from tests.integration.knowledge_support import (
        EDITOR,
        PLATFORM,
        as_actor,
        workspace_with_editor,
    )
    from tests.integration.ocr_support import (
        FakeNemotron,
        execute_now,
        ocr_blocks,
        prepare_source,
        request_run,
        runs_url,
        setup_ocr_provider,
    )

    with FakeNemotron() as primary, FakeNemotron() as backup:
        backup.responses = [ocr_blocks("Synthetic source|Text")]
        ws = workspace_with_editor(client, "ocr-fallback-reuse")
        as_actor(EDITOR)
        collection, source, revision = prepare_source(client, ws["id"], "Synthetic fallback")
        first = setup_ocr_provider(client, ws["id"], primary.base_url)
        second = setup_ocr_provider(client, ws["id"], backup.base_url)
        as_actor(PLATFORM)
        granted = client.put(API + "/modelops/defaults", json={"ocr_provider_id": first["id"]})
        assert granted.status_code == 200, granted.text
        saved = client.put(
            API + f"/modelops/providers/{first['id']}/resilience",
            json={"fallbacks": {"ocr": [second["id"]]}},
        )
        assert saved.status_code == 200, saved.text
        client.patch(API + f"/modelops/providers/{first['id']}", json={"is_active": False})
        as_actor(EDITOR)
        created = request_run(client, ws["id"], collection["id"], source["id"], revision["id"])
        assert created.status_code == 201, created.text
        run_id = created.json()["run"]["id"]
        assert execute_now(client, run_id).status == "completed"
        detail = client.get(
            runs_url(ws["id"], collection["id"], source["id"], revision["id"]) + "/" + run_id
        )
        assert detail.json()["provider_id"] == second["id"]
        replay = request_run(client, ws["id"], collection["id"], source["id"], revision["id"])
        assert replay.status_code == 200, replay.text
        assert replay.json()["run"]["id"] == run_id and not replay.json()["created"]
