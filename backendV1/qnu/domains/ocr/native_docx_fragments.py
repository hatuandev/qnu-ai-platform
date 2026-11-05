"""Prove DOCX page-table continuity using literal cell prefixes, never fuzzy text.

Page rows and empty cells stay physical evidence. Mapping is attached only when an
entire unique source table is accounted for, including split cells and repeated
headers. Vertical merges across pages are deliberately left unresolved.
"""

from dataclasses import dataclass, replace

from qnu.domains.ocr.layout import Cell, Table

VERSION = "docx.table-fragments/v1"
Row = tuple[Cell, ...]


@dataclass
class _Cursor:
    row: int
    offsets: list[int]

    def advance(self, source: Table) -> bool:
        if any(
            offset != len(_literal(cell.text))
            for offset, cell in zip(self.offsets, source.rows[self.row], strict=True)
        ):
            return False
        self.row += 1
        if self.row < len(source.rows):
            self.offsets = [0] * len(source.rows[self.row])
        return True


def _literal(text: str) -> str:
    return "".join(text.split())


def _same_row(left: Row, right: Row) -> bool:
    return len(left) == len(right) and all(
        (a.row_span, a.col_span, _literal(a.text)) == (b.row_span, b.col_span, _literal(b.text))
        for a, b in zip(left, right, strict=True)
    )


def _same_table(left: Table, right: Table) -> bool:
    return (
        left.column_count == right.column_count
        and len(left.rows) == len(right.rows)
        and all(_same_row(a, b) for a, b in zip(left.rows, right.rows, strict=True))
    )


def _header_count(table: Table) -> int:
    count = 0
    for row in table.rows:
        if not row or not all(c.header or not c.text.strip() for c in row):
            break
        count += 1
    return count


def _consume(row: Row, source: Row, offsets: list[int], source_row: int) -> list[dict] | None:
    if len(row) != len(source):
        return None
    result, column = [], 0
    for cell_index, (cell, original) in enumerate(zip(row, source, strict=True)):
        if cell.col_span != original.col_span or cell.row_span != 1:
            return None
        text, whole = _literal(cell.text), _literal(original.text)
        start = offsets[cell_index]
        if not whole[start:].startswith(text):
            return None
        end = start + len(text)
        offsets[cell_index] = end
        result.append(
            {
                "row_index": source_row,
                "cell_index": cell_index,
                "column_index": column,
                "text_start": start,
                "text_end": end,
                "continued": bool(text) and (start > 0 or end < len(whole)),
            }
        )
        column += cell.col_span
    return result


def _project_fragment(source: Table, fragment: Table, cursor: _Cursor, repeated: bool):
    rows, links = [], []
    header_count = _header_count(source) if repeated else 0
    for physical_row, row in enumerate(fragment.rows):
        header_row = physical_row < header_count
        index = physical_row if header_row else cursor.row
        if index >= len(source.rows):
            return None
        offsets = [0] * len(source.rows[index]) if header_row else cursor.offsets
        link = _consume(row, source.rows[index], offsets, index)
        if link is None:
            return None
        # An all-empty fragment cannot stand for unread text in a source row.
        if not any(c.text.strip() for c in row) and any(c.text.strip() for c in source.rows[index]):
            return None
        rows.append(
            tuple(
                replace(cell, header=original.header)
                for cell, original in zip(row, source.rows[index], strict=True)
            )
        )
        links.append(link)
        if not header_row and not cursor.advance(source) and physical_row != len(fragment.rows) - 1:
            # A partial row can continue only at the next page boundary.
            return None
    return tuple(rows), links


def _match(source: Table, fragments: list[Table], source_index: int) -> list[Table] | None:
    header_count = _header_count(source)
    if not header_count or any(c.row_span != 1 for r in source.rows for c in r):
        return None
    cursor, mapped = _Cursor(0, [0] * len(source.rows[0])), []
    for fragment in fragments:
        if fragment.column_count != source.column_count:
            return None
        repeated = (
            len(mapped) > 0
            and len(fragment.rows) >= header_count
            and all(_same_row(fragment.rows[i], source.rows[i]) for i in range(header_count))
        )
        projected = _project_fragment(source, fragment, cursor, repeated)
        if projected is None:
            return None
        rows, links = projected
        mapped.append(
            replace(
                fragment,
                rows=rows,
                source_mapping={
                    "schema_version": VERSION,
                    "source_table_index": source_index,
                    "source_row_count": len(source.rows),
                    "fragment_index": len(mapped),
                    "repeated_header": repeated,
                    "text_range_units": "non_whitespace_codepoints",
                    "cells": links,
                },
            )
        )
        if cursor.row == len(source.rows):
            return (
                [
                    replace(t, source_mapping={**t.source_mapping, "fragment_count": len(mapped)})
                    for t in mapped
                ]
                if len(mapped) > 1
                else None
            )
    return None


def match_fragments(
    sources: list[Table], entries: list[tuple[int, int, Table]]
) -> dict[tuple[int, int], Table]:
    """Return physical (page index, block index) mappings only for unique proofs."""
    standalone = {
        (page, block)
        for page, block, table in entries
        if any(_same_table(source, table) for source in sources)
    }
    result = {}
    for start, (page, block, first) in enumerate(entries):
        if (page, block) in result or (page, block) in standalone:
            continue
        chain = [first]
        previous = page
        for next_page, next_block, table in entries[start + 1 :]:
            if (
                next_page != previous + 1
                or table.column_count != first.column_count
                or (next_page, next_block) in result
                or (next_page, next_block) in standalone
            ):
                break
            chain.append(table)
            previous = next_page
        candidates = [
            match
            for index, source in enumerate(sources)
            if source.column_count == first.column_count and (match := _match(source, chain, index))
        ]
        if len(candidates) != 1:
            continue
        for (page, block, _), table in zip(entries[start:], candidates[0], strict=False):
            result[page, block] = table
    return result
