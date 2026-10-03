import numpy as np
from PIL import Image

img = Image.open("scratch/tb2618_page_1.png").convert("L")
arr = np.array(img)
h, w = arr.shape
print(f"Shape: {w}x{h}")

# Threshold to find dark pixels (lines and text)
dark = arr < 180

# Horizontal projection profile (sum across columns)
h_proj = dark.sum(axis=1)

# Find horizontal lines (rows with very high number of dark pixels)
# A horizontal line across the table will have a large contiguous span of dark pixels
row_dark_count = (arr < 150).sum(axis=1)
# Across 1240 pixels width, a table border line has at least 400 dark pixels in a single row
table_lines = [y for y, count in enumerate(row_dark_count) if count > 400]
print(f"Candidate table horizontal lines y-coords: {table_lines}")
if table_lines:
    print(f"Table y-min: {min(table_lines)} ({min(table_lines)/h*100:.1f}%), y-max: {max(table_lines)} ({max(table_lines)/h*100:.1f}%)")
