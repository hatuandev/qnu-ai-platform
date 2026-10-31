"""Read a canonical cell grid without changing source text, spans or coordinates."""

from dataclasses import dataclass

VERSION = "qnu.table-layout/v1"


@dataclass(frozen=True)
class CellPosition:
    row: int
    index: int
    column: int
    cell: dict


def layout(structure: dict) -> tuple[list[CellPosition], list[str]]:
    rows, indices = structure.get("rows"), structure.get("row_indices")
    columns, count = structure.get("original_column_count"), structure.get("original_row_count")
    if (
        not isinstance(rows, list)
        or not isinstance(indices, list)
        or len(rows) != len(indices)
        or not rows
        or type(columns) is not int
        or not 0 < columns <= 512
        or type(count) is not int
        or not 0 < count <= 100000
        or any(type(r) is not int or not 0 <= r < count for r in indices)
        or indices != sorted(set(indices))
    ):
        return [], ["invalid_dimensions"]
    occupied, placed = {}, []
    for absolute, row in zip(indices, rows, strict=True):
        if not isinstance(row, list):
            return [], ["invalid_row"]
        column = 0
        for index, cell in enumerate(row):
            if not isinstance(cell, dict) or not isinstance(cell.get("text"), str):
                return [], ["invalid_cell"]
            rs, cs = cell.get("row_span"), cell.get("col_span")
            if type(rs) is not int or type(cs) is not int or rs < 1 or cs < 1:
                return [], ["invalid_span"]
            while (absolute, column) in occupied:
                column += 1
            if column + cs > columns or absolute + rs > count or rs * cs > 100000:
                return [], ["span_outside_table"]
            if len(occupied) + rs * cs > 1000000:
                return [], ["grid_too_large"]
            position = CellPosition(absolute, index, column, cell)
            for r in range(absolute, absolute + rs):
                for c in range(column, column + cs):
                    if (r, c) in occupied:
                        return [], ["overlapping_cells"]
                    occupied[r, c] = position
            placed.append(position)
            column += cs
        if any((absolute, c) not in occupied for c in range(columns)):
            return [], ["incomplete_row"]
    return placed, []


def header_rows(structure: dict) -> list[int]:
    """Only explicit leading header rows; never guess from numeric values."""
    result = []
    for number, row in zip(structure.get("row_indices", []), structure.get("rows", [])):
        if number != len(result) or not row or not any(c.get("header") for c in row):
            break
        if not all(c.get("header") or not c.get("text", "").strip() for c in row):
            break
        result.append(number)
    return result


def quality(structure: dict) -> dict:
    _, issues = layout(structure)
    headers = header_rows(structure) if not issues else []
    if not issues and not headers:
        issues = ["header_unresolved"]
    return {
        "version": VERSION,
        "status": "review_required" if issues else "structured",
        "issues": issues,
        "header_rows": headers,
    }
