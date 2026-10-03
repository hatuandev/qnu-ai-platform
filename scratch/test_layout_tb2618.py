import sys
import cv2
import numpy as np
import pymupdf as fitz
from app.modules.ocr.layout_detector import SmartLayoutDetector

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()

print(f"Total pages: {len(doc)}")

for page_idx, page in enumerate(doc):
    p_num = page_idx + 1
    print(f"\n================ PAGE {p_num} ================")
    
    # 1. Text from fitz
    fitz_text = page.get_text()
    print(f"PyMuPDF get_text() length: {len(fitz_text.strip())}")
    
    # 2. Render image
    pix = page.get_pixmap(dpi=150)
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
    if pix.n == 4:
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
    
    h, w = img_bgr.shape[:2]
    print(f"Image dimension: {w}x{h}")
    
    # 3. Test _detect_red_stamps
    stamps, red_mask = detector._detect_red_stamps(img_bgr, w, h)
    print(f"Red stamps found: {len(stamps)}")
    for s in stamps:
        print("  Stamp:", s)
        
    # 4. Test _detect_hybrid_pdf_regions
    hybrid = detector._detect_hybrid_pdf_regions(fitz_page=page, stamps=stamps, page_number=p_num)
    print(f"_detect_hybrid_pdf_regions returned: {len(hybrid)} regions")
    for r in hybrid:
        print("  Hybrid:", r["type"], r["label"], r["top"], r["left"], r["width"], r["height"])
        
    # 5. Test _detect_tables
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    tables, text_thresh = detector._detect_tables(gray, w, h, red_mask)
    print(f"_detect_tables returned: {len(tables)} tables")
    for t in tables:
        print("  Table:", t["top"], t["left"], t["width"], t["height"])
        
    # 6. Test _detect_text_regions
    text_regions = detector._detect_text_regions(text_thresh, w, h, tables, markdown_text="", page_number=p_num)
    print(f"_detect_text_regions returned: {len(text_regions)} regions")
    for tr in text_regions:
        print("  Text region:", tr["type"], tr["label"], tr["top"], tr["left"], tr["width"], tr["height"])
        
    # 7. Total detect_layout_regions
    all_regions = detector.detect_layout_regions(img_bgr, markdown_text="", page_number=p_num, fitz_page=page)
    print(f"Total detect_layout_regions with fitz_page: {len(all_regions)} regions")
    for r in all_regions:
        print("  Final:", r["type"], r["label"], f"top={r['top']:.1f}, left={r['left']:.1f}, w={r['width']:.1f}, h={r['height']:.1f}")

    all_regions_pure_cv = detector.detect_layout_regions(img_bgr, markdown_text="", page_number=p_num, fitz_page=None)
    print(f"Total detect_layout_regions without fitz_page (pure CV): {len(all_regions_pure_cv)} regions")
    for r in all_regions_pure_cv:
        print("  Pure CV Final:", r["type"], r["label"], f"top={r['top']:.1f}, left={r['left']:.1f}, w={r['width']:.1f}, h={r['height']:.1f}")
