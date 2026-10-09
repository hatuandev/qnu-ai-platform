import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeCollection, KnowledgeDocument


async def check():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(KnowledgeDocument))
        docs = result.scalars().all()
        print(f"Total documents: {len(docs)}")
        for d in docs:
            print(f"- ID: {d.id} | Name: {d.file_name} | Col: {d.collection_id} | Status: {d.status} | IndexStatus: {d.index_status} | Error: {d.index_error}")

        col_result = await session.execute(select(KnowledgeCollection))
        cols = col_result.scalars().all()
        print(f"\nTotal collections: {len(cols)}")
        for c in cols:
            print(f"- Col: {c.id} | Name: {c.name} | DocCount: {c.document_count}")

if __name__ == "__main__":
    asyncio.run(check())
