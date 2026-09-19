"""Knowledge Collection Service — CRUD, stats, and cascade deletion."""

from __future__ import annotations

import logging

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.core.storage import storage_service
from app.modules.knowledge.models import (
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeFact,
)
from app.modules.knowledge.schemas import (
    CollectionCreateRequest,
    CollectionUpdateRequest,
)

logger = logging.getLogger(__name__)


class CollectionService:
    """Service managing Knowledge Collections and their stats."""

    async def create_collection(
        self, db: AsyncSession, req: CollectionCreateRequest
    ) -> KnowledgeCollection:
        col = KnowledgeCollection(
            name=req.name,
            description=req.description,
            module_code=req.module_code,
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
            collection_metadata=req.metadata,
        )
        db.add(col)
        await db.commit()
        await db.refresh(col)
        logger.info("Created knowledge collection: id=%s, name=%s", col.id, col.name)
        return col

    async def list_collections(
        self, db: AsyncSession, tenant_id: str = "tenant_qnu", workspace_id: str = "workspace_qnu"
    ) -> list[KnowledgeCollection]:
        query = (
            select(KnowledgeCollection)
            .where(
                KnowledgeCollection.tenant_id == tenant_id,
                KnowledgeCollection.workspace_id == workspace_id,
            )
            .order_by(KnowledgeCollection.created_at.desc())
        )
        res = await db.execute(query)
        cols = list(res.scalars().all())
        if not cols:
            seed_data = [
                (
                    "col_admissions",
                    "Kho Tri Thức Đề Án Tuyển Sinh",
                    "admissions",
                    "Đề án tuyển sinh chính quy, bảng chỉ tiêu, điểm chuẩn và thông tin học phí.",
                ),
                (
                    "col_regulations",
                    "Kho Tri Thức Quy Chế Học Vụ",
                    "regulations",
                    "Quy chế đào tạo tín chỉ, quy định chuẩn đầu ra, điều kiện tốt nghiệp.",
                ),
                (
                    "col_library",
                    "Kho Tri Thức Cẩm Nang Thư Viện",
                    "library",
                    "Quy trình mượn trả tài liệu, giáo trình số, hướng dẫn cơ sở dữ liệu.",
                ),
                (
                    "col_drafting",
                    "Kho Mẫu Văn Bản Chuẩn NĐ 30",
                    "drafting",
                    "Mẫu văn bản hành chính, quyết định, tờ trình, quy cách căn lề theo NĐ 30/2020.",
                ),
                (
                    "col_question_bank",
                    "Kho Tri Thức Khảo Thí & Đề Thi Bloom",
                    "question_bank",
                    "Quy định ma trận khảo thí, chuẩn đầu ra học phần và 4 mức độ Bloom.",
                ),
            ]
            for cid, cname, mcode, cdesc in seed_data:
                item = KnowledgeCollection(
                    id=cid,
                    name=cname,
                    module_code=mcode,
                    description=cdesc,
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    collection_metadata={
                        "chunking_strategy": (
                            "ClauseBasedChunker"
                            if mcode in ("regulations", "drafting")
                            else "SemanticChunker"
                        ),
                        "ocr_profile": "Docling",
                        "document_count": 8,
                        "chunk_count": 246,
                    },
                )
                db.add(item)
            await db.commit()
            res = await db.execute(query)
            cols = list(res.scalars().all())
        await self._attach_collection_stats(db, cols)
        return cols

    async def _chunk_counts_by_document(
        self, db: AsyncSession, document_ids: list[str]
    ) -> dict[str, int]:
        """Real chunk counts per document (single GROUP BY query)."""
        if not document_ids:
            return {}
        res = await db.execute(
            select(KnowledgeChunk.document_id, func.count(KnowledgeChunk.id))
            .where(KnowledgeChunk.document_id.in_(document_ids))
            .group_by(KnowledgeChunk.document_id)
        )
        return {row[0]: row[1] for row in res.all()}

    async def _attach_collection_stats(
        self, db: AsyncSession, cols: list[KnowledgeCollection]
    ) -> None:
        """Fill real document_count/chunk_count transient attrs on collections."""
        for col in cols:
            doc_res = await db.execute(
                select(func.count(KnowledgeDocument.id)).where(
                    KnowledgeDocument.collection_id == col.id,
                    KnowledgeDocument.is_active.is_(True),
                )
            )
            chunk_res = await db.execute(
                select(func.count(KnowledgeChunk.id))
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(
                    KnowledgeChunk.collection_id == col.id,
                    KnowledgeDocument.is_active.is_(True),
                )
            )
            col.document_count = doc_res.scalar() or 0
            col.chunk_count = chunk_res.scalar() or 0

    async def get_collection(self, db: AsyncSession, collection_id: str) -> KnowledgeCollection:
        query = select(KnowledgeCollection).where(KnowledgeCollection.id == collection_id)
        res = await db.execute(query)
        col = res.scalar_one_or_none()
        if not col:
            raise EntityNotFoundError(f"Bộ sưu tập '{collection_id}' không tồn tại.")
        await self._attach_collection_stats(db, [col])
        return col

    async def update_collection(
        self, db: AsyncSession, collection_id: str, req: CollectionUpdateRequest
    ) -> KnowledgeCollection:
        col = await self.get_collection(db, collection_id)
        updates = req.model_dump(exclude_unset=True)
        if "metadata" in updates:
            merged = dict(col.collection_metadata or {})
            merged.update(updates.pop("metadata") or {})
            col.collection_metadata = merged
        for field, value in updates.items():
            if hasattr(col, field):
                setattr(col, field, value)
        await db.commit()
        await db.refresh(col)
        return col

    async def delete_collection(self, db: AsyncSession, collection_id: str) -> None:
        """Delete a collection, all its documents, chunks, facts, and Qdrant index (zero ghost collections)."""
        col = await self.get_collection(db, collection_id)

        # 0. Delete physical files from Storage driver
        docs = list(
            (
                await db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.collection_id == collection_id)
                )
            )
            .scalars()
            .all()
        )
        for doc in docs:
            try:
                await storage_service.delete(doc.storage_path)
            except Exception as exc:
                logger.warning("Storage file deletion failed for %s: %s", doc.storage_path, exc)

        # 1. Delete Qdrant vector collection
        try:
            from app.modules.rag.vector_indexer import vector_indexer
            await vector_indexer.delete_collection(collection_id=collection_id)
        except Exception as exc:
            logger.warning("Qdrant collection deletion failed for %s (graceful): %s", collection_id, exc)

        # 2. Delete all Chunks
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.collection_id == collection_id))

        # 3. Delete all Facts
        await db.execute(delete(KnowledgeFact).where(KnowledgeFact.collection_id == collection_id))

        # 4. Delete all Documents
        await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.collection_id == collection_id))

        # 5. Delete Collection record
        await db.delete(col)
        await db.commit()

        # 6. Invalidate Semantic Cache
        try:
            from app.core.redis import semantic_cache
            await semantic_cache.invalidate_collection(collection_id=collection_id)
        except Exception as exc:
            logger.warning("Cache invalidation failed for collection %s: %s", collection_id, exc)

        logger.info("Permanently deleted collection %s and all associated assets", collection_id)


collection_service = CollectionService()
