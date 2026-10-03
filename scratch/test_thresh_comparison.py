import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)
page = doc[0]
pix = page.get_pixmap(dpi=150)
pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

w, h = pil_img.size
arr_gray = np.array(pil_img.convert("L"))

margin_x1 = int(0.04 * w)
margin_x2 = int(0.96 * w)
margin_y1 = int(0.03 * h)
margin_y2 = int(0.97 * h)

bg_level = float(np.percentile(arr_gray, 90))
ink_thresh = min(190, int(bg_level * 0.78))
cleaned = (arr_gray < ink_thresh).astype(np.int32)
cleaned[:margin_y1, :] = 0
cleaned[margin_y2:, :] = 0
cleaned[:, :margin_x1] = 0
cleaned[:, margin_x2:] = 0

# Table line detection
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
        y1 = min(clusters) - 4
        y2 = max(clusters) + 4
        sub = cleaned[y1:y2, :]
        cols = np.where(sub.sum(axis=0) > 3)[0]
        if len(cols) >= 2:
            tx1 = max(0, cols[0] - 6)
            tx2 = min(w, cols[-1] + 6)
            above_slice = cleaned[max(0, y1 - 120):y1, :]
            above_cols = np.where(above_slice.sum(axis=0) > 3)[0]
            if len(above_cols) >= 2 and (above_cols[-1] - above_cols[0]) >= 0.40 * w:
                above_rows = np.where(above_slice.sum(axis=1) > 10)[0]
                if len(above_rows) > 0:
                    y1 = max(0, y1 - 120 + above_rows[0] - 4)
            table_boxes.append((tx1, y1, tx2, y2))

# Text lines
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
    is_tbl = any(max(ly1, ty1) < min(ly2, ty2) for (tx1, ty1, tx2, ty2) in table_boxes)
    if not is_tbl:
        outside_lines.append((ly1, ly2))

for thresh in [16.5, 20.0, 24.0, 28.0]:
    clusters = []
    if outside_lines:
        curr = [outside_lines[0]]
        for i in range(len(outside_lines) - 1):
            gap = outside_lines[i + 1][0] - outside_lines[i][1]
            if gap >= thresh:
                clusters.append((curr[0][0], curr[-1][1]))
                curr = [outside_lines[i + 1]]
            else:
                curr.append(outside_lines[i + 1])
        if curr:
            clusters.append((curr[0][0], curr[-1][1]))
    print(f"\n--- split_thresh = {thresh}px ({len(clusters)} text clusters) ---")
    for cy1, cy2 in clusters:
        print(f"  y={cy1/h*100:5.1f}% to {cy2/h*100:5.1f}% (h={(cy2-cy1)/h*100:4.1f}%)")
