import json
from dataclasses import replace

import pytest

from qnu.domains.modelops.resilience.execution import ManagedChatModel, _reported_output_limit
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatRequest, ChatResponseError, ChatResult
from qnu.ports.provider_execution import ProviderExecution, ProviderFailure


class Executor:
    async def call(self, capability, request, invoke):
        return await invoke(request)


class Adapter:
    def __init__(self, status, textual=False):
        self.calls = []
        self.status = status
        self.textual = textual

    async def complete(self, messages, request):
        self.calls.append(request.max_output_tokens)
        if request.max_output_tokens > 4096:
            error = AppException("rejected", code="chat_provider_rejected")
            error.provider_failure = ProviderFailure(self.status)
            raw = json.dumps(
                {
                    "error": {
                        "message": (
                            "max_tokens: 8192 > 4096, which is the maximum allowed number of output tokens"
                        )
                    }
                    if self.textual
                    else {
                        "code": "max_output_tokens_exceeded",
                        "max_output_tokens": 4096,
                    }
                }
            ).encode()
            raise ChatResponseError(error, raw, None)
        return ChatResult(str(request.max_output_tokens), "fixture", "model", 1, 1, "stop", 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("textual", [False, True])
async def test_automatic_budget_retries_explicit_rejection_once_and_reuses_observation(textual):
    request = ChatRequest(
        "https://example.com/v1",
        "model",
        8192,
        30,
        "fixture",
        execution=ProviderExecution("workspace", "provider"),
        automatic_output_budget=True,
    )
    adapter = Adapter(422, textual)
    managed = ManagedChatModel(adapter, Executor())
    first = await managed.complete([], request)
    assert first.content == "4096"
    assert first.budget_trace["sent_output_tokens"] == 4096
    assert (await managed.complete([], request)).content == "4096"
    with pytest.raises(ChatResponseError):
        await managed.complete([], replace(request, automatic_output_budget=False))
    assert adapter.calls == [8192, 4096, 4096, 8192]

    uncertain = Adapter(504)
    with pytest.raises(ChatResponseError):
        await ManagedChatModel(uncertain, Executor()).complete([], request)
    assert uncertain.calls == [8192]


@pytest.mark.asyncio
async def test_changed_target_and_expired_observation_send_original_budget(monkeypatch):
    request = ChatRequest(
        "https://example.com/v1",
        "model",
        8192,
        30,
        "fixture",
        execution=ProviderExecution("workspace", "provider"),
        automatic_output_budget=True,
        budget_identity="generation-a",
    )
    adapter = Adapter(400)
    managed = ManagedChatModel(adapter, Executor())
    await managed.complete([], request)
    await managed.complete([], replace(request, budget_identity="generation-b"))
    assert adapter.calls == [8192, 4096, 8192, 4096]
    monkeypatch.setattr("qnu.domains.modelops.resilience.execution.time.monotonic", lambda: 1e15)
    await managed.complete([], request)
    assert adapter.calls[-2:] == [8192, 4096]


@pytest.mark.parametrize("limit", [None, True, -1, 0, "4096", 8192, 16384])
def test_invalid_limits_are_not_learned(limit):
    error = AppException("rejected", code="chat_provider_rejected")
    error.provider_failure = ProviderFailure(422)
    raw = json.dumps(
        {
            "error": {"code": "max_output_tokens_exceeded", "max_output_tokens": limit},
        }
    ).encode()
    assert _reported_output_limit(ChatResponseError(error, raw, None), 8192) is None


def test_output_rejection_with_observed_usage_is_not_retried():
    error = AppException("rejected", code="chat_provider_rejected")
    error.provider_failure = ProviderFailure(422)
    raw = json.dumps(
        {
            "error": {"code": "max_output_tokens_exceeded", "max_output_tokens": 4096},
            "usage": {"completion_tokens": 1},
        }
    ).encode()
    assert _reported_output_limit(ChatResponseError(error, raw, None), 8192) is None
