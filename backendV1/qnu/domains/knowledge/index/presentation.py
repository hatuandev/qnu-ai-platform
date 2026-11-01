"""Readable views of sealed chunks; never infer headers or join separate tables."""

import json

from qnu.domains.knowledge.index.contextual import original_text
from qnu.domains.knowledge.index.schemas import SearchHit

TABLE_FIELDS = (
    "source_table_citation",
    "original_row_count",
    "original_column_count",
    "row_indices",
    "rows",
    "page_notes",
)
PRESENTATION_VERSION = "qnu.evidence-reading/v1"


def table_prefix(hit: SearchHit) -> str | None:
    structure = hit.structure or {}
    if hit.kind != "table" or not structure.get("rows"):
        return None
    if not all(key in structure for key in TABLE_FIELDS):
        return None
    duplicate = json.dumps(
        {key: structure[key] for key in TABLE_FIELDS}, ensure_ascii=False, sort_keys=True
    )
    text = original_text(hit)
    return text[: -len(duplicate)] if text.endswith(duplicate) else None


def reading_text(hit: SearchHit) -> str:
    prefix = table_prefix(hit)
    if prefix is None:
        return original_text(hit)
    structure = hit.structure
    lines = [prefix.rstrip()]
    for index, row in zip(structure["row_indices"], structure["rows"], strict=True):
        cells = [" ".join(cell["text"].split()) for cell in row]
        # Cell positions describe the supplied list, not expanded column offsets.
        # Spans, source row indices and IDs remain authoritative in structure.
        lines.append(f"row[{index}]: " + " | ".join(cells))
    return "\n".join(lines)


def rerank_text(hit: SearchHit) -> str:
    # JSON-escaped newlines separate words inside table cells. Models should see
    # natural text, not cell IDs, serialization keys or duplicate JSON.
    context = (hit.structure or {}).get("search_context", {})
    return " ".join((context.get("prefix", "") + reading_text(hit)).split())
