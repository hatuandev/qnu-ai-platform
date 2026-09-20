"""Markdown parser preserving GFM tables and structured QNU action-plan records."""

from __future__ import annotations

import re
import unicodedata

from app.modules.knowledge.normalization.markdown_renderer import (
    render_canonical_document_markdown,
    render_canonical_table_markdown,
)
from app.modules.knowledge.normalization.models import (
    BlockType,
    CanonicalBlock,
    CanonicalCell,
    CanonicalDocument,
    CanonicalRow,
    CanonicalTable,
    SourceSpan,
)
from app.modules.knowledge.normalization.table_reconstructor import (
    reconstruct_multi_page_tables,
    table_schema_key,
)
from app.modules.knowledge.normalization.text_normalizer import (
    normalize_encoding,
    normalize_whitespace,
)
from app.modules.knowledge.parsers.base import BaseDocumentParser, ExtractedTable, ParsedContent

_GFM_SEPARATOR_RE = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)
_TASK_HEADING_RE = re.compile(
    r"^Kế hoạch nhiệm vụ\s+(?P<code>\d+\.\d+)\s+\((?P<category>[^)]*)\):\s*$",
    re.IGNORECASE,
)
_TASK_FIELD_RE = re.compile(
    r"^-\s*(?P<name>Nội dung nhiệm vụ|Đơn vị chủ trì|Đơn vị phối hợp|Thời gian thực hiện|Sản phẩm kết quả):\s*",
    re.IGNORECASE,
)


def _split_gfm_row(line: str) -> list[str]:
    """Split one GFM row while preserving escaped pipes and cell line breaks."""
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line.strip():
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip().replace("<br>", "\n"))
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip().replace("<br>", "\n"))
    if cells and not cells[0]:
        cells.pop(0)
    if cells and not cells[-1]:
        cells.pop()
    return cells


def _cell(value: str, page_number: int, row_index: int, column_index: int) -> CanonicalCell:
    clean_value = unicodedata.normalize("NFC", value).strip()
    return CanonicalCell(
        raw_value=clean_value,
        normalized_value=clean_value or None,
        source_span=SourceSpan(page_number=page_number),
        confidence=0.95,
    )


def _make_table(block_lines: list[str], virtual_page: int, table_index: int) -> CanonicalTable:
    headers = _split_gfm_row(block_lines[0])
    rows = [
        CanonicalRow(
            row_id=f"md_p{virtual_page}_t{table_index}_r{row_index}",
            cells=[_cell(value, virtual_page, row_index, column_index) for column_index, value in enumerate(_split_gfm_row(line))],
            source_pages=[virtual_page],
        )
        for row_index, line in enumerate(block_lines[2:], start=1)
    ]
    return CanonicalTable(
        table_id=f"markdown_table_{table_index}",
        schema_key=table_schema_key(headers),
        headers=headers,
        rows=rows,
        source_pages=[virtual_page],
    )


def _extract_gfm_tables(lines: list[str]) -> tuple[list[CanonicalTable], set[int]]:
    """Extract GFM blocks and return their line positions for paragraph suppression."""
    tables: list[CanonicalTable] = []
    table_lines: set[int] = set()
    line_index = 0
    table_index = 1
    virtual_page = 1
    while line_index + 1 < len(lines):
        if "|" not in lines[line_index] or not _GFM_SEPARATOR_RE.match(lines[line_index + 1]):
            line_index += 1
            continue
        block_lines = [lines[line_index], lines[line_index + 1]]
        row_index = line_index + 2
        while row_index < len(lines) and "|" in lines[row_index]:
            next_line_is_separator = (
                row_index + 1 < len(lines)
                and _GFM_SEPARATOR_RE.match(lines[row_index + 1]) is not None
            )
            if _GFM_SEPARATOR_RE.match(lines[row_index]) or next_line_is_separator:
                break
            block_lines.append(lines[row_index])
            row_index += 1
        tables.append(_make_table(block_lines, virtual_page, table_index))
        table_lines.update(range(line_index, row_index))
        table_index += 1
        virtual_page += 1
        line_index = row_index
    return tables, table_lines


def _field_values(task_lines: list[str]) -> dict[str, str]:
    """Read labeled task fields, joining OCR-wrapped continuation lines."""
    values: dict[str, list[str]] = {}
    current_name: str | None = None
    for line in task_lines:
        match = _TASK_FIELD_RE.match(line.strip())
        if match:
            current_name = match.group("name").casefold()
            values[current_name] = [line[match.end() :].strip()]
            continue
        if current_name and line.strip() and not line.lstrip().startswith("---"):
            values[current_name].append(line.strip())
    return {
        name: re.sub(r"\s+", " ", " ".join(parts)).strip()
        for name, parts in values.items()
    }


def _extract_plan_table(lines: list[str], start_index: int) -> tuple[CanonicalTable | None, set[int]]:
    """Convert narrative ``Kế hoạch nhiệm vụ X.Y`` sections into one canonical table."""
    matches = [
        (index, match)
        for index, line in enumerate(lines[start_index:], start=start_index)
        if (match := _TASK_HEADING_RE.match(line.strip()))
    ]
    if not matches:
        return None, set()

    rows: list[CanonicalRow] = []
    consumed: set[int] = set()
    for match_index, (line_index, match) in enumerate(matches):
        next_index = matches[match_index + 1][0] if match_index + 1 < len(matches) else len(lines)
        block_lines = lines[line_index:next_index]
        consumed.update(range(line_index, next_index))
        fields = _field_values(block_lines[1:])
        content = fields.get("nội dung nhiệm vụ", "")
        if not content:
            continue
        source_page = 1
        rows.append(
            CanonicalRow(
                row_id=f"markdown_task_{match.group('code')}",
                cells=[
                    _cell(match.group("code"), source_page, len(rows), 0),
                    _cell(content, source_page, len(rows), 1),
                    _cell(fields.get("đơn vị chủ trì", ""), source_page, len(rows), 2),
                    _cell(fields.get("đơn vị phối hợp", ""), source_page, len(rows), 3),
                    _cell(fields.get("thời gian thực hiện", ""), source_page, len(rows), 4),
                    _cell("", source_page, len(rows), 5),
                    _cell(fields.get("sản phẩm kết quả", ""), source_page, len(rows), 6),
                ],
                source_pages=[source_page],
            )
        )

    if not rows:
        return None, consumed
    headers = [
        "TT",
        "Nội dung nhiệm vụ",
        "Đơn vị chủ trì",
        "Đơn vị phối hợp",
        "Thời gian thực hiện",
        "Thời gian hoàn thành",
        "Sản phẩm kết quả",
    ]
    return (
        CanonicalTable(
            table_id="markdown_implementation_tasks",
            schema_key=table_schema_key(headers),
            headers=headers,
            rows=rows,
            source_pages=[1],
        ),
        consumed,
    )


def _make_blocks(lines: list[str], suppressed_lines: set[int]) -> list[CanonicalBlock]:
    """Keep non-table Markdown as provenance-bearing narrative blocks."""
    blocks: list[CanonicalBlock] = []
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        text = re.sub(r"\s+", " ", " ".join(buffer)).strip()
        if text:
            block_type = BlockType.HEADING if text.startswith("#") else BlockType.PARAGRAPH
            blocks.append(
                CanonicalBlock(
                    block_id=f"markdown_block_{len(blocks) + 1}",
                    type=block_type,
                    text=text,
                    source_span=SourceSpan(page_number=1),
                )
            )
        buffer.clear()

    for index, line in enumerate(lines):
        if index in suppressed_lines or not line.strip():
            flush()
            continue
        if line.strip() == "---":
            flush()
            continue
        buffer.append(line.strip())
    flush()
    return blocks


class MarkdownParser(BaseDocumentParser):
    """Parse cleaned Markdown into canonical tables, narrative blocks and domain records."""

    async def parse(self, file_bytes: bytes, file_name: str) -> ParsedContent:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")
        text = normalize_whitespace(normalize_encoding(text))
        lines = text.splitlines()

        markdown_tables, table_lines = _extract_gfm_tables(lines)
        plan_table, plan_lines = _extract_plan_table(lines, 0)
        if plan_table is not None:
            markdown_tables.append(plan_table)
            table_lines.update(plan_lines)

        canonical_tables = reconstruct_multi_page_tables(markdown_tables)
        blocks = _make_blocks(lines, table_lines)
        canonical_document = CanonicalDocument(
            document_id=file_name,
            page_count=max(1, len(markdown_tables)),
            blocks=blocks,
            tables=canonical_tables,
            metadata={
                "title": file_name,
                "file_type": "md",
                "table_count": len(canonical_tables),
            },
        )
        clean_markdown = render_canonical_document_markdown(canonical_document)
        extracted_tables = [
            ExtractedTable(
                page_number=min(table.source_pages) if table.source_pages else 1,
                headers=table.headers,
                rows=[[cell.raw_value for cell in row.cells] for row in table.rows],
                markdown_repr=render_canonical_table_markdown(table),
            )
            for table in canonical_tables
        ]
        return ParsedContent(
            raw_text=clean_markdown or text,
            page_count=canonical_document.page_count,
            tables=extracted_tables,
            metadata=canonical_document.metadata,
            canonical_document=canonical_document,
        )
