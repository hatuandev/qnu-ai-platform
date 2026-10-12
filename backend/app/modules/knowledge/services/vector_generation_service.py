"""Vector Generation Service — Multi-Vector Generation Lifecycle & Atomic CAS (ADR-012).

Manages multi-vector spaces for Knowledge Collections:
1. Dynamic model resolution from ModelOps DB (zero-env hardcoding).
2. 'Parse Once, Embed Many': Builds new vector spaces directly from materialized ChunkSets.
3. Strict Vector Space Isolation: Vectors with different models/dimensions are never mixed.
4. Parity Gate Verification: Ensures 100% parity between PostgreSQL chunks and Qdrant points.
5. Atomic Pointer Swap (CAS): Atomically activates generations and archives previous generations.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeFact,
    KnowledgeIndexRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import (
    ActivateVectorGenerationResponse,
    BuildVectorGenerationResponse,
)
from app.modules.knowledge.services.chunk_set_service import chunk_set_service
from app.modules.knowledge.services.scope_helper import (
    get_scoped_collection,
)
from app.modules.modelops.services.model_catalog_service import model_catalog_service
from app.modules.rag.vector_indexer import vector_indexer

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


class VectorGenerationService:
    """Service managing multi-vector generations and atomic activations."""

    async def list_vector_generations(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> list[KnowledgeVectorGeneration]:
        """List all vector generations for a collection ordered by epoch descending."""
        await get_scoped_collection(db, collection_id, actor=actor)
        stmt = (
            select(KnowledgeVectorGeneration)
            .where(KnowledgeVectorGeneration.collection_id == collection_id)
            .order_by(KnowledgeVectorGeneration.generation_epoch.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_vector_generation(
        self,
        db: AsyncSession,
        collection_id: str,
        generation_id: str,
        actor: Any | None = None,
    ) -> KnowledgeVectorGeneration:
        """Fetch a specific vector generation with scope validation."""
        await get_scoped_collection(db, collection_id, actor=actor)
        stmt = select(KnowledgeVectorGeneration).where(
            KnowledgeVectorGeneration.id == generation_id,
            KnowledgeVectorGeneration.collection_id == collection_id,
        )
        res = await db.execute(stmt)
        gen = res.scalar_one_or_none()
        if not gen:
            raise AppException(
                message=f"Không tìm thấy thế hệ vector '{generation_id}' trong bộ sưu tập",
                code="VECTOR_GENERATION_NOT_FOUND",
                status_code=404,
            )
        return gen

    async def create_vector_generation(
        self,
        db: AsyncSession,
        collection_id: str,
        model_name: str,
        provider_id: str | None = None,
        dimension: int | None = None,
        actor: Any | None = None,
    ) -> KnowledgeVectorGeneration:
        """Create a new vector generation dynamically resolved from ModelOps DB."""
        col = await get_scoped_collection(db, collection_id, actor=actor, for_update=True)

        # 1. Resolve Provider and Model from ModelOps DB
        catalog = await model_catalog_service.get_system_model_defaults(db)
        defaults = catalog.defaults
        resolved_provider = provider_id or defaults.default_embedding_provider_id
        resolved_model = model_name or defaults.default_embedding_model

        if not resolved_provider or not resolved_model:
            raise AppException(
                message="Chưa cấu hình nhà cung cấp và mô hình embedding trong ModelOps.",
                code="EMBEDDING_MODEL_NOT_CONFIGURED",
                status_code=409,
            )

        resolved_dim = await model_catalog_service.resolve_embedding_dimension(
            db=db,
            provider_id=resolved_provider,
            model_name=resolved_model,
            metadata_dimension=dimension,
        )

        config_hash = hashlib.sha256(
            f"{resolved_provider}:{resolved_model}:{resolved_dim}:cosine:v2".encode()
        ).hexdigest()

        qdrant_col_name = f"{vector_indexer._get_collection_name(col.id)}_{config_hash[:16]}"

        # 2. Check if a generation with identical config already exists
        exist_stmt = select(KnowledgeVectorGeneration).where(
            KnowledgeVectorGeneration.collection_id == col.id,
            KnowledgeVectorGeneration.config_hash == config_hash,
        )
        exist_res = await db.execute(exist_stmt)
        existing_gen = exist_res.scalars().first()
        if existing_gen:
            logger.info("Reusing existing vector generation %s for config %s", existing_gen.id, config_hash)
            return existing_gen

        # 3. Calculate next epoch
        max_epoch_stmt = select(
            func.coalesce(func.max(KnowledgeVectorGeneration.generation_epoch), 0)
        ).where(KnowledgeVectorGeneration.collection_id == col.id)
        next_epoch = int((await db.execute(max_epoch_stmt)).scalar() or 0) + 1

        # Check if this is the first generation
        status = "building"
        gen = KnowledgeVectorGeneration(
            collection_id=col.id,
            embedding_model=resolved_model,
            provider_id=resolved_provider,
            qdrant_collection_name=qdrant_col_name,
            config_hash=config_hash,
            payload_schema_version=2,
            embedding_dimension=resolved_dim,
            distance_metric="cosine",
            generation_epoch=next_epoch,
            status=status,
            tenant_id=col.tenant_id,
            workspace_id=col.workspace_id,
        )
        db.add(gen)
        await db.commit()
        await db.refresh(gen)
        return gen

    async def build_generation_for_source(
        self,
        db: AsyncSession,
        collection_id: str,
        binding_id: str,
        generation_id: str,
        chunk_strategy: str = "ClauseBasedChunker",
        chunk_config: dict[str, Any] | None = None,
        job_id: str | None = None,
        expected_source_revision_id: str | None = None,
    ) -> KnowledgeIndexRevision:
        """Build vector index revision for a source using its materialized ChunkSet.

        Invariant:
        - NEVER calls parser or OCR! Directly reads materialized ChunkSet.
        - Verifies Parity Gate before setting revision to 'ready'.
        """
        # Serialize build reservation against source purge before external I/O.
        col = await get_scoped_collection(db, collection_id, for_update=True)
        # 1. Fetch Binding and Vector Generation
        b_stmt = (
            select(KnowledgeBinding)
            .options(
                selectinload(KnowledgeBinding.active_source_revision),
            )
            .where(
                KnowledgeBinding.id == binding_id,
                KnowledgeBinding.collection_id == collection_id,
            )
            .with_for_update()
        )
        b_res = await db.execute(b_stmt)
        binding = b_res.scalar_one_or_none()
        if not binding:
            raise AppException(
                message=f"Không tìm thấy nguồn tri thức '{binding_id}' trong bộ sưu tập",
                code="SOURCE_NOT_FOUND",
                status_code=404,
            )

        if binding.status == "paused":
            raise AppException("Nguồn đã ngừng dùng.", code="SOURCE_PAUSED", status_code=409)
        if binding.status in ("detached", "deleting"):
            raise AppException("Nguồn đã gỡ hoặc đang xóa.", code="SOURCE_DELETING", status_code=409)
        gen_stmt = select(KnowledgeVectorGeneration).where(
            KnowledgeVectorGeneration.id == generation_id,
            KnowledgeVectorGeneration.collection_id == collection_id,
        )
        gen_res = await db.execute(gen_stmt)
        gen = gen_res.scalar_one_or_none()
        if not gen:
            raise AppException(
                message=f"Không tìm thấy thế hệ vector '{generation_id}' trong bộ sưu tập",
                code="VECTOR_GENERATION_NOT_FOUND",
                status_code=404,
            )

        source_rev = binding.active_source_revision
        if expected_source_revision_id and (not source_rev or source_rev.id != expected_source_revision_id):
            raise AppException(
                "Markdown đã thay đổi; hãy tải lại và nạp đúng bản đã lưu.",
                code="SOURCE_REVISION_CHANGED", status_code=409,
            )
        if not source_rev or source_rev.status != "ready":
            raise AppException(
                message=f"Nguồn tri thức '{binding_id}' chưa có bản sửa đổi sẵn sàng ('ready') để lập chỉ mục vector.",
                code="SOURCE_REVISION_NOT_READY",
                status_code=409,
            )

        # 2. Materialize or retrieve existing ChunkSet (Parse Once, Embed Many)
        chunk_set = await chunk_set_service.get_or_create_chunk_set(
            db=db,
            source_revision_id=source_rev.id,
            chunk_strategy=chunk_strategy,
            chunk_config=chunk_config,
        )

        # 3. Check for existing IndexRevision for this (binding, generation, chunk_set)
        idx_stmt = select(KnowledgeIndexRevision).where(
            KnowledgeIndexRevision.binding_id == binding.id,
            KnowledgeIndexRevision.vector_generation_id == gen.id,
            KnowledgeIndexRevision.chunk_set_id == chunk_set.id,
            KnowledgeIndexRevision.status.in_(["ready", "active"]),
        )
        existing_idx = (await db.execute(idx_stmt)).scalars().first()
        if existing_idx:
            logger.info("Reusing existing index revision %s for generation %s", existing_idx.id, gen.id)
            return existing_idx

        # 4. Prepare Chunks and Payload
        chunks_manifest = chunk_set.chunk_config.get("_manifest", [])
        if not chunks_manifest:
            raise AppException(
                message=f"Tập đoạn cắt '{chunk_set.id}' không có dữ liệu chunks.",
                code="CHUNK_SET_EMPTY",
                status_code=422,
            )

        # Next revision number for binding
        rev_no_stmt = select(func.coalesce(func.max(KnowledgeIndexRevision.revision_no), 0) + 1).where(
            KnowledgeIndexRevision.binding_id == binding.id
        )
        next_rev_no = (await db.execute(rev_no_stmt)).scalar() or 1

        idx_rev = KnowledgeIndexRevision(
            binding_id=binding.id,
            source_revision_id=None,  # Legacy provenance is not a Knowledge source FK
            source_revision_v2_id=source_rev.id,
            chunk_set_id=chunk_set.id,
            vector_generation_id=gen.id,
            revision_no=next_rev_no,
            chunk_count=len(chunks_manifest),
            fact_count=chunk_set.fact_count,
            point_ids=[],
            parity_report={},
            status="building",
            lock_version=1,
        )
        db.add(idx_rev)
        await db.flush()

        # 5. Build Qdrant points payload
        point_ids: list[str] = []
        payload_chunks: list[dict[str, Any]] = []

        for item in chunks_manifest:
            idx = item["index"]
            c_text = item["content"]
            c_hash = item["chunk_hash"]
            c_section = item.get("section")
            c_page = item.get("page_number")

            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{col.id}:{gen.id}:{idx_rev.id}:{idx}"))
            point_ids.append(point_id)

            db.add(KnowledgeChunk(
                id=f"chk_{uuid.UUID(point_id).hex[:12]}",
                document_id=None, collection_id=col.id,
                binding_id=binding.id, index_revision_id=idx_rev.id,
                chunk_index=idx, content=c_text, chunk_hash=c_hash,
                token_count=item.get("token_count", 0),
                section=c_section, page_number=c_page,
                chunk_metadata={
                    "source_revision_id": source_rev.id,
                    "chunk_set_id": chunk_set.id,
                    "title": (source_rev.snapshot_metadata or {}).get("title", binding.id),
                    "document_title": (source_rev.snapshot_metadata or {}).get("title", binding.id),
                    "file_name": (source_rev.snapshot_metadata or {}).get("file_name"),
                    "document_number": (source_rev.citation_metadata or {}).get("document_number"),
                    "chunk_index": idx,
                },
            ))
            payload_chunks.append(
                {
                    "id": f"chk_{uuid.UUID(point_id).hex[:12]}",
                    "point_id": point_id,
                    "content": c_text,
                    "content_hash": c_hash,
                    "collection_id": col.id,
                    "tenant_id": col.tenant_id,
                    "workspace_id": col.workspace_id,
                    "document_id": binding.id,
                    "document_revision": source_rev.revision_no,
                    "document_status": "staging",
                    "is_retrievable": False,
                    "section": c_section,
                    "page_number": c_page,
                    "embedding_model": gen.embedding_model,
                    "index_revision_id": idx_rev.id,
                    "vector_generation_id": gen.id,
                    "metadata": {
                        "document_title": (source_rev.snapshot_metadata or {}).get("title", binding.id),
                        "file_name": (source_rev.snapshot_metadata or {}).get("file_name"),
                        "document_number": (source_rev.citation_metadata or {}).get("document_number"),
                        "chunk_index": idx,
                        "binding_id": binding.id,
                        "source_revision_id": source_rev.id,
                        "chunk_set_id": chunk_set.id,
                        "vector_generation_id": gen.id,
                        "index_revision_id": idx_rev.id,
                        "epoch": gen.generation_epoch,
                    },
                }
            )

        from app.modules.knowledge.services.source_artifact import get_source_artifact

        artifact = get_source_artifact(source_rev)
        facts = [dict(fact) for fact in artifact["facts"]]
        for fact in facts:
            fingerprint = hashlib.sha256(f"{idx_rev.id}:{fact['id']}".encode()).hexdigest()[:24]
            fact["id"] = f"fct_{fingerprint}"
            fact["collection_id"] = col.id
            fact["document_id"] = None
            fact["binding_id"] = binding.id
            fact["index_revision_id"] = idx_rev.id
            fact["raw_data"] = {**fact["raw_data"], "source_revision_id": source_rev.id,
                                "fact_set_hash": artifact["fact_set_hash"]}
            db.add(KnowledgeFact(**fact))
        idx_rev.fact_count = len(facts)
        chunk_set.fact_count = len(facts)
        await db.flush()

        # 6. Index into Qdrant
        try:
            indexed_count = await vector_indexer.index_chunks(
                collection_id=col.id,
                chunks=payload_chunks,
                vector_generation=gen,
            )
        except Exception as exc:
            logger.exception("Failed to index chunks into Qdrant for idx_rev %s", idx_rev.id)
            idx_rev.status = "failed"
            idx_rev.failure_code = "VECTOR_INDEXING_FAILED"
            idx_rev.failure_detail = str(exc)
            idx_rev.finished_at = utcnow()
            await db.commit()
            raise AppException(
                message=f"Lỗi lập chỉ mục vector vào Qdrant: {exc}",
                code="VECTOR_INDEXING_FAILED",
                status_code=502,
            ) from exc

        # 7. Parity Gate Verification
        db_count = len(payload_chunks)
        target_qdrant_col = gen.qdrant_collection_name or col.id
        if indexed_count == db_count:
            parity_passed, parity_reason, verified_count = await vector_indexer.verify_index_revision_parity(
                collection_id=col.id,
                index_revision_id=idx_rev.id,
                expected_points={p["point_id"]: p["content_hash"] for p in payload_chunks},
                qdrant_collection_name=target_qdrant_col,
            )
        else:
            parity_passed = False
            parity_reason = f"Số points ghi nhận ({indexed_count}) không khớp số chunks ({db_count})"
            verified_count = indexed_count

        parity_report = {
            "source_content_hash": source_rev.canonical_hash,
            "fact_set_hash": artifact["fact_set_hash"],
            "parity_passed": parity_passed,
            "parity_reason": parity_reason,
            "verified_count": verified_count,
            "expected_count": db_count,
            "checked_at": utcnow().isoformat(),
        }

        idx_rev.point_ids = point_ids
        idx_rev.parity_report = parity_report
        idx_rev.finished_at = utcnow()

        if not parity_passed:
            idx_rev.status = "failed"
            idx_rev.failure_code = "PARITY_GATE_FAILED"
            idx_rev.failure_detail = parity_reason
            await db.commit()
            raise AppException(
                message=f"Parity Gate thất bại: {parity_reason}",
                code="PARITY_GATE_FAILED",
                status_code=422,
            )

        idx_rev.status = "ready"
        await db.commit()
        await db.refresh(idx_rev)
        return idx_rev

    async def build_all_sources_for_generation(
        self,
        db: AsyncSession,
        collection_id: str,
        generation_id: str,
        chunk_strategy: str | None = None,
        chunk_config: dict[str, Any] | None = None,
        job_id: str | None = None,
        actor: Any | None = None,
    ) -> BuildVectorGenerationResponse:
        """Trigger building vector index revisions for all active sources in a collection."""
        gen = await self.get_vector_generation(db, collection_id, generation_id, actor=actor)
        stmt = (
            select(KnowledgeBinding)
            .where(
                KnowledgeBinding.collection_id == collection_id,
                KnowledgeBinding.status.in_(["active", "pending"]),
            )
        )
        res = await db.execute(stmt)
        bindings = list(res.scalars().all())

        built_count = 0
        reused_count = 0
        failed_count = 0

        strategy = chunk_strategy or "ClauseBasedChunker"
        for b in bindings:
            try:
                build_started_at = utcnow()
                idx_rev = await self.build_generation_for_source(
                    db=db,
                    collection_id=collection_id,
                    binding_id=b.id,
                    generation_id=generation_id,
                    chunk_strategy=strategy,
                    chunk_config=chunk_config,
                    job_id=job_id,
                )
                if idx_rev.created_at < build_started_at:
                    reused_count += 1
                else:
                    built_count += 1
            except Exception as exc:
                logger.error("Failed to build index revision for binding %s: %s", b.id, exc)
                failed_count += 1

        # Check if generation reaches ready status
        if failed_count == 0 and built_count + reused_count > 0:
            if gen.status != "active":
                gen.status = "ready"
            await db.commit()

        return BuildVectorGenerationResponse(
            collection_id=collection_id,
            generation_id=generation_id,
            total_sources=len(bindings),
            built_count=built_count,
            reused_count=reused_count,
            failed_count=failed_count,
            status=gen.status,
        )

    async def activate_vector_generation(
        self, db: AsyncSession, collection_id: str, generation_id: str,
        actor: Any | None = None,
    ) -> ActivateVectorGenerationResponse:
        from app.modules.knowledge.services.generation_publish_service import publish_generation

        return await publish_generation(db, collection_id, generation_id, actor=actor)

    async def rollback_vector_generation(
        self, db: AsyncSession, collection_id: str, target_generation_id: str,
        actor: Any | None = None,
    ) -> ActivateVectorGenerationResponse:
        from app.modules.knowledge.services.generation_publish_service import publish_generation

        return await publish_generation(
            db, collection_id, target_generation_id, actor=actor, rollback=True,
        )


vector_generation_service = VectorGenerationService()
