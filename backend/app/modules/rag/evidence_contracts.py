"""Data-only output instructions and request-bound verification contracts."""

import json
from typing import Annotated, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, Field, create_model
from pydantic_core import PydanticCustomError

from app.modules.rag.evidence_schemas import ClaimVerdict, VerificationResult

DataInstance = TypeVar("DataInstance", bound=BaseModel)


def validate_data_instance(contract: type[DataInstance], text: str) -> DataInstance:
    """Allow unambiguous root notation without changing evaluated data values.

    Some models output the guide's $.field notation as a literal root key.
    A same-level alias is formatting, not evidence repair. Collisions, nested
    paths and unknown fields remain validation failures. A sole object-valued
    '$' envelope denotes the root itself; unwrap once, never merge siblings or
    recursively relocate nested fields. Quotes and verdicts are untouched.
    """
    data = json.loads(text)
    if isinstance(data, dict) and set(data) == {"$"} and isinstance(data["$"], dict):
        data = data["$"]
    if isinstance(data, dict):
        aliases = {key: key[2:] for key in data
                   if key.startswith("$.") and key[2:] in contract.model_fields}
        if any(name in data for name in aliases.values()):
            raise ValueError("Ambiguous root field aliases")
        if aliases:
            data = {aliases.get(key, key): value for key, value in data.items()}
    return contract.model_validate_json(json.dumps(data, ensure_ascii=False))


def data_field_guide(contract: type[BaseModel]) -> str:
    """Describe data fields without placing a copyable JSON Schema in the prompt.

    Pydantic remains the validator. Resolve nested definitions for instructions;
    preserve constraints rather than substituting fabricated example answers.
    """
    schema = contract.model_json_schema()

    def describe(node: dict, path: str = "$", seen: frozenset[str] = frozenset()) -> str:
        if ref := node.get("$ref"):
            if ref in seen:
                return "recursive " + ref.rsplit("/", 1)[-1]
            return describe(schema["$defs"][ref.rsplit("/", 1)[-1]], path, seen | {ref})
        if options := node.get("anyOf") or node.get("oneOf"):
            kind = " OR ".join(describe(option, path, seen) for option in options)
        elif "const" in node or "enum" in node:
            kind = "one of " + json.dumps(node.get("enum", [node.get("const")]), ensure_ascii=False)
        elif node.get("type") == "object":
            required = set(node.get("required", []))
            fields = [f"{path}.{name} ({'required' if name in required else 'optional'}): "
                      + describe(value, f"{path}.{name}", seen)
                      for name, value in node.get("properties", {}).items()]
            extras = node.get("additionalProperties", True)
            fields.append(f"{path} other keys: " + (describe(extras, path + ".*", seen) if isinstance(extras, dict)
                                           else "allowed" if extras else "forbidden"))
            kind = "object at " + path + "\n" + "\n".join(fields)
        elif node.get("type") == "array":
            kind = "array of (" + describe(node.get("items", {}), path + "[]", seen) + ")"
        else:
            kind = node.get("type", "JSON value")
        bounds = {key: node[key] for key in (
            "minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum",
            "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "pattern", "format",
        ) if key in node}
        if bounds:
            kind += " constraints " + json.dumps(bounds, ensure_ascii=False)
        if "description" in node:
            kind += " — " + node["description"]
        return kind

    return describe(schema)


def exact_id_items(expected: tuple[str, ...], field: str) -> AfterValidator:
    """Validate identity coverage during the existing structured repair budget.

    Never fill in missing verdicts, renumber by position or pick a duplicate.
    Diagnostics contain counts only, not untrusted generated IDs or claims.
    """
    def validate(items: list) -> list:
        ids = [getattr(item, field) for item in items]
        if len(ids) != len(set(ids)) or set(ids) != set(expected):
            raise PydanticCustomError("id_coverage", "Return exactly one entry per supplied ID", {
                "missing_count": len(set(expected) - set(ids)),
                "unknown_count": len(set(ids) - set(expected)),
                "duplicate_count": len(ids) - len(set(ids)),
            })
        return items
    return AfterValidator(validate)


def verification_contract(claims: list[dict], topics: list[str] | None = None) -> type[VerificationResult]:
    expected = tuple(claim["id"] for claim in claims)
    verdict = create_model("BoundClaimVerdict", __base__=ClaimVerdict,
                           claim_id=(Literal[expected], ...))
    verdicts = Annotated[list[verdict], exact_id_items(expected, "claim_id")]
    fields = {}
    if topics:
        expected_topics = frozenset(topics)

        def check_topics(value: dict[str, bool]) -> dict[str, bool]:
            if set(value) != expected_topics:
                raise PydanticCustomError("topic_coverage", "Evaluate every exact requested topic", {
                    "missing_count": len(expected_topics - set(value)),
                    "unknown_count": len(set(value) - expected_topics)})
            return value

        fields["topic_coverage"] = (Annotated[dict[str, bool], AfterValidator(check_topics)],
            Field(..., description="Required keys, each explicitly true or false: " + json.dumps(topics, ensure_ascii=False)))
    return create_model("BoundVerificationResult", __base__=VerificationResult, **fields,
        verdicts=(verdicts, Field(min_length=len(expected), max_length=len(expected),
            description="Exactly one verdict per supplied claim ID; no duplicates or omissions.")))
