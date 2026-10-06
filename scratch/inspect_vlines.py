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
bg_level = float(np.percentile(arr_gray, 90))
ink_thresh = min(190, int(bg_level * 0.78))
cleaned = (arr_gray < ink_thresh).astype(np.int32)

bridged_v = cleaned.copy()
for s in range(1, 7):
    bridged_v[:-s, :] |= cleaned[s:, :]
    bridged_v[s:, :] |= cleaned[:-s, :]

min_v_len = max(90, int(h * 0.06))
v_lines = []
for x in range(int(w*0.04), int(w*0.96)):
    col = bridged_v[:, x]
    diffs = np.diff(np.pad(col, (1, 1), "constant"))
    starts = np.where(diffs == 1)[0]
    ends = np.where(diffs == -1)[0]
    for st, en, l in zip(starts, ends, ends - starts):
        if l >= min_v_len:
            v_lines.append((x, st, en))

print(f"Total v_lines: {len(v_lines)}")
for vl in v_lines[:20]:
    print(f"  x={vl[0]/w*100:.1f}%, y={vl[1]/h*100:.1f}% -> {vl[2]/h*100:.1f}% (len={vl[2]-vl[1]}px)")

doc.close()
