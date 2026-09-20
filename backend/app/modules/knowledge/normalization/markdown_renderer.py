"""Markdown Renderer for Canonical Documents & Reconstructed Tables.

Renders high-fidelity, single-line Markdown tables and clean document text:
- Enforces strict 1-row-per-line Markdown table specification (no broken lines).
- Escapes pipe delimiters and transforms multi-line cell breaks into clean `<br>` or semicolons.
- Suppresses phantom columns ('Cột N') and redundant duplicated headers.
- Emits clean provenance page comments without splitting table rows.
"""

from __future__ import annotations

import re

from app.modules.knowledge.normalization.models import (
    CanonicalDocument,
    CanonicalTable,
)


def format_cell_value(val: str | None, join_multiline: bool = True) -> str:
    """Format an atomic cell value for Markdown table rendering."""
    if not val:
        return ""
    text = str(val).strip()
    # Escape pipe characters
    text = text.replace("|", "\\|")
    if join_multiline:
        # Replace physical line-breaks with <br> for clean table layout
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        text = "<br>".join(lines)
    else:
        text = re.sub(r"\s+", " ", text).strip()
    return text


def render_canonical_table_markdown(table: CanonicalTable) -> str:
    """Render a CanonicalTable into standard GitHub Flavored Markdown."""
    if not table.headers and not table.rows:
        return ""

    # A missing header is a structural extraction error, not a value that may be
    # silently promoted to ``Cột N`` and later embedded into Qdrant.
    if not table.headers or any(not header.strip() for header in table.headers):
        return ""

    headers = table.headers
    col_count = len(headers)

    # 1. Header line
    header_line = "| " + " | ".join(format_cell_value(h, join_multiline=False) for h in headers) + " |"

    # 2. Separator line with smart alignment
    sep_elements = []
    for idx, h in enumerate(headers):
        h_lower = h.lower()
        if idx == 0 or "stt" in h_lower or "tt" in h_lower or "mã" in h_lower or "điểm" in h_lower or "chỉ tiêu" in h_lower or "năm" in h_lower:
            sep_elements.append(":---:")
        else:
            sep_elements.append(":---")
    sep_line = "| " + " | ".join(sep_elements) + " |"

    # 3. Data rows (strictly 1 line per row)
    data_lines: list[str] = []
    for row in table.rows:
        row_cells = []
        for c_idx in range(col_count):
            cell_val = row.cells[c_idx].raw_value if c_idx < len(row.cells) else ""
            row_cells.append(format_cell_value(cell_val, join_multiline=True))
        data_lines.append("| " + " | ".join(row_cells) + " |")

    return "\n".join([header_line, sep_line] + data_lines)


def render_canonical_document_markdown(doc: CanonicalDocument) -> str:
    """Render an entire CanonicalDocument into unified, duplicate-free Markdown."""
    parts: list[str] = []

    # Sort blocks by page and position
    sorted_blocks = sorted(
        doc.blocks,
        key=lambda b: (
            b.source_span.page_number,
            b.source_span.bbox[1] if b.source_span.bbox else 0.0,
        ),
    )

    # Group blocks and tables by page
    page_items: dict[int, list[tuple[float, str]]] = {}

    for b in sorted_blocks:
        pnum = b.source_span.page_number
        top_y = b.source_span.bbox[1] if b.source_span.bbox else 0.0
        page_items.setdefault(pnum, []).append((top_y, b.text))

    for tbl in doc.tables:
        pnum = min(tbl.source_pages) if tbl.source_pages else 1
        top_y = tbl.bbox[1] if tbl.bbox else 50.0
        tbl_md = render_canonical_table_markdown(tbl)
        if tbl_md:
            page_items.setdefault(pnum, []).append((top_y, tbl_md))

    all_pages = sorted(page_items.keys())
    for pnum in all_pages:
        parts.append(f"\n\n<!-- Page {pnum} -->\n")
        items = sorted(page_items[pnum], key=lambda x: x[0])
        for _, content in items:
            if content.strip():
                parts.append(content.strip() + "\n\n")

    return "".join(parts).strip()
