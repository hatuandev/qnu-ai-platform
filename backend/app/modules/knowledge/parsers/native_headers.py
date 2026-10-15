"""Resolve merged native PDF header cells by geometry, never vocabulary or forward fill."""

import re
import unicodedata
from typing import Any


def native_header_matrix(table: Any) -> tuple[list[list[str]], int]:
    """Return a lossless matrix with one resolved header and original header depth.

    Only a bounded header prefix followed by a numeric/percentage row key is
    eligible. Unsupported geometry stays unchanged for normal review handling.
    """
    raw = table.extract() or []
    clean = [[unicodedata.normalize("NFC", str(cell or "")).strip() for cell in row] for row in raw]
    if not raw or any(len(row) != table.col_count for row in raw):
        return clean, 1
    depth = next((index for index, row in enumerate(clean)
                  if row and re.fullmatch(r"\d+(?:[.,]\d+)?%?", row[0])), 0)
    if not 1 < depth <= 3 or not any(cell is None for row in raw[:depth] for cell in row):
        return clean, 1
    if any(value and (len(value) > 80 or not any(char.isalpha() for char in value))
           for row in clean[:depth] for value in row):
        return clean, 1
    headers = []
    for column in range(table.col_count):
        body_boxes = [row.cells[column] for row in table.rows[depth:] if row.cells[column] is not None]
        if not body_boxes:
            return clean, 1
        center = (body_boxes[0][0] + body_boxes[0][2]) / 2
        path = []
        for row_index, row in enumerate(table.rows[:depth]):
            matches = [clean[row_index][index] for index, box in enumerate(row.cells)
                       if box is not None and box[0] < center < box[2] and clean[row_index][index]]
            if len(matches) > 1:
                return clean, 1
            if matches and matches[0] not in path:
                path.append(matches[0].replace("\n", " "))
        if not path:
            return clean, 1
        headers.append(" / ".join(path))
    return [headers, *clean[depth:]], depth
