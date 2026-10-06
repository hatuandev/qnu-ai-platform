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

arr_rgb = np.array(pil_img.convert("RGB"))
r_chan = arr_rgb[:, :, 0].astype(np.int32)
g_chan = arr_rgb[:, :, 1].astype(np.int32)
b_chan = arr_rgb[:, :, 2].astype(np.int32)
red_mask = (r_chan > 120) & ((r_chan - g_chan) > 35) & ((r_chan - b_chan) > 35)

red_y, red_x = np.where(red_mask)
if len(red_y) > 0:
    min_y, max_y = red_y.min(), red_y.max()
    min_x, max_x = red_x.min(), red_x.max()
    print(f"Red pixels: {len(red_y)}")
    print(f"Red box: x={min_x/w*100:.1f}% -> {max_x/w*100:.1f}%, y={min_y/h*100:.1f}% -> {max_y/h*100:.1f}%")

doc.close()
