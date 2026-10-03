import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf"
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

print(f"Page 1 size: {w}x{h}, bg_level={bg_level}, ink_thresh={ink_thresh}")

# Bridged horizontal lines
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
        max_len = np.max(lens)
        if max_len >= min_line_len:
            tbl_line_rows.append((y, max_len))

print(f"Found {len(tbl_line_rows)} horizontal scan rows with line >= {min_line_len}px:")
for y, mlen in tbl_line_rows:
    print(f"  y={y:4d} ({y/h*100:5.1f}%) max_len={mlen}px")
