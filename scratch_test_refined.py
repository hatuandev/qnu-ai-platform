import numpy as np
from PIL import Image, ImageDraw
import pymupdf as fitz

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)
page = doc[0]
pix = page.get_pixmap(dpi=150)
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
arr_gray = np.array(img.convert("L"))
h, w = arr_gray.shape

# Threshold
margin_x1 = int(0.04 * w)
margin_x2 = int(0.96 * w)
margin_y1 = int(0.03 * h)
margin_y2 = int(0.97 * h)

bg_level = np.percentile(arr_gray, 90)
ink_thresh = min(190, int(bg_level * 0.78))
binary = (arr_gray < ink_thresh).astype(np.uint8)
cleaned = np.zeros_like(binary)
cleaned[margin_y1:margin_y2, margin_x1:margin_x2] = binary[margin_y1:margin_y2, margin_x1:margin_x2]

# Horizontal line extraction (table lines)
kernel_len = max(60, int(w * 0.12))
tbl_lines = []
for y in range(margin_y1, margin_y2):
    row = cleaned[y, :]
    diffs = np.diff(np.pad(row, (1, 1), 'constant'))
    starts = np.where(diffs == 1)[0]
    ends = np.where(diffs == -1)[0]
    if len(starts) > 0 and len(ends) > 0:
        if np.any((ends - starts) >= kernel_len):
            tbl_lines.append(y)

table_box = None
if tbl_lines:
    t_y1 = min(tbl_lines)
    t_y2 = max(tbl_lines)
    sub = cleaned[t_y1:t_y2, :]
    cols = np.where(sub.sum(axis=0) > 3)[0]
    if len(cols) >= 2:
        table_box = (cols[0] - 4, t_y1 - 4, cols[-1] + 4, t_y2 + 4)
        print(f"Detected Table Box: x={table_box[0]}..{table_box[2]} ({table_box[0]/w*100:.1f}%..{table_box[2]/w*100:.1f}%), y={table_box[1]}..{table_box[3]} ({table_box[1]/h*100:.1f}%..{table_box[3]/h*100:.1f}%)")

# Extract lines
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

# Segment blocks using gap threshold = 17px
# In our gap inspection:
# Intra-line in paragraph = 11-13px
# Inter-paragraph / Inter-section = 17-59px
split_thresh = 16.5

clusters = []
curr = [lines[0]]
for i in range(len(lines) - 1):
    gap = lines[i+1][0] - lines[i][1]
    
    # If this line is inside table, don't split within table
    in_table_curr = table_box and (table_box[1] <= lines[i][0] <= table_box[3])
    in_table_next = table_box and (table_box[1] <= lines[i+1][0] <= table_box[3])
    
    if (gap > split_thresh and not (in_table_curr and in_table_next)) or (in_table_curr != in_table_next):
        clusters.append((curr[0][0], curr[-1][1]))
        curr = [lines[i+1]]
    else:
        curr.append(lines[i+1])
if curr:
    clusters.append((curr[0][0], curr[-1][1]))

print(f"\nTotal clusters with threshold 16.5px: {len(clusters)}")
vis = img.copy()
draw = ImageDraw.Draw(vis)

for idx, (cy1, cy2) in enumerate(clusters, 1):
    sub = cleaned[cy1:cy2, :]
    cols = np.where(sub.sum(axis=0) > 2)[0]
    cx1 = max(0, cols[0] - 6) if len(cols) > 0 else margin_x1
    cx2 = min(w, cols[-1] + 6) if len(cols) > 0 else margin_x2
    
    top_pct = cy1 / h * 100
    left_pct = cx1 / w * 100
    h_pct = (cy2 - cy1) / h * 100
    w_pct = (cx2 - cx1) / w * 100
    
    # Check if table
    is_tbl = table_box and (max(cy1, table_box[1]) < min(cy2, table_box[3]))
    
    label = "table" if is_tbl else ("header" if top_pct < 15 else ("title" if top_pct < 22 else "text"))
    print(f"  [{idx}] {label:8s} top={top_pct:5.1f}%, left={left_pct:5.1f}%, w={w_pct:5.1f}%, h={h_pct:5.1f}% (px: y={cy1}..{cy2}, x={cx1}..{cx2})")
    draw.rectangle([cx1, cy1, cx2, cy2], outline="cyan" if is_tbl else "red", width=3)

vis.save("scratch/test_refined_morphology.png")
print("Saved scratch/test_refined_morphology.png")
