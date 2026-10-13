"""Deterministic identity and lossless text projections for structured facts."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

_LABEL_LIMIT = 512
_LABEL_HASH_LENGTH = 12
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class FactIdentity:
    """Stable machine key plus bounded display and lossless search projections."""

    entity_key: str
    entity_label: str
    entity_text: str


def normalize_fact_text(value: Any) -> str:
    """Normalize Unicode and structural whitespace without applying domain vocabulary."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", str(value or ""))).strip()


def bounded_fact_label(entity_text: str, limit: int = _LABEL_LIMIT) -> str:
    """Build a collision-resistant UI label while retaining full text elsewhere."""
    text = normalize_fact_text(entity_text)
    if len(text) <= limit:
        return text
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:_LABEL_HASH_LENGTH]
    suffix = f" … #{digest}"
    prefix_limit = max(1, limit - len(suffix))
    prefix = text[:prefix_limit].rstrip()
    boundary = prefix.rfind(" ")
    if boundary >= prefix_limit // 2:
        prefix = prefix[:boundary]
    return f"{prefix}{suffix}"


def build_fact_identity(
    entity_text: Any,
    *,
    raw_data: dict[str, Any] | None = None,
    entity_code: str | None = None,
) -> FactIdentity:
    """Derive identity only from normalized structure and provenance invariants."""
    text = normalize_fact_text(entity_text)
    evidence = raw_data or {}
    identity_material = {
        "entity_code": normalize_fact_text(entity_code or evidence.get("entity_code")),
        "entity_text": text,
        "page_number": evidence.get("page_number"),
        "table_id": evidence.get("table_id"),
        "row_index": evidence.get("row_index"),
        "row_context": evidence.get("row_context"),
    }
    encoded = json.dumps(identity_material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:48]
    return FactIdentity(
        entity_key=f"fact_{digest}",
        entity_label=bounded_fact_label(text),
        entity_text=text,
    )
