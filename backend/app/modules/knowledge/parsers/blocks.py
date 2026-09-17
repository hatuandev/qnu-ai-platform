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


def extract_page_blocks(page: Any, max_text_blocks: int = 60) -> list[dict[str, Any]]:
    """Extract real text/table blocks with percent bboxes from a fitz Page."""
    blocks: list[dict[str, Any]] = []
    page_rect = page.rect
    page_width = float(page_rect.width)
    page_height = float(page_rect.height)

    try:
        raw_blocks = page.get_text("blocks") or []
    except Exception:
        raw_blocks = []
    for idx, block in enumerate(sorted(raw_blocks, key=lambda b: (b[1], b[0]))):
        if len(block) < 5:
            continue
        snippet = str(block[4] or "").strip().replace("\n", " ")
        if not snippet:
            continue
        if len(blocks) >= max_text_blocks:
            break
        blocks.append(
            {
                "type": "text",
                "coordinates": to_percent(
                    block[0], block[1], block[2], block[3], page_width, page_height
                ),
                "label": f"Khối văn bản {idx + 1}",
                "content_snippet": snippet[:160],
            }
        )

    try:
        tables = page.find_tables()
        table_list = list(getattr(tables, "tables", []) or [])
    except Exception:
        table_list = []
    for tab_idx, tab in enumerate(table_list):
        try:
            bbox = tab.bbox
            coords = to_percent(
                bbox.x0, bbox.y0, bbox.x1, bbox.y1, page_width, page_height
            )
        except Exception as exc:
            logger.debug("Skipping table with unreadable bbox: %s", exc)
            continue
        blocks.append(
            {
                "type": "table",
                "coordinates": coords,
                "label": f"Bảng {tab_idx + 1}",
                "content_snippet": "",
            }
        )
    return blocks
