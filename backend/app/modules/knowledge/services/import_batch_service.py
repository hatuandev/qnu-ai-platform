"""Service for managing snapshot import batches into KnowledgeCollection.

Implements ADR-012 batch import lifecycle:
- Snapshot provenance preservation (zero foreign key cascade).
- Idempotency with Idempotency-Key and request hash.
- Per-item phase tracking (snapshot, parse, normalize, validate, chunk, facts, embed, parity, publish).
- Retry and cancellation capabilities.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.modules.documents.models import (
    DocumentGroupMembership,
    RepositoryDocument,
)
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import enqueue_arq_job
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeImportBatch,
    KnowledgeImportItem,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import KnowledgeImportBatchCreateRequest


class ImportBatchService:
    """Manages snapshot import batches and item lifecycle."""

    async def create_import_batch(
        self,
        collection_id: str,
        payload: KnowledgeImportBatchCreateRequest,
        idempotency_key: str | None = None,
        created_by: str | None = None,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        db: AsyncSession | None = None,
    ) -> KnowledgeImportBatch:
        """Create a new snapshot import batch with items for each requested document."""
        assert db is not None, "Database session is required"

        # 1. Validate collection
        coll_res = await db.execute(
            select(KnowledgeCollection).where(
                KnowledgeCollection.id == collection_id,
                KnowledgeCollection.tenant_id == tenant_id,
                KnowledgeCollection.workspace_id == workspace_id,
            ).with_for_update()
        )
        coll = coll_res.scalar_one_or_none()
        if not coll:
            raise AppException(
                status_code=404,
                code="COLLECTION_NOT_FOUND",
                detail=f"Không tìm thấy kho tri thức {collection_id}",
            )

        request_hash = hashlib.sha256(json.dumps({
            **payload.model_dump(mode="json"),
            "document_ids": sorted(set(payload.document_ids)),
        }, sort_keys=True).encode("utf-8")).hexdigest()

        # 2. Check Idempotency-Key
        if idempotency_key:
            existing_res = await db.execute(
                select(KnowledgeImportBatch)
                .options(selectinload(KnowledgeImportBatch.items))
                .where(
                    KnowledgeImportBatch.collection_id == collection_id,
                    KnowledgeImportBatch.idempotency_key == idempotency_key,
                )
            )
            existing_batch = existing_res.scalar_one_or_none()
            if existing_batch:
                if existing_batch.request_hash != request_hash:
                    raise AppException("Idempotency-Key đã dùng cho yêu cầu khác.", code="IDEMPOTENCY_CONFLICT", status_code=409)
                return existing_batch

        # 3. Validate documents in workspace
        unique_doc_ids = list(dict.fromkeys(payload.document_ids))
        deleting = await db.scalar(select(KnowledgeBinding.id).where(
            KnowledgeBinding.collection_id == collection_id,
            KnowledgeBinding.repository_document_id.in_(unique_doc_ids),
            KnowledgeBinding.status == "deleting",
        ).limit(1))
        if deleting:
            raise AppException("Nguồn đang xóa vĩnh viễn; chờ hoàn tất rồi nạp lại.",
                               code="SOURCE_DELETING", status_code=409)
        docs_res = await db.execute(
            select(RepositoryDocument).where(
                RepositoryDocument.id.in_(unique_doc_ids),
                RepositoryDocument.tenant_id == tenant_id,
                RepositoryDocument.workspace_id == workspace_id,
                RepositoryDocument.is_active.is_(True),
            )
        )
        valid_docs = docs_res.scalars().all()
        if not valid_docs:
            raise AppException(
                status_code=400,
                code="NO_VALID_DOCUMENTS_FOUND",
                detail="Không tìm thấy tài liệu hợp lệ nào trong kho tài liệu để nạp",
            )

        # 4. Resolve target vector generation
        effective_gen_id = payload.vector_generation_id
        if effective_gen_id:
            gen_res = await db.execute(
                select(KnowledgeVectorGeneration).where(
                    KnowledgeVectorGeneration.id == effective_gen_id,
                    KnowledgeVectorGeneration.collection_id == collection_id,
                )
            )
            if not gen_res.scalar_one_or_none():
                raise AppException(
                    status_code=400,
                    code="INVALID_VECTOR_GENERATION",
                    detail=f"Thế hệ vector {effective_gen_id} không tồn tại trong kho tri thức",
                )
        else:
            active_gen_res = await db.execute(
                select(KnowledgeVectorGeneration)
                .where(
                    KnowledgeVectorGeneration.collection_id == collection_id,
                    KnowledgeVectorGeneration.status.in_(["active", "ready", "building"]),
                )
                .order_by(
                    KnowledgeVectorGeneration.status == "active",
                    KnowledgeVectorGeneration.created_at.desc(),
                )
            )
            active_gen = active_gen_res.scalars().first()
            if active_gen:
                effective_gen_id = active_gen.id

        # 6. Lookup primary group for each doc
        memberships_res = await db.execute(
            select(
                DocumentGroupMembership.document_id,
                DocumentGroupMembership.group_id,
            ).where(DocumentGroupMembership.document_id.in_([d.id for d in valid_docs]))
        )
        primary_group_map: dict[str, str] = {}
        for d_id, g_id in memberships_res.all():
            if d_id not in primary_group_map:
                primary_group_map[d_id] = str(g_id)

        # 7. Create batch entity
        batch_id = f"imp_batch_{uuid.uuid4().hex[:12]}"
        batch = KnowledgeImportBatch(
            id=batch_id,
            collection_id=collection_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            vector_generation_id=effective_gen_id,
            parser_profile=payload.parser_profile,
            chunk_strategy=payload.chunk_strategy,
            chunk_config=payload.chunk_config or {},
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            total_count=len(valid_docs),
            queued_count=len(valid_docs),
            processing_count=0,
            review_required_count=0,
            succeeded_count=0,
            failed_count=0,
            skipped_count=0,
            status="queued",
            created_by=created_by,
        )
        db.add(batch)

        # 8. Create individual import items
        items: list[KnowledgeImportItem] = []
        for doc in valid_docs:
            origin_metadata: dict[str, Any] = {
                "_storage_path": doc.storage_path,
                "document_type_code": doc.document_type_code,
                "document_number": doc.document_number,
                "issuing_authority": doc.issuing_authority,
                "issued_date": str(doc.issued_date) if doc.issued_date else None,
            }
            item = KnowledgeImportItem(
                id=f"imp_item_{uuid.uuid4().hex[:12]}",
                batch_id=batch_id,
                origin_document_id=doc.id,
                origin_group_id=primary_group_map.get(doc.id),
                origin_file_revision_id=None,
                origin_file_hash=doc.file_hash,
                origin_title=doc.title,
                origin_file_name=doc.file_name,
                origin_file_type=doc.file_type,
                origin_metadata=origin_metadata,
                phase="snapshot",
                status="queued",
            )
            items.append(item)
            db.add(item)

        batch.items = items
        jobs = self._create_jobs(db, batch, items)
        await db.commit()
        await self._dispatch_jobs(db, jobs)

        return batch

    @staticmethod
    def _create_jobs(db: AsyncSession, batch: KnowledgeImportBatch, items: list[KnowledgeImportItem]) -> list[JobRecord]:
        jobs = [
            JobRecord(
                job_type="knowledge_source_ingestion", status="queued",
                collection_id=batch.collection_id,
                tenant_id=batch.tenant_id, workspace_id=batch.workspace_id,
                document_id=item.origin_document_id,
                idempotency_key=f"ingest_{item.id}_{item.retry_count}",
                payload={"item_id": item.id, "batch_id": batch.id},
                dispatch_status="pending",
            ) for item in items
        ]
        for job in jobs:
            db.add(job)
        return jobs

    @staticmethod
    async def _dispatch_jobs(db: AsyncSession, jobs: list[JobRecord]) -> None:
        for job in jobs:
            arq_id = await enqueue_arq_job(
                "task_knowledge_source_ingestion", job.id, broker_job_id=f"knowledge_ingest_{job.id}",
            )
            if arq_id:
                job.arq_job_id = arq_id
                job.dispatch_status = "dispatched"
        await db.commit()

    async def get_import_batch(
        self,
        collection_id: str,
        batch_id: str,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        db: AsyncSession | None = None,
    ) -> KnowledgeImportBatch:
        """Fetch import batch details including all items."""
        assert db is not None, "Database session is required"

        res = await db.execute(
            select(KnowledgeImportBatch)
            .options(
                selectinload(KnowledgeImportBatch.items),
            )
            .where(
                KnowledgeImportBatch.id == batch_id,
                KnowledgeImportBatch.collection_id == collection_id,
                KnowledgeImportBatch.tenant_id == tenant_id,
                KnowledgeImportBatch.workspace_id == workspace_id,
            )
        )
        batch = res.scalar_one_or_none()
        if not batch:
            raise AppException(
                status_code=404,
                code="IMPORT_BATCH_NOT_FOUND",
                detail=f"Không tìm thấy đợt nạp tài liệu {batch_id}",
            )
        return batch

    async def retry_failed_items(
        self,
        collection_id: str,
        batch_id: str,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        db: AsyncSession | None = None,
    ) -> KnowledgeImportBatch:
        """Reset failed items in a batch to queued for reprocessing."""
        batch = await self.get_import_batch(
            collection_id=collection_id,
            batch_id=batch_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            db=db,
        )

        failed_items = [it for it in batch.items if it.status == "failed"]
        if not failed_items:
            return batch

        for it in failed_items:
            it.status = "queued"
            it.phase = "snapshot"
            it.failure_code = None
            it.failure_detail = None
            it.retry_count += 1

        batch.failed_count = max(0, batch.failed_count - len(failed_items))
        batch.queued_count += len(failed_items)
        if batch.status in ("failed", "partial_failed", "completed"):
            batch.status = "queued"

        assert db is not None
        jobs = self._create_jobs(db, batch, failed_items)
        await db.commit()
        await self._dispatch_jobs(db, jobs)

        return batch

    async def cancel_import_batch(
        self,
        collection_id: str,
        batch_id: str,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        db: AsyncSession | None = None,
    ) -> KnowledgeImportBatch:
        """Cancel a queued or processing batch."""
        batch = await self.get_import_batch(
            collection_id=collection_id,
            batch_id=batch_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            db=db,
        )

        cancelled_count = 0
        for it in batch.items:
            if it.status in ("queued", "processing"):
                it.status = "skipped"
                it.failure_code = "BATCH_CANCELLED"
                cancelled_count += 1

        batch.status = "cancelled"
        batch.queued_count = sum(it.status == "queued" for it in batch.items)
        batch.processing_count = sum(it.status == "processing" for it in batch.items)
        batch.skipped_count = sum(it.status == "skipped" for it in batch.items)

        assert db is not None
        await db.commit()
        await db.refresh(batch)
        return batch


import_batch_service = ImportBatchService()
