"""Persist observed, credential-free request capabilities per provider/alias."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modelops.models import ModelProviderConfig


def load_chat_capabilities(extra: dict | None, model: str, endpoint: str | None) -> dict[str, Any]:
    record = ((extra or {}).get("chat_request_contracts") or {}).get(model, {})
    if record.get("endpoint") != endpoint:
        return {}
    return dict(record.get("capabilities") or {})


async def save_chat_capabilities(
    db: AsyncSession,
    provider_id: str,
    model: str,
    endpoint: str | None,
    capabilities: dict[str, Any],
) -> None:
    if not isinstance(capabilities, dict) or not capabilities:
        return
    provider = (
        await db.execute(
            select(ModelProviderConfig)
            .where(ModelProviderConfig.id == provider_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if provider is None or provider.api_base_url != endpoint:
        return  # A run must not attach old-endpoint observations to new config.
    extra = deepcopy(provider.extra_config or {})
    contracts = extra.setdefault("chat_request_contracts", {})
    contracts[model] = {
        "endpoint": endpoint,
        "capabilities": capabilities,
        "observed_at": datetime.now(UTC).isoformat(),
    }
    provider.extra_config = extra
    await db.commit()


async def save_connection_observation(
    db: AsyncSession, provider_id: str, endpoint: str | None, result: dict[str, Any]
) -> None:
    provider = (
        await db.execute(
            select(ModelProviderConfig)
            .where(ModelProviderConfig.id == provider_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if provider is None or provider.api_base_url != endpoint:
        return
    extra = deepcopy(provider.extra_config or {})
    extra["last_connection_test"] = {
        "success": result["success"],
        "latency_ms": result["latency_ms"],
        "tested_at": datetime.now(UTC).isoformat(),
    }
    provider.extra_config = extra
    await db.commit()
