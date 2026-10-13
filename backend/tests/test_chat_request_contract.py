"""Real HTTP-contract regressions; no production mock/fallback success paths."""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.exceptions import AppException
from app.modules.modelops.providers.openai_adapter import OpenAIAdapter
from app.modules.modelops.schemas import ChatMessage
from app.modules.modelops.services.provider_service import provider_service


@pytest.mark.asyncio
async def test_generate_negotiates_parameter_without_changing_alias(monkeypatch):
    requests = []

    def server(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["model"] == "vendor/arbitrary-alias[large]"
        assert payload["stream"] is False
        if "temperature" in payload:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "Unsupported parameter: 'temperature' is not supported with this model."
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "model": "served-alias",
                "choices": [{"message": {"content": "OK"}}],
                "usage": {"total_tokens": 8},
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(server))
    )
    adapter = OpenAIAdapter(
        "vendor/arbitrary-alias[large]", "real-fixture-key", "http://gateway/v1"
    )
    result = await adapter.generate([ChatMessage(role="user", content="ping")], max_tokens=32)
    assert result.content == "OK"
    assert result.model == "served-alias"
    assert len(requests) == 2
    assert adapter.request_capabilities["temperature_supported"] is False


@pytest.mark.asyncio
async def test_probe_and_runtime_share_valid_request(monkeypatch):
    requests = []

    def server(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if payload["max_tokens"] < 48:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "Invalid 'max_output_tokens': integer below minimum value. Expected a value >= 48."
                    }
                },
            )
        return httpx.Response(
            200, json={"model": "arbitrary", "choices": [{"message": {"content": "OK"}}]}
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(server))
    )
    result = await provider_service._ping_single_model(
        "custom", "arbitrary", "http://gateway/v1", "real-fixture-key"
    )
    assert result["success"] is True
    assert result["request_capabilities"]["minimum_output_tokens"] == 48
    assert all(payload["stream"] is False for payload in requests)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,headers",
    [
        ({"choices": []}, {}),
        ({"choices": [{"message": {"content": ""}}]}, {}),
        ({"error": {"message": "upstream failed"}}, {}),
        (
            {"choices": [{"message": {"content": "not a JSON completion"}}]},
            {"content-type": "text/event-stream"},
        ),
    ],
)
async def test_http_200_is_not_automatically_success(monkeypatch, data, headers):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data, headers=headers))
        ),
    )
    with pytest.raises(AppException):
        await OpenAIAdapter("arbitrary", "real-fixture-key", "http://gateway/v1").generate(
            [ChatMessage(role="user", content="ping")]
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 429, 500])
async def test_transport_failures_are_not_adapted_or_hidden(monkeypatch, status):
    calls = []

    def server(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "failed"}})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(server))
    )
    with pytest.raises(httpx.HTTPStatusError):
        await OpenAIAdapter("arbitrary", "real-fixture-key", "http://gateway/v1").generate(
            [ChatMessage(role="user", content="ping")]
        )
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_save_observed_contract_preserves_provider_settings():
    from app.modules.modelops.models import ModelProviderConfig
    from app.modules.modelops.services.chat_capabilities import save_chat_capabilities

    provider = ModelProviderConfig(
        id="provider",
        name="Gateway",
        provider_type="custom",
        api_base_url="http://a/v1",
        extra_config={"models": ["arbitrary"], "other_setting": {"keep": True}},
    )
    original_extra = provider.extra_config
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = provider
    db.execute.return_value = result
    await save_chat_capabilities(
        db, "provider", "arbitrary", "http://a/v1", {"temperature_supported": False}
    )
    assert provider.extra_config["other_setting"] == {"keep": True}
    assert "chat_request_contracts" not in original_extra
    assert (
        provider.extra_config["chat_request_contracts"]["arbitrary"]["capabilities"][
            "temperature_supported"
        ]
        is False
    )
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unrelated_http400_is_not_adapted(monkeypatch):
    calls = []

    def server(request):
        calls.append(request)
        return httpx.Response(
            400, json={"error": {"message": "Model is not enabled for your account."}}
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(server))
    )
    with pytest.raises(httpx.HTTPStatusError):
        await OpenAIAdapter("arbitrary", "real-fixture-key", "http://gateway/v1").generate(
            [ChatMessage(role="user", content="ping")]
        )
    assert len(calls) == 1


def test_error_detail_redacts_credentials_and_urls():
    from app.modules.modelops.providers.chat_contract import safe_error_message

    response = httpx.Response(
        400,
        json={
            "error": {
                "message": "Unsupported parameter: 'temperature'; real-secret at https://gateway/key?token=value"
            }
        },
    )
    text = safe_error_message(response, "real-secret")
    assert "real-secret" not in text and "token=value" not in text
    assert "temperature" in text


def test_capability_observation_is_bound_to_exact_alias_and_endpoint():
    from app.modules.modelops.services.chat_capabilities import load_chat_capabilities

    extra = {
        "chat_request_contracts": {
            "vendor/alias": {
                "endpoint": "http://a/v1",
                "capabilities": {"temperature_supported": False},
            }
        }
    }
    assert load_chat_capabilities(extra, "vendor/alias", "http://a/v1") == {
        "temperature_supported": False
    }
    assert load_chat_capabilities(extra, "vendor/other", "http://a/v1") == {}
    assert load_chat_capabilities(extra, "vendor/alias", "http://b/v1") == {}


@pytest.mark.asyncio
async def test_runtime_does_not_increase_user_token_budget(monkeypatch):
    def server(request):
        return httpx.Response(
            400, json={"error": {"message": "Invalid 'max_tokens': Expected a value >= 100."}}
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(server))
    )
    with pytest.raises(httpx.HTTPStatusError):
        await OpenAIAdapter("arbitrary", "real-fixture-key", "http://gateway/v1").generate(
            [ChatMessage(role="user", content="ping")], max_tokens=32
        )


@pytest.mark.asyncio
async def test_stream_negotiation_and_actual_usage(monkeypatch):
    requests = []

    def server(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["stream"] is True
        if "temperature" in payload:
            return httpx.Response(
                400, json={"error": {"message": "Unsupported parameter: 'temperature'."}}
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content='data: {"model":"actual","choices":[{"delta":{"content":"OK"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}\n\ndata: [DONE]\n\n',
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(server))
    )
    adapter = OpenAIAdapter("arbitrary", "real-fixture-key", "http://gateway/v1")
    assert (
        "".join(
            [chunk async for chunk in adapter.stream([ChatMessage(role="user", content="ping")])]
        )
        == "OK"
    )
    assert len(requests) == 2
    assert adapter.served_model == "actual"
    assert adapter.stream_usage["total_tokens"] == 3


@pytest.mark.asyncio
async def test_partial_stream_error_does_not_replay_generate(monkeypatch):
    calls = []

    def server(request):
        calls.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content='data: {"choices":[{"delta":{"content":"partial"}}]}\n\ndata: invalid\n\n',
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(server))
    )
    chunks = []
    with pytest.raises(AppException):
        async for chunk in OpenAIAdapter(
            "arbitrary", "real-fixture-key", "http://gateway/v1"
        ).stream([ChatMessage(role="user", content="ping")]):
            chunks.append(chunk)
    assert chunks == ["partial"]
    assert len(calls) == 1
