import sys
import numpy as np
from PIL import Image, ImageDraw
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

def detect_morphology_regions_pure_numpy(
    image_input,
    markdown_text: str = "",
    page_number: int = 1,
) -> list[dict]:
    """Detect high-precision visual layout regions using pure NumPy/Pillow morphology.
    Zero dependency on OpenCV C++.
    """
    if isinstance(image_input, str):
        pil_img = Image.open(image_input)
    elif isinstance(image_input, bytes):
        import io
        pil_img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, np.ndarray):
        pil_img = Image.fromarray(image_input)
    elif isinstance(image_input, Image.Image):
        pil_img = image_input
    else:
        return []

    rgb_img = pil_img.convert("RGB")
    gray_img = pil_img.convert("L")
    w, h = gray_img.size
    arr_gray = np.array(gray_img)
    arr_rgb = np.array(rgb_img)

    # 1. Red Stamp Detection (RGB color space invariant)
    # Red seals: High R, significantly higher than G and B
    r = arr_rgb[:, :, 0].astype(np.int16)
    g = arr_rgb[:, :, 1].astype(np.int16)
    b = arr_rgb[:, :, 2].astype(np.int16)
    
    red_mask = (r > 120) & ((r - g) > 35) & ((r - b) > 35) & (r * 2 > (g + b) * 1.3)
    # Ignore border margins for stamps
    margin_x1 = int(0.04 * w)
    margin_x2 = int(0.96 * w)
    margin_y1 = int(0.03 * h)
    margin_y2 = int(0.97 * h)
    red_mask_clean = np.zeros_like(red_mask)
    red_mask_clean[margin_y1:margin_y2, margin_x1:margin_x2] = red_mask[margin_y1:margin_y2, margin_x1:margin_x2]

    stamps = []
    # Project red mask to find stamp bounding boxes
    red_rows = np.where(red_mask_clean.sum(axis=1) > 15)[0]
    if len(red_rows) > 0:
        # Group contiguous red rows
        curr = [red_rows[0]]
        clusters = []
        for row in red_rows[1:]:
            if row - curr[-1] <= 10:
                curr.append(row)
            else:
                if len(curr) >= 25: # at least 25 pixels high
                    clusters.append((curr[0], curr[-1]))
                curr = [row]
        if len(curr) >= 25:
            clusters.append((curr[0], curr[-1]))
        
        for sy1, sy2 in clusters:
            sub = red_mask_clean[sy1:sy2, :]
            cols = np.where(sub.sum(axis=0) > 5)[0]
            if len(cols) >= 25: # at least 25 pixels wide
                sx1, sx2 = cols[0], cols[-1]
                stamp_w = sx2 - sx1
                stamp_h = sy2 - sy1
                # Circular or oval seal aspect ratio 0.6 to 1.6
                if 0.5 <= stamp_w / max(stamp_h, 1) <= 2.0:
                    stamps.append({
                        "type": "signature",
                        "label": "Con dấu",
                        "top": round(sy1 / h * 100, 1),
                        "left": round(sx1 / w * 100, 1),
                        "width": round(stamp_w / w * 100, 1),
                        "height": round(stamp_h / h * 100, 1),
                        "px_bbox": (sx1, sy1, sx2, sy2),
                    })

    # 2. Binarize gray image: dark ink vs light paper
    # Calculate background level using 90th percentile of image brightness
    bg_level = np.percentile(arr_gray, 90)
    ink_thresh = min(190, int(bg_level * 0.78))
    binary = (arr_gray < ink_thresh).astype(np.uint8)

    # Clean scanner bed border noise
    cleaned = np.zeros_like(binary)
    cleaned[margin_y1:margin_y2, margin_x1:margin_x2] = binary[margin_y1:margin_y2, margin_x1:margin_x2]

    # 3. Detect Table Grid Lines (Mathematical Morphology on 2D matrix)
    # Horizontal line filter: horizontal run-length >= 120 pixels
    # We can detect this with 1D convolution / moving average
    kernel_len = max(60, int(w * 0.12))
    h_kernel = np.ones(kernel_len, dtype=np.uint8)
    
    # Check rows with dense continuous horizontal segments
    # Fast row-wise check: count run-lengths of consecutive 1s
    table_horizontal_lines = []
    for y_idx in range(margin_y1, margin_y2):
        row = cleaned[y_idx, :]
        # Vectorized check: run length of 1s
        # Where row is 1, compute cumulative sum
        diffs = np.diff(np.pad(row, (1, 1), 'constant'))
        starts = np.where(diffs == 1)[0]
        ends = np.where(diffs == -1)[0]
        if len(starts) > 0 and len(ends) > 0:
            lens = ends - starts
            if np.any(lens >= kernel_len):
                table_horizontal_lines.append(y_idx)

    # Cluster table horizontal lines into tables
    table_boxes = []
    if table_horizontal_lines:
        curr_lines = [table_horizontal_lines[0]]
        tbl_line_clusters = []
        for line_y in table_horizontal_lines[1:]:
            if line_y - curr_lines[-1] <= 6:
                # Same physical drawn line (thickness > 1px)
                curr_lines.append(line_y)
            else:
                tbl_line_clusters.append(int(np.mean(curr_lines)))
                curr_lines = [line_y]
        tbl_line_clusters.append(int(np.mean(curr_lines)))

        # If there are >= 2 distinct horizontal lines within a reasonable distance (table height between 40px and 800px)
        if len(tbl_line_clusters) >= 2:
            # Group lines into table blocks
            tbl_start = tbl_line_clusters[0]
            for i in range(len(tbl_line_clusters) - 1):
                gap = tbl_line_clusters[i+1] - tbl_line_clusters[i]
                if gap > 200: # gap between tables or distant lines
                    tbl_end = tbl_line_clusters[i]
                    if tbl_end - tbl_start >= 40:
                        # Find left and right bounds of table
                        sub_img = cleaned[tbl_start:tbl_end, :]
                        v_counts = sub_img.sum(axis=0)
                        cols = np.where(v_counts > (tbl_end - tbl_start) * 0.3)[0]
                        if len(cols) >= 2:
                            table_boxes.append((cols[0], tbl_start, cols[-1], tbl_end))
                    tbl_start = tbl_line_clusters[i+1]
            
            tbl_end = tbl_line_clusters[-1]
            if tbl_end - tbl_start >= 40:
                sub_img = cleaned[tbl_start:tbl_end, :]
                v_counts = sub_img.sum(axis=0)
                # Find columns with vertical grid lines or table boundaries
                cols = np.where(v_counts > 5)[0]
                if len(cols) >= 2:
                    tx1 = max(0, cols[0] - 4)
                    tx2 = min(w, cols[-1] + 4)
                    table_boxes.append((tx1, tbl_start, tx2, tbl_end))

    # 4. Horizontal Projection Profile for Text Segmentation
    h_proj = cleaned.sum(axis=1)
    line_thresh = max(12, int(w * 0.012)) # at least ~15 dark pixels in row
    in_line = False
    start_y = 0
    raw_lines = []

    for y in range(margin_y1, margin_y2):
        if h_proj[y] > line_thresh:
            if not in_line:
                in_line = True
                start_y = y
        else:
            if in_line:
                in_line = False
                if y - start_y >= 4:
                    raw_lines.append((start_y, y))
    if in_line and (margin_y2 - start_y >= 4):
        raw_lines.append((start_y, margin_y2))

    # Calculate inter-line gaps
    gaps = [raw_lines[i+1][0] - raw_lines[i][1] for i in range(len(raw_lines) - 1)]
    median_gap = np.median(gaps) if gaps else 12.0
    paragraph_split_gap = max(18.0, median_gap * 1.7)

    # Group lines into blocks, keeping table regions separate
    clusters = []
    curr_cluster = [raw_lines[0]] if raw_lines else []

    for i in range(len(raw_lines) - 1):
        l_curr = raw_lines[i]
        l_next = raw_lines[i+1]
        gap = l_next[0] - l_curr[1]

        # Check if crossing table boundary
        crossing_table = False
        for (tx1, ty1, tx2, ty2) in table_boxes:
            if (l_curr[1] <= ty1 and l_next[0] >= ty1) or (l_curr[1] <= ty2 and l_next[0] >= ty2):
                crossing_table = True
                break

        if gap > paragraph_split_gap or crossing_table:
            clusters.append((curr_cluster[0][0], curr_cluster[-1][1]))
            curr_cluster = [l_next]
        else:
            curr_cluster.append(l_next)
    if curr_cluster:
        clusters.append((curr_cluster[0][0], curr_cluster[-1][1]))

    # Merge table boxes if any cluster overlaps heavily with a table
    final_regions = []

    for cy1, cy2 in clusters:
        # Check if this cluster is part of a table
        is_table = False
        for (tx1, ty1, tx2, ty2) in table_boxes:
            # Overlap in y >= 50%
            inter_y1 = max(cy1, ty1)
            inter_y2 = min(cy2, ty2)
            if inter_y2 > inter_y1:
                inter_h = inter_y2 - inter_y1
                if inter_h / (cy2 - cy1) >= 0.5:
                    is_table = True
                    break
        
        # Calculate horizontal bounds
        block_slice = cleaned[cy1:cy2, :]
        v_proj = block_slice.sum(axis=0)
        nonzero_cols = np.where(v_proj > 2)[0]
        if len(nonzero_cols) > 0:
            cx1 = max(0, nonzero_cols[0] - 6)
            cx2 = min(w, nonzero_cols[-1] + 6)
        else:
            cx1, cx2 = margin_x1, margin_x2

        top_pct = round(cy1 / h * 100, 1)
        left_pct = round(cx1 / w * 100, 1)
        height_pct = round((cy2 - cy1) / h * 100, 1)
        width_pct = round((cx2 - cx1) / w * 100, 1)

        # Classify region based on administrative semantics
        if is_table:
            r_type = "table"
            r_label = "Bảng dữ liệu"
        elif page_number == 1 and top_pct <= 14.0:
            r_type = "header"
            r_label = "Phần đầu văn bản"
        elif page_number == 1 and top_pct <= 22.0 and height_pct <= 8.0:
            r_type = "title"
            r_label = "Tiêu đề"
        elif top_pct >= 50.0 and left_pct >= 45.0:
            # Check for signature on closing page
            r_type = "signature"
            r_label = "Chữ ký / Nơi nhận"
        elif height_pct >= 8.0:
            r_type = "list"
            r_label = "Danh sách"
        else:
            r_type = "text"
            r_label = "Khối văn bản"

        final_regions.append({
            "type": r_type,
            "label": r_label,
            "top": top_pct,
            "left": left_pct,
            "width": width_pct,
            "height": height_pct,
            "px_coords": (cx1, cy1, cx2, cy2),
        })

    # Combine adjacent table slices into unified table box if needed
    unified_regions = []
    i = 0
    while i < len(final_regions):
        curr = final_regions[i]
        if curr["type"] == "table" and i + 1 < len(final_regions) and final_regions[i+1]["type"] == "table":
            nxt = final_regions[i+1]
            # Merge curr and nxt
            merged_top = curr["top"]
            merged_bot = nxt["top"] + nxt["height"]
            merged_left = min(curr["left"], nxt["left"])
            merged_right = max(curr["left"] + curr["width"], nxt["left"] + nxt["width"])
            curr["top"] = merged_top
            curr["height"] = round(merged_bot - merged_top, 1)
            curr["left"] = merged_left
            curr["width"] = round(merged_right - merged_left, 1)
            unified_regions.append(curr)
            i += 2
        else:
            unified_regions.append(curr)
            i += 1

    return unified_regions

# Test on page 1 and page 2 of TB2618
pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)

for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    regions = detect_morphology_regions_pure_numpy(img, page_number=p_num)
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
        print(f"  [{idx}] type={r['type']:10s} label={r['label']:20s} top={r['top']:5.1f}% left={r['left']:5.1f}% w={r['width']:5.1f}% h={r['height']:5.1f}%")
        px1, py1, px2, py2 = r["px_coords"]
        draw.rectangle([px1, py1, px2, py2], outline=colors.get(r["type"], "yellow"), width=3)
    
    out_vis = f"scratch/proto_page_{p_num}_blocks.png"
    vis.save(out_vis)
    print(f"Saved visualization to {out_vis}")
