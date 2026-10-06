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
arr_rgb = np.array(pil_img.convert("RGB"))

bg_level = float(np.percentile(arr_gray, 90))
print("bg_level:", bg_level)
y_bottom = int(0.65 * h)
sub_gray = arr_gray[y_bottom:, :]
print("Min gray in bottom:", sub_gray.min(), "Mean gray in bottom:", sub_gray.mean())
print("Histogram of gray in bottom:")
hist, bins = np.histogram(sub_gray, bins=[0, 50, 100, 150, 180, 200, 220, 255])
for b, count in zip(bins[:-1], hist):
    print(f"  [{b}..]: {count}")

# Check lines with darker pixels
ink_mask = (sub_gray < 220)
h_proj_bottom = ink_mask.sum(axis=1)
print(f"Rows with ink_mask > 20: {np.count_nonzero(h_proj_bottom > 20)} out of {len(h_proj_bottom)}")

doc.close()
