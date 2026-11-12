"""Admin-only diagnostics, stored separately from declared capacity and runtime usage.

Only generated samples leave QNU. No raw content/credentials enter the safe history.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.capacity.automatic import capacity_identity, operational_budget
from qnu.domains.modelops.capacity.service import read_capacity
from qnu.domains.modelops.diagnostics.observations import MAX_OBSERVATIONS, stored_observations
from qnu.domains.modelops.diagnostics.schemas import (
    DiagnosticCheck,
    ObservedOutputLimit,
    ProviderDiagnostics,
)
from qnu.domains.modelops.embedding.configuration import read_dimension
from qnu.domains.modelops.keys.scope import key_scope
from qnu.domains.modelops.models import Provider, ProviderKey
from qnu.domains.modelops.providers.service import provider_service
from qnu.platform.crypto import decrypt
from qnu.platform.errors import AppException, Conflict
from qnu.ports.provider_diagnostics import (
    DiagnosticKind,
    DiagnosticResult,
    DiagnosticTarget,
    ProviderDiagnosticClient,
)

HISTORY_KEY = "diagnostic_checks_v1"


def _observed_limits(provider: Provider) -> list[ObservedOutputLimit]:
    rows = stored_observations(provider)
    if not rows:
        return []
    effective = operational_budget(read_capacity(provider), "chat")
    current = capacity_identity(
        provider.id,
        provider.base_url,
        provider.model_name,
        effective.token_limits,
        effective,
    )
    now = datetime.now(UTC)
    limits = []
    for row in rows[:MAX_OBSERVATIONS]:
        try:
            limit = ObservedOutputLimit.model_validate(
                {
                    field: row.get(field)
                    for field in (
                        "endpoint",
                        "model_name",
                        "max_output_tokens",
                        "observed_at",
                        "expires_at",
                    )
                }
            )
        except (ValueError, TypeError):
            continue
        if row.get("budget_identity") != current or limit.expires_at <= now:
            limit.configuration_status = "stale"
        limits.append(limit)
    return limits


async def identity(db: AsyncSession, provider: Provider) -> str:
    key = (
        await db.scalars(
            select(ProviderKey)
            .where(key_scope(provider), ProviderKey.status == "active")
            .order_by(ProviderKey.priority, ProviderKey.created_at)
            .limit(1)
        )
    ).first()
    return configuration_identity(provider, key)


def configuration_identity(provider: Provider, key: ProviderKey | None) -> str:
    """Shared fingerprint for batched summaries and detailed diagnostics."""
    capacity = read_capacity(provider)
    dimension, dimension_status = read_dimension(provider)
    material = [
        "qnu-provider-diagnostics/v1",
        provider.base_url.rstrip("/"),
        provider.model_name,
        provider.provider_type,
        provider.capabilities,
        provider.is_active,
        provider.timeout_seconds,
        (provider.extra_config or {}).get("api_type"),
        (provider.extra_config or {}).get("connection_family"),
        bool((provider.extra_config or {}).get("ocr_auth_optional", False)),
        capacity.token_limits.model_dump() if capacity.token_limits else None,
        dimension,
        dimension_status,
        [key.id, hashlib.sha256(key.secret_encrypted.encode()).hexdigest()] if key else None,
    ]
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def history_current(provider: Provider, row: dict, active_keys: list[ProviderKey]) -> bool:
    """A result for the second key must not be compared to the first key."""
    key_id = row.get("key_id")
    key = (
        next((item for item in active_keys if item.id == key_id), None)
        if key_id
        else next(iter(active_keys), None)
    )
    if key_id and key is None:
        return False
    return row.get("identity") == configuration_identity(provider, key)


async def read_diagnostics(
    db: AsyncSession, provider_id: str, actor: AuthActor
) -> ProviderDiagnostics:
    require_model_admin(actor)
    provider = await provider_service.get(db, provider_id)
    keys = list(
        (
            await db.scalars(
                select(ProviderKey)
                .where(key_scope(provider), ProviderKey.status == "active")
                .order_by(ProviderKey.priority, ProviderKey.created_at, ProviderKey.id)
            )
        ).all()
    )
    checks = []
    for row in (provider.extra_config or {}).get(HISTORY_KEY, [])[:20]:
        check = DiagnosticCheck.model_validate(row)
        check.configuration_status = "current" if history_current(provider, row, keys) else "stale"
        checks.append(check)
    return ProviderDiagnostics(
        provider_id=provider.id,
        configured_active=provider.is_active,
        checks=checks,
        observed_output_limits=_observed_limits(provider),
    )


async def run_diagnostic(
    db: AsyncSession,
    provider_id: str,
    kind: DiagnosticKind,
    actor: AuthActor,
    client: ProviderDiagnosticClient,
) -> DiagnosticCheck:
    require_model_admin(actor)
    provider = await provider_service.get(db, provider_id)
    if provider.parent_id:
        parent = await provider_service.get(db, provider.parent_id)
        if not parent.is_connection or not parent.is_active:
            raise Conflict(
                "Nhà cung cấp đang tắt; bật lại trước khi kiểm tra.", code="provider_inactive"
            )
    if not provider.is_active:
        raise Conflict("Provider đang tắt; bật lại trước khi kiểm tra.", code="provider_inactive")
    if kind != "discovery" and kind not in provider.capabilities:
        raise Conflict(
            "Chức năng chưa được khai báo cho provider.", code="provider_capability_mismatch"
        )
    fingerprint = await identity(db, provider)
    key = (
        await db.scalars(
            select(ProviderKey)
            .where(key_scope(provider), ProviderKey.status == "active")
            .order_by(ProviderKey.priority, ProviderKey.created_at)
            .limit(1)
        )
    ).first()
    capacity = read_capacity(provider)
    maximum = capacity.token_limits.max_output_tokens if capacity.token_limits else None
    dimension, _ = read_dimension(provider)
    target = DiagnosticTarget(
        endpoint=provider.base_url,
        model=provider.model_name,
        provider_type=provider.provider_type,
        timeout_seconds=min(provider.timeout_seconds, 60),
        expected_dimension=dimension,
        max_output_tokens=min(maximum or 1024, 1024),
        auth_optional=kind == "ocr"
        and bool((provider.extra_config or {}).get("ocr_auth_optional", False)),
    )
    credential_error = False
    if key:
        try:
            target = replace(target, api_key=decrypt(key.secret_encrypted))
        except AppException:
            # Never attach cryptography/provider error strings to the public diagnostic.
            credential_error = True
    # No row locks/DB transaction held while waiting on upstream.
    await db.commit()
    result = (
        DiagnosticResult("failed", "credentials_unreadable", "Không đọc được khóa đã lưu.")
        if credential_error
        else await client.check(kind, target)
    )
    current = (
        await db.execute(
            select(Provider)
            .where(Provider.id == provider_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    if await identity(db, current) != fingerprint:
        await db.rollback()
        raise Conflict(
            "Cấu hình đã đổi trong lúc thử; hãy chạy lại.", code="diagnostic_configuration_changed"
        )
    check = DiagnosticCheck(
        id="diag_" + uuid.uuid4().hex[:16],
        kind=kind,
        outcome=result.outcome,
        tested_at=datetime.now(UTC),
        latency_ms=result.latency_ms,
        code=result.code,
        detail=result.detail,
        http_status=result.http_status,
        retry_after=result.retry_after,
        requested_model=target.model,
        observed_model=result.observed_model,
        observed_dimension=result.observed_dimension,
        total_tokens=result.total_tokens,
        models=result.models,
        model_metadata=result.model_metadata,
    )
    config = dict(current.extra_config or {})
    config[HISTORY_KEY] = [
        {**check.model_dump(mode="json"), "identity": fingerprint},
        *config.get(HISTORY_KEY, []),
    ][:20]
    current.extra_config = config
    record_event(db, actor, "provider.diagnostic." + kind, provider_id, [check.code])
    await db.commit()
    return check
