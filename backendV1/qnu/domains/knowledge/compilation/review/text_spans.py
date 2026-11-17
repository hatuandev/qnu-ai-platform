"""Budgeted review views of text whose draft preserves the source exactly."""

from __future__ import annotations

import re
from dataclasses import replace

from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.review import parts
from qnu.domains.knowledge.compilation.review.material import ReviewMaterial
from qnu.platform.errors import AppException, Conflict

VERSION = "source_text_spans/v1"
TOO_LARGE = "compilation_review_segment_too_large"
SpanLayout = dict[str, dict[str, list[int]]]


def _escaped_bytes(text: str) -> int:
    # The unit JSON is inside the user message, which is itself JSON serialized.
    return len(json_bytes(json_bytes(text).decode()))


def _ends(text: str, budget: int) -> list[int]:
    ends = []
    start = 0
    while start < len(text):
        left, right = start, min(len(text), start + budget)
        while left < right:
            mid = (left + right + 1) // 2
            if _escaped_bytes(text[start:mid]) <= budget:
                left = mid
            else:
                right = mid - 1
        if left == start:
            return []
        end = left
        if end < len(text):
            tail_start = start + (end - start) * 3 // 4
            tail = text[tail_start:end]
            boundary = list(re.finditer(r"[.!?;:]\s", tail)) or list(re.finditer(r"\s", tail))
            if boundary:
                end = tail_start + boundary[-1].end()
        ends.append(end)
        start = end
    return ends


def _drafts_by_source(payload: dict) -> dict[str, list[dict]]:
    by_source: dict[str, list[dict]] = {}
    shared: set[str] = set()
    for unit in payload["draft_units"]:
        refs = unit.get("citations") or []
        if unit["kind"] == "paragraph" and len(refs) == 1:
            by_source.setdefault(refs[0], []).append(unit)
        else:
            shared.update(refs)
    return {ref: units for ref, units in by_source.items() if ref not in shared}


def _layout(payload: dict, budget: int) -> SpanLayout:
    by_source = _drafts_by_source(payload)
    layout = {}
    for source in payload["source_units"]:
        drafts = by_source.get(source["id"])
        if source.get("table_id") or not drafts or _escaped_bytes(source["text"]) <= budget:
            continue
        if "".join(unit["text"] for unit in drafts) != source["text"]:
            continue
        offsets = {unit["id"]: _ends(unit["text"], budget) for unit in drafts}
        if all(offsets.values()):
            layout[source["id"]] = offsets
    return layout


def _span_conflict() -> Conflict:
    return Conflict(
        "Phạm vi đoạn rà soát không khớp văn bản nguồn đã ghim.",
        code="compilation_review_text_span_mismatch",
    )


def _replacements(payload: dict, layout: SpanLayout) -> tuple[dict, dict]:
    sources = {unit["id"]: unit for unit in payload["source_units"]}
    by_source = _drafts_by_source(payload)
    source_replacements, draft_replacements = {}, {}
    for key, offsets in layout.items():
        source, drafts = sources.get(key), by_source.get(key)
        if not source or source.get("table_id") or not drafts:
            raise _span_conflict()
        if (
            set(offsets) != {unit["id"] for unit in drafts}
            or "".join(unit["text"] for unit in drafts) != source["text"]
        ):
            raise _span_conflict()
        source_spans = []
        origin = 0
        for draft in drafts:
            ends = offsets[draft["id"]]
            if (
                not ends
                or ends[-1] != len(draft["text"])
                or not all(type(end) is int and end > start for start, end in zip((0, *ends), ends))
            ):
                raise _span_conflict()
            draft_spans = []
            for start, end in zip((0, *ends), ends):
                a, b = origin + start, origin + end
                source_id = f"{key}:chars:{a}:{b}"
                provenance = {"source_block_id": key, "start_char": a, "end_char": b}
                text = source["text"][a:b]
                source_spans.append({**source, **provenance, "id": source_id, "text": text})
                draft_spans.append(
                    {
                        **draft,
                        **provenance,
                        "id": f"{draft['id']}:chars:{start}:{end}",
                        "draft_paragraph_id": draft["id"],
                        "text": text,
                        "citations": [source_id],
                    }
                )
            draft_replacements[draft["id"]] = draft_spans
            origin += ends[-1]
        source_replacements[key] = source_spans
    return source_replacements, draft_replacements


def apply_layout(material: ReviewMaterial, layout: SpanLayout) -> ReviewMaterial:
    if not layout:
        return material
    source, draft = _replacements(material.payload, layout)
    return replace(
        material,
        payload={
            **material.payload,
            "source_units": [
                item for u in material.payload["source_units"] for item in source.get(u["id"], [u])
            ],
            "draft_units": [
                item for u in material.payload["draft_units"] for item in draft.get(u["id"], [u])
            ],
        },
    )


def plan(
    material: ReviewMaterial,
    *,
    capacity: int,
    output_tokens: int,
    reasoning_shares_budget: bool,
    structural_drafts: tuple[dict, ...],
    source_copies: dict[str, str] | None = None,
) -> tuple[ReviewMaterial, list[parts.ReviewPartPlan], SpanLayout]:
    payload = {**material.payload, "segment_prompt_version": parts.CONCISE_SEGMENT_PROMPT_VERSION}
    options = {
        "capacity": capacity,
        "output_tokens": output_tokens,
        "structured": True,
        "reasoning_shares_budget": reasoning_shares_budget,
    }
    try:
        return (
            material,
            parts.plan_parts(
                payload, **options, structural_drafts=structural_drafts, source_copies=source_copies
            ),
            {},
        )
    except AppException as exc:
        if exc.code != TOO_LARGE:
            raise
        initial_error = exc

    empty = parts.build_part(payload, index=1, total=1, source_ids=[], draft_ids=[], **options)
    # A one-span request can also carry its two adjacent spans on both sides.
    # The full planner still checks the actual prompt, references and schema.
    budget = (int(capacity * parts.MAX_PART_RATIO) - empty.input_tokens) // 6
    if budget <= 0:
        raise initial_error
    layout = _layout(payload, budget)
    if source_copies:
        layout = {
            key: offsets
            for key, offsets in layout.items()
            if not offsets.keys() & source_copies.keys()
        }
    if not layout:
        raise initial_error
    projected = apply_layout(material, layout)
    first = {
        u["source_block_id"]: u["id"]
        for u in reversed(projected.payload["source_units"])
        if "source_block_id" in u
    }
    headings = tuple(
        {**item, "source_ids": [first.get(ref, ref) for ref in item["source_ids"]]}
        for item in structural_drafts
    )
    projected_payload = {
        **projected.payload,
        "segment_prompt_version": parts.CONCISE_SEGMENT_PROMPT_VERSION,
    }
    return (
        projected,
        parts.plan_parts(
            projected_payload, **options, structural_drafts=headings, source_copies=source_copies
        ),
        layout,
    )
