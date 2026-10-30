"""Model-specific declarations stored in existing provider JSONB, without new DDL."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
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

CAPACITY_KEY = "model_token_capacity_v1"


def set_capacity(
    provider: Provider,
    limits: ModelTokenLimits | None,
    *,
    basis: CapacityBasis = "operator_configured",
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
    except (ValidationError, KeyError, ValueError) as exc:
        raise AppException(
            "Capacity đã lưu không hợp lệ.", code="model_token_limits_invalid", status_code=422
        ) from exc
    return ModelCapacity(status="configured", token_limits=limits, basis=raw["basis"])


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
    if state.status != "configured":
        raise AppException(
            "Cần cấu hình lại capacity." if state.status == "stale" else "Chưa cấu hình capacity.",
            code="model_token_limits_stale"
            if state.status == "stale"
            else "model_capacity_required",
            status_code=409 if state.status == "stale" else 422,
        )
    material = {
        "provider_id": provider.id,
        "endpoint": provider.base_url.rstrip("/"),
        "model_name": provider.model_name,
        "limits": state.token_limits.model_dump(),
    }
    return CapacitySnapshot(
        provider_id=provider.id,
        model_name=provider.model_name,
        token_limits=state.token_limits,
        basis=state.basis,
        configuration_hash=hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
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
    budget = plan_token_budget(
        snapshot.token_limits,
        input_tokens=input_tokens,
        requested_output_tokens=requested_output_tokens,
        reserve_tokens=reserve_tokens,
        minimum_output_tokens=minimum_output_tokens,
    )
    return snapshot, budget
