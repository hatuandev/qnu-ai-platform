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

page2 = doc[1]
regions = detector.detect_layout_regions(None, markdown_text="", page_number=2, fitz_page=page2)
print("=== PAGE 2 REGIONS ===")
for r in regions:
    print(r)

doc.close()
