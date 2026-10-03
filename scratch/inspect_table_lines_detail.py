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

bg_level = float(np.percentile(arr_gray, 90))
ink_thresh = min(190, int(bg_level * 0.78))
cleaned = (arr_gray < ink_thresh).astype(np.int32)

# Bridged horizontal lines with gap up to 4
bridged_4 = cleaned.copy()
for s in [1, 2, 3, 4]:
    bridged_4[:, :-s] |= cleaned[:, s:]
    bridged_4[:, s:] |= cleaned[:, :-s]

# Bridged horizontal lines with gap up to 8
bridged_8 = cleaned.copy()
for s in range(1, 9):
    bridged_8[:, :-s] |= cleaned[:, s:]
    bridged_8[:, s:] |= cleaned[:, :-s]

for y in range(700, 1300):
    for b_name, b_arr in [("gap4", bridged_4), ("gap8", bridged_8)]:
        row = b_arr[y, :]
        diffs = np.diff(np.pad(row, (1, 1), "constant"))
        starts = np.where(diffs == 1)[0]
        ends = np.where(diffs == -1)[0]
        if len(starts) > 0 and len(ends) > 0:
            lens = ends - starts
            max_len = np.max(lens)
            if max_len >= 150:
                print(f"y={y:4d} ({y/h*100:5.1f}%) [{b_name}]: max_len={max_len:3d} (x={starts[np.argmax(lens)]} to {ends[np.argmax(lens)]})")
