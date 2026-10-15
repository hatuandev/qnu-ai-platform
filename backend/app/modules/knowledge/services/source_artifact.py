"""Revision-bound structured derivatives; no vocabulary-based table classification."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.modules.knowledge.facts import column_role_evidence, detect_column_role
from app.modules.knowledge.normalization.retrieval_units import build_unit_manifest, manifest_digest
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.fact_identity import build_fact_identity
from app.modules.knowledge.services.html_tables import normalize_html_tables
from app.modules.knowledge.services.table_context import (
    clean_cell,
    extract_context_tables,
    row_identities,
)
from app.modules.knowledge.services.temporal_metadata import extract_temporal_metadata

ARTIFACT_VERSION = "structured-source-v7-context-links"
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_ATTRIBUTE_CODES = {"benchmark": "cutoff_score", "quota": "expected_quota", "combos": "subject_combinations",
                    "tuition": "tuition_fee", "code": "entity_code", "method": "admission_method"}


def cell_context(header: str) -> dict[str, Any]:
    years = sorted({int(y) for y in _YEAR.findall(header)})
    role, matched = column_role_evidence(header)
    words = lambda value: re.findall(r"[^\W\d_]+", value.casefold())
    specific = bool(matched)
    if role == "benchmark":
        specific = len(words(matched or "")) >= 2
    elif role == "method":
        specific = words(header) == words(matched or "")
    methods = re.findall(r"\(([^()]*)\)", header)
    temporal = {"type": "year" if len(years) == 1 else "unknown", "year": years[0] if len(years) == 1 else None,
                "years": years, "status": "proposed" if len(years) == 1 else "ambiguous" if years else "unknown",
                "evidence": "column_header"}
    return {"attribute_code": _ATTRIBUTE_CODES.get(role) if specific else None, "temporal_context": temporal,
            "attribute_context": {"raw_header": header, "status": "recognized" if specific else "unknown"},
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
    data_tables = [table for table in (parser_tables or []) if len(table.get("headers", [])) >= 2]
    if data_tables and not tables:
        issues.append({"code": "TABLES_NOT_MATERIALIZED"})
    values: dict[tuple[Any, ...], str] = {}
    for table in tables:
        headers = table["headers"]
        duplicate_columns = {col for col, header in enumerate(headers) if header.strip()
                             and sum(other.casefold() == header.casefold() for other in headers) > 1}
        if duplicate_columns:
            issues.append({"code": "AMBIGUOUS_COLUMN_CONTEXT", "table_id": table["id"],
                           "column_indexes": sorted(duplicate_columns)})
        if headers and re.fullmatch(r"\d+[.)]?", headers[0].strip()) and any(re.fullmatch(r"\d{3,}", h.strip()) for h in headers[1:]):
            issues.append({"code": "TABLE_HEADER_UNRESOLVED", "table_id": table["id"], "page_number": table["page_number"]})
            continue
        for row_index, row in enumerate(table["rows"]):
            if len(row) != len(headers):
                issues.append({"code": "TABLE_WIDTH_MISMATCH", "table_id": table["id"], "row_index": row_index})
                continue
            for identity, end, entity, code in row_identities(row, table):
                row_context = tuple((headers[col], clean_cell(row[col])) for col in range(identity)
                                    if clean_cell(row[col]) and clean_cell(row[col]) != code
                                    and not (col == 0 and re.fullmatch(r"\d+[.)]?", clean_cell(row[col]))))
                code_columns = [col for col in range(identity) if identity + 1 == end and code and clean_cell(row[col]) == code
                                and detect_column_role(headers[col])[0] == "code"]
                for col in [*code_columns, *range(identity + 1, end)]:
                    cell = clean_cell(row[col])
                    if not cell:
                        continue
                    if not headers[col].strip():
                        issues.append({"code": "MISSING_COLUMN_HEADER", "table_id": table["id"], "column_index": col})
                        continue
                    attribute = headers[col].strip()
                    key = (code or "", entity.casefold(), attribute.casefold(), row_context)
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
                    evidence["row_context"] = list(row_context)
                    if col in duplicate_columns:
                        evidence["temporal_context"]["status"] = "ambiguous"
                        evidence["context_ambiguous"] = True
                    evidence["header_page_number"] = table.get("header_page_number", table["page_number"])
                    if table.get("continuation_of"):
                        evidence["continuation_of"] = table["continuation_of"]
                    identity_value = clean_cell(row[identity])
                    if re.fullmatch(r"\d+(?:[.,]\d+)?", identity_value) and not re.fullmatch(r"(?:19|20)\d{2}", identity_value):
                        evidence["relation"] = {"type": "numeric_mapping", "input_label": " / ".join(table["header_paths"][identity]), "input_value": identity_value}
                    fact_id = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
                    fact_identity = build_fact_identity(entity, raw_data=evidence, entity_code=code)
                    facts.append({"id": f"draft_{fact_id}", "entity_name": fact_identity.entity_text,
                              "entity_key": fact_identity.entity_key, "entity_label": fact_identity.entity_label,
                              "entity_text": fact_identity.entity_text, "entity_type": "table_row",
                              "attribute_name": attribute, "attribute_value": cell.strip(),
                              "confidence": 0.0, "raw_data": evidence})
    temporal_metadata = extract_temporal_metadata(markdown, str(metadata.get("filename") or ""))
    units = build_unit_manifest(markdown, temporal_metadata)
    from app.modules.knowledge.services.source_links import attach_fact_context, build_context_graph

    graph = build_context_graph(units)
    attach_fact_context(facts, units, graph)
    return {"version": ARTIFACT_VERSION, "content_hash": content_hash, "metadata": metadata,
            "temporal_metadata": temporal_metadata,
            "retrieval_units": units.model_dump(), "unit_manifest_hash": manifest_digest(units),
            "context_graph": graph,
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


def get_structured_review_state(revision: Any) -> tuple[str, bool, int]:
    """Derive the effective review state from the revision-bound artifact.

    ``revision.status`` is the parsing lifecycle state and can be stale for
    revisions created before structured review was introduced. Publication and
    UI decisions must therefore use this artifact state as their source of
    truth.
    """
    artifact = get_source_artifact(revision)
    issues = list(artifact.get("issues") or [])
    review_status = str((artifact.get("review") or {}).get("status") or "auto_ready")
    approved = review_status == "approved"
    requires_review = not approved and (review_status == "required" or bool(issues))
    effective_status = "required" if requires_review else review_status
    return effective_status, requires_review, len(issues)


def add_layout_issues(artifact: dict[str, Any], pages: list[dict[str, Any]]) -> None:
    """Retain visual uncertainty instead of making chart numbers into facts."""
    for page in pages:
        number = page.get("page_number", page.get("page"))
        rescue = page.get("metadata_rescue")
        if rescue:
            artifact["issues"].append({"code": "METADATA_OCR_REVIEW", "page_number": number,
                                       "rescue": rescue})
        blocks = page.get("blocks", [])
        data_regions = [b for b in blocks if b.get("type") == "table" and _is_data_region(b.get("text", ""))]
        if data_regions and not any(t.get("page_number") == number for t in artifact["tables"]):
            artifact["issues"].append({"code": "TABLES_NOT_MATERIALIZED", "page_number": number})
        for block in blocks:
            coordinates = block.get("coordinates") or {}
            area = coordinates.get("width", 0) * coordinates.get("height", 0)
            if block.get("type") in {"chart", "figure", "image"} and area >= 200:
                artifact["issues"].append({"code": "VISUAL_CONTENT_REVIEW", "page_number": number, "block_id": block.get("id")})
    if artifact["issues"]:
        artifact["review"] = {"status": "required"}


def _is_data_region(text: str) -> bool:
    """Whitespace-aligned prose is not evidence of a missing structured table."""
    grid = [_split_gfm_row(line) for line in normalize_html_tables(text).splitlines()
            if line.strip().startswith("|") and not re.fullmatch(r"[\s|:\-]+", line)]
    if not grid:
        return False
    headers = [clean_cell(cell) for cell in grid[0] if clean_cell(cell)]
    if len(headers) >= 2 and all(any(char.isalpha() for char in h) and len(h) <= 120 for h in headers):
        return True
    return sum(bool(row and re.fullmatch(r"\d+[.)]?", clean_cell(row[0]))
                    and any(re.fullmatch(r"\d{3,}[A-Za-z]*", clean_cell(cell)) for cell in row[1:]))
               for row in grid) >= 2
