import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pymupdf as fitz
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.layout_detector import SmartLayoutDetector

# Let's inspect the code of _detect_morphology_regions around table_boxes
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

# Red Stamp Detection
arr_rgb = np.array(pil_img.convert("RGB"))
r_chan = arr_rgb[:, :, 0].astype(np.int32)
g_chan = arr_rgb[:, :, 1].astype(np.int32)
b_chan = arr_rgb[:, :, 2].astype(np.int32)
red_mask = (r_chan > 120) & ((r_chan - g_chan) > 35) & ((r_chan - b_chan) > 35)
has_seal = np.count_nonzero(red_mask) > 400
seal_y1, seal_y2 = 0, 0
seal_x1, seal_x2 = 0, 0
if has_seal:
    red_rows = np.where(red_mask.sum(axis=1) > 5)[0]
    seal_y1 = max(0, red_rows[0] - 10)
    seal_y2 = min(h, red_rows[-1] + 10)
    red_cols = np.where(red_mask.sum(axis=0) > 5)[0]
    seal_x1 = max(0, red_cols[0] - 10)
    seal_x2 = min(w, red_cols[-1] + 10)

# Vertical lines
bridged_v = cleaned.copy()
for s in range(1, 7):
    bridged_v[:-s, :] |= cleaned[s:, :]
    bridged_v[s:, :] |= cleaned[:-s, :]

min_v_len = max(90, int(h * 0.06))
v_lines = []
for x in range(int(w*0.04), int(w*0.96)):
    col = bridged_v[:, x]
    diffs = np.diff(np.pad(col, (1, 1), "constant"))
    starts = np.where(diffs == 1)[0]
    ends = np.where(diffs == -1)[0]
    for st, en, l in zip(starts, ends, ends - starts):
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

# Horizontal grid lines
bridged_h = cleaned.copy()
for s in (1, 2, 3):
    bridged_h[:, :-s] |= cleaned[:, s:]
    bridged_h[:, s:] |= cleaned[:, :-s]

min_h_solid_len = max(180, int(w * 0.35))
h_line_rows = []
for y in range(int(h*0.03), int(h*0.97)):
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
            if len(curr) <= 6:
                h_clusters.append(int(np.mean(curr)))
            curr = [r]
    if len(curr) <= 6:
        h_clusters.append(int(np.mean(curr)))

print("v_clusters:", len(v_clusters))
print("h_clusters:", [f"{y/h*100:.1f}%" for y in h_clusters])

# Correct table box:
# Only vertical clusters that overlap with the table horizontal lines!
v_table = [item for item in v_clusters if item[1] <= max(h_clusters) and item[2] >= min(h_clusters)]
v_min_x = min(item[0] for item in v_table)
v_max_x = max(item[0] for item in v_table)
tbl_y1 = min(h_clusters)
tbl_y2 = max(h_clusters)
table_boxes = [(max(0, v_min_x - 6), max(0, tbl_y1 - 4), min(w, v_max_x + 6), min(h, tbl_y2 + 4))]

print(f"Table box: x={table_boxes[0][0]/w*100:.1f}% -> {table_boxes[0][2]/w*100:.1f}%, y={table_boxes[0][1]/h*100:.1f}% -> {table_boxes[0][3]/h*100:.1f}%")

# Now check lines outside table
h_proj = cleaned.sum(axis=1)
line_thresh = max(12, int(w * 0.012))
lines = []
in_line = False
start_y = 0
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

outside_lines = []
for (ly1, ly2) in lines:
    is_inside_tbl = False
    for (tx1, ty1, tx2, ty2) in table_boxes:
        if max(ly1, ty1) < min(ly2, ty2):
            is_inside_tbl = True
            break
    if not is_inside_tbl:
        outside_lines.append((ly1, ly2))

print(f"Outside lines count: {len(outside_lines)}")
for ly1, ly2 in outside_lines:
    print(f"  Outside line: y={ly1/h*100:.1f}% -> {ly2/h*100:.1f}%")

doc.close()
