import os
import sys
import pymupdf as fitz

pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
doc = fitz.open(pdf_path)
page2 = doc[1]
pw = page2.rect.width
ph = page2.rect.height

print("=== PAGE 2 BLOCKS ===")
for b in page2.get_text("blocks"):
    x0, y0, x1, y1, text, block_no, block_type = b[:7]
    top = round(y0 / ph * 100, 1)
    left = round(x0 / pw * 100, 1)
    w = round((x1 - x0) / pw * 100, 1)
    h = round((y1 - y0) / ph * 100, 1)
    print(f"Block {block_no} (type {block_type}): top={top}%, left={left}%, w={w}%, h={h}% | text={text[:60].replace(chr(10), ' ')}")

tabs = page2.find_tables()
print(f"\n=== PAGE 2 TABLES: {len(tabs.tables)} ===")
for t in tabs.tables:
    bbox = t.bbox
    top = round(bbox[1] / ph * 100, 1)
    left = round(bbox[0] / pw * 100, 1)
    w = round((bbox[2] - bbox[0]) / pw * 100, 1)
    h = round((bbox[3] - bbox[1]) / ph * 100, 1)
    print(f"Table bbox: top={top}%, left={left}%, w={w}%, h={h}% (rows: {len(t.extract())})")

doc.close()
