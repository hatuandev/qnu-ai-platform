import sys
import numpy as np
from PIL import Image
import pymupdf as fitz

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)
page = doc[0]
pix = page.get_pixmap(dpi=150)
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("L")
arr = np.array(img)
h, w = arr.shape

margin_x1 = int(0.04 * w)
margin_x2 = int(0.96 * w)
margin_y1 = int(0.03 * h)
margin_y2 = int(0.97 * h)

bg_level = np.percentile(arr, 90)
ink_thresh = min(190, int(bg_level * 0.78))
binary = (arr < ink_thresh).astype(np.uint8)

cleaned = np.zeros_like(binary)
cleaned[margin_y1:margin_y2, margin_x1:margin_x2] = binary[margin_y1:margin_y2, margin_x1:margin_x2]

# Look at y from 900 to 1700 (Block 8 and Block 9)
h_proj = cleaned.sum(axis=1)
line_thresh = max(12, int(w * 0.012))

in_line = False
lines = []
start_y = 0
for y in range(margin_y1, margin_y2):
    if h_proj[y] > line_thresh:
        if not in_line:
            in_line = True
            start_y = y
    else:
        if in_line:
            in_line = False
            if y - start_y >= 4:
                lines.append((start_y, y))

print(f"Total lines: {len(lines)}")
for i in range(len(lines) - 1):
    gap = lines[i+1][0] - lines[i][1]
    y_mid = (lines[i][1] + lines[i+1][0]) / 2.0
    print(f"Line {i} (y={lines[i][0]}..{lines[i][1]}, {lines[i][0]/h*100:.1f}%) -> Line {i+1}: gap = {gap}px ({gap/h*100:.2f}%)")
