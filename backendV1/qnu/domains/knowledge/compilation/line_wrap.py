"""Join OCR blocks that are the wrapped continuation of one source paragraph."""

from __future__ import annotations

from qnu.domains.knowledge.compilation.schemas import DRAFT_PARAGRAPH_TEXT_LIMIT

TERMINALS = ".!?…:;"
CLOSERS = "\"')]}»”’"
NON_BODY_TYPES = {"figure", "title", "heading", "section-header"}
# A wrapped line ends at the page's right text edge and the next line starts
# immediately below it; separate paragraphs keep visible vertical spacing.
RIGHT_EDGE_TOLERANCE = 0.02
INDENT_TOLERANCE = 0.03
GAP_RATIO = 0.25


def _body(block: dict) -> bool:
    if block.get("table") or block.get("requires_review"):
        return False
    if block.get("type") in NON_BODY_TYPES:
        return False
    bbox = block.get("bbox") or {}
    if bbox.get("units") != "normalized_0_1":
        return False
    if not all(key in bbox for key in ("x0", "y0", "x1", "y1")):
        return False
    return bool(str(block.get("text") or "").strip())


def _ends_open(text: str) -> bool:
    stripped = text.rstrip()
    while stripped and stripped[-1] in CLOSERS:
        stripped = stripped[:-1].rstrip()
    return bool(stripped) and stripped[-1] not in TERMINALS


def wrapped_line_windows(blocks: list[dict], blocked: set[int] | None = None) -> dict[int, int]:
    """Map each start index to the exclusive end of its wrapped-line group."""
    blocked = blocked or set()
    eligible = [
        index for index, block in enumerate(blocks) if index not in blocked and _body(block)
    ]
    if len(eligible) < 2:
        return {}
    remaining = set(eligible)
    right_edges = sorted(blocks[index]["bbox"]["x1"] for index in eligible)
    # Ceiling keeps the right text edge on pages that hold only a few blocks.
    position = -(-9 * (len(right_edges) - 1) // 10)
    margin = right_edges[min(position, len(right_edges) - 1)]
    windows: dict[int, int] = {}
    consumed = 0
    for index in eligible:
        if index < consumed:
            continue
        current = blocks[index]
        if not _ends_open(current["text"]):
            continue
        end = index
        total = len(current["text"].strip())
        while True:
            following = end + 1
            if following not in remaining:
                break
            nxt = blocks[following]
            previous_box, next_box = current["bbox"], nxt["bbox"]
            height = min(previous_box["y1"] - previous_box["y0"], next_box["y1"] - next_box["y0"])
            if height <= 0:
                break
            continues = (
                previous_box["x1"] >= margin - RIGHT_EDGE_TOLERANCE
                and next_box["y0"] - previous_box["y1"] <= GAP_RATIO * height
                and next_box["x0"] <= previous_box["x0"] + INDENT_TOLERANCE
            )
            if not continues:
                break
            length = len(nxt["text"].strip())
            if total + 1 + length > DRAFT_PARAGRAPH_TEXT_LIMIT:
                break
            end = following
            total += 1 + length
            current = nxt
            if not _ends_open(nxt["text"]):
                break
        if end > index:
            windows[index] = end + 1
            consumed = end + 1
    return windows
