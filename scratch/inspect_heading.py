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

# Inspect rows from y = 650 to 760
for y in range(680, 755, 5):
    sub = cleaned[y:y+5, :]
    cols = np.where(sub.sum(axis=0) > 1)[0]
    if len(cols) > 0:
        print(f"y={y}-{y+5} ({y/h*100:.1f}%): cols={cols[0]} ({cols[0]/w*100:.1f}%) to {cols[-1]} ({cols[-1]/w*100:.1f}%) total_ink={sub.sum()}")
