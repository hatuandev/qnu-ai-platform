import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeDocument

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == 'doc_64869d87a6f9'))
        doc = res.scalar_one_or_none()
        meta = doc.doc_metadata or {}
        p_mds = meta.get("page_markdowns") or {}
        for p, md in p_mds.items():
            print(f"=== Page {p} Markdown ===")
            print(md)
            print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
