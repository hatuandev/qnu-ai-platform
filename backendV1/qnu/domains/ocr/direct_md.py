"""Direct Markdown (.md) extraction into canonical evidence format."""

from __future__ import annotations

import asyncio
import re

from qnu.domains.knowledge.compilation.schemas import DRAFT_PARAGRAPH_TEXT_LIMIT
from qnu.domains.ocr.artifacts.render import PageImage, RenderedDocument
from qnu.domains.ocr.layout import MAX_TABLE_COLUMNS, MAX_TABLE_ROWS, Block, Cell, PageLayout, Table
from qnu.domains.ocr.native import NativePage, NativePlan
from qnu.platform.errors import AppException

MD_PARAGRAPH_TEXT_LIMIT = 4000

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_TABLE_SEP_CELL_RE = re.compile(r"^\s*:?-+:?\s*$")


def _is_table_separator_row(cells: list[str]) -> bool:
    return len(cells) > 0 and all(_TABLE_SEP_CELL_RE.match(c) for c in cells)


def _split_table_row(line: str) -> list[str]:
    raw = line.strip().removeprefix("|").removesuffix("|")
    return [c.strip() for c in raw.split("|")]


def _split_long_text(text: str, limit: int = MD_PARAGRAPH_TEXT_LIMIT) -> list[str]:
    # Never exceed compilation draft paragraph limit either
    effective_limit = min(limit, DRAFT_PARAGRAPH_TEXT_LIMIT)
    if len(text) <= effective_limit:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = start + effective_limit
        if end >= len(text):
            parts.append(text[start:].strip())
            break
        # Try to break at a newline or space
        space_idx = text.rfind("\n", start, end)
        if space_idx == -1 or space_idx <= start:
            space_idx = text.rfind(" ", start, end)
        if space_idx > start:
            end = space_idx
        parts.append(text[start:end].strip())
        start = end + 1
    return [p for p in parts if p]


def extract_md(payload: bytes) -> tuple[RenderedDocument, NativePlan]:
    """Parse a Markdown (.md) payload directly into canonical layout blocks."""
    if not payload:
        raise AppException("Tệp Markdown rỗng.", code="md_empty", status_code=422)

    try:
        content = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppException(
            f"Không thể giải mã tệp Markdown (yêu cầu UTF-8): {exc}",
            code="md_encoding_invalid",
            status_code=422,
        ) from exc

    raw_lines = content.splitlines()
    if not any(line.strip() for line in raw_lines):
        raise AppException(
            "Tệp Markdown không chứa nội dung hợp lệ.",
            code="md_empty_content",
            status_code=422,
        )

    # 1. Skip YAML Frontmatter if present
    start_line_idx = 0
    if raw_lines and raw_lines[0].strip() == "---":
        for idx in range(1, len(raw_lines)):
            if raw_lines[idx].strip() == "---":
                start_line_idx = idx + 1
                break

    blocks: list[Block] = []
    order = 1
    pending_text_lines: list[str] = []
    in_fenced_code = False
    fenced_fence = ""
    fenced_lines: list[str] = []

    def flush_pending_text():
        nonlocal order, pending_text_lines
        if not pending_text_lines:
            return
        combined = "\n".join(pending_text_lines).strip()
        pending_text_lines = []
        if not combined:
            return
        for segment in _split_long_text(combined):
            blocks.append(
                Block(
                    order=order,
                    label="Text",
                    kind="text",
                    text=segment,
                    bbox=None,
                    requires_review=False,
                    origin="native",
                    source_locator={"format": "md"},
                )
            )
            order += 1

    idx = start_line_idx
    total_lines = len(raw_lines)

    while idx < total_lines:
        line = raw_lines[idx]
        stripped = line.strip()

        # Check fenced code block
        if stripped.startswith(("```", "~~~")):
            fence = stripped[:3]
            if not in_fenced_code:
                flush_pending_text()
                in_fenced_code = True
                fenced_fence = fence
                fenced_lines = [line]
                idx += 1
                continue
            elif fence == fenced_fence:
                fenced_lines.append(line)
                code_text = "\n".join(fenced_lines)
                for segment in _split_long_text(code_text):
                    blocks.append(
                        Block(
                            order=order,
                            label="Code",
                            kind="text",
                            text=segment,
                            bbox=None,
                            requires_review=False,
                            origin="native",
                            source_locator={"format": "md"},
                        )
                    )
                    order += 1
                in_fenced_code = False
                fenced_fence = ""
                fenced_lines = []
                idx += 1
                continue

        if in_fenced_code:
            fenced_lines.append(line)
            idx += 1
            continue

        # Check Heading
        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            flush_pending_text()
            level = len(heading_match.group(1))
            blocks.append(
                Block(
                    order=order,
                    label=f"Heading {level}",
                    kind="title",
                    text=stripped,
                    bbox=None,
                    requires_review=False,
                    origin="native",
                    source_locator={"format": "md", "level": level},
                )
            )
            order += 1
            idx += 1
            continue

        # Check Table
        if "|" in stripped and idx + 1 < total_lines and "|" in raw_lines[idx + 1]:
            sep_cells = _split_table_row(raw_lines[idx + 1])
            if _is_table_separator_row(sep_cells):
                flush_pending_text()
                header_row = _split_table_row(stripped)
                col_count = len(header_row)

                if col_count > MAX_TABLE_COLUMNS:
                    col_count = MAX_TABLE_COLUMNS
                    header_row = header_row[:MAX_TABLE_COLUMNS]

                table_rows: list[list[Cell]] = []
                table_rows.append([Cell(text=c, header=True) for c in header_row])

                # Advance past separator
                idx += 2
                while idx < total_lines:
                    cur_line = raw_lines[idx].strip()
                    if not cur_line or "|" not in cur_line:
                        break
                    row_cells = _split_table_row(cur_line)
                    # Align columns
                    if len(row_cells) < col_count:
                        row_cells.extend([""] * (col_count - len(row_cells)))
                    elif len(row_cells) > col_count:
                        row_cells = row_cells[:col_count]

                    table_rows.append([Cell(text=c, header=False) for c in row_cells])
                    idx += 1

                if len(table_rows) > MAX_TABLE_ROWS:
                    raise AppException(
                        f"Bảng Markdown chứa {len(table_rows)} hàng, vượt quá giới hạn hệ thống ({MAX_TABLE_ROWS} hàng).",
                        code="md_table_exceeds_layout_limit",
                        status_code=422,
                    )

                table_obj = Table(
                    status="parsed",
                    rows=tuple(tuple(r) for r in table_rows),
                    column_count=col_count,
                    source_mapping={"format": "md", "rows": len(table_rows)},
                )

                # Reconstruct clean Markdown table representation
                md_lines = []
                md_lines.append("| " + " | ".join(c.text for c in table_rows[0]) + " |")
                md_lines.append("| " + " | ".join(["---"] * col_count) + " |")
                for r in table_rows[1:]:
                    md_lines.append("| " + " | ".join(c.text for c in r) + " |")
                md_table_text = "\n".join(md_lines)

                blocks.append(
                    Block(
                        order=order,
                        label="Table",
                        kind="table",
                        text=md_table_text,
                        bbox=None,
                        requires_review=False,
                        table=table_obj,
                        origin="native",
                        source_locator={"format": "md"},
                    )
                )
                order += 1
                continue

        # Blank line flushes paragraph
        if not stripped:
            flush_pending_text()
            idx += 1
            continue

        # Accumulate text line
        pending_text_lines.append(line)
        idx += 1

    # Final flush
    if in_fenced_code and fenced_lines:
        code_text = "\n".join(fenced_lines)
        for segment in _split_long_text(code_text):
            blocks.append(
                Block(
                    order=order,
                    label="Code",
                    kind="text",
                    text=segment,
                    bbox=None,
                    requires_review=False,
                    origin="native",
                    source_locator={"format": "md"},
                )
            )
            order += 1

    flush_pending_text()

    if not blocks:
        raise AppException(
            "Tệp Markdown không chứa khối nội dung nào.",
            code="md_empty_content",
            status_code=422,
        )

    page_layout = PageLayout(blocks=tuple(blocks))
    pages = (
        NativePage(
            page_number=1,
            layout=page_layout,
            images=(),
            needs_ocr=False,
            native_text=True,
        ),
    )
    rendered_pages = (PageImage(1, None, None, None, None, False, None),)

    rendered = RenderedDocument(
        extension=".md",
        renderer={
            "name": "native_md",
            "version": "1.0.0",
            "pagination": "document",
        },
        pages=rendered_pages,
    )
    return rendered, NativePlan(pages, "source_revision")


async def extract_md_async(payload: bytes) -> tuple[RenderedDocument, NativePlan]:
    return await asyncio.to_thread(extract_md, payload)
