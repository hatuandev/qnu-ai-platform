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
    clean_headers = [h if h else "" for h in raw_headers]

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

    # 0. Header / Footer Pagination (ở đỉnh trang <= 8% hoặc đáy trang >= 88%, là số trang đơn độc như "2", "15", "Trang 2/22")
    if (top_percent <= 8.0 or top_percent >= 88.0) and re.fullmatch(
        r"(?:Trang\s+)?\d{1,3}(?:\s*/\s*\d{1,3})?", clean, re.IGNORECASE
    ):
        return "footer", "Số trang"

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
    # và tuyệt đối không phải là đoạn văn bản quy định hành chính (a., b., c., Trường hợp...)
    block_height = bottom_percent - top_percent
    has_table_signals = bool(
        re.search(r"\b7\d{6}\b", clean)
        or re.search(
            r"\b(?:A00|A01|A02|B00|B08|C00|C01|D01|D07|D08|D14|D15|H00|M00|M01|N00|T00|V00)\b",
            clean,
        )
    )
    is_admin_paragraph = bool(
        re.match(
            r"^(?:[a-z]\.|\d+\.|\+|-\s|Trường hợp|Theo quy định|Căn cứ)\b",
            clean,
            re.IGNORECASE,
        )
    )
    if not is_admin_paragraph and top_percent <= 25.0 and block_height <= 12.0 and has_table_signals:
        return "table", "Bảng dữ liệu (tiếp nối)"

    # 5. Mặc định là Text (bao gồm cả các đoạn văn xuôi, căn cứ, danh mục, thuyết minh)
    return "text", "Khối văn bản"


def _rect_area(r: tuple[float, float, float, float]) -> float:
    """Calculate width * height of a bounding box."""
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _rect_intersection(
    r1: tuple[float, float, float, float], r2: tuple[float, float, float, float]
) -> float:
    """Calculate intersection area between two bounding boxes."""
    ix0 = max(r1[0], r2[0])
    iy0 = max(r1[1], r2[1])
    ix1 = min(r1[2], r2[2])
    iy1 = min(r1[3], r2[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def suppress_nested_tables(table_list: list[Any]) -> list[Any]:
    """Remove sub-tables that are substantially enclosed (>= 70%) within a larger parent table."""
    if len(table_list) <= 1:
        return table_list

    table_data = []
    for tab in table_list:
        try:
            bbox = _get_bbox_coords(tab.bbox)
            area = _rect_area(bbox)
            table_data.append({"tab": tab, "bbox": bbox, "area": area})
        except Exception as exc:
            logger.debug("Skipping unreadable table bbox in suppression: %s", exc)
            continue

    keep = [True] * len(table_data)
    for i, t_i in enumerate(table_data):
        if not keep[i]:
            continue
        for j, t_j in enumerate(table_data):
            if i == j or not keep[j]:
                continue
            # If t_j is larger than t_i and contains >= 70% of t_i area
            if t_j["area"] > t_i["area"]:
                inter = _rect_intersection(t_i["bbox"], t_j["bbox"])
                if t_i["area"] > 0 and (inter / t_i["area"]) >= 0.70:
                    keep[i] = False
                    break

    return [t["tab"] for i, t in enumerate(table_data) if keep[i]]


def detect_open_top_lines(page: Any) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Phát hiện các đường kẻ dọc ở đỉnh trang bị thiếu đường kẻ ngang trên cùng do ngắt trang.

    Khi bảng biểu kéo dài qua nhiều trang (multi-page table continuation), trang tiếp nối
    thường không có đường kẻ ngang ở đỉnh (open-top). Thuật toán PyMuPDF mặc định yêu cầu
    khung khép kín nên sẽ bỏ qua hàng đầu tiên. Hàm này tạo một đường kẻ ngang ảo (add_lines)
    nối qua các đường kẻ dọc tại đỉnh trang để PyMuPDF nhận diện trọn vẹn 100% các hàng tiếp nối.
    """
    add_lines: list[tuple[tuple[float, float], tuple[float, float]]] = []
    try:
        drawings = page.get_drawings() or []
        page_height = float(page.rect.height)
        v_lines: list[Any] = []
        for d in drawings:
            r = d.get("rect")
            if r and (r.x1 - r.x0) <= 4.0 and (r.y1 - r.y0) >= 8.0:
                v_lines.append(r)

        top_v = [vl for vl in v_lines if vl.y0 < page_height * 0.35]
        if top_v:
            min_y0 = min(vl.y0 for vl in top_v)
            at_min = [vl for vl in top_v if abs(vl.y0 - min_y0) <= 2.5]
            if len(at_min) >= 2:
                min_x = min(vl.x0 for vl in at_min)
                max_x = max(vl.x1 for vl in at_min)
                has_h = any(
                    d.get("rect")
                    and abs(d["rect"].y0 - min_y0) <= 2.5
                    and (d["rect"].x1 - d["rect"].x0) >= 20.0
                    for d in drawings
                )
                if not has_h and (max_x - min_x) >= 100.0:
                    add_lines.append(((min_x, min_y0), (max_x, min_y0)))
    except Exception as exc:
        logger.debug("detect_open_top_lines error: %s", exc)
    return add_lines


def find_page_tables(page: Any, **kwargs: Any) -> Any:
    """Gọi page.find_tables() kèm cơ chế tự động bù đường kẻ biên cho bảng ngắt trang (open-top)."""
    if "add_lines" not in kwargs:
        missing_lines = detect_open_top_lines(page)
        if missing_lines:
            kwargs["add_lines"] = missing_lines
    try:
        return page.find_tables(**kwargs)
    except Exception as exc:
        logger.debug("find_page_tables failed: %s", exc)
        return getattr(page, "find_tables", lambda **k: None)()


def _rescue_open_top_table(
    page: Any, bbox: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """Mở rộng bounding box của bảng ở đỉnh trang nếu có đường kẻ hoặc text block tiếp giáp phía trên."""
    tx0, ty0, tx1, ty1 = bbox
    page_height = float(page.rect.height)
    if ty0 > page_height * 0.35:
        return bbox

    raw_blocks = page.get_text("blocks") or []
    bridging_y0: float | None = None
    for b in raw_blocks:
        if len(b) < 5:
            continue
        bx0, by0, bx1, by1 = float(b[0]), float(b[1]), float(b[2]), float(b[3])
        if (
            bx1 >= tx0 - 10.0
            and bx0 <= tx1 + 10.0
            and by0 < ty0 - 5.0
            and by1 > ty0 + 5.0
        ):
            bridging_y0 = by0 if bridging_y0 is None else min(bridging_y0, by0)

    line_y0: float | None = None
    try:
        drawings = page.get_drawings() or []
        for d in drawings:
            dr = d.get("rect")
            if (
                dr
                and dr.y1 <= ty0 + 2.0
                and dr.y0 < ty0 - 5.0
                and (dr.x1 - dr.x0) <= 4.0
                and tx0 - 5.0 <= dr.x0 <= tx1 + 5.0
            ):
                line_y0 = dr.y0 if line_y0 is None else min(line_y0, dr.y0)
    except Exception:
        pass

    candidate_y0: float | None = None
    if line_y0 is not None:
        candidate_y0 = line_y0
    elif bridging_y0 is not None:
        candidate_y0 = bridging_y0 - 2.0

    if candidate_y0 is not None and candidate_y0 < ty0 and (ty0 - candidate_y0) <= 120.0:
        return (tx0, max(0.0, candidate_y0), tx1, ty1)

    return bbox


def extract_page_blocks(page: Any, max_text_blocks: int = 60) -> list[dict[str, Any]]:
    """Extract real text/table blocks with percent bboxes from a fitz Page."""
    blocks: list[dict[str, Any]] = []
    page_rect = page.rect
    page_width = float(page_rect.width)
    page_height = float(page_rect.height)

    # 1. Trích xuất tables và lọc khử bảng con lồng trong bảng cha (Nested Table Suppression)
    table_bboxes: list[tuple[float, float, float, float]] = []
    try:
        raw_tables = find_page_tables(page)
        raw_list = list(getattr(raw_tables, "tables", []) or [])
        table_list = suppress_nested_tables(raw_list)
    except Exception:
        table_list = []

    for tab_idx, tab in enumerate(table_list):
        try:
            bbox = _rescue_open_top_table(page, _get_bbox_coords(tab.bbox))
            tx0, ty0, tx1, ty1 = bbox
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

    # 2. Trích xuất text blocks (loại trừ các block nằm trong table, kể cả bảng song song)
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

        # Kiểm tra xem text block có nằm trong bảng không (tính tổng diện tích giao cắt đa bảng)
        bx0, by0, bx1, by1 = float(block[0]), float(block[1]), float(block[2]), float(block[3])
        b_rect = (bx0, by0, bx1, by1)
        b_area = _rect_area(b_rect)

        is_inside_tbl = False
        if b_area > 0 and table_bboxes:
            total_table_inter = sum(_rect_intersection(b_rect, tb) for tb in table_bboxes)
            if (total_table_inter / b_area) >= 0.40:
                is_inside_tbl = True

            if not is_inside_tbl:
                cx = (bx0 + bx1) / 2.0
                cy = (by0 + by1) / 2.0
                for tx0, ty0, tx1, ty1 in table_bboxes:
                    if tx0 - 3.0 <= cx <= tx1 + 3.0 and ty0 - 3.0 <= cy <= ty1 + 3.0:
                        is_inside_tbl = True
                        break

            # Xử lý khối văn bản cắt ngang biên giới bảng (ví dụ: chân bảng nối với Nơi nhận / Chữ ký)
            if not is_inside_tbl and total_table_inter > 0:
                import fitz

                for tx0, ty0, tx1, ty1 in table_bboxes:
                    inter_area = _rect_intersection(b_rect, (tx0, ty0, tx1, ty1))
                    if inter_area > 0:
                        # Khối bắt đầu từ trong bảng và kéo dài xuống dưới bảng
                        if ty0 <= by0 < ty1 < by1:
                            clipped_txt = page.get_text("text", clip=fitz.Rect(bx0, ty1, bx1, by1)).strip()
                            if clipped_txt:
                                raw_txt = clipped_txt
                                snippet = raw_txt.replace("\n", " ")
                                by0 = ty1
                                b_rect = (bx0, by0, bx1, by1)
                            else:
                                is_inside_tbl = True
                            break
                        # Khối bắt đầu phía trên bảng và ăn vào trong bảng
                        elif by0 < ty0 < by1 <= ty1:
                            clipped_txt = page.get_text("text", clip=fitz.Rect(bx0, by0, bx1, ty0)).strip()
                            if clipped_txt:
                                raw_txt = clipped_txt
                                snippet = raw_txt.replace("\n", " ")
                                by1 = ty0
                                b_rect = (bx0, by0, bx1, by1)
                            else:
                                is_inside_tbl = True
                            break

        if is_inside_tbl:
            continue

        if len(blocks) >= max_text_blocks + len(table_list):
            break

        coords = to_percent(
            bx0, by0, bx1, by1, page_width, page_height
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

    # Sắp xếp các khối theo tọa độ đọc tự nhiên (từ trên xuống dưới, từ trái sang phải)
    blocks.sort(key=lambda b: (b["coordinates"]["y"], b["coordinates"]["x"]))
    return blocks
