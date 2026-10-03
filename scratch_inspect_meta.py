import asyncio
import json
import sys
from app.core.database import AsyncSessionFactory
from sqlalchemy import text

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(text("SELECT doc_metadata FROM knowledge_documents WHERE id = 'doc_527d541ae08a'"))
        row = res.fetchone()
        if row and row[0]:
            meta = row[0]
            print("OCR Method:", meta.get("ocr_method"))
            print("OCR Model:", meta.get("ocr_model"))
            print("Layout regions count:", len(meta.get("layout_regions", [])))
            print("Page blocks:", json.dumps(meta.get("page_blocks"), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
