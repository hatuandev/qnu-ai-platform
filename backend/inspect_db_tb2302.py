import asyncio
import sys
from app.core.database import AsyncSessionFactory
from sqlalchemy import select
from app.modules.knowledge.models import KnowledgeDocument

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.file_name.ilike('%TB2302%')))
        docs = res.scalars().all()
        print(f"Found docs: {len(docs)}")
        for d in docs:
            print(f"\nID: {d.id}, name: {d.file_name}, status: {d.status}")
            meta = d.doc_metadata or {}
            pb = meta.get('page_blocks', {})
            print(f"page_blocks keys: {list(pb.keys())}")
            total_b = sum(len(v) for v in pb.values())
            print(f"Total blocks in metadata: {total_b}")
            for p, blks in pb.items():
                print(f" Page {p}: {len(blks)} blocks")
                for b in blks:
                    b_type = b.get('type')
                    text_str = str(b.get('text') or b.get('content_snippet') or "")
                    if b_type in ('table', 'signature') or 'Quản lý' in text_str or 'hình thức' in text_str.lower():
                        coords = b.get('coordinates', {})
                        print(f"   [{b_type}] (y={coords.get('y')}, x={coords.get('x')}, w={coords.get('width')}, h={coords.get('height')}) label={b.get('label')}, text={repr(text_str[:40])}")

if __name__ == "__main__":
    asyncio.run(main())
