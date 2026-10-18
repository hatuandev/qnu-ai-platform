"""Context-window overflow is a client budget error, never provider outage."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import HTTPStatusError, Request, Response

from app.core.exceptions import AppException
from app.modules.modelops.models import TenantQuota
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service

WINDOW_MESSAGE = (
    "This model's maximum context length is 8192 tokens. However, you requested "
    "1600 output tokens and your prompt contains at least 6593 input tokens. "
    "Please reduce the length of the input prompt or the number of requested output tokens."
)


def _overflow_error() -> HTTPStatusError:
    request = Request("POST", "https://internal.example/v1/chat/completions")
    response = Response(400, request=request, json={"error": {"message": WINDOW_MESSAGE}})
    return HTTPStatusError("HTTP 400", request=request, response=response)


def _upstream_error() -> HTTPStatusError:
    request = Request("POST", "https://internal.example/v1/chat/completions")
    response = Response(502, request=request, json={"error": {"message": "Bad gateway"}})
    return HTTPStatusError("HTTP 502", request=request, response=response)


def _provider(provider_id: str, model: str) -> dict:
    return {
        "id": provider_id,
        "name": provider_id,
        "provider_type": "custom",
        "model_name": model,
        "models": [model],
        "api_key": "secret",
        "api_base_url": "https://internal.example/v1",
        "timeout_seconds": 15,
    }


def _request() -> LLMGenerateRequest:
    return LLMGenerateRequest(
        messages=[ChatMessage(role="user", content="large evidence prompt")],
        preferred_provider_id="prov-a",
        preferred_model_name="m-a",
        fallback_provider_id="prov-b",
        fallback_model_name="m-b",
    )


def _patches(db, providers, adapter_factory):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    quota = TenantQuota(
        tokens_used=0, cost_used_usd=0, monthly_token_limit=100000, is_blocked=False
    )
    return [
        patch.object(modelops_service, "check_quota_available", AsyncMock(return_value=quota)),
        patch.object(modelops_service, "get_active_providers", AsyncMock(return_value=providers)),
        patch("app.modules.modelops.service.get_llm_adapter", side_effect=adapter_factory),
        patch("app.modules.modelops.services.inference_service.circuit_breaker_registry"),
    ]


def _breaker():
    breaker = MagicMock()
    breaker.can_execute.return_value = True
    return breaker


@pytest.mark.asyncio
async def test_overflow_alone_reports_context_not_unavailable_and_spares_breaker():
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        provider_key_rotation_service,
    )

    db = AsyncMock()
    adapters = {"secret": _overflow_error()}

    class Adapter:
        def __init__(self, key):
            self.key = key

        async def generate(self, **kwargs):
            raise adapters[self.key]

    patches = _patches(db, [_provider("prov-a", "m-a")], lambda **kw: Adapter(kw["api_key"]))
    breaker = _breaker()
    with patches[0], patches[1], patches[2], patches[3] as registry, patch.object(
        provider_key_rotation_service, "acquire",
        AsyncMock(return_value=KeyAcquireResult(False, None)),
    ):
        registry.get.return_value = breaker
        with pytest.raises(AppException) as error:
            await modelops_service.generate(db, _request())
    assert error.value.code == "MODEL_CONTEXT_EXCEEDED"
    breaker.record_failure.assert_not_called()
    breaker.record_success.assert_not_called()


@pytest.mark.asyncio
async def test_overflow_plus_upstream_keeps_outage_verdict_and_charges_only_outage():
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        provider_key_rotation_service,
    )

    db = AsyncMock()

    class Adapter:
        def __init__(self, key):
            self.key = key

        async def generate(self, **kwargs):
            raise _overflow_error() if self.key == "secret-a" else _upstream_error()

    providers = [_provider("prov-a", "m-a"), _provider("prov-b", "m-b")]
    providers[0]["api_key"] = "secret-a"
    providers[1]["api_key"] = "secret-b"
    patches = _patches(db, providers, lambda **kw: Adapter(kw["api_key"]))
    breaker = _breaker()
    with patches[0], patches[1], patches[2], patches[3] as registry, patch.object(
        provider_key_rotation_service, "acquire",
        AsyncMock(return_value=KeyAcquireResult(False, None)),
    ):
        registry.get.return_value = breaker
        with pytest.raises(AppException) as error:
            await modelops_service.generate(db, _request())
    assert error.value.code == "ALL_PROVIDERS_UNAVAILABLE"
    breaker.record_failure.assert_called_once()
    breaker.record_success.assert_not_called()


@pytest.mark.asyncio
async def test_stream_overflow_after_first_token_never_appends_fallback():
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        LeasedProviderKey,
        provider_key_rotation_service,
    )

    lease = LeasedProviderKey("k1", "prov-a", "Key", "secret-a", None, "lease-1")

    class PrefixThenOverflowAdapter:
        async def stream(self, **kwargs):
            yield "prefix"
            raise _overflow_error()

    db = AsyncMock()
    factory = MagicMock(side_effect=lambda **kw: PrefixThenOverflowAdapter())
    patches = _patches(db, [_provider("prov-a", "m-a"), _provider("prov-b", "m-b")], factory)
    breaker = _breaker()
    with patches[0], patches[1], patches[2], patches[3] as registry, patch.object(
        provider_key_rotation_service, "acquire",
        AsyncMock(return_value=KeyAcquireResult(True, lease)),
    ), patch.object(
        provider_key_rotation_service, "release", AsyncMock(return_value=True),
    ) as release, patch.object(
        provider_key_rotation_service, "complete_failure", AsyncMock(),
    ) as failure:
        registry.get.return_value = breaker
        chunks = []
        with pytest.raises(HTTPStatusError):
            async for chunk in modelops_service.generate_stream(db, _request()):
                chunks.append(chunk)
    assert chunks == ["prefix"]  # emitted part kept, nothing appended
    assert factory.call_count == 1  # fallback route never attempted mid-stream
    breaker.record_failure.assert_not_called()  # no circuit charge for overflow
    failure.assert_not_awaited()  # credential state untouched
    release.assert_awaited_once_with(db, lease)  # lease freed exactly once


@pytest.mark.asyncio
async def test_stream_overflow_before_first_token_falls_back_per_policy():
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        LeasedProviderKey,
        provider_key_rotation_service,
    )

    leases = [LeasedProviderKey(f"k{n}", f"prov-{p}", "Key", f"secret-{p}", None, f"lease-{n}")
              for n, p in ((1, "a"), (2, "b"))]

    class OverflowAdapter:
        async def stream(self, **kwargs):
            raise _overflow_error()
            yield  # pragma: no cover - generator marker

    class CompleteAdapter:
        async def stream(self, **kwargs):
            yield "complete"

    def factory(**kwargs):
        return OverflowAdapter() if kwargs["api_key"] == "secret-a" else CompleteAdapter()

    db = AsyncMock()
    patches = _patches(db, [_provider("prov-a", "m-a"), _provider("prov-b", "m-b")], factory)
    breaker = _breaker()
    with patches[0], patches[1], patches[2], patches[3] as registry, patch.object(
        provider_key_rotation_service, "acquire",
        AsyncMock(side_effect=[KeyAcquireResult(True, lease) for lease in leases]),
    ), patch.object(
        provider_key_rotation_service, "release", AsyncMock(return_value=True),
    ) as release, patch.object(
        modelops_service._inference, "_call_record_usage_log", AsyncMock(),
    ):
        registry.get.return_value = breaker
        chunks = [chunk async for chunk in modelops_service.generate_stream(db, _request())]
    assert chunks == ["complete"]
    breaker.record_failure.assert_not_called()
    release.assert_awaited_once()  # only the overflowed route's lease


@pytest.mark.asyncio
async def test_lease_unavailable_route_is_skipped_with_traceable_reason(caplog):
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        provider_key_rotation_service,
    )

    db = AsyncMock()
    patches = _patches(
        db, [_provider("prov-a", "m-a")], lambda **kw: SimpleNamespace(generate=AsyncMock())
    )
    breaker = _breaker()
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3] as registry,
        caplog.at_level("WARNING"),
        patch.object(
            provider_key_rotation_service,
            "acquire",
            AsyncMock(return_value=KeyAcquireResult(True, None, True)),
        ),
    ):
        registry.get.return_value = breaker
        with pytest.raises(AppException) as error:
            await modelops_service.generate(db, _request())
    assert error.value.code == "ALL_PROVIDERS_UNAVAILABLE"
    assert "key_lease_unavailable" in caplog.text
    breaker.record_failure.assert_not_called()
