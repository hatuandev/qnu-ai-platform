import asyncio
import json
import sys
from app.core.database import AsyncSessionFactory
from app.modules.knowledge.services.ingestion_service import ingestion_service

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        res = await ingestion_service.get_studio_view(db, 'doc_527d541ae08a', refresh_layout=False)
        print("Total pages:", len(res["pages"]))
        for p in res["pages"]:
            p_num = p["page_number"]
            print(f"=== Page {p_num} ===")
            boxes = p.get("bounding_boxes", [])
            print(f"bounding_boxes: {len(boxes)}")
            for b in boxes:
                print(f"  Box: {b['type']}, label={b['label']}, coords={b['coordinates']}, snippet={repr(b['content_snippet'][:40])}")
            regs = p.get("regions", [])
            print(f"regions: {len(regs)}")
            for r in regs:
                print(f"  Region: {r['type']}, title={r['title']}, details={repr(r.get('details', '')[:40])}")

if __name__ == "__main__":
    asyncio.run(main())
