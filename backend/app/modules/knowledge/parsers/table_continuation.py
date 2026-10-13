"""Inherit schema only with adjacent-page geometry and ordinal evidence."""

import re

from app.modules.knowledge.normalization.models import CanonicalTable


def inherit_table_header(headers: list[str], rows: list[list[str]], previous: list[CanonicalTable],
                         page: int, bbox: tuple[float, float, float, float]) -> tuple[list[str], list[list[str]]]:
    if not headers or (headers[0].strip() and not re.fullmatch(r"\d+[.)]?", headers[0].strip())):
        return headers, rows
    ordinal = lambda cells: int(cells[0].strip().rstrip(".)")) if cells and re.fullmatch(r"\d+[.)]?", cells[0].strip()) else None
    first = next((ordinal(row) for row in [headers, *rows] if ordinal(row) is not None), None)
    candidates = []
    for table in previous:
        if table.source_pages != [page - 1] or len(table.headers) != len(headers) or not table.bbox or not table.rows:
            continue
        last = next((ordinal([cell.raw_value for cell in row.cells]) for row in reversed(table.rows)
                     if ordinal([cell.raw_value for cell in row.cells]) is not None), None)
        overlap = max(0, min(bbox[2], table.bbox[2]) - max(bbox[0], table.bbox[0]))
        width = max(bbox[2] - bbox[0], table.bbox[2] - table.bbox[0], 1)
        if first is not None and last is not None and first in {last, last + 1} and overlap / width >= 0.8:
            candidates.append(table)
    if len(candidates) != 1:
        return headers, rows
    return candidates[0].headers.copy(), [headers, *rows]
