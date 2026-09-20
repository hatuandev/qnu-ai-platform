"""Smart Document Layout & Table Detector using Computer Vision (OpenCV).

Precisely identifies:
1. Exact table bounding boxes via morphological line extraction (horizontal & vertical kernels).
2. Red stamp & seal detection via HSV color masking.
3. Paragraph and text region segmentation (preventing tables from bleeding into text).
4. Image pre-processing (auto-deskew, contrast enhancement via CLAHE).
"""

from __future__ import annotations

import re
from typing import Any

import cv2
import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class SmartLayoutDetector:
    """Extracts high-precision bounding boxes for tables, text, stamps, and headers."""

    def deskew_image(self, img: np.ndarray) -> tuple[np.ndarray, float]:
        """Detect and correct document skew angle (0 to 5 degrees) using minAreaRect."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return img, 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        # If angle is negligible or extreme (>15 deg), don't rotate
        if abs(angle) < 0.3 or abs(angle) > 15.0:
            return img, 0.0

        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated, angle

    def enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) to sharpen scan text."""
        if len(img.shape) == 3:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_chan, a_chan, b_chan = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l_chan)
            enhanced = cv2.merge((l_enhanced, a_chan, b_chan))
            return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(img)

    def detect_layout_regions(
        self,
        image_input: bytes | str | np.ndarray,
        markdown_text: str = "",
        page_number: int = 1,
        fitz_page: Any = None,
    ) -> list[dict[str, Any]]:
        """Compute precise bounding boxes for the given page image.

        Supports hybrid geometry detection when fitz_page is provided (vector-precise),
        with fallback to OpenCV morphological & HSV detection for scanned images.

        Returns a list of region dicts:
        [{
            "type": "table" | "header" | "text" | "title" | "signature" | "list",
            "label": str,
            "text": str,
            "top": float,     # Percentage (0-100)
            "left": float,    # Percentage (0-100)
            "width": float,   # Percentage (0-100)
            "height": float,  # Percentage (0-100)
        }]
        """
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
        elif isinstance(image_input, bytes):
            nparr = np.frombuffer(image_input, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            return []

        if img is None:
            return []

        h, w = img.shape[:2]

        # 1. Detect Red Stamp / Legal Seal (HSV color segmentation)
        stamps, red_mask = self._detect_red_stamps(img, w, h)

        # 2. If a fitz PDF page is provided, perform vector-precise hybrid layout analysis
        if fitz_page is not None:
            try:
                hybrid_regions = self._detect_hybrid_pdf_regions(
                    fitz_page=fitz_page,
                    stamps=stamps,
                    page_number=page_number,
                )
                if hybrid_regions:
                    return hybrid_regions
            except Exception as exc:
                logger.warning("hybrid_layout_detection_fallback", error=str(exc))

        # 3. Fallback: Detect Tables via Morphological Grid Line Extraction
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        tables, text_thresh = self._detect_tables(gray, w, h, red_mask)

        # 4. Detect Text, Header, Title, List Regions via Projection Profile
        text_regions = self._detect_text_regions(
            text_thresh, w, h, tables, markdown_text=markdown_text, page_number=page_number
        )

        # 5. Combine all detected visual regions
        regions: list[dict[str, Any]] = []
        regions.extend(tables)

        for tr in text_regions:
            tx1 = int((tr["left"] / 100.0) * w)
            ty1 = int((tr["top"] / 100.0) * h)
            tx2 = int(((tr["left"] + tr["width"]) / 100.0) * w)
            ty2 = int(((tr["top"] + tr["height"]) / 100.0) * h)

            is_inside_table = False
            for t in tables:
                x_overlap = max(0, min(tx2, t["raw_x"] + t["raw_w"]) - max(tx1, t["raw_x"]))
                y_overlap = max(0, min(ty2, t["raw_y"] + t["raw_h"]) - max(ty1, t["raw_y"]))
                overlap_area = x_overlap * y_overlap
                tr_area = max(1, (tx2 - tx1) * (ty2 - ty1))
                table_area = max(1, t["raw_w"] * t["raw_h"])
                if (overlap_area / tr_area > 0.35) or (overlap_area / table_area > 0.35):
                    is_inside_table = True
                    break
            if not is_inside_table:
                regions.append(tr)

        # 6. Attach Signatures / Stamps
        for s in stamps:
            regions.append({
                "type": "signature",
                "label": "signature",
                "text": s.get("text", ""),
                "top": s["top"],
                "left": s["left"],
                "width": s["width"],
                "height": s["height"],
            })

        # 7. Suppress duplicate / heavily overlapping boxes
        regions = self._suppress_overlapping_boxes(regions)
        regions.sort(key=lambda r: (r["top"], r["left"]))
        return regions

    def _detect_red_stamps(self, img: np.ndarray, w: int, h: int) -> tuple[list[dict[str, Any]], np.ndarray]:
        """Detect circular/oval official red stamps with high precision and adaptive density."""
        stamps: list[dict[str, Any]] = []
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([12, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([165, 50, 50]), np.array([180, 255, 255]))
        red_mask = cv2.add(mask1, mask2)

        try:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (12, 12))
            dilated = cv2.dilate(red_mask, kernel, iterations=2)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                x, y, bw, bh = cv2.boundingRect(cnt)
                area = bw * bh
                if bw >= 40 and bh >= 40 and area >= 2000:
                    roi = red_mask[y:y+bh, x:x+bw]
                    density = np.count_nonzero(roi) / float(area)
                    # Official circular seals have hollow centers; large seals have lower red density (0.04 - 0.07)
                    min_density = 0.04 if area >= 5000 else 0.06
                    if density >= min_density:
                        stamps.append({
                            "type": "signature",
                            "label": "signature",
                            "text": "",
                            "top": round((y / h) * 100, 1),
                            "left": round((x / w) * 100, 1),
                            "width": round((bw / w) * 100, 1),
                            "height": round((bh / h) * 100, 1),
                            "raw_y": y,
                            "raw_h": bh,
                            "raw_x": x,
                            "raw_w": bw,
                        })
        except Exception as exc:
            logger.warning("red_stamp_detection_failed", error=str(exc))

        return stamps, red_mask

    def _detect_tables(
        self, gray: np.ndarray, w: int, h: int, red_mask: np.ndarray | None = None
    ) -> tuple[list[dict[str, Any]], np.ndarray]:
        """Detect tables by extracting perpendicular grid lines."""
        tables: list[dict[str, Any]] = []
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        if red_mask is not None:
            thresh[red_mask > 0] = 0

        try:
            thresh_h = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1)))
            h_len = max(28, int(w / 34))
            h_k = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1))
            h_lines = cv2.morphologyEx(thresh_h, cv2.MORPH_OPEN, h_k, iterations=1)

            thresh_v = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))
            v_len = max(25, int(h / 45))
            v_k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len))
            v_lines = cv2.morphologyEx(thresh_v, cv2.MORPH_OPEN, v_k, iterations=1)

            intersections = cv2.bitwise_and(h_lines, v_lines)
            table_grid = cv2.add(h_lines, v_lines)

            merged_grid = cv2.morphologyEx(table_grid, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 3)))
            contours, _ = cv2.findContours(merged_grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            raw_boxes = []
            for cnt in contours:
                x, y, bw, bh = cv2.boundingRect(cnt)
                if bw > w * 0.25 and bh > h * 0.035:
                    roi_h = h_lines[y:y+bh, x:x+bw]
                    roi_v = v_lines[y:y+bh, x:x+bw]
                    roi_int = intersections[y:y+bh, x:x+bw]

                    h_pix = np.count_nonzero(roi_h)
                    v_pix = np.count_nonzero(roi_v)
                    int_pix = np.count_nonzero(roi_int)

                    if h_pix >= 150 and v_pix >= 100 and int_pix >= 4:
                        h_cnts, _ = cv2.findContours(roi_h, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        max_h_span = max([cv2.boundingRect(hc)[2] for hc in h_cnts], default=0)

                        v_cnts, _ = cv2.findContours(roi_v, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        max_v_span = max([cv2.boundingRect(vc)[3] for vc in v_cnts], default=0)

                        if max_h_span >= max(90, int(bw * 0.25)) and max_v_span >= min(40, int(bh * 0.35)):
                            raw_boxes.append([x, y, x + bw, y + bh])

            merged = True
            while merged:
                merged = False
                new_boxes = []
                skip: set[int] = set()
                for i in range(len(raw_boxes)):
                    if i in skip:
                        continue
                    b1 = raw_boxes[i]
                    x1, y1, x2, y2 = b1
                    for j in range(i + 1, len(raw_boxes)):
                        if j in skip:
                            continue
                        b2 = raw_boxes[j]
                        bx1, by1, bx2, by2 = b2

                        y_overlap = max(0, min(y2, by2) - max(y1, by1))
                        min_h = min(y2 - y1, by2 - by1)
                        x_dist = max(0, max(x1, bx1) - min(x2, bx2))

                        if min_h > 0 and (y_overlap / min_h > 0.60) and x_dist < int(w * 0.12):
                            x1 = min(x1, bx1)
                            y1 = min(y1, by1)
                            x2 = max(x2, bx2)
                            y2 = max(y2, by2)
                            skip.add(j)
                            merged = True
                    new_boxes.append([x1, y1, x2, y2])
                raw_boxes = new_boxes

            for b in raw_boxes:
                x1, y1, x2, y2 = b
                bw = x2 - x1
                bh = y2 - y1
                if bw > w * 0.30 and bh > h * 0.04:
                    tables.append({
                        "type": "table",
                        "label": "table",
                        "text": "",
                        "content_snippet": "",
                        "top": round((y1 / h) * 100, 1),
                        "left": round((x1 / w) * 100, 1),
                        "width": round((bw / w) * 100, 1),
                        "height": round((bh / h) * 100, 1),
                        "raw_x": x1,
                        "raw_y": y1,
                        "raw_w": bw,
                        "raw_h": bh,
                        "raw_bottom": y2,
                    })
        except Exception as exc:
            logger.warning("table_detection_failed", error=str(exc))

        tables.sort(key=lambda t: t["raw_y"])

        text_thresh = thresh.copy()
        for t in tables:
            y1 = max(0, t["raw_y"] - 3)
            y2 = min(h, t["raw_y"] + t["raw_h"] + 3)
            x1 = max(0, t["raw_x"] - 3)
            x2 = min(w, t["raw_x"] + t["raw_w"] + 3)
            text_thresh[y1:y2, x1:x2] = 0

        return tables, text_thresh

    @staticmethod
    def _is_doc_or_section_title(text: str) -> bool:
        """Nhận diện tiêu đề văn bản, phần La Mã (I., II.), hoặc mục số chính không có dấu hai chấm."""
        first_line = text.strip().split("\n")[0].strip()
        # Roman numerals I., II., III.
        if re.match(r"^(?:[IVXLCDM]+\.)\s+[A-ZÀ-ỸĐ]", first_line):
            return True
        # Multi-level numbered section e.g. '1.1. Mục đích', '1.1 Mục đích'
        if re.match(r"^\d+\.\d+\.?\s+[A-ZÀ-ỸĐ]", first_line):
            return True
        # Document title types
        if re.match(
            r"^(?:KẾ HOẠCH|KE HOACH|QUYẾT ĐỊNH|QUYET DINH|THÔNG BÁO|THONG BAO|PHƯƠNG ÁN|PHUONG AN|ĐỀ ÁN|DE AN|TỜ TRÌNH|TO TRINH|BÁO CÁO|BAO CAO|HƯỚNG DẪN|HUONG DAN|QUY ĐỊNH|QUY DINH|QUY CHẾ|QUY CHE)\b",
            first_line,
            re.IGNORECASE,
        ):
            return True
        # Section titles e.g. '1. Trung tâm Số và Học liệu', '6. Tổ chức tuyển sinh'
        if re.match(r"^\d+\.\s+[A-ZÀ-ỸĐ][a-zA-ZÀ-ỸĐà-ỹđ\s,\-]+$", first_line) and len(first_line) < 60 and ":" not in first_line:
            return True
        # Phase subtitles e.g. 'Đợt 1:', 'Đợt 2:', 'Ưu tiên xét tuyển:'
        return bool(re.match(r"^(?:Đợt \d+:|Dot \d+:|Ưu tiên xét tuyển:|Uu tien xet tuyen:)", first_line, re.IGNORECASE))

    @classmethod
    def _is_list_marker(cls, text: str) -> bool:
        """Nhận diện marker danh sách: +, -, *, •, –, —, 1., 1), a., a), (1), (a)... hoặc Nơi nhận:"""
        s = text.strip()
        if not s:
            return False
        first_line = s.split("\n")[0].strip()
        first_lower = first_line.lower()
        if first_lower.startswith(("nơi nhận:", "noi nhan:")):
            return True
        # Bullets +, -, *, •, –, —
        if re.match(r"^[\+\-\*•\–\—]\s*", first_line):
            return True
        # a), b), c)... or a., b., c.... (including đ, Đ)
        if re.match(r"^[a-zA-ZđĐ][\.\)]\s*", first_line):
            return True
        # (1), (2), (a), (b)...
        if re.match(r"^\([0-9a-zA-ZđĐ]+\)\s*", first_line):
            return True
        # 1), 2), 3)...
        if re.match(r"^\d+\)\s*", first_line):
            return True
        # 1., 2., 3. numbered lists
        return bool(re.match(r"^\d+\.\s+", first_line))

    @staticmethod
    def _format_table_markdown(rows: list[list[Any]]) -> str:
        """Chuyển đổi ma trận ô bảng thành Markdown Table chuẩn GitHub Flavored Markdown."""
        if not rows:
            return ""
        clean_rows: list[list[str]] = []
        for row in rows:
            if not row:
                continue
            r_cells = [str(c or "").strip().replace("|", "\\|").replace("\n", " ") for c in row]
            if any(r_cells):  # Bỏ qua hàng hoàn toàn rỗng
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

    def _detect_hybrid_pdf_regions(
        self,
        fitz_page: Any,
        stamps: list[dict[str, Any]],
        page_number: int = 1,
    ) -> list[dict[str, Any]]:
        """Vector-precise layout extraction from PyMuPDF page combined with HSV stamps.

        Identifies:
        - Exact table bounding boxes via page.find_tables() and extracts actual table rows into Markdown.
        - Unified signature block on closing pages (signer title + red seal + blue ink + signer name).
        - Administrative Vietnamese semantics (Nghị định 30/2020/NĐ-CP):
          * header (letterhead/quốc hiệu page 1)
          * title (document title, Roman headings, numbered sections)
          * list (bullet items, dash items, 'Nơi nhận:')
          * text (independent paragraphs, never greedily collapsed)
        """
        import pymupdf as fitz

        page_rect = fitz_page.rect
        pw = float(page_rect.width) or 1.0
        ph = float(page_rect.height) or 1.0

        # 1. Tables via fitz_page.find_tables()
        tables: list[dict[str, Any]] = []
        try:
            from app.modules.knowledge.parsers.blocks import (
                find_page_tables,
                suppress_nested_tables,
            )

            tab_finder = find_page_tables(fitz_page)
            raw_tab_list = list(getattr(tab_finder, "tables", []) or [])
            tab_list = suppress_nested_tables(raw_tab_list)
            for t_idx, tab in enumerate(tab_list):
                x0, y0, x1, y1 = tab.bbox
                t_top = round(y0 / ph * 100, 1)
                t_left = round(x0 / pw * 100, 1)
                t_w = round((x1 - x0) / pw * 100, 1)
                t_h = round((y1 - y0) / ph * 100, 1)
                if t_w > 15.0 and t_h >= 1.5:
                    rows = []
                    try:
                        rows = tab.extract() or []
                    except Exception:
                        rows = []
                    md_table = self._format_table_markdown(rows) if rows else ""
                    if not md_table:
                        rect = fitz.Rect(x0, y0, x1, y1)
                        clipped_txt = fitz_page.get_text("text", clip=rect).strip()
                        md_table = clipped_txt or "Bảng dữ liệu"

                    first_header = ""
                    if rows and rows[0]:
                        first_header = " | ".join(str(c or "").strip() for c in rows[0] if str(c or "").strip())

                    tables.append({
                        "type": "table",
                        "label": "table",
                        "text": md_table,
                        "content_snippet": (f"Bảng: {first_header}" if first_header else md_table[:160]),
                        "top": t_top,
                        "left": t_left,
                        "width": t_w,
                        "height": t_h,
                        "bbox": (x0, y0, x1, y1),
                    })
        except Exception as exc:
            logger.debug("fitz_table_detection_skipped", error=str(exc))

        # 2. Extract vector text blocks
        raw_blocks = fitz_page.get_text("blocks") or []
        text_blocks: list[dict[str, Any]] = []
        for b in raw_blocks:
            if len(b) >= 7 and b[6] != 0:
                continue
            txt = str(b[4] or "").strip()
            if not txt:
                continue
            x0, y0, x1, y1 = float(b[0]), float(b[1]), float(b[2]), float(b[3])

            # Suppress text blocks falling inside any detected table (including side-by-side tables)
            b_area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
            is_inside_table = False
            if b_area > 0 and tables:
                total_inter = 0.0
                for t in tables:
                    tx0, ty0, tx1, ty1 = t["bbox"]
                    ix0 = max(x0, tx0)
                    iy0 = max(y0, ty0)
                    ix1 = min(x1, tx1)
                    iy1 = min(y1, ty1)
                    if ix1 > ix0 and iy1 > iy0:
                        total_inter += (ix1 - ix0) * (iy1 - iy0)
                if (total_inter / b_area) >= 0.40:
                    is_inside_table = True

                if not is_inside_table:
                    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                    for t in tables:
                        tx0, ty0, tx1, ty1 = t["bbox"]
                        if tx0 - 5.0 <= cx <= tx1 + 5.0 and ty0 - 3.0 <= cy <= ty1 + 3.0:
                            is_inside_table = True
                            break

            if not is_inside_table:
                text_blocks.append({
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "text": txt,
                    "top": round(y0 / ph * 100, 1),
                    "left": round(x0 / pw * 100, 1),
                    "width": round((x1 - x0) / pw * 100, 1),
                    "height": round((y1 - y0) / ph * 100, 1),
                })

        # If no text blocks at all, return empty to fall back to pure CV
        if not text_blocks and not tables:
            return []

        # 3. Unify Signatures (Stamps + Signer Title + Signer Name)
        signatures: list[dict[str, Any]] = []
        used_text_indices: set[int] = set()

        for s in stamps:
            s_top = float(s["top"])
            s_left = float(s["left"])
            s_width = float(s["width"])
            s_height = float(s["height"])
            s_bottom = s_top + s_height
            s_right = s_left + s_width

            title_block = None
            title_idx = None
            name_block = None
            name_idx = None

            # Find signer title near stamp (within 12% above or 8% overlapping stamp top)
            for idx, tb in enumerate(text_blocks):
                tb_top = tb["top"]
                tb_left = tb["left"]
                if tb_left >= 40.0 and (s_top - 12.0) <= tb_top <= (s_top + 8.0):
                    txt_upper = tb["text"].upper()
                    if any(kw in txt_upper for kw in [
                        "HIỆU TRƯỞNG", "HIEU TRUONG",
                        "PHÓ HIỆU TRƯỞNG", "PHO HIEU TRUONG",
                        "GIÁM ĐỐC", "GIAM DOC",
                        "PHÓ GIÁM ĐỐC", "PHO GIAM DOC",
                        "TRƯỞNG PHÒNG", "TRUONG PHONG",
                        "PHÓ TRƯỞNG PHÒNG", "PHO TRUONG PHONG",
                        "TRƯỞNG KHOA", "TRUONG KHOA",
                        "CHỦ TỊCH", "CHU TICH",
                        "KT. HIỆU TRƯỞNG", "KT. HIEU TRUONG",
                        "TL. HIỆU TRƯỞNG", "TL. HIEU TRUONG",
                        "TUQ. HIỆU TRƯỞNG", "TUQ. HIEU TRUONG",
                    ]):
                        title_block = tb
                        title_idx = idx
                        break

            # Find signer name near/below stamp (within 8% above stamp bottom to 16% below stamp bottom)
            for idx, tb in enumerate(text_blocks):
                tb_bottom = tb["top"] + tb["height"]
                tb_left = tb["left"]
                if tb_left >= 40.0 and (s_bottom - 8.0) <= tb_bottom <= (s_bottom + 16.0):
                    txt = tb["text"]
                    if re.search(r"(?:PGS\.|GS\.|TS\.|ThS\.|CN\.|BS\.|Đoàn Đức Tùng|[A-ZÀ-ỸĐ][a-zà-ỹđ]+\s+[A-ZÀ-ỸĐ][a-zà-ỹđ]+)", txt):
                        name_block = tb
                        name_idx = idx
                        break

            min_top = s_top
            max_bottom = s_bottom
            min_left = s_left
            max_right = s_right
            sig_text_lines: list[str] = []

            if title_block:
                min_top = min(min_top, title_block["top"])
                min_left = min(min_left, title_block["left"])
                max_right = max(max_right, title_block["left"] + title_block["width"])
                sig_text_lines.append(title_block["text"])
                used_text_indices.add(title_idx)

            if name_block:
                max_bottom = max(max_bottom, name_block["top"] + name_block["height"])
                min_left = min(min_left, name_block["left"])
                max_right = max(max_right, name_block["left"] + name_block["width"])
                sig_text_lines.append(name_block["text"])
                used_text_indices.add(name_idx)

            box_top = max(0.0, round(min_top - 0.8, 1))
            box_bottom = min(100.0, round(max_bottom + 0.8, 1))
            box_left = max(0.0, round(min_left - 1.2, 1))
            box_right = min(100.0, round(max_right + 1.2, 1))

            signatures.append({
                "type": "signature",
                "label": "signature",
                "text": "\n".join(sig_text_lines),
                "top": box_top,
                "left": box_left,
                "width": round(box_right - box_left, 1),
                "height": round(box_bottom - box_top, 1),
            })

        # Fallback for unstamped signatures (e.g. black-and-white scan or draft)
        if not signatures:
            for idx, tb in enumerate(text_blocks):
                if idx in used_text_indices:
                    continue
                tb_top = tb["top"]
                tb_left = tb["left"]
                if tb_left >= 40.0 and tb_top >= 50.0:
                    txt_upper = tb["text"].upper()
                    if any(kw in txt_upper for kw in [
                        "HIỆU TRƯỞNG", "HIEU TRUONG",
                        "PHÓ HIỆU TRƯỞNG", "PHO HIEU TRUONG",
                        "GIÁM ĐỐC", "GIAM DOC",
                        "PHÓ GIÁM ĐỐC", "PHO GIAM DOC",
                        "TRƯỞNG PHÒNG", "TRUONG PHONG",
                        "PHÓ TRƯỞNG PHÒNG", "PHO TRUONG PHONG",
                        "TRƯỞNG KHOA", "TRUONG KHOA",
                        "CHỦ TỊCH", "CHU TICH",
                        "KT. HIỆU TRƯỞNG", "KT. HIEU TRUONG",
                        "TL. HIỆU TRƯỞNG", "TL. HIEU TRUONG",
                        "TUQ. HIỆU TRƯỞNG", "TUQ. HIEU TRUONG",
                    ]):
                        name_block = None
                        name_idx = None
                        for n_idx, n_tb in enumerate(text_blocks):
                            if n_idx == idx or n_idx in used_text_indices:
                                continue
                            if n_tb["left"] >= 40.0 and 2.0 <= (n_tb["top"] - (tb_top + tb["height"])) <= 22.0:
                                n_txt = n_tb["text"]
                                if re.search(r"(?:PGS\.|GS\.|TS\.|ThS\.|CN\.|BS\.|[A-ZÀ-ỸĐ][a-zà-ỹđ]+\s+[A-ZÀ-ỸĐ][a-zà-ỹđ]+)", n_txt):
                                    name_block = n_tb
                                    name_idx = n_idx
                                    break
                        if name_block:
                            used_text_indices.add(idx)
                            used_text_indices.add(name_idx)
                            min_top = tb_top
                            max_bottom = name_block["top"] + name_block["height"]
                            min_left = min(tb_left, name_block["left"])
                            max_right = max(tb_left + tb["width"], name_block["left"] + name_block["width"])
                            signatures.append({
                                "type": "signature",
                                "label": "signature",
                                "text": f"{tb['text']}\nChữ ký xác thực\n{name_block['text']}",
                                "top": max(0.0, round(min_top - 0.8, 1)),
                                "left": max(0.0, round(min_left - 1.2, 1)),
                                "width": round(min(100.0, max_right + 1.2) - max(0.0, min_left - 1.2), 1),
                                "height": round(min(100.0, max_bottom + 0.8) - max(0.0, min_top - 0.8), 1),
                            })
                            break

        # 4. Classify remaining text blocks
        classified: list[dict[str, Any]] = []
        for idx, tb in enumerate(text_blocks):
            if idx in used_text_indices:
                continue
            txt = tb["text"]
            t = tb["top"]
            left_val = tb["left"]
            w = tb["width"]
            h = tb["height"]

            if page_number == 1 and t < 15.0:
                rtype = "header"
                lbl = "header"
            elif self._is_doc_or_section_title(txt):
                rtype = "title"
                lbl = "title"
            elif self._is_list_marker(txt):
                rtype = "list"
                lbl = "list"
            else:
                rtype = "text"
                lbl = "text"

            classified.append({
                "type": rtype,
                "label": lbl,
                "text": txt,
                "top": t,
                "left": left_val,
                "width": w,
                "height": h,
            })

        clean_tables = [
            {k: v for k, v in tab.items() if k != "bbox"}
            for tab in tables
        ]

        all_regions = clean_tables + signatures + classified
        all_regions = self._suppress_overlapping_boxes(all_regions)
        all_regions = self._merge_into_macro_regions(all_regions, page_number=page_number)
        all_regions.sort(key=lambda r: (r["top"], r["left"]))
        return all_regions

    def _merge_into_macro_regions(
        self,
        boxes: list[dict[str, Any]],
        page_number: int = 1,
    ) -> list[dict[str, Any]]:
        """Consolidate micro-segmented text boxes into coherent macro layout sections.

        Matches QNU-AI-Core design:
        - Prevents overwhelming users with dozens of tiny bounding boxes.
        - Unifies headers on Page 1 into Left and Right header blocks.
        - Preserves standalone document titles (e.g. KẾ HOẠCH, QUYẾT ĐỊNH).
        - Merges consecutive body text, clauses, and lists belonging to the same section.
        - Preserves tables, signatures, and bottom-left 'Nơi nhận' as distinct entities.
        """
        tables = [b for b in boxes if b["type"] == "table"]
        signatures = [b for b in boxes if b["type"] == "signature"]

        recipients: list[dict[str, Any]] = []
        content_boxes: list[dict[str, Any]] = []
        for b in boxes:
            if b["type"] in ("table", "signature"):
                continue
            txt = b.get("text", "")
            top = float(b["top"])
            left = float(b["left"])
            if ("Nơi nhận" in txt or "Noi nhan" in txt) and top >= 45.0 and left <= 35.0:
                b_copy = dict(b)
                b_copy["type"] = "list"
                b_copy["label"] = "list"
                recipients.append(b_copy)
            else:
                content_boxes.append(b)

        content_boxes.sort(key=lambda b: (float(b["top"]), float(b["left"])))

        merged_content: list[dict[str, Any]] = []

        # 1. Page 1: Merge header letterhead (top < 15%)
        if page_number == 1:
            left_headers: list[dict[str, Any]] = []
            right_headers: list[dict[str, Any]] = []
            other_boxes: list[dict[str, Any]] = []
            for b in content_boxes:
                if float(b["top"]) < 15.0 and b["type"] == "header":
                    w = float(b["width"])
                    left_val = float(b["left"])
                    if w > 60.0:
                        txt = b.get("text", "")
                        if "ngày" in txt or "tháng" in txt:
                            left_headers.append({
                                **b,
                                "text": txt.split("Gia Lai")[0].split("ngày")[0].strip(),
                                "width": 38.0,
                            })
                            right_headers.append({
                                **b,
                                "text": txt[len(txt.split("Gia Lai")[0]):].strip() if "Gia Lai" in txt else txt,
                                "left": 45.0,
                                "width": 48.0,
                            })
                        else:
                            left_headers.append(b)
                    elif left_val < 42.0:
                        left_headers.append(b)
                    else:
                        right_headers.append(b)
                else:
                    other_boxes.append(b)

            if left_headers:
                t = min(float(b["top"]) for b in left_headers)
                left_val = min(float(b["left"]) for b in left_headers)
                r = max(float(b["left"]) + float(b["width"]) for b in left_headers)
                bt = max(float(b["top"]) + float(b["height"]) for b in left_headers)
                merged_content.append({
                    "type": "header",
                    "label": "header",
                    "text": "\n".join(b.get("text", "").strip() for b in left_headers if b.get("text", "").strip()),
                    "top": round(t, 1),
                    "left": round(left_val, 1),
                    "width": round(min(50.0, r - left_val), 1),
                    "height": round(bt - t, 1),
                })

            if right_headers:
                t = min(float(b["top"]) for b in right_headers)
                left_val = min(float(b["left"]) for b in right_headers)
                r = max(float(b["left"]) + float(b["width"]) for b in right_headers)
                bt = max(float(b["top"]) + float(b["height"]) for b in right_headers)
                merged_content.append({
                    "type": "header",
                    "label": "header",
                    "text": "\n".join(b.get("text", "").strip() for b in right_headers if b.get("text", "").strip()),
                    "top": round(t, 1),
                    "left": round(max(40.0, left_val), 1),
                    "width": round(min(55.0, r - max(40.0, left_val)), 1),
                    "height": round(bt - t, 1),
                })

            content_boxes = other_boxes

        # 2. Merge consecutive text & list blocks
        for b in content_boxes:
            if not merged_content:
                merged_content.append(dict(b))
                continue

            prev = merged_content[-1]
            prev_bottom = float(prev["top"]) + float(prev["height"])
            gap = float(b["top"]) - prev_bottom
            txt = b.get("text", "").strip()

            is_main_doc_title = (
                b["type"] == "title"
                and any(txt.upper().startswith(kw) for kw in (
                    "KẾ HOẠCH", "KE HOACH",
                    "QUYẾT ĐỊNH", "QUYET DINH",
                    "THÔNG BÁO", "THONG BAO",
                    "TỜ TRÌNH", "TO TRINH",
                    "BÁO CÁO", "BAO CAO",
                    "HƯỚNG DẪN", "HUONG DAN",
                ))
            )
            prev_is_main_doc_title = (
                prev["type"] == "title"
                and any(prev.get("text", "").strip().upper().startswith(kw) for kw in (
                    "KẾ HOẠCH", "KE HOACH",
                    "QUYẾT ĐỊNH", "QUYET DINH",
                    "THÔNG BÁO", "THONG BAO",
                    "TỜ TRÌNH", "TO TRINH",
                    "BÁO CÁO", "BAO CAO",
                    "HƯỚNG DẪN", "HUONG DAN",
                ))
            )

            is_roman_section = (
                b["type"] == "title"
                and any(txt.strip().startswith(kw) for kw in ("I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.", "IX.", "X."))
            )

            # Check if any table sits vertically between prev and b
            table_between = any(
                (prev_bottom - 1.0 <= float(t["top"]) <= float(b["top"]) + 1.0)
                or (prev_bottom - 1.0 <= float(t["top"]) + float(t["height"]) <= float(b["top"]) + 1.0)
                for t in tables
            )

            # Compatible merge rule:
            # - Same types merge (list with list, text with text, header with header, title with title)
            # - Preserves list regions distinctly with type='list', never overwriting list into text
            # - Multi-line title with title if gap <= 2.5%
            # - DO NOT merge across tables
            can_merge = (
                not is_main_doc_title
                and not prev_is_main_doc_title
                and not is_roman_section
                and not table_between
                and (prev["type"] == b["type"])
                and 0.0 <= gap <= 3.5
                and abs(float(b["left"]) - float(prev["left"])) <= 20.0
            )

            if can_merge:
                new_left = min(float(prev["left"]), float(b["left"]))
                new_right = max(float(prev["left"]) + float(prev["width"]), float(b["left"]) + float(b["width"]))
                new_top = min(float(prev["top"]), float(b["top"]))
                new_bottom = max(prev_bottom, float(b["top"]) + float(b["height"]))
                prev["top"] = round(new_top, 1)
                prev["left"] = round(new_left, 1)
                prev["width"] = round(new_right - new_left, 1)
                prev["height"] = round(new_bottom - new_top, 1)
                prev["text"] = prev.get("text", "") + "\n\n" + b.get("text", "")
            else:
                merged_content.append(dict(b))

        all_res = tables + signatures + recipients + merged_content
        all_res = self._suppress_overlapping_boxes(all_res)
        all_res.sort(key=lambda r: (float(r["top"]), float(r["left"])))
        return all_res

    def _detect_text_regions(
        self,
        text_thresh: np.ndarray,
        w: int,
        h: int,
        _tables: list[dict[str, Any]],
        markdown_text: str = "",
        page_number: int = 1,
    ) -> list[dict[str, Any]]:
        """Segment paragraphs, headers, titles, and lists."""
        margin_l = int(w * 0.04)
        margin_r = int(w * 0.96)
        cleaned = text_thresh.copy()
        cleaned[:, :margin_l] = 0
        cleaned[:, margin_r:] = 0

        row_sums = np.sum(cleaned, axis=1) / 255.0
        in_p = False
        p_start = 0
        bands: list[tuple[int, int]] = []
        blank_cnt = 0

        for y, val in enumerate(row_sums):
            if val > 12:
                if not in_p:
                    in_p = True
                    p_start = y
                blank_cnt = 0
            else:
                if in_p:
                    blank_cnt += 1
                    if blank_cnt > 14:
                        p_end = y - blank_cnt
                        if p_end - p_start > 12:
                            bands.append((p_start, p_end))
                        in_p = False
                        blank_cnt = 0
        if in_p and (h - p_start > 12):
            bands.append((p_start, h))

        raw_boxes: list[dict[str, Any]] = []

        for p0, p1 in bands:
            band = cleaned[p0:p1, :]
            bh = p1 - p0
            col_sums = np.sum(band, axis=0)
            cols = np.where(col_sums > 0)[0]
            if len(cols) == 0:
                continue

            c0, c1 = cols[0], cols[-1]
            bw = c1 - c0
            top_pct = round((p0 / h) * 100, 1)
            left_pct = round((c0 / w) * 100, 1)
            w_pct = round((bw / w) * 100, 1)
            h_pct = round((bh / h) * 100, 1)

            if page_number == 1 and top_pct < 16.0 and bw > w * 0.55:
                mid_start = int(w * 0.40)
                mid_end = int(w * 0.56)
                mid_sum = np.sum(band[:, mid_start:mid_end])
                if mid_sum < 50:
                    left_cols = np.where(col_sums[:mid_start] > 0)[0]
                    if len(left_cols) > 0:
                        lx0, lx1 = left_cols[0], left_cols[-1]
                        raw_boxes.append({
                            "type": "header",
                            "label": "header",
                            "text": "",
                            "top": top_pct,
                            "left": round((lx0 / w) * 100, 1),
                            "width": round(((lx1 - lx0) / w) * 100, 1),
                            "height": h_pct,
                        })
                    right_cols = np.where(col_sums[mid_end:] > 0)[0]
                    if len(right_cols) > 0:
                        rx0, rx1 = mid_end + right_cols[0], mid_end + right_cols[-1]
                        raw_boxes.append({
                            "type": "header",
                            "label": "header",
                            "text": "",
                            "top": top_pct,
                            "left": round((rx0 / w) * 100, 1),
                            "width": round(((rx1 - rx0) / w) * 100, 1),
                            "height": h_pct,
                        })
                    continue

            rtype = "text"
            label = "text"

            if page_number == 1:
                if top_pct < 16.0:
                    rtype = "header"
                    label = "header"
                elif (16.0 <= top_pct <= 24.0 and w_pct < 85.0 and left_pct > 12.0) or (
                    h_pct < 4.5 and w_pct < 38.0 and (36.0 <= left_pct <= 54.0)
                ):
                    rtype = "title"
                    label = "title"
                elif top_pct > 68.0 and left_pct < 20.0 and w_pct < 45.0:
                    rtype = "list"
                    label = "list"
            else:
                # Trang sau: Nơi nhận nằm ở góc dưới bên trái
                if top_pct > 50.0 and left_pct < 30.0 and w_pct < 35.0:
                    rtype = "list"
                    label = "list"

            raw_boxes.append({
                "type": rtype,
                "label": label,
                "text": "",
                "top": top_pct,
                "left": left_pct,
                "width": w_pct,
                "height": h_pct,
            })

        merged_boxes: list[dict[str, Any]] = []
        for b in raw_boxes:
            if not merged_boxes:
                merged_boxes.append(b)
                continue
            prev = merged_boxes[-1]
            gap = b["top"] - (prev["top"] + prev["height"])
            same_type = (prev["type"] == b["type"])
            # Only merge small line breaks within the same paragraph (gap <= 0.8% and same left margin)
            # Never collapse distinct paragraphs across larger gaps
            is_same_paragraph = (
                same_type
                and 0.0 <= gap <= 0.8
                and abs(prev["left"] - b["left"]) < 4.0
                and prev["type"] not in ("title", "signature")
            )
            if is_same_paragraph:
                new_left = min(prev["left"], b["left"])
                new_right = max(prev["left"] + prev["width"], b["left"] + b["width"])
                new_top = prev["top"]
                new_bottom = b["top"] + b["height"]
                prev["top"] = round(new_top, 1)
                prev["left"] = round(new_left, 1)
                prev["width"] = round(new_right - new_left, 1)
                prev["height"] = round(new_bottom - new_top, 1)
            else:
                merged_boxes.append(b)

        md_items: list[str] = []
        if markdown_text and markdown_text.strip():
            raw_blocks = [blk.strip() for blk in re.split(r"\n\s*\n", markdown_text) if blk.strip()]
            for blk in raw_blocks:
                if blk.startswith(("<!--", "|")):
                    continue
                blk_lines = [
                    line_item.strip()
                    for line_item in blk.splitlines()
                    if line_item.strip() and not line_item.strip().startswith("|")
                ]
                if len(blk_lines) > 1 and all(self._is_list_marker(line_item) for line_item in blk_lines):
                    md_items.extend(blk_lines)
                else:
                    md_items.append(blk)

            if not md_items:
                md_items = [
                    line_item.strip()
                    for line_item in markdown_text.splitlines()
                    if line_item.strip() and not line_item.strip().startswith(("<!--", "|"))
                ]

        num_boxes = len(merged_boxes)
        num_items = len(md_items)
        for idx, box in enumerate(merged_boxes):
            assigned_text = ""
            if num_items > 0 and idx < num_items:
                assigned_text = md_items[idx]
                if idx == num_boxes - 1 and num_items > num_boxes:
                    assigned_text = "\n\n".join(md_items[idx:])

            if assigned_text:
                box["text"] = assigned_text
                if self._is_list_marker(assigned_text):
                    box["type"] = "list"
                    box["label"] = "list"
                elif page_number > 1:
                    box["type"] = "text"
                    box["label"] = "text"

        return merged_boxes

    def _suppress_overlapping_boxes(self, regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Suppress boxes with high overlap (>80% area or IoU > 0.8), guarding tables & signatures."""
        if len(regions) <= 1:
            return regions

        def _area(r: dict[str, Any]) -> float:
            return max(0.001, float(r.get("width", 0.0)) * float(r.get("height", 0.0)))

        def _intersection(r1: dict[str, Any], r2: dict[str, Any]) -> float:
            x1 = max(float(r1.get("left", 0.0)), float(r2.get("left", 0.0)))
            y1 = max(float(r1.get("top", 0.0)), float(r2.get("top", 0.0)))
            x2 = min(
                float(r1.get("left", 0.0)) + float(r1.get("width", 0.0)),
                float(r2.get("left", 0.0)) + float(r2.get("width", 0.0)),
            )
            y2 = min(
                float(r1.get("top", 0.0)) + float(r1.get("height", 0.0)),
                float(r2.get("top", 0.0)) + float(r2.get("height", 0.0)),
            )
            if x2 <= x1 or y2 <= y1:
                return 0.0
            return (x2 - x1) * (y2 - y1)

        keep = [True] * len(regions)
        for i in range(len(regions)):
            if not keep[i]:
                continue
            r_i = regions[i]
            t_i = str(r_i.get("type", "")).lower()

            for j in range(i + 1, len(regions)):
                if not keep[j]:
                    continue
                r_j = regions[j]
                t_j = str(r_j.get("type", "")).lower()

                inter = _intersection(r_i, r_j)
                if inter <= 0:
                    continue

                area_i = _area(r_i)
                area_j = _area(r_j)
                union = area_i + area_j - inter
                iou = inter / union if union > 0 else 0.0
                contain_i = inter / area_i
                contain_j = inter / area_j

                if iou > 0.80 or contain_i > 0.80 or contain_j > 0.80:
                    if t_i in ("table", "signature") and t_j not in ("table", "signature"):
                        if contain_j > 0.60 or iou > 0.60:
                            keep[j] = False
                    elif t_j in ("table", "signature") and t_i not in ("table", "signature"):
                        if contain_i > 0.60 or iou > 0.60:
                            keep[i] = False
                            break
                    elif t_i in ("table", "signature") and t_j in ("table", "signature"):
                        continue
                    else:
                        if contain_i > 0.80:
                            keep[i] = False
                            break
                        if contain_j > 0.80:
                            keep[j] = False
                        elif iou > 0.80:
                            if area_i >= area_j:
                                keep[j] = False
                            else:
                                keep[i] = False
                                break

        filtered = [r for idx, r in enumerate(regions) if keep[idx]]
        clean_result = []
        for r in filtered:
            clean_result.append({
                "type": r["type"],
                "label": r.get("label") or r["type"],
                "text": r.get("text") or "",
                "top": float(r["top"]),
                "left": float(r["left"]),
                "width": float(r["width"]),
                "height": float(r["height"]),
            })
        clean_result.sort(key=lambda r: (r["top"], r["left"]))
        return clean_result


smart_layout_detector = SmartLayoutDetector()
