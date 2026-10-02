"""Transactional provider credential leasing shared by every model runtime."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret
from app.modules.modelops.models import ProviderApiKey, ProviderKeyEvent
from app.modules.modelops.services.key_rotation import KeyFailure, classify_key_failure
from app.modules.modelops.services.key_status import normalize_provider_key_status


@dataclass(frozen=True, slots=True)
class LeasedProviderKey:
    """Decrypted credential temporarily reserved for one outbound request."""

    id: str
    provider_id: str
    name: str
    api_key: str
    account_id: str | None
    lease_token: str


@dataclass(frozen=True, slots=True)
class KeyAcquireResult:
    """Distinguish a legacy provider from a managed pool with no free key."""

    managed: bool
    lease: LeasedProviderKey | None


class ProviderKeyRotationService:
    """Select and update keys atomically across all API workers."""

    async def acquire(
        self,
        db: AsyncSession,
        provider_id: str,
        *,
        estimated_tokens: int = 0,
        excluded_key_ids: set[str] | None = None,
        lease_seconds: int = 120,
    ) -> KeyAcquireResult:
        now = datetime.now(UTC)
        excluded = excluded_key_ids or set()

        total_result = await db.execute(
            select(func.count(ProviderApiKey.id)).where(ProviderApiKey.provider_id == provider_id)
        )
        if total_result.scalar_one() <= 0:
            return KeyAcquireResult(managed=False, lease=None)

        await db.execute(
            update(ProviderApiKey)
            .where(
                ProviderApiKey.provider_id == provider_id,
                ProviderApiKey.status == "rate_limited",
                ProviderApiKey.cooldown_until.is_not(None),
                ProviderApiKey.cooldown_until <= now,
            )
            .values(status="active", cooldown_until=None, updated_at=now)
        )
        await db.execute(
            update(ProviderApiKey)
            .where(
                ProviderApiKey.provider_id == provider_id,
                ProviderApiKey.status == "active",
                ProviderApiKey.quota_limit.is_not(None),
                ProviderApiKey.usage_tokens >= ProviderApiKey.quota_limit,
            )
            .values(status="exhausted", cooldown_until=None, updated_at=now)
        )

        while True:
            conditions = [
                ProviderApiKey.provider_id == provider_id,
                ProviderApiKey.is_active.is_(True),
                ProviderApiKey.status == "active",
                or_(
                    ProviderApiKey.quota_limit.is_(None),
                    (ProviderApiKey.usage_tokens < ProviderApiKey.quota_limit)
                    & (ProviderApiKey.usage_tokens + max(0, estimated_tokens) <= ProviderApiKey.quota_limit),
                ),
                or_(
                    ProviderApiKey.lease_until.is_(None),
                    ProviderApiKey.lease_until <= now,
                ),
            ]
            if excluded:
                conditions.append(ProviderApiKey.id.not_in(excluded))
            result = await db.execute(
                select(ProviderApiKey)
                .where(*conditions)
                .order_by(
                    ProviderApiKey.priority.asc(),
                    ProviderApiKey.usage_tokens.asc(),
                    ProviderApiKey.last_used_at.asc().nullsfirst(),
                    ProviderApiKey.id.asc(),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            key = result.scalar_one_or_none()
            if key is None:
                await db.commit()
                return KeyAcquireResult(managed=True, lease=None)

            plain_key = decrypt_secret(key.api_key_encrypted)
            if not plain_key:
                key.status = "invalid"
                key.last_error_code = "provider_key_decryption_failed"
                key.last_error_at = now
                key.lease_token = None
                key.lease_until = None
                key.version = (key.version or 0) + 1
                db.add(ProviderKeyEvent(
                    provider_id=provider_id,
                    key_id=key.id,
                    event_type="invalid",
                    reason="provider_key_decryption_failed",
                ))
                await db.commit()
                excluded.add(key.id)
                continue

            token = str(uuid.uuid4())
            key.lease_token = token
            key.lease_until = now + timedelta(seconds=max(15, lease_seconds))
            key.last_used_at = now
            key.version = (key.version or 0) + 1
            db.add(
                ProviderKeyEvent(
                    provider_id=provider_id,
                    key_id=key.id,
                    event_type="rotated" if excluded else "selected",
                    reason="previous_key_failed" if excluded else None,
                )
            )
            await db.commit()
            return KeyAcquireResult(
                managed=True,
                lease=LeasedProviderKey(
                    id=key.id,
                    provider_id=key.provider_id,
                    name=key.name,
                    api_key=plain_key,
                    account_id=key.account_id,
                    lease_token=token,
                ),
            )

    async def complete_success(
        self,
        db: AsyncSession,
        lease: LeasedProviderKey,
        *,
        total_tokens: int = 0,
    ) -> bool:
        key = await self._lock_lease(db, lease)
        if key is None:
            await db.rollback()
            return False
        now = datetime.now(UTC)
        key.usage_tokens = max(0, key.usage_tokens or 0) + max(0, total_tokens)
        key.status = (
            "exhausted"
            if key.quota_limit is not None and key.usage_tokens >= key.quota_limit
            else "active"
        )
        key.cooldown_until = None
        key.last_used_at = now
        key.last_error_code = None
        key.consecutive_failures = 0
        key.lease_token = None
        key.lease_until = None
        key.version = (key.version or 0) + 1
        db.add(
            ProviderKeyEvent(
                provider_id=lease.provider_id,
                key_id=lease.id,
                event_type="success",
                tokens=max(0, total_tokens),
            )
        )
        await db.commit()
        return True

    async def complete_failure(
        self,
        db: AsyncSession,
        lease: LeasedProviderKey,
        exc: Exception,
    ) -> KeyFailure:
        failure = classify_key_failure(exc)
        key = await self._lock_lease(db, lease)
        if key is None:
            await db.rollback()
            return failure
        now = datetime.now(UTC)
        if failure.state is not None:
            key.status = failure.state
        if failure.state == "rate_limited":
            key.cooldown_until = now + timedelta(seconds=failure.retry_after_seconds or 60)
        elif failure.state in {"exhausted", "invalid"}:
            key.cooldown_until = None
        key.last_error_at = now
        key.last_error_code = failure.reason
        key.consecutive_failures = (key.consecutive_failures or 0) + 1
        key.lease_token = None
        key.lease_until = None
        key.version = (key.version or 0) + 1
        db.add(
            ProviderKeyEvent(
                provider_id=lease.provider_id,
                key_id=lease.id,
                event_type=failure.state or "failed",
                reason=failure.reason,
            )
        )
        await db.commit()
        return failure

    async def release(self, db: AsyncSession, lease: LeasedProviderKey) -> bool:
        key = await self._lock_lease(db, lease)
        if key is None:
            await db.rollback()
            return False
        key.lease_token = None
        key.lease_until = None
        key.version = (key.version or 0) + 1
        await db.commit()
        return True

    async def renew(self, db: AsyncSession, lease: LeasedProviderKey, lease_seconds: int) -> bool:
        """Extend ownership during long streams without changing the routing order."""
        result = await db.execute(
            update(ProviderApiKey)
            .where(ProviderApiKey.id == lease.id, ProviderApiKey.provider_id == lease.provider_id,
                   ProviderApiKey.lease_token == lease.lease_token)
            .values(lease_until=datetime.now(UTC) + timedelta(seconds=max(15, lease_seconds)))
        )
        await db.commit()
        return result.rowcount == 1

    async def list_keys(self, db: AsyncSession, provider_id: str) -> list[ProviderApiKey]:
        result = await db.execute(
            select(ProviderApiKey)
            .where(ProviderApiKey.provider_id == provider_id)
            .order_by(ProviderApiKey.priority, ProviderApiKey.created_at, ProviderApiKey.id)
        )
        return list(result.scalars().all())

    @staticmethod
    def to_public_dict(key: ProviderApiKey) -> dict[str, Any]:
        return {
            "id": key.id,
            "name": key.name,
            "api_key_masked": key.api_key_masked,
            "account_id": key.account_id,
            "priority": key.priority,
            "is_active": key.is_active,
            "status": normalize_provider_key_status(key.status),
            "quota_limit": key.quota_limit,
            "usage_tokens": key.usage_tokens,
            "cooldown_until": key.cooldown_until.isoformat() if key.cooldown_until else None,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "last_error_at": key.last_error_at.isoformat() if key.last_error_at else None,
            "last_error_code": key.last_error_code,
            "consecutive_failures": key.consecutive_failures,
            "is_leased": bool(key.lease_until and key.lease_until > datetime.now(UTC)),
            "lease_until": key.lease_until.isoformat() if key.lease_until else None,
            "created_at": key.created_at.isoformat() if key.created_at else None,
        }

    @staticmethod
    async def _lock_lease(db: AsyncSession, lease: LeasedProviderKey) -> ProviderApiKey | None:
        result = await db.execute(
            select(ProviderApiKey)
            .where(
                ProviderApiKey.id == lease.id,
                ProviderApiKey.provider_id == lease.provider_id,
                ProviderApiKey.lease_token == lease.lease_token,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()


provider_key_rotation_service = ProviderKeyRotationService()
