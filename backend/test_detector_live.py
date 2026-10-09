import asyncio
import sys

import pymupdf as fitz
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.ocr.layout_detector import SmartLayoutDetector

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == 'doc_64869d87a6f9'))
        doc = res.scalar_one_or_none()
        meta = doc.doc_metadata or {}
        p_mds = meta.get("page_markdowns") or {}
        print("Got page markdowns:", list(p_mds.keys()))

    pdf_path = r"d:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\TB2302_Thong_bao_tuyen_sinh_dao_tao_tu_xa_trinh_do_dai_hoc.pdf"
    pdf = fitz.open(pdf_path)
    detector = SmartLayoutDetector()

    for p_idx, page in enumerate(pdf):
        p_num = p_idx + 1
        md = p_mds.get(str(p_num)) or p_mds.get(p_num) or ""
        print(f"\n=== PAGE {p_num} (md length: {len(md)}) ===")
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        
        regions = detector._detect_morphology_regions(
            image_input=img_bytes,
            fitz_page=page,
            markdown_text=md,
            page_number=p_num,
        )
        print(f"Detected {len(regions)} regions:")
        for r in regions:
            coords = f"top={r.get('top')}, left={r.get('left')}, w={r.get('width')}, h={r.get('height')}"
            print(f"  [{r['type']}] {coords} | {r.get('label')} | {r.get('text', '')[:40]!r}")

if __name__ == "__main__":
    asyncio.run(main())
