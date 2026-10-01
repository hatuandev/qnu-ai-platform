"""Regression tests for production ModelOps API-key rotation behavior."""

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

    assert changed is True
    assert keys[0]["status"] == "exhausted"
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
