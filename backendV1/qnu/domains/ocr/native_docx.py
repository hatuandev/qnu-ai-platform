"""Recover explicit DOCX table headers/spans from its existing HTML projection.

Only an exact, unique content match can attach source cell structure to a measured
rendered PDF table. Split or ambiguous tables keep geometry and a review warning.
"""

import re
from dataclasses import replace
from html.parser import HTMLParser

from qnu.domains.ocr.artifacts.docx_html import convert_docx_to_html
from qnu.domains.ocr.layout import Cell, Table, _table_grid


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


def restore_source_tables(payload, pages):
    parser = _Tables()
    parser.feed(convert_docx_to_html(payload).html)
    result = []
    for page in pages:
        blocks = []
        warnings = list(page.layout.warnings)
        for block in page.layout.blocks:
            if block.table and block.table.status == "parsed":
                matches = [
                    t
                    for t in parser.tables
                    if _content(t) == _content(block.table)
                    and t.column_count == block.table.column_count
                ]
                if len(matches) == 1:
                    block = replace(block, table=matches[0])
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
