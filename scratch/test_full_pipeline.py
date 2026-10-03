import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

def test_full_pipeline(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"\n=======================================================")
    print(f"PROCESSING: {pdf_path}")
    print(f"Total pages: {len(doc)}")

    for p_idx, page in enumerate(doc):
        p_num = p_idx + 1
        pix = page.get_pixmap(dpi=150)
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
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

        # 2. Red Stamp / Seal Detection
        r_chan = arr_rgb[:, :, 0].astype(np.int32)
        g_chan = arr_rgb[:, :, 1].astype(np.int32)
        b_chan = arr_rgb[:, :, 2].astype(np.int32)
        red_mask = (r_chan > 120) & ((r_chan - g_chan) > 35) & ((r_chan - b_chan) > 35)
        red_mask[:margin_y1, :] = False
        red_mask[margin_y2:, :] = False
        red_mask[:, :margin_x1] = False
        red_mask[:, margin_x2:] = False

        red_bottom = red_mask.copy()
        red_bottom[:int(0.40 * h), :] = False
        has_seal = np.count_nonzero(red_bottom) > 400
        seal_y1, seal_y2 = 0, 0
        if has_seal:
            red_rows = np.where(red_bottom.sum(axis=1) > 5)[0]
            seal_y1 = max(0, red_rows[0] - 10)
            seal_y2 = min(h, red_rows[-1] + 10)

        # 3. Enhanced Table Detection (Vertical columns + Horizontal grid lines)
        # Vertical lines with gap bridging up to 6px
        bridged_v = cleaned.copy()
        for s in range(1, 7):
            bridged_v[:-s, :] |= cleaned[s:, :]
            bridged_v[s:, :] |= cleaned[:-s, :]

        min_v_len = max(90, int(h * 0.06))
        v_lines = []
        for x in range(margin_x1, margin_x2):
            col = bridged_v[:, x]
            diffs = np.diff(np.pad(col, (1, 1), "constant"))
            starts = np.where(diffs == 1)[0]
            ends = np.where(diffs == -1)[0]
            if len(starts) > 0 and len(ends) > 0:
                lens = ends - starts
                for st, en, l in zip(starts, ends, lens):
                    if l >= min_v_len:
                        v_lines.append((x, st, en))

        v_clusters = []
        if v_lines:
            v_lines.sort(key=lambda item: item[0])
            curr_v = [v_lines[0]]
            for vl in v_lines[1:]:
                if vl[0] - curr_v[-1][0] <= 5:
                    curr_v.append(vl)
                else:
                    vx = int(np.mean([item[0] for item in curr_v]))
                    v_st = min(item[1] for item in curr_v)
                    v_en = max(item[2] for item in curr_v)
                    v_clusters.append((vx, v_st, v_en))
                    curr_v = [vl]
            vx = int(np.mean([item[0] for item in curr_v]))
            v_st = min(item[1] for item in curr_v)
            v_en = max(item[2] for item in curr_v)
            v_clusters.append((vx, v_st, v_en))

        # Horizontal lines with gap bridging up to 8px
        bridged_h = cleaned.copy()
        for s in range(1, 9):
            bridged_h[:, :-s] |= cleaned[:, s:]
            bridged_h[:, s:] |= cleaned[:, :-s]

        min_h_len = max(100, int(w * 0.18))
        h_line_rows = []
        for y in range(margin_y1, margin_y2):
            row = bridged_h[y, :]
            diffs = np.diff(np.pad(row, (1, 1), "constant"))
            starts = np.where(diffs == 1)[0]
            ends = np.where(diffs == -1)[0]
            if len(starts) > 0 and len(ends) > 0:
                lens = ends - starts
                if np.any(lens >= min_h_len):
                    h_line_rows.append(y)

        h_clusters = []
        if h_line_rows:
            curr = [h_line_rows[0]]
            for r in h_line_rows[1:]:
                if r - curr[-1] <= 6:
                    curr.append(r)
                else:
                    h_clusters.append(int(np.mean(curr)))
                    curr = [r]
            h_clusters.append(int(np.mean(curr)))

        table_boxes = []
        if len(v_clusters) >= 3:
            v_min_y = min(item[1] for item in v_clusters)
            v_max_y = max(item[2] for item in v_clusters)
            v_min_x = min(item[0] for item in v_clusters)
            v_max_x = max(item[0] for item in v_clusters)
            overlapping_v = [item for item in v_clusters if max(0, min(item[2], v_max_y) - max(item[1], v_min_y)) >= (v_max_y - v_min_y) * 0.40]
            if len(overlapping_v) >= 3 and (v_max_x - v_min_x) >= int(w * 0.30):
                tbl_y1 = v_min_y
                tbl_y2 = v_max_y
                nearby_h = [hy for hy in h_clusters if (v_min_y - 30) <= hy <= (v_max_y + 30)]
                if nearby_h:
                    tbl_y1 = min(tbl_y1, min(nearby_h))
                    tbl_y2 = max(tbl_y2, max(nearby_h))
                table_boxes.append((
                    max(0, v_min_x - 6),
                    max(0, tbl_y1 - 4),
                    min(w, v_max_x + 6),
                    min(h, tbl_y2 + 4)
                ))

        # 4. Text line horizontal projection
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

        outside_lines = []
        for (ly1, ly2) in lines:
            is_inside_tbl = False
            for (tx1, ty1, tx2, ty2) in table_boxes:
                if max(ly1, ty1) < min(ly2, ty2):
                    is_inside_tbl = True
                    break
            if not is_inside_tbl:
                outside_lines.append((ly1, ly2))

        split_thresh = max(14.0, min(18.0, 0.0095 * h))
        clusters_lines = []
        if outside_lines:
            curr_cl = [outside_lines[0]]
            for i in range(len(outside_lines) - 1):
                gap = outside_lines[i + 1][0] - outside_lines[i][1]
                if gap >= split_thresh:
                    clusters_lines.append((curr_cl[0][0], curr_cl[-1][1]))
                    curr_cl = [outside_lines[i + 1]]
                else:
                    curr_cl.append(outside_lines[i + 1])
            if curr_cl:
                clusters_lines.append((curr_cl[0][0], curr_cl[-1][1]))

        all_raw = []
        for cy1, cy2 in clusters_lines:
            sub = cleaned[cy1:cy2, :]
            cols = np.where(sub.sum(axis=0) > 2)[0]
            cx1 = max(0, cols[0] - 6) if len(cols) > 0 else margin_x1
            cx2 = min(w, cols[-1] + 6) if len(cols) > 0 else margin_x2
            all_raw.append({"type": "text", "bbox": (cx1, cy1, cx2, cy2)})

        for (tx1, ty1, tx2, ty2) in table_boxes:
            all_raw.append({"type": "table", "bbox": (tx1, ty1, tx2, ty2)})

        all_raw.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

        # Page 1 header consolidation
        final_blocks = []
        if p_num == 1:
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

        # Closing page dual-column logic (targeted ONLY at true signing block)
        is_closing = (p_num == len(doc))
        processed_blocks = []

        for b in final_blocks:
            bx1, by1, bx2, by2 = b["bbox"]
            bh_pct = (by2 - by1) / h * 100.0

            # Dual-column candidate check:
            # Must be closing page, not a table, and have substantial height (>= 5.0% of page)
            is_signing_area = False
            if is_closing and b["type"] != "table" and bh_pct >= 5.0:
                if has_seal:
                    # Overlaps with or is near the red seal
                    if by1 <= seal_y2 and by2 >= (seal_y1 - int(0.04 * h)):
                        is_signing_area = True
                else:
                    # Bottom of page without seal
                    if (by1 / h) >= 0.70:
                        is_signing_area = True

            if is_signing_area:
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
                            "label": "Nơi nhận",
                            "bbox": (max(0, left_cols[0] - 6), by1, gutter_x - 4, by2),
                        })
                        processed_blocks.append({
                            "type": "signature",
                            "label": "Chữ ký / Con dấu",
                            "bbox": (gutter_x + right_cols[0] - 4, by1, min(w, gutter_x + right_cols[-1] + 6), by2),
                        })
                        continue
            processed_blocks.append(b)

        print(f"\n--- PAGE {p_num} ({len(processed_blocks)} regions) ---")
        for b in processed_blocks:
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
                r_label = "Chữ ký / Con dấu"
            elif p_num == 1 and top_pct <= 14.0:
                r_type = "header"
                r_label = "Phần đầu văn bản"
            elif p_num == 1 and top_pct <= 22.0:
                r_type = "title"
                r_label = "Tiêu đề"
            elif h_pct >= 6.0:
                r_type = "list"
                r_label = "Danh sách"
            else:
                r_type = "text"
                r_label = "Khối văn bản"

            print(f"  {r_type:10s} {r_label:22s} y={top_pct:5.1f}% x={left_pct:5.1f}% w={w_pct:5.1f}% h={h_pct:5.1f}% (bot={top_pct+h_pct:5.1f}%)")

test_full_pipeline("docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf")
test_full_pipeline("docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf")
