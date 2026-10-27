"""Decode Nemotron located output without rewriting the recognised text.

The provider returns blocks as ``<x_0.1><y_0.2>text<x_0.9><y_0.3><class_Text>``.
Coordinates are normalised to 0..1 by the model. This module keeps response order,
keeps the literal text (no spell correction, no dictionary substitution), and only
projects what the provider explicitly marked:

* ``\\thead{...}`` establishes a header cell — bold text alone does not;
* ``\\multicolumn`` / ``\\multirow`` establish spans;
* a table that cannot be reconstructed is reported as ``unsupported`` with its raw
  text kept, never silently flattened.

Anything structurally invalid (bad coordinates, leftover text between blocks) raises,
because a response that does not parse cannot be evidence.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from qnu.platform.errors import AppException

BLOCK_PATTERN = re.compile(
    r"<x_([0-9.eE+-]+)><y_([0-9.eE+-]+)>(.*?)<x_([0-9.eE+-]+)><y_([0-9.eE+-]+)><class_([A-Za-z_-]+)>",
    re.DOTALL,
)

CLASS_MAP = {
    "Text": "text",
    "Title": "title",
    "Section-header": "title",
    "Page-header": "header",
    "Page-footer": "footer",
    "Table": "table",
    "Picture": "figure",
    "Figure": "figure",
    "Caption": "caption",
    "Footnote": "footnote",
    "Formula": "formula",
    "List-item": "text",
}

_TABULAR = re.compile(r"^\s*\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}\s*$", re.DOTALL)
_ROW_RULE = re.compile(r"\\(?:hline|toprule|midrule|bottomrule|cline\{[^}]*\})")
_THEAD = re.compile(r"^\\thead\{(.*)\}$", re.DOTALL)
_MULTICOLUMN = re.compile(r"^\\multicolumn\{(\d+)\}\{[^}]*\}\{(.*)\}$", re.DOTALL)
_MULTIROW = re.compile(r"^\\multirow\{(\d+)\}\{[^}]*\}\{(.*)\}$", re.DOTALL)
_INLINE = re.compile(r"\\(?:textbf|textit|emph)\{([^{}]*)\}")
_ESCAPES = {"&": "&", "%": "%", "_": "_", "$": "$", "#": "#", "{": "{", "}": "}", "\\": "\\"}
_LINEBREAK = re.compile(r"\\(?:linebreak|newline)(?:\{\})?")

MAX_TABLE_COLUMNS = 64
MAX_TABLE_ROWS = 2048


@dataclass(frozen=True, slots=True)
class Cell:
    text: str
    row_span: int = 1
    col_span: int = 1
    header: bool = False


@dataclass(frozen=True, slots=True)
class Table:
    status: str
    rows: tuple[tuple[Cell, ...], ...] = ()
    column_count: int = 0
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Block:
    order: int
    label: str
    kind: str
    text: str
    bbox: tuple[float, float, float, float]
    requires_review: bool
    table: Table | None = None


@dataclass(frozen=True, slots=True)
class PageLayout:
    blocks: tuple[Block, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text)

    @property
    def has_tables(self) -> bool:
        return any(block.table is not None for block in self.blocks)


def _invalid(detail: str = "Phản hồi OCR thiếu cấu trúc hoặc tọa độ hợp lệ.") -> AppException:
    return AppException(
        detail, code="ocr_response_invalid", status_code=502, title="Phản hồi OCR không hợp lệ"
    )


def _split_top_level(text: str, separator: str) -> list[str]:
    """Split outside braces so escaped ampersands and nested groups stay intact."""
    pieces: list[str] = []
    start = 0
    depth = 0
    index = 0
    while index < len(text):
        if depth == 0 and text.startswith(separator, index):
            pieces.append(text[start:index])
            index += len(separator)
            start = index
            continue
        character = text[index]
        if character == "\\":
            index += 2
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced braces")
        index += 1
    if depth:
        raise ValueError("unbalanced braces")
    pieces.append(text[start:])
    return pieces


def _inline_text(raw: str) -> str:
    """Unescape LaTeX while preserving the literal characters the model produced."""
    text = _LINEBREAK.sub("\n", raw.strip())
    for _ in range(8):
        reduced = _INLINE.sub(r"\1", text)
        if reduced == text:
            break
        text = reduced
    output: list[str] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character == "\\" and index + 1 < len(text):
            following = text[index + 1]
            if following in _ESCAPES:
                output.append(_ESCAPES[following])
                index += 2
                continue
            raise ValueError(f"unsupported command \\{following}")
        if character in "{}":
            raise ValueError("unsupported brace")
        output.append(character)
        index += 1
    return "".join(output)


def _unwrap(cell: str) -> tuple[str, int, int, bool]:
    """Return (text, colspan, rowspan, header) for one raw cell."""
    text = cell.strip()
    colspan = 1
    rowspan = 1
    header = False
    for _ in range(4):
        match = _MULTICOLUMN.match(text)
        if match:
            colspan = max(1, min(int(match.group(1)), MAX_TABLE_COLUMNS))
            text = match.group(2).strip()
            continue
        match = _MULTIROW.match(text)
        if match:
            rowspan = max(1, min(int(match.group(1)), MAX_TABLE_ROWS))
            text = match.group(2).strip()
            continue
        match = _THEAD.match(text)
        if match:
            header = True
            text = match.group(1).strip()
            continue
        break
    return _inline_text(text), colspan, rowspan, header


def _place_rows(rows: list[list[Cell]], column_count: int) -> list[list[Cell]] | None:
    """Place cells on the grid, absorbing empty placeholders left by a vertical merge.

    ``\\multirow`` keeps one empty placeholder cell in the following rows, while Word's
    ``vMerge`` omits the cell entirely. Both shapes are accepted; anything that does not
    tile the declared columns exactly is refused, because a table that cannot be
    reconstructed must stay raw instead of being flattened into wrong columns.
    """
    occupied: set[tuple[int, int]] = set()
    cleaned: list[list[Cell]] = []
    for row_index, row in enumerate(rows):
        free = [column for column in range(column_count) if (row_index, column) not in occupied]
        cells = list(row)
        if len(cells) > len(free):
            extra = len(cells) - len(free)
            placeholders = cells[:extra]
            if not all(
                cell.text == "" and cell.col_span == 1 and cell.row_span == 1
                for cell in placeholders
            ):
                return None
            cells = cells[extra:]
        if sum(cell.col_span for cell in cells) != len(free):
            return None

        remaining = iter(free)
        for cell in cells:
            start = next(remaining, None)
            if start is None:
                return None
            columns = [start]
            for _ in range(cell.col_span - 1):
                following = next(remaining, None)
                if following is None:
                    return None
                columns.append(following)
            for column in columns:
                for depth in range(cell.row_span):
                    key = (row_index + depth, column)
                    if key in occupied:
                        return None
                    occupied.add(key)
        if next(remaining, None) is not None:
            return None
        cleaned.append(cells)

    for row_index in range(len(rows)):
        for column in range(column_count):
            if (row_index, column) not in occupied:
                return None
    return cleaned


def _table_grid(rows: list[list[Cell]], column_count: int) -> bool:
    """Verify spans tile the grid exactly; an untileable table is not reconstructed."""
    return _place_rows(rows, column_count) is not None


def parse_table(raw: str) -> Table:
    """Project explicit tabular cells; keep ``unsupported`` instead of guessing."""
    match = _TABULAR.match(raw)
    if not match:
        return Table(status="unsupported", reason="unsupported_layout")
    spec = match.group(1)
    column_count = sum(1 for character in spec if character in "clr")
    if not 0 < column_count <= MAX_TABLE_COLUMNS:
        return Table(status="unsupported", reason="invalid_column_spec")

    body = _ROW_RULE.sub("", match.group(2))
    try:
        raw_rows = [row for row in _split_top_level(body, "\\\\") if row.strip()]
    except ValueError:
        return Table(status="unsupported", reason="unbalanced_row")
    if not 0 < len(raw_rows) <= MAX_TABLE_ROWS:
        return Table(status="unsupported", reason="invalid_row_count")

    rows: list[list[Cell]] = []
    try:
        for raw_row in raw_rows:
            cells: list[Cell] = []
            for raw_cell in _split_top_level(raw_row, "&"):
                text, colspan, rowspan, header = _unwrap(raw_cell)
                cells.append(
                    Cell(text=text, row_span=rowspan, col_span=colspan, header=header)
                )
            rows.append(cells)
    except ValueError as exc:
        return Table(status="unsupported", reason=f"unsupported_cell:{exc}")

    if not _table_grid(rows, column_count):
        return Table(status="unsupported", reason="grid_mismatch")
    placed = _place_rows(rows, column_count) or rows
    return Table(
        status="parsed",
        rows=tuple(tuple(cell for cell in row) for row in placed),
        column_count=column_count,
    )


def parse_page(raw: str) -> PageLayout:
    """Parse one page response, preserving order and literal text."""
    if not isinstance(raw, str):
        raise _invalid()
    blocks: list[Block] = []
    warnings: list[str] = []
    cursor = 0
    for order, match in enumerate(BLOCK_PATTERN.finditer(raw), start=1):
        if raw[cursor : match.start()].strip():
            raise _invalid("Có nội dung nằm ngoài khối OCR có tọa độ.")
        try:
            x0, y0, x1, y1 = (float(match.group(index)) for index in (1, 2, 4, 5))
        except ValueError as exc:
            raise _invalid() from exc
        if not all(math.isfinite(value) for value in (x0, y0, x1, y1)):
            raise _invalid()
        if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
            raise _invalid(f"Tọa độ khối {order} nằm ngoài trang.")

        label = match.group(6)
        kind = CLASS_MAP.get(label)
        requires_review = kind is None
        source = match.group(3)
        table: Table | None = None
        text = source.strip()
        if label == "Table":
            table = parse_table(source)
            if table.status == "parsed":
                text = "\n".join(
                    "\t".join(cell.text for cell in row) for row in table.rows
                )
            else:
                requires_review = True
                warnings.append(f"table_unsupported:{table.reason}")
        blocks.append(
            Block(
                order=order,
                label=label,
                kind=kind or "unknown",
                text=text,
                bbox=(x0, y0, x1, y1),
                requires_review=requires_review,
                table=table,
            )
        )
        cursor = match.end()

    if raw[cursor:].strip():
        raise _invalid("Có nội dung nằm ngoài khối OCR có tọa độ.")
    if not blocks:
        warnings.append("no_blocks")
    return PageLayout(blocks=tuple(blocks), warnings=tuple(warnings))
