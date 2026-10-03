import sys
sys.path.insert(0, 'backend')
import pymupdf as fitz
from app.modules.ocr.layout_detector import SmartLayoutDetector

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()

for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    regs = detector.detect_layout_regions(None, page_number=p_num, fitz_page=page)
    print(f"\n=== PAGE {p_num} ({len(regs)} regions detected) ===")
    for r in regs:
        b_type = r["type"]
        b_lbl = r["label"]
        b_top = r["top"]
        b_left = r["left"]
        b_w = r["width"]
        b_h = r["height"]
        print(f"  {b_type:10s} {b_lbl:22s} y={b_top:5.1f}% x={b_left:5.1f}% w={b_w:5.1f}% h={b_h:5.1f}%")
