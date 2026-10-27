"""Bounded native header roles from independent typography and grid structure."""

from __future__ import annotations

from itertools import pairwise
from typing import Any


def _inside(center: tuple[float, float], box: list[float]) -> bool:
    return box[0] <= center[0] <= box[2] and box[1] <= center[1] <= box[3]


def _row_style(box: list[float], spans: list[dict[str, Any]], backgrounds: list[dict[str, Any]],
               xs: list[float]) -> dict[str, Any]:
    ink = [s for s in spans if _inside(((s["bbox"][0] + s["bbox"][2]) / 2,
                                      (s["bbox"][1] + s["bbox"][3]) / 2), box)]
    y = (box[1] + box[3]) / 2
    colors = []
    for left, right in pairwise(xs):
        covering = [p for p in backgrounds if _inside(((left + right) / 2, y), p["rect"])]
        colors.append({tuple(p["fill"]) for p in covering})
    shared = set.intersection(*colors) if colors else set()
    return {"bold": bool(ink) and all(s.get("flags", 0) & 16 for s in ink),
            "shading": shared, "span_boxes": [list(s["bbox"]) for s in ink]}


def _centered_cells(boxes: list, spans: list, top: float, bottom: float) -> list[bool]:
    cells = sorted({tuple(b) for b in boxes if b[1] <= (top + bottom) / 2 < b[3]})
    result = []
    for cell in cells:
        ink = [s['bbox'] for s in spans if _inside(
            ((s['bbox'][0] + s['bbox'][2]) / 2, (s['bbox'][1] + s['bbox'][3]) / 2), cell)]
        centered = bool(ink) and abs((min(b[0] for b in ink) + max(b[2] for b in ink)) / 2
            - (cell[0] + cell[2]) / 2) <= max(1, (cell[2] - cell[0]) * .1)
        result.append(centered)
    return result


def _hierarchy_depth(boxes: list, xs: list, ys: list) -> int:
    parents = {tuple(b) for b in boxes if abs(b[1] - ys[0]) < .1
        and (xs[0] + .1 < b[0] or b[2] < xs[-1] - .1)
        and sum(b[0] - .1 <= x <= b[2] + .1 for x in xs) > 2}
    if not parents:
        return 0
    leaves, expanded = set(parents), False
    for _ in ys:
        updated = set(leaves)
        for parent in leaves:
            children = sorted({tuple(b) for b in boxes if abs(b[1] - parent[3]) < .1
                and b[0] >= parent[0] - .1 and b[2] <= parent[2] + .1
                and b[2] - b[0] < parent[2] - parent[0] - .1})
            if (len(children) < 2 or abs(children[0][0] - parent[0]) > .1
                    or abs(children[-1][2] - parent[2]) > .1
                    or any(abs(a[2] - b[0]) > .1 for a, b in pairwise(children))):
                continue
            updated.remove(parent)
            updated.update(children)
            expanded = True
        if updated == leaves:
            break
        leaves = updated
    bottoms = {round(b[3], 1) for b in leaves}
    if not expanded or len(bottoms) != 1:
        return 0
    return next((i for i, y in enumerate(ys) if abs(y - next(iter(bottoms))) < .1), 0)


def _unshaded_basis(boxes: list, spans: list, xs: list, ys: list, depth: int) -> str | None:
    header_cells = {tuple(b) for b in boxes if b[1] < ys[depth] - .1}
    # Multiple bold levels need a real partial-width parent spanning child columns.
    # A whole-width title/body band does not establish a column hierarchy.
    if depth > 1 and _hierarchy_depth(boxes, xs, ys) == depth:
        return 'bounded_bold_merged_header_hierarchy'
    if depth != 1 or len(header_cells) != len(xs) - 1 or len(xs) < 3:
        return None
    centered = _centered_cells(boxes, spans, ys[0], ys[1])
    if not centered or not all(centered):
        return None
    body = [_centered_cells(boxes, spans, ys[i], ys[i + 1]) for i in (depth, depth + 1)]
    contrast = all(len(row) == len(centered) for row in body) and any(
        not body[0][c] and not body[1][c] for c in range(len(centered)))
    taller = ys[1] - ys[0] >= 1.2 * max(ys[i + 1] - ys[i] for i in (depth, depth + 1))
    return 'bounded_bold_centered_header_with_body_contrast' if contrast or taller else None


def header_role_evidence(table: dict[str, Any], layout: dict[str, Any],
                         drawings: list[dict[str, Any]], *, allow_unshaded: bool = True) -> dict[str, Any]:
    """Engine names, text content and numeric-looking rows never establish a role."""
    boxes = [b for row in table["cell_boxes"] for b in row if b]
    xs = sorted({b[i] for b in boxes for i in (0, 2)})
    ys = sorted({b[i] for b in boxes for i in (1, 3)})
    matrix = table["matrix"]
    if len(ys) != len(matrix) + 1 or len(xs) < 2 or len(matrix) < 3:
        return {}
    spans = [s for block in layout.get("blocks", []) for line in block.get("lines", [])
             for s in line.get("spans", []) if s.get("text", "").strip()]
    backgrounds = [p for p in drawings if p.get("type") == "f" and p.get("fill")
                   and min(p["fill"]) < .995 and p["rect"][2] - p["rect"][0] > 3
                   and p["rect"][3] - p["rect"][1] > 3]
    styles = [_row_style([xs[0], top, xs[-1], bottom], spans, backgrounds, xs)
              for top, bottom in pairwise(ys)]
    band_colors = styles[0]["shading"]
    if not band_colors and not allow_unshaded:
        return {}
    depth = 0
    for index, style in enumerate(styles):
        # A whole-width merged band below an existing column header is a body
        # group/note, even when it shares that header's fill and bold font.
        row_boxes = [b for b in boxes if b[1] <= (ys[index] + ys[index + 1]) / 2 <= b[3]]
        if index and len(xs) > 2 and row_boxes and all(
                abs(b[0] - xs[0]) < .1 and abs(b[2] - xs[-1]) < .1 for b in row_boxes):
            break
        if not style["bold"] or (band_colors and not style["shading"] & band_colors):
            break
        depth += 1
    if not band_colors and depth > 1:
        # Typography can continue into a bold data row. Only nested cell
        # boundaries may extend an unshaded multi-level header.
        structural_depth = _hierarchy_depth(boxes, xs, ys)
        if not structural_depth or structural_depth > depth:
            return {}
        depth = structural_depth
    if not depth or len(styles) - depth < 2:
        return {}
    # Skip full-width body bands while proving the ordinary rows below the header.
    body = [style for index, style in enumerate(styles[depth:], depth)
            if len(xs) == 2 or not any(abs(b[0] - xs[0]) < .1 and abs(b[2] - xs[-1]) < .1
                and b[1] <= (ys[index] + ys[index + 1]) / 2 <= b[3] for b in boxes)][:2]
    if len(body) < 2:
        return {}
    if any(s["bold"] or s["shading"] & band_colors or not s["span_boxes"] for s in body):
        return {}
    # A cell crossing the proposed boundary would consume data or split a merged role.
    if any(b[1] < ys[depth] - .1 and b[3] > ys[depth] + .1 for b in boxes):
        return {}
    basis = 'bounded_bold_shaded_band' if band_colors else _unshaded_basis(boxes, spans, xs, ys, depth)
    if not basis:
        return {}
    return {"status": "verified", "basis": basis, "depth": depth,
            "bbox": [xs[0], ys[0], xs[-1], ys[depth]],
            "header_span_boxes": [box for style in styles[:depth] for box in style["span_boxes"]],
            "body_span_boxes": [box for style in body for box in style["span_boxes"]]}
