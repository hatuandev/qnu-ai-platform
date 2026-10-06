import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pymupdf as fitz
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath("backend"))

# Load test bounded table logic and run the remaining steps of _detect_morphology_regions
pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
doc = fitz.open(pdf_path)
page2 = doc[1]
pix = page2.get_pixmap(dpi=150)
pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
w, h = pil_img.size
arr_gray = np.array(pil_img.convert("L"))
bg_level = float(np.percentile(arr_gray, 90))
ink_thresh = min(190, int(bg_level * 0.78))
cleaned = (arr_gray < ink_thresh).astype(np.int32)

# Red seal
arr_rgb = np.array(pil_img.convert("RGB"))
r_chan = arr_rgb[:, :, 0].astype(np.int32)
g_chan = arr_rgb[:, :, 1].astype(np.int32)
b_chan = arr_rgb[:, :, 2].astype(np.int32)
red_mask = (r_chan > 120) & ((r_chan - g_chan) > 35) & ((r_chan - b_chan) > 35)
has_seal = np.count_nonzero(red_mask) > 400
red_rows = np.where(red_mask.sum(axis=1) > 5)[0]
seal_y1 = max(0, red_rows[0] - 10)
seal_y2 = min(h, red_rows[-1] + 10)

# Table horizontal lines
min_h_solid_len = max(180, int(w * 0.35))
bridged_h = cleaned.copy()
for s in (1, 2, 3):
    bridged_h[:, :-s] |= cleaned[:, s:]
    bridged_h[:, s:] |= cleaned[:, :-s]
h_line_rows = []
for y in range(int(h*0.03), int(h*0.97)):
    row = bridged_h[y, :]
    diffs = np.diff(np.pad(row, (1, 1), "constant"))
    starts = np.where(diffs == 1)[0]
    ends = np.where(diffs == -1)[0]
    if len(starts) > 0 and len(ends) > 0:
        if np.any((ends - starts) >= min_h_solid_len):
            h_line_rows.append(y)

h_clusters = []
if h_line_rows:
    curr = [h_line_rows[0]]
    for r in h_line_rows[1:]:
        if r - curr[-1] <= 6:
            curr.append(r)
        else:
            if len(curr) <= 6:
                h_clusters.append(int(np.mean(curr)))
            curr = [r]
    if len(curr) <= 6:
        h_clusters.append(int(np.mean(curr)))

tbl_y1 = min(h_clusters)
tbl_y2 = max(h_clusters)

# Vertical table
v_min_x = int(0.10 * w)
v_max_x = int(0.91 * w)
table_boxes = [(v_min_x - 6, tbl_y1 - 4, v_max_x + 6, tbl_y2 + 4)]

# Outside lines
line_thresh = max(12, int(w * 0.012))
lines = []
in_line = False
start_y = 0
h_proj = cleaned.sum(axis=1)
for y in range(int(0.03*h), int(0.97*h)):
    if h_proj[y] > line_thresh:
        if not in_line:
            in_line = True
            start_y = y
    else:
        if in_line:
            in_line = False
            if y - start_y >= 4:
                lines.append((start_y, y))

outside_lines = [l for l in lines if not (max(l[0], table_boxes[0][1]) < min(l[1], table_boxes[0][3]))]

# Cluster
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

print(f"Clusters count: {len(clusters_lines)}")
for cl in clusters_lines:
    print(f"  Cluster: y={cl[0]/h*100:.1f}% -> {cl[1]/h*100:.1f}%")

all_raw = []
for (tx1, ty1, tx2, ty2) in table_boxes:
    all_raw.append({"type": "table", "bbox": (tx1, ty1, tx2, ty2)})

for cy1, cy2 in clusters_lines:
    sub = cleaned[cy1:cy2, :]
    cols = np.where(sub.sum(axis=0) > 2)[0]
    cx1 = max(0, cols[0] - 6) if len(cols) > 0 else 0
    cx2 = min(w, cols[-1] + 6) if len(cols) > 0 else w
    all_raw.append({"type": "text", "bbox": (cx1, cy1, cx2, cy2)})

# Process signing blocks
processed = []
for b in all_raw:
    bx1, by1, bx2, by2 = b["bbox"]
    bh_pct = (by2 - by1) / h * 100.0
    is_signing_area = (b["type"] != "table" and bh_pct >= 5.0 and has_seal and by1 <= seal_y2 and by2 >= (seal_y1 - int(0.04 * h)))
    if is_signing_area:
        sub = cleaned[by1:by2, :]
        v_p = sub.sum(axis=0)
        gutter_start = int(0.36 * w)
        gutter_end = int(0.55 * w)
        gutter_x = gutter_start + int(np.argmin(v_p[gutter_start:gutter_end]))
        left_cols = np.where(v_p[:gutter_x] > 2)[0]
        right_cols = np.where(v_p[gutter_x:] > 2)[0]
        processed.append({
            "type": "list",
            "label": "Nơi nhận",
            "bbox": (max(0, left_cols[0] - 6), by1, gutter_x - 4, by2),
        })
        processed.append({
            "type": "signature",
            "label": "Chữ ký / Con dấu",
            "bbox": (gutter_x + right_cols[0] - 4, by1, min(w, gutter_x + right_cols[-1] + 6), by2),
        })
    else:
        processed.append(b)

print(f"\nFinal blocks on page 2: {len(processed)}")
for p in processed:
    bx1, by1, bx2, by2 = p["bbox"]
    print(f"  [{p['type']:10s}] top={by1/h*100:5.1f}%, left={bx1/w*100:5.1f}%, w={(bx2-bx1)/w*100:5.1f}%, h={(by2-by1)/h*100:5.1f}% | label={p.get('label')}")

doc.close()
