from PIL import Image

img = Image.open("scratch/tb2618_page_1.png")
w, h = img.size
print(f"Image size: {w}x{h}")

# In Block 7: y=69.6%, height=20.0% -> y_pixel = 0.696 * 1754 = 1220 px, height = 350 px
# On 1754 px height:
# 69.6% is at y=1220
# Let's crop from y=700 (40%) to y=1250 (71%) and see what is actually there!
# Let's check text position
