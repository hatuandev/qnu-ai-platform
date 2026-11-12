"""Bounded source context and conservative, text-only spelling proposals."""

import re
import unicodedata

from pydantic import ValidationError

from qnu.domains.ocr.review.anchors import anchor_suggestions, context_supports, reject
from qnu.domains.ocr.review.schemas import (
    ContextSuggestedText,
    RejectedSuggestion,
    Suggestion,
    TextUnit,
)
from qnu.platform.errors import AppException

CONTEXT_VERSION = "qnu.ocr.spelling-context/v1"
MAX_CONTEXT_CHARS = 8000
MAX_CONTEXT_ITEM_CHARS = 1500


def build_context(document: dict, targets: dict[str, TextUnit], *, max_chars=MAX_CONTEXT_CHARS):
    """Only same-table cells, source neighbors and the preceding heading are read-only."""
    contexts, seen = [], set(targets)
    remaining, truncated = max_chars, False

    def add(block, page, relation, parent=None, row=None, column=None):
        nonlocal remaining, truncated
        evidence_id = block["evidence_id"]
        if evidence_id in seen:
            return
        seen.add(evidence_id)
        text = block["text"]
        limit = min(MAX_CONTEXT_ITEM_CHARS, remaining)
        clipped = len(text) > limit
        truncated |= clipped
        if not limit or not text:
            return
        contexts.append(
            {
                "evidence_id": evidence_id,
                "page": page,
                "kind": block.get("type", "table_cell"),
                "text": text[:limit],
                "read_only": True,
                "relationship": relation,
                "parent_evidence_id": parent,
                "row": row,
                "column": column,
                "truncated": clipped,
            }
        )
        remaining -= len(text[:limit])

    blocks = [(p["page_number"], b) for p in document["pages"] for b in p["blocks"]]
    heading = None
    for index, (page, block) in enumerate(blocks):
        if block["type"] == "title":
            heading = (page, block)
        table = block.get("table")
        rows = table["rows"] if table and table["status"] == "parsed" else []
        selected_rows = {
            r for r, row in enumerate(rows) if any(c["evidence_id"] in targets for c in row)
        }
        if block["evidence_id"] not in targets and not selected_rows:
            continue
        if heading:
            add(heading[1], heading[0], "preceding_heading")
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                if cell.get("header") or r in selected_rows:
                    add(
                        cell,
                        page,
                        "table_header" if cell.get("header") else "table_row",
                        block["evidence_id"],
                        r + 1,
                        c + 1,
                    )
        for neighbor in (index - 1, index + 1):
            if 0 <= neighbor < len(blocks):
                other_page, other = blocks[neighbor]
                if not other.get("table") and abs(other_page - page) <= 1:
                    relation = "adjacent_block" if other_page == page else "page_boundary_candidate"
                    add(other, other_page, relation)
    return {
        "context_version": CONTEXT_VERSION,
        "source_image_verified": False,
        "units": [u.model_dump(exclude={"original_text", "bbox"}) for u in targets.values()],
        "context": contexts,
        "context_truncated": truncated,
    }


def _letter_shape(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return "".join(c for c in text if not unicodedata.combining(c))


def contextual_suggestions(
    content: str, units: dict[str, TextUnit]
) -> tuple[list[Suggestion], list[Suggestion], list[RejectedSuggestion]]:
    """Quarantine proposals one by one; only edits proven against the source survive."""
    try:
        parsed = ContextSuggestedText.model_validate_json(content)
    except ValidationError as exc:
        raise AppException(
            "Gợi ý hoặc ngữ cảnh sửa không khớp nguồn; chưa áp dụng thay đổi nào.",
            code="ocr_spelling_invalid",
            status_code=502,
        ) from exc
    anchored, rejected = anchor_suggestions(parsed.suggestions, units)
    accepted, withheld, occupied = [], [], {}
    for item in anchored:
        text = units[item.evidence_id].text
        if item.original == item.replacement:
            rejected.append(reject(item, "no_change"))
            continue
        if not item.replacement.strip():
            rejected.append(reject(item, "empty_replacement"))
            continue
        if re.findall(r"\d+", item.original) != re.findall(r"\d+", item.replacement):
            rejected.append(reject(item, "numeric_change"))
            continue
        spans = occupied.setdefault(item.evidence_id, [])
        if any(item.start < end and item.end > start for start, end in spans):
            rejected.append(reject(item, "overlap"))
            continue
        result = Suggestion.model_validate({**item.model_dump(), "review_reason": None})
        if not context_supports(item, text, item.start):
            # A definite anchor is kept for manual review; an ambiguous literal
            # with a contradictory quote is not a trustworthy target at all.
            if len(re.findall(re.escape(item.original), text)) != 1:
                rejected.append(reject(item, "context_unverified"))
                continue
            spans.append((item.start, item.end))
            withheld.append(result.model_copy(update={"review_reason": "context_unverified"}))
            continue
        spans.append((item.start, item.end))
        if _letter_shape(item.original) != _letter_shape(item.replacement):
            withheld.append(result.model_copy(update={"review_reason": "source_image_required"}))
        else:
            accepted.append(result)
    return accepted, withheld, rejected
