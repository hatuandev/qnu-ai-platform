import sys
import numpy as np
from PIL import Image, ImageDraw
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

def detect_page_layout_morphology(
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

    # 1. Red Stamp Detection (RGB color space)
    r = arr_rgb[:, :, 0].astype(np.int16)
    g = arr_rgb[:, :, 1].astype(np.int16)
    b = arr_rgb[:, :, 2].astype(np.int16)
    red_mask = (r > 120) & ((r - g) > 35) & ((r - b) > 35) & (r * 2 > (g + b) * 1.3)
    red_clean = np.zeros_like(red_mask)
    red_clean[margin_y1:margin_y2, margin_x1:margin_x2] = red_mask[margin_y1:margin_y2, margin_x1:margin_x2]

    stamps = []
    red_rows = np.where(red_clean.sum(axis=1) > 15)[0]
    if len(red_rows) > 0:
        clusters = []
        curr = [red_rows[0]]
        for row in red_rows[1:]:
            if row - curr[-1] <= 10:
                curr.append(row)
            else:
                if len(curr) >= 25:
                    clusters.append((curr[0], curr[-1]))
                curr = [row]
        if len(curr) >= 25:
            clusters.append((curr[0], curr[-1]))

        for sy1, sy2 in clusters:
            sub = red_clean[sy1:sy2, :]
            cols = np.where(sub.sum(axis=0) > 5)[0]
            if len(cols) >= 25:
                sx1, sx2 = cols[0], cols[-1]
                stamps.append((sx1, sy1, sx2, sy2))

    # 2. Binarization
    bg_level = np.percentile(arr_gray, 90)
    ink_thresh = min(190, int(bg_level * 0.78))
    binary = (arr_gray < ink_thresh).astype(np.uint8)
    cleaned = np.zeros_like(binary)
    cleaned[margin_y1:margin_y2, margin_x1:margin_x2] = binary[margin_y1:margin_y2, margin_x1:margin_x2]

    # 3. Detect Table Grid Lines
    kernel_len = max(60, int(w * 0.12))
    tbl_lines = []
    for y in range(margin_y1, margin_y2):
        row = cleaned[y, :]
        diffs = np.diff(np.pad(row, (1, 1), 'constant'))
        starts = np.where(diffs == 1)[0]
        ends = np.where(diffs == -1)[0]
        if len(starts) > 0 and len(ends) > 0:
            if np.any((ends - starts) >= kernel_len):
                tbl_lines.append(y)

    table_boxes = []
    if len(tbl_lines) >= 2:
        t_y1 = min(tbl_lines)
        t_y2 = max(tbl_lines)
        sub = cleaned[t_y1:t_y2, :]
        cols = np.where(sub.sum(axis=0) > 3)[0]
        if len(cols) >= 2:
            tx1 = max(0, cols[0] - 4)
            tx2 = min(w, cols[-1] + 4)
            table_boxes.append((tx1, t_y1 - 3, tx2, t_y2 + 3))

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

    # 5. Cluster lines into blocks
    # Table lines stay inside table_box
    blocks = []

    # First add lines outside table
    outside_lines = []
    table_lines_group = []
    for (ly1, ly2) in lines:
        is_inside_any_table = False
        for (tx1, ty1, tx2, ty2) in table_boxes:
            if ty1 <= ly1 <= ty2 or ty1 <= ly2 <= ty2:
                is_inside_any_table = True
                break
        if is_inside_any_table:
            table_lines_group.append((ly1, ly2))
        else:
            outside_lines.append((ly1, ly2))

    # Group outside lines by inter-paragraph gap
    # Section gap threshold: ~22px
    inter_para_thresh = 22.0
    clusters = []
    if outside_lines:
        curr = [outside_lines[0]]
        for i in range(len(outside_lines) - 1):
            gap = outside_lines[i+1][0] - outside_lines[i][1]
            if gap > inter_para_thresh:
                clusters.append((curr[0][0], curr[-1][1]))
                curr = [outside_lines[i+1]]
            else:
                curr.append(outside_lines[i+1])
        if curr:
            clusters.append((curr[0][0], curr[-1][1]))

    # Combine clusters with table boxes
    raw_blocks = []
    for cy1, cy2 in clusters:
        sub = cleaned[cy1:cy2, :]
        cols = np.where(sub.sum(axis=0) > 2)[0]
        cx1 = max(0, cols[0] - 6) if len(cols) > 0 else margin_x1
        cx2 = min(w, cols[-1] + 6) if len(cols) > 0 else margin_x2
        raw_blocks.append({"type": "text", "bbox": (cx1, cy1, cx2, cy2)})

    for (tx1, ty1, tx2, ty2) in table_boxes:
        raw_blocks.append({"type": "table", "bbox": (tx1, ty1, tx2, ty2)})

    # Sort blocks top-to-bottom
    raw_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

    # Special handling for closing page bottom: Nơi nhận (left) and Signature (right)
    final_blocks = []
    for blk in raw_blocks:
        bx1, by1, bx2, by2 = blk["bbox"]
        b_type = blk["type"]

        # Check if closing page bottom with two columns (Nơi nhận & Chữ ký)
        if by1 / h >= 0.50 and b_type != "table":
            # Check vertical projection of this bottom block
            sub = cleaned[by1:by2, :]
            v_p = sub.sum(axis=0)
            # Find vertical white space gutter in the middle (between 40% and 55% width)
            gutter_start = int(0.38 * w)
            gutter_end = int(0.55 * w)
            mid_min = v_p[gutter_start:gutter_end].min()
            if mid_min <= 2: # Clean vertical gutter found!
                gutter_x = gutter_start + np.argmin(v_p[gutter_start:gutter_end])
                # Left block (Nơi nhận)
                left_cols = np.where(v_p[:gutter_x] > 2)[0]
                if len(left_cols) > 0:
                    final_blocks.append({
                        "type": "list",
                        "label": "Danh sách (Nơi nhận)",
                        "bbox": (max(0, left_cols[0] - 6), by1, gutter_x - 4, by2),
                    })
                # Right block (Chữ ký / Dấu)
                right_cols = np.where(v_p[gutter_x:] > 2)[0]
                if len(right_cols) > 0:
                    final_blocks.append({
                        "type": "signature",
                        "label": "Chữ ký / Con dấu",
                        "bbox": (gutter_x + right_cols[0] - 4, by1, min(w, gutter_x + right_cols[-1] + 6), by2),
                    })
                continue

        final_blocks.append(blk)

    # Classify semantic types and labels
    regions = []
    for idx, blk in enumerate(final_blocks, 1):
        bx1, by1, bx2, by2 = blk["bbox"]
        top_pct = round(by1 / h * 100, 1)
        left_pct = round(bx1 / w * 100, 1)
        h_pct = round((by2 - by1) / h * 100, 1)
        w_pct = round((bx2 - bx1) / w * 100, 1)
        b_type = blk.get("type", "text")

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
        elif h_pct >= 8.0:
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
    regions = detect_page_layout_morphology(img, page_number=p_num)
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
        print(f"  [{idx}] type={r['type']:10s} label={r['label']:22s} top={r['top']:5.1f}% left={r['left']:5.1f}% w={r['width']:5.1f}% h={r['height']:5.1f}%")
        px1, py1, px2, py2 = r["px_coords"]
        draw.rectangle([px1, py1, px2, py2], outline=colors.get(r["type"], "yellow"), width=3)
    
    out_vis = f"scratch/final_morphology_page_{p_num}.png"
    vis.save(out_vis)
    print(f"Saved visualization to {out_vis}")
