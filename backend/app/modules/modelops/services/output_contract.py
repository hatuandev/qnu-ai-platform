"""Backend-owned output schemas and explicit, endpoint-scoped capability policy."""
import json
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.exceptions import AppException

OutputMode = Literal["json_schema", "json_object", "prompt_only"]


class OutputContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: Literal["qnu_semantic_selector_v1", "qnu_semantic_selector_v2"] = "qnu_semantic_selector_v1"
    requested_mode: OutputMode = "json_schema"
    allowed_weaker_modes: tuple[OutputMode, ...] = ()


def schema_hash(schema: dict) -> str:
    return sha256(json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@lru_cache(maxsize=2)
def _schemas(name: str) -> tuple[dict, dict]:
    from app.modules.knowledge.services.semantic_binding import selector_type
    business = selector_type(name).model_json_schema()
    wire = deepcopy(business)

    def visit(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["required"] = list(node.get("properties", {}))
                node["additionalProperties"] = False
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(wire)
    if len(json.dumps(wire).encode()) > 32000:
        raise ValueError("OUTPUT_SCHEMA_TOO_LARGE")
    return business, wire


def contract_schemas(name: str = "qnu_semantic_selector_v1") -> tuple[dict, dict]:
    return deepcopy(_schemas(name))


def contract_version(name: str) -> int:
    # Validation is explicit; never infer a version from a model response shape.
    OutputContract(name=name)
    return 1 if name == "qnu_semantic_selector_v1" else 2


def resolve_contract(contract: OutputContract, capabilities: dict, *, supports_chat_schema: bool) -> dict:
    modes = ["json_schema", "json_object", "prompt_only"]
    requested = contract.requested_mode
    permitted = [requested, *(m for m in contract.allowed_weaker_modes if modes.index(m) > modes.index(requested))]
    effective = next((mode for mode in permitted if supports_chat_schema and (mode == "prompt_only" or
        capabilities.get(mode + "_supported") is True)), None)
    if effective is None:
        raise AppException("Provider chưa có capability phù hợp hợp đồng đầu ra.",
            code="MODEL_OUTPUT_CONTRACT_UNSUPPORTED", status_code=422, details={"stage": "capability", "requested_mode": requested})
    business, wire = contract_schemas(contract.name)
    return {"name": contract.name, "version": contract_version(contract.name), "requested_mode": requested, "effective_mode": effective,
        "reason": "declared_capability" if effective == requested else "explicit_policy_allows_weaker_mode",
        "schema_hash": schema_hash(wire), "business_schema_hash": schema_hash(business)}


def response_format(contract: dict) -> dict | None:
    version = contract_version(contract["name"])
    business, wire = contract_schemas(contract["name"])
    if (contract.get("version", version) != version or contract.get("schema_hash", schema_hash(wire)) != schema_hash(wire)
            or contract.get("business_schema_hash", schema_hash(business)) != schema_hash(business)):
        raise ValueError("OUTPUT_CONTRACT_METADATA_MISMATCH")
    if contract["effective_mode"] == "prompt_only":
        return None
    if contract["effective_mode"] == "json_object":
        return {"type": "json_object"}
    return {"type": "json_schema", "json_schema": {"name": contract["name"], "strict": True,
        "schema": wire}}
