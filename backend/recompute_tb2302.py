import asyncio
import sys
from app.core.database import AsyncSessionFactory
from sqlalchemy import select
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.knowledge.services.ingestion_service import ingestion_service

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == 'doc_64869d87a6f9'))
        doc = res.scalar_one_or_none()
        if not doc:
            print("Doc not found!")
            return
        
        meta = doc.doc_metadata or {}
        old_blocks = meta.get("page_blocks", {})
        is_stale = ingestion_service._is_stale_raw_blocks(old_blocks)
        print(f"Old blocks stale check: {is_stale}")
        
        # Test get_studio_view with refresh_layout=True to force recomputation and saving to DB
        view = await ingestion_service.get_studio_view(db, 'doc_64869d87a6f9', refresh_layout=True)
        print("get_studio_view completed successfully!")
        print(f"Total pages: {len(view['pages'])}")
        
        for p in view['pages']:
            p_num = p['page_number']
            boxes = p.get('bounding_boxes', [])
            print(f"\n--- Page {p_num} ({len(boxes)} boxes) ---")
            for b in boxes:
                coords = b['coordinates']
                print(f"  [{b['type']:10s}] (y={coords['y']:4.1f}%, x={coords['x']:4.1f}%, w={coords['width']:4.1f}%, h={coords['height']:4.1f}%) | {b['label']:18s} | snip={repr(b['content_snippet'][:40])}")

        # Check DB to confirm page_blocks in doc_metadata was updated
        res2 = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == 'doc_64869d87a6f9'))
        doc2 = res2.scalar_one_or_none()
        meta2 = doc2.doc_metadata or {}
        new_blocks = meta2.get("page_blocks", {})
        print("\nDB page_blocks updated keys:", list(new_blocks.keys()))
        for p, blks in new_blocks.items():
            print(f"  Page {p} in DB now has {len(blks)} blocks.")

if __name__ == "__main__":
    asyncio.run(main())
