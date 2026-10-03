import os
import pymupdf as fitz
import numpy as np
from PIL import Image

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

pix = page.get_pixmap(dpi=150)
os.makedirs("scratch", exist_ok=True)
out_png = "scratch/tb2618_page_1.png"
pix.save(out_png)

img = Image.open(out_png).convert("L")
arr = np.array(img)
h, w = arr.shape
print(f"Rendered {out_png}: {w}x{h} px")

# Find table lines
# Table lines are horizontal lines where many pixels across width are dark (< 150)
# Let's count dark pixels in each row
dark_counts = (arr < 150).sum(axis=1)

# Rows with at least 350 dark pixels (lines across table)
table_rows = [y for y, c in enumerate(dark_counts) if c > 350]
print("Candidate table line rows:", table_rows)
if table_rows:
    # Cluster consecutive rows
    clusters = []
    curr = [table_rows[0]]
    for r in table_rows[1:]:
        if r - curr[-1] <= 3:
            curr.append(r)
        else:
            clusters.append(int(np.mean(curr)))
            curr = [r]
    clusters.append(int(np.mean(curr)))
    print("Table line clusters (y in px):", clusters)
    for y in clusters:
        print(f"  Line at y={y} ({y/h*100:.2f}%)")

# Let's also check vertical lines to find table left and right
col_dark_counts = (arr[min(table_rows):max(table_rows), :] < 150).sum(axis=0)
v_table_cols = [x for x, c in enumerate(col_dark_counts) if c > (max(table_rows) - min(table_rows)) * 0.7]
print(f"Table x bounds: left={min(v_table_cols)} ({min(v_table_cols)/w*100:.2f}%), right={max(v_table_cols)} ({max(v_table_cols)/w*100:.2f}%)")
