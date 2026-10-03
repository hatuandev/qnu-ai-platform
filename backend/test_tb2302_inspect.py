import pymupdf as fitz
import sys
from app.modules.ocr.layout_detector import SmartLayoutDetector

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"d:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()

print(f"Total pages: {len(doc)}")
for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    page_text = page.get_text()
    print(f"\n================ PAGE {p_num} ================")
    print(f"Text length from page.get_text(): {len(page_text)}")
    print(f"Sample text: {repr(page_text[:100])}")
    
    # Check tables detected by find_tables
    tables = page.find_tables()
    print(f"PyMuPDF find_tables found: {len(tables.tables)} tables")
    for t_idx, t in enumerate(tables.tables):
        print(f" Table {t_idx}: bbox={t.bbox}, rows={len(t.extract())}")
        for r in t.extract():
            print("   Row:", r)
            
    # Check what detector.detect_layout_regions returns
    res = detector.detect_layout_regions(None, markdown_text=page_text, page_number=p_num, fitz_page=page)
    print(f"\ndetector.detect_layout_regions returned {len(res)} regions:")
    for r in res:
        print(f"  [{r['type']}] top={r['top']}, left={r['left']}, w={r['width']}, h={r['height']}, text={repr(r.get('text', '')[:40])}")
