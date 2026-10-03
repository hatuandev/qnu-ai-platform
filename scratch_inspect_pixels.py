import numpy as np
from PIL import Image

img = Image.open("scratch/tb2618_page_1.png").convert("L")
arr = np.array(img)
h, w = arr.shape

# Print min, max, mean of pixel values
print("Min pixel:", arr.min(), "Max pixel:", arr.max(), "Mean pixel:", arr.mean())

# Look at rows between y = 20% to y = 50%
y_start = int(0.20 * h)
y_end = int(0.50 * h)

for y in range(y_start, y_end, 20):
    row = arr[y, :]
    dark_count = (row < 128).sum()
    if dark_count > 50:
        print(f"y={y} ({y/h*100:.1f}%): dark_count={dark_count}, min_val={row.min()}")
