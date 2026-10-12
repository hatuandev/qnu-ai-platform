"""Revision-bound structured derivatives; no vocabulary-based table classification."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.source_pages import canonical_pages

ARTIFACT_VERSION = "structured-source-v1"
_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_YEAR = re.compile(r"(?:19|20)\d{2}")


def _tables(markdown: str, page_count: int) -> list[dict[str, Any]]:
    tables = []
    for page in canonical_pages(markdown, page_count):
        lines = page["markdown_content"].splitlines()
        index = 0
        while index + 1 < len(lines):
            if "|" not in lines[index] or not _SEPARATOR.fullmatch(lines[index + 1]):
                index += 1
                continue
            start = index
            headers = _split_gfm_row(lines[index])
            index += 2
            rows = []
            while index < len(lines) and "|" in lines[index] and not _SEPARATOR.fullmatch(lines[index]):
                if index + 1 < len(lines) and _SEPARATOR.fullmatch(lines[index + 1]):
                    break
                rows.append(_split_gfm_row(lines[index]))
                index += 1
            header_rows = [headers.copy()]
            # A secondary header with year-only cells is structural, not a data row.
            if rows and any(_YEAR.fullmatch(v) for v in rows[0]) and all(
                not v or _YEAR.fullmatch(v) for v in rows[0]
            ):
                secondary = rows.pop(0)
                header_rows.append(secondary)
                parent = ""
                for col, value in enumerate(headers):
                    parent = value or parent
                    child = secondary[col] if col < len(secondary) else ""
                    headers[col] = " / ".join(v for v in (parent if child else value, child) if v)
            tables.append({"id": f"table_{len(tables) + 1}", "page_number": page["page_number"],
                           "line_number": start + 1, "headers": headers, "header_rows": header_rows,
                           "rows": rows, "evidence": "canonical_markdown"})
    return tables


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
    values: dict[tuple[str, str], str] = {}
    for table in tables:
        headers = table["headers"]
        for row_index, row in enumerate(table["rows"]):
            if len(row) != len(headers):
                issues.append({"code": "TABLE_WIDTH_MISMATCH", "table_id": table["id"], "row_index": row_index})
                continue
            # The first textual cell identifies the row. Ordinals/quantities are not identities.
            identity = next((i for i, cell in enumerate(row) if any(char.isalpha() for char in cell)), None)
            if identity is None:
                continue
            entity = row[identity].strip()
            for col, cell in enumerate(row):
                if col == identity or not cell.strip():
                    continue
                if not headers[col].strip():
                    issues.append({"code": "MISSING_COLUMN_HEADER", "table_id": table["id"], "column_index": col})
                    continue
                attribute = headers[col].strip()
                key = (entity.casefold(), attribute.casefold())
                if key in values and values[key] != cell:
                    issues.append({"code": "CONFLICTING_FACT_VALUES", "table_id": table["id"], "row_index": row_index})
                values[key] = cell
                evidence = {"page_number": table["page_number"], "table_id": table["id"],
                            "row_index": row_index, "column_index": col,
                            "header_path": attribute, "raw_value": cell,
                            "row_values": row, "content_hash": content_hash,
                            "extractor_version": ARTIFACT_VERSION,
                            "confidence_source": "unavailable",
                            "year": (match.group() if (match := _YEAR.search(attribute)) else None)}
                fact_id = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
                facts.append({"id": f"draft_{fact_id}", "entity_name": entity, "entity_type": "table_row",
                              "attribute_name": attribute, "attribute_value": cell.strip(),
                              "confidence": 0.0, "raw_data": evidence})
    return {"version": ARTIFACT_VERSION, "content_hash": content_hash, "metadata": metadata,
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
