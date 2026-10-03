import sys
sys.path.insert(0, 'backend')
import pymupdf as fitz
from app.modules.knowledge.services.ingestion_service import IngestionService
from app.modules.ocr.layout_detector import SmartLayoutDetector

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf"
doc = fitz.open(pdf_path)
detector = SmartLayoutDetector()
service = IngestionService()

extracted_blocks = {}
for p_idx, page in enumerate(doc):
    p_num = p_idx + 1
    cv_regions = detector.detect_layout_regions(None, page_number=p_num, fitz_page=page)
    blks = []
    for reg in cv_regions:
        r_type = str(reg.get("type", "text"))
        blks.append({
            "type": r_type,
            "coordinates": {
                "x": float(reg.get("left", 0.0)),
                "y": float(reg.get("top", 0.0)),
                "width": float(reg.get("width", 0.0)),
                "height": float(reg.get("height", 0.0)),
            },
            "label": str(reg.get("label") or r_type),
            "text": str(reg.get("text") or ""),
            "content_snippet": str(reg.get("content_snippet") or reg.get("text") or "")[:160],
            "confidence": 0.98 if r_type in ("table", "signature") else 0.92,
        })
    extracted_blocks[str(p_num)] = blks

pages = service.build_studio_pages(
    chunks=[],
    page_blocks=extracted_blocks,
    document_id="doc_527d541ae08a",
    page_markdowns={},
    page_dimensions={
        1: {"width": 1240, "height": 1754, "orientation": "portrait"},
        2: {"width": 1240, "height": 1754, "orientation": "portrait"},
    },
)

print(f"Total studio pages built: {len(pages)}")
for p in pages:
    p_num = p["page_number"]
    boxes = p["bounding_boxes"]
    print(f"\n--- Page {p_num}: {len(boxes)} bounding boxes ---")
    for b in boxes:
        c = b["coordinates"]
        print(f"  {b['type']:10s} label={b['label']:22s} y={c['y']:5.1f}% h={c['height']:5.1f}% bot={c['y']+c['height']:5.1f}%")
