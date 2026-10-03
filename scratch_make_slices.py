from PIL import Image

img = Image.open("scratch/tb2618_page_1.png")
w, h = img.size

# Let's save slices
slices = [
    ("header", 0.03, 0.15),
    ("title", 0.15, 0.28),
    ("table_area", 0.26, 0.44),
    ("section2_area", 0.42, 0.68),
    ("section345_area", 0.65, 0.95),
]

for name, y1_pct, y2_pct in slices:
    y1 = int(y1_pct * h)
    y2 = int(y2_pct * h)
    cropped = img.crop((0, y1, w, y2))
    cropped.save(f"scratch/slice_{name}.png")
    print(f"Saved slice_{name}.png: y={y1_pct*100:.1f}% to {y2_pct*100:.1f}% (px {y1} to {y2})")
