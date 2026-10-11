"""Reconciliation Service — 3-way consistency audit (PostgreSQL - MinIO - Qdrant) & Orphan Points GC.

Dual-layer support:
- Modern V3: When collection has active_vector_generation_id, audits KnowledgeBinding,
             KnowledgeSourceRevision, KnowledgeChunkSet, KnowledgeVectorGeneration, and clean_orphan_points.
- Legacy V1: KnowledgeDocument & KnowledgeChunk parity, storage verification, reindex_document.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeChunkSet,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.services.scope_helper import get_scoped_collection
from app.modules.rag.vector_indexer import vector_indexer

logger = logging.getLogger(__name__)


class ReconciliationReport(BaseModel):
    model_config = {"extra": "allow"}

    collection_id: str
    active_sources: int = 0
    source_revisions_count: int = 0
    chunk_sets_count: int = 0
    vector_generations_count: int = 0
    active_vector_generation_id: str | None = None
    expected_qdrant_points: int = 0
    actual_qdrant_points: int = 0
    parity_healthy: bool = True
    orphan_points_detected: int = 0
    issues: list[str] = Field(default_factory=list)

    # Legacy compatibility fields (dict-accessible)
    db_documents_count: int = 0
    indexed_documents_count: int = 0
    failed_documents_count: int = 0
    db_chunks_count: int = 0
    qdrant_points_count: int = 0
    storage_files_count: int = 0
    is_consistent: bool = True
    discrepancies: list[dict[str, Any]] = Field(default_factory=list)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class ReconciliationService:
    """Audits consistency between PostgreSQL relational records, Qdrant vector index, and MinIO storage."""

    def __init__(self, get_document_fn: Any | None = None) -> None:
        self._get_document_fn = get_document_fn
        self._facade: Any | None = None

    @property
    def facade(self) -> Any | None:
        return self._facade

    @facade.setter
    def facade(self, val: Any) -> None:
        self._facade = val

    def set_get_document_fn(self, fn: Any) -> None:
        self._get_document_fn = fn

    async def _get_collection(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ) -> KnowledgeCollection:
        if self._facade and hasattr(self._facade, "get_collection"):
            from app.modules.knowledge.service import KnowledgeService

            if getattr(self._facade.get_collection, "__func__", None) is not KnowledgeService.get_collection:
                try:
                    return await self._facade.get_collection(db, collection_id, actor=actor)
                except TypeError:
                    return await self._facade.get_collection(db, collection_id)
        return await get_scoped_collection(db, collection_id, actor=actor)

    async def _get_document(self, db: AsyncSession, document_id: str) -> KnowledgeDocument:
        if self._get_document_fn:
            return await self._get_document_fn(db, document_id)
        if self._facade and hasattr(self._facade, "get_document"):
            return await self._facade.get_document(db, document_id)
        from app.modules.knowledge.services.ingestion_service import ingestion_service

        return await ingestion_service.get_document(db, document_id)

    async def reconcile_collection(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> ReconciliationReport:
        col = await self._get_collection(db, collection_id, actor=actor)
        meta = dict(col.collection_metadata or {})
        active_gen_id = meta.get("active_vector_generation_id")

        # ----------------------------------------------------------------------
        # PATH A: Modern V3 Collection Audit (Has active_vector_generation_id)
        # ----------------------------------------------------------------------
        if active_gen_id:
            issues: list[str] = []

            # 1. Active bindings count
            bindings_stmt = select(func.count(KnowledgeBinding.id)).where(
                KnowledgeBinding.collection_id == col.id,
                KnowledgeBinding.status == "active",
            )
            raw_sources = (await db.execute(bindings_stmt)).scalar()
            active_sources = int(raw_sources or 0) if isinstance(raw_sources, (int, float)) else 0

            # 2. Source revisions count
            sr_stmt = (
                select(func.count(KnowledgeSourceRevision.id))
                .join(KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id)
                .where(KnowledgeBinding.collection_id == col.id)
            )
            raw_sr = (await db.execute(sr_stmt)).scalar()
            source_revs_count = int(raw_sr or 0) if isinstance(raw_sr, (int, float)) else 0

            # 3. Chunk sets count
            cs_stmt = (
                select(func.count(KnowledgeChunkSet.id))
                .join(
                    KnowledgeSourceRevision,
                    KnowledgeChunkSet.source_revision_id == KnowledgeSourceRevision.id,
                )
                .join(KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id)
                .where(KnowledgeBinding.collection_id == col.id)
            )
            raw_cs = (await db.execute(cs_stmt)).scalar()
            chunk_sets_count = int(raw_cs or 0) if isinstance(raw_cs, (int, float)) else 0

            # 4. Vector generations count
            vg_stmt = select(func.count(KnowledgeVectorGeneration.id)).where(
                KnowledgeVectorGeneration.collection_id == col.id,
            )
            raw_vg = (await db.execute(vg_stmt)).scalar()
            vector_generations_count = int(raw_vg or 0) if isinstance(raw_vg, (int, float)) else 0

            # 5. Expected points count from active index revisions
            points_stmt = (
                select(func.sum(KnowledgeIndexRevision.chunk_count))
                .join(KnowledgeBinding, KnowledgeIndexRevision.binding_id == KnowledgeBinding.id)
                .where(
                    KnowledgeBinding.collection_id == col.id,
                    KnowledgeBinding.status == "active",
                    KnowledgeIndexRevision.status == "active",
                )
            )
            raw_points = (await db.execute(points_stmt)).scalar()
            expected_points = int(raw_points or 0) if isinstance(raw_points, (int, float)) else 0

            # 6. Actual points from Qdrant
            actual_points = 0
            try:
                actual_points = await vector_indexer.count_points(col.id)
            except Exception as exc:
                issues.append(f"Không thể truy vấn số points từ Qdrant: {exc}")

            parity_healthy = (expected_points == actual_points) and (len(issues) == 0)
            orphan_points = max(0, actual_points - expected_points)

            if expected_points != actual_points:
                issues.append(
                    f"Lệch số điểm vector: PostgreSQL kỳ vọng {expected_points} points, "
                    f"Qdrant thực tế có {actual_points} points."
                )

            return ReconciliationReport(
                collection_id=col.id,
                active_sources=active_sources,
                source_revisions_count=source_revs_count,
                chunk_sets_count=chunk_sets_count,
                vector_generations_count=vector_generations_count,
                active_vector_generation_id=active_gen_id,
                expected_qdrant_points=expected_points,
                actual_qdrant_points=actual_points,
                parity_healthy=parity_healthy,
                orphan_points_detected=orphan_points,
                issues=issues,
                db_documents_count=0,
                indexed_documents_count=0,
                failed_documents_count=0,
                db_chunks_count=0,
                qdrant_points_count=actual_points,
                storage_files_count=0,
                is_consistent=parity_healthy,
                discrepancies=[],
            )

        # ----------------------------------------------------------------------
        # PATH B: Legacy V1 Collection Audit (KnowledgeDocument & KnowledgeChunk)
        # ----------------------------------------------------------------------
        issues = []
        discrepancies: list[dict[str, Any]] = []

        docs: list[KnowledgeDocument] = []
        all_legacy_chunks: list[KnowledgeChunk] = []

        try:
            docs_stmt = select(KnowledgeDocument).where(KnowledgeDocument.collection_id == col.id)
            docs_exec = await db.execute(docs_stmt)
            if hasattr(docs_exec, "scalars"):
                docs = list(docs_exec.scalars().all())
        except Exception:
            docs = []

        try:
            chunks_stmt = select(KnowledgeChunk).where(KnowledgeChunk.collection_id == col.id)
            chunks_exec = await db.execute(chunks_stmt)
            if hasattr(chunks_exec, "scalars"):
                all_legacy_chunks = list(chunks_exec.scalars().all())
        except Exception:
            all_legacy_chunks = []

        db_chunks_count = len(all_legacy_chunks)
        indexed_docs_count = sum(1 for d in docs if getattr(d, "index_status", None) == "indexed")
        failed_docs_count = sum(1 for d in docs if getattr(d, "index_status", None) == "index_failed")
        storage_files_count = 0

        chunks_per_doc: dict[str, int] = {}
        for c in all_legacy_chunks:
            if hasattr(c, "document_id"):
                chunks_per_doc[c.document_id] = chunks_per_doc.get(c.document_id, 0) + 1

        active_indexable_doc_ids = {
            d.id for d in docs if getattr(d, "is_active", True) and getattr(d, "status", None) in ("approved", "ready")
        }
        legacy_expected_points = sum(
            1 for c in all_legacy_chunks if getattr(c, "document_id", None) in active_indexable_doc_ids
        )

        for d in docs:
            try:
                if d.storage_path and await storage_service.exists(d.storage_path):
                    storage_files_count += 1
                elif d.storage_path:
                    discrepancies.append({
                        "type": "missing_storage_file",
                        "document_id": d.id,
                        "details": f"Tệp tin vật lý không tồn tại tại đường dẫn: {d.storage_path}",
                    })
            except Exception:
                pass

            if getattr(d, "status", None) in ("approved", "ready") and getattr(d, "index_status", None) != "indexed":
                discrepancies.append({
                    "type": "missing_qdrant_vector",
                    "document_id": d.id,
                    "details": f"Tài liệu '{getattr(d, 'title', d.id)}' đã duyệt nhưng chưa lập chỉ mục thành công (index_status: {getattr(d, 'index_status', None)}).",
                })

            if d.id in active_indexable_doc_ids and chunks_per_doc.get(d.id, 0) == 0:
                discrepancies.append({
                    "type": "missing_document_chunks",
                    "document_id": d.id,
                    "details": f"Tài liệu '{getattr(d, 'title', d.id)}' đã duyệt nhưng không có chunk dữ liệu.",
                })

        actual_points = 0
        try:
            cname = vector_indexer._get_collection_name(col.id)
            if hasattr(vector_indexer.client, "collection_exists"):
                exists = await vector_indexer.client.collection_exists(cname)
                if exists:
                    count_res = await vector_indexer.client.count(collection_name=cname)
                    actual_points = getattr(count_res, "count", 0)
                elif legacy_expected_points > 0:
                    discrepancies.append({
                        "type": "missing_qdrant_collection",
                        "document_id": None,
                        "details": f"Qdrant chưa có collection '{cname}'.",
                    })
            else:
                actual_points = await vector_indexer.count_points(col.id)
        except Exception as exc:
            issues.append(f"Không thể truy vấn số points từ Qdrant: {exc}")

        if actual_points < legacy_expected_points:
            discrepancies.append({
                "type": "vector_points_deficit",
                "document_id": None,
                "details": f"Qdrant có {actual_points} points, nhưng các tài liệu đã duyệt có {legacy_expected_points} chunks.",
            })

        is_consistent = (len(discrepancies) == 0) and (len(issues) == 0)
        return ReconciliationReport(
            collection_id=col.id,
            active_sources=0,
            source_revisions_count=0,
            chunk_sets_count=0,
            vector_generations_count=0,
            active_vector_generation_id=None,
            expected_qdrant_points=legacy_expected_points,
            actual_qdrant_points=actual_points,
            parity_healthy=is_consistent,
            orphan_points_detected=max(0, actual_points - legacy_expected_points),
            issues=issues,
            db_documents_count=len(docs),
            indexed_documents_count=indexed_docs_count,
            failed_documents_count=failed_docs_count,
            db_chunks_count=db_chunks_count,
            qdrant_points_count=actual_points,
            storage_files_count=storage_files_count,
            is_consistent=is_consistent,
            discrepancies=discrepancies,
        )

    async def clean_orphan_points(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> int:
        """Purge stale Qdrant points not belonging to any active index revision in this collection."""
        col = await self._get_collection(db, collection_id, actor=actor)

        # Fetch all active index revision IDs for this collection
        active_revs_stmt = (
            select(KnowledgeIndexRevision.id)
            .join(KnowledgeBinding, KnowledgeIndexRevision.binding_id == KnowledgeBinding.id)
            .where(
                KnowledgeBinding.collection_id == col.id,
                KnowledgeIndexRevision.status == "active",
            )
        )
        active_rev_ids = set((await db.execute(active_revs_stmt)).scalars().all())

        # Also fetch archived/failed revisions that still have points
        stale_revs_stmt = (
            select(KnowledgeIndexRevision.id)
            .join(KnowledgeBinding, KnowledgeIndexRevision.binding_id == KnowledgeBinding.id)
            .where(
                KnowledgeBinding.collection_id == col.id,
                KnowledgeIndexRevision.status.in_(["archived", "pruned", "failed"]),
            )
        )
        stale_rev_ids = (await db.execute(stale_revs_stmt)).scalars().all()

        purged_total = 0
        for stale_id in stale_rev_ids:
            if stale_id not in active_rev_ids:
                try:
                    if hasattr(vector_indexer, "delete_points_by_index_revision"):
                        deleted = await vector_indexer.delete_points_by_index_revision(col.id, stale_id)
                    else:
                        deleted = await vector_indexer.delete_by_revision(col.id, stale_id)
                    purged_total += int(deleted or 0)
                except Exception as exc:
                    logger.warning("Error purging index revision points %s: %s", stale_id, exc)

        logger.info(
            "Cleaned %s orphan points for collection %s",
            purged_total,
            col.id,
        )
        return purged_total

    async def reindex_document(
        self, db: AsyncSession, document_id: str, actor: Any | None = None
    ) -> dict[str, Any]:
        """Re-index chunks of a single legacy document into Qdrant vector database."""
        doc = await self._get_document(db, document_id)
        col = await self._get_collection(db, doc.collection_id, actor=actor)
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

        col_dp = (col.collection_metadata.get("data_processing") or {}) if col and col.collection_metadata else {}
        col_embedding_model = col_dp.get("embedding_model")
        if not col_embedding_model:
            from app.modules.modelops.services.model_catalog_service import model_catalog_service

            try:
                catalog = await model_catalog_service.get_system_model_defaults(db)
                col_embedding_model = catalog.defaults.default_embedding_model
            except Exception:
                col_embedding_model = "BAAI/bge-m3"

        if not col_embedding_model:
            col_embedding_model = "BAAI/bge-m3"

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
                "document_revision": getattr(doc, "version", 1),
                "document_status": "indexing",
                "is_retrievable": False,
                "content_hash": getattr(c, "chunk_hash", ""),
                "embedding_model": col_embedding_model,
                "payload_schema_version": "v1",
                "section": getattr(c, "section", None),
            }
            for c in chunks
        ]

        indexed_count = await vector_indexer.index_chunks(
            doc.collection_id, chunks_payload, model_name=col_embedding_model
        )
        await vector_indexer.activate_document_revision(
            doc.collection_id, doc.id, getattr(doc, "version", 1)
        )
        doc.status = "ready" if doc.status in ("approved", "ready") else doc.status
        doc.index_status = "indexed"
        doc.index_error = None

        meta = dict(doc.doc_metadata or {})
        meta["indexed_chunks"] = indexed_count
        meta["index_status"] = doc.index_status
        doc.doc_metadata = meta

        job = JobRecord(
            job_type="vector_indexing",
            status="completed" if doc.index_status == "indexed" else "failed",
            progress=100.0 if doc.index_status == "indexed" else 0.0,
            collection_id=doc.collection_id,
            document_id=doc.id,
            payload={"document_id": doc.id, "trigger": "manual_reindex"},
            result={"points_reindexed": indexed_count, "index_status": doc.index_status, "error": doc.index_error},
        )
        db.add(job)

        await db.commit()
        await db.refresh(doc)
        return {
            "document_id": doc.id,
            "status": doc.status,
            "index_status": doc.index_status,
            "indexed_chunks": indexed_count,
            "message": "Đã lập chỉ mục lại thành công.",
        }

    async def reconcile_fix_collection(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ) -> dict[str, Any]:
        """Automatically recover and re-index all missing vectors for approved/ready documents in a collection."""
        col = await self._get_collection(db, collection_id, actor=actor)
        docs = list(
            (
                await db.execute(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.collection_id == col.id,
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
                res = await self.reindex_document(db, d.id, actor=actor)
                if res["index_status"] == "indexed":
                    reindexed.append(d.id)
                    total_chunks += res.get("indexed_chunks", 0)
                else:
                    failed.append(d.id)
        return {
            "collection_id": col.id,
            "reindexed_documents": reindexed,
            "failed_documents": failed,
            "total_reindexed_chunks": total_chunks,
            "message": f"Đã phục hồi chỉ mục cho {len(reindexed)}/{len(reindexed) + len(failed)} tài liệu.",
        }


reconciliation_service = ReconciliationService()
