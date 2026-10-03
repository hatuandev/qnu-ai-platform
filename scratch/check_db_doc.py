import asyncio
import sys
from sqlalchemy import text
from app.core.database import AsyncSessionFactory

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(text("""
            SELECT id, file_name, title, status, doc_metadata 
            FROM knowledge_documents 
            WHERE file_name LIKE '%TB2618%' OR title LIKE '%TB2618%'
            LIMIT 5
        """))
        rows = res.fetchall()
        for r in rows:
            print("ID:", r[0])
            print("File:", r[1])
            print("Title:", r[2])
            print("Status:", r[3])
            meta = r[4] or {}
            print("OCR Method:", meta.get("ocr_method"))
            pb = meta.get("page_blocks") or {}
            print("Page blocks keys:", list(pb.keys()))
            for p, blks in pb.items():
                print(f"-- Page {p}: {len(blks)} blocks")
                for b in blks:
                    print(f"   type={b.get('type')}, label={b.get('label')}, coords={b.get('coordinates')}, snippet={repr(b.get('content_snippet', '')[:60])}")

if __name__ == "__main__":
    asyncio.run(main())
