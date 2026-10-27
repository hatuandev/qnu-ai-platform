"""Transport, credential and error contracts of OpenAI-compatible chat."""

import json

import httpx
import pytest

from qnu.adapters.providers.openai_compatible import OpenAICompatibleChatModel, completions_url
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage, ChatRequest, ChatResponseError


def request(**options):
    return ChatRequest(
        endpoint="http://127.0.0.1:20128/v1",
        model="gh/gpt-6-luna",
        max_output_tokens=1024,
        timeout_seconds=5,
        api_key="test-secret",
        **options,
    )


def response(content="{}", finish="stop", usage=None):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}], "usage": usage}


@pytest.mark.parametrize("url", ["http://x", "http://x/v1", "http://x/v1/chat/completions"])
def test_chat_endpoint_normalized_once(url):
    assert completions_url(url) == "http://x/v1/chat/completions"


@pytest.mark.asyncio
async def test_chat_contract_unknown_usage_and_secret_repr():
    calls = []

    async def handle(r):
        calls.append(r)
        assert r.headers["authorization"] == "Bearer test-secret"
        body = json.loads(r.content)
        assert body["model"] == "gh/gpt-6-luna"
        assert body["max_tokens"] == 1024
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json=response())

    result = await OpenAICompatibleChatModel(transport=httpx.MockTransport(handle)).complete(
        [ChatMessage("user", "synthetic")],
        request(),
    )
    assert result.total_tokens is None and result.prompt_tokens is None
    assert "test-secret" not in repr(request())
    assert len(calls) == 1


@pytest.mark.parametrize(
    "status,body,code",
    [
        (401, {}, "chat_provider_auth_failed"),
        (429, {}, "chat_provider_rate_limited"),
        (503, {}, "chat_provider_unavailable"),
        (302, {}, "chat_provider_rejected"),
        (200, {"choices": []}, "chat_response_invalid"),
        (200, response(finish="length"), "chat_output_truncated"),
        (200, response(content=" "), "chat_response_empty"),
        (200, response(finish="tool_calls"), "chat_response_incomplete"),
    ],
)
@pytest.mark.asyncio
async def test_chat_error_retains_raw_and_never_retries(status, body, code):
    raw = json.dumps(body).encode()
    calls = []

    def handle(r):
        calls.append(r)
        return httpx.Response(status, content=raw, headers={"location": "http://forbidden.example"})

    with pytest.raises(ChatResponseError) as caught:
        await OpenAICompatibleChatModel(transport=httpx.MockTransport(handle)).complete(
            [ChatMessage("user", "synthetic")],
            request(),
        )
    assert caught.value.code == code and caught.value.raw_body == raw
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_chat_timeout_is_uncertain_and_does_not_leak_exception():
    def handle(r):
        raise httpx.ReadTimeout("private detail test-secret", request=r)

    with pytest.raises(AppException) as caught:
        await OpenAICompatibleChatModel(transport=httpx.MockTransport(handle)).complete(
            [ChatMessage("user", "synthetic")],
            request(),
        )
    assert caught.value.code == "chat_provider_uncertain"
    assert "test-secret" not in caught.value.detail


@pytest.mark.asyncio
async def test_explicit_output_schema_is_sent_without_fallback():
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    calls = []

    def handle(r):
        calls.append(json.loads(r.content))
        return httpx.Response(400, json={"error": "unsupported"})

    with pytest.raises(ChatResponseError):
        await OpenAICompatibleChatModel(transport=httpx.MockTransport(handle)).complete(
            [ChatMessage("user", "synthetic")], request(output_schema=schema)
        )
    assert len(calls) == 1
    assert calls[0]["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "qnu_output", "schema": schema, "strict": True},
    }
