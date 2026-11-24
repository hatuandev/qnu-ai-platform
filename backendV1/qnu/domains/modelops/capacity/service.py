"""Model-specific declarations stored in existing provider JSONB, without new DDL."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.capacity.automatic import capacity_identity, operational_budget
from qnu.domains.modelops.capacity.policy import plan_token_budget
from qnu.domains.modelops.capacity.schemas import (
    CapacityBasis,
    CapacitySnapshot,
    ModelCapacity,
    ModelTokenLimits,
    RequestTokenBudget,
)
from qnu.domains.modelops.models import Provider
from qnu.platform.errors import AppException
from qnu.platform.logging import get_logger

logger = get_logger(__name__)
CAPACITY_KEY = "model_token_capacity_v1"


def set_capacity(
    provider: Provider,
    limits: ModelTokenLimits | None,
    *,
    basis: CapacityBasis = "operator_configured",
    field_sources: dict[str, CapacityBasis] | None = None,
) -> None:
    config = dict(provider.extra_config or {})
    if limits is None:
        config.pop(CAPACITY_KEY, None)
    else:
        config[CAPACITY_KEY] = {
            "endpoint": provider.base_url.rstrip("/"),
            "model_name": provider.model_name,
            "token_limits": limits.model_dump(),
            "basis": basis,
            "field_sources": {
                field: (field_sources or {}).get(field, basis)
                for field in limits.model_dump(exclude_none=True)
            },
            "recorded_at": datetime.now(UTC).isoformat(),
        }
    provider.extra_config = config


def invalidate_capacity(provider: Provider) -> None:
    config = dict(provider.extra_config or {})
    if CAPACITY_KEY in config:
        config[CAPACITY_KEY] = {**config[CAPACITY_KEY], "invalidated": True}
        provider.extra_config = config


def read_capacity(provider: Provider) -> ModelCapacity:
    raw = (provider.extra_config or {}).get(CAPACITY_KEY)
    if raw is None:
        return ModelCapacity(status="unknown")
    if not isinstance(raw, dict):
        raise AppException(
            "Capacity đã lưu không hợp lệ.", code="model_token_limits_invalid", status_code=422
        )
    if (
        raw.get("invalidated")
        or raw.get("endpoint") != provider.base_url.rstrip("/")
        or raw.get("model_name") != provider.model_name
    ):
        return ModelCapacity(status="stale")
    try:
        limits = ModelTokenLimits.model_validate(raw["token_limits"])
        if raw.get("basis") not in ("operator_configured", "server_reported"):
            raise ValueError("Invalid capacity basis")
        sources = raw.get("field_sources", {})
        if not isinstance(sources, dict) or any(
            field not in limits.model_dump(exclude_none=True)
            or value not in ("operator_configured", "server_reported")
            for field, value in sources.items()
        ):
            raise ValueError("Invalid capacity sources")
    except (ValidationError, KeyError, ValueError) as exc:
        raise AppException(
            "Capacity đã lưu không hợp lệ.", code="model_token_limits_invalid", status_code=422
        ) from exc
    return ModelCapacity(
        status="configured", token_limits=limits, basis=raw["basis"], field_sources=sources
    )


async def resolve_model_capacity(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    capability: str,
    provider_id: str | None = None,
) -> CapacitySnapshot:
    # Provider CRUD imports the configuration helpers in this module.
    from qnu.domains.modelops.catalog.service import catalog_service

    provider = await catalog_service.resolve_provider(
        db, actor, workspace_id, capability, provider_id
    )
    state = read_capacity(provider)
    effective = operational_budget(state, capability)
    if effective.status == "blocked":
        raise AppException(
            "Cần cấu hình lại capacity."
            if state.status == "stale"
            else "Chưa có cách tính token ảnh.",
            code=effective.reason_code,
            status_code=409 if state.status == "stale" else 422,
        )
    return CapacitySnapshot(
        provider_id=provider.id,
        model_name=provider.model_name,
        token_limits=effective.token_limits,
        basis="application_default" if effective.status == "provisional" else state.basis,
        operational_budget=effective,
        configuration_hash=capacity_identity(
            provider.id, provider.base_url, provider.model_name, effective.token_limits, effective
        ),
    )


async def plan_model_request(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    capability: str,
    *,
    input_tokens: int | None,
    provider_id: str | None = None,
    requested_output_tokens: int | None = None,
    reserve_tokens: int = 0,
    minimum_output_tokens: int = 1,
) -> tuple[CapacitySnapshot, RequestTokenBudget]:
    snapshot = await resolve_model_capacity(db, actor, workspace_id, capability, provider_id)
    is_provisional_chat = (
        capability == "chat"
        and snapshot.operational_budget is not None
        and snapshot.operational_budget.status == "provisional"
    )
    if (
        is_provisional_chat
        and input_tokens is not None
        and snapshot.token_limits.context_window_tokens is not None
        and input_tokens + reserve_tokens >= snapshot.token_limits.context_window_tokens
    ):
        logger.warning(
            "model_provisional_budget_soft_pass",
            provider_id=snapshot.provider_id,
            model_name=snapshot.model_name,
            estimated_input_tokens=input_tokens + reserve_tokens,
            provisional_context_window=snapshot.token_limits.context_window_tokens,
        )
    budget = plan_token_budget(
        snapshot.token_limits,
        input_tokens=input_tokens,
        requested_output_tokens=requested_output_tokens,
        reserve_tokens=reserve_tokens,
        minimum_output_tokens=minimum_output_tokens,
        provisional=is_provisional_chat,
    )
    return snapshot, budget
