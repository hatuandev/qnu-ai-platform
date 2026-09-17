"""Shared PyMuPDF Geometry Helper — Real Text/Table Bounding Boxes in Percent.

Both the knowledge ``PyMuPdfParser`` and the OCR ``PyMuPDFOCRAdapter`` use this
helper so bounding boxes stay consistent: absolute PDF points are converted to
0–100 % coordinates relative to the page rectangle, matching the frontend
``DocumentBoundingBox`` contract. Only boxes with real geometry are returned;
nothing is invented.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def to_percent(
    x0: float, y0: float, x1: float, y1: float, page_width: float, page_height: float
) -> dict[str, float]:
    """Convert absolute PDF points to rounded 0–100 % coordinates."""
    page_width = float(page_width) or 1.0
    page_height = float(page_height) or 1.0
    left = max(0.0, min(float(x0) / page_width * 100.0, 100.0))
    top = max(0.0, min(float(y0) / page_height * 100.0, 100.0))
    right = max(0.0, min(float(x1) / page_width * 100.0, 100.0))
    bottom = max(0.0, min(float(y1) / page_height * 100.0, 100.0))
    return {
        "x": round(left, 2),
        "y": round(top, 2),
        "width": round(max(right - left, 0.0), 2),
        "height": round(max(bottom - top, 0.0), 2),
    }


def _format_table_markdown(rows: list[list[Any]]) -> str:
    """Chuyển đổi ma trận ô bảng thành Markdown Table chuẩn GitHub Flavored Markdown."""
    if not rows:
        return ""
    clean_rows: list[list[str]] = []
    for row in rows:
        if not row:
            continue
        r_cells = [str(c or "").strip().replace("|", "\\|").replace("\n", " ") for c in row]
        if any(r_cells):
            clean_rows.append(r_cells)

    if not clean_rows:
        return ""

    max_cols = max(len(r) for r in clean_rows)
    if max_cols == 0:
        return ""

    padded_rows = [r + [""] * (max_cols - len(r)) for r in clean_rows]
    raw_headers = padded_rows[0]
    clean_headers = [h if h else f"Cột {idx + 1}" for idx, h in enumerate(raw_headers)]

    lines = [
        "| " + " | ".join(clean_headers) + " |",
        "| " + " | ".join([":---:" if idx == 0 and max_cols > 3 else ":---" for idx in range(max_cols)]) + " |",
    ]
    for r in padded_rows[1:]:
        lines.append("| " + " | ".join(r) + " |")

    return "\n".join(lines)


def extract_page_blocks(page: Any, max_text_blocks: int = 60) -> list[dict[str, Any]]:
    """Extract real text/table blocks with percent bboxes from a fitz Page."""
    blocks: list[dict[str, Any]] = []
    page_rect = page.rect
    page_width = float(page_rect.width)
    page_height = float(page_rect.height)

    # 1. Trích xuất tables trước để lấy bbox và dữ liệu bảng Markdown
    table_bboxes: list[Any] = []
    try:
        tables = page.find_tables()
        table_list = list(getattr(tables, "tables", []) or [])
    except Exception:
        table_list = []

    for tab_idx, tab in enumerate(table_list):
        try:
            bbox = tab.bbox
            table_bboxes.append(bbox)
            coords = to_percent(
                bbox.x0, bbox.y0, bbox.x1, bbox.y1, page_width, page_height
            )
        except Exception as exc:
            logger.debug("Skipping table with unreadable bbox: %s", exc)
            continue

        rows = []
        try:
            rows = tab.extract() or []
        except Exception:
            rows = []
        md_table = _format_table_markdown(rows) if rows else ""
        first_hdr = (
            " | ".join(str(c or "").strip() for c in rows[0] if str(c or "").strip())
            if rows and rows[0]
            else ""
        )

        blocks.append(
            {
                "type": "table",
                "coordinates": coords,
                "label": f"Bảng {tab_idx + 1}",
                "text": md_table,
                "content_snippet": f"Bảng: {first_hdr}" if first_hdr else md_table[:160],
            }
        )

    # 2. Trích xuất text blocks (loại trừ các block nằm trong table)
    try:
        raw_blocks = page.get_text("blocks") or []
    except Exception:
        raw_blocks = []
    for idx, block in enumerate(sorted(raw_blocks, key=lambda b: (b[1], b[0]))):
        if len(block) < 5:
            continue
        # Bỏ qua image blocks
        if len(block) >= 7 and block[6] != 0:
            continue
        raw_txt = str(block[4] or "").strip()
        snippet = raw_txt.replace("\n", " ")
        if not snippet:
            continue

        # Kiểm tra xem text block có nằm trong bảng không
        bx0, by0, bx1, by1 = float(block[0]), float(block[1]), float(block[2]), float(block[3])
        is_inside_tbl = False
        for tb in table_bboxes:
            if bx0 >= tb.x0 - 2 and by0 >= tb.y0 - 2 and bx1 <= tb.x1 + 2 and by1 <= tb.y1 + 2:
                is_inside_tbl = True
                break
        if is_inside_tbl:
            continue

        if len(blocks) >= max_text_blocks + len(table_list):
            break
        blocks.append(
            {
                "type": "text",
                "coordinates": to_percent(
                    block[0], block[1], block[2], block[3], page_width, page_height
                ),
                "label": f"Khối văn bản {idx + 1}",
                "text": raw_txt,
                "content_snippet": snippet[:160],
            }
        )

    return blocks
