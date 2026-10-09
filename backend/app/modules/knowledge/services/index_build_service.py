"""Knowledge Index Build Service — Staging build, Parity Gate, and atomic pointer swap."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.knowledge.chunker import get_chunker
from app.modules.knowledge.cleaner import clean_markdown_text
from app.modules.knowledge.models import (
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeIndexActivation,
    KnowledgeIndexRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import (
    IndexActivationResponse,
    KnowledgeIndexRevisionResponse,
    ParityReportDTO,
)
from app.modules.knowledge.services.scope_helper import (
    bump_collection_index_epoch,
    get_scoped_binding,
    get_scoped_collection,
    get_scoped_index_revision,
)

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


class IndexBuildService:
    """Service managing staging index builds, Parity Gate, and atomic pointer swaps."""

    async def get_or_create_vector_generation(
        self,
        db: AsyncSession,
        collection: KnowledgeCollection,
    ) -> KnowledgeVectorGeneration:
        """Resolve the configured vector space without coupling it to publication epochs."""
        meta = collection.collection_metadata or {}
        dp = meta.get("data_processing") or {}
        from app.modules.modelops.services.model_catalog_service import model_catalog_service
        from app.modules.rag.vector_indexer import vector_indexer

        catalog = await model_catalog_service.get_system_model_defaults(db)
        defaults = catalog.defaults
        model_name = dp.get("embedding_model") or defaults.default_embedding_model
        provider_id = (
            dp.get("embedding_provider_id") or defaults.default_embedding_provider_id
        )
        if not model_name or not provider_id:
            raise AppException(
                "Chưa cấu hình embedding provider/model trong ModelOps.",
                code="EMBEDDING_MODEL_NOT_CONFIGURED",
                status_code=409,
            )
        meta_dim: int | None = None
        if dp.get("embedding_dimension") is not None:
            try:
                meta_dim = int(dp["embedding_dimension"])
            except (ValueError, TypeError):
                meta_dim = None

        dim = await model_catalog_service.resolve_embedding_dimension(
            db,
            provider_id,
            model_name,
            metadata_dimension=meta_dim,
        )

        qdrant_collection_name = vector_indexer._get_collection_name(collection.id)
        config_hash = hashlib.sha256(
            f"{provider_id}:{model_name}:{dim}:cosine:v2".encode()
        ).hexdigest()

        # Serialize vector-space creation per collection. Publication epochs may
        # change many times while one embedding generation remains active.
        await db.execute(
            select(KnowledgeCollection.id)
            .where(KnowledgeCollection.id == collection.id)
            .with_for_update()
        )
        active_stmt = (
            select(KnowledgeVectorGeneration)
            .where(
                KnowledgeVectorGeneration.collection_id == collection.id,
                KnowledgeVectorGeneration.status == "active",
            )
            .order_by(KnowledgeVectorGeneration.generation_epoch.desc())
        )
        active_gen = (await db.execute(active_stmt)).scalars().first()
        if active_gen:
            if active_gen.config_hash != config_hash:
                raise AppException(
                    "Cấu hình embedding đã thay đổi; cần chạy quy trình chuyển đổi vector generation trước khi xuất bản.",
                    code="VECTOR_GENERATION_MIGRATION_REQUIRED",
                    status_code=409,
                    details={
                        "active_generation_id": active_gen.id,
                        "active_config_hash": active_gen.config_hash,
                        "requested_config_hash": config_hash,
                    },
                )
            return active_gen

        max_epoch_stmt = select(
            func.coalesce(func.max(KnowledgeVectorGeneration.generation_epoch), 0)
        ).where(KnowledgeVectorGeneration.collection_id == collection.id)
        next_generation_epoch = int((await db.execute(max_epoch_stmt)).scalar() or 0) + 1

        gen = KnowledgeVectorGeneration(
            collection_id=collection.id,
            embedding_model=model_name,
            provider_id=provider_id,
            qdrant_collection_name=qdrant_collection_name,
            config_hash=config_hash,
            payload_schema_version=2,
            embedding_dimension=dim,
            distance_metric="cosine",
            generation_epoch=next_generation_epoch,
            status="active",
            tenant_id=collection.tenant_id,
            workspace_id=collection.workspace_id,
        )
        db.add(gen)
        await db.flush()
        return gen

    async def _ensure_collection_doc_projection(
        self,
        db: AsyncSession,
        collection_id: str,
        rep_doc: RepositoryDocument,
    ) -> KnowledgeDocument:
        """Ensure a KnowledgeDocument projection exists for backward compatibility with RAG and Studio."""
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.collection_id == collection_id,
            KnowledgeDocument.repository_document_id == rep_doc.id,
        )
        kdoc = (await db.execute(stmt)).scalar_one_or_none()
        if not kdoc:
            kdoc = KnowledgeDocument(
                collection_id=collection_id,
                repository_document_id=rep_doc.id,
                title=rep_doc.title,
                file_name=rep_doc.file_name,
                file_type=rep_doc.file_type,
                file_size_bytes=rep_doc.file_size_bytes,
                file_hash=rep_doc.file_hash,
                storage_path=rep_doc.storage_path,
                status="processed",
                index_status="indexing",
                is_active=True,
                version=1,
            )
            db.add(kdoc)
            await db.flush()
        return kdoc

    async def _check_job_cancelled(
        self,
        db: AsyncSession,
        job_id: str | None,
        idx_rev: KnowledgeIndexRevision | None = None,
        point_ids: list[str] | None = None,
        col_id: str | None = None,
    ) -> bool:
        if not job_id:
            return False
        from app.modules.jobs.models import JobRecord
        from app.modules.jobs.service import is_job_cancelled

        if await is_job_cancelled(job_id, db=db):
            stmt = (
                select(JobRecord)
                .where(JobRecord.id == job_id)
                .execution_options(populate_existing=True)
            )
            job = (await db.execute(stmt)).scalar_one_or_none()
            if job:
                job.status = "cancelled"
                job.phase = "cancelled"
                job.cancel_requested = True
                job.error = "Tác vụ đã bị hủy bởi người dùng (cooperative cancel)."
            if idx_rev:
                idx_rev.status = "failed"
                idx_rev.failure_code = "JOB_CANCELLED"
                idx_rev.failure_detail = "Tác vụ dựng chỉ mục đã bị hủy bởi người dùng (cooperative cancel)."
                idx_rev.finished_at = utcnow()
            await db.commit()
            if point_ids and col_id:
                try:
                    from qdrant_client.http import models as qmodels

                    from app.modules.rag.vector_indexer import vector_indexer

                    cname = vector_indexer._get_collection_name(col_id)
                    await vector_indexer.client.delete(
                        collection_name=cname,
                        points_selector=qmodels.PointIdsList(points=point_ids),
                    )
                except Exception as exc:
                    correlation_id = getattr(idx_rev, "id", None) or job_id
                    logger.error(
                        "Could not clean up partial points on cancel. Reconciliation required: correlation_id=%s, col_id=%s, err=%s",
                        correlation_id,
                        col_id,
                        exc,
                    )
            return True
        return False

    async def build_staging_index(
        self,
        db: AsyncSession,
        binding_id: str,
        source_revision_id: str | None = None,
        chunk_strategy: str | None = None,
        auto_activate: bool = False,
        actor: Any | None = None,
        job_id: str | None = None,
    ) -> KnowledgeIndexRevision:
        """Build immutable indexing artifact in staging without touching active query vectors."""
        # Checkpoint 0: Cancel check before starting
        if await self._check_job_cancelled(db, job_id):
            raise AppException("Job đã bị hủy trước khi bắt đầu.", code="JOB_CANCELLED", status_code=409)

        # 1. Fetch Binding and Collection with lock and actor scope
        binding = await get_scoped_binding(db, binding_id, actor=actor, for_update=True)
        col = await get_scoped_collection(db, binding.collection_id, actor=actor)

        rep_doc = await db.get(RepositoryDocument, binding.repository_document_id)
        if not rep_doc:
            raise EntityNotFoundError(f"Không tìm thấy tài liệu kho '{binding.repository_document_id}'")

        # 2. Resolve source document revision
        target_rev_id = source_revision_id or binding.source_revision_id
        source_rev = await db.get(DocumentRevision, target_rev_id)
        if not source_rev:
            raise EntityNotFoundError(f"Không tìm thấy phiên bản tài liệu '{target_rev_id}'")
        if source_rev.document_id != rep_doc.id:
            raise AppException(
                "Phiên bản nguồn không thuộc tài liệu của binding.",
                code="SOURCE_REVISION_DOCUMENT_MISMATCH",
                status_code=409,
            )
        if source_rev.status != "ready":
            raise AppException(
                f"Chỉ revision 'ready' mới được xuất bản (hiện tại: {source_rev.status}).",
                code="SOURCE_REVISION_NOT_READY",
                status_code=409,
            )
        if (
            binding.tenant_id != col.tenant_id
            or (col.workspace_id and binding.workspace_id != col.workspace_id)
            or rep_doc.tenant_id != col.tenant_id
            or (col.workspace_id and rep_doc.workspace_id != col.workspace_id)
        ):
            raise AppException(
                "Binding, tài liệu và bộ sưu tập không cùng tenant/workspace.",
                code="KNOWLEDGE_SCOPE_MISMATCH",
                status_code=409,
            )

        # 3. Resolve active Vector Generation
        vector_gen = await self.get_or_create_vector_generation(db, col)

        # 4. Determine next revision number for this binding
        rev_no_stmt = select(func.coalesce(func.max(KnowledgeIndexRevision.revision_no), 0) + 1).where(
            KnowledgeIndexRevision.binding_id == binding.id
        )
        next_rev_no = (await db.execute(rev_no_stmt)).scalar() or 1

        # 5. Create KnowledgeIndexRevision record in 'building' status
        idx_rev = KnowledgeIndexRevision(
            binding_id=binding.id,
            source_revision_id=source_rev.id,
            vector_generation_id=vector_gen.id,
            revision_no=next_rev_no,
            chunk_count=0,
            fact_count=0,
            point_ids=[],
            parity_report={},
            status="building",
            lock_version=1,
        )
        db.add(idx_rev)
        await db.flush()

        # Checkpoint 1: Cancel check after creating revision record
        if await self._check_job_cancelled(db, job_id, idx_rev):
            return idx_rev

        # 6. Extract raw text or markdown
        raw_text = (
            getattr(source_rev, "canonical_markdown", None)
            or getattr(source_rev, "extracted_markdown", None)
            or getattr(source_rev, "extracted_text", None)
            or ""
        )
        cleaned_text = clean_markdown_text(raw_text)

        if not cleaned_text.strip():
            idx_rev.status = "failed"
            idx_rev.failure_code = "EMPTY_EXTRACTED_TEXT"
            idx_rev.failure_detail = "Phiên bản tài liệu không có nội dung văn bản bóc tách."
            idx_rev.finished_at = utcnow()
            await db.commit()
            return idx_rev

        # 7. Chunk text using chunk_strategy
        strategy = chunk_strategy or binding.chunk_strategy or "ClauseBasedChunker"
        chunker = get_chunker(strategy)
        chunks_data = chunker.chunk(cleaned_text)

        if not chunks_data:
            idx_rev.status = "failed"
            idx_rev.failure_code = "CHUNKER_RETURNED_ZERO"
            idx_rev.failure_detail = f"Thuật toán {strategy} trả về 0 chunks."
            idx_rev.finished_at = utcnow()
            await db.commit()
            return idx_rev

        # Checkpoint 2: Cancel check after chunking
        if await self._check_job_cancelled(db, job_id, idx_rev):
            return idx_rev

        # 8. Ensure projection document in knowledge_documents
        kdoc = await self._ensure_collection_doc_projection(db, col.id, rep_doc)

        # 9. Store Chunks in DB with binding and revision scope
        created_chunks: list[KnowledgeChunk] = []
        payload_chunks: list[dict[str, Any]] = []
        point_ids: list[str] = []
        expected_points: dict[str, str] = {}

        for idx, c in enumerate(chunks_data):
            if isinstance(c, dict):
                c_text = c.get("text") or c.get("content") or ""
                c_hash = c.get("chunk_hash") or hashlib.sha256(c_text.encode("utf-8")).hexdigest()
                c_tokens = c.get("token_count") or max(1, len(c_text) // 4)
                c_section = c.get("section")
                c_page = c.get("page_number", 1) or 1
            else:
                c_text = getattr(c, "content", "")
                c_hash = getattr(c, "chunk_hash", None) or hashlib.sha256(c_text.encode("utf-8")).hexdigest()
                c_tokens = getattr(c, "token_count", None) or max(1, len(c_text) // 4)
                c_section = getattr(c, "section", None)
                c_page = getattr(c, "page_number", 1) or 1

            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{col.id}:{idx_rev.id}:{idx}"))
            point_ids.append(point_id)
            expected_points[point_id] = c_hash

            db_chunk = KnowledgeChunk(
                document_id=kdoc.id,
                collection_id=col.id,
                binding_id=binding.id,
                index_revision_id=idx_rev.id,
                chunk_index=idx,
                content=c_text,
                chunk_hash=c_hash,
                token_count=c_tokens,
                section=c_section,
                page_number=c_page,
                chunk_metadata={
                    "strategy": strategy,
                    "binding_id": binding.id,
                    "index_revision_id": idx_rev.id,
                    "source_revision_id": source_rev.id,
                    "vector_generation_id": vector_gen.id,
                    "point_id": point_id,
                },
            )
            db.add(db_chunk)
            created_chunks.append(db_chunk)

            payload_chunks.append(
                {
                    "id": db_chunk.id,
                    "point_id": point_id,
                    "content": c_text,
                    "content_hash": c_hash,
                    "collection_id": col.id,
                    "tenant_id": col.tenant_id,
                    "workspace_id": col.workspace_id,
                    "document_id": kdoc.id,
                    "repository_document_id": rep_doc.id,
                    "binding_id": binding.id,
                    "index_revision_id": idx_rev.id,
                    "document_revision": source_rev.revision_no,
                    "document_status": "staging",
                    "is_retrievable": False,
                    "section": c_section,
                    "page_number": c_page,
                    "embedding_model": vector_gen.embedding_model,
                    "metadata": {
                        "binding_id": binding.id,
                        "index_revision_id": idx_rev.id,
                        "epoch": vector_gen.generation_epoch,
                    },
                }
            )

        await db.flush()

        # Checkpoint 3: Cancel check before vector indexer call
        if await self._check_job_cancelled(db, job_id, idx_rev, point_ids=point_ids, col_id=col.id):
            return idx_rev

        # 10. Index staging points to Qdrant (without deleting existing points!)
        from app.modules.rag.vector_indexer import vector_indexer

        try:
            indexed_count = await vector_indexer.index_chunks(
                collection_id=col.id,
                chunks=payload_chunks,
                vector_generation=vector_gen,
            )
        except Exception as exc:
            logger.exception("Vector indexing to Qdrant failed for idx_rev %s", idx_rev.id)
            indexed_count = 0
            parity_reason = str(exc)
        else:
            parity_reason = ""

        # Checkpoint 4: Cancel check before parity gate verification
        if await self._check_job_cancelled(db, job_id, idx_rev, point_ids=point_ids, col_id=col.id):
            return idx_rev

        # 11. Run Parity Gate Check (Bảo đảm so khớp 100%)
        db_count = len(created_chunks)
        if indexed_count == db_count:
            parity_passed, parity_reason, verified_count = (
                await vector_indexer.verify_index_revision_parity(
                    collection_id=col.id,
                    index_revision_id=idx_rev.id,
                    expected_points=expected_points,
                )
            )
        else:
            parity_passed = False
            verified_count = 0
            parity_reason = parity_reason or (
                f"Số points index trả về ({indexed_count}) không khớp số chunks ({db_count})."
            )

        parity_report = {
            "expected_chunks": db_count,
            "indexed_points": indexed_count,
            "verified_points": verified_count,
            "point_ids_count": len(point_ids),
            "parity_status": "passed" if parity_passed else "failed",
            "reason": parity_reason,
            "checked_at": utcnow().isoformat(),
        }

        idx_rev.chunk_count = db_count
        idx_rev.point_ids = point_ids
        idx_rev.parity_report = parity_report
        idx_rev.finished_at = utcnow()

        if parity_passed:
            idx_rev.status = "ready"
        else:
            idx_rev.status = "failed"
            idx_rev.failure_code = "PARITY_GATE_MISMATCH"
            idx_rev.failure_detail = parity_reason

        await db.commit()
        await db.refresh(idx_rev)

        # Checkpoint 5: Cancel check before auto-activation
        if await self._check_job_cancelled(db, job_id, idx_rev, point_ids=point_ids, col_id=col.id):
            return idx_rev

        # 12. If auto_activate requested and parity passed, promote immediately
        if auto_activate and idx_rev.status == "ready":
            await self.promote_index_revision(
                db=db,
                binding_id=binding.id,
                index_revision_id=idx_rev.id,
                expected_epoch=binding.active_epoch,
                reason="Auto-activated on staging build completion",
                actor=actor,
            )
            await db.refresh(idx_rev)

        return idx_rev

    async def promote_index_revision(
        self,
        db: AsyncSession,
        binding_id: str,
        index_revision_id: str,
        expected_epoch: int,
        reason: str | None = None,
        activated_by: str | None = None,
        actor: Any | None = None,
    ) -> IndexActivationResponse:
        """Atomic pointer swap: promotes staging index revision to active without downtime."""
        binding = await get_scoped_binding(db, binding_id, actor=actor, for_update=True)

        # Concurrency CAS check (Bắt buộc Compare-And-Swap)
        if binding.active_epoch != expected_epoch:
            raise AppException(
                f"Xung đột phiên bản (CAS conflict): active_epoch hiện tại ({binding.active_epoch}) không khớp expected_epoch ({expected_epoch}).",
                code="CAS_EPOCH_CONFLICT",
                status_code=409,
                details={"current_epoch": binding.active_epoch, "expected_epoch": expected_epoch},
            )

        target_rev = await get_scoped_index_revision(
            db, index_revision_id, binding_id=binding.id, actor=actor
        )

        if target_rev.status != "ready":
            raise AppException(
                f"Không thể kích hoạt revision ở trạng thái '{target_rev.status}'. Chỉ revision 'ready' mới được kích hoạt.",
                code="INVALID_REVISION_STATUS",
                status_code=400,
            )

        if target_rev.chunk_count <= 0:
            raise AppException(
                "Revision không có artifact hợp lệ để kích hoạt.",
                code="EMPTY_INDEX_REVISION",
                status_code=409,
            )

        col = await get_scoped_collection(db, binding.collection_id, actor=actor)

        from app.modules.rag.vector_indexer import vector_indexer

        await vector_indexer.activate_index_revision(
            collection_id=col.id,
            index_revision_id=target_rev.id,
            expected_count=target_rev.chunk_count,
        )

        old_active_id = binding.active_index_revision_id

        # 1. Update previous active revision to archived
        if old_active_id:
            old_rev = await db.get(KnowledgeIndexRevision, old_active_id)
            if old_rev:
                old_rev.status = "archived"

        # 2. Swap pointer & bump epoch atomically
        binding.active_index_revision_id = target_rev.id
        binding.active_epoch += 1
        new_epoch = await bump_collection_index_epoch(db, col.id)
        col.index_epoch = new_epoch
        target_rev.status = "active"

        # 3. Create audit activation log
        activation = KnowledgeIndexActivation(
            binding_id=binding.id,
            from_index_revision_id=old_active_id,
            to_index_revision_id=target_rev.id,
            action="promote",
            epoch=binding.active_epoch,
            reason=reason or "Thăng cấp atomic index revision",
            activated_by=activated_by,
        )
        db.add(activation)

        await db.commit()
        await db.refresh(activation)

        if old_active_id and old_active_id != target_rev.id:
            await vector_indexer.deactivate_index_revision(col.id, old_active_id)

        return IndexActivationResponse(
            id=activation.id,
            binding_id=activation.binding_id,
            from_index_revision_id=activation.from_index_revision_id,
            to_index_revision_id=activation.to_index_revision_id,
            action=activation.action,
            epoch=activation.epoch,
            reason=activation.reason,
            activated_by=activation.activated_by,
            created_at=activation.created_at,
        )

    async def rollback_index_revision(
        self,
        db: AsyncSession,
        binding_id: str,
        target_index_revision_id: str,
        expected_epoch: int,
        reason: str | None = None,
        activated_by: str | None = None,
        actor: Any | None = None,
    ) -> IndexActivationResponse:
        """Instant zero-reindex rollback: reverts active pointer to a historical revision."""
        binding = await get_scoped_binding(db, binding_id, actor=actor, for_update=True)

        if binding.active_epoch != expected_epoch:
            raise AppException(
                f"Xung đột phiên bản (CAS conflict): active_epoch hiện tại ({binding.active_epoch}) không khớp expected_epoch ({expected_epoch}).",
                code="CAS_EPOCH_CONFLICT",
                status_code=409,
                details={"current_epoch": binding.active_epoch, "expected_epoch": expected_epoch},
            )

        target_rev = await get_scoped_index_revision(
            db, target_index_revision_id, binding_id=binding.id, actor=actor
        )

        if target_rev.status == "pruned":
            raise AppException(
                "Phiên bản chỉ mục này đã bị dọn dẹp an toàn (pruned) theo chính sách lưu trữ, không thể rollback trực tiếp. Vui lòng tạo index staging mới.",
                code="REVISION_ALREADY_PRUNED",
                status_code=400,
            )

        if target_rev.status in ("failed", "building"):
            raise AppException(
                f"Không thể rollback về revision ở trạng thái '{target_rev.status}'.",
                code="INVALID_ROLLBACK_TARGET",
                status_code=400,
            )

        if target_rev.chunk_count <= 0:
            raise AppException(
                "Revision không còn artifact hợp lệ để rollback.",
                code="EMPTY_INDEX_REVISION",
                status_code=409,
            )

        col = await get_scoped_collection(db, binding.collection_id, actor=actor)

        from app.modules.rag.vector_indexer import vector_indexer

        await vector_indexer.activate_index_revision(
            collection_id=col.id,
            index_revision_id=target_rev.id,
            expected_count=target_rev.chunk_count,
        )

        old_active_id = binding.active_index_revision_id

        # 1. Update previous active revision to archived
        if old_active_id:
            old_rev = await db.get(KnowledgeIndexRevision, old_active_id)
            if old_rev:
                old_rev.status = "archived"

        # 2. Swap pointer & bump epoch atomically
        binding.active_index_revision_id = target_rev.id
        binding.active_epoch += 1
        new_epoch = await bump_collection_index_epoch(db, col.id)
        col.index_epoch = new_epoch
        target_rev.status = "active"

        # 3. Create audit activation log
        activation = KnowledgeIndexActivation(
            binding_id=binding.id,
            from_index_revision_id=old_active_id,
            to_index_revision_id=target_rev.id,
            action="rollback",
            epoch=binding.active_epoch,
            reason=reason or "Instant zero-reindex rollback",
            activated_by=activated_by,
        )
        db.add(activation)

        await db.commit()
        await db.refresh(activation)

        if old_active_id and old_active_id != target_rev.id:
            await vector_indexer.deactivate_index_revision(col.id, old_active_id)

        return IndexActivationResponse(
            id=activation.id,
            binding_id=activation.binding_id,
            from_index_revision_id=activation.from_index_revision_id,
            to_index_revision_id=activation.to_index_revision_id,
            action=activation.action,
            epoch=activation.epoch,
            reason=activation.reason,
            activated_by=activation.activated_by,
            created_at=activation.created_at,
        )

    async def list_index_revisions(
        self,
        db: AsyncSession,
        binding_id: str,
        actor: Any | None = None,
    ) -> list[KnowledgeIndexRevisionResponse]:
        """List all historical index revisions for a given binding."""
        await get_scoped_binding(db, binding_id, actor=actor)
        stmt = (
            select(KnowledgeIndexRevision)
            .where(KnowledgeIndexRevision.binding_id == binding_id)
            .order_by(KnowledgeIndexRevision.revision_no.desc())
        )
        rows = (await db.execute(stmt)).scalars().all()
        return [
            KnowledgeIndexRevisionResponse(
                id=r.id,
                binding_id=r.binding_id,
                source_revision_id=r.source_revision_id,
                vector_generation_id=r.vector_generation_id,
                revision_no=r.revision_no,
                chunk_count=r.chunk_count,
                fact_count=r.fact_count,
                point_ids=r.point_ids or [],
                parity_report=ParityReportDTO.model_validate(r.parity_report or {}),
                status=r.status,
                failure_code=r.failure_code,
                failure_detail=r.failure_detail,
                is_rollback_available=(
                    r.status in ("archived", "ready")
                    and r.status != "active"
                    and r.status != "pruned"
                    and (r.chunk_count or 0) > 0
                ),
                storage_state="pruned" if r.status == "pruned" else "available",
                created_at=r.created_at,
                finished_at=r.finished_at,
            )
            for r in rows
        ]


index_build_service = IndexBuildService()
