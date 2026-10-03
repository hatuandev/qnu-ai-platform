import sys
import numpy as np
from PIL import Image, ImageDraw
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

def detect_visual_layout_morphology(
    img_rgb: Image.Image,
    page_number: int = 1,
    markdown_text: str = "",
) -> list[dict]:
    w, h = img_rgb.size
    arr_gray = np.array(img_rgb.convert("L"))
    arr_rgb = np.array(img_rgb)

    margin_x1 = int(0.04 * w)
    margin_x2 = int(0.96 * w)
    margin_y1 = int(0.03 * h)
    margin_y2 = int(0.97 * h)

    # 1. Binarize (dark ink vs light paper)
    bg_level = np.percentile(arr_gray, 90)
    ink_thresh = min(190, int(bg_level * 0.78))
    cleaned = (arr_gray < ink_thresh).astype(np.int32)
    cleaned[:margin_y1, :] = 0
    cleaned[margin_y2:, :] = 0
    cleaned[:, :margin_x1] = 0
    cleaned[:, margin_x2:] = 0

    # 2. Ruled Table Detection
    # Bridge small gaps up to 4px
    bridged_h = cleaned.copy()
    for s in [1, 2, 3, 4]:
        bridged_h[:, :-s] |= cleaned[:, s:]
        bridged_h[:, s:] |= cleaned[:, :-s]

    min_line_len = int(w * 0.09) # ~110px continuous line length
    tbl_line_rows = []
    for y in range(margin_y1, margin_y2):
        row = bridged_h[y, :]
        diffs = np.diff(np.pad(row, (1, 1), 'constant'))
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
                gap = clusters[i+1] - clusters[i]
                if 18 <= gap <= 250:
                    curr_tbl_lines.append(clusters[i+1])
                else:
                    if len(curr_tbl_lines) >= 2:
                        y1 = min(curr_tbl_lines) - 4
                        y2 = max(curr_tbl_lines) + 4
                        sub = cleaned[y1:y2, :]
                        cols = np.where(sub.sum(axis=0) > 3)[0]
                        if len(cols) >= 2:
                            table_boxes.append((max(0, cols[0] - 6), y1, min(w, cols[-1] + 6), y2))
                    curr_tbl_lines = [clusters[i+1]]
            if len(curr_tbl_lines) >= 2:
                y1 = min(curr_tbl_lines) - 4
                y2 = max(curr_tbl_lines) + 4
                sub = cleaned[y1:y2, :]
                cols = np.where(sub.sum(axis=0) > 3)[0]
                if len(cols) >= 2:
                    table_boxes.append((max(0, cols[0] - 6), y1, min(w, cols[-1] + 6), y2))

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
    # Intra-line gap is 11-13px. Section/paragraph gap is >= 16.5px.
    split_thresh = 16.5
    clusters = []
    if outside_lines:
        curr = [outside_lines[0]]
        for i in range(len(outside_lines) - 1):
            gap = outside_lines[i+1][0] - outside_lines[i][1]
            if gap >= split_thresh:
                clusters.append((curr[0][0], curr[-1][1]))
                curr = [outside_lines[i+1]]
            else:
                curr.append(outside_lines[i+1])
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

    # Sort top to bottom
    all_raw.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

    # Handle dual column at bottom of closing page (Nơi nhận & Chữ ký)
    final_raw = []
    for b in all_raw:
        bx1, by1, bx2, by2 = b["bbox"]
        if b["type"] != "table" and (by1 / h) >= 0.50:
            sub = cleaned[by1:by2, :]
            v_p = sub.sum(axis=0)
            gutter_start = int(0.36 * w)
            gutter_end = int(0.55 * w)
            if v_p[gutter_start:gutter_end].min() <= 2:
                gutter_x = gutter_start + int(np.argmin(v_p[gutter_start:gutter_end]))
                left_cols = np.where(v_p[:gutter_x] > 2)[0]
                right_cols = np.where(v_p[gutter_x:] > 2)[0]
                if len(left_cols) > 0 and len(right_cols) > 0:
                    final_raw.append({
                        "type": "list",
                        "label": "Danh sách",
                        "bbox": (max(0, left_cols[0] - 6), by1, gutter_x - 4, by2),
                    })
                    final_raw.append({
                        "type": "signature",
                        "label": "Chữ ký / Nơi nhận",
                        "bbox": (gutter_x + right_cols[0] - 4, by1, min(w, gutter_x + right_cols[-1] + 6), by2),
                    })
                    continue
        final_raw.append(b)

    # 7. Convert to percent coordinates & labels
    regions = []
    for idx, b in enumerate(final_raw, 1):
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
            "top": top_pct,
            "left": left_pct,
            "width": w_pct,
            "height": h_pct,
            "px_coords": (bx1, by1, bx2, by2),
        })

    return regions

# Run on TB2618
pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)

for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    regions = detect_visual_layout_morphology(img, page_number=p_num)
    print(f"\n================ PAGE {p_num} ================")
    print(f"Total detected regions: {len(regions)}")
    
    vis = img.copy()
    draw = ImageDraw.Draw(vis)
    colors = {
        "header": "blue",
        "title": "green",
        "text": "orange",
        "table": "cyan",
        "list": "magenta",
        "signature": "red",
    }
    
    for idx, r in enumerate(regions, 1):
        print(f"  [{idx:2d}] type={r['type']:10s} label={r['label']:22s} top={r['top']:5.1f}% left={r['left']:5.1f}% w={r['width']:5.1f}% h={r['height']:5.1f}%")
        px1, py1, px2, py2 = r["px_coords"]
        draw.rectangle([px1, py1, px2, py2], outline=colors.get(r["type"], "yellow"), width=3)
    
    out_vis = f"scratch/verified_morphology_page_{p_num}.png"
    vis.save(out_vis)
    print(f"Saved visualization to {out_vis}")
