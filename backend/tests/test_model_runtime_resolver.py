"""Tests for resolving embedding and reranker providers from ModelOps."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.services.model_runtime_resolver import ModelRuntimeResolver


def _query_result(record: ModelProviderConfig | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = record
    return result


@pytest.mark.asyncio
async def test_resolve_embedding_runtime_from_persisted_modelops_config() -> None:
    defaults = ModelProviderConfig(
        id="system_model_defaults",
        name="System defaults",
        provider_type="system_routing",
        extra_config={
            "defaults": {
                "default_embedding_provider_id": "prov_cf_custom",
                "default_embedding_model": "@cf/baai/bge-m3",
            }
        },
    )
    provider = ModelProviderConfig(
        id="prov_cf_custom",
        name="Cloudflare Workers AI",
        provider_type="cloudflare",
        is_active=True,
        timeout_seconds=25,
        api_key_encrypted="fallback-token",
        extra_config={
            "account_id": "account-from-provider",
            "api_keys": [
                {
                    "api_key": "disabled-token",
                    "is_active": False,
                    "status": "disabled",
                    "priority": 1,
                },
                {
                    "api_key": "active-token",
                    "account_id": "account-from-key",
                    "is_active": True,
                    "status": "active",
                    "priority": 2,
                },
            ],
        },
    )
    db = AsyncMock()
    db.execute.side_effect = [_query_result(defaults), _query_result(provider)]

    runtime = await ModelRuntimeResolver().resolve(db, "embedding")

    assert runtime.provider_id == "prov_cf_custom"
    assert runtime.provider_type == "cloudflare"
    assert runtime.model_name == "@cf/baai/bge-m3"
    assert runtime.api_key == "active-token"
    assert runtime.account_id == "account-from-key"
    assert runtime.timeout_seconds == 25


@pytest.mark.asyncio
async def test_resolve_runtime_rejects_missing_default_provider() -> None:
    defaults = ModelProviderConfig(
        id="system_model_defaults",
        name="System defaults",
        provider_type="system_routing",
        extra_config={
            "defaults": {
                "default_embedding_provider_id": "prov_missing",
                "default_embedding_model": "@cf/baai/bge-m3",
            }
        },
    )
    db = AsyncMock()
    db.execute.side_effect = [_query_result(defaults), _query_result(None)]

    with pytest.raises(AppException) as exc_info:
        await ModelRuntimeResolver().resolve(db, "embedding")

    assert exc_info.value.code == "MODEL_PROVIDER_NOT_AVAILABLE"
