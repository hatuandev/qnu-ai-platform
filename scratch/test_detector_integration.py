import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pymupdf as fitz

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.layout_detector import SmartLayoutDetector

pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()

for p_num in range(1, len(doc) + 1):
    page = doc[p_num - 1]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    
    # Run detector with both image and fitz_page
    regions = detector.detect_layout_regions(img_bytes, markdown_text="", page_number=p_num, fitz_page=page)
    print(f"\n=== PAGE {p_num}: {len(regions)} regions ===")
    for r in regions:
        t = float(r.get("top", 0))
        l = float(r.get("left", 0))
        w = float(r.get("width", 0))
        h = float(r.get("height", 0))
        r_type = r.get("type")
        label = r.get("label")
        print(f"  [{r_type:10s}] x={l:5.1f}%, y={t:5.1f}%, w={w:5.1f}%, h={h:5.1f}% | label={label}")

doc.close()
