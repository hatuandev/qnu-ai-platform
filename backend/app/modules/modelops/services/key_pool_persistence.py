"""Keep transitional JSONB configuration aligned with authoritative key rows."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret
from app.modules.modelops.models import ModelProviderConfig, ProviderApiKey
from app.modules.modelops.services.provider_key_rotation_service import (
    provider_key_rotation_service,
)


async def key_pool_snapshot(db: AsyncSession, config: ModelProviderConfig) -> dict[str, Any]:
    extra = deepcopy(config.extra_config or {})
    rows = await provider_key_rotation_service.list_keys(db, config.id)
    if rows:
        extra["api_keys"] = [
            {**provider_key_rotation_service.to_public_dict(row), "api_key": row.api_key_encrypted}
            for row in rows
        ]
    return extra


async def sync_imported_keys(db: AsyncSession, config: ModelProviderConfig) -> None:
    """Persist imported credentials without replacing runtime usage for unchanged keys."""
    extra = deepcopy(config.extra_config or {})
    keys = extra.get("api_keys", [])
    if not keys and config.api_key_encrypted:
        keys = [{"id": f"primary_{config.id}", "name": "Khóa chính", "api_key": config.api_key_encrypted}]
    for item in keys:
        if not item.get("api_key"):
            continue
        item.setdefault("id", f"key_{uuid4().hex}")
        result = await db.execute(
            select(ProviderApiKey).where(ProviderApiKey.id == item["id"], ProviderApiKey.provider_id == config.id).with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ProviderApiKey(id=item["id"], provider_id=config.id, usage_tokens=0, status="active", consecutive_failures=0)
            db.add(row)
        elif decrypt_secret(row.api_key_encrypted) != decrypt_secret(item["api_key"]):
            row.status = "active"
            row.usage_tokens = 0
            row.cooldown_until = None
            row.last_error_code = None
            row.last_error_at = None
            row.consecutive_failures = 0
            row.lease_token = None
            row.lease_until = None
        row.api_key_encrypted = item["api_key"]
        row.api_key_masked = item.get("api_key_masked") or "••••••••"
        row.name = item.get("name") or "Khóa API"
        row.account_id = item.get("account_id") or extra.get("account_id")
        row.priority = item.get("priority", 1)
        row.is_active = item.get("is_active", True)
        row.quota_limit = item.get("quota_limit")
    extra["api_keys"] = keys
    config.extra_config = extra
