import sys
sys.path.insert(0, 'backend')
import pymupdf as fitz
from app.modules.ocr.layout_detector import SmartLayoutDetector

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()

for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    # Test passing fitz_page directly without OpenCV!
    regs = detector.detect_layout_regions(image_input=None, page_number=p_num, fitz_page=page)
    print(f"\n=== PAGE {p_num} ({len(regs)} regions detected) ===")
    for r in regs:
        print(f"  {r['type']:10s} {r['label']:22s} top={r['top']:5.1f}% left={r['left']:5.1f}% w={r['width']:5.1f}% h={r['height']:5.1f}%")
