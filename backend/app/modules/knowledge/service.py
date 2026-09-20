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
    CollectionCreateRequest,
    CollectionUpdateRequest,
    FactExcelImportResponse,
    FactListResponse,
    ParsePreviewResponse,
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
    ) -> None:
        self._collection = collection_svc or default_collection_service
        self._ingestion = ingestion_svc or default_ingestion_service
        self._facts = facts_svc or default_facts_service
        self._reconciliation = reconciliation_svc or default_reconciliation_service

        # Link sub-services back to facade to honor test patches & monkeypatching
        self._collection.facade = self
        self._ingestion.facade = self
        self._facts.facade = self
        self._reconciliation.facade = self

    # ==========================================================================
    # 1. Collection Management (Delegated to collection_service)
    # ==========================================================================
    async def create_collection(
        self, db: AsyncSession, req: CollectionCreateRequest
    ) -> KnowledgeCollection:
        return await self._collection.create_collection(db, req)

    async def list_collections(
        self, db: AsyncSession, tenant_id: str = "tenant_qnu", workspace_id: str = "workspace_qnu"
    ) -> list[KnowledgeCollection]:
        return await self._collection.list_collections(db, tenant_id, workspace_id)

    async def get_collection(self, db: AsyncSession, collection_id: str) -> KnowledgeCollection:
        return await self._collection.get_collection(db, collection_id)

    async def update_collection(
        self, db: AsyncSession, collection_id: str, req: CollectionUpdateRequest
    ) -> KnowledgeCollection:
        return await self._collection.update_collection(db, collection_id, req)

    async def delete_collection(self, db: AsyncSession, collection_id: str) -> None:
        await self._collection.delete_collection(db, collection_id)

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

    async def get_preview_pdf(
        self, db: AsyncSession, document_id: str
    ) -> tuple[bytes, str]:
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
    ) -> dict:
        return await self._ingestion.prepare_ingestion(db, module_code, file_bytes, file_name, ocr_engine)

    async def replace_document_content(
        self,
        db: AsyncSession,
        doc: KnowledgeDocument,
        collection_id: str,
        module_code: str,
        prepared: dict,
    ) -> int:
        return await self._ingestion.replace_document_content(db, doc, collection_id, module_code, prepared)

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

    async def reconcile_collection(self, db: AsyncSession, collection_id: str) -> dict[str, Any]:
        return await self._reconciliation.reconcile_collection(db, collection_id)

    async def reconcile_fix_collection(self, db: AsyncSession, collection_id: str) -> dict[str, Any]:
        return await self._reconciliation.reconcile_fix_collection(db, collection_id)


knowledge_service = KnowledgeService()

__all__ = [
    "KnowledgeService",
    "knowledge_service",
    "storage_service",
]
