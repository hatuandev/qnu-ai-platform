"""Batch summary using the same history contract/fingerprint as detailed diagnostics."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.modelops.diagnostics.schemas import DiagnosticCheck
from qnu.domains.modelops.diagnostics.service import HISTORY_KEY, history_current
from qnu.domains.modelops.models import ProviderKey
from qnu.domains.modelops.providers.service import provider_payload, provider_service
from qnu.domains.modelops.schemas import ProviderSummaryItem


async def provider_summaries(db: AsyncSession) -> list[ProviderSummaryItem]:
    providers = await provider_service.list(db)
    keys = (
        await db.scalars(select(ProviderKey).order_by(ProviderKey.priority, ProviderKey.created_at))
    ).all()
    grouped: dict[str, list[ProviderKey]] = {}
    for key in keys:
        grouped.setdefault(key.provider_id, []).append(key)
    items = []
    for provider in providers:
        provider_keys = [
            key
            for key in grouped.get(provider.parent_id or provider.id, [])
            if key.model_ids is None or provider.id in key.model_ids
        ]
        active = [key for key in provider_keys if key.status == "active"]
        history = (provider.extra_config or {}).get(HISTORY_KEY, [])
        status, tested_at, latency = "untested", None, None
        if history:
            last = history[0]
            check = DiagnosticCheck.model_validate(last)
            current = history_current(provider, last, active)
            status = (
                "stale" if not current else ("success" if check.outcome == "ok" else check.outcome)
            )
            tested_at, latency = check.tested_at, check.latency_ms
        items.append(
            ProviderSummaryItem(
                **provider_payload(provider),
                active_keys_count=len(active),
                total_keys_count=len(provider_keys),
                last_probe_status=status,
                last_probe_at=tested_at,
                last_probe_latency_ms=latency,
            )
        )
    return items
