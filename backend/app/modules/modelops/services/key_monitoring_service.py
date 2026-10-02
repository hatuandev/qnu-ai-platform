"""Read-only provider key monitoring and deterministic failover previews."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig, ProviderKeyEvent
from app.modules.modelops.services.key_status import normalize_provider_key_status
from app.modules.modelops.services.provider_key_rotation_service import (
    provider_key_rotation_service,
)


class KeyMonitoringService:
    async def history(self, db: AsyncSession, provider_id: str, limit: int) -> list[dict[str, Any]]:
        provider = await db.get(ModelProviderConfig, provider_id)
        if provider is None:
            raise AppException(
                "Provider không tồn tại.", code="PROVIDER_NOT_FOUND", status_code=404
            )
        result = await db.execute(
            select(ProviderKeyEvent)
            .where(ProviderKeyEvent.provider_id == provider_id)
            .order_by(ProviderKeyEvent.created_at.desc(), ProviderKeyEvent.id.desc())
            .limit(limit)
        )
        return [
            {
                "id": event.id,
                "key_id": event.key_id,
                "event_type": event.event_type,
                "reason": event.reason,
                "tokens": event.tokens,
                "created_at": event.created_at.isoformat(),
            }
            for event in result.scalars().all()
        ]

    @staticmethod
    def preview(keys: list[dict[str, Any]]) -> dict[str, Any]:
        now = datetime.now(UTC)
        available = []
        for key in keys:
            status = normalize_provider_key_status(key.get("status"))
            cooldown = key.get("cooldown_until")
            if status == "rate_limited" and cooldown:
                until = datetime.fromisoformat(cooldown)
                if until.tzinfo is None:
                    until = until.replace(tzinfo=UTC)
                if until <= now:
                    status = "active"
            quota = key.get("quota_limit")
            busy = key.get("is_leased", False)
            if (
                key.get("is_active", True)
                and status == "active"
                and not busy
                and (quota is None or int(key.get("usage_tokens", 0)) < quota)
            ):
                available.append(key)
        available.sort(
            key=lambda key: (
                key.get("priority", 1),
                key.get("usage_tokens", 0),
                key.get("last_used_at") or "",
                key["id"],
            )
        )
        return {
            "dry_run": True,
            "rotated": len(available) >= 2,
            "key_order": [{"id": key["id"], "name": key["name"]} for key in available],
            "message": (
                "Mô phỏng 429: sẽ chuyển sang khóa tiếp theo; quota và trạng thái không thay đổi."
                if len(available) >= 2
                else "Cần ít nhất hai khóa khả dụng để chuyển khóa khi gặp 429."
            ),
        }

    async def failover_preview(self, db: AsyncSession, provider_id: str) -> dict[str, Any]:
        if await db.get(ModelProviderConfig, provider_id) is None:
            raise AppException(
                "Provider không tồn tại.", code="PROVIDER_NOT_FOUND", status_code=404
            )
        keys = await provider_key_rotation_service.list_keys(db, provider_id)
        return self.preview([provider_key_rotation_service.to_public_dict(key) for key in keys])


key_monitoring_service = KeyMonitoringService()
