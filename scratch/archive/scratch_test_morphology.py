import numpy as np
from PIL import Image, ImageDraw

img = Image.open("scratch/tb2618_page_1.png").convert("L")
arr = np.array(img)
h, w = arr.shape

# 1. Binarize: dark ink vs white paper
# White paper is > 220, dark text/lines are < 180
binary = (arr < 180).astype(np.uint8)

# Remove scanner border noise: zero out margins outside 4% to 96% width and 3% to 97% height
margin_x_left = int(0.06 * w)
margin_x_right = int(0.94 * w)
margin_y_top = int(0.03 * h)
margin_y_bot = int(0.97 * h)

cleaned = np.zeros_like(binary)
cleaned[margin_y_top:margin_y_bot, margin_x_left:margin_x_right] = binary[margin_y_top:margin_y_bot, margin_x_left:margin_x_right]

# 2. Horizontal Projection Profile (count ink pixels per line)
h_proj = cleaned.sum(axis=1)

# Find text line bands (where h_proj > threshold)
line_thresh = int(0.015 * w) # At least ~18 ink pixels in a row
in_line = False
line_bands = []
start_y = 0

for y in range(h):
    if h_proj[y] > line_thresh:
        if not in_line:
            in_line = True
            start_y = y
    else:
        if in_line:
            in_line = False
            if y - start_y >= 5: # Line height at least 5px
                line_bands.append((start_y, y))

print(f"Detected {len(line_bands)} raw text/table lines:")

# Group lines into paragraph/block clusters based on vertical gap (inter-line gap vs inter-paragraph gap)
gaps = []
for i in range(len(line_bands) - 1):
    gap = line_bands[i+1][0] - line_bands[i][1]
    gaps.append(gap)

median_gap = np.median(gaps) if gaps else 10
paragraph_gap_thresh = max(18, median_gap * 1.8)
print(f"Median line gap: {median_gap:.1f}px, Paragraph split threshold: {paragraph_gap_thresh:.1f}px")

clusters = []
curr_cluster = [line_bands[0]] if line_bands else []

for i in range(len(line_bands) - 1):
    gap = line_bands[i+1][0] - line_bands[i][1]
    if gap > paragraph_gap_thresh:
        clusters.append((curr_cluster[0][0], curr_cluster[-1][1]))
        curr_cluster = [line_bands[i+1]]
    else:
        curr_cluster.append(line_bands[i+1])
if curr_cluster:
    clusters.append((curr_cluster[0][0], curr_cluster[-1][1]))

print(f"\nDetected {len(clusters)} visual layout blocks:")
debug_vis = Image.open("scratch/tb2618_page_1.png").convert("RGB")
draw = ImageDraw.Draw(debug_vis)

for idx, (cy1, cy2) in enumerate(clusters, 1):
    # Find horizontal bounds (x1, x2) for this cluster
    block_slice = cleaned[cy1:cy2, :]
    v_proj = block_slice.sum(axis=0)
    nonzero_cols = np.where(v_proj > 2)[0]
    if len(nonzero_cols) > 0:
        cx1 = max(0, nonzero_cols[0] - 6)
        cx2 = min(w, nonzero_cols[-1] + 6)
    else:
        cx1, cx2 = margin_x_left, margin_x_right
    
    top_pct = cy1 / h * 100
    left_pct = cx1 / w * 100
    height_pct = (cy2 - cy1) / h * 100
    width_pct = (cx2 - cx1) / w * 100
    print(f"  [{idx}] top={top_pct:5.1f}%, left={left_pct:5.1f}%, w={width_pct:5.1f}%, h={height_pct:5.1f}% (px: y={cy1}..{cy2}, x={cx1}..{cx2})")
    draw.rectangle([cx1, cy1, cx2, cy2], outline="red", width=3)

debug_vis.save("scratch/test_morphology_blocks.png")
print("\nSaved scratch/test_morphology_blocks.png")
