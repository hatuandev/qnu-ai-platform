"""Independent review probes. Synthetic data, isolated test DB, no upstream calls."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from qnu.api.dependencies import get_actor
from qnu.domains.assistants.models import Assistant
from qnu.domains.identity.service import resolve_actor
from qnu.domains.integration.gateway import get_redis_client
from qnu.domains.integration.models import AppApiKey, AppClient
from qnu.domains.integration.schemas import AppApiKeyCreate, AppApiKeyRotateRequest
from qnu.domains.integration.service import integration_service
from qnu.domains.modelops.diagnostics.service import identity
from qnu.domains.modelops.models import Provider
from qnu.domains.rag.answer.schemas import AnswerResponse, AnswerTrace
from qnu.domains.workspaces.models import Workspace, WorkspaceMember
from qnu.main import app
from qnu.platform.config import get_settings
from qnu.platform.database import engine
from qnu.platform.errors import AppException
from tests.integration.test_application_api_keys import (
    ADMIN_A,
    API,
    PLATFORM,
    _as,
    _setup_test_workspaces,
)


def healthy_redis():
    redis = MagicMock()
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=[1, True, 1, True])
    redis.pipeline.return_value.__aenter__ = AsyncMock(return_value=pipeline)
    redis.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)
    return redis


def setup_case(client, **policy):
    ws, _ = _setup_test_workspaces(client)
    _as(PLATFORM)
    r = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "Review synthetic",
            "provider_type": "openai_compatible",
            "base_url": "http://127.0.0.1:19999/v1",
            "model_name": "review-model",
            "capabilities": ["chat"],
            "timeout_seconds": 5,
        },
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    client.put(
        f"{API}/workspaces/{ws}/allowed-providers",
        json={"provider_ids": [pid], "defaults": {"chat": pid}},
    )
    _as(ADMIN_A)
    r = client.post(f"{API}/workspaces/{ws}/collections", json={"name": "Review collection"})
    assert r.status_code == 201, r.text
    r = client.post(
        f"{API}/workspaces/{ws}/assistants",
        json={
            "name": "Review assistant",
            "collection_id": r.json()["id"],
            "chat_provider_id": pid,
            "persona": "Synthetic persona",
            "max_output_tokens": 128,
            "rag_policy": policy,
        },
    )
    assert r.status_code == 201, r.text
    ast = r.json()["id"]
    r = client.post(
        f"{API}/workspaces/{ws}/integrations/keys",
        json={
            "name": "Review key",
            "app_name": "Review client",
            "rate_limit_rpm": 1,
            "allowed_assistant_ids": [ast],
        },
    )
    assert r.status_code == 201, r.text
    key_id = r.json()["id"]
    headers = {"Authorization": "Bearer " + r.json()["secret_key"]}
    app.dependency_overrides.pop(resolve_actor, None)
    app.dependency_overrides.pop(get_actor, None)
    app.dependency_overrides[get_redis_client] = healthy_redis
    return ws, pid, ast, key_id, headers


@pytest.fixture(autouse=True)
def reset_overrides():
    settings = get_settings().model_copy(update={"PUBLIC_BASE_URL": "https://qnu-review.invalid"})
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(resolve_actor, None)
    app.dependency_overrides.pop(get_redis_client, None)


def fake_answer():
    return AnswerResponse(
        id="ans_review",
        status="insufficient_evidence",
        reason="no_match",
        index_run_id="idx_review",
        generation=1,
        trace=AnswerTrace(prompt_version="review"),
    )


def post_chat(client, ast, headers, **extra):
    return client.post(
        f"{API}/integrations/openai/v1/chat/completions",
        headers=headers,
        json={
            "model": ast,
            "messages": [{"role": "user", "content": "Synthetic question"}],
            **extra,
        },
    )


def test_review_assistant_policy_and_persona_are_preserved(client):
    _, _, ast, _, headers = setup_case(
        client, retrieval_mode="hybrid", verification_mode="enforce", context_window=2
    )
    with patch(
        "qnu.domains.integration.gateway.execute_rag_answer",
        new_callable=AsyncMock,
        return_value=fake_answer(),
    ) as call:
        response = post_chat(client, ast, headers)
        assert response.status_code == 200, response.text
        kwargs = call.call_args.kwargs
        assert kwargs["req"].retrieval_mode == "hybrid", "Gateway reset assistant policy to dense"
        assert kwargs["req"].verification_mode == "enforce"
        assert kwargs["req"].max_output_tokens == 128
        assert kwargs["persona"] == "Synthetic persona"


def test_review_revocation_from_another_connection_stops_response(client):
    _, _, ast, key_id, headers = setup_case(client)

    async def revoke_during_inference(**kwargs):
        async with async_sessionmaker(engine, expire_on_commit=False)() as other:
            await other.execute(
                update(AppApiKey).where(AppApiKey.id == key_id).values(status="revoked")
            )
            await other.commit()
        return fake_answer()

    with patch(
        "qnu.domains.integration.gateway.execute_rag_answer", side_effect=revoke_during_inference
    ):
        response = post_chat(client, ast, headers)
    assert response.status_code == 403, f"Revoked key still returned HTTP {response.status_code}"


def test_review_redis_unavailable_does_not_disable_rate_limit(client):
    _, _, _, _, headers = setup_case(client)
    app.dependency_overrides[get_redis_client] = lambda: None
    path = f"{API}/integrations/openai/v1/models"
    statuses = [client.get(path, headers=headers).status_code for _ in range(3)]
    assert statuses != [200, 200, 200], f"RPM=1 bypassed while Redis unavailable: {statuses}"


def test_review_provider_error_preserves_status(client):
    _, _, ast, _, headers = setup_case(client)
    with patch(
        "qnu.domains.integration.gateway.execute_rag_answer",
        side_effect=AppException("Synthetic limit", code="quota_exceeded", status_code=429),
    ):
        response = post_chat(client, ast, headers)
    assert response.status_code == 429, f"Quota error became HTTP {response.status_code}"


def test_review_endpoint_config_ignores_untrusted_host(client):
    _as(PLATFORM)
    response = client.get(
        f"{API}/integrations/config",
        headers={"X-Forwarded-Host": "review-attacker.invalid", "X-Forwarded-Proto": "https"},
    )
    assert response.status_code == 200, response.text
    assert "review-attacker.invalid" not in response.json()["openai_endpoint"]


def test_review_summary_uses_actual_diagnostic_fields(client):
    _, pid, _, _, _ = setup_case(client)

    async def seed_check():
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            provider = await db.get(Provider, pid)
            fingerprint = await identity(db, provider)
            await db.execute(
                update(Provider)
                .where(Provider.id == pid)
                .values(
                    extra_config={
                        "diagnostic_checks_v1": [
                            {
                                "id": "diag_review",
                                "kind": "chat",
                                "outcome": "ok",
                                "tested_at": "2026-10-28T00:00:00Z",
                                "latency_ms": 12,
                                "code": "ok",
                                "detail": "Synthetic successful diagnostic",
                                "requested_model": "review-model",
                                "identity": fingerprint,
                            }
                        ]
                    }
                )
            )
            await db.commit()

    client.portal.call(seed_check)
    _as(PLATFORM)
    response = client.get(f"{API}/modelops/providers-summary")
    assert response.status_code == 200, response.text
    item = next(p for p in response.json() if p["id"] == pid)
    assert item["last_probe_status"] == "success", (
        f"Successful check summarized as {item['last_probe_status']}"
    )


def test_review_multiturn_is_processed_or_explicitly_rejected(client):
    _, _, ast, _, headers = setup_case(client)
    messages = [
        {"role": "user", "content": "Synthetic previous topic"},
        {"role": "assistant", "content": "Synthetic previous answer"},
        {"role": "user", "content": "And its price?"},
    ]
    with patch(
        "qnu.domains.integration.gateway.execute_rag_answer",
        new_callable=AsyncMock,
        return_value=fake_answer(),
    ) as call:
        response = post_chat(client, ast, headers, messages=messages)
        if response.status_code == 200:
            values = repr(call.call_args)
            assert "Synthetic previous topic" in values, (
                "History silently discarded; only final question reached RAG"
            )
        else:
            assert response.status_code == 400


def test_review_concurrent_idempotency_creates_one_key(client):
    ws, _, _, key_id, _ = setup_case(client)

    async def concurrent_create():
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as lookup:
            seed = await lookup.get(AppApiKey, key_id)
            app_id = seed.app_id
        barrier = asyncio.Event()
        arrived = 0

        async def run():
            nonlocal arrived
            async with factory() as db:
                execute = db.execute

                async def synchronized(stmt, *args, **kwargs):
                    nonlocal arrived
                    result = await execute(stmt, *args, **kwargs)
                    if "app_api_keys.idempotency_key =" in str(stmt):
                        arrived += 1
                        if arrived == 2:
                            barrier.set()
                        await asyncio.wait_for(barrier.wait(), timeout=5)
                    return result

                db.execute = synchronized
                try:
                    await integration_service.create_key(
                        db,
                        ADMIN_A,
                        ws,
                        AppApiKeyCreate(
                            app_id=app_id,
                            name="Concurrent review",
                            allow_all_assistants=True,
                            idempotency_key="review-same-operation",
                        ),
                    )
                    return "created"
                except Exception as exc:
                    return type(exc).__name__

        results = await asyncio.gather(run(), run())
        assert results.count("created") == 1, (
            f"Same idempotency key produced {results.count('created')} keys"
        )

    client.portal.call(concurrent_create)


def test_review_concurrent_rotation_cannot_mint_two_replacements(client):
    ws, _, _, key_id, _ = setup_case(client)

    async def concurrent_rotate():
        factory = async_sessionmaker(engine, expire_on_commit=False)
        barrier = asyncio.Event()
        arrived = 0

        async def run():
            nonlocal arrived
            async with factory() as db:
                original_scalar = db.scalar

                async def synchronized(stmt, *args, **kwargs):
                    nonlocal arrived
                    if "app_api_keys" in str(stmt) and "FOR UPDATE" in str(stmt):
                        arrived += 1
                        if arrived == 2:
                            barrier.set()
                        await asyncio.wait_for(barrier.wait(), timeout=5)
                    return await original_scalar(stmt, *args, **kwargs)

                db.scalar = synchronized
                try:
                    await integration_service.rotate_key(
                        db, ADMIN_A, ws, key_id, AppApiKeyRotateRequest()
                    )
                    return "created"
                except Exception as exc:
                    return type(exc).__name__

        results = await asyncio.gather(run(), run())
        assert results.count("created") == 1, (
            f"Same old key produced {results.count('created')} active replacements"
        )

    client.portal.call(concurrent_rotate)


@pytest.mark.parametrize(
    "change", ["expiry", "app", "membership", "workspace", "assistant", "revision"]
)
def test_access_changes_during_inference_are_enforced(client, change):
    ws, _, ast, key_id, headers = setup_case(client)

    async def alter(**kwargs):
        async with async_sessionmaker(engine, expire_on_commit=False)() as other:
            if change == "expiry":
                stmt = (
                    update(AppApiKey)
                    .where(AppApiKey.id == key_id)
                    .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
                )
            elif change == "app":
                stmt = (
                    update(AppClient).where(AppClient.workspace_id == ws).values(status="suspended")
                )
            elif change == "membership":
                stmt = (
                    update(WorkspaceMember)
                    .where(
                        WorkspaceMember.workspace_id == ws,
                        WorkspaceMember.actor_ref == kwargs["actor"].actor_id,
                    )
                    .values(status="revoked")
                )
            elif change == "workspace":
                stmt = update(Workspace).where(Workspace.id == ws).values(status="suspended")
            elif change == "assistant":
                stmt = update(Assistant).where(Assistant.id == ast).values(is_active=False)
            else:
                stmt = update(Assistant).where(Assistant.id == ast).values(revision=2)
            await other.execute(stmt)
            await other.commit()
        return fake_answer()

    with patch("qnu.domains.integration.gateway.execute_rag_answer", side_effect=alter):
        response = post_chat(client, ast, headers)
    assert response.status_code in (401, 403, 404, 409), response.text
    assert "choices" not in response.json()


@pytest.mark.parametrize(
    "extra",
    [
        {"temperature": 0},
        {"top_p": 0.5},
        {"max_tokens": 128},
        {"tools": []},
        {"functions": []},
        {"n": 2},
        {"messages": []},
        {"messages": [{"role": "system", "content": "Synthetic system"}]},
    ],
)
def test_unsupported_options_fail_before_inference(client, extra):
    _, _, ast, _, headers = setup_case(client)
    with patch(
        "qnu.domains.integration.gateway.execute_rag_answer", new_callable=AsyncMock
    ) as call:
        response = post_chat(client, ast, headers, **extra)
    assert response.status_code == 400, response.text
    assert "error" in response.json()
    call.assert_not_called()


@pytest.mark.parametrize("status", [403, 409, 429, 502, 503])
def test_error_status_and_redaction(client, status):
    _, _, ast, _, headers = setup_case(client)
    marker = "qnu_live_syntheticSensitive123456"
    with patch(
        "qnu.domains.integration.gateway.execute_rag_answer",
        side_effect=AppException(marker, code="synthetic_error", status_code=status),
    ):
        response = post_chat(client, ast, headers)
    assert response.status_code == status
    assert response.json()["error"]["code"] == "synthetic_error"
    assert marker not in response.text


def test_missing_public_url_fails_without_origin_guessing(client):
    _as(PLATFORM)
    settings = get_settings().model_copy(update={"PUBLIC_BASE_URL": None})
    app.dependency_overrides[get_settings] = lambda: settings
    response = client.get(f"{API}/integrations/config")
    assert response.status_code == 503
    assert response.json()["code"] == "public_endpoint_unconfigured"


def test_empty_scope_requires_explicit_all_permission(client):
    ws, _, _, _, _ = setup_case(client)
    _as(ADMIN_A)
    path = f"{API}/workspaces/{ws}/integrations/keys"
    payload = {"name": "Empty scope", "app_name": "Scope review", "allowed_assistant_ids": []}
    assert client.post(path, json=payload).status_code == 422
    allowed = client.post(path, json={**payload, "allow_all_assistants": True})
    assert allowed.status_code == 201, allowed.text
    assert allowed.headers["cache-control"] == "no-store"
    assert "secret_key" not in client.get(path).json()[0]


def test_real_redis_limiter_and_retry_after(client):
    from redis.asyncio import from_url

    redis_url = os.environ.get("TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("NOT RUN: isolated test Redis required")
    _, _, _, key_id, headers = setup_case(client)
    redis = from_url(redis_url, decode_responses=True)
    app.dependency_overrides[get_redis_client] = lambda: redis
    try:
        path = f"{API}/integrations/openai/v1/models"
        assert client.get(path, headers=headers).status_code == 200
        blocked = client.get(path, headers=headers)
        assert blocked.status_code == 429, blocked.text
        assert blocked.json()["error"]["code"] == "rate_limit_exceeded"
        assert int(blocked.headers["retry-after"]) > 0
    finally:

        async def cleanup():
            keys = [k async for k in redis.scan_iter(match=f"*integrations:*:{key_id}:*")]
            if keys:
                await redis.delete(*keys)
            await redis.aclose()

        client.portal.call(cleanup)


def test_redis_exception_is_503_and_never_runs_rag(client):
    _, _, ast, _, headers = setup_case(client)
    redis = healthy_redis()
    redis.pipeline.return_value.__aenter__.return_value.execute.side_effect = RuntimeError(
        "synthetic outage"
    )
    app.dependency_overrides[get_redis_client] = lambda: redis
    with patch(
        "qnu.domains.integration.gateway.execute_rag_answer", new_callable=AsyncMock
    ) as call:
        response = post_chat(client, ast, headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "rate_limiter_unavailable"
    call.assert_not_called()


def test_summary_marks_old_fingerprint_stale(client):
    _, pid, _, _, _ = setup_case(client)

    async def seed():
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            await db.execute(
                update(Provider)
                .where(Provider.id == pid)
                .values(
                    extra_config={
                        "diagnostic_checks_v1": [
                            {
                                "id": "diag_review",
                                "kind": "chat",
                                "outcome": "ok",
                                "tested_at": "2026-10-28T00:00:00Z",
                                "latency_ms": 12,
                                "code": "ok",
                                "detail": "Synthetic check",
                                "requested_model": "review-model",
                                "identity": "old-fingerprint",
                            }
                        ]
                    }
                )
            )
            await db.commit()

    client.portal.call(seed)
    _as(PLATFORM)
    result = client.get(f"{API}/modelops/providers-summary")
    assert result.status_code == 200
    item = next(x for x in result.json() if x["id"] == pid)
    assert item["last_probe_status"] == "stale"
    assert item["last_probe_latency_ms"] == 12
    assert item["last_probe_at"] is not None
