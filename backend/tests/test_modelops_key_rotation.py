"""Regression tests for production ModelOps API-key rotation behavior."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import HTTPStatusError, Request, Response

from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig, TenantQuota
from app.modules.modelops.providers.base import LLMResponse
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.modelops.services.key_rotation import (
    classify_key_failure,
    describe_provider_failure,
)


def _http_error(
    status_code: int,
    payload: dict,
    *,
    retry_after: str | None = None,
) -> HTTPStatusError:
    request = Request("POST", "https://provider.example/v1/chat/completions")
    headers = {"Retry-After": retry_after} if retry_after else None
    response = Response(status_code, request=request, headers=headers, json=payload)
    return HTTPStatusError(
        f"HTTP {status_code}",
        request=request,
        response=response,
    )


def test_key_failure_classifier_uses_retry_after() -> None:
    error = _http_error(
        429,
        {"error": {"code": "rate_limit_exceeded"}},
        retry_after="17",
    )
    failure = classify_key_failure(error)

    assert failure.state == "rate_limited"
    assert failure.retry_after_seconds == 17
    assert "provider.example" not in describe_provider_failure(error)


def test_key_failure_classifier_distinguishes_hard_quota_and_invalid_key() -> None:
    quota_failure = classify_key_failure(
        _http_error(429, {"error": {"code": "insufficient_quota"}})
    )
    invalid_failure = classify_key_failure(
        _http_error(401, {"error": {"code": "invalid_api_key"}})
    )

    assert quota_failure.state == "exhausted"
    assert quota_failure.retry_after_seconds is None
    assert invalid_failure.state == "invalid"


@pytest.mark.parametrize("status", [402, 403, 429])
def test_hard_quota_is_exhausted_regardless_of_http_status(status: int) -> None:
    failure = classify_key_failure(_http_error(status, {"error": {"code": "insufficient_quota"}}))
    assert failure.state == "exhausted"


def test_http_402_is_always_treated_as_hard_quota() -> None:
    failure = classify_key_failure(_http_error(402, {"detail": "Payment required"}))
    assert failure.state == "exhausted"
    assert failure.reason == "provider_quota_exhausted"


def test_http_403_with_quota_context_is_hard_quota() -> None:
    failure = classify_key_failure(
        _http_error(403, {"error": {"message": "Project has exceeded its current quota"}})
    )
    assert failure.state == "exhausted"
    assert failure.reason == "provider_quota_exhausted"


def test_http_403_without_quota_context_is_request_failed() -> None:
    failure = classify_key_failure(
        _http_error(403, {"error": {"message": "Access denied for this resource"}})
    )
    assert failure.state is None
    assert failure.reason == "provider_request_failed"


def test_key_pool_skips_key_without_enough_configured_quota() -> None:
    keys = [
        {
            "id": "key-1",
            "priority": 1,
            "is_active": True,
            "status": "active",
            "usage_tokens": 900,
            "quota_limit": 1_000,
        },
        {
            "id": "key-2",
            "priority": 2,
            "is_active": True,
            "status": "active",
            "usage_tokens": 0,
            "quota_limit": 10_000,
        },
    ]

    available, changed = modelops_service._inference._prepare_available_keys(
        keys, estimated_tokens=200
    )

    assert changed is False
    assert keys[0]["status"] == "active"
    assert [key["id"] for key in available] == ["key-2"]


@pytest.mark.asyncio
async def test_generate_rotates_from_rate_limited_key_and_persists_state() -> None:
    provider_config = ModelProviderConfig(
        id="provider-rotation-test",
        name="Rotation Test Provider",
        provider_type="openai",
        model_name="dynamic-chat-model",
        api_base_url="https://provider.example/v1",
        api_key_encrypted="key-one",
        priority=1,
        is_active=True,
        timeout_seconds=15,
        extra_config={
            "models": ["dynamic-chat-model"],
            "api_keys": [
                {
                    "id": "key-1",
                    "name": "Key 1",
                    "api_key": "key-one",
                    "priority": 1,
                    "is_active": True,
                    "status": "active",
                    "usage_tokens": 0,
                },
                {
                    "id": "key-2",
                    "name": "Key 2",
                    "api_key": "key-two",
                    "priority": 2,
                    "is_active": True,
                    "status": "active",
                    "usage_tokens": 0,
                },
            ],
        },
    )
    provider = {
        "id": provider_config.id,
        "name": provider_config.name,
        "provider_type": provider_config.provider_type,
        "model_name": provider_config.model_name,
        "models": ["dynamic-chat-model"],
        "api_key": "key-one",
        "api_base_url": provider_config.api_base_url,
        "timeout_seconds": provider_config.timeout_seconds,
        "is_active": True,
        "api_keys": provider_config.extra_config["api_keys"],
    }
    quota = TenantQuota(
        tenant_id="rotation-test",
        month_period="2026-10",
        monthly_token_limit=1_000_000,
        monthly_cost_limit_usd=50.0,
        tokens_used=0,
        cost_used_usd=0.0,
        is_blocked=False,
    )
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 0
    result.scalar_one_or_none.return_value = provider_config
    db.execute.return_value = result
    attempted_keys: list[str] = []

    class Adapter:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        async def generate(self, **_: object) -> LLMResponse:
            attempted_keys.append(self.api_key)
            if self.api_key == "key-one":
                raise _http_error(
                    429,
                    {"error": {"code": "rate_limit_exceeded"}},
                    retry_after="23",
                )
            return LLMResponse(
                content="Phản hồi từ key 2",
                provider="openai",
                model="dynamic-chat-model",
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                latency_ms=25.0,
            )

    def adapter_factory(*_: object, api_key: str, **__: object) -> Adapter:
        return Adapter(api_key)

    request = LLMGenerateRequest(
        messages=[ChatMessage(role="user", content="Kiểm tra xoay khóa")],
        tenant_id="rotation-test",
        preferred_provider_id=provider_config.id,
        preferred_model_name="dynamic-chat-model",
        max_tokens=200,
    )

    with (
        patch.object(
            modelops_service,
            "check_quota_available",
            new_callable=AsyncMock,
            return_value=quota,
        ),
        patch.object(
            modelops_service,
            "get_active_providers",
            new_callable=AsyncMock,
            return_value=[provider],
        ),
        patch.object(
            modelops_service,
            "record_usage_log",
            new_callable=AsyncMock,
        ),
        patch("app.modules.modelops.service.get_llm_adapter", side_effect=adapter_factory),
    ):
        response = await modelops_service.generate(db, request)

    stored_keys = provider_config.extra_config["api_keys"]
    assert attempted_keys == ["key-one", "key-two"]
    assert response.active_key_id == "key-2"
    assert stored_keys[0]["status"] == "rate_limited"
    assert stored_keys[0]["cooldown_until"] is not None
    assert stored_keys[1]["usage_tokens"] == 30
    assert db.commit.await_count >= 2


@pytest.mark.asyncio
async def test_provider_secrets_are_write_only() -> None:
    with pytest.raises(AppException) as exc_info:
        await modelops_service.reveal_provider_key(
            AsyncMock(), "provider-id", "key-id"
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "KEY_REVEAL_DISABLED"


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_cancelled_chat_releases_managed_key(stream: bool) -> None:
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        LeasedProviderKey,
        provider_key_rotation_service,
    )
    lease = LeasedProviderKey("cancel-key", "cancel-provider", "Key", "secret", None, "lease-token")
    provider = {"id": lease.provider_id, "name": "Cancellation verification",
                "provider_type": "custom", "model_name": "user-selected-model",
                "models": ["user-selected-model"], "api_key": "secret",
                "api_base_url": None, "timeout_seconds": 15}
    quota = TenantQuota(tokens_used=0, cost_used_usd=0, monthly_token_limit=100000, is_blocked=False)
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    class Adapter:
        async def generate(self, **kwargs):
            raise asyncio.CancelledError()
        async def stream(self, **kwargs):
            raise asyncio.CancelledError()
            yield "unreachable"

    request = LLMGenerateRequest(messages=[ChatMessage(role="user", content="cancel")], preferred_provider_id=lease.provider_id)
    with (
        patch.object(modelops_service, "check_quota_available", AsyncMock(return_value=quota)),
        patch.object(modelops_service, "get_active_providers", AsyncMock(return_value=[provider])),
        patch("app.modules.modelops.service.get_llm_adapter", return_value=Adapter()),
        patch.object(provider_key_rotation_service, "acquire", AsyncMock(return_value=KeyAcquireResult(True, lease))),
        patch.object(provider_key_rotation_service, "release", AsyncMock(return_value=True)) as release,
    ):
        with pytest.raises(asyncio.CancelledError):
            if stream:
                async for _ in modelops_service.generate_stream(db, request):
                    pass
            else:
                await modelops_service.generate(db, request)
        release.assert_awaited_once_with(db, lease)


@pytest.mark.asyncio
@pytest.mark.parametrize("partial", [False, True])
async def test_managed_stream_rotates_only_before_first_token(partial: bool) -> None:
    from app.modules.modelops.services.provider_key_rotation_service import (
        KeyAcquireResult,
        LeasedProviderKey,
        provider_key_rotation_service,
    )
    leases = [LeasedProviderKey(f"stream-key-{n}", "stream-provider", f"Key {n}", f"secret-{n}", None, f"lease-{n}") for n in (1, 2)]
    provider = {"id": "stream-provider", "name": "Stream verification", "provider_type": "custom",
                "model_name": "dynamic-stream-model", "models": ["dynamic-stream-model"],
                "api_key": "secret-1", "api_base_url": None, "timeout_seconds": 15}
    quota = TenantQuota(tokens_used=0, cost_used_usd=0, monthly_token_limit=100000, is_blocked=False)
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    attempted = []
    error = _http_error(429, {"error": {"code": "rate_limit_exceeded"}})

    class Adapter:
        def __init__(self, key): self.key = key
        async def stream(self, **kwargs):
            attempted.append(self.key)
            if self.key == "secret-1":
                if partial: yield "prefix"
                raise error
            yield "complete"

    request = LLMGenerateRequest(messages=[ChatMessage(role="user", content="stream")], preferred_provider_id="stream-provider", preferred_model_name="dynamic-stream-model")
    with (
        patch.object(modelops_service, "check_quota_available", AsyncMock(return_value=quota)),
        patch.object(modelops_service, "get_active_providers", AsyncMock(return_value=[provider])),
        patch("app.modules.modelops.service.get_llm_adapter", side_effect=lambda **kw: Adapter(kw["api_key"])),
        patch.object(provider_key_rotation_service, "acquire", AsyncMock(side_effect=[KeyAcquireResult(True, lease) for lease in leases])) as acquire,
        patch.object(provider_key_rotation_service, "complete_failure", AsyncMock(return_value=classify_key_failure(error))) as failure,
        patch.object(provider_key_rotation_service, "complete_success", AsyncMock(return_value=True)),
        patch.object(modelops_service._inference, "_call_record_usage_log", AsyncMock()),
    ):
        chunks = []
        async def consume():
            async for chunk in modelops_service.generate_stream(db, request): chunks.append(chunk)
        if partial:
            with pytest.raises(HTTPStatusError): await consume()
            assert chunks == ["prefix"]
            assert attempted == ["secret-1"]
            assert acquire.await_count == 1
        else:
            await consume()
            assert chunks == ["complete"]
            assert attempted == ["secret-1", "secret-2"]
            assert acquire.await_count == 2
        failure.assert_awaited_once_with(db, leases[0], error)
