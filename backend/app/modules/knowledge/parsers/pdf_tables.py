"""Lossless table adapters for PDF native matrices and OCR HTML (no domain vocabulary)."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from app.modules.knowledge.normalization.markdown_renderer import format_cell_value
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuQualityFlag,
    QnuSourceLocation,
)
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row

# A bare dash or slash is not readable data on its own; it stays ambiguous unless the document defines it.
UNRESOLVED_CELL_SYMBOLS = frozenset({"-", "–", "—", "/"})


class _HTMLGrid(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict[str, Any]]] = []
        self.cell: dict[str, Any] | None = None
        self.depth = 0
        self.table_count = 0
        self.invalid = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.table_count += 1
            self.depth += 1
            self.invalid |= self.depth > 1 or self.table_count > 1
        if tag == "tr":
            self.rows.append([])
        if tag in {"td", "th"}:
            values = dict(attrs)
            try:
                rowspan, colspan = int(values.get("rowspan") or 1), int(values.get("colspan") or 1)
                if not (1 <= rowspan <= 1000 and 1 <= colspan <= 1000):
                    raise ValueError("span")
            except ValueError:
                self.invalid = True
                rowspan = colspan = 1
            self.cell = {"raw": "", "rowspan": rowspan, "colspan": colspan, "header": tag == "th"}
        if tag == "br" and self.cell is not None:
            self.cell["raw"] += "\n"

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell["raw"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None:
            if not self.rows:
                self.rows.append([])
                self.invalid = True
            self.rows[-1].append(self.cell)
            self.cell = None
        if tag == "table":
            self.depth -= 1


def html_table(text: str) -> dict[str, Any] | None:
    parser = _HTMLGrid()
    parser.feed(text)
    if parser.invalid or parser.depth != 0 or not parser.rows or parser.cell is not None:
        return None
    occupied: dict[tuple[int, int], dict[str, Any]] = {}
    for row_index, row in enumerate(parser.rows):
        column = 0
        for cell in row:
            while (row_index, column) in occupied:
                column += 1
            cell["origin"] = [row_index, column]
            for r in range(row_index, row_index + cell["rowspan"]):
                for c in range(column, column + cell["colspan"]):
                    if (r, c) in occupied or len(occupied) >= 100000:
                        return None
                    occupied[r, c] = cell
            column += cell["colspan"]
    if not occupied:
        return None
    height = max(r for r, _ in occupied) + 1
    width = max(c for _, c in occupied) + 1
    if height * width > 100000:
        return None
    grid = [[occupied.get((r, c), {"raw": "", "origin": [r, c]}) for c in range(width)]
            for r in range(height)]
    depth = 0
    for row in grid:
        if not all(cell.get("header") for cell in row):
            break
        depth += 1
    return {"grid": grid, "header_depth": depth, "raw_html": text}


def ocr_table(text: str) -> dict[str, Any] | None:
    """Parse a raw table block, never a flattened whole-page projection."""
    if "<table" in text.lower():
        return html_table(text)
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2 or any(not line.strip().startswith("|") for line in lines):
        return None
    separator = _split_gfm_row(lines[1])
    if not separator or not all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in separator):
        return None
    matrix = [_split_gfm_row(line) for line in [lines[0], *lines[2:]]]
    if any(len(row) != len(separator) for row in matrix):
        return None
    return {"grid": [[{"raw": value, "origin": [r, c]} for c, value in enumerate(row)]
                     for r, row in enumerate(matrix)], "header_depth": 1, "raw_markdown": text}


def native_table(table: dict[str, Any]) -> dict[str, Any]:
    matrix, boxes = table.get("matrix") or [], table.get("cell_boxes") or []
    width = max((len(row) for row in matrix), default=0)
    header = table.get("header") or {}
    names = header.get("names") or []
    depth = int(bool(matrix and names and list(matrix[0]) == names and not header.get("external")))
    proposed = table.get("proposed_header_depth", 1)
    if depth and isinstance(proposed, int) and 1 < proposed < len(matrix):
        depth = proposed
    x_edges = sorted({box[x] for row in boxes for box in row if box for x in (0, 2)})
    y_edges = sorted({box[y] for row in boxes for box in row if box for y in (1, 3)})
    raw_origins = [(r, c, box) for r, row in enumerate(boxes) for c, box in enumerate(row) if box]
    grid = []
    origins: dict[tuple[float, ...], list[int]] = {}
    for r, row in enumerate(matrix):
        cells = []
        for c in range(width):
            box = boxes[r][c] if r < len(boxes) and c < len(boxes[r]) else None
            origin = origins.setdefault(tuple(box), [r, c]) if box else [r, c]
            if box is None and len(x_edges) == width + 1 and len(y_edges) == len(matrix) + 1:
                x, y = (x_edges[c] + x_edges[c + 1]) / 2, (y_edges[r] + y_edges[r + 1]) / 2
                covering = [(rr, cc, b) for rr, cc, b in raw_origins if b[0] < x < b[2] and b[1] < y < b[3]]
                if len(covering) == 1:
                    rr, cc, box = covering[0]
                    origin = [rr, cc]
            value = matrix[origin[0]][origin[1]] if origin != [r, c] else (row[c] if c < len(row) else None)
            cells.append({"raw": value if value is not None else "",
                          "origin": origin, "bbox": box, "unresolved": box is None})
        grid.append(cells)
    return {"grid": grid, "header_depth": depth, "external_headers": names if header.get("external") else [],
            "raw_native": table}


def table_blocks(table: dict[str, Any], *, block_id: str, parent_id: str | None,
                 location: QnuSourceLocation, section_path: list[str], engine: str,
                 symbol_definitions: dict[str, dict[str, Any]] | None = None) -> list[QnuBlock]:
    grid, depth = table["grid"], table["header_depth"]
    if not grid:
        return []
    columns = []
    for c in range(len(grid[0])):
        path = []
        for row in grid[:depth]:
            value = row[c]["raw"]
            if value and (not path or path[-1] != value):
                path.append(value)
        external = table.get("external_headers") or []
        columns.append({"id": f"c{c + 1:02d}", "header_path": path or external[c:c + 1]})
    flags = []
    if table.get("raw_native"):
        flags.append(QnuQualityFlag(code="native_header_needs_review", detail="Header PDF được parser đề xuất; chưa là xác nhận của người duyệt."))
    if table.get("header_proposal"):
        flags.append(QnuQualityFlag(code="native_header_needs_review",
            detail="Lớp chữ gốc của trang lặp lại mọi nhãn ở dòng đầu bảng OCR; parser đề xuất header, chưa phải xác nhận của người duyệt."))
    if not depth and not table.get("external_headers"):
        flags.append(QnuQualityFlag(code="table_header_unresolved", detail="Không suy dòng đầu thành header; giữ mọi dòng."))
    container = QnuBlock(id=block_id, parent_id=parent_id, type="table", source_locations=[location],
                         section_path=section_path, attributes={"representation": "records", "columns": columns,
                                                               "engine_used": engine},
                         quality_flags=flags, source_data=table)
    if depth >= len(grid):
        container.attributes["representation"] = "gfm"
        container.body = "| " + " | ".join(format_cell_value(" / ".join(c["header_path"]), join_multiline=True) for c in columns) + " |\n"
        container.body += "| " + " | ".join("---" for _ in columns) + " |"
        return [container]
    blocks = [container]
    for r in range(depth, len(grid)):
        row_id = f"{block_id}_r{r + 1:04d}"
        fields, origins, field_sources, definitions = {}, {}, {}, {}
        lines: list[str] = []
        for c, cell in enumerate(grid[r]):
            key, value = columns[c]["id"], cell["raw"]
            symbol = value.strip()
            legend = (symbol_definitions or {}).get(symbol) if symbol and not any(ch.isalnum() for ch in symbol) else None
            state = "ambiguous" if cell.get("unresolved") else "blank" if not value.strip() else "present"
            if state == "present" and legend is None and symbol in UNRESOLVED_CELL_SYMBOLS:
                state = "ambiguous"
            if state == "present" and legend is not None:
                definitions[key] = legend
            fields[key] = {"raw": value, "state": state, "normalized": None}
            origin_row, origin_col = cell["origin"]
            if (origin_row, origin_col) != (r, c):
                origins[key] = {"block_id": block_id if origin_row < depth else f"{block_id}_r{origin_row + 1:04d}",
                                "column_id": columns[origin_col]["id"], "basis": "merged_cell"}
            source = location.model_copy(deep=True)
            source.locator = f"{location.locator}/row/{r + 1}/cell/{c + 1}"
            source.bbox = cell.get("bbox")  # Unknown OCR cell box is NOT the enclosing table box.
            field_sources[key] = source.model_dump()
            label = " / ".join(columns[c]["header_path"]) or key
            lines.append(f"**{label}:** {value if value.strip() else '[Ô trống trong nguồn]'}")
        attributes: dict[str, Any] = {"fields": fields, "field_sources": field_sources, "engine_used": engine}
        spanning = len(grid[r]) > 1 and len({tuple(cell["origin"]) for cell in grid[r]}) == 1
        if spanning:
            attributes["row_role"] = "spanning_row_unclassified"
        if origins:
            attributes["field_origins"] = origins
        if definitions:
            attributes["symbol_definitions"] = definitions
        row_flags = [QnuQualityFlag(code="ambiguous_cell", field_id=key, detail="Ô thiếu hình học hoặc ký hiệu chưa rõ nghĩa.")
                     for key, field in fields.items() if field["state"] == "ambiguous"]
        row_flags += [QnuQualityFlag(code="cell_symbol_defined", status="resolved", field_id=key,
                     detail=f"Ký hiệu \"{entry['symbol']}\" được chính tài liệu định nghĩa ở trang {entry['page']}: \"{entry['line']}\".")
                     for key, entry in definitions.items()]
        if spanning:
            row_flags.append(QnuQualityFlag(code="spanning_row_needs_review", detail="Dòng gộp có thể là nhãn nhóm hoặc ghi chú; chưa suy vai trò."))
        blocks.append(QnuBlock(id=row_id, parent_id=block_id, type="table_row", source_locations=[
            location.model_copy(update={"locator": f"{location.locator}/row/{r + 1}"})],
            section_path=section_path, attributes=attributes, quality_flags=row_flags, body="\n\n".join(lines)))
    return blocks
