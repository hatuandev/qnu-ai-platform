"""Versioned operational defaults, independent of actual model capacity.

Defaults let an unlisted text model start with bounded requests. They are not
certified safe limits: an upstream may reject them. No probe, database write,
provider fallback or retry is performed here; stale declarations fail closed.
"""

import hashlib
import json

from qnu.domains.modelops.capacity.schemas import (
    ModelCapacity,
    ModelTokenLimits,
    OperationalBudget,
)

CHAT_CONTEXT = 131072
CHAT_OUTPUT = 4096
TEXT_INPUT = 2048


def operational_budget(state: ModelCapacity, capability: str) -> OperationalBudget:
    if state.status == "stale":
        return OperationalBudget(status="blocked", reason_code="model_token_limits_stale")
    limits = state.token_limits
    if capability == "ocr" and (limits is None or limits.ocr_page_input is None):
        return OperationalBudget(status="blocked", reason_code="model_input_budget_unknown")
    values = limits.model_dump(exclude_none=True) if limits else {}
    sources = {field: state.field_sources.get(field, state.basis) for field in values}
    defaults = _defaults(values, capability)
    for field, value in defaults.items():
        values[field] = value
        sources[field] = "application_default"
    return OperationalBudget(
        status="provisional" if defaults else "declared",
        token_limits=ModelTokenLimits.model_validate(values),
        sources=sources,
    )


def _defaults(values: dict, capability: str) -> dict[str, int]:
    defaults = {}
    context = values.get("context_window_tokens")
    if context is None and values.get("max_input_tokens") is None:
        if capability == "chat" and not values:
            defaults["context_window_tokens"] = CHAT_CONTEXT
        else:
            defaults["max_input_tokens"] = (
                CHAT_CONTEXT - CHAT_OUTPUT if capability in ("chat", "ocr") else TEXT_INPUT
            )
    if capability in ("chat", "ocr") and values.get("max_output_tokens") is None:
        # Leave input headroom even for small declared shared contexts.
        defaults["max_output_tokens"] = (
            min(CHAT_OUTPUT, max(1, context // 4)) if context else CHAT_OUTPUT
        )
    return defaults


def capacity_identity(
    provider_id: str,
    endpoint: str,
    model_name: str,
    limits: ModelTokenLimits | None,
    operational: OperationalBudget | None = None,
) -> str:
    material = {
        "provider_id": provider_id,
        "endpoint": endpoint.rstrip("/"),
        "model_name": model_name,
        "limits": limits.model_dump() if limits else None,
    }
    if operational and operational.status == "provisional":
        material["operational_budget"] = operational.model_dump()
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
