import asyncio
from app.core.database import AsyncSessionFactory
from sqlalchemy import select
from app.modules.knowledge.models import KnowledgeDocument, KnowledgeCollection

async def main():
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(KnowledgeCollection).where(KnowledgeCollection.id == 'col_admissions'))
        col = res.scalar_one_or_none()
        col_title = col.name if col else "Không tìm thấy"
        print(f"Collection: col_admissions | Name: {col_title}")
        
        doc_res = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.collection_id == 'col_admissions')
            .order_by(KnowledgeDocument.created_at.asc())
        )
        docs = doc_res.scalars().all()
        print(f"Total documents: {len(docs)}")
        for d in docs:
            print(f"ID: {d.id} | File: {d.file_name} | Title: {d.title} | Status: {d.status} | Index: {d.index_status}")

if __name__ == '__main__':
    asyncio.run(main())
