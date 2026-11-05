"""Recover explicit DOCX table headers and spans from the source document.

Only an exact, unique content match can attach source cell structure to a measured
rendered PDF table. Page fragments require a complete literal cell-continuity proof.
"""

import re
from dataclasses import replace
from html.parser import HTMLParser
from io import BytesIO

from qnu.domains.ocr.artifacts.docx_html import convert_docx_to_html
from qnu.domains.ocr.layout import Cell, Table, _table_grid
from qnu.domains.ocr.native_docx_fragments import match_fragments


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.depth = 0
        self.rows = []
        self.cells = []
        self.text = []
        self.attrs = None
        self.nested = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.depth += 1
            if self.depth > 1:
                self.nested = True
            else:
                self.rows, self.nested = [], False
        if self.depth != 1:
            return
        if tag == "tr":
            self.cells = []
        elif tag in {"th", "td"}:
            values = dict(attrs)
            self.attrs = (int(values.get("rowspan", 1)), int(values.get("colspan", 1)), tag == "th")
            self.text = []
        elif tag == "br" and self.attrs:
            self.text.append("\n")

    def handle_data(self, data):
        if self.depth == 1 and self.attrs:
            self.text.append(data)

    def handle_endtag(self, tag):
        if self.depth == 1:
            if tag in {"th", "td"} and self.attrs:
                self.cells.append(Cell("".join(self.text).strip("\n"), *self.attrs))
                self.attrs = None
            elif tag == "tr":
                self.rows.append(tuple(self.cells))
            elif tag in {"p", "h1", "h2", "h3", "h4", "h5", "h6"} and self.attrs:
                self.text.append("\n")
            elif tag == "table" and not self.nested:
                maximum = max((sum(c.col_span for c in r) for r in self.rows), default=0)
                if _table_grid([list(r) for r in self.rows], maximum):
                    self.tables.append(Table("parsed", tuple(self.rows), maximum))
        if tag == "table":
            self.depth -= 1


def _content(table):
    return re.sub(r"\s+", "", "".join(c.text for row in table.rows for c in row))


def _docling_tables(payload: bytes) -> list[Table]:
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter
    from docling_core.types.io import DocumentStream

    document = (
        DocumentConverter(allowed_formats=[InputFormat.DOCX])
        .convert(DocumentStream(name="source.docx", stream=BytesIO(payload)))
        .document
    )
    tables = []
    for item in document.tables:
        data = item.data
        rows: list[list[Cell]] = [[] for _ in range(data.num_rows)]
        for cell in sorted(
            data.table_cells,
            key=lambda cell: (cell.start_row_offset_idx, cell.start_col_offset_idx),
        ):
            rows[cell.start_row_offset_idx].append(
                Cell(cell.text, cell.row_span, cell.col_span, cell.column_header or cell.row_header)
            )
        if _table_grid(rows, data.num_cols):
            tables.append(Table("parsed", tuple(tuple(row) for row in rows), data.num_cols))
    return tables


def restore_source_tables(payload, pages, *, converter):
    if converter == "gotenberg-libreoffice":
        source_tables = _docling_tables(payload)
    else:
        parser = _Tables()
        parser.feed(convert_docx_to_html(payload).html)
        source_tables = parser.tables
    entries = [
        (page_index, block_index, block.table)
        for page_index, page in enumerate(pages)
        for block_index, block in enumerate(page.layout.blocks)
        if block.table and block.table.status == "parsed"
    ]
    fragments = match_fragments(source_tables, entries)
    result = []
    for page_index, page in enumerate(pages):
        blocks = []
        warnings = list(page.layout.warnings)
        for block_index, block in enumerate(page.layout.blocks):
            if block.table and block.table.status == "parsed":
                matches = [
                    t
                    for t in source_tables
                    if _content(t) == _content(block.table)
                    and t.column_count == block.table.column_count
                ]
                if (page_index, block_index) in fragments:
                    # Keep page text, bbox, cells and spans. Attach only proven
                    # source header roles and row/cell/continuation identities.
                    block = replace(block, table=fragments[page_index, block_index])
                elif len(matches) == 1:
                    table = matches[0]
                    block = replace(
                        block,
                        table=table,
                        text="\n".join(" | ".join(c.text for c in row) for row in table.rows),
                    )
                else:
                    warnings.append("docx_table_source_mapping_requires_review")
                    block = replace(block, requires_review=True)
            blocks.append(block)
        result.append(
            replace(
                page, layout=replace(page.layout, blocks=tuple(blocks), warnings=tuple(warnings))
            )
        )
    return tuple(result)
