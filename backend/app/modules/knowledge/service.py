"""Knowledge Management Service — Orchestrating Document Ingestion Pipeline.

This module acts as a unified Facade aggregating sub-services:
- collection_service: Collection CRUD, stats, and cascade deletion
- ingestion_service: Ingestion pipeline, OCR rescue, studio views, approve, reprocess
- facts_service: Excel/CSV parsing and structured facts management
- reconciliation_service: 4-layer parity audit (DB, Qdrant, Storage, Redis) and recovery
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import storage_service
from app.modules.knowledge.models import KnowledgeCollection, KnowledgeDocument
from app.modules.knowledge.schemas import (
    AttachDocumentGroupRequest,
    CanaryPolicyResponse,
    CollectionCreateRequest,
    CollectionUpdateRequest,
    FactExcelImportResponse,
    FactListResponse,
    ParsePreviewResponse,
    PreviewDocumentGroupRequest,
    UpdateCanaryPolicyRequest,
)
from app.modules.knowledge.services.binding_service import (
    BindingService,
)
from app.modules.knowledge.services.binding_service import (
    binding_service as default_binding_service,
)
from app.modules.knowledge.services.canary_service import (
    CanaryService,
)
from app.modules.knowledge.services.canary_service import (
    canary_service as default_canary_service,
)
from app.modules.knowledge.services.collection_service import (
    CollectionService,
)
from app.modules.knowledge.services.collection_service import (
    collection_service as default_collection_service,
)
from app.modules.knowledge.services.facts_service import (
    FactsService,
)
from app.modules.knowledge.services.facts_service import (
    facts_service as default_facts_service,
)
from app.modules.knowledge.services.gc_service import (
    KnowledgeArtifactGCService,
)
from app.modules.knowledge.services.gc_service import (
    gc_service as default_gc_service,
)
from app.modules.knowledge.services.index_build_service import (
    IndexBuildService,
)
from app.modules.knowledge.services.index_build_service import (
    index_build_service as default_index_build_service,
)
from app.modules.knowledge.services.ingestion_service import (
    IngestionService,
)
from app.modules.knowledge.services.ingestion_service import (
    ingestion_service as default_ingestion_service,
)
from app.modules.knowledge.services.reconciliation_service import (
    ReconciliationService,
)
from app.modules.knowledge.services.reconciliation_service import (
    reconciliation_service as default_reconciliation_service,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Unified Facade service for Knowledge Management."""

    def __init__(
        self,
        collection_svc: CollectionService | None = None,
        ingestion_svc: IngestionService | None = None,
        facts_svc: FactsService | None = None,
        reconciliation_svc: ReconciliationService | None = None,
        binding_svc: BindingService | None = None,
        index_build_svc: IndexBuildService | None = None,
        canary_svc: CanaryService | None = None,
        gc_svc: KnowledgeArtifactGCService | None = None,
    ) -> None:
        self._collection = collection_svc or default_collection_service
        self._ingestion = ingestion_svc or default_ingestion_service
        self._facts = facts_svc or default_facts_service
        self._reconciliation = reconciliation_svc or default_reconciliation_service
        self._binding = binding_svc or default_binding_service
        self._index_build = index_build_svc or default_index_build_service
        self._canary = canary_svc or default_canary_service
        self._gc = gc_svc or default_gc_service

        # Link sub-services back to facade to honor test patches & monkeypatching
        self._collection.facade = self
        self._ingestion.facade = self
        self._facts.facade = self
        self._reconciliation.facade = self

    # ==========================================================================
    # 1. Collection Management (Delegated to collection_service)
    # ==========================================================================
    async def create_collection(
        self, db: AsyncSession, req: CollectionCreateRequest, actor: Any | None = None
    ) -> KnowledgeCollection:
        return await self._collection.create_collection(db, req, actor=actor)

    async def list_collections(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> list[KnowledgeCollection]:
        return await self._collection.list_collections(
            db, tenant_id=tenant_id, workspace_id=workspace_id, actor=actor
        )

    async def get_collection(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ) -> KnowledgeCollection:
        return await self._collection.get_collection(db, collection_id, actor=actor)

    async def update_collection(
        self,
        db: AsyncSession,
        collection_id: str,
        req: CollectionUpdateRequest,
        actor: Any | None = None,
    ) -> KnowledgeCollection:
        return await self._collection.update_collection(db, collection_id, req, actor=actor)

    async def delete_collection(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ) -> None:
        await self._collection.delete_collection(db, collection_id, actor=actor)

    # ==========================================================================
    # 2. Document Ingestion & Studio Views (Delegated to ingestion_service)
    # ==========================================================================
    @staticmethod
    def compute_file_hash(data: bytes) -> str:
        return IngestionService.compute_file_hash(data)

    async def ingest_document(
        self,
        db: AsyncSession,
        collection_id: str,
        file_bytes: bytes,
        file_name: str,
        title: str | None = None,
        ocr_engine: str | None = None,
        document_type_code: str | None = None,
        auto_approve: bool = False,
    ) -> KnowledgeDocument:
        return await self._ingestion.ingest_document(
            db=db,
            collection_id=collection_id,
            file_bytes=file_bytes,
            file_name=file_name,
            title=title,
            ocr_engine=ocr_engine,
            document_type_code=document_type_code,
            auto_approve=auto_approve,
        )

    async def attach_repository_documents(
        self,
        db: AsyncSession,
        collection_id: str,
        document_ids: list[str],
        chunk_strategy: str | None = None,
        auto_approve: bool = True,
    ) -> list[KnowledgeDocument]:
        return await self._ingestion.attach_repository_documents(
            db=db,
            collection_id=collection_id,
            document_ids=document_ids,
            chunk_strategy=chunk_strategy,
            auto_approve=auto_approve,
        )

    async def parse_preview(
        self,
        file_bytes: bytes,
        file_name: str,
        strategy: str = "semantic",
        db: AsyncSession | None = None,
        ocr_engine: str | None = None,
    ) -> ParsePreviewResponse:
        return await self._ingestion.parse_preview(
            file_bytes=file_bytes,
            file_name=file_name,
            strategy=strategy,
            db=db,
            ocr_engine=ocr_engine,
        )

    async def get_document(self, db: AsyncSession, document_id: str) -> KnowledgeDocument:
        return await self._ingestion.get_document(db, document_id)

    async def list_documents(
        self,
        db: AsyncSession,
        collection_id: str | None = None,
        document_type_code: str | None = None,
    ) -> list[KnowledgeDocument]:
        return await self._ingestion.list_documents(db, collection_id, document_type_code)

    async def archive_document(self, db: AsyncSession, document_id: str) -> KnowledgeDocument:
        return await self._ingestion.archive_document(db, document_id)

    async def delete_document(self, db: AsyncSession, document_id: str) -> None:
        await self._ingestion.delete_document(db, document_id)

    async def get_studio_view(
        self, db: AsyncSession, document_id: str, refresh_layout: bool = False
    ) -> dict:
        return await self._ingestion.get_studio_view(db, document_id, refresh_layout)

    async def render_page_image(
        self, db: AsyncSession, document_id: str, page_number: int
    ) -> bytes:
        return await self._ingestion.render_page_image(db, document_id, page_number)

    async def get_preview_pdf(self, db: AsyncSession, document_id: str) -> tuple[bytes, str]:
        return await self._ingestion.get_preview_pdf(db, document_id)

    async def _convert_office_to_pdf(self, file_bytes: bytes, file_name: str) -> bytes:
        return await self._ingestion._convert_office_to_pdf(file_bytes, file_name)

    async def approve_document(
        self,
        db: AsyncSession,
        document_id: str,
        pages: list[dict] | None = None,
    ) -> dict:
        return await self._ingestion.approve_document(db, document_id, pages)

    async def batch_approve_documents(
        self,
        db: AsyncSession,
        document_ids: list[str],
    ) -> dict:
        return await self._ingestion.batch_approve_documents(db, document_ids)

    async def download_document(self, db: AsyncSession, document_id: str) -> tuple[bytes, str, str]:
        return await self._ingestion.download_document(db, document_id)

    async def sync_ingestion_job_records(self, db: AsyncSession) -> int:
        return await self._ingestion.sync_ingestion_job_records(db)

    def build_studio_pages(
        self,
        chunks: list[dict],
        page_blocks: dict,
        document_id: str,
        page_markdowns: dict[int, str] | None = None,
        page_dimensions: dict[int, dict] | None = None,
    ) -> list[dict]:
        return self._ingestion.build_studio_pages(
            chunks, page_blocks, document_id, page_markdowns, page_dimensions
        )

    async def prepare_ingestion(
        self,
        db: AsyncSession,
        module_code: str,
        file_bytes: bytes,
        file_name: str,
        ocr_engine: str | None = None,
        collection_id: str | None = None,
    ) -> dict:
        return await self._ingestion.prepare_ingestion(
            db, module_code, file_bytes, file_name, ocr_engine, collection_id=collection_id
        )

    async def replace_document_content(
        self,
        db: AsyncSession,
        doc: KnowledgeDocument,
        collection_id: str,
        module_code: str,
        prepared: dict,
    ) -> int:
        return await self._ingestion.replace_document_content(
            db, doc, collection_id, module_code, prepared
        )

    # ==========================================================================
    # 3. Structured Facts Management (Delegated to facts_service)
    # ==========================================================================
    async def import_facts_from_excel(
        self,
        db: AsyncSession,
        collection_id: str,
        file_bytes: bytes,
        filename: str,
    ) -> FactExcelImportResponse:
        return await self._facts.import_facts_from_excel(db, collection_id, file_bytes, filename)

    async def get_collection_facts(
        self,
        db: AsyncSession,
        collection_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> FactListResponse:
        return await self._facts.get_collection_facts(db, collection_id, limit, offset)

    # ==========================================================================
    # 4. Reconciliation & Indexing Audit (Delegated to reconciliation_service)
    # ==========================================================================
    async def reindex_document(self, db: AsyncSession, document_id: str) -> dict[str, Any]:
        return await self._reconciliation.reindex_document(db, document_id)

    async def reconcile_collection(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ) -> dict[str, Any]:
        return await self._reconciliation.reconcile_collection(db, collection_id, actor=actor)

    async def reconcile_fix_collection(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ) -> dict[str, Any]:
        return await self._reconciliation.reconcile_fix_collection(db, collection_id, actor=actor)

    # ==========================================================================
    # 5. Knowledge Binding Management (Delegated to binding_service)
    # ==========================================================================
    async def get_available_documents(
        self,
        db: AsyncSession,
        collection_id: str,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        actor: Any | None = None,
    ):
        return await self._binding.get_available_documents(
            db,
            collection_id,
            search=search,
            page=page,
            page_size=page_size,
            actor=actor,
        )

    async def create_bindings(
        self,
        db: AsyncSession,
        collection_id: str,
        req,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ):
        return await self._binding.create_bindings(
            db,
            collection_id,
            req,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            actor=actor,
        )

    async def preview_document_group(
        self,
        db: AsyncSession,
        collection_id: str,
        req: PreviewDocumentGroupRequest,
        actor: Any | None = None,
    ):
        return await self._binding.preview_document_group(
            db=db,
            collection_id=collection_id,
            req=req,
            actor=actor,
        )

    async def attach_document_group(
        self,
        db: AsyncSession,
        collection_id: str,
        req: AttachDocumentGroupRequest,
        actor: Any | None = None,
    ):
        return await self._binding.attach_document_group(
            db=db,
            collection_id=collection_id,
            req=req,
            actor=actor,
        )

    async def list_bindings(
        self,
        db: AsyncSession,
        collection_id: str,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        actor: Any | None = None,
    ):
        return await self._binding.list_bindings(
            db,
            collection_id,
            status=status,
            page=page,
            page_size=page_size,
            actor=actor,
        )

    async def get_binding(self, db: AsyncSession, binding_id: str, actor: Any | None = None):
        return await self._binding.get_binding(db, binding_id, actor=actor)

    async def detach_binding(self, db: AsyncSession, binding_id: str, actor: Any | None = None):
        return await self._binding.detach_binding(db, binding_id, actor=actor)

    async def list_binding_chunks(
        self,
        db: AsyncSession,
        binding_id: str,
        index_revision_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
        actor: Any | None = None,
    ):
        return await self._binding.list_binding_chunks(
            db,
            binding_id=binding_id,
            index_revision_id=index_revision_id,
            page=page,
            page_size=page_size,
            actor=actor,
        )

    # ==========================================================================
    # 6. Staging Index Build & Atomic Activation (Delegated to index_build_service)
    # ==========================================================================
    async def build_staging_index(
        self,
        db: AsyncSession,
        binding_id: str,
        source_revision_id: str | None = None,
        chunk_strategy: str | None = None,
        auto_activate: bool = False,
        actor: Any | None = None,
        job_id: str | None = None,
    ):
        return await self._index_build.build_staging_index(
            db,
            binding_id=binding_id,
            source_revision_id=source_revision_id,
            chunk_strategy=chunk_strategy,
            auto_activate=auto_activate,
            actor=actor,
            job_id=job_id,
        )

    async def promote_index_revision(
        self,
        db: AsyncSession,
        binding_id: str,
        index_revision_id: str,
        expected_epoch: int,
        reason: str | None = None,
        activated_by: str | None = None,
        actor: Any | None = None,
    ):
        return await self._index_build.promote_index_revision(
            db,
            binding_id=binding_id,
            index_revision_id=index_revision_id,
            expected_epoch=expected_epoch,
            reason=reason,
            activated_by=activated_by,
            actor=actor,
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
    ):
        return await self._index_build.rollback_index_revision(
            db,
            binding_id=binding_id,
            target_index_revision_id=target_index_revision_id,
            expected_epoch=expected_epoch,
            reason=reason,
            activated_by=activated_by,
            actor=actor,
        )

    async def list_index_revisions(
        self, db: AsyncSession, binding_id: str, actor: Any | None = None
    ):
        return await self._index_build.list_index_revisions(
            db, binding_id=binding_id, actor=actor
        )

    # ==========================================================================
    # 7. Legacy Canary, Backfill & Shadow Retrieval (Delegated to canary_service)
    # ==========================================================================
    async def audit_collection_legacy_state(
        self, db: AsyncSession, collection_id: str, actor: Any | None = None
    ):
        return await self._canary.audit_collection_legacy_state(
            db, collection_id, actor=actor
        )

    async def backfill_legacy_collection(
        self,
        db: AsyncSession,
        collection_id: str,
        actor_id: str | None = None,
        force_rebuild: bool = False,
        default_chunk_strategy: str = "ClauseBasedChunker",
        actor: Any | None = None,
    ):
        return await self._canary.backfill_legacy_collection(
            db,
            collection_id=collection_id,
            actor_id=actor_id,
            force_rebuild=force_rebuild,
            default_chunk_strategy=default_chunk_strategy,
            actor=actor,
        )

    async def run_shadow_retrieval_comparison(
        self,
        db: AsyncSession,
        collection_id: str,
        query: str,
        top_k: int = 5,
        actor: Any | None = None,
    ):
        return await self._canary.run_shadow_retrieval_comparison(
            db,
            collection_id=collection_id,
            query=query,
            top_k=top_k,
            actor=actor,
        )

    async def get_collection_canary_policy(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> CanaryPolicyResponse:
        return await self._canary.get_collection_canary_policy(
            db, collection_id=collection_id, actor=actor
        )

    async def update_collection_canary_policy(
        self,
        db: AsyncSession,
        collection_id: str,
        req: UpdateCanaryPolicyRequest,
        actor: Any | None = None,
    ) -> CanaryPolicyResponse:
        return await self._canary.update_collection_canary_policy(
            db, collection_id=collection_id, req=req, actor=actor
        )

    # ==========================================================================
    # 8. Artifact Garbage Collection (Delegated to gc_service)
    # ==========================================================================
    async def collect_garbage(
        self,
        db: AsyncSession,
        collection_id: str,
        keep_revisions: int = 2,
        dry_run: bool = False,
        actor: Any | None = None,
    ):
        return await self._gc.collect_garbage(
            db,
            collection_id=collection_id,
            keep_revisions=keep_revisions,
            dry_run=dry_run,
            actor=actor,
        )

    async def collect_garbage_system_wide(
        self,
        db: AsyncSession,
        default_keep_revisions: int = 2,
        dry_run: bool = False,
        actor: Any | None = None,
    ):
        return await self._gc.collect_garbage_system_wide(
            db,
            default_keep_revisions=default_keep_revisions,
            dry_run=dry_run,
            actor=actor,
        )

    async def audit_system_decommissioning(
        self,
        db: AsyncSession,
        actor: Any | None = None,
    ):
        return await self._gc.audit_system_decommissioning(db, actor=actor)


knowledge_service = KnowledgeService()

__all__ = [
    "KnowledgeService",
    "knowledge_service",
    "storage_service",
]
