from PIL import Image

img = Image.open("scratch/tb2618_page_1.png")
w, h = img.size

# In block 4: x=20%, y=31%, width=60%, height=10%
# In pixels:
x1 = int(0.20 * w)
y1 = int(0.31 * h)
x2 = int((0.20 + 0.60) * w)
y2 = int((0.31 + 0.10) * h)

print(f"Table box in pixels: ({x1}, {y1}) to ({x2}, {y2})")

cropped = img.crop((x1, y1, x2, y2))
cropped.save("scratch/crop_table_box.png")

# Also let's draw the 5 boxes on tb2618_page_1.png with red rectangles and save as debug_page_1_boxes.png!
from PIL import ImageDraw

debug_img = img.copy().convert("RGB")
draw = ImageDraw.Draw(debug_img)

boxes = [
    ("header", 10.0, 4.0, 79.0, 8.0, "blue"),
    ("title", 15.0, 15.0, 70.0, 6.0, "green"),
    ("text", 10.0, 23.0, 79.0, 4.0, "yellow"),
    ("table", 20.0, 31.0, 60.0, 10.0, "cyan"),
    ("list", 10.0, 43.0, 79.0, 32.0, "magenta"),
]

for name, bx, by, bw, bh, color in boxes:
    px1 = int((bx / 100.0) * w)
    py1 = int((by / 100.0) * h)
    px2 = int(((bx + bw) / 100.0) * w)
    py2 = int(((by + bh) / 100.0) * h)
    draw.rectangle([px1, py1, px2, py2], outline=color, width=4)
    print(f"Drawn {name}: ({px1}, {py1}) to ({px2}, {py2}) in {color}")

debug_img.save("scratch/debug_page_1_boxes.png")
print("Saved scratch/debug_page_1_boxes.png")
