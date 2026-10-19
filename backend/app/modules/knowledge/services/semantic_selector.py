"""Validate the complete final output, never repair or accept a JSON prefix."""
import hashlib
import json

from pydantic import ValidationError

from app.core.exceptions import AppException
from app.modules.knowledge.services.semantic_binding import selector_type
from app.modules.modelops.services.output_contract import (
    contract_schemas,
    contract_version,
    schema_hash,
)


class SelectorError(AppException):
    def __init__(self, stage: str, reason: str, **diagnostics):
        super().__init__("Phản hồi selector chưa đạt hợp đồng; chưa áp dụng dữ liệu.",
            code="SEMANTIC_OUTPUT_INVALID", status_code=422,
            details={"stage": stage, "reason": reason, **diagnostics})


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("non_finite_number")


def _required_fields(data, node, root):
    if "$ref" in node:
        node = root["$defs"][node["$ref"].rsplit("/", 1)[1]]
    if isinstance(data, dict) and node.get("type") == "object":
        if set(node.get("properties", {})) - data.keys():
            raise ValueError("missing_required_field")
        for key, value in data.items():
            if key in node.get("properties", {}):
                _required_fields(value, node["properties"][key], root)
    if isinstance(data, list) and node.get("type") == "array":
        for value in data:
            _required_fields(value, node["items"], root)


def parse_selector(response, effective_mode: str, *, expected_contract: str = "qnu_semantic_selector_v1") -> tuple:
    raw = response.content
    trace = {"raw_content_sha256": hashlib.sha256(raw.encode()).hexdigest(), "normalization": "none"}
    try:
        expected = selector_type(expected_contract)
        version = contract_version(expected_contract)
        business, schema = contract_schemas(expected_contract)
        metadata = getattr(response, "output_contract", None)
        if metadata is not None and (metadata.get("name") != expected_contract or metadata.get("version") != version
                or metadata.get("schema_hash") != schema_hash(schema) or metadata.get("business_schema_hash") != schema_hash(business)
                or metadata.get("effective_mode") != effective_mode):
            raise ValueError("SELECTOR_CONTRACT_METADATA_MISMATCH")
    except ValueError as exc:
        raise SelectorError("contract", "expected_contract_mismatch", **trace) from exc
    if getattr(response, "refusal", None) or getattr(response, "finish_reason", None) == "content_filter":
        raise SelectorError("refusal", "provider_refused", **trace)
    finish = getattr(response, "finish_reason", None)
    if finish is not None and finish != "stop":
        raise SelectorError("response_incomplete", "output_not_complete", **trace)
    if not raw.strip():
        raise SelectorError("response_incomplete", "empty_content", **trace)
    content = raw.strip()
    if effective_mode == "prompt_only" and content.startswith(("```json\n", "```\n")) and content.endswith("\n```"):
        content = content.split("\n", 1)[1][:-4]
        trace["normalization"] = "single_whole_json_fence"
    trace["normalized_content_sha256"] = hashlib.sha256(content.encode()).hexdigest()
    try:
        data = json.loads(content, object_pairs_hook=_unique_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        reason = exc.msg if isinstance(exc, json.JSONDecodeError) else "duplicate_key_or_non_finite_or_depth"
        raise SelectorError("json_syntax", reason, line=getattr(exc, "lineno", None),
            column=getattr(exc, "colno", None), **trace) from exc
    try:
        if not isinstance(data, dict):
            raise TypeError("root_must_be_object")
        _required_fields(data, schema, schema)
        return expected.model_validate(data, strict=True), trace
    except (ValueError, TypeError, ValidationError, RecursionError) as exc:
        raise SelectorError("selector_schema", "selector_shape_invalid", **trace) from exc
