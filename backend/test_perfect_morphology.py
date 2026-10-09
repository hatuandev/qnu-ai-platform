import sys

import numpy as np
import pymupdf as fitz
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

def detect_morphology_refined(
    pil_img: Image.Image,
    page_number: int = 1,
    is_last_page: bool = False,
    markdown_text: str = "",
) -> list[dict]:
    w, h = pil_img.size
    arr_gray = np.array(pil_img.convert("L"))
    arr_rgb = np.array(pil_img.convert("RGB"))

    margin_x1 = int(0.04 * w)
    margin_x2 = int(0.96 * w)
    margin_y1 = int(0.03 * h)
    margin_y2 = int(0.97 * h)

    # 1. Binarize with dynamic ink threshold
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

    # 3. Table Detection via Vertical Column Grids + True Ruled Horizontal Lines
    # 3a. Vertical column grid lines with gap bridging up to 6px
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

    # 3b. True horizontal ruled lines: must be long, continuous, and thin (thickness <= 4px)
    # Don't bridge 8px which merges text words! Only bridge 3px to heal small scan breaks.
    bridged_h = cleaned.copy()
    for s in (1, 2, 3):
        bridged_h[:, :-s] |= cleaned[:, s:]
        bridged_h[:, s:] |= cleaned[:, :-s]

    min_h_solid_len = max(180, int(w * 0.35)) # Real table lines span >= 35% of page width
    h_line_rows = []
    for y in range(margin_y1, margin_y2):
        row = bridged_h[y, :]
        diffs = np.diff(np.pad(row, (1, 1), "constant"))
        starts = np.where(diffs == 1)[0]
        ends = np.where(diffs == -1)[0]
        if len(starts) > 0 and len(ends) > 0:
            lens = ends - starts
            if np.any(lens >= min_h_solid_len):
                h_line_rows.append(y)

    h_clusters = []
    if h_line_rows:
        curr = [h_line_rows[0]]
        for r in h_line_rows[1:]:
            if r - curr[-1] <= 6:
                curr.append(r)
            else:
                # Table rule line thickness must be small (<= 6px)
                if len(curr) <= 6:
                    h_clusters.append(int(np.mean(curr)))
                curr = [r]
        if len(curr) <= 6:
            h_clusters.append(int(np.mean(curr)))

    table_boxes: list[tuple[int, int, int, int]] = []
    # Primary: Multi-column table detection from vertical columns (>= 3 columns)
    if len(v_clusters) >= 3:
        v_min_y = min(item[1] for item in v_clusters)
        v_max_y = max(item[2] for item in v_clusters)
        v_min_x = min(item[0] for item in v_clusters)
        v_max_x = max(item[0] for item in v_clusters)
        overlapping_v = [
            item for item in v_clusters
            if max(0, min(item[2], v_max_y) - max(item[1], v_min_y)) >= (v_max_y - v_min_y) * 0.40
        ]
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
                min(h, tbl_y2 + 4),
            ))

    # Secondary: Open-sided table (only horizontal rules), requires at least 3 distinct horizontal lines
    if not table_boxes and len(h_clusters) >= 3:
        curr_tbl_lines = [h_clusters[0]]
        for i in range(len(h_clusters) - 1):
            gap = h_clusters[i + 1] - h_clusters[i]
            if 20 <= gap <= 200:
                curr_tbl_lines.append(h_clusters[i + 1])
            else:
                if len(curr_tbl_lines) >= 3:
                    y1 = min(curr_tbl_lines) - 4
                    y2 = max(curr_tbl_lines) + 4
                    sub = cleaned[y1:y2, :]
                    cols = np.where(sub.sum(axis=0) > 3)[0]
                    if len(cols) >= 2 and (cols[-1] - cols[0]) >= int(w * 0.35):
                        table_boxes.append((max(0, cols[0] - 6), y1, min(w, cols[-1] + 6), y2))
                curr_tbl_lines = [h_clusters[i + 1]]
        if len(curr_tbl_lines) >= 3:
            y1 = min(curr_tbl_lines) - 4
            y2 = max(curr_tbl_lines) + 4
            sub = cleaned[y1:y2, :]
            cols = np.where(sub.sum(axis=0) > 3)[0]
            if len(cols) >= 2 and (cols[-1] - cols[0]) >= int(w * 0.35):
                table_boxes.append((max(0, cols[0] - 6), y1, min(w, cols[-1] + 6), y2))

    # 4. Text line extraction via Horizontal Projection
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

    # 5. Filter text lines outside table boxes
    outside_lines = []
    for (ly1, ly2) in lines:
        is_inside_tbl = False
        for (tx1, ty1, tx2, ty2) in table_boxes:
            if max(ly1, ty1) < min(ly2, ty2):
                is_inside_tbl = True
                break
        if not is_inside_tbl:
            outside_lines.append((ly1, ly2))

    # 6. Cluster outside lines into paragraphs/sections
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

    # 7. Combine all visual blocks
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

    # 8. Page 1 header consolidation
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

    # 9. Dual-column signing block (Nơi nhận on left, Chữ ký on right)
    processed_blocks = []
    for b in final_blocks:
        bx1, by1, bx2, by2 = b["bbox"]
        bh_pct = (by2 - by1) / h * 100.0

        # Strict signing block criteria:
        # - Must be the closing page
        # - Must NOT be a table
        # - Must have substantial height (>= 5.0% page height)
        # - Must be located near red seal OR at bottom >= 75%
        is_signing_area = False
        if is_last_page and b["type"] != "table" and bh_pct >= 5.0:
            if has_seal:
                if by1 <= seal_y2 and by2 >= (seal_y1 - int(0.04 * h)):
                    is_signing_area = True
            else:
                if (by1 / h) >= 0.75:
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

    # 10. Format output
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
            r_label = "Chữ ký / Con dấu"
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
            "px_bbox": (bx1, by1, bx2, by2),
        })

    return regions

# Test on TB2302
pdf_path = r"d:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf"
doc = fitz.open(pdf_path)

print("Testing TB2302...")
for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    is_last = (p_num == len(doc))
    pix = page.get_pixmap(dpi=150)
    pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    regs = detect_morphology_refined(pil_img, page_number=p_num, is_last_page=is_last)
    print(f"\n--- PAGE {p_num} ({len(regs)} blocks) ---")
    for r in regs:
        print(f"  [{r['type']:10s}] top={r['top']:5.1f}%, left={r['left']:5.1f}%, w={r['width']:5.1f}%, h={r['height']:5.1f}% | {r['label']}")

# Test on TB2618
pdf_path2 = r"d:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc2 = fitz.open(pdf_path2)

print("\nTesting TB2618...")
for p_idx, page in enumerate(doc2):
    p_num = p_idx + 1
    is_last = (p_num == len(doc2))
    pix = page.get_pixmap(dpi=150)
    pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    regs = detect_morphology_refined(pil_img, page_number=p_num, is_last_page=is_last)
    print(f"\n--- PAGE {p_num} ({len(regs)} blocks) ---")
    for r in regs:
        if r['type'] in ('table', 'signature') or p_num == 2:
            print(f"  [{r['type']:10s}] top={r['top']:5.1f}%, left={r['left']:5.1f}%, w={r['width']:5.1f}%, h={r['height']:5.1f}% | {r['label']}")
