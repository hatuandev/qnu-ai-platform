"""Recover ruled PDF grids without treating paragraph shading as cell borders."""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise
from typing import Any


def _axes(table: Any) -> tuple[list[float], list[float]]:
    boxes = [box for row in table.rows for box in row.cells if box]
    return (sorted({b[i] for b in boxes for i in (0, 2)}),
            sorted({b[i] for b in boxes for i in (1, 3)}))


def _aligned_backgrounds(table: Any, drawings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Only whole cell regions aligned on both axes can supply missing edges."""
    xs, ys = _axes(table)
    if len(xs) < 2 or len(ys) < 3:
        return []
    # The detector snaps at 3pt by default; stay below a quarter of a real cell.
    xtol = min(3.0, min(b - a for a, b in pairwise(xs)) / 4)
    ytol = min(3.0, min(b - a for a, b in pairwise(ys)) / 4)
    result = []
    for index, path in enumerate(drawings):
        rect = path["rect"]
        if path.get("type") != "f" or rect.width <= 3 or rect.height <= 3:
            continue
        if not path.get("items") or any(item[0] != "re" for item in path["items"]):
            continue
        edges = [min(axis, key=lambda edge: abs(edge - value))
                 for value, axis in zip(rect, (xs, ys, xs, ys), strict=True)]
        if any(abs(a - b) > tol for a, b, tol in zip(rect, edges, (xtol, ytol, xtol, ytol), strict=True)):
            continue
        if edges[0] < edges[2] and edges[1] < edges[3]:
            result.append({"drawing_index": index, "source_bbox": list(rect), "aligned_bbox": edges})
    return result


def find_ruled_tables(page: Any, options: dict[str, Any]) -> Any:
    """Use real rules first, then restore cell edges supported by aligned fills."""
    original = page.find_tables(**options)
    strict = page.find_tables(strategy="lines_strict", **options)
    _restore_single_columns(page, strict)
    if not strict.tables:
        # Fill-only tables still retain their original extraction for review.
        for table in original.tables:
            table.qnu_geometry = {"strategy": "lines_fallback", "status": "unresolved"}
        return original
    drawings = page.get_drawings()
    regions = [region for table in strict.tables for region in _aligned_backgrounds(table, drawings)]
    lines = [((x, box[1]), (x, box[3])) for region in regions
             for box in [region["aligned_bbox"]] for x in (box[0], box[2])]
    if lines:
        refined = dict(options, add_lines=[*options.get("add_lines", []), *lines])
        recovered = page.find_tables(strategy="lines_strict", **refined)
        _restore_single_columns(page, recovered)
        if recovered.tables:
            strict = recovered
    for table in strict.tables:
        box = table.bbox
        table.qnu_geometry = {"strategy": "lines_strict_aligned_fills", "status": "reconstructed",
            "cell_regions": [r for r in regions if box[0] - 3 <= r["aligned_bbox"][0]
                             and r["aligned_bbox"][2] <= box[2] + 3
                             and box[1] - 3 <= r["aligned_bbox"][1]
                             and r["aligned_bbox"][3] <= box[3] + 3]}
    _preserve_candidates(strict.tables, original.tables)
    return strict


def _restore_single_columns(page: Any, finder: Any) -> None:
    """MuPDF discards one-column groups even when their closed cells are intact."""
    from pymupdf.table import Table

    groups: dict[tuple[float, float], list[tuple[float, ...]]] = defaultdict(list)
    for cell in finder.cells:
        if any(_contained(cell, t.bbox) for t in finder.tables):
            continue
        groups[cell[0], cell[2]].append(cell)
    for cells in groups.values():
        stack: list[tuple[float, ...]] = []
        for cell in sorted(cells, key=lambda b: b[1]):
            if stack and abs(cell[1] - stack[-1][3]) > 3:
                _append_single_column(page, finder, stack, Table)
                stack = []
            stack.append(cell)
        _append_single_column(page, finder, stack, Table)


def _append_single_column(page: Any, finder: Any, cells: list[tuple[float, ...]], table_type: Any) -> None:
    if len(cells) < 2:
        return
    table = table_type(page, cells)
    if any(value and value.strip() for row in table.extract() for value in row):
        finder.tables.append(table)


def _contained(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return b[0] - 1 <= a[0] <= a[2] <= b[2] + 1 and b[1] - 1 <= a[1] <= a[3] <= b[3] + 1


def _preserve_candidates(selected: list[Any], original: list[Any]) -> None:
    for candidate in original:
        matches = [table for table in selected if _overlap(table.bbox, candidate.bbox) >= .5]
        if matches:
            for table in matches:
                table.qnu_geometry.setdefault("original_candidates", []).append({
                    "bbox": list(candidate.bbox), "matrix": candidate.extract(),
                    "cell_boxes": [[list(b) if b else None for b in row.cells] for row in candidate.rows]})
        else:
            candidate.qnu_geometry = {"strategy": "lines_fallback", "status": "unresolved"}
            selected.append(candidate)


def _overlap(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / area if area > 0 else 0
