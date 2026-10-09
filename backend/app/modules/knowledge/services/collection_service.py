"""Knowledge Collection Service — CRUD, stats, and cascade deletion."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
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
from app.modules.knowledge.services.scope_helper import (
    get_scoped_collection,
)

logger = logging.getLogger(__name__)


class CollectionService:
    """Service managing Knowledge Collections and their stats."""

    async def create_collection(
        self, db: AsyncSession, req: CollectionCreateRequest, actor: Any | None = None
    ) -> KnowledgeCollection:
        tenant_id = getattr(actor, "tenant_id", None) or req.tenant_id
        workspace_id = getattr(actor, "workspace_id", None) or req.workspace_id

        meta = dict(req.metadata or {})
        if req.data_processing:
            meta["data_processing"] = (
                req.data_processing.model_dump()
                if hasattr(req.data_processing, "model_dump")
                else dict(req.data_processing)
            )
        elif "data_processing" not in meta:
            from app.modules.modelops.services.model_catalog_service import model_catalog_service

            catalog = await model_catalog_service.get_system_model_defaults(db)
            defaults = catalog.defaults
            if not defaults.default_embedding_provider_id or not defaults.default_embedding_model:
                raise AppException(
                    "Chưa cấu hình embedding provider/model mặc định trong ModelOps DB.",
                    code="EMBEDDING_MODEL_NOT_CONFIGURED",
                    status_code=400,
                )
            dim = await model_catalog_service.resolve_embedding_dimension(
                db,
                defaults.default_embedding_provider_id,
                defaults.default_embedding_model,
            )

            meta["data_processing"] = {
                "embedding_provider_id": defaults.default_embedding_provider_id,
                "embedding_model": defaults.default_embedding_model,
                "embedding_dimension": int(dim),
                "ocr_mode": defaults.ocr_mode or "auto",
                "primary_ocr_provider_id": defaults.default_ocr_provider_id,
                "primary_ocr_model": defaults.default_ocr_model,
                "fallback_ocr_provider_id": defaults.fallback_ocr_provider_id,
                "fallback_ocr_model": defaults.fallback_ocr_model,
            }
        col = KnowledgeCollection(
            name=req.name,
            description=req.description,
            module_code=req.module_code,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            collection_metadata=meta,
        )
        db.add(col)
        await db.commit()
        await db.refresh(col)
        logger.info("Created knowledge collection: id=%s, name=%s", col.id, col.name)
        return col

    async def list_collections(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> list[KnowledgeCollection]:
        t_id = getattr(actor, "tenant_id", None) or tenant_id
        w_id = getattr(actor, "workspace_id", None) or workspace_id

        query = select(KnowledgeCollection)
        if t_id:
            query = query.where(KnowledgeCollection.tenant_id == t_id)
        if w_id:
            query = query.where(KnowledgeCollection.workspace_id == w_id)
        query = query.order_by(KnowledgeCollection.created_at.desc())

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

    async def get_collection(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ) -> KnowledgeCollection:
        col = await get_scoped_collection(db, collection_id, actor=actor)
        await self._attach_collection_stats(db, [col])
        return col

    async def update_collection(
        self,
        db: AsyncSession,
        collection_id: str,
        req: CollectionUpdateRequest,
        actor: Any | None = None,
    ) -> KnowledgeCollection:
        col = await self.get_collection(db, collection_id, actor=actor)
        updates = req.model_dump(exclude_unset=True)
        if "metadata" in updates:
            merged = dict(col.collection_metadata or {})
            merged.update(updates.pop("metadata") or {})
            col.collection_metadata = merged
        if updates.get("data_processing"):
            dp = updates.pop("data_processing")
            dp_dict = dp if isinstance(dp, dict) else (dp.model_dump() if hasattr(dp, "model_dump") else dict(dp))
            merged = dict(col.collection_metadata or {})
            if getattr(col, "document_count", 0) and col.document_count > 0:
                old_dp = merged.get("data_processing") or {}
                old_emb = old_dp.get("embedding_model")
                new_emb = dp_dict.get("embedding_model")
                if old_emb and new_emb and old_emb != new_emb:
                    raise AppException(
                        f"Không thể thay đổi mô hình Embedding ('{old_emb}' -> '{new_emb}') khi Kho tri thức đã có dữ liệu. Vui lòng tạo kho mới hoặc chạy Re-index.",
                        code="CANNOT_CHANGE_EMBEDDING_OF_POPULATED_COLLECTION",
                        status_code=400,
                    )
            merged["data_processing"] = dp_dict
            col.collection_metadata = merged
        for field, value in updates.items():
            if hasattr(col, field):
                setattr(col, field, value)
        await db.commit()
        await db.refresh(col)
        return col

    async def delete_collection(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ) -> None:
        """Delete a collection, all its documents, chunks, facts, and Qdrant index (zero ghost collections)."""
        col = await self.get_collection(db, collection_id, actor=actor)

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
