"""An explicit ModelOps policy can wait for a chat result without a read deadline."""

import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest

from qnu.adapters.providers.openai_compatible import OpenAICompatibleChatModel
from qnu.domains.modelops.resilience import execution
from qnu.domains.modelops.resilience.heartbeat import maintain_lease
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage, ChatRequest


def request(wait):
    return ChatRequest(
        endpoint="http://localhost/v1", model="test", api_key="test-only",
        timeout_seconds=0.01, max_output_tokens=32, wait_for_completion=wait,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("wait", [False, True])
async def test_managed_deadline_is_disabled_only_by_explicit_policy(monkeypatch, wait):
    @asynccontextmanager
    async def slot(_):
        yield

    monkeypatch.setattr(execution, "chat_slot", slot)
    calls = 0

    async def invoke(_):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.04)
        return "done"

    if wait:
        assert await execution.CredentialExecutor().call("chat", request(wait), invoke) == "done"
    else:
        with pytest.raises(AppException, match="Hết thời gian") as caught:
            await execution.CredentialExecutor().call("chat", request(wait), invoke)
        assert caught.value.code == "chat_provider_uncertain"
    assert calls == 1


@pytest.mark.asyncio
async def test_unbounded_read_keeps_transport_timeouts_and_cancellation():
    seen = []

    async def transport(req):
        seen.append(req.extensions["timeout"])
        await asyncio.sleep(0.02)
        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
        })

    adapter = OpenAICompatibleChatModel(transport=httpx.MockTransport(transport))
    await adapter.complete([ChatMessage("user", "synthetic")], request(True))
    assert seen[0]["read"] is None
    assert seen[0]["connect"] is not None
    assert seen[0]["write"] is not None


@pytest.mark.asyncio
async def test_unbounded_call_can_still_be_cancelled_without_retry(monkeypatch):
    @asynccontextmanager
    async def slot(_):
        yield

    monkeypatch.setattr(execution, "chat_slot", slot)
    started = asyncio.Event()
    calls = 0

    async def invoke(_):
        nonlocal calls
        calls += 1
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(execution.CredentialExecutor().call("chat", request(True), invoke))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls == 1


@pytest.mark.asyncio
async def test_lost_lease_cancels_inference_as_uncertain():
    async def lost():
        return False

    with pytest.raises(AppException) as caught:
        async with maintain_lease(lost, 0.01):
            await asyncio.Event().wait()
    assert caught.value.code == "chat_provider_uncertain"
