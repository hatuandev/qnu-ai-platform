"""Shared PyMuPDF Geometry Helper — Real Text/Table Bounding Boxes in Percent.

Both the knowledge ``PyMuPdfParser`` and the OCR ``PyMuPDFOCRAdapter`` use this
helper so bounding boxes stay consistent: absolute PDF points are converted to
0–100 % coordinates relative to the page rectangle, matching the frontend
``DocumentBoundingBox`` contract. Only boxes with real geometry are returned;
nothing is invented.
"""

from __future__ import annotations

import logging
import re
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


def _get_bbox_coords(bbox: Any) -> tuple[float, float, float, float]:
    """Safely extract (x0, y0, x1, y1) from fitz.Rect, tuple, list or dict."""
    if hasattr(bbox, "x0"):
        return float(bbox.x0), float(bbox.y0), float(bbox.x1), float(bbox.y1)
    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    if isinstance(bbox, dict):
        return (
            float(bbox.get("x0", bbox.get("x", 0))),
            float(bbox.get("y0", bbox.get("y", 0))),
            float(bbox.get("x1", bbox.get("x", 0) + bbox.get("width", 0))),
            float(bbox.get("y1", bbox.get("y", 0) + bbox.get("height", 0))),
        )
    raise ValueError(f"Unsupported bbox format: {type(bbox)}")


def classify_text_block(text: str, top_percent: float, bottom_percent: float) -> tuple[str, str]:
    """Phân loại ngữ nghĩa của một khối văn bản dựa trên nội dung và vị trí tọa độ.

    Trả về (block_type, label):
    - header: Phần đầu văn bản (quốc hiệu, tiêu ngữ, tên trường, số hiệu) ở đỉnh trang
    - title: Tiêu đề số La Mã (I., II.), THÔNG BÁO, QUYẾT ĐỊNH, hoặc dòng in hoa toàn bộ
    - signature: Chữ ký, chức danh người ký, nơi nhận ở cuối văn bản
    - text: Đoạn văn xuôi, căn cứ pháp lý, danh mục mặc định (chuẩn Mistral Document AI)
    """
    clean = text.strip()
    if not clean:
        return "text", "Khối văn bản"

    # 1. Header (chỉ ở đầu trang <= 16% và BẮT ĐẦU bằng từ khóa hành chính / số hiệu)
    if top_percent <= 16.0 and re.match(
        r"^(?:bộ giáo dục|trường đại học|cộng hòa xã hội|độc lập\s*-\s*tự do|số\s*[:\/])",
        clean,
        re.IGNORECASE,
    ):
        return "header", "Phần đầu văn bản"

    # 2. Signature (chỉ ở cuối trang >= 65% và BẮT ĐẦU bằng chức danh người ký / nơi nhận)
    if (bottom_percent >= 68.0 or top_percent >= 65.0) and re.match(
        r"^(?:hiệu trưởng|kt\.\s*hiệu trưởng|phó hiệu trưởng|trưởng phòng|giám đốc|chủ tịch|tl\.\s*hiệu trưởng|nơi nhận\s*[:\/])",
        clean,
        re.IGNORECASE,
    ):
        return "signature", "Chữ ký / Nơi nhận"

    # 3. Title (tiêu đề đề mục lớn, số La Mã, THÔNG BÁO, QUYẾT ĐỊNH, in hoa)
    # 3.1. Số La Mã: "I. THÔNG TIN CHUNG", "II. TUYỂN SINH..."
    if re.match(r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+[A-ZÀ-Ỹ]", clean):
        return "title", "Tiêu đề"

    # 3.2. Tiêu đề văn bản chỉ đạo
    if re.match(
        r"^(?:THÔNG BÁO|QUYẾT ĐỊNH|KẾ HOẠCH|QUY ĐỊNH|HƯỚNG DẪN)\b",
        clean,
        re.IGNORECASE,
    ):
        return "title", "Tiêu đề"

    # 3.3. Dòng in hoa toàn bộ ngắn (< 120 ký tự, có ít nhất 8 chữ cái)
    first_line = clean.split("\n")[0].strip()
    letters = [c for c in first_line if c.isalpha()]
    if 8 <= len(letters) <= 100 and len(first_line) <= 120:
        upper_letters = [c for c in letters if c.isupper()]
        if len(upper_letters) / len(letters) >= 0.8:
            return "title", "Tiêu đề"

    # 4. Table continuation row (hàng dữ liệu của bảng bị rớt sang trang sau do ngắt trang)
    # Đặc điểm: ở đầu trang <= 25%, chiều cao nhỏ <= 12%, chứa mã ngành 7 số hoặc mã tổ hợp môn
    block_height = bottom_percent - top_percent
    has_table_signals = bool(
        re.search(r"\b7\d{6}\b", clean)
        or re.search(
            r"\b(?:A00|A01|A02|B00|B08|C00|C01|D01|D07|D08|D14|D15|H00|M00|M01|N00|T00|V00)\b",
            clean,
        )
    )
    if top_percent <= 25.0 and block_height <= 12.0 and has_table_signals:
        return "table", "Bảng dữ liệu (tiếp nối)"

    # 5. Mặc định là Text (bao gồm cả các đoạn văn xuôi, căn cứ, danh mục, thuyết minh)
    return "text", "Khối văn bản"


def extract_page_blocks(page: Any, max_text_blocks: int = 60) -> list[dict[str, Any]]:
    """Extract real text/table blocks with percent bboxes from a fitz Page."""
    blocks: list[dict[str, Any]] = []
    page_rect = page.rect
    page_width = float(page_rect.width)
    page_height = float(page_rect.height)

    # 1. Trích xuất tables trước để lấy bbox và dữ liệu bảng Markdown
    table_bboxes: list[tuple[float, float, float, float]] = []
    try:
        tables = page.find_tables()
        table_list = list(getattr(tables, "tables", []) or [])
    except Exception:
        table_list = []

    for tab_idx, tab in enumerate(table_list):
        try:
            bbox = tab.bbox
            tx0, ty0, tx1, ty1 = _get_bbox_coords(bbox)
            table_bboxes.append((tx0, ty0, tx1, ty1))
            coords = to_percent(tx0, ty0, tx1, ty1, page_width, page_height)
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
        for tx0, ty0, tx1, ty1 in table_bboxes:
            if bx0 >= tx0 - 2 and by0 >= ty0 - 2 and bx1 <= tx1 + 2 and by1 <= ty1 + 2:
                is_inside_tbl = True
                break
        if is_inside_tbl:
            continue

        if len(blocks) >= max_text_blocks + len(table_list):
            break

        coords = to_percent(
            block[0], block[1], block[2], block[3], page_width, page_height
        )
        b_type, b_label = classify_text_block(
            raw_txt, coords["y"], coords["y"] + coords["height"]
        )

        blocks.append(
            {
                "type": b_type,
                "coordinates": coords,
                "label": f"{b_label} {idx + 1}" if b_type == "text" else b_label,
                "text": raw_txt,
                "content_snippet": snippet[:160],
            }
        )

    return blocks
