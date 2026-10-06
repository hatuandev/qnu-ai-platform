import os
import sys
import fitz

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.layout_detector import SmartLayoutDetector

pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()

for p_num in range(1, len(doc) + 1):
    page = doc[p_num - 1]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    
    regions = detector.detect_layout_regions(img_bytes, markdown_text="", page_number=p_num, fitz_page=page)
    print(f"\n=== PAGE {p_num}: {len(regions)} regions detected ===")
    for r in regions:
        print(f"  [{r.get('type')}] top={r.get('top'):.1f}%, left={r.get('left'):.1f}%, w={r.get('width'):.1f}%, h={r.get('height'):.1f}% | snippet={r.get('text', '')[:60]}")

doc.close()
