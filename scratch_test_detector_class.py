import io
import logging
import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

class TestDetector:
    def _detect_morphology_regions(
        self,
        image_input: any = None,
        fitz_page: any = None,
        markdown_text: str = "",
        page_number: int = 1,
    ) -> list[dict]:
        pil_img = None
        if fitz_page is not None:
            try:
                pix = fitz_page.get_pixmap(dpi=150)
                pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            except Exception as exc:
                logger.debug("fitz_pixmap_failed: %s", exc)

        if pil_img is None and image_input is not None:
            if isinstance(image_input, str):
                pil_img = Image.open(image_input)
            elif isinstance(image_input, bytes):
                pil_img = Image.open(io.BytesIO(image_input))
            elif isinstance(image_input, np.ndarray):
                pil_img = Image.fromarray(image_input)
            elif isinstance(image_input, Image.Image):
                pil_img = image_input

        if pil_img is None:
            return []

        w, h = pil_img.size
        arr_gray = np.array(pil_img.convert("L"))
        arr_rgb = np.array(pil_img.convert("RGB"))

        margin_x1 = int(0.04 * w)
        margin_x2 = int(0.96 * w)
        margin_y1 = int(0.03 * h)
        margin_y2 = int(0.97 * h)

        # 1. Binarize using dynamic ink threshold
        bg_level = float(np.percentile(arr_gray, 90))
        ink_thresh = min(190, int(bg_level * 0.78))
        cleaned = (arr_gray < ink_thresh).astype(np.int32)
        cleaned[:margin_y1, :] = 0
        cleaned[margin_y2:, :] = 0
        cleaned[:, :margin_x1] = 0
        cleaned[:, margin_x2:] = 0

        # 2. Ruled Table Detection
        bridged_h = cleaned.copy()
        for s in [1, 2, 3, 4]:
            bridged_h[:, :-s] |= cleaned[:, s:]
            bridged_h[:, s:] |= cleaned[:, :-s]

        min_line_len = max(120, int(w * 0.20))
        tbl_line_rows = []
        for y in range(margin_y1, margin_y2):
            row = bridged_h[y, :]
            diffs = np.diff(np.pad(row, (1, 1), "constant"))
            starts = np.where(diffs == 1)[0]
            ends = np.where(diffs == -1)[0]
            if len(starts) > 0 and len(ends) > 0:
                lens = ends - starts
                if np.any(lens >= min_line_len):
                    tbl_line_rows.append(y)

        table_boxes = []
        if tbl_line_rows:
            clusters = []
            curr = [tbl_line_rows[0]]
            for r in tbl_line_rows[1:]:
                if r - curr[-1] <= 6:
                    curr.append(r)
                else:
                    clusters.append(int(np.mean(curr)))
                    curr = [r]
            clusters.append(int(np.mean(curr)))

            if len(clusters) >= 2:
                tbl_start = clusters[0]
                curr_tbl_lines = [clusters[0]]
                for i in range(len(clusters) - 1):
                    gap = clusters[i + 1] - clusters[i]
                    if 18 <= gap <= 250:
                        curr_tbl_lines.append(clusters[i + 1])
                    else:
                        if len(curr_tbl_lines) >= 2:
                            y1 = min(curr_tbl_lines) - 4
                            y2 = max(curr_tbl_lines) + 4
                            sub = cleaned[y1:y2, :]
                            cols = np.where(sub.sum(axis=0) > 3)[0]
                            if len(cols) >= 2:
                                table_boxes.append((max(0, cols[0] - 6), y1, min(w, cols[-1] + 6), y2))
                        curr_tbl_lines = [clusters[i + 1]]
                if len(curr_tbl_lines) >= 2:
                    y1 = min(curr_tbl_lines) - 4
                    y2 = max(curr_tbl_lines) + 4
                    sub = cleaned[y1:y2, :]
                    cols = np.where(sub.sum(axis=0) > 3)[0]
                    if len(cols) >= 2:
                        tx1 = max(0, cols[0] - 6)
                        tx2 = min(w, cols[-1] + 6)
                        # Expand upwards to include header row if column alignment matches
                        above_slice = cleaned[max(0, y1 - 120):y1, :]
                        above_cols = np.where(above_slice.sum(axis=0) > 3)[0]
                        if len(above_cols) >= 2 and (above_cols[-1] - above_cols[0]) >= 0.40 * w:
                            above_rows = np.where(above_slice.sum(axis=1) > 10)[0]
                            if len(above_rows) > 0:
                                y1 = max(0, y1 - 120 + above_rows[0] - 4)
                        table_boxes.append((tx1, y1, tx2, y2))

        # 3. Horizontal projection profile for text lines
        h_proj = cleaned.sum(axis=1)
        line_thresh = max(12, int(w * 0.012))
        in_line = False
        lines = []
        start_y = 0
        for y in range(margin_y1, margin_y2):
            if h_proj[y] > line_thresh:
                if not in_line:
                    in_line = True
                    start_y = y
            else:
                if in_line:
                    in_line = False
                    if y - start_y >= 4:
                        lines.append((start_y, y))

        # 4. Filter text lines outside table boxes
        outside_lines = []
        for (ly1, ly2) in lines:
            is_inside_tbl = False
            for (tx1, ty1, tx2, ty2) in table_boxes:
                if max(ly1, ty1) < min(ly2, ty2):
                    is_inside_tbl = True
                    break
            if not is_inside_tbl:
                outside_lines.append((ly1, ly2))

        # 5. Cluster outside lines into paragraphs/sections
        split_thresh = 16.5
        clusters = []
        if outside_lines:
            curr = [outside_lines[0]]
            for i in range(len(outside_lines) - 1):
                gap = outside_lines[i + 1][0] - outside_lines[i][1]
                if gap >= split_thresh:
                    clusters.append((curr[0][0], curr[-1][1]))
                    curr = [outside_lines[i + 1]]
                else:
                    curr.append(outside_lines[i + 1])
            if curr:
                clusters.append((curr[0][0], curr[-1][1]))

        # 6. Combine all visual blocks
        all_raw = []
        for cy1, cy2 in clusters:
            sub = cleaned[cy1:cy2, :]
            cols = np.where(sub.sum(axis=0) > 2)[0]
            cx1 = max(0, cols[0] - 6) if len(cols) > 0 else margin_x1
            cx2 = min(w, cols[-1] + 6) if len(cols) > 0 else margin_x2
            all_raw.append({"type": "text", "bbox": (cx1, cy1, cx2, cy2)})

        for (tx1, ty1, tx2, ty2) in table_boxes:
            all_raw.append({"type": "table", "bbox": (tx1, ty1, tx2, ty2)})

        all_raw.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

        # 7. Page 1 header consolidation
        final_blocks = []
        if page_number == 1:
            hdr_group = [b for b in all_raw if (b["bbox"][1] / h) <= 0.14 and b["type"] != "table"]
            other_group = [b for b in all_raw if (b["bbox"][1] / h) > 0.14 or b["type"] == "table"]
            if hdr_group:
                hx1 = min(b["bbox"][0] for b in hdr_group)
                hy1 = min(b["bbox"][1] for b in hdr_group)
                hx2 = max(b["bbox"][2] for b in hdr_group)
                hy2 = max(b["bbox"][3] for b in hdr_group)
                final_blocks.append({
                    "type": "header",
                    "label": "Phần đầu văn bản",
                    "bbox": (hx1, hy1, hx2, hy2),
                })
            final_blocks.extend(other_group)
        else:
            final_blocks = all_raw

        # 8. Check if closing page with dual columns (Nơi nhận & Chữ ký)
        is_closing = False
        if fitz_page is not None:
            try:
                is_closing = (page_number == len(fitz_page.parent))
            except Exception:
                is_closing = (page_number > 1)
        elif page_number > 1:
            is_closing = True

        processed_blocks = []
        for b in final_blocks:
            bx1, by1, bx2, by2 = b["bbox"]
            if is_closing and b["type"] != "table" and (by1 / h) >= 0.50:
                sub = cleaned[by1:by2, :]
                v_p = sub.sum(axis=0)
                gutter_start = int(0.36 * w)
                gutter_end = int(0.55 * w)
                if v_p[gutter_start:gutter_end].min() <= 2:
                    gutter_x = gutter_start + int(np.argmin(v_p[gutter_start:gutter_end]))
                    left_cols = np.where(v_p[:gutter_x] > 2)[0]
                    right_cols = np.where(v_p[gutter_x:] > 2)[0]
                    if len(left_cols) > 0 and len(right_cols) > 0:
                        processed_blocks.append({
                            "type": "list",
                            "label": "Danh sách",
                            "bbox": (max(0, left_cols[0] - 6), by1, gutter_x - 4, by2),
                        })
                        processed_blocks.append({
                            "type": "signature",
                            "label": "Chữ ký / Nơi nhận",
                            "bbox": (gutter_x + right_cols[0] - 4, by1, min(w, gutter_x + right_cols[-1] + 6), by2),
                        })
                        continue
            processed_blocks.append(b)

        # 9. Format output with percentage coordinates
        regions = []
        for idx, b in enumerate(processed_blocks, 1):
            bx1, by1, bx2, by2 = b["bbox"]
            top_pct = round(by1 / h * 100, 1)
            left_pct = round(bx1 / w * 100, 1)
            w_pct = round((bx2 - bx1) / w * 100, 1)
            h_pct = round((by2 - by1) / h * 100, 1)
            b_type = b.get("type", "text")

            if b_type == "table":
                r_type = "table"
                r_label = "Bảng dữ liệu"
            elif b_type == "signature":
                r_type = "signature"
                r_label = "Chữ ký / Nơi nhận"
            elif page_number == 1 and top_pct <= 14.0:
                r_type = "header"
                r_label = "Phần đầu văn bản"
            elif page_number == 1 and top_pct <= 22.0:
                r_type = "title"
                r_label = "Tiêu đề"
            elif h_pct >= 6.0:
                r_type = "list"
                r_label = "Danh sách"
            else:
                r_type = "text"
                r_label = "Khối văn bản"

            regions.append({
                "type": r_type,
                "label": r_label,
                "text": "",
                "content_snippet": "",
                "top": top_pct,
                "left": left_pct,
                "width": w_pct,
                "height": h_pct,
            })

        return regions

# Run test
pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)
detector = TestDetector()

for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    regs = detector._detect_morphology_regions(fitz_page=page, page_number=p_num)
    print(f"\n=== PAGE {p_num} ({len(regs)} regions) ===")
    for r in regs:
        print(f"  {r['type']:10s} {r['label']:22s} top={r['top']:5.1f}% left={r['left']:5.1f}% w={r['width']:5.1f}% h={r['height']:5.1f}%")
