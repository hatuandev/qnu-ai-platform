"""Admission contract tests; Redis atomicity still requires an isolated Redis run."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.modelops.resilience import admission
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatResponseError


def fixture(monkeypatch):
    client = SimpleNamespace(eval=AsyncMock(return_value=1), zrem=AsyncMock())
    monkeypatch.setattr(admission, "get_redis", lambda: client)
    monkeypatch.setattr(admission, "namespaced", lambda key: "test:" + key)
    monkeypatch.setattr(
        admission, "get_settings",
        lambda: SimpleNamespace(MODEL_CHAT_CONCURRENCY=2, MODEL_CHAT_QUEUE_TIMEOUT_SECONDS=1),
    )
    request = SimpleNamespace(endpoint="https://ai.example/v1/", model="model", timeout_seconds=300)
    return client, request


def test_aliases_share_the_same_resource_key(monkeypatch):
    fixture(monkeypatch)
    first = admission.resource_key("https://AI.example/v1/", "model")
    assert first == admission.resource_key("https://ai.example:443/v1", "model")
    assert first != admission.resource_key("https://ai.example/v1", "other-model")


@pytest.mark.asyncio
async def test_success_releases_only_its_own_shared_slot(monkeypatch):
    client, request = fixture(monkeypatch)
    async with admission.chat_slot(request):
        client.zrem.assert_not_called()
    args = client.eval.await_args.args
    assert args[3:5] == (2, 330_000)
    client.zrem.assert_awaited_once_with(args[2], args[5])


@pytest.mark.asyncio
async def test_pinned_document_limit_raises_the_shared_admission_limit(monkeypatch):
    client, request = fixture(monkeypatch)
    request.admission_limit = 7
    async with admission.chat_slot(request):
        pass
    assert client.eval.await_args.args[3] == 7


@pytest.mark.asyncio
async def test_pinned_limit_never_lowers_the_shared_default(monkeypatch):
    client, request = fixture(monkeypatch)
    request.admission_limit = 1
    async with admission.chat_slot(request):
        pass
    assert client.eval.await_args.args[3] == 2


@pytest.mark.asyncio
async def test_no_dispatch_when_admission_cannot_be_checked(monkeypatch):
    client, request = fixture(monkeypatch)
    client.eval.side_effect = ConnectionError("offline")
    entered = False
    with pytest.raises(ChatResponseError) as caught:
        async with admission.chat_slot(request):
            entered = True
    assert not entered
    assert caught.value.code == "chat_admission_unavailable"
    assert caught.value.usage_tokens == 0
    client.zrem.assert_not_called()


@pytest.mark.asyncio
async def test_queue_deadline_stops_before_trying_to_dispatch_again(monkeypatch):
    client, request = fixture(monkeypatch)
    client.eval.return_value = 0
    ticks = iter([10, 10, 11, 11])
    # Patch this module's clock, never the event loop's monotonic clock.
    monkeypatch.setattr(admission, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    with pytest.raises(ChatResponseError) as caught:
        async with admission.chat_slot(request):
            pytest.fail("must not enter when queued until deadline")
    assert caught.value.code == "chat_admission_timeout"
    assert caught.value.usage_tokens == 0
    client.eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancelled_dispatch_keeps_the_ttl_lease(monkeypatch):
    client, request = fixture(monkeypatch)
    with pytest.raises(asyncio.CancelledError):
        async with admission.chat_slot(request):
            raise asyncio.CancelledError
    client.zrem.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("code,retained", [("chat_provider_uncertain", True), ("chat_output_truncated", False)])
async def test_uncertain_response_keeps_slot_but_definite_response_releases(monkeypatch, code, retained):
    client, request = fixture(monkeypatch)
    with pytest.raises(AppException):
        async with admission.chat_slot(request):
            raise AppException("error", code=code)
    assert client.zrem.await_count == (0 if retained else 1)


@pytest.mark.asyncio
async def test_release_failure_does_not_discard_a_measured_result(monkeypatch):
    client, request = fixture(monkeypatch)
    client.zrem.side_effect = ConnectionError("offline")
    async with admission.chat_slot(request):
        result = "measured"
    assert result == "measured"
    client.zrem.assert_awaited_once()
