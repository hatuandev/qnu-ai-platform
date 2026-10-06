import sys
import numpy as np
from PIL import Image, ImageDraw
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

def detect_page_layout_smart_morphology(
    img_rgb: Image.Image,
    page_number: int = 1,
    is_closing_page: bool = False,
    page_markdown: str = "",
) -> list[dict]:
    """Pure NumPy & Pillow Morphological Document Layout Detector.
    Strictly invariant-based, zero hardcoded words, zero OpenCV C++ dependency.
    """
    w, h = img_rgb.size
    arr_gray = np.array(img_rgb.convert("L"))
    arr_rgb = np.array(img_rgb)

    margin_x1 = int(0.04 * w)
    margin_x2 = int(0.96 * w)
    margin_y1 = int(0.03 * h)
    margin_y2 = int(0.97 * h)

    # 1. Binarize using dynamic ink threshold
    bg_level = np.percentile(arr_gray, 90)
    ink_thresh = min(190, int(bg_level * 0.78))
    cleaned = (arr_gray < ink_thresh).astype(np.int32)
    cleaned[:margin_y1, :] = 0
    cleaned[margin_y2:, :] = 0
    cleaned[:, :margin_x1] = 0
    cleaned[:, margin_x2:] = 0

    # 2. Horizontal Projection Profile
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

    if not lines:
        return []

    # 3. Line properties: compute horizontal bounds for each line
    line_info = []
    for (ly1, ly2) in lines:
        sub = cleaned[ly1:ly2, :]
        cols = np.where(sub.sum(axis=0) > 2)[0]
        if len(cols) > 0:
            lx1 = max(0, cols[0] - 6)
            lx2 = min(w, cols[-1] + 6)
        else:
            lx1, lx2 = margin_x1, margin_x2
        line_info.append({
            "y1": ly1,
            "y2": ly2,
            "x1": lx1,
            "x2": lx2,
            "w": lx2 - lx1,
            "h": ly2 - ly1,
        })

    # 4. Group lines into candidate clusters
    # Intra-line gap is typically 11-13px, section gap is >= 16.5px
    split_thresh = 16.5
    raw_clusters = []
    curr = [line_info[0]]
    for i in range(len(line_info) - 1):
        gap = line_info[i+1]["y1"] - line_info[i]["y2"]
        if gap >= split_thresh:
            raw_clusters.append(curr)
            curr = [line_info[i+1]]
        else:
            curr.append(line_info[i+1])
    if curr:
        raw_clusters.append(curr)

    # Convert line clusters to bounding boxes
    blocks = []
    for c_lines in raw_clusters:
        cy1 = min(l["y1"] for l in c_lines)
        cy2 = max(l["y2"] for l in c_lines)
        cx1 = min(l["x1"] for l in c_lines)
        cx2 = max(l["x2"] for l in c_lines)
        blocks.append({
            "x1": cx1,
            "y1": cy1,
            "x2": cx2,
            "y2": cy2,
            "line_count": len(c_lines),
        })

    # 5. Detect Ruled Tables by column alignment invariance
    # Consecutive blocks with identical left margins (diff <= 15px) and identical widths (diff <= 15px)
    # and width between 40% and 85% of page width are table rows!
    merged_blocks = []
    i = 0
    while i < len(blocks):
        b_curr = blocks[i]
        curr_w = b_curr["x2"] - b_curr["x1"]
        # Check if start of a table
        if 0.40 * w <= curr_w <= 0.85 * w:
            tbl_group = [b_curr]
            j = i + 1
            while j < len(blocks):
                b_next = blocks[j]
                next_w = b_next["x2"] - b_next["x1"]
                # Column alignment invariant: left margin within 20px, width within 25px
                if abs(b_next["x1"] - b_curr["x1"]) <= 22 and abs(next_w - curr_w) <= 25:
                    tbl_group.append(b_next)
                    j += 1
                else:
                    break
            if len(tbl_group) >= 2:
                # Merge into unified table
                tx1 = min(b["x1"] for b in tbl_group)
                ty1 = min(b["y1"] for b in tbl_group)
                tx2 = max(b["x2"] for b in tbl_group)
                ty2 = max(b["y2"] for b in tbl_group)
                merged_blocks.append({
                    "x1": tx1,
                    "y1": ty1,
                    "x2": tx2,
                    "y2": ty2,
                    "type": "table",
                    "label": "Bảng dữ liệu",
                })
                i = j
                continue

        merged_blocks.append(b_curr)
        i += 1

    # 6. Merge Header (Page 1 top blocks <= 14% height)
    final_blocks = []
    if page_number == 1:
        hdr_group = [b for b in merged_blocks if (b["y1"] / h) <= 0.14]
        other_group = [b for b in merged_blocks if (b["y1"] / h) > 0.14]
        if hdr_group:
            hx1 = min(b["x1"] for b in hdr_group)
            hy1 = min(b["y1"] for b in hdr_group)
            hx2 = max(b["x2"] for b in hdr_group)
            hy2 = max(b["y2"] for b in hdr_group)
            final_blocks.append({
                "x1": hx1,
                "y1": hy1,
                "x2": hx2,
                "y2": hy2,
                "type": "header",
                "label": "Phần đầu văn bản",
            })
        final_blocks.extend(other_group)
    else:
        final_blocks = merged_blocks

    # 7. Merge sub-items for lists (e.g. section title + bullet items)
    # If a short block is immediately followed by a large text block with gap <= 28px, they form a cohesive section
    i = 0
    cohesive_blocks = []
    while i < len(final_blocks):
        b1 = final_blocks[i]
        if b1.get("type") in ("table", "header"):
            cohesive_blocks.append(b1)
            i += 1
            continue

        b1_w = b1["x2"] - b1["x1"]
        b1_h = b1["y2"] - b1["y1"]
        
        # Check if b1 is a section heading (short width <= 45% or height <= 25px) followed by its bullets
        if i + 1 < len(final_blocks):
            b2 = final_blocks[i + 1]
            gap = b2["y1"] - b1["y2"]
            if b2.get("type") not in ("table", "header") and b1_w <= 0.45 * w and gap <= 30:
                # Merge b1 and b2 into one section box
                cohesive_blocks.append({
                    "x1": min(b1["x1"], b2["x1"]),
                    "y1": b1["y1"],
                    "x2": max(b1["x2"], b2["x2"]),
                    "y2": b2["y2"],
                    "type": "list" if (b2["y2"] - b1["y1"]) >= 0.08 * h else "text",
                    "label": "Danh sách" if (b2["y2"] - b1["y1"]) >= 0.08 * h else "Khối văn bản",
                })
                i += 2
                continue

        cohesive_blocks.append(b1)
        i += 1

    # 8. Closing Page bottom dual column (Nơi nhận & Chữ ký)
    processed_blocks = []
    for b in cohesive_blocks:
        by1 = b["y1"]
        by2 = b["y2"]
        if is_closing_page and (by1 / h) >= 0.50 and b.get("type") != "table":
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
                        "x1": max(0, left_cols[0] - 6),
                        "y1": by1,
                        "x2": gutter_x - 4,
                        "y2": by2,
                        "type": "list",
                        "label": "Danh sách",
                    })
                    processed_blocks.append({
                        "x1": gutter_x + right_cols[0] - 4,
                        "y1": by1,
                        "x2": min(w, gutter_x + right_cols[-1] + 6),
                        "y2": by2,
                        "type": "signature",
                        "label": "Chữ ký / Nơi nhận",
                    })
                    continue
        processed_blocks.append(b)

    # 9. Format output with percentage coordinates
    result = []
    for idx, b in enumerate(processed_blocks, 1):
        top_pct = round(b["y1"] / h * 100, 1)
        left_pct = round(b["x1"] / w * 100, 1)
        w_pct = round((b["x2"] - b["x1"]) / w * 100, 1)
        h_pct = round((b["y2"] - b["y1"]) / h * 100, 1)
        
        b_type = b.get("type")
        if not b_type:
            if page_number == 1 and top_pct <= 14.0:
                b_type = "header"
            elif page_number == 1 and top_pct <= 22.0:
                b_type = "title"
            elif h_pct >= 6.0:
                b_type = "list"
            else:
                b_type = "text"

        label_map = {
            "header": "Phần đầu văn bản",
            "title": "Tiêu đề",
            "table": "Bảng dữ liệu",
            "list": "Danh sách",
            "signature": "Chữ ký / Nơi nhận",
            "text": "Khối văn bản",
        }

        result.append({
            "type": b_type,
            "label": label_map.get(b_type, "Khối văn bản"),
            "top": top_pct,
            "left": left_pct,
            "width": w_pct,
            "height": h_pct,
            "px_coords": (b["x1"], b["y1"], b["x2"], b["y2"]),
        })

    return result

# Run on TB2618
pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)

for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    is_closing = (p_num == len(doc))
    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    regions = detect_page_layout_smart_morphology(img, page_number=p_num, is_closing_page=is_closing)
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
    
    out_vis = f"scratch/smart_morphology_page_{p_num}.png"
    vis.save(out_vis)
    print(f"Saved visualization to {out_vis}")
