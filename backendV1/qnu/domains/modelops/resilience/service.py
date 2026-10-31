"""Server-managed policy, validated against supported adapters and model identity."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.models import ModelOpsEvent, Provider
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.registry import transport_for
from qnu.domains.modelops.resilience.schemas import (
    TASK_CAPABILITIES,
    ExecutionObservation,
    PolicyResponse,
    ResiliencePolicy,
)
from qnu.platform.errors import Conflict

POLICY_KEY = "resilience_v1"
LEASES_KEY = "key_leases_v1"


async def execution_history(
    db: AsyncSession, actor: AuthActor, provider_id: str
) -> list[ExecutionObservation]:
    require_model_admin(actor)
    await provider_service.get(db, provider_id)
    rows = (
        await db.scalars(
            select(ModelOpsEvent)
            .where(
                ModelOpsEvent.provider_id == provider_id,
                ModelOpsEvent.action == "provider.execution",
            )
            .order_by(ModelOpsEvent.created_at.desc())
            .limit(50)
        )
    ).all()
    return [
        ExecutionObservation(id=row.id, created_at=row.created_at, **row.detail) for row in rows
    ]


def identity(provider: Provider) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                provider.base_url.rstrip("/"),
                provider.model_name,
                provider.provider_type,
            ]
        ).encode()
    ).hexdigest()


def read_policy(provider: Provider) -> PolicyResponse:
    saved = (provider.extra_config or {}).get(POLICY_KEY)
    if not saved:
        return PolicyResponse(provider_id=provider.id, status="default", policy=ResiliencePolicy())
    return PolicyResponse(
        provider_id=provider.id,
        status="configured" if saved["identity"] == identity(provider) else "stale",
        policy=ResiliencePolicy.model_validate(saved["policy"]),
    )


def effective_policy(provider: Provider) -> ResiliencePolicy:
    current = read_policy(provider)
    return current.policy if current.status != "stale" else ResiliencePolicy()


async def save_policy(
    db: AsyncSession, actor: AuthActor, provider_id: str, policy: ResiliencePolicy
) -> PolicyResponse:
    require_model_admin(actor)
    provider = (
        await db.scalars(
            select(Provider)
            .where(Provider.id == provider_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).one_or_none()
    if provider is None:
        await provider_service.get(db, provider_id)
    own_transport = transport_for(provider.provider_type)
    if policy.wait_for_completion and "chat" not in provider.capabilities:
        raise Conflict("Chỉ model chat được chờ hoàn tất.", code="chat_policy_capability_mismatch")
    if policy.key_pool_enabled and not own_transport.protocols:
        raise Conflict(
            "Loại provider chưa có adapter runtime.", code="provider_transport_unsupported"
        )
    for task, ids in policy.fallbacks.items():
        cap = TASK_CAPABILITIES[task]
        if cap not in provider.capabilities or cap not in own_transport.protocols:
            raise Conflict(
                "Tác vụ không phù hợp provider gốc.", code="fallback_capability_mismatch"
            )
        for pid in ids:
            if pid == provider_id:
                raise Conflict("Không dùng chính model gốc làm dự phòng.", code="fallback_cycle")
            candidate = await provider_service.require_capability(db, pid, cap)
            if cap not in transport_for(candidate.provider_type).protocols:
                raise Conflict(
                    "Model dự phòng chưa có adapter.", code="fallback_transport_unsupported"
                )
    provider.extra_config = {
        **(provider.extra_config or {}),
        POLICY_KEY: {
            "identity": identity(provider),
            "policy": policy.model_dump(mode="json"),
        },
    }
    record_event(
        db, actor, "provider.resilience_updated", provider.id, list(policy.model_fields_set)
    )
    await db.commit()
    return read_policy(provider)
