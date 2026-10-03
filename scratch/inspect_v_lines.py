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

# Inspect rows 1260-1280
for y in range(1260, 1275):
    row = cleaned[y, :]
    total_ink = np.sum(row[180:1100])
    print(f"y={y}: total_ink={total_ink}")

# Let's inspect vertical grid lines of the table as well
# In a ruled table, vertical grid lines run from top to bottom of the table!
v_proj = cleaned[750:1280, :].sum(axis=0)
v_cols = np.where(v_proj > 250)[0]
print("Strong vertical column lines in table region:", v_cols)
