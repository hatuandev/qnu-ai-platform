import asyncio
import sys
from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeDocument

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        doc = await db.get(KnowledgeDocument, 'doc_527d541ae08a')
        if not doc:
            print('Document not found')
            return
        pb = (doc.doc_metadata or {}).get('page_blocks', {})
        for p, blks in pb.items():
            print(f'Page {p}: {len(blks)} blocks')
            for b in blks:
                c = b.get('coordinates', {})
                b_type = b.get('type')
                b_y = c.get('y', 0)
                b_h = c.get('height', 0)
                b_bot = b_y + b_h
                b_lbl = b.get('label')
                b_txt = (b.get('text') or '').replace('\n', ' ')[:40]
                print(f"  {b_type:10s} y={b_y:5.1f}% h={b_h:5.1f}% bot={b_bot:5.1f}% lbl={b_lbl} txt={b_txt}")

if __name__ == '__main__':
    asyncio.run(main())
