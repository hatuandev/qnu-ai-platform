import asyncio
import sys
import json
from app.core.database import AsyncSessionFactory
from sqlalchemy import select
from app.modules.knowledge.models import KnowledgeDocument

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == 'doc_64869d87a6f9'))
        doc = res.scalar_one_or_none()
        if not doc:
            print("Doc not found!")
            return
        meta = doc.doc_metadata or {}
        print("ocr_method:", meta.get("ocr_method"))
        print("ocr_fallback:", meta.get("ocr_fallback"))
        print("page_count:", meta.get("page_count"))
        print("page_blocks keys:", list((meta.get("page_blocks") or {}).keys()))
        for p, blks in (meta.get("page_blocks") or {}).items():
            print(f"Page {p} has {len(blks)} blocks:")
            for b in blks:
                coords = b.get("coordinates") or {}
                print(f"  [{b.get('type')}] top={coords.get('y')}, left={coords.get('x')}, w={coords.get('width')}, h={coords.get('height')}, label={b.get('label')}")

if __name__ == "__main__":
    asyncio.run(main())
