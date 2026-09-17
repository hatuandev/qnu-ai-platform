"""Knowledge Management Service — Orchestrating Document Ingestion Pipeline."""

from __future__ import annotations

import hashlib
import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException, EntityAlreadyExistsError, EntityNotFoundError
from app.core.storage import storage_service
from app.modules.knowledge.chunker import get_chunker
from app.modules.knowledge.cleaner import clean_markdown_text
from app.modules.knowledge.models import (
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeFact,
)
from app.modules.knowledge.parsers import get_document_parser
from app.modules.knowledge.parsers.base import ParsedContent
from app.modules.knowledge.schemas import (
    CollectionCreateRequest,
    ParsePreviewResponse,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service layer managing collections, documents, chunks and fact extraction."""

    # ==========================================================================
    # 1. Collection Management
    # ==========================================================================
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
        return cols

    async def list_documents(
        self, db: AsyncSession, collection_id: str | None = None
    ) -> list[KnowledgeDocument]:
        query = select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
        if collection_id:
            query = query.where(KnowledgeDocument.collection_id == collection_id)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_collection(self, db: AsyncSession, collection_id: str) -> KnowledgeCollection:
        query = select(KnowledgeCollection).where(KnowledgeCollection.id == collection_id)
        res = await db.execute(query)
        col = res.scalar_one_or_none()
        if not col:
            raise EntityNotFoundError(f"Bộ sưu tập '{collection_id}' không tồn tại.")
        return col

    # ==========================================================================
    # 2. Document Ingestion Pipeline
    # ==========================================================================
    @staticmethod
    def compute_file_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    async def _run_ocr_rescue(
        self,
        db: AsyncSession,
        file_bytes: bytes,
        file_name: str,
        ocr_engine: str | None,
    ) -> tuple[str, str, int, bool]:
        """Rescue blank parses (scanned PDFs/images) via OCR auto-routing.

        Returns (markdown_text, engine_used, page_count, rescued). Never raises:
        OCR failure only means the document stays pending for manual handling.
        """
        try:
            from app.modules.ocr.service import OCRService

            ocr_result = await OCRService().extract_document(
                session=db,
                content=file_bytes,
                filename=file_name,
                engine_name=ocr_engine or "auto",
            )
        except Exception as exc:
            logger.warning("OCR rescue failed for file='%s': %s", file_name, exc)
            return "", "none", 0, False
        rescued = bool((ocr_result.raw_text or "").strip())
        return ocr_result.raw_text, ocr_result.engine_used, ocr_result.total_pages, rescued

    async def ingest_document(
        self,
        db: AsyncSession,
        collection_id: str,
        file_bytes: bytes,
        file_name: str,
        title: str | None = None,
        ocr_engine: str | None = None,
    ) -> KnowledgeDocument:
        col = await self.get_collection(db, collection_id)
        file_hash = self.compute_file_hash(file_bytes)
        file_size = len(file_bytes)
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"

        # Check duplicate file (Idempotency)
        dup_query = select(KnowledgeDocument).where(
            KnowledgeDocument.collection_id == collection_id,
            KnowledgeDocument.file_hash == file_hash,
            KnowledgeDocument.is_active.is_(True),
        )
        existing = (await db.execute(dup_query)).scalar_one_or_none()
        if existing:
            raise EntityAlreadyExistsError(
                f"Tệp '{file_name}' đã tồn tại trong kho tri thức này.",
                details={"existing_document_id": existing.id},
            )

        # 1. Save original file to storage driver
        storage_rel_path = f"uploads/{collection_id}/{uuid.uuid4().hex[:8]}_{file_name}"
        await storage_service.save(storage_rel_path, file_bytes)

        # 2. Parse document strategy
        parser = get_document_parser(ext)
        parsed = await parser.parse(file_bytes, file_name)
        ocr_method = parser.__class__.__name__
        ocr_fallback = False

        # 2b. Scanned-document rescue: blank text -> OCR auto-routing
        if not (parsed.raw_text or "").strip() and ext in (
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "webp",
            "bmp",
        ):
            ocr_text, ocr_engine_used, ocr_pages, rescued = await self._run_ocr_rescue(
                db, file_bytes, file_name, ocr_engine
            )
            if rescued:
                parsed = ParsedContent(
                    raw_text=ocr_text,
                    page_count=ocr_pages,
                    tables=[],
                    metadata={"ocr_engine": ocr_engine_used},
                )
                ocr_method = ocr_engine_used
                ocr_fallback = True
                logger.info("OCR rescue succeeded for file='%s' via %s", file_name, ocr_method)

        # 3. Clean and normalize text
        cleaned_text = clean_markdown_text(parsed.raw_text)

        # 4. Chunking strategy (Clause-based for regulations, Semantic for others)
        chunk_strategy = "clause" if col.module_code == "regulations" else "semantic"
        chunker = get_chunker(chunk_strategy)
        chunk_drafts = chunker.chunk(cleaned_text)

        # 5. Persist Document entity (pending review -> approve indexes to Qdrant)
        doc = KnowledgeDocument(
            collection_id=collection_id,
            title=title or file_name.rsplit(".", 1)[0],
            file_name=file_name,
            file_type=ext,
            file_size_bytes=file_size,
            file_hash=file_hash,
            storage_path=storage_rel_path,
            doc_metadata={
                "page_count": parsed.page_count,
                "table_count": len(parsed.tables),
                "chunk_count": len(chunk_drafts),
                "parser": parser.__class__.__name__,
                "ocr_method": ocr_method,
                "ocr_fallback": ocr_fallback,
            },
            status="pending",
            is_active=True,
        )
        db.add(doc)
        await db.flush()  # populate doc.id

        # 6. Persist Chunks
        for draft in chunk_drafts:
            chunk = KnowledgeChunk(
                document_id=doc.id,
                collection_id=collection_id,
                chunk_index=draft.index,
                content=draft.content,
                chunk_hash=draft.chunk_hash,
                token_count=draft.token_count,
                section=draft.section,
                page_number=draft.page_number,
                chunk_metadata=draft.metadata,
            )
            db.add(chunk)

        # 7. Extract structured facts from tables
        for tab in parsed.tables:
            if len(tab.headers) >= 2:
                # Store table metadata as structured fact
                fact = KnowledgeFact(
                    collection_id=collection_id,
                    document_id=doc.id,
                    entity_name=tab.headers[0],
                    entity_type="table",
                    attribute_name="headers",
                    attribute_value=", ".join(tab.headers),
                    confidence=1.0,
                    raw_data={"rows_sample": tab.rows[:5]},
                )
                db.add(fact)

        await db.commit()
        await db.refresh(doc)
        logger.info("Ingested document id=%s, chunks=%d", doc.id, len(chunk_drafts))
        return doc

    async def parse_preview(
        self,
        file_bytes: bytes,
        file_name: str,
        strategy: str = "semantic",
        db: AsyncSession | None = None,
        ocr_engine: str | None = None,
    ) -> ParsePreviewResponse:
        """Parse preview without persisting to database."""
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"
        parser = get_document_parser(ext)
        parsed = await parser.parse(file_bytes, file_name)
        ocr_method = parser.__class__.__name__

        if (
            db is not None
            and not (parsed.raw_text or "").strip()
            and ext in ("pdf", "png", "jpg", "jpeg", "webp", "bmp")
        ):
            ocr_text, ocr_engine_used, ocr_pages, rescued = await self._run_ocr_rescue(
                db, file_bytes, file_name, ocr_engine
            )
            if rescued:
                parsed = ParsedContent(
                    raw_text=ocr_text,
                    page_count=ocr_pages,
                    tables=[],
                    metadata={"ocr_engine": ocr_engine_used},
                )
                ocr_method = ocr_engine_used
        cleaned_text = clean_markdown_text(parsed.raw_text)

        chunker = get_chunker(strategy)
        chunk_drafts = chunker.chunk(cleaned_text)

        preview_chunks = [
            {
                "index": c.index,
                "token_count": c.token_count,
                "section": c.section,
                "preview": c.content[:300] + "..." if len(c.content) > 300 else c.content,
            }
            for c in chunk_drafts[:10]  # preview first 10 chunks
        ]

        total_tokens = sum(c.token_count for c in chunk_drafts)

        return ParsePreviewResponse(
            file_name=file_name,
            file_type=ext,
            file_size_bytes=len(file_bytes),
            raw_markdown=cleaned_text[:4000],
            chunk_count=len(chunk_drafts),
            estimated_tokens=total_tokens,
            extracted_tables_count=len(parsed.tables),
            preview_chunks=preview_chunks,
            ocr_method=ocr_method,
        )

    # ==========================================================================
    # 3. Document Lifecycle & Retrieval Queries
    # ==========================================================================
    async def get_document(self, db: AsyncSession, document_id: str) -> KnowledgeDocument:
        query = (
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.chunks))
            .where(KnowledgeDocument.id == document_id)
        )
        res = await db.execute(query)
        doc = res.scalar_one_or_none()
        if not doc:
            raise EntityNotFoundError(f"Tài liệu '{document_id}' không tồn tại.")
        return doc

    async def archive_document(self, db: AsyncSession, document_id: str) -> KnowledgeDocument:
        doc = await self.get_document(db, document_id)
        doc.is_active = False
        doc.status = "archived"
        await db.commit()
        await db.refresh(doc)
        logger.info("Archived document id=%s", doc.id)
        return doc

    async def delete_document(self, db: AsyncSession, document_id: str) -> None:
        doc = await self.get_document(db, document_id)
        # Delete from storage driver
        await storage_service.delete(doc.storage_path)
        await db.delete(doc)
        await db.commit()
        logger.info("Permanently deleted document id=%s", document_id)

    async def approve_document(
        self,
        db: AsyncSession,
        document_id: str,
        pages: list[dict] | None = None,
    ) -> dict:
        """Approve a pending document and index its chunks to Qdrant.

        When ``pages`` (human-verified per-page markdown) is provided, existing
        chunks are replaced by re-chunked edited pages first. Returns summary
        with the number of chunks actually indexed to the vector store.
        """
        from app.modules.rag.vector_indexer import vector_indexer

        doc = await self.get_document(db, document_id)
        if not doc.is_active or doc.status == "archived":
            raise AppException(
                f"Tài liệu '{document_id}' đã lưu trữ, không thể phê duyệt.",
                code="document_archived",
                status_code=409,
            )

        if pages:
            await db.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
            )
            await db.flush()
            col = await self.get_collection(db, doc.collection_id)
            chunk_strategy = "clause" if col.module_code == "regulations" else "semantic"
            chunker = get_chunker(chunk_strategy)
            chunk_index = 0
            for page in pages:
                page_number = int(page.get("page_number", 1))
                cleaned = clean_markdown_text(str(page.get("markdown_content", "")))
                if not cleaned:
                    continue
                for draft in chunker.chunk(cleaned):
                    db.add(
                        KnowledgeChunk(
                            document_id=doc.id,
                            collection_id=doc.collection_id,
                            chunk_index=chunk_index,
                            content=draft.content,
                            chunk_hash=draft.chunk_hash,
                            token_count=draft.token_count,
                            section=draft.section,
                            page_number=page_number,
                            chunk_metadata={**(draft.metadata or {}), "human_verified": True},
                        )
                    )
                    chunk_index += 1
            metadata = dict(doc.doc_metadata or {})
            metadata["human_verified"] = True
            doc.doc_metadata = metadata

        doc.status = "approved"
        await db.commit()
        await db.refresh(doc)

        chunks = list(
            (
                await db.execute(
                    select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
                )
            )
            .scalars()
            .all()
        )
        indexed = await vector_indexer.index_chunks(
            collection_id=doc.collection_id,
            chunks=[
                {
                    "id": c.id,
                    "point_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.collection_id}:{c.id}")),
                    "content": c.content,
                    "document_id": c.document_id,
                    "section": c.section,
                    "page_number": c.page_number,
                    "metadata": c.chunk_metadata or {},
                }
                for c in chunks
            ],
        )
        metadata = dict(doc.doc_metadata or {})
        metadata["indexed_chunks"] = indexed
        doc.doc_metadata = metadata
        await db.commit()

        logger.info("Approved document id=%s, chunks=%d, indexed=%d", doc.id, len(chunks), indexed)
        return {
            "document_id": doc.id,
            "status": doc.status,
            "total_chunks": len(chunks),
            "indexed_chunks": indexed,
        }


knowledge_service = KnowledgeService()
