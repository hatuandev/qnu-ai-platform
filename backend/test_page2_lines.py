import pymupdf as fitz
import numpy as np
from PIL import Image
import sys

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"d:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf"
doc = fitz.open(pdf_path)

page2 = doc[1]
pix = page2.get_pixmap(dpi=150)
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

# Check vertical lines
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

print(f"Page 2: v_lines count: {len(v_lines)}")
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

print(f"Page 2: v_clusters: {len(v_clusters)}")
for vc in v_clusters:
    print(f"  v_col x={vc[0]} (x%={vc[0]/w*100:.1f}%), y={vc[1]}-{vc[2]} (len={vc[2]-vc[1]})")

# Check horizontal lines
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

print(f"Page 2: h_line_rows count: {len(h_line_rows)}")
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

print(f"Page 2: h_clusters: {len(h_clusters)}")
for hy in h_clusters:
    print(f"  h_line y={hy} (y%={hy/h*100:.1f}%)")
