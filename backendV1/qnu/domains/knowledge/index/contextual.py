"""Opt-in, source-bound search enrichment. Original chunk bytes remain separately sealed.

No inferred year, industry vocabulary, free-form summaries or model calls. Definitions
are conservative explicit parenthetical pairs in already cited canonical source.
"""

import json
import re
from collections.abc import Callable
from dataclasses import replace

from qnu.domains.knowledge.index.abbreviations import parenthetical
from qnu.domains.knowledge.index.chunking import Chunk
from qnu.platform.errors import AppException

VERSION = "qnu.search-context/v1"
MAX_DEFINITIONS = 32


def glossary(content: dict, documents: list[dict]) -> list[dict]:
    result = parenthetical(content, documents)
    if len(result) > MAX_DEFINITIONS:
        raise AppException(
            "Danh mục định nghĩa vượt ngân sách ngữ cảnh.",
            code="index_glossary_too_large",
            status_code=422,
        )
    return result


def _prefix(chunk: Chunk, content: dict, definitions: list[dict]) -> str:
    if chunk.kind == "row_card":
        # The card renderer already adds a source breadcrumb to the indexed text.
        return ""
    structure = chunk.structure or {}
    # Structured metadata stays per annotated unit; do not turn all values
    # in a table fragment into a claim about every row.
    metadata = structure.get("retrieval_metadata", [])
    context = {
        "version": VERSION,
        "title": content.get("title", ""),
        "heading": structure.get("context", {}).get("heading"),
        "units": [{"target": a["target"], "values": a["values"]} for a in metadata],
        "definitions": [
            d
            for d in definitions
            if re.search(r"(?<!\w)" + re.escape(d["alias"]) + r"(?!\w)", chunk.text)
        ],
    }
    return json.dumps(context, ensure_ascii=False, separators=(",", ":")) + "\n"


def contextual_size(content: dict, documents: list[dict]) -> Callable[[Chunk], int]:
    """Measure the exact enrichment sent to embedding while grouping source units."""
    definitions = glossary(content, documents)

    def measure(chunk: Chunk) -> int:
        return len((_prefix(chunk, content, definitions) + chunk.text).encode("utf-8"))

    return measure


def enrich(chunks, content: dict, documents: list[dict], maximum: int):
    definitions = glossary(content, documents)
    result = []
    for chunk in chunks:
        prefix = _prefix(chunk, content, definitions)
        text = prefix + chunk.text
        if len(text.encode("utf-8")) > maximum:
            raise AppException(
                "Ngữ cảnh nguồn vượt ngân sách chunk; giảm kích thước đơn vị hoặc metadata.",
                code="index_context_too_large",
                status_code=422,
            )
        result.append(
            replace(
                chunk,
                text=text,
                structure={
                    **(chunk.structure or {}),
                    "search_context": {
                        "version": VERSION,
                        "original_text": chunk.text,
                        "original_sha256": chunk.sha256,
                        "prefix": prefix,
                        "glossary": definitions if prefix else [],
                    },
                },
            )
        )
    return result


def original_text(hit) -> str:
    return original_text_fields(hit.text, hit.structure or {})


def original_text_fields(text: str, structure: dict) -> str:
    context = structure.get("search_context")
    if not context:
        return text
    original = context.get("original_text", "")
    if (
        context.get("version") != VERSION
        or text != context.get("prefix", "") + original
        or digest_text(original) != context.get("original_sha256")
    ):
        raise AppException(
            "Ngữ cảnh tìm kiếm không khớp nguồn.", code="index_context_invalid", status_code=409
        )
    return original


def digest_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
