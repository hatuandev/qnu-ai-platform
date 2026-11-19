"""Readable views of sealed chunks; never infer headers or join separate tables."""

import json
import re

from qnu.domains.knowledge.index.contextual import original_text, original_text_fields
from qnu.domains.knowledge.index.schemas import SearchHit

TABLE_FIELDS = (
    "source_table_citation",
    "original_row_count",
    "original_column_count",
    "row_indices",
    "rows",
    "page_notes",
)
PRESENTATION_VERSION = "qnu.evidence-reading/v3"

# Paragraph units are one source line each, so a sentence routinely crosses
# several ordinals. Rerank reads a bounded window of the same input instead.
STITCH_MAX_PARTS = 4
STITCH_MAX_SIDE = 2
STITCH_MAX_BYTES = 800
SENTENCE_END = (".", "!", "?", ":", ";", "\u2026")
CLOSERS = "\"')]}\u201d\u2019\u00bb\u00ab"
NUMBERED_ITEM = re.compile(r"^\s*\d{1,3}(?:\.\d{1,3})*[.)]\s")


def table_prefix(hit: SearchHit) -> str | None:
    structure = hit.structure or {}
    if hit.kind != "table" or not structure.get("rows"):
        return None
    if not all(key in structure for key in TABLE_FIELDS):
        return None
    text = original_text(hit)
    head, separator, tail = text.rpartition("\n")
    if not separator:
        return None
    try:
        serialized = json.loads(tail)
    except ValueError:
        return None
    if not isinstance(serialized, dict) or not all(key in serialized for key in TABLE_FIELDS):
        return None
    # Split table groups add metadata such as rowspan_split to the sealed tail;
    # every serialized value must still match this chunk before reinterpreting it.
    if any(structure.get(key) != value for key, value in serialized.items()):
        return None
    return head + separator


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


def _envelope(structure: dict) -> dict | None:
    prefix = (structure.get("search_context") or {}).get("prefix", "")
    head, separator, _ = prefix.partition("\n")
    if not separator:
        return None
    try:
        value = json.loads(head)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def paragraph_body(kind: str, text: str, structure: dict) -> str | None:
    """Original paragraph text without the repeated title/heading header lines.

    The stored heading is inherited at compile time and can be stale for a line
    the compiler did not classify as a heading; it is dropped, not corrected.
    """
    envelope = _envelope(structure)
    if kind != "paragraph" or envelope is None:
        return None
    original = original_text_fields(text, structure)
    header = f"{envelope.get('title') or ''}\n{envelope.get('heading') or ''}"
    if not original.startswith(header + "\n"):
        return None
    body = original[len(header) + 1 :].strip()
    return body or None


def paragraph_title(structure: dict) -> str:
    envelope = _envelope(structure)
    return (envelope or {}).get("title") or ""


def _ends_sentence(body: str) -> bool:
    return body.rstrip().rstrip(CLOSERS).rstrip().endswith(SENTENCE_END)


def _starts_numbered_item(body: str) -> bool:
    return bool(NUMBERED_ITEM.match(body))


def stitch_window(bodies: dict[int, str], anchor: int) -> str | None:
    """Join contiguous paragraph fragments that together form sentence(s) around anchor.

    A fragment that already ends its sentence is never merged backward; a
    neighbor that opens a numbered item is included and ends the walk so the
    window covers whole items only.
    """
    if anchor not in bodies:
        return None
    parts = [bodies[anchor]]
    current = anchor
    for _ in range(STITCH_MAX_SIDE):
        previous = bodies.get(current - 1)
        if previous is None or _ends_sentence(previous):
            break
        parts.insert(0, previous)
        current -= 1
        if _starts_numbered_item(previous):
            break
    current = anchor
    for _ in range(min(STITCH_MAX_SIDE, STITCH_MAX_PARTS - len(parts))):
        if _ends_sentence(parts[-1]):
            break
        following = bodies.get(current + 1)
        if following is None:
            break
        parts.append(following)
        current += 1
    if len(parts) < 2:
        return None
    window = " ".join(parts)
    if len(window.encode("utf-8")) > STITCH_MAX_BYTES:
        return None
    return window
