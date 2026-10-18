"""Uncapped native PDF evidence, captured before legacy cleanup and table fusion."""

from __future__ import annotations

from typing import Any

import pymupdf

from app.modules.knowledge.parsers.blocks import find_page_tables
from app.modules.knowledge.parsers.native_headers import native_header_matrix


def _geometry_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _geometry_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, pymupdf.Rect, pymupdf.Point, pymupdf.Quad)):
        return [_geometry_json(item) for item in value]
    return value


def capture_native_page(page: Any) -> dict[str, Any]:
    """Keep raw strings and real geometry; never turn table boxes into cell boxes."""
    layout = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
    tables: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        detected = find_page_tables(page)
        for index, table in enumerate(getattr(detected, "tables", []) or []):
            header = getattr(table, "header", None)
            _, header_depth = native_header_matrix(table)
            tables.append({
                "id": f"native_table_{index}", "bbox": list(table.bbox),
                "matrix": table.extract(),
                "cell_boxes": [[list(box) if box is not None else None for box in row.cells]
                               for row in table.rows],
                "proposed_header_depth": header_depth,
                "header": {"external": bool(getattr(header, "external", False)),
                           "names": list(getattr(header, "names", []) or []),
                           "bbox": list(header.bbox) if header and header.bbox else None},
            })
    except Exception as exc:
        # Text remains available, but table completeness is explicitly not certified.
        errors.append(type(exc).__name__)
    images = [{"bbox": list(image["bbox"]), "width": image.get("width"), "height": image.get("height")}
              for image in page.get_image_info()]
    return {"page": page.number + 1, "page_label": page.get_label() or None,
            "width": layout["width"], "height": layout["height"], "rotation": page.rotation,
            "bbox_space": "pymupdf_unrotated_points", "layout": layout,
            "tables": tables, "images": images, "drawings": _geometry_json(page.get_drawings()), "table_errors": errors}


def intersection_fraction(box: list[float], target: list[float]) -> float:
    area = max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    intersection = max(0, min(box[2], target[2]) - max(box[0], target[0])) * max(
        0, min(box[3], target[3]) - max(box[1], target[1]))
    return intersection / area if area else 0


def reading_order(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """XY cut: full-width items split bands, a genuine vertical gutter separates columns."""
    if len(items) < 2 or any(not item.get("bbox") for item in items):
        return items
    xs = sorted(items, key=lambda item: item["bbox"][0])
    right = xs[0]["bbox"][2]
    for index in range(1, len(xs)):
        left = xs[index]["bbox"][0]
        if left > right:
            before, after = xs[:index], xs[index:]
            # Columns must overlap vertically, otherwise this is simply two paragraphs.
            if max(min(i["bbox"][1] for i in before), min(i["bbox"][1] for i in after)) < min(
                max(i["bbox"][3] for i in before), max(i["bbox"][3] for i in after)):
                return reading_order(before) + reading_order(after)
        right = max(right, xs[index]["bbox"][2])
    ys = sorted(items, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    bottom = ys[0]["bbox"][3]
    for index in range(1, len(ys)):
        if ys[index]["bbox"][1] > bottom:
            return reading_order(ys[:index]) + reading_order(ys[index:])
        bottom = max(bottom, ys[index]["bbox"][3])
    return ys
