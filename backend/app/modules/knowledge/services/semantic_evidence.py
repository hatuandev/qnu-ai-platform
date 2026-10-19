"""Exact source selectors. All offsets are Python Unicode code points, half-open."""

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.knowledge.normalization.retrieval_models import UnitManifest


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class EvidenceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_identity: dict[str, str | None]
    input_hash: str
    source_unit_id: str
    coordinate_space: Literal["unit_codepoints", "cell_raw_codepoints"]
    column_id: str | None = None
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text_sha256: str
    evidence_id: str


def source_identity(artifact: dict) -> dict:
    reference = artifact["qnu_input"]
    return {key: reference.get(key) for key in ("document_id", "revision_id", "sha256", "structured_sha256")}


def source_text(artifact: dict, unit_id: str, column_id: str | None = None) -> str:
    units = [unit for unit in artifact["retrieval_units"]["units"] if unit["id"] == unit_id]
    if len(units) != 1 or units[0]["is_container"]:
        raise ValueError("EVIDENCE_UNIT_INVALID")
    if column_id is None:
        return units[0]["text"]
    fields = [field for table in artifact["tables"]
              for rid, row in zip(table["row_unit_ids"], table["row_fields"], strict=True) if rid == unit_id
              for field in row if field["column_id"] == column_id]
    if len(fields) != 1:
        raise ValueError("EVIDENCE_CELL_INVALID")
    return fields[0]["raw"]


def make_binding(artifact: dict, unit_id: str, start: int, end: int,
                 column_id: str | None = None, *, input_hash: str | None = None) -> EvidenceBinding:
    from app.modules.knowledge.services.semantic_annotations import semantic_input_hash

    text = source_text(artifact, unit_id, column_id)
    if not 0 <= start < end <= len(text):
        raise ValueError("EVIDENCE_SPAN_INVALID")
    payload = {"source_identity": source_identity(artifact), "input_hash": input_hash or semantic_input_hash(artifact),
               "source_unit_id": unit_id, "column_id": column_id, "start": start, "end": end,
               "coordinate_space": "cell_raw_codepoints" if column_id else "unit_codepoints",
               "text_sha256": hashlib.sha256(text.encode()).hexdigest()}
    return EvidenceBinding(**payload, evidence_id="ev:" + digest(payload)[:32])


def verify_binding(artifact: dict, binding: EvidenceBinding, quote: str, unit_id: str) -> None:
    if binding.source_unit_id != unit_id:
        raise ValueError("EVIDENCE_UNIT_MISMATCH")
    expected = make_binding(artifact, unit_id, binding.start, binding.end, binding.column_id)
    if expected != binding or quote != source_text(artifact, unit_id, binding.column_id)[binding.start:binding.end]:
        raise ValueError("EVIDENCE_SOURCE_OR_SPAN_MISMATCH")


def evidence_spans(artifact: dict, unit_id: str, *, max_chars: int,
                   column_id: str | None = None, input_hash: str | None = None) -> list[dict]:
    """Offer exact whole/clauses, never a normalized or reconstructed quote."""
    text = source_text(artifact, unit_id, column_id)
    spans = []
    if 3 <= len(text) <= max_chars:
        spans.append((0, len(text)))
    for match in re.finditer(r"[^.;\n]+(?:[.;]|$)", text):
        for start in range(match.start(), match.end(), max_chars):
            end = min(match.end(), start + max_chars)
            if len(text[start:end].strip()) >= 3:
                spans.append((start, end))
    result = []
    for start, end in dict.fromkeys(spans):
        binding = make_binding(artifact, unit_id, start, end, column_id, input_hash=input_hash)
        result.append({"id": binding.evidence_id, "source_unit_id": unit_id, "column_id": column_id,
                       "text": text[start:end], "binding": binding.model_dump()})
    return result


def verify_annotation_bindings(artifact: dict, proposals) -> None:
    for category in (proposals.notes, proposals.cells, proposals.limitations):
        for item in category:
            binding = item.evidence_binding
            if binding is None:
                continue  # Exact-quote legacy annotations retain their existing validators.
            unit_id = getattr(item, "note_unit_id", None) or item.evidence_unit_id
            verify_binding(artifact, binding, item.evidence_quote, unit_id)
            if binding.column_id is not None and (getattr(item, "row_unit_id", None), item.column_id) != (unit_id, binding.column_id):
                raise ValueError("EVIDENCE_SIBLING_CELL_FORBIDDEN")


def verify_source_document(artifact: dict, document) -> UnitManifest:
    """The caller supplies the Structured Document read from a verified source pair."""
    from app.modules.knowledge.normalization.qnu_projection import project_document
    from app.modules.knowledge.normalization.retrieval_units import manifest_hash_matches
    from app.modules.knowledge.services.qnu_serving import input_reference

    if document is None:
        raise ValueError("SEMANTIC_STRUCTURED_SOURCE_REQUIRED")
    manifest = UnitManifest.model_validate(artifact["retrieval_units"])
    if not manifest_hash_matches(artifact["unit_manifest_hash"], manifest):
        raise ValueError("SEMANTIC_MANIFEST_INVALID")
    _, original = project_document(document, input_reference(artifact["qnu_input"]), {})
    actual = [(u.id, u.text, u.qnu_block_id, u.source_locations) for u in manifest.units]
    expected = [(u["id"], u["text"], u["qnu_block_id"], u["source_locations"]) for u in original["retrieval_units"]["units"]]
    raw = lambda obj: [[[(f["column_id"], f["raw"], f["state"]) for f in row] for row in t["row_fields"]] for t in obj["tables"]]
    if actual != expected or raw(artifact) != raw(original) or artifact["content_hash"] != original["content_hash"]:
        raise ValueError("SEMANTIC_STRUCTURED_SOURCE_MISMATCH")
    return manifest
