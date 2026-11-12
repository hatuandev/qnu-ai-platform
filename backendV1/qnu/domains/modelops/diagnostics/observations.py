"""Observed output ceilings are diagnostics evidence, never published capacity.

A definite pre-generation rejection reveals the provider's real output ceiling.
The runtime keeps that value in RAM for a few minutes; this durable copy lets a
restarted process start from the observation instead of repeating the rejected
request. Declared capacity and its basis are never rewritten here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qnu.domains.modelops.models import Provider
from qnu.platform.logging import get_logger

logger = get_logger(__name__)

OBSERVATIONS_KEY = "observed_output_limits_v1"
OBSERVATION_TTL_SECONDS = 24 * 60 * 60
MAX_OBSERVATIONS = 8
NEGATIVE_CACHE_SECONDS = 60


def _scope(endpoint: str, model_name: str, budget_identity: str | None) -> tuple:
    return endpoint.rstrip("/"), model_name, budget_identity


def _rows(provider: Provider) -> list[dict]:
    rows = (provider.extra_config or {}).get(OBSERVATIONS_KEY)
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def stored_observations(provider: Provider) -> list[dict]:
    return _rows(provider)


def _parse(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def matching_observation(
    provider: Provider,
    *,
    endpoint: str,
    model_name: str,
    budget_identity: str | None,
    now: datetime,
) -> tuple[int, datetime] | None:
    scope = _scope(endpoint, model_name, budget_identity)
    for row in _rows(provider):
        limit = row.get("max_output_tokens")
        expires_at = _parse(row.get("expires_at"))
        if (
            (row.get("endpoint"), row.get("model_name"), row.get("budget_identity")) != scope
            or type(limit) is not int
            or limit <= 0
            or expires_at is None
        ):
            continue
        if expires_at > now:
            return limit, expires_at
    return None


def record_observation(
    provider: Provider,
    *,
    endpoint: str,
    model_name: str,
    budget_identity: str,
    limit: int,
    now: datetime,
) -> None:
    scope = _scope(endpoint, model_name, budget_identity)
    rows = [
        row
        for row in _rows(provider)
        if (row.get("endpoint"), row.get("model_name"), row.get("budget_identity")) != scope
    ]
    rows.insert(
        0,
        {
            "endpoint": scope[0],
            "model_name": scope[1],
            "budget_identity": scope[2],
            "max_output_tokens": limit,
            "observed_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=OBSERVATION_TTL_SECONDS)).isoformat(),
        },
    )
    provider.extra_config = {
        **(provider.extra_config or {}),
        OBSERVATIONS_KEY: rows[:MAX_OBSERVATIONS],
    }


async def remember_limit(
    sessions,
    *,
    provider_id: str,
    endpoint: str,
    model_name: str,
    budget_identity: str | None,
    limit: int,
) -> None:
    """Best-effort durable copy; a chat call never fails because storage did."""
    if sessions is None or budget_identity is None:
        return
    try:
        async with sessions() as db:
            provider = await db.get(Provider, provider_id, with_for_update=True)
            if provider is None:
                return
            record_observation(
                provider,
                endpoint=endpoint,
                model_name=model_name,
                budget_identity=budget_identity,
                limit=limit,
                now=datetime.now(UTC),
            )
            await db.commit()
    except Exception:
        logger.warning("chat_output_limit_not_persisted", provider_id=provider_id)


async def load_limit(
    sessions,
    *,
    provider_id: str,
    endpoint: str,
    model_name: str,
    budget_identity: str | None,
) -> tuple[int, float] | None:
    """Return the newest unexpired observed limit and its remaining lifetime."""
    if sessions is None or budget_identity is None:
        return None
    try:
        async with sessions() as db:
            provider = await db.get(Provider, provider_id)
            found = (
                matching_observation(
                    provider,
                    endpoint=endpoint,
                    model_name=model_name,
                    budget_identity=budget_identity,
                    now=datetime.now(UTC),
                )
                if provider is not None
                else None
            )
    except Exception:
        logger.warning("chat_output_limit_not_loaded", provider_id=provider_id)
        return None
    if found is None:
        return None
    remaining = (found[1] - datetime.now(UTC)).total_seconds()
    return (found[0], remaining) if remaining > 0 else None
