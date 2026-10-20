"""Build the QNU RAG Markdown structured model from a Docling document (DOCX first).

The builder reads Docling items, table cells and provenance directly. It never
re-parses Docling Markdown, never invents page numbers or bounding boxes and keeps
unknown values empty with an explicit state or flag.

DOCX has no physical pagination: every block carries a locator to the DOCX body
element (reading order). When the preview render alignment is available, a render
page is attached as a derived page hint; the mapping method and render hash are
recorded in the document metadata.
"""

from __future__ import annotations

import re
import unicodedata
from itertools import pairwise
from typing import Any

from app.modules.knowledge.normalization.markdown_renderer import format_cell_value
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuColumn,
    QnuFieldValue,
    QnuQualityFlag,
    QnuSourceInfo,
    QnuSourceLocation,
    QnuStructuredDocument,
    cell_state,
)
from app.modules.knowledge.parsers.docx_numbering import (
    MARKER,
    list_item_evidence,
    render_list_items,
)

LOCATOR_SCHEME = "docx_body_reading_order/v1"
_WORD = re.compile(r"\w+")
_BLANK_DISPLAY = "[Ô trống trong nguồn]"


def clean_text(value: Any) -> str:
    """Presentation-only normalization: NFC and CRLF; raw values stay strings."""
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value).replace("\r\n", "\n").replace("\r", "\n"))


def _fence_for(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _unit_pattern(text: str) -> re.Pattern | None:
    """Whole-unit pattern: a row or list item must be matched by all of its tokens."""
    tokens = [token.casefold() for token in _WORD.findall(text)]
    if not tokens:
        return None
    body = r"(?:\W+)".join(re.escape(token) for token in tokens)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def _span_pages(
    start: int,
    end: int,
    page_ranges: list[tuple[int, int, int]],
) -> list[int] | None:
    """Render pages holding [start, end); None when a gap leaves part of the span unpinned."""
    covering = [(page, lo, hi) for page, lo, hi in page_ranges if lo < end and hi > start]
    if not covering:
        return None
    if covering[0][1] > start or covering[-1][2] < end:
        return None
    if any(prev[2] != nxt[1] for prev, nxt in pairwise(covering)):
        return None
    return [page for page, _, _ in covering]


def map_unit_to_page(
    text: str,
    page_ranges: list[tuple[int, int, int]],
    cursor: int,
    markdown: str,
    *,
    full_lines: bool = False,
) -> tuple[list[int], int, str]:
    """Render pages for one unit, forward-only and only when the projection pins every token.

    Returns (pages, next_cursor, state); empty pages means the unit is not certainly located.
    The whole match decides the pages, so a row or list item that wraps across a boundary
    keeps every page it occupies instead of being pinned to its first page alone. Repeats
    are ambiguous only when they land on different page spans; a wrap-around match is never
    a certain position, so it stays unknown.
    """
    pattern = _unit_pattern(text)
    if pattern is None or not page_ranges or not markdown:
        return [], cursor, "unavailable"
    hits = list(pattern.finditer(markdown))
    if full_lines:
        # Heading/paragraph occurrences must occupy their own source lines. A TOC
        # prefix or a word inside another paragraph is not that source occurrence.
        hits = [hit for hit in hits if _full_line_match(markdown, hit)]
    if not hits:
        return [], cursor, "absent"
    spans = [(_span_pages(hit.start(), hit.end(), page_ranges), hit) for hit in hits]
    unpinned = [hit for pages, hit in spans if pages is None]
    if unpinned:
        return [], cursor, "ambiguous"
    signatures = {tuple(pages) for pages, _ in spans if pages is not None}
    if len(signatures) > 1:
        return [], cursor, "ambiguous"
    for pages, hit in spans:
        if hit.start() >= cursor:
            certain = pages or []
            state = "matched" if len(certain) == 1 else "spanning"
            return certain, max(cursor, hit.end()), state
    return [], cursor, "out_of_order"


def _full_line_match(markdown: str, hit: re.Match) -> bool:
    left = markdown[markdown.rfind("\n", 0, hit.start()) + 1:hit.start()]
    stop = markdown.find("\n", hit.end())
    right = markdown[hit.end():stop if stop >= 0 else len(markdown)]
    return bool(re.fullmatch(r"[\W_]*(?:(?:\d+[.)]|[^\W\d_][.)])\s+)?[\W_]*", left)
                and re.fullmatch(r"\W*", right))


def _row_unit_text(row: list[Any]) -> str:
    """Join the row as the projection writes it, span repeats included."""
    return " ".join(
        text
        for text in (clean_text(getattr(cell, "text", "")) for cell in row if cell is not None)
        if text.strip()
    )


def _location(index: int, page: int | None, suffix: str = "") -> QnuSourceLocation:
    return QnuSourceLocation(page=page, page_label=None, locator=f"docx:block:{index}{suffix}")


def _locations(index: int, pages: list[int], suffix: str = "") -> list[QnuSourceLocation]:
    """One location per render page the unit occupies; an unresolved unit keeps only its locator."""
    return [_location(index, page, suffix) for page in (pages or [None])]


class _Builder:
    def __init__(self, has_page_mapping: bool = False, render_pages: dict[int, str] | None = None) -> None:
        self.blocks: list[QnuBlock] = []
        self.counters: dict[str, int] = {}
        self.headings: list[tuple[int, str, str]] = []
        self.mapped = 0
        self.unmapped = 0
        self.unit_states: dict[str, int] = {}
        self.has_page_mapping = has_page_mapping
        self.note_tables: set[str] = set()
        self.render_pages = render_pages or {}

    def next_id(self, prefix: str) -> str:
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        return f"{prefix}{self.counters[prefix]:03d}"

    def section_path(self) -> list[str]:
        return [text for _, text, _ in self.headings]

    def parent_id(self) -> str | None:
        return self.headings[-1][2] if self.headings else None

    def open_section(self, level: int, text: str, block_id: str) -> str | None:
        """Retire siblings and deeper headings first, then the parent is whatever survives."""
        while self.headings and self.headings[-1][0] >= level:
            self.headings.pop()
        parent_id = self.parent_id()
        self.headings.append((level, text, block_id))
        return parent_id

    def map_unit(
        self, text: str, page_ranges: list[tuple[int, int, int]], cursor: int, markdown: str,
        *, full_lines: bool = False,
    ) -> tuple[list[int], int]:
        pages, cursor, state = map_unit_to_page(text, page_ranges, cursor, markdown, full_lines=full_lines)
        if not pages and self.render_pages:
            pattern = _unit_pattern(text)
            native = [page for page, body in self.render_pages.items() if pattern and any(
                not full_lines or _full_line_match(body, hit) for hit in pattern.finditer(body))]
            if len(native) == 1:
                pages, state = native, "native_matched"
        if state == "unavailable" and not self.has_page_mapping:
            return pages, cursor
        self.unit_states[state] = self.unit_states.get(state, 0) + 1
        if pages:
            self.mapped += 1
        else:
            self.unmapped += 1
        return pages, cursor

    def add(self, block: QnuBlock) -> None:
        if (self.has_page_mapping and any(loc.page is None for loc in block.source_locations)
                and not any(flag.code == "page_unresolved" for flag in block.quality_flags)):
            block.quality_flags.append(QnuQualityFlag(
                code="page_unresolved", detail="Không ghim được toàn bộ nội dung vào trang render; giữ locator và page = null."))
        self.blocks.append(block)


def _label(item: Any) -> str:
    return str(getattr(item, "label", "") or "").lower()


def _item_text(item: Any) -> str:
    return clean_text(getattr(item, "text", "") or "")


def _caption_text(item: Any, document: Any) -> str:
    captions = getattr(item, "captions", None) or []
    parts: list[str] = []
    for caption in captions:
        try:
            resolved = caption.resolve(document)
        except Exception:
            resolved = None
        if resolved is not None:
            text = clean_text(getattr(resolved, "text", ""))
            if text:
                parts.append(text)
    return "\n".join(parts)


def _proposed_header_rows(data: Any) -> int:
    grid = getattr(data, "grid", None) or []
    count = 0
    for row in grid:
        cells = [cell for cell in row if cell is not None]
        if not cells:
            break
        if all(getattr(cell, "column_header", False) for cell in cells):
            count += 1
        else:
            break
    return count


def _header_paths(data: Any, header_rows: int) -> list[list[str]]:
    grid = getattr(data, "grid", None) or []
    num_cols = int(getattr(data, "num_cols", 0) or 0)
    paths: list[list[str]] = []
    for col in range(num_cols):
        path: list[str] = []
        origins = set()
        for row in range(header_rows):
            cell = grid[row][col] if row < len(grid) and col < len(grid[row]) else None
            origin = (getattr(cell, "start_row_offset_idx", row), getattr(cell, "start_col_offset_idx", col))
            if origin in origins:
                continue
            origins.add(origin)
            path.append(clean_text(getattr(cell, "text", "") if cell is not None else ""))
        while path and not path[-1].strip():
            path.pop()
        paths.append(path)
    return paths


def _render_gfm(headers: list[str], rows: list[list[str]]) -> str:
    def render(values: list[str]) -> str:
        cells = [format_cell_value(value, join_multiline=True) for value in values]
        return "| " + " | ".join(cells) + " |"

    separator = "| " + " | ".join("---" for _ in headers) + " |"
    return "\n".join([render(headers), separator, *[render(row) for row in rows]])


def _uses_records(data: Any, header_rows: int) -> bool:
    cells = list(getattr(data, "table_cells", None) or [])
    if any(
        int(getattr(cell, "row_span", 1) or 1) > 1 or int(getattr(cell, "col_span", 1) or 1) > 1
        for cell in cells
    ):
        return True
    if header_rows > 1:
        return True
    num_cols = int(getattr(data, "num_cols", 0) or 0)
    num_rows = int(getattr(data, "num_rows", 0) or 0)
    if num_cols > 8 or num_rows > 40:
        return True
    return any(len(clean_text(getattr(cell, "text", ""))) > 120 for cell in cells)


def _table_source_data(data: Any, header_rows: int) -> dict[str, Any]:
    """Exact Docling cells for the JSON artifact; raw values stay strings."""
    cells = list(getattr(data, "table_cells", None) or [])
    return {
        "num_rows": int(getattr(data, "num_rows", 0) or 0),
        "num_cols": int(getattr(data, "num_cols", 0) or 0),
        "header_rows": header_rows,
        "cells": [
            {
                "text": clean_text(getattr(cell, "text", "")),
                "row_start": int(getattr(cell, "start_row_offset_idx", 0)),
                "row_end": int(getattr(cell, "end_row_offset_idx", 0)),
                "col_start": int(getattr(cell, "start_col_offset_idx", 0)),
                "col_end": int(getattr(cell, "end_col_offset_idx", 0)),
                "row_span": int(getattr(cell, "row_span", 1) or 1),
                "col_span": int(getattr(cell, "col_span", 1) or 1),
                "column_header": bool(getattr(cell, "column_header", False)),
                "row_header": bool(getattr(cell, "row_header", False)),
                "row_section": bool(getattr(cell, "row_section", False)),
            }
            for cell in cells
        ],
    }


def _table_columns(header_paths: list[list[str]]) -> list[dict[str, Any]]:
    return [
        QnuColumn(id=f"c{index + 1:02d}", header_path=path).model_dump()
        for index, path in enumerate(header_paths)
    ]


def _add_table(
    builder: _Builder,
    item: Any,
    block_index: int,
    page_ranges: list[tuple[int, int, int]],
    cursor: int,
    markdown: str,
    header_evidence: dict[str, dict[str, Any]],
) -> int:
    data = getattr(item, "data", None)
    section_path = builder.section_path()
    parent_id = builder.parent_id()
    grid = list(getattr(data, "grid", None) or []) if data is not None else []
    num_cols = int(getattr(data, "num_cols", 0) or 0) if data is not None else 0
    if data is None or not grid or num_cols <= 0:
        builder.add(
            QnuBlock(
                id=builder.next_id("t"),
                parent_id=parent_id,
                type="table",
                source_locations=[_location(block_index, None)],
                section_path=section_path,
                attributes={
                    "representation": "gfm",
                    "source_ref": getattr(item, "self_ref", None),
                },
                quality_flags=[
                    QnuQualityFlag(
                        code="missing_content",
                        detail="Docling không trả về ô dữ liệu cho bảng này; cần đối soát nguồn.",
                    )
                ],
                body="",
            )
        )
        return cursor
    proposal_depth = _proposed_header_rows(data)
    proof = header_evidence.get(getattr(item, "self_ref", ""), {})
    depth = proof.get("leading_header_rows")
    header_rows = depth if (proof.get("basis") == "docx_tblHeader" and isinstance(depth, int)
                            and not isinstance(depth, bool) and 0 <= depth <= len(grid)) else 0
    source_data = _table_source_data(data, header_rows)
    source_data.update(header_evidence=proof, proposed_header_rows=proposal_depth)
    flags = [] if header_rows else [QnuQualityFlag(code="table_header_unresolved",
        detail="Header do engine đề xuất chưa có vai trò được xác minh từ DOCX; giữ mọi hàng dữ liệu.")]
    # Locate each row once. Only a table whose entire grid is on the same known page
    # can share one GFM location; records retain independent locations otherwise.
    row_pages = []
    for row in grid:
        pages, cursor = builder.map_unit(_row_unit_text(row), page_ranges, cursor, markdown)
        row_pages.append(pages)
    # Ordered DOCX rows bracketed by independently located rows on the same
    # physical page cannot cross a page boundary. Never infer across two pages.
    for row, located in enumerate(row_pages):
        if located:
            continue
        left = next((p for p in reversed(row_pages[:row]) if p), [])
        right = next((p for p in row_pages[row + 1:] if p), [])
        if left and right and left[-1] == right[0]:
            row_pages[row] = [left[-1]]
    header_pages = row_pages[:header_rows] or row_pages[:1]
    pages = sorted({page for located in header_pages for page in located}) if all(header_pages) else []
    single_page = all(row_pages) and len({page for located in row_pages for page in located}) == 1
    header_paths = _header_paths(data, header_rows)
    table_id = builder.next_id("t")
    attributes: dict[str, Any] = {
        "representation": "records" if header_rows < len(grid) and (
            not header_rows or _uses_records(data, header_rows) or (page_ranges and not single_page)) else "gfm",
        "columns": _table_columns(header_paths),
        "source_ref": getattr(item, "self_ref", None),
    }
    table_number = proof.get("locator", "").rsplit("/", 1)[-1]
    if table_number in builder.note_tables and header_rows < len(grid):
        attributes["representation"] = "records"  # Anchor coordinates need independently identifiable rows.
    if attributes["representation"] == "records":
        table_block = QnuBlock(
            id=table_id,
            parent_id=parent_id,
            type="table",
            source_locations=_locations(block_index, pages),
            section_path=section_path,
            attributes=attributes,
            quality_flags=flags,
            body="",
            source_data=source_data,
        )
        builder.add(table_block)
        return _add_table_rows(
            builder,
            grid,
            header_rows,
            num_cols,
            table_block,
            block_index,
            section_path,
            header_paths,
            row_pages,
            cursor,
        )
    headers = [path[-1] if path else "" for path in header_paths]
    rows = [
        [clean_text(getattr(cell, "text", "")) for cell in grid[row]]
        for row in range(header_rows, len(grid))
    ]
    builder.add(
        QnuBlock(
            id=table_id,
            parent_id=parent_id,
            type="table",
            source_locations=_locations(block_index, pages),
            section_path=section_path,
            attributes=attributes,
            quality_flags=flags,
            body=_render_gfm(headers, rows),
            source_data=source_data,
        )
    )
    return cursor


def _row_fields(grid: list[list[Any]], row: int, column_ids: list[str]) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    for col, column_id in enumerate(column_ids):
        cell = grid[row][col] if col < len(grid[row]) else None
        raw = clean_text(getattr(cell, "text", "") if cell is not None else "")
        fields[column_id] = QnuFieldValue(raw=raw, state=cell_state(raw)).model_dump()
    return fields


def _add_table_rows(
    builder: _Builder,
    grid: list[list[Any]],
    header_rows: int,
    num_cols: int,
    table_block: QnuBlock,
    block_index: int,
    section_path: list[str],
    header_paths: list[list[str]],
    row_pages: list[list[int]],
    cursor: int,
) -> int:
    table_id = table_block.id
    column_ids = [f"c{index + 1:02d}" for index in range(num_cols)]
    row_ids: dict[int, str] = {}
    emitted: list[QnuBlock] = []
    unknown_rows: list[str] = []
    for row in range(header_rows, len(grid)):
        row_id = builder.next_id("r")
        row_ids[row] = row_id
        fields = _row_fields(grid, row, column_ids)
        origins: dict[str, dict[str, Any]] = {}
        for col, column_id in enumerate(column_ids):
            cell = grid[row][col] if col < len(grid[row]) else None
            if cell is None:
                continue
            origin_row = int(getattr(cell, "start_row_offset_idx", row))
            origin_col = int(getattr(cell, "start_col_offset_idx", col))
            if (origin_row, origin_col) == (row, col):
                continue
            origins[column_id] = {
                "block_id": row_ids.get(origin_row, table_id),
                "column_id": f"c{origin_col + 1:02d}",
                "basis": "merged_cell",
            }
        attributes: dict[str, Any] = {"fields": fields}
        if origins:
            attributes["field_origins"] = origins
        cells = [cell for cell in grid[row] if cell is not None]
        spanning = num_cols > 1 and len(cells) == num_cols and all(cell is cells[0] for cell in cells)
        if spanning:
            attributes["row_role"] = "spanning_row_unclassified"
        body_lines: list[str] = []
        for col, column_id in enumerate(column_ids):
            path = header_paths[col] if col < len(header_paths) else []
            label = " / ".join(part for part in path if part.strip()) or f"Cột {col + 1:02d}"
            value = fields[column_id]["raw"]
            body_lines.append(f"**{label}:** {value if value.strip() else _BLANK_DISPLAY}")
        pages = row_pages[row]
        if not pages:
            unknown_rows.append(row_id)
        emitted.append(
            QnuBlock(
                id=row_id,
                parent_id=table_id,
                type="table_row",
                source_locations=_locations(block_index, pages, f"#row{row + 1}"),
                source_label=str(row + 1),
                section_path=section_path,
                attributes=attributes,
                quality_flags=[QnuQualityFlag(code="spanning_row_needs_review",
                    detail="Dòng gộp chưa rõ là dữ liệu, nhãn nhóm hay chú thích; giữ hàng và ô nguồn.")] if spanning else [],
                body="\n\n".join(body_lines),
            )
        )
    if unknown_rows:
        table_block.quality_flags.append(
            QnuQualityFlag(
                code="page_unresolved",
                detail=(
                    "Bảng qua trang hoặc có dòng không định vị được chắc chắn trong bản render; "
                    "các dòng này giữ page = null kèm locator dòng."
                ),
                related_block_ids=unknown_rows[:50],
            )
        )
    for block in emitted:
        builder.add(block)
    return cursor


def build_qnu_structured_document(
    document: Any,
    *,
    filename: str,
    sha256: str | None,
    projection_markdown: str = "",
    page_ranges: list[tuple[int, int, int]] | None = None,
    render_sha256: str | None = None,
    render_page_count: int | None = None,
    title: str | None = None,
    document_type: str | None = None,
    header_evidence: dict[str, dict[str, Any]] | None = None,
    source_evidence: dict[str, Any] | None = None,
) -> QnuStructuredDocument:
    """Walk a Docling document in reading order and build the QNU v1.0 model."""
    ranges = page_ranges or []
    render_pages = (source_evidence or {}).get("render_pages") or {}
    builder = _Builder(has_page_mapping=bool(ranges or render_pages), render_pages=render_pages)
    builder.note_tables = {str(p["table"]["table"]) for p in (source_evidence or {}).get("paragraphs", [])
                           if p.get("notes") and p.get("table")}
    indexed = [
        (index + 1, item, int(level or 0))
        for index, (item, level) in enumerate(document.iterate_items())
    ]
    native_lists = list_item_evidence(indexed, (source_evidence or {}).get('paragraphs', []))
    list_stack: list[dict] = []
    list_section = None
    position = 0
    cursor = 0
    while position < len(indexed):
        block_index, item, level = indexed[position]
        label = _label(item)
        text = _item_text(item)
        if _is_materialized_cell_text(item, document, text):
            position += 1
            continue
        if label == "list_item":
            run: list[tuple[int, Any, int]] = []
            while position < len(indexed) and _label(indexed[position][1]) == "list_item":
                run.append(indexed[position])
                position += 1
            base_level = min(run_level for _, _, run_level in run)
            list_items: list[dict] = []
            locations: list[QnuSourceLocation] = []
            unknown_items: list[str] = []
            for item_index, list_item, item_level in run:
                item_text = _item_text(list_item)
                if not item_text.strip():
                    continue
                native = native_lists.get(item_index, {})
                numbering = native.get('numbering') or {}
                manual = MARKER.match(native.get('text', ''))
                marker = (numbering.get('marker') if numbering.get('status') == 'source_defined' else None) or (manual[1] if manual else None)
                marker = marker or (clean_text(getattr(list_item, 'marker', '')).strip() if getattr(list_item, 'enumerated', False) else '-') or '-'
                # Each item is located on its own: a run can cross a page boundary.
                item_pages, cursor = builder.map_unit(item_text, ranges, cursor, projection_markdown, full_lines=True)
                if not item_pages:
                    unknown_items.append(str(item_index))
                locations.extend(_locations(item_index, item_pages))
                item_level = numbering.get('level', max(0, item_level - base_level))
                list_items.append({'id': f'item_{item_index}', 'level': item_level, 'marker': marker,
                    'text': item_text, 'numbering': numbering, 'source_locator': native.get('locator'),
                    'source_locations': [loc.model_dump() for loc in _locations(item_index, item_pages)]})
            if list_items:
                if list_section != builder.parent_id():
                    list_stack.clear()
                list_section = builder.parent_id()
                for entry in list_items:
                    while list_stack and list_stack[-1]['level'] >= entry['level']:
                        list_stack.pop()
                    entry['parent_id'] = list_stack[-1]['id'] if list_stack else None
                    list_stack.append(entry)
                builder.add(
                    QnuBlock(
                        id=builder.next_id("l"),
                        parent_id=builder.parent_id(),
                        type="list",
                        source_locations=locations,
                        section_path=builder.section_path(),
                        attributes={'list_items': list_items, 'list_structure_version': 'docx-lists/v1'},
                        quality_flags=(
                            []
                            if not unknown_items
                            else [
                                QnuQualityFlag(
                                    code="page_unresolved",
                                    detail=(
                                        "Danh sách qua trang hoặc có mục không định vị được chắc chắn; "
                                        "các mục đó giữ page = null kèm locator."
                                    ),
                                    related_block_ids=unknown_items[:50],
                                )
                            ]
                        ),
                        body=render_list_items(list_items),
                    )
                )
            continue
        if label in {"section_header", "title"}:
            if text.strip():
                depth = 1 if label == "title" else min(max(level, 1), 6)
                section_id = builder.next_id("s")
                parent_id = builder.open_section(level, text, section_id)
                pages, cursor = builder.map_unit(text, ranges, cursor, projection_markdown, full_lines=True)
                builder.add(
                    QnuBlock(
                        id=section_id,
                        parent_id=parent_id,
                        type="section",
                        source_locations=_locations(block_index, pages),
                        section_path=builder.section_path(),
                        body=f"{'#' * depth} {text}",
                    )
                )
            position += 1
            continue
        if label == "table":
            cursor = _add_table(builder, item, block_index, ranges, cursor, projection_markdown, header_evidence or {})
            position += 1
            continue
        if label == "picture":
            caption = _caption_text(item, document)
            pages, cursor = builder.map_unit(caption, ranges, cursor, projection_markdown)
            builder.add(
                QnuBlock(
                    id=builder.next_id("fg"),
                    parent_id=builder.parent_id(),
                    type="figure",
                    source_locations=_locations(block_index, pages),
                    section_path=builder.section_path(),
                    attributes={
                        "resource": {
                            "kind": "docx_embedded_image",
                            "ref": getattr(item, "self_ref", None),
                        }
                    },
                    quality_flags=[
                        QnuQualityFlag(
                            code="missing_content",
                            detail="Chưa trích xuất được tệp ảnh; chỉ giữ tham chiếu phần tử và chú thích nếu có.",
                        )
                    ],
                    body=caption,
                )
            )
            position += 1
            continue
        if label == "formula":
            pages, cursor = builder.map_unit(text, ranges, cursor, projection_markdown, full_lines=True)
            flags = (
                []
                if text.strip()
                else [
                    QnuQualityFlag(
                        code="missing_content",
                        detail="Công thức trong nguồn chưa trích xuất được dạng văn bản.",
                    )
                ]
            )
            builder.add(
                QnuBlock(
                    id=builder.next_id("fm"),
                    parent_id=builder.parent_id(),
                    type="formula",
                    source_locations=_locations(block_index, pages),
                    section_path=builder.section_path(),
                    quality_flags=flags,
                    body=text or "*[Công thức chưa trích xuất được]*",
                )
            )
            position += 1
            continue
        if label == "code":
            pages, cursor = builder.map_unit(text, ranges, cursor, projection_markdown, full_lines=True)
            fence = _fence_for(text)
            language = clean_text(getattr(item, "code_language", "") or "")
            builder.add(
                QnuBlock(
                    id=builder.next_id("c"),
                    parent_id=builder.parent_id(),
                    type="code",
                    source_locations=_locations(block_index, pages),
                    section_path=builder.section_path(),
                    attributes={"language": language} if language else {},
                    body=f"{fence}{language}\n{text}\n{fence}",
                )
            )
            position += 1
            continue
        if text.strip():
            pages, cursor = builder.map_unit(text, ranges, cursor, projection_markdown, full_lines=True)
            block_type = "note" if label in {"caption", "footnote"} else "text"
            builder.add(
                QnuBlock(
                    id=builder.next_id("n" if block_type == "note" else "p"),
                    parent_id=builder.parent_id(),
                    type=block_type,
                    source_locations=_locations(block_index, pages),
                    section_path=builder.section_path(),
                    attributes={"role": label} if label in {"page_header", "page_footer"} else {},
                    body=text,
                )
            )
        position += 1
    stats = {
        "block_count": len(builder.blocks),
        "type_counts": {
            block_type: sum(1 for block in builder.blocks if block.type == block_type)
            for block_type in sorted({block.type for block in builder.blocks})
        },
        "mapped_units": builder.mapped,
        "unmapped_units": builder.unmapped,
        "unit_states": dict(sorted(builder.unit_states.items())),
        "table_representations": {
            "records": sum(
                1
                for block in builder.blocks
                if block.type == "table" and block.attributes.get("representation") == "records"
            ),
            "gfm": sum(
                1
                for block in builder.blocks
                if block.type == "table" and block.attributes.get("representation") == "gfm"
            ),
        },
    }
    has_mapping = bool(ranges or render_pages)
    mapping_status = "aligned" if has_mapping and not builder.unmapped else "partial" if has_mapping else "unavailable"
    document_meta: dict[str, Any] = {
        "list_structure_version": "docx-lists/v1",
        "source_format": "docx",
        "locator_scheme": LOCATOR_SCHEME,
        "page_mapping": {
            "status": mapping_status,
            "kind": "pdf_preview_render" if has_mapping else None,
            "render_sha256": render_sha256,
            "render_page_count": render_page_count,
            "method": "aligned_tokens_unique_native_units_and_same_page_row_brackets" if has_mapping else None,
            "note": (
                "DOCX không có số trang vật lý; page là trang của bản PDF render xem trước, "
                "không phải trang in của DOCX."
            ),
        },
    }
    document_title = title or next(
        (
            _item_text(doc_item)
            for _, doc_item, _ in indexed
            if _label(doc_item) == "title" and _item_text(doc_item).strip()
        ),
        None,
    )
    model = QnuStructuredDocument(
        title=document_title or filename.rsplit(".", 1)[0] or filename,
        document_type=document_type,
        source=QnuSourceInfo(filename=filename, sha256=sha256, page_count=None),
        document_meta=document_meta,
        blocks=builder.blocks,
        stats=stats,
    )
    from app.modules.knowledge.parsers.docx_evidence import apply_docx_evidence

    apply_docx_evidence(model, source_evidence or {})
    return model


def _is_materialized_cell_text(item: Any, document: Any, text: str) -> bool:
    """Rich-cell children already preserved in the table must not become duplicate prose."""
    if not text.strip() or _label(item) not in {"text", "section_header", "list_item", "code"}:
        return False
    parent = getattr(item, "parent", None)
    seen = set()
    while parent is not None and getattr(parent, "cref", None) not in seen:
        seen.add(getattr(parent, "cref", None))
        ancestor = parent.resolve(document)
        if _label(ancestor) == "table":
            wanted = " ".join(text.split())
            return any(wanted in " ".join(clean_text(getattr(cell, "text", "")).split())
                       for cell in getattr(getattr(ancestor, "data", None), "table_cells", []))
        parent = getattr(ancestor, "parent", None)
    return False
