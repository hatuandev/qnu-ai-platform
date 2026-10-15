"""HTTP contracts: provider-tokenized budgets never crop source evidence."""

import json

import httpx
import pytest

from app.core.exceptions import AppException
from app.modules.modelops.providers.openai_adapter import OpenAIAdapter
from app.modules.modelops.schemas import ChatMessage

ERROR = {"error": {"message": "This model's maximum context length is 8192 tokens. However, you requested "
         "5000 output tokens and your prompt contains at least 3193 input tokens, for a total of at least 8193 tokens."}}
MESSAGES = [ChatMessage(role="system", content="Keep conditions and sources."),
            ChatMessage(role="user", content="Full row 15 / 18 / 600 / 15 and its notes.")]


def connect(monkeypatch, server):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(server)))
    return OpenAIAdapter("vendor/future-alias", "fixture-credential", "http://gateway/prefix/v1", provider_type="vllm")


@pytest.mark.asyncio
async def test_context_retry_uses_exact_tokenizer_count_not_lower_bound(monkeypatch):
    calls = []

    def server(request):
        payload = json.loads(request.content)
        calls.append((request.url.path, payload))
        assert payload["model"] == "vendor/future-alias"
        assert payload["messages"] == [message.model_dump() for message in MESSAGES]
        if request.url.path == "/prefix/tokenize":
            assert payload["add_generation_prompt"] is True
            return httpx.Response(200, json={"count": 4500, "max_model_len": 8192})
        if len(calls) == 1:
            return httpx.Response(400, json=ERROR)
        assert payload["max_tokens"] == 3692
        return httpx.Response(200, json={"choices": [{"message": {"content": "Complete answer"}, "finish_reason": "stop"}]})

    adapter = connect(monkeypatch, server)
    result = await adapter.generate(MESSAGES, max_tokens=5000)
    assert result.content == "Complete answer" and len(calls) == 3
    assert adapter.request_capabilities == {}  # Per-request counts are NOT a permanent capability.


@pytest.mark.asyncio
@pytest.mark.parametrize("count,maximum", [(8192, 8192), (9000, 8192), (False, 8192), (100, 8192), (4500, 16384)])
async def test_invalid_or_incompatible_tokenizer_cannot_invent_budget(monkeypatch, count, maximum):
    calls = []

    def server(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/tokenize"):
            return httpx.Response(200, json={"count": count, "max_model_len": maximum})
        return httpx.Response(400, json=ERROR)

    with pytest.raises(httpx.HTTPStatusError):
        await connect(monkeypatch, server).generate(MESSAGES, max_tokens=5000)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_missing_tokenize_endpoint_preserves_original_error(monkeypatch):
    calls = []

    def server(request):
        calls.append(request.url.path)
        return httpx.Response(404 if request.url.path.endswith("/tokenize") else 400, json=ERROR)

    with pytest.raises(httpx.HTTPStatusError) as error:
        await connect(monkeypatch, server).generate(MESSAGES, max_tokens=5000)
    assert error.value.response.status_code == 400 and len(calls) == 2


@pytest.mark.asyncio
async def test_context_recovery_retries_at_most_once(monkeypatch):
    calls = []

    def server(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/tokenize"):
            return httpx.Response(200, json={"count": 4500, "max_model_len": 8192})
        return httpx.Response(400, json=ERROR)

    with pytest.raises(httpx.HTTPStatusError):
        await connect(monkeypatch, server).generate(MESSAGES, max_tokens=5000)
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_stream_context_retry_preserves_template_and_arbitrary_alias(monkeypatch):
    calls = []

    def server(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["chat_template_kwargs"] == {"enable_thinking": True}
        if request.url.path.endswith("/tokenize"):
            return httpx.Response(200, json={"count": 4500, "max_model_len": 8192})
        if len(calls) == 1:
            return httpx.Response(400, json=ERROR)
        assert payload["max_tokens"] == 3692
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n',
                              headers={"content-type": "text/event-stream"})

    adapter = connect(monkeypatch, server)
    assert [token async for token in adapter.stream(MESSAGES, max_tokens=5000, thinking_budget=10)] == ["OK"]
    assert len(calls) == 3 and all(call["model"] == adapter.model_name for call in calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 429, 500])
async def test_unrelated_error_never_calls_tokenizer(monkeypatch, status):
    calls = []

    def server(request):
        calls.append(request.url.path)
        return httpx.Response(status, json={"error": {"message": "Unrelated invalid request"}})

    with pytest.raises(httpx.HTTPStatusError):
        await connect(monkeypatch, server).generate(MESSAGES, max_tokens=5000)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_nonempty_truncated_completion_is_not_success(monkeypatch, stream):
    def server(request):
        if stream:
            event = {"choices": [{"delta": {"content": "Partial answer"}, "finish_reason": "length"}]}
            return httpx.Response(200, text="data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n",
                                  headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "Partial answer"}, "finish_reason": "length"}]})

    adapter = connect(monkeypatch, server)
    with pytest.raises(AppException) as error:
        if stream:
            _ = [token async for token in adapter.stream(MESSAGES)]
        else:
            await adapter.generate(MESSAGES)
    assert error.value.code == "MODEL_OUTPUT_BUDGET_EXHAUSTED"
