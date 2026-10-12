"""Revision-bound structured derivatives; no vocabulary-based table classification."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.services.table_context import (
    clean_cell,
    extract_context_tables,
    row_identities,
)
from app.modules.knowledge.services.temporal_metadata import extract_temporal_metadata

ARTIFACT_VERSION = "structured-source-v3-context-relations"
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_ATTRIBUTE_CODES = {"benchmark": "cutoff_score", "quota": "expected_quota", "combos": "subject_combinations",
                    "tuition": "tuition_fee", "code": "entity_code", "method": "admission_method"}


def cell_context(header: str) -> dict[str, Any]:
    years = sorted({int(y) for y in _YEAR.findall(header)})
    role, _ = detect_column_role(header)
    methods = re.findall(r"\(([^()]*)\)", header)
    temporal = {"type": "year" if len(years) == 1 else "unknown", "year": years[0] if len(years) == 1 else None,
                "years": years, "status": "proposed" if len(years) == 1 else "ambiguous" if years else "unknown",
                "evidence": "column_header"}
    return {"attribute_code": _ATTRIBUTE_CODES.get(role), "temporal_context": temporal,
            "qualifiers": {"method": methods[-1] if role == "benchmark" and len(methods) == 1 else None}}


def _tables(markdown: str, page_count: int) -> list[dict[str, Any]]:
    return extract_context_tables(markdown, page_count)

def build_source_artifact(markdown: str, page_count: int, metadata: dict[str, Any],
                          parser_tables: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Extract draft cell facts once, preserving nulls, headers and exact evidence.

    No inferred major/type/unit: row identity and attribute are copied from the table.
    Ambiguous width/header/conflicts require review, never coerce empty cells to zero.
    """
    content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    tables = _tables(markdown, page_count)
    facts, issues = [], []
    if parser_tables and not tables:
        issues.append({"code": "TABLES_NOT_MATERIALIZED"})
    values: dict[tuple[str, str, str], str] = {}
    for table in tables:
        headers = table["headers"]
        for row_index, row in enumerate(table["rows"]):
            if len(row) != len(headers):
                issues.append({"code": "TABLE_WIDTH_MISMATCH", "table_id": table["id"], "row_index": row_index})
                continue
            for identity, end, entity, code in row_identities(row, table):
                for col in range(identity + 1, end):
                    cell = clean_cell(row[col])
                    if not cell:
                        continue
                    if not headers[col].strip():
                        issues.append({"code": "MISSING_COLUMN_HEADER", "table_id": table["id"], "column_index": col})
                        continue
                    attribute = headers[col].strip()
                    key = (code or "", entity.casefold(), attribute.casefold())
                    if key in values and values[key] != cell:
                        issues.append({"code": "CONFLICTING_FACT_VALUES", "table_id": table["id"], "row_index": row_index})
                    values[key] = cell
                    evidence = {"page_number": table["page_number"], "table_id": table["id"],
                            "row_index": row_index, "column_index": col,
                            "header_path": attribute, "raw_value": cell,
                            "row_values": row, "content_hash": content_hash,
                            "extractor_version": ARTIFACT_VERSION,
                            "confidence_source": "unavailable",
                            "year": (match.group() if (match := _YEAR.search(attribute)) else None),
                            "entity_code": code, "header_segments": table["header_paths"][col], **cell_context(attribute)}
                    evidence["header_page_number"] = table.get("header_page_number", table["page_number"])
                    if table.get("continuation_of"):
                        evidence["continuation_of"] = table["continuation_of"]
                    identity_value = clean_cell(row[identity])
                    if re.fullmatch(r"\d+(?:[.,]\d+)?", identity_value) and not re.fullmatch(r"(?:19|20)\d{2}", identity_value):
                        evidence["relation"] = {"type": "numeric_mapping", "input_label": " / ".join(table["header_paths"][identity]), "input_value": identity_value}
                    fact_id = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
                    facts.append({"id": f"draft_{fact_id}", "entity_name": entity, "entity_type": "table_row",
                              "attribute_name": attribute, "attribute_value": cell.strip(),
                              "confidence": 0.0, "raw_data": evidence})
    return {"version": ARTIFACT_VERSION, "content_hash": content_hash, "metadata": metadata,
            "temporal_metadata": extract_temporal_metadata(markdown, str(metadata.get("filename") or "")),
            "tables": tables, "parser_tables": parser_tables or [], "facts": facts, "issues": issues,
            "fact_set_hash": hashlib.sha256(json.dumps(facts, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "review": {"status": "required" if issues else "auto_ready"}}


def get_source_artifact(revision: Any) -> dict[str, Any]:
    """Legacy compatibility computes a read-only draft, never mutates published data."""
    stored = (revision.parse_provenance or {}).get("structured_artifact")
    if stored and stored.get("content_hash") == revision.canonical_hash:
        return stored
    from app.modules.knowledge.services.source_pages import manifest_page_count

    artifact = build_source_artifact(revision.canonical_markdown or "", manifest_page_count(revision.page_manifest),
                                     revision.citation_metadata or {})
    artifact["review"] = {"status": "legacy_preview"}
    return artifact
