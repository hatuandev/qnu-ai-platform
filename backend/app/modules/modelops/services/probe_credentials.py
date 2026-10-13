"""Read-only key selection; relational pool is authoritative even when unusable."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modelops.models import ModelProviderConfig, ProviderApiKey


async def select_probe_credential(
    db: AsyncSession,
    config: ModelProviderConfig,
) -> tuple[str | None, str | None]:
    keys = (
        (
            await db.execute(
                select(ProviderApiKey)
                .where(
                    ProviderApiKey.provider_id == config.id,
                )
                .order_by(ProviderApiKey.priority, ProviderApiKey.id)
            )
        )
        .scalars()
        .all()
    )
    now = datetime.now(UTC)
    if keys:
        for key in keys:
            if (
                key.is_active
                and (
                    key.status == "active"
                    or (key.status == "rate_limited" and key.cooldown_until is not None)
                )
                and (key.cooldown_until is None or key.cooldown_until <= now)
                and (key.quota_limit is None or (key.usage_tokens or 0) < key.quota_limit)
            ):
                return key.api_key_encrypted, key.account_id or (config.extra_config or {}).get(
                    "account_id"
                )
        return None, None
    extra = config.extra_config or {}
    legacy = extra.get("api_keys", [])
    for key in legacy:
        if (
            key.get("is_active", True)
            and key.get("status", "active") == "active"
            and not key.get("cooldown_until")
            and (key.get("quota_limit") is None or key.get("usage_tokens", 0) < key["quota_limit"])
            and key.get("api_key")
        ):
            return key["api_key"], key.get("account_id") or extra.get("account_id")
    return (None if legacy else config.api_key_encrypted), extra.get("account_id")
