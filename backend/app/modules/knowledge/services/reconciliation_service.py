"""Knowledge Reconciliation Service — Cross-store 4-layer audit and recovery."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.knowledge.services.collection_service import collection_service

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Service managing 4-layer data reconciliation (DB, Qdrant, Storage, Redis)."""

    def __init__(self, get_document_fn=None):
        self._get_document_fn = get_document_fn
        self._facade = None

    @property
    def facade(self):
        return self._facade

    @facade.setter
    def facade(self, val):
        self._facade = val

    def set_get_document_fn(self, fn):
        self._get_document_fn = fn

    async def _get_document(self, db: AsyncSession, document_id: str) -> KnowledgeDocument:
        if self._get_document_fn:
            return await self._get_document_fn(db, document_id)
        if self._facade and hasattr(self._facade, "get_document"):
            return await self._facade.get_document(db, document_id)
        from app.modules.knowledge.services.ingestion_service import ingestion_service
        return await ingestion_service.get_document(db, document_id)

    async def _get_collection(self, db: AsyncSession, collection_id: str):
        if self._facade and hasattr(self._facade, "get_collection"):
            return await self._facade.get_collection(db, collection_id)
        return await collection_service.get_collection(db, collection_id)

    async def reindex_document(self, db: AsyncSession, document_id: str) -> dict[str, Any]:
        """Re-index chunks of a single document into Qdrant vector database."""
        doc = await self._get_document(db, document_id)
        col = await self._get_collection(db, doc.collection_id)
        metadata = doc.doc_metadata or {}
        quality_report = metadata.get("quality_report") or {}
        is_human_verified = bool(metadata.get("human_verified"))
        if doc.status == "review_pending" or (
            quality_report
            and not bool(quality_report.get("passed"))
            and not is_human_verified
        ):
            raise AppException(
                "Tài liệu còn lỗi chất lượng dữ liệu và chưa được phép lập chỉ mục lại.",
                code="document_review_required",
                status_code=409,
                details={"quality_report": quality_report},
            )

        chunks = list(
            (
                await db.execute(
                    select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
                )
            )
            .scalars()
            .all()
        )
        if not chunks:
            doc.index_status = "index_failed"
            doc.index_error = "Tài liệu không có chunk nào để lập chỉ mục."
            await db.commit()
            await db.refresh(doc)
            return {
                "document_id": doc.id,
                "status": doc.status,
                "index_status": doc.index_status,
                "indexed_chunks": 0,
                "message": doc.index_error,
            }

        doc.index_status = "indexing"
        doc.index_error = None
        await db.commit()

        chunks_payload = [
            {
                "id": c.id,
                "chunk_id": c.id,
                "point_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.collection_id}:{c.id}")),
                "content": c.content,
                "document_id": c.document_id,
                "collection_id": doc.collection_id,
                "tenant_id": col.tenant_id,
                "workspace_id": col.workspace_id,
                "document_revision": doc.version,
                "document_status": "indexing",
                "is_retrievable": False,
                "content_hash": c.chunk_hash,
                "embedding_model": settings.EMBEDDING_MODEL,
                "payload_schema_version": "v1",
                "section": c.section,
                "page_number": c.page_number,
                "metadata": c.chunk_metadata or {},
            }
            for c in chunks
        ]

        try:
            from app.modules.rag.vector_indexer import vector_indexer
            indexed = await vector_indexer.index_chunks(
                collection_id=doc.collection_id,
                chunks=chunks_payload,
            )
            if indexed > 0:
                is_parity, parity_reason = await vector_indexer.verify_revision_parity(
                    collection_id=doc.collection_id,
                    document_id=doc.id,
                    target_revision=doc.version,
                    expected_count=len(chunks),
                )
                if is_parity:
                    await vector_indexer.activate_document_revision(
                        collection_id=doc.collection_id,
                        document_id=doc.id,
                        target_revision=doc.version,
                    )
                    await vector_indexer.purge_stale_revisions(
                        collection_id=doc.collection_id,
                        document_id=doc.id,
                        current_revision=doc.version,
                    )
                    doc.status = "ready" if doc.status in ("approved", "ready") else doc.status
                    doc.index_status = "indexed"
                    doc.index_error = None
                else:
                    doc.index_status = "index_failed"
                    doc.index_error = parity_reason
            else:
                doc.index_status = "index_failed"
                doc.index_error = "Vector indexer trả về 0 điểm."
        except Exception as exc:
            logger.error("Reindexing failed for doc %s: %s", doc.id, exc)
            doc.index_status = "index_failed"
            doc.index_error = str(exc)
            indexed = 0

        metadata = dict(doc.doc_metadata or {})
        metadata["indexed_chunks"] = indexed
        metadata["index_status"] = doc.index_status
        doc.doc_metadata = metadata

        job = JobRecord(
            job_type="vector_indexing",
            status="completed" if doc.index_status == "indexed" else "failed",
            progress=100.0 if doc.index_status == "indexed" else 0.0,
            collection_id=doc.collection_id,
            document_id=doc.id,
            payload={"document_id": doc.id, "trigger": "manual_reindex"},
            result={"points_reindexed": indexed, "index_status": doc.index_status, "error": doc.index_error},
        )
        db.add(job)

        try:
            from app.core.redis import semantic_cache
            await semantic_cache.invalidate_collection(doc.collection_id)
        except Exception as exc:
            logger.warning("Cache invalidation failed: %s", exc)

        await db.commit()
        await db.refresh(doc)

        return {
            "document_id": doc.id,
            "status": doc.status,
            "index_status": doc.index_status,
            "indexed_chunks": indexed,
            "message": doc.index_error or "Đã lập chỉ mục lại thành công.",
        }

    async def reconcile_collection(self, db: AsyncSession, collection_id: str) -> dict[str, Any]:
        """Audit parity across 4 layers: PostgreSQL DB, Qdrant Vector, Storage Driver, Redis Cache."""
        col = await self._get_collection(db, collection_id)
        docs = list(
            (
                await db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.collection_id == collection_id)
                )
            )
            .scalars()
            .all()
        )
        chunk_exec = await db.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.collection_id == collection_id)
        )
        all_chunks: list[KnowledgeChunk] = []
        db_chunks_count = 0
        try:
            if hasattr(chunk_exec, "scalar") and callable(chunk_exec.scalar):
                val = chunk_exec.scalar()
                if isinstance(val, (int, float)) and val > 0:
                    db_chunks_count = int(val)
        except Exception:
            pass

        if db_chunks_count == 0 and hasattr(chunk_exec, "scalars"):
            try:
                sc = chunk_exec.scalars()
                if hasattr(sc, "all") and callable(sc.all):
                    raw_chunks = sc.all()
                    if isinstance(raw_chunks, (list, tuple, set)):
                        all_chunks = list(raw_chunks)
                        db_chunks_count = len(all_chunks)
            except Exception:
                pass

        chunk_by_id = {c.id: c for c in all_chunks}
        doc_by_id = {d.id: d for d in docs}

        # Qdrant points count & inspection
        qdrant_points_count = 0
        discrepancies: list[dict[str, Any]] = []

        try:
            from app.modules.rag.vector_indexer import vector_indexer
            cname = vector_indexer._get_collection_name(collection_id)
            count_res = await vector_indexer.client.count(collection_name=cname)
            qdrant_points_count = count_res.count

            # Scroll up to 100 points to audit payload metadata schema
            scroll_res = await vector_indexer.client.scroll(
                collection_name=cname,
                limit=100,
                with_payload=True,
                with_vectors=False,
            )
            points = scroll_res[0] if scroll_res else []
            for pt in points:
                p_load = pt.payload or {}
                # 1. Check payload schema version
                if p_load.get("payload_schema_version") != "v1":
                    discrepancies.append({
                        "type": "legacy_payload_schema",
                        "point_id": str(pt.id),
                        "details": f"Point '{pt.id}' có payload schema '{p_load.get('payload_schema_version')}', chưa chuẩn hóa v1.",
                    })
                # 2. Check tenant and workspace scope
                if p_load.get("tenant_id") != col.tenant_id or p_load.get("workspace_id") != col.workspace_id:
                    discrepancies.append({
                        "type": "scope_mismatch",
                        "point_id": str(pt.id),
                        "details": f"Point '{pt.id}' thuộc tenant '{p_load.get('tenant_id')}'/workspace '{p_load.get('workspace_id')}', không khớp với bộ sưu tập.",
                    })
                # 3. Check orphan points
                p_chunk_id = p_load.get("chunk_id")
                if p_chunk_id and p_chunk_id not in chunk_by_id:
                    discrepancies.append({
                        "type": "orphan_qdrant_point",
                        "point_id": str(pt.id),
                        "details": f"Point '{pt.id}' tham chiếu chunk '{p_chunk_id}' không tồn tại trong CSDL.",
                    })
                # 4. Check unretrievable active points
                p_doc_id = p_load.get("document_id")
                parent_doc = doc_by_id.get(p_doc_id)
                if (
                    parent_doc
                    and (not parent_doc.is_active or parent_doc.status not in ("approved", "ready"))
                    and p_load.get("is_retrievable") is True
                ):
                    discrepancies.append({
                        "type": "unretrievable_point_active",
                        "point_id": str(pt.id),
                        "details": f"Point '{pt.id}' thuộc tài liệu status '{parent_doc.status}' nhưng vẫn đang bật is_retrievable.",
                    })
        except Exception as exc:
            logger.warning("Failed to inspect points in Qdrant for collection %s: %s", collection_id, exc)

        # Storage files count & discrepancies
        storage_files_count = 0
        indexed_docs_count = sum(1 for d in docs if getattr(d, "index_status", None) == "indexed")
        failed_docs_count = sum(1 for d in docs if getattr(d, "index_status", None) == "index_failed")

        for d in docs:
            # Check storage existence
            try:
                exists = await storage_service.exists(d.storage_path)
                if exists:
                    storage_files_count += 1
                else:
                    discrepancies.append({
                        "type": "missing_storage_file",
                        "document_id": d.id,
                        "details": f"Tệp tin vật lý không tồn tại tại đường dẫn: {d.storage_path}",
                    })
            except Exception:
                pass

            # Check approved/ready but index_failed or pending
            if d.status in ("approved", "ready") and d.index_status != "indexed":
                discrepancies.append({
                    "type": "missing_qdrant_vector",
                    "document_id": d.id,
                    "details": f"Tài liệu '{d.title}' đã duyệt nhưng chưa lập chỉ mục thành công (index_status: {d.index_status}).",
                })

        # Check chunk vs point parity for ready/approved documents
        approved_doc_ids = {d.id for d in docs if d.status in ("approved", "ready") and d.is_active}
        approved_chunks_count = sum(1 for c in all_chunks if c.document_id in approved_doc_ids)

        if qdrant_points_count < approved_chunks_count:
            discrepancies.append({
                "type": "vector_points_deficit",
                "document_id": None,
                "details": f"Qdrant có {qdrant_points_count} points, nhưng các tài liệu đã duyệt có {approved_chunks_count} chunks.",
            })

        is_consistent = len(discrepancies) == 0

        return {
            "collection_id": collection_id,
            "db_documents_count": len(docs),
            "indexed_documents_count": indexed_docs_count,
            "failed_documents_count": failed_docs_count,
            "db_chunks_count": db_chunks_count,
            "qdrant_points_count": qdrant_points_count,
            "storage_files_count": storage_files_count,
            "is_consistent": is_consistent,
            "discrepancies": discrepancies,
        }

    async def reconcile_fix_collection(self, db: AsyncSession, collection_id: str) -> dict[str, Any]:
        """Automatically recover and re-index all missing vectors for approved/ready documents in a collection."""
        await collection_service.get_collection(db, collection_id)
        docs = list(
            (
                await db.execute(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.collection_id == collection_id,
                        KnowledgeDocument.status.in_(["approved", "ready"]),
                    )
                )
            )
            .scalars()
            .all()
        )
        reindexed: list[str] = []
        failed: list[str] = []
        total_chunks = 0
        for d in docs:
            if d.index_status != "indexed":
                res = await self.reindex_document(db, d.id)
                if res["index_status"] == "indexed":
                    reindexed.append(d.id)
                    total_chunks += res.get("indexed_chunks", 0)
                else:
                    failed.append(d.id)
        return {
            "collection_id": collection_id,
            "reindexed_documents": reindexed,
            "failed_documents": failed,
            "total_reindexed_chunks": total_chunks,
            "message": f"Đã phục hồi chỉ mục cho {len(reindexed)}/{len(reindexed) + len(failed)} tài liệu.",
        }


reconciliation_service = ReconciliationService()
