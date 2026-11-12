"""ModelOps admin policy, actual DB key fences and real Redis renewal."""

import asyncio
from dataclasses import replace

import httpx

from qnu.adapters.providers.openai_compatible import OpenAICompatibleChatModel
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.resilience import admission
from qnu.domains.modelops.resilience.execution import ManagedChatModel
from qnu.domains.modelops.resilience.key_pool import acquire, finish, renew
from qnu.domains.modelops.resilience.schemas import ResiliencePolicy
from qnu.platform.database import AsyncSessionFactory
from qnu.ports.provider_execution import ProviderExecution
from tests.integration.test_modelops_resilience_695 import (
    ADMIN,
    API,
    MESSAGES,
    ok,
    request,
    setup,
)


def test_admin_policy_keeps_chat_bounded_and_lets_document_tasks_wait(client):
    ws, providers, _ = setup(client)
    url = API + f"/modelops/providers/{providers[0]}/resilience"
    policy = ResiliencePolicy(key_pool_enabled=True, max_key_attempts=2, wait_for_completion=True)
    saved = client.put(url, json=policy.model_dump())
    assert saved.status_code == 200, saved.text
    assert client.get(url).json()["policy"]["wait_for_completion"] is True
    seen = []

    async def upstream(req):
        seen.append(req.extensions["timeout"])
        await asyncio.sleep(0.04)
        return ok()

    async def run():
        async with AsyncSessionFactory() as db:
            for task in ("chat", "answer", "followup"):
                _, request, _ = await prepare_chat_request(
                    db, ADMIN, ws, MESSAGES, provider_id=providers[0], max_output_tokens=100,
                    task=task,
                )
                assert not request.wait_for_completion, task
                assert request.timeout_seconds == 30
            for task in ("compiler", "ocr_review"):
                _, request, _ = await prepare_chat_request(
                    db, ADMIN, ws, MESSAGES, provider_id=providers[0], max_output_tokens=100,
                    task=task,
                )
                assert request.wait_for_completion, task
            runtime, prepared, _ = await prepare_chat_request(
                db, ADMIN, ws, MESSAGES, provider_id=providers[0], max_output_tokens=100,
                task="compiler_review",
            )
            assert runtime.wait_for_completion and prepared.wait_for_completion
        model = ManagedChatModel(OpenAICompatibleChatModel(transport=httpx.MockTransport(upstream)))
        return await model.complete(MESSAGES, replace(prepared, timeout_seconds=0.01))

    assert client.portal.call(run).total_tokens == 7
    assert len(seen) == 1 and seen[0]["read"] is None


def test_key_renewal_is_fenced_and_release_keeps_policy(client):
    ws, providers, _ = setup(client, two_keys=False)

    async def run():
        async with AsyncSessionFactory() as db:
            lease = await acquire(
                db, ProviderExecution(ws, providers[0]), "chat", request(ws, providers[0]).endpoint,
                "model-0", 1, set(),
            )
        async with AsyncSessionFactory() as db:
            assert await renew(db, lease, 30)
        async with AsyncSessionFactory() as db:
            assert not await renew(db, replace(lease, token="wrong-owner"), 30)
        async with AsyncSessionFactory() as db:
            await finish(db, lease, call_id="renew760", capability="chat", code="ok", success=True)

    client.portal.call(run)


def test_redis_renewal_never_creates_a_foreign_or_expired_lease(client):
    async def run():
        redis = admission.get_redis()
        key = admission.resource_key("https://test.invalid/v1", "wait760")
        try:
            assert await redis.eval(admission.ACQUIRE, 1, key, 1, 1000, "owned") == 1
            assert await redis.eval(admission.RENEW, 1, key, 1000, "foreign") == 0
            assert await redis.eval(admission.RENEW, 1, key, 2000, "owned") == 1
            await redis.zadd(key, {"owned": 0})
            assert await redis.eval(admission.RENEW, 1, key, 2000, "owned") == 0
        finally:
            await redis.delete(key)

    client.portal.call(run)
