"""Server-owned inference restrictions and request budgets; no live services."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import AppException
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.rag.evidence_model import structured_call
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest


@pytest.mark.asyncio
async def test_rag_scope_blocks_external_fallback_at_inference_boundary():
    from app.modules.modelops.services.inference_policy import rag_chat_scope

    providers = [{"id": key, "name": key, "provider_type": "custom", "model_name": "m",
        "api_key": "secret", "models": ["m"], "api_base_url": "https://fake.invalid/v1",
        "timeout_seconds": 1} for key in ("internal", "external")]
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    req = LLMGenerateRequest(messages=[ChatMessage(role="user", content="private evidence")],
        preferred_provider_id="internal", preferred_model_name="m",
        fallback_provider_id="external", fallback_model_name="m")
    adapter = SimpleNamespace(generate=AsyncMock(side_effect=RuntimeError("upstream failed")))
    with (patch("app.modules.modelops.services.inference_policy.load_rag_provider_ids", AsyncMock(return_value=frozenset({"internal"}))),
          patch.object(modelops_service, "check_quota_available", AsyncMock()),
          patch.object(modelops_service, "get_active_providers", AsyncMock(return_value=providers)),
          patch("app.modules.modelops.service.get_llm_adapter", return_value=adapter) as factory,
          patch("app.modules.modelops.services.inference_service.circuit_breaker_registry") as breakers,
          patch("app.modules.modelops.services.provider_key_rotation_service.provider_key_rotation_service.acquire",
                AsyncMock(return_value=SimpleNamespace(managed=False, lease=None)))):
        breakers.get.return_value.can_execute.return_value = True
        async with rag_chat_scope():
            with pytest.raises(AppException):
                await modelops_service.generate(db, req)
    assert factory.call_count == 1
    assert factory.call_args.kwargs["base_url"] == providers[0]["api_base_url"]


@pytest.mark.asyncio
async def test_policy_is_server_owned_and_missing_policy_fails_closed():
    from app.modules.modelops.services.inference_policy import filter_chat_routes, rag_chat_scope

    with patch("app.modules.modelops.services.inference_policy.load_rag_provider_ids", AsyncMock(return_value=frozenset())):
        async with rag_chat_scope():
            with pytest.raises(AppException) as error:
                filter_chat_routes([({"id": "client-claimed-internal"}, "m")])
    assert error.value.code == "RAG_PROVIDER_NOT_ALLOWED"
    assert filter_chat_routes([({"id": "ordinary-modelops"}, "m")])


@pytest.mark.asyncio
async def test_ask_installs_policy_before_conversation_resolution():
    from app.modules.modelops.services.inference_policy import filter_chat_routes
    from app.modules.rag.service import RagService

    async def check(*args, **kwargs):
        with pytest.raises(AppException):
            filter_chat_routes([({"id": "external"}, "m")])
        return "guarded"
    with (patch("app.modules.modelops.services.inference_policy.load_rag_provider_ids", AsyncMock(return_value=frozenset({"internal"}))),
          patch.object(RagService, "_ask_conversation", side_effect=check)):
        assert await RagService().ask(None, AskRequest(question="hello", collection_id="test")) == "guarded"


@pytest.mark.asyncio
async def test_repair_keeps_full_contract_budget_even_with_many_invalid_fields():
    seen = []
    async def fake_generate(db, request):
        seen.append(request)
        content = json.dumps({f"extra_{i}": True for i in range(25)}) if len(seen) == 1 else '{"query":"ok"}'
        return SimpleNamespace(content=content, provider="fake", model="fake")
    with patch("app.modules.rag.evidence_model.modelops_service.generate", side_effect=fake_generate):
        result = await structured_call(None, AskRequest(question="test", collection_id="test"),
                                       QueryPlan, "Plan", {"evidence": "unchanged"}, max_tokens=500)
    assert result.query == "ok"
    assert [request.max_tokens for request in seen] == [500, 500]
    assert seen[0].messages[1].content == seen[1].messages[1].content


@pytest.mark.asyncio
async def test_one_transient_retry_keeps_payload_and_stops_after_second_failure():
    from app.modules.modelops.providers.chat_contract import post_chat
    from app.modules.modelops.services.inference_policy import transient_retry_scope

    seen = []
    async def handle(request):
        seen.append(request.content)
        return httpx.Response(502, json={"error": {"message": "private content must not be logged"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), timeout=2) as client:
        with transient_retry_scope(), pytest.raises(httpx.HTTPStatusError):
            await post_chat(client, "https://fake.invalid/v1/chat/completions", {}, {"messages": ["same"]}, {})
    assert len(seen) == 2 and seen[0] == seen[1]


def test_failure_diagnostics_never_include_response_body_or_secret():
    from app.modules.modelops.services.key_rotation import provider_failure_diagnostics

    request = httpx.Request("POST", "https://fake.invalid/v1/chat/completions")
    response = httpx.Response(502, request=request, json={"error": {"message": "SECRET private source"}},
                              headers={"x-request-id": "d345fa4c-bcd6-4ab6-a3d7-b06873ca195a"})
    result = provider_failure_diagnostics(httpx.HTTPStatusError("SECRET", request=request, response=response))
    assert result["http_status"] == 502 and result["upstream_request_id"]
    assert "SECRET" not in json.dumps(result) and "private source" not in json.dumps(result)


@pytest.mark.asyncio
async def test_long_required_quote_is_not_forced_into_a_256_token_repair():
    from pydantic import BaseModel, Field

    class Contract(BaseModel):
        quote: str = Field(min_length=1200)
    quote = "x" * 1200
    valid = json.dumps({"quote": quote})
    budgets = []
    async def generate(db, req):
        budgets.append(req.max_tokens)
        content = "{}" if len(budgets) == 1 else valid[:req.max_tokens * 3]
        return SimpleNamespace(content=content, provider="fake", model="fake")
    with patch("app.modules.rag.evidence_model.modelops_service.generate", side_effect=generate):
        result = await structured_call(None, AskRequest(question="quote", collection_id="test"), Contract,
                                       "Keep original quote", {"evidence": quote}, max_tokens=600)
    assert result.quote == quote and budgets == [600, 600]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 429])
async def test_nontransient_failures_never_retry(status):
    from app.modules.modelops.providers.chat_contract import post_chat
    from app.modules.modelops.services.inference_policy import transient_retry_scope

    requests = []
    def handler(req):
        requests.append(req)
        return httpx.Response(status, json={"error": {"message": "Rejected"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with transient_retry_scope(), pytest.raises(httpx.HTTPStatusError):
            await post_chat(client, "https://fake.invalid/v1/chat/completions", {}, {"max_tokens": 500}, {})
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_retry_budget_is_shared_across_calls_and_honors_retry_after():
    from app.modules.modelops.providers.chat_contract import post_chat
    from app.modules.modelops.services.inference_policy import transient_retry_scope

    requests = []
    def handler(req):
        requests.append(req)
        return httpx.Response(503, json={"error": {"message": "Temporary unavailable"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=2) as client:
        with transient_retry_scope():
            for _ in range(2):
                with pytest.raises(httpx.HTTPStatusError):
                    await post_chat(client, "https://fake.invalid/v1/chat/completions", {}, {"max_tokens": 500}, {})
    assert len(requests) == 3  # One total retry, not one per call/layer.
    requests.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: (requests.append(req), httpx.Response(503, headers={"retry-after": "60"}))[1]), timeout=1) as client:
        with transient_retry_scope(), pytest.raises(httpx.HTTPStatusError):
            await post_chat(client, "https://fake.invalid/v1/chat/completions", {}, {"max_tokens": 500}, {})
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_structured_context_negotiation_cannot_squeeze_required_output():
    from app.modules.modelops.providers.chat_contract import post_chat
    from app.modules.modelops.services.inference_policy import preserve_structured_output

    requests = []
    def handler(req):
        requests.append(req.url.path)
        if req.url.path == "/tokenize":
            return httpx.Response(200, json={"count": 7800, "max_model_len": 8192})
        return httpx.Response(400, json={"error": {"message":
            "maximum context length is 8192 tokens; prompt contains 7800 input tokens"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with preserve_structured_output(), pytest.raises(httpx.HTTPStatusError):
            await post_chat(client, "https://fake.invalid/v1/chat/completions", {},
                            {"model": "m", "messages": [], "max_tokens": 600}, {})
    assert requests == ["/v1/chat/completions"]  # No pointless tokenization: shrinking is forbidden.


@pytest.mark.asyncio
async def test_policy_file_errors_fail_closed_and_scopes_are_task_local(tmp_path):
    import asyncio

    from app.modules.modelops.services.inference_policy import (
        filter_chat_routes,
        load_rag_provider_ids,
        rag_chat_scope,
    )

    with (patch("app.modules.modelops.services.inference_policy.get_configs_dir", return_value=tmp_path),
          pytest.raises(AppException) as error):
        await load_rag_provider_ids()
    assert error.value.code == "RAG_INFERENCE_POLICY_UNAVAILABLE"

    ready, done = asyncio.Event(), asyncio.Event()
    async def restricted():
        async with rag_chat_scope():
            ready.set()
            await done.wait()
            with pytest.raises(AppException):
                filter_chat_routes([({"id": "external"}, "m")])
    with patch("app.modules.modelops.services.inference_policy.load_rag_provider_ids", AsyncMock(return_value=frozenset({"internal"}))):
        task = asyncio.create_task(restricted())
        await ready.wait()
        assert filter_chat_routes([({"id": "external"}, "m")])  # Unrelated request.
        done.set()
        await task


@pytest.mark.asyncio
async def test_stream_transient_headers_retry_but_never_retry_emitted_content(monkeypatch):
    from app.modules.modelops.providers.openai_adapter import OpenAIAdapter
    from app.modules.modelops.services.inference_policy import transient_retry_scope

    requests = []
    def handle(req):
        requests.append(req)
        if len(requests) == 1:
            return httpx.Response(502)
        return httpx.Response(200, headers={"content-type": "text/event-stream"},
            text='data: {"choices":[{"delta":{"content":"complete"},"finish_reason":null}]}\n\n'
                 'data: [DONE]\n\n')
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle)))
    adapter = OpenAIAdapter("m", "fixture-key", "https://fake.invalid/v1")
    with transient_retry_scope():
        output = [chunk async for chunk in adapter.stream([ChatMessage(role="user", content="test")])]
    assert output == ["complete"] and len(requests) == 2


@pytest.mark.asyncio
async def test_cancellation_during_backoff_is_not_retried():
    import asyncio
    import time

    from app.modules.modelops.services.inference_policy import (
        retry_transient_response,
        transient_retry_scope,
    )

    response = httpx.Response(502, request=httpx.Request("POST", "https://fake.invalid"))
    with (transient_retry_scope(), patch("app.modules.modelops.services.inference_policy.asyncio.sleep",
                                        AsyncMock(side_effect=asyncio.CancelledError)) as sleep):
        with pytest.raises(asyncio.CancelledError):
            await retry_transient_response(response, time.monotonic() + 2)
        assert not await retry_transient_response(response, time.monotonic() + 2)
    assert sleep.await_count == 1
