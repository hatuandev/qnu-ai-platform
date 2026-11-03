"""Find contiguous, explicitly enumerated points across compiled section boundaries."""

import re
from collections.abc import Iterator

from qnu.domains.knowledge.index.contextual import original_text
from qnu.domains.knowledge.index.models import IndexChunk

_LEAD = re.compile(r"\d+\.\s+.+:\s*$", re.DOTALL)
_BLOCK = re.compile(r"pages\[(\d+)\]\.blocks\[(\d+)\]")
_POINTS = "abcdđeghiklmnopqrstuvxy"


def _paragraph(row: IndexChunk) -> tuple[str, tuple, int] | None:
    if row.kind != "paragraph" or len(row.citations) != 1:
        return None
    context = (row.structure or {}).get("context", {})
    if context.get("part") != 0 or not all(context.get(k) for k in ("title", "heading")):
        return None
    ref = next(iter(row.citations.values()))
    path = _BLOCK.fullmatch(ref.get("path", ""))
    if path is None or ref.get("kind") != "block" or not ref.get("canonical_sha256"):
        return None
    prefix = f"{context['title']}\n{context['heading']}\n"
    text = original_text(row)
    if not text.startswith(prefix):
        return None
    identity = (
        row.input_id,
        ref.get("run_id"),
        ref.get("revision_id"),
        ref["canonical_sha256"],
        path[1],
    )
    return text[len(prefix) :].strip(), identity, int(path[2])


def clause_groups(rows: list[IndexChunk], anchors: set[str]) -> Iterator[list[IndexChunk]]:
    for start, lead in enumerate(rows):
        opening = _paragraph(lead)
        if opening is None or not _LEAD.fullmatch(opening[0]):
            continue
        group = [lead]
        for offset, marker in enumerate(_POINTS, 1):
            if start + offset >= len(rows):
                break
            row = rows[start + offset]
            point = _paragraph(row)
            if (
                point is None
                or row.ordinal != lead.ordinal + offset
                or point[1:] != (opening[1], opening[2] + offset)
                or not re.match(rf"{marker}\)\s+\S", point[0])
            ):
                break
            group.append(row)
        if len(group) < 3 or not anchors.intersection(row.id for row in group):
            continue
        following = start + len(group)
        if following < len(rows):
            tail = rows[following]
            next_point = _paragraph(tail)
            if tail.input_id == lead.input_id and (
                group[-1].citations.keys() & tail.citations.keys()
                or (
                    next_point is not None
                    and next_point[1] == opening[1]
                    and re.match(r"[a-zđ]\)\s", next_point[0])
                )
            ):
                continue
        yield group
