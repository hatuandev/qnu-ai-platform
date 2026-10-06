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
has_seal = np.count_nonzero(red_mask) > 400
if has_seal:
    red_rows = np.where(red_mask.sum(axis=1) > 5)[0]
    seal_y1 = max(0, red_rows[0] - 10)
    seal_y2 = min(h, red_rows[-1] + 10)
    red_cols = np.where(red_mask.sum(axis=0) > 5)[0]
    seal_x1 = max(0, red_cols[0] - 10)
    seal_x2 = min(w, red_cols[-1] + 10)
    print(f"Red seal: x={seal_x1/w*100:.1f}% -> {seal_x2/w*100:.1f}%, y={seal_y1/h*100:.1f}% -> {seal_y2/h*100:.1f}%")

# Table horizontal lines
h_clusters = [143, 471, 702]
tbl_y1 = min(h_clusters)
tbl_y2 = max(h_clusters)
print(f"Correct table: top={tbl_y1/h*100:.1f}%, bottom={tbl_y2/h*100:.1f}%, h={(tbl_y2-tbl_y1)/h*100:.1f}%")

doc.close()
