import os
import sys
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

# Save an image of page 2 with line markers or print clusters
bg_level = float(np.percentile(arr_gray, 90))
ink_thresh = min(190, int(bg_level * 0.78))
cleaned = (arr_gray < ink_thresh).astype(np.int32)

# Find horizontal lines
row_ink = cleaned.sum(axis=1)
h_line_candidates = []
for y in range(h):
    if cleaned[y, int(w*0.2):int(w*0.8)].sum() > (w * 0.5):
        h_line_candidates.append(y)

print(f"Page 2 h={h}, w={w}")
print("Solid horizontal lines at y%:")
for y in h_line_candidates:
    print(f"  y = {y/h*100:.1f}% ({y}px)")

doc.close()
