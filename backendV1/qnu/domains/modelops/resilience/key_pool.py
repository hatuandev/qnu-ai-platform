"""PostgreSQL-serialized leases, fenced by UUID; no locks held during inference.

Lease owners live in the provider's bounded server-managed JSON alongside the
existing key lease/cooldown columns. Every writer locks provider, then key. An
expired worker cannot release a replacement lease. No schema migration required.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.models import ModelOpsEvent, ModelUsageRecord, Provider, ProviderKey
from qnu.domains.modelops.resilience.schemas import ResiliencePolicy
from qnu.domains.modelops.resilience.service import LEASES_KEY, effective_policy
from qnu.platform.crypto import decrypt
from qnu.platform.errors import Conflict, DependencyUnavailable
from qnu.ports.provider_execution import ProviderExecution, ProviderFailure


def eligible(now: datetime):
    return (
        ProviderKey.status == "active",
        or_(ProviderKey.cooldown_until.is_(None), ProviderKey.cooldown_until <= now),
        or_(ProviderKey.lease_until.is_(None), ProviderKey.lease_until <= now),
    )


@dataclass(frozen=True)
class KeyLease:
    provider_id: str
    model_name: str
    key_id: str | None
    token: str | None = field(repr=False)
    secret: str | None = field(repr=False)
    policy: ResiliencePolicy


async def acquire(
    db: AsyncSession,
    scope: ProviderExecution,
    capability: str,
    endpoint: str,
    model: str,
    timeout: float,
    excluded: set[str],
) -> KeyLease:
    provider = (
        await db.scalars(
            select(Provider)
            .where(Provider.id == scope.provider_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).one_or_none()
    # Revalidate grants and current active/capability state immediately before dispatch.
    allowed = await catalog_service.resolve_workspace_provider(
        db,
        scope.workspace_id,
        capability,
        scope.provider_id,
    )
    if allowed is not provider or (provider.base_url.rstrip("/"), provider.model_name) != (
        endpoint.rstrip("/"),
        model,
    ):
        raise Conflict("Model đã đổi trước khi gọi.", code="provider_execution_changed")
    if scope.usage_id:
        usage = await db.get(ModelUsageRecord, scope.usage_id)
        if usage is None or (
            usage.workspace_id,
            usage.provider_id,
            usage.capability,
            usage.model_name,
            usage.status,
        ) != (
            scope.workspace_id,
            scope.provider_id,
            capability,
            model,
            "reserved",
        ):
            raise Conflict("Reservation không khớp lượt gọi.", code="provider_reservation_mismatch")
    policy, now = effective_policy(provider), datetime.now(UTC)
    stmt = select(ProviderKey).where(
        ProviderKey.provider_id == provider.id,
        ProviderKey.status == "active",
        ProviderKey.id.not_in(excluded),
    )
    if policy.key_pool_enabled:
        stmt = stmt.where(*eligible(now))
    key = (
        await db.scalars(
            stmt.order_by(
                ProviderKey.priority,
                ProviderKey.updated_at if policy.key_pool_enabled else ProviderKey.created_at,
                ProviderKey.id,
            )
            .limit(1)
            .with_for_update()
        )
    ).first()
    if key is None:
        if capability == "ocr" and (provider.extra_config or {}).get("ocr_auth_optional"):
            return KeyLease(provider.id, model, None, None, None, policy)
        raise DependencyUnavailable(
            "Không có khóa sẵn sàng; không gửi request.", code="provider_keys_unavailable"
        )
    secret = decrypt(key.secret_encrypted)
    token = None
    if policy.key_pool_enabled:
        token = uuid.uuid4().hex
        key.lease_until = now + timedelta(seconds=timeout + 10)
        leases = {
            kid: data
            for kid, data in (provider.extra_config or {}).get(LEASES_KEY, {}).items()
            if data["expires"] > now.isoformat()
        }
        leases[key.id] = {"token": token, "expires": key.lease_until.isoformat()}
        provider.extra_config = {**(provider.extra_config or {}), LEASES_KEY: leases}
    await db.commit()
    return KeyLease(provider.id, model, key.id, token, secret, policy)


async def finish(
    db: AsyncSession,
    lease: KeyLease,
    *,
    call_id: str,
    capability: str,
    code: str,
    failure: ProviderFailure | None = None,
    success: bool = False,
    latency_ms: int | None = None,
    attempt: int = 1,
    total_tokens: int | None = None,
    usage_id: str | None = None,
) -> None:
    provider = (
        await db.scalars(
            select(Provider)
            .where(Provider.id == lease.provider_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).one()
    if lease.token:
        leases = dict((provider.extra_config or {}).get(LEASES_KEY, {}))
        if leases.get(lease.key_id, {}).get("token") != lease.token:
            return  # A newer worker owns this key now.
        key = await db.get(ProviderKey, lease.key_id, with_for_update=True)
        del leases[lease.key_id]
        provider.extra_config = {**(provider.extra_config or {}), LEASES_KEY: leases}
        key.lease_until = None
        if key.status == "active":
            if success:
                key.consecutive_failures, key.cooldown_until = 0, None
            elif failure is not None and failure.retryable_key:
                key.consecutive_failures += 1
                seconds = (
                    lease.policy.auth_cooldown_seconds
                    if failure.upstream_status == 401
                    else lease.policy.rate_cooldown_seconds
                )
                seconds = max(seconds, min(failure.retry_after_seconds or 0, 86400))
                key.cooldown_until = datetime.now(UTC) + timedelta(seconds=seconds)
    db.add(
        ModelOpsEvent(
            id="moe_" + uuid.uuid4().hex[:16],
            actor_ref="modelops-runtime",
            action="provider.execution",
            provider_id=lease.provider_id,
            detail={
                "call_id": call_id,
                "usage_id": usage_id,
                "capability": capability,
                "model_name": lease.model_name,
                "attempt": attempt,
                "latency_ms": latency_ms,
                "total_tokens": total_tokens,
                "key_id": lease.key_id,
                "code": code,
                "upstream_status": failure.upstream_status if failure else None,
            },
        )
    )
    await db.commit()
