"""Provider probes must prove capability, not merely an HTTP200 or a catalogue hit."""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.modules.modelops.providers.gemini_adapter import GeminiAdapter
from app.modules.modelops.schemas import ChatMessage
from app.modules.modelops.services.chat_probe import probe_chat


def transport(monkeypatch, server):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(server))
    )


@pytest.mark.asyncio
async def test_probe_retries_truncated_empty_answer_with_same_alias(monkeypatch):
    calls = []

    def server(request):
        body = json.loads(request.content)
        calls.append(body)
        if len(calls) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {"content": "", "reasoning_content": "private"},
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "model": "served",
                "choices": [{"finish_reason": "stop", "message": {"content": "OK"}}],
            },
        )

    transport(monkeypatch, server)
    result = await probe_chat("custom", "vendor/opaque[1m]", "http://gateway/v1", "fixture-key")
    assert result["success"]
    assert [c["max_tokens"] for c in calls] == [32, 256]
    assert all(c["model"] == "vendor/opaque[1m]" and c["stream"] is False for c in calls)
    assert result["served_model"] == "served"


@pytest.mark.asyncio
async def test_probe_budget_retry_is_bounded_and_not_protocol_error(monkeypatch):
    calls = []

    def server(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": "", "reasoning_content": "private"},
                    }
                ]
            },
        )

    transport(monkeypatch, server)
    result = await probe_chat("custom", "opaque", "http://gateway/v1", "fixture-key")
    assert not result["success"]
    assert result["error_code"] == "MODEL_OUTPUT_BUDGET_EXHAUSTED"
    assert result["http_status"] == 200
    assert len(calls) == 2
    assert "private" not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "error"),
        (403, "error"),
        (404, "unavailable"),
        (410, "deprecated"),
        (402, "payment_required"),
        (429, "rate_limited"),
        (503, "temporarily_overloaded"),
    ],
)
async def test_probe_distinguishes_upstream_status(monkeypatch, status, expected):
    transport(
        monkeypatch,
        lambda r: httpx.Response(status, json={"error": {"message": "provider rejected"}}),
    )
    result = await probe_chat("custom", "opaque", "http://gateway/v1", "fixture-key")
    assert not result["success"] and result["status"] == expected
    assert result["http_status"] == status
    assert result["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_gemini_missing_model_never_silently_changes_model(monkeypatch):
    calls = []

    def server(request):
        calls.append(str(request.url))
        return httpx.Response(404, json={"error": {"message": "not found"}})

    transport(monkeypatch, server)
    with pytest.raises(httpx.HTTPStatusError):
        await GeminiAdapter("models/opaque", "fixture-key", "http://gemini/v1beta").generate(
            [ChatMessage(role="user", content="ping")]
        )
    assert len(calls) == 1
    assert calls[0].startswith("http://gemini/v1beta/models/opaque:generateContent")


@pytest.mark.asyncio
async def test_authoritative_inactive_key_pool_never_uses_legacy_secret():
    from app.modules.modelops.models import ModelProviderConfig, ProviderApiKey
    from app.modules.modelops.services.probe_credentials import select_probe_credential

    config = ModelProviderConfig(
        id="p", name="Gateway", provider_type="custom", api_key_encrypted="legacy", extra_config={}
    )
    key = ProviderApiKey(
        id="k",
        provider_id="p",
        name="key",
        api_key_encrypted="inactive",
        is_active=False,
        status="inactive",
    )
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [key]
    db.execute.return_value = result
    secret, account = await select_probe_credential(db, config)
    assert secret is None and account is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role,data,success",
    [
        ("embedding", {"data": [{"embedding": [0.2, 0.1]}]}, True),
        ("embedding", {"data": [{"embedding": [True]}]}, False),
        ("embedding", {"data": []}, False),
        ("reranker", {"results": [{"index": 0, "relevance_score": 0.8}]}, True),
        ("reranker", {"results": [{"index": 2, "relevance_score": 0.8}]}, False),
        ("reranker", {"results": [{"index": 0, "relevance_score": "0.8"}]}, False),
        ("ocr", {"data": [{"id": "opaque"}]}, True),
        ("ocr", {"data": [{"id": "other"}]}, False),
    ],
)
async def test_role_probe_validates_actual_structure(monkeypatch, role, data, success):
    from app.modules.modelops.services.provider_service import provider_service

    calls = []

    def server(request):
        calls.append(request)
        return httpx.Response(200, json=data)

    transport(monkeypatch, server)
    result = await provider_service._ping_single_model(
        "custom", "opaque", "http://gateway/api", "fixture-key", probe_role=role
    )
    assert result["success"] is success
    assert str(calls[0].url).startswith("http://gateway/api/")
    if role != "ocr":
        assert json.loads(calls[0].content)["model"] == "opaque"
    else:
        assert result["verification_scope"] == "catalogue"


@pytest.mark.asyncio
async def test_model_spelling_does_not_select_embedding_endpoint(monkeypatch):
    from app.modules.modelops.services.provider_service import provider_service

    def server(request):
        assert request.url.path == "/v1/chat/completions"
        assert json.loads(request.content)["model"] == "vendor/bge-looking-chat"
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    transport(monkeypatch, server)
    result = await provider_service._ping_single_model(
        "custom", "vendor/bge-looking-chat", "http://gateway/v1", "fixture-key"
    )
    assert result["success"]


@pytest.mark.asyncio
async def test_http200_html_catalogue_is_not_healthy(monkeypatch):
    from app.modules.modelops.services.provider_service import provider_service

    transport(monkeypatch, lambda r: httpx.Response(200, text="<html>login</html>"))
    success, _, _ = await provider_service._ping_provider_api(
        "custom", "http://gateway/v1", "fixture-test-key"
    )
    assert not success


@pytest.mark.asyncio
async def test_network_failure_is_truthful(monkeypatch):
    def server(request):
        raise httpx.ConnectError("offline", request=request)

    transport(monkeypatch, server)
    result = await probe_chat("custom", "opaque", "http://gateway/v1", "fixture-key")
    assert result["error_code"] == "PROVIDER_CONNECTION_ERROR" and not result["success"]


@pytest.mark.asyncio
async def test_probe_timeout_is_bounded(monkeypatch):
    import asyncio

    async def server(request):
        await asyncio.sleep(0.1)
        return httpx.Response(200, json={})

    transport(monkeypatch, server)
    result = await probe_chat(
        "custom", "opaque", "http://gateway/v1", "fixture-key", timeout_seconds=0.01
    )
    assert result["error_code"] == "PROVIDER_TIMEOUT"


@pytest.mark.asyncio
async def test_native_anthropic_headers_and_text_only(monkeypatch):
    def server(request):
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "fixture-key"
        assert json.loads(request.content)["model"] == "opaque"
        return httpx.Response(
            200,
            json={
                "model": "served",
                "content": [
                    {"type": "thinking", "thinking": "private"},
                    {"type": "text", "text": "OK"},
                ],
                "usage": {"input_tokens": 3, "output_tokens": 1},
            },
        )

    transport(monkeypatch, server)
    result = await probe_chat("claude", "opaque", "http://anthropic/v1", "fixture-key")
    assert result["success"] and result["served_model"] == "served" and "private" not in str(result)


@pytest.mark.asyncio
async def test_gemini_thought_is_not_answer_and_custom_budget_is_preserved(monkeypatch):
    def server(request):
        assert json.loads(request.content)["generationConfig"]["maxOutputTokens"] == 32
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"thought": True, "text": "private"}]},
                    }
                ]
            },
        )

    transport(monkeypatch, server)
    result = await probe_chat("gemini", "opaque", "http://gemini/v1beta", "fixture-key")
    assert not result["success"] and "private" not in str(result)


@pytest.mark.asyncio
async def test_runtime_does_not_retry_reasoning_only_response(monkeypatch):
    from app.core.exceptions import AppException
    from app.modules.modelops.providers.openai_adapter import OpenAIAdapter

    calls = []

    def server(request):
        calls.append(request)
        return httpx.Response(
            200, json={"choices": [{"finish_reason": "length", "message": {"content": ""}}]}
        )

    transport(monkeypatch, server)
    with pytest.raises(AppException) as error:
        await OpenAIAdapter("opaque", "fixture-key", "http://gateway/v1").generate(
            [ChatMessage(role="user", content="ping")], max_tokens=32
        )
    assert error.value.code == "MODEL_OUTPUT_BUDGET_EXHAUSTED" and len(calls) == 1


@pytest.mark.asyncio
async def test_unsupported_temperature_value_uses_parameter_evidence(monkeypatch):
    calls = []
    def server(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if "temperature" in payload:
            return httpx.Response(400, json={"error": {"message": "Unsupported value: 'temperature' does not support 0.2; only the default value is supported."}})
        return httpx.Response(200, json={"model": "actual", "choices": [{"message": {"content": "OK"}}]})
    transport(monkeypatch, server)
    result = await probe_chat("openai", "opaque", "http://gateway/v1", "fixture-key")
    assert result["success"] and len(calls) == 2
    assert calls[0]["model"] == calls[1]["model"] == "opaque"


@pytest.mark.asyncio
async def test_provider_catalogue_db_down_does_not_look_empty():
    from app.core.exceptions import AppException
    from app.modules.modelops.services.provider_service import provider_service
    db = AsyncMock()
    db.execute.side_effect = ConnectionError("fixture DB down")
    with pytest.raises(AppException) as error:
        await provider_service.get_active_providers(db)
    assert error.value.code == "PROVIDER_CATALOGUE_UNAVAILABLE"


def test_persisted_role_controls_runtime_chat_route():
    from app.modules.modelops.services.chat_routes import is_chat_model
    provider = {"model_specs": {"opaque": {"type": "text"}}, "model_capabilities": {"opaque": {"probe_role": "reranker"}}}
    assert not is_chat_model(provider, "opaque")
    provider["model_capabilities"]["opaque"]["probe_role"] = "chat"
    assert is_chat_model(provider, "opaque")


@pytest.mark.parametrize("url", ["localhost:20128", "ftp://gateway/v1", "http://user:secret@gateway/v1", "http://gateway:invalid/v1", "http://gateway/v1?key=secret"])
def test_invalid_base_urls_are_rejected_before_saving(url):
    from pydantic import ValidationError

    from app.modules.modelops.schemas import ProviderConfigUpdate
    with pytest.raises(ValidationError):
        ProviderConfigUpdate(api_base_url=url)


def test_exact_aliases_are_trimmed_and_deduplicated_not_rewritten():
    from app.modules.modelops.schemas import ProviderConfigUpdate
    config = ProviderConfigUpdate(models=[" vendor/opaque[1m] ", "vendor/opaque[1m]"])
    assert config.models == ["vendor/opaque[1m]"]
