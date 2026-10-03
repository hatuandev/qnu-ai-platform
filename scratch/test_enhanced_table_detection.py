import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

def detect_tables_enhanced(cleaned, w, h):
    margin_x1 = int(0.04 * w)
    margin_x2 = int(0.96 * w)
    margin_y1 = int(0.03 * h)
    margin_y2 = int(0.97 * h)

    # 1. Horizontal lines with gap bridging up to 8px
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

    # Cluster consecutive horizontal rows (line thickness)
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

    # 2. Vertical lines with gap bridging up to 6px
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

    # Cluster vertical lines by x
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

    print(f"Detected {len(h_clusters)} horizontal lines: {h_clusters}")
    print(f"Detected {len(v_clusters)} vertical column lines: {[(vx, f'{v_st}->{v_en}') for vx, v_st, v_en in v_clusters]}")

    table_boxes = []

    # Table candidate from vertical columns (if >= 3 vertical lines span similar y range)
    if len(v_clusters) >= 3:
        # Check if >= 3 vertical lines overlap vertically
        v_min_y = min(item[1] for item in v_clusters)
        v_max_y = max(item[2] for item in v_clusters)
        v_min_x = min(item[0] for item in v_clusters)
        v_max_x = max(item[0] for item in v_clusters)

        # Count how many vertical lines span at least 50% of this range
        overlapping_v = [item for item in v_clusters if max(0, min(item[2], v_max_y) - max(item[1], v_min_y)) >= (v_max_y - v_min_y) * 0.40]
        if len(overlapping_v) >= 3 and (v_max_x - v_min_x) >= int(w * 0.30):
            # We have a confirmed multi-column table grid!
            # Align with nearest horizontal lines if available
            tbl_y1 = v_min_y
            tbl_y2 = v_max_y

            # Check if there are horizontal lines near or within this range
            nearby_h = [hy for hy in h_clusters if (v_min_y - 30) <= hy <= (v_max_y + 30)]
            if nearby_h:
                tbl_y1 = min(tbl_y1, min(nearby_h))
                tbl_y2 = max(tbl_y2, max(nearby_h))

            # Expand 4px padding
            table_boxes.append((
                max(0, v_min_x - 6),
                max(0, tbl_y1 - 4),
                min(w, v_max_x + 6),
                min(h, tbl_y2 + 4)
            ))

    # Also check horizontal line clusters if not already covered by vertical
    if h_clusters and len(h_clusters) >= 2:
        curr_tbl_lines = [h_clusters[0]]
        for i in range(len(h_clusters) - 1):
            gap = h_clusters[i + 1] - h_clusters[i]
            if 18 <= gap <= 250:
                curr_tbl_lines.append(h_clusters[i + 1])
            else:
                if len(curr_tbl_lines) >= 2:
                    y1 = min(curr_tbl_lines) - 4
                    y2 = max(curr_tbl_lines) + 4
                    sub = cleaned[y1:y2, :]
                    cols = np.where(sub.sum(axis=0) > 3)[0]
                    if len(cols) >= 2 and (cols[-1] - cols[0]) >= int(w * 0.30):
                        # Check overlap with existing table_boxes
                        if not any(max(y1, ty1) < min(y2, ty2) for tx1, ty1, tx2, ty2 in table_boxes):
                            table_boxes.append((max(0, cols[0] - 6), y1, min(w, cols[-1] + 6), y2))
                curr_tbl_lines = [h_clusters[i + 1]]
        if len(curr_tbl_lines) >= 2:
            y1 = min(curr_tbl_lines) - 4
            y2 = max(curr_tbl_lines) + 4
            sub = cleaned[y1:y2, :]
            cols = np.where(sub.sum(axis=0) > 3)[0]
            if len(cols) >= 2 and (cols[-1] - cols[0]) >= int(w * 0.30):
                if not any(max(y1, ty1) < min(y2, ty2) for tx1, ty1, tx2, ty2 in table_boxes):
                    table_boxes.append((max(0, cols[0] - 6), y1, min(w, cols[-1] + 6), y2))

    return table_boxes

for pdf_name in [
    "TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf",
    "TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
]:
    pdf_path = f"docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/{pdf_name}"
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    w, h = pil_img.size
    arr_gray = np.array(pil_img.convert("L"))

    bg_level = float(np.percentile(arr_gray, 90))
    ink_thresh = min(190, int(bg_level * 0.78))
    cleaned = (arr_gray < ink_thresh).astype(np.int32)

    print(f"\n==========================================")
    print(f"Testing {pdf_name}")
    boxes = detect_tables_enhanced(cleaned, w, h)
    for b in boxes:
        print(f"Table box: x={b[0]} ({b[0]/w*100:.1f}%) to {b[2]} ({b[2]/w*100:.1f}%), y={b[1]} ({b[1]/h*100:.1f}%) to {b[3]} ({b[3]/h*100:.1f}%), h={(b[3]-b[1])/h*100:.1f}%")
