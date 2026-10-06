import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pymupdf as fitz
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.layout_detector import SmartLayoutDetector

pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()

for p_num in (1, 2):
    page = doc[p_num - 1]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    
    regions = detector.detect_layout_regions(image_input=img_bytes, page_number=p_num)
    print(f"\n=== PAGE {p_num}: {len(regions)} regions ===")
    for r in regions:
        t = float(r.get("top", 0))
        l = float(r.get("left", 0))
        w = float(r.get("width", 0))
        h = float(r.get("height", 0))
        print(f"  [{r.get('type'):10s}] top={t:5.1f}%, left={l:5.1f}%, w={w:5.1f}%, h={h:5.1f}% | label={r.get('label')}")

doc.close()
