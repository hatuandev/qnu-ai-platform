"""Opt-in, source-bound search enrichment. Original chunk bytes remain separately sealed.

No inferred year, industry vocabulary, free-form summaries or model calls. Definitions
are conservative explicit parenthetical pairs in already cited canonical source.
"""

import json
import re
from dataclasses import replace

from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform.errors import AppException

VERSION = "qnu.search-context/v1"
RESERVE_BYTES = 2048
MAX_DEFINITIONS = 32


def glossary(content: dict, documents: list[dict]) -> list[dict]:
    definitions = {}
    # Definitions must themselves be reachable through the pinned citation map.
    pattern = re.compile(r"([^\n.;:!?()]{3,160})\s*\(([A-ZÀ-ỴĐ][A-ZÀ-ỴĐ0-9-]{1,15})\)")
    for document in documents:
        for page in document["pages"]:
            for block in page["blocks"]:
                citation = document["ocr_run_id"] + ":" + block["evidence_id"]
                if citation not in content["citations"]:
                    continue
                for match in pattern.finditer(block["text"]):
                    expansion, alias = match.groups()
                    expansion = expansion.strip()
                    words = expansion.split()[-len(alias) :]
                    expansion = " ".join(words)
                    # Match initials exactly; never interpret a cohort code/year or
                    # consume a whole preceding sentence as an invented definition.
                    initials = "".join(w[0] for w in words).casefold()
                    if not alias.isupper() or initials != alias.casefold() or not 2 <= len(words) <= 12:
                        continue
                    entry = {
                        "alias": alias,
                        "expansion": expansion,
                        "citation": citation,
                        "quote": match.group(0)[match.group(0).find(words[0]) :],
                    }
                    definitions[digest(entry)] = entry
    result = [definitions[key] for key in sorted(definitions)]
    if len(result) > MAX_DEFINITIONS:
        raise AppException(
            "Danh mục định nghĩa vượt ngân sách ngữ cảnh.",
            code="index_glossary_too_large",
            status_code=422,
        )
    return result


def enrich(chunks, content: dict, documents: list[dict], maximum: int):
    definitions = glossary(content, documents)
    result = []
    for chunk in chunks:
        structure = chunk.structure or {}
        # Structured metadata stays per annotated unit; do not turn all values
        # in a table fragment into a claim about every row.
        metadata = structure.get("retrieval_metadata", [])
        context = {
            "version": VERSION,
            "title": content["title"],
            "heading": structure.get("context", {}).get("heading"),
            "units": [{"target": a["target"], "values": a["values"]} for a in metadata],
            "definitions": [
                d
                for d in definitions
                if re.search(r"(?<!\w)" + re.escape(d["alias"]) + r"(?!\w)", chunk.text)
            ],
        }
        prefix = json.dumps(context, ensure_ascii=False, separators=(",", ":")) + "\n"
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
                    **structure,
                    "search_context": {
                        "version": VERSION,
                        "original_text": chunk.text,
                        "original_sha256": chunk.sha256,
                        "prefix": prefix,
                        "glossary": definitions,
                    },
                },
            )
        )
    return result


def original_text(hit) -> str:
    context = (hit.structure or {}).get("search_context")
    if not context:
        return hit.text
    original = context.get("original_text", "")
    if (
        context.get("version") != VERSION
        or hit.text != context.get("prefix", "") + original
        or digest_text(original) != context.get("original_sha256")
    ):
        raise AppException(
            "Ngữ cảnh tìm kiếm không khớp nguồn.", code="index_context_invalid", status_code=409
        )
    return original


def digest_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
