"""Project measured PDF cell rectangles into rows/spans without inferring headers/years."""

import pymupdf

from qnu.domains.ocr.layout import Cell, Table, _table_grid


def read_table(table) -> Table:
    rectangles = sorted({tuple(c) for row in table.rows for c in row.cells if c})
    xs = sorted({round(c[i], 2) for c in rectangles for i in (0, 2)})
    ys = sorted({round(c[i], 2) for c in rectangles for i in (1, 3)})
    values = table.extract()
    text_by_rect = {}
    for r, row in enumerate(table.rows):
        for c, rect in enumerate(row.cells):
            if rect:
                text_by_rect[tuple(round(v, 2) for v in rect)] = values[r][c] or ""
    rows = []
    covered = set()
    for r, top in enumerate(ys[:-1]):
        cells = []
        for c, left in enumerate(xs[:-1]):
            if (r, c) in covered:
                continue
            rect = next((v for v in text_by_rect if v[0] == left and v[1] == top), None)
            if rect is None:
                # A hole is not proof of an empty cell: retain unsupported structure.
                return Table(status="unsupported", reason="native_table_geometry_incomplete")
            col_span, row_span = xs.index(rect[2]) - c, ys.index(rect[3]) - r
            cells.append(Cell(text_by_rect[rect], row_span, col_span))
            covered.update(
                (rr, cc) for rr in range(r, r + row_span) for cc in range(c, c + col_span)
            )
        rows.append(tuple(cells))
    if not _table_grid([list(r) for r in rows], len(xs) - 1):
        return Table(status="unsupported", reason="native_table_geometry_inconsistent")
    return Table("parsed", tuple(rows), len(xs) - 1)


def table_regions(page: pymupdf.Page):
    return [
        (pymupdf.Rect(t.bbox), read_table(t))
        for t in page.find_tables(strategy="lines_strict").tables
    ]
