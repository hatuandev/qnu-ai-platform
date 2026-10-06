import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pymupdf as fitz
import numpy as np
from PIL import Image

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

# Check red seal
arr_rgb = np.array(pil_img.convert("RGB"))
r_chan = arr_rgb[:, :, 0].astype(np.int32)
g_chan = arr_rgb[:, :, 1].astype(np.int32)
b_chan = arr_rgb[:, :, 2].astype(np.int32)
red_mask = (r_chan > 120) & ((r_chan - g_chan) > 35) & ((r_chan - b_chan) > 35)
print("Red pixels on page 2:", np.count_nonzero(red_mask))

# Check line detection
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

print(f"Total lines on page 2: {len(lines)}")
for ly1, ly2 in lines:
    pct_top = ly1 / h * 100
    pct_h = (ly2 - ly1) / h * 100
    print(f"  Line y={pct_top:.1f}% -> {(ly2/h*100):.1f}% (h={pct_h:.1f}%)")

doc.close()
