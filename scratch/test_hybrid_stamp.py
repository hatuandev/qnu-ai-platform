import os
import sys
import fitz
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.layout_detector import SmartLayoutDetector

pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()

for p_num in range(1, len(doc) + 1):
    page = doc[p_num - 1]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    
    stamps, red_mask = detector._detect_red_stamps(img, w, h)
    print(f"\n--- Page {p_num}: {len(stamps)} red stamps detected ---")
    for s in stamps:
        print(f"  Stamp: top={s['top']}%, left={s['left']}%, w={s['width']}%, h={s['height']}%")
        
    hybrid = detector._detect_hybrid_pdf_regions(fitz_page=page, stamps=stamps, page_number=p_num)
    print(f"Hybrid regions with stamp: {len(hybrid)}")
    for r in hybrid:
        print(f"  [{r.get('type')}] top={r.get('top'):.1f}%, left={r.get('left'):.1f}%, w={r.get('width'):.1f}%, h={r.get('height'):.1f}% | label={r.get('label')} | snippet={r.get('text', '')[:60].replace(chr(10), ' ')}")

doc.close()
