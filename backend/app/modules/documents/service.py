"""Service Layer for Central Document Repository — MinIO storage, pre-parsing, and metadata management."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFoundError
from app.core.storage import storage_service
from app.modules.documents.models import RepositoryDocument
from app.modules.documents.schemas import (
    AttachedCollectionInfo,
    RepositoryDocumentListItem,
    RepositoryDocumentResponse,
    RepositoryDocumentStatsResponse,
    RepositoryDocumentUpdate,
)
from app.modules.knowledge.cleaner import clean_markdown_text, extract_sections_metadata
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.knowledge.parsers import get_document_parser

logger = logging.getLogger(__name__)


class DocumentRepositoryService:
    """Service managing the centralized document vault on MinIO S3."""

    SUPPORTED_EXTENSIONS = {"pdf", "docx", "doc", "xlsx", "xls", "txt", "md", "csv"}

    @staticmethod
    def compute_file_hash(content: bytes) -> str:
        """Compute SHA-256 digest for deduplication."""
        return hashlib.sha256(content).hexdigest()

    async def upload_document(
        self,
        db: AsyncSession,
        file_bytes: bytes,
        file_name: str,
        title: str | None = None,
        document_type_code: str | None = None,
        document_number: str | None = None,
        issuing_authority: str | None = None,
        issued_date: date | None = None,
        effective_date: date | None = None,
        ocr_engine: str | None = None,
        auto_parse: bool = True,
    ) -> RepositoryDocument:
        """Upload a file to MinIO S3 and register it in the document repository."""
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"
        file_size = len(file_bytes)
        file_hash = self.compute_file_hash(file_bytes)

        # 1. Deduplication check across active repository documents
        stmt = select(RepositoryDocument).where(
            RepositoryDocument.file_hash == file_hash,
            RepositoryDocument.is_active.is_(True),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            logger.info("File '%s' with hash '%s' already exists in repository (%s).", file_name, file_hash, existing.id)
            return existing

        # 2. Persist original file in MinIO S3 under immutable hash path
        safe_name = file_name.replace(" ", "_")
        storage_key = f"documents/originals/{file_hash}/{safe_name}"
        await storage_service.save(storage_key, file_bytes)
        logger.info("Saved %d bytes to MinIO S3: %s", file_size, storage_key)

        # 3. Create database record
        doc_id = f"rep_doc_{uuid.uuid4().hex[:12]}"
        doc = RepositoryDocument(
            id=doc_id,
            title=title or file_name.rsplit(".", 1)[0],
            file_name=file_name,
            file_type=ext,
            file_size_bytes=file_size,
            file_hash=file_hash,
            storage_path=storage_key,
            document_type_code=document_type_code,
            document_number=document_number,
            issuing_authority=issuing_authority,
            issued_date=issued_date,
            effective_date=effective_date,
            parse_status="pending",
            ocr_engine=ocr_engine,
            is_active=True,
            doc_metadata={
                "original_filename": file_name,
                "upload_channel": "repository_vault",
            },
        )
        db.add(doc)
        await db.flush()

        # 4. Trigger pre-parse pipeline if requested
        if auto_parse:
            await self.parse_and_cache_document(
                db=db,
                doc=doc,
                file_bytes=file_bytes,
                ocr_engine=ocr_engine,
            )

        await db.commit()
        await db.refresh(doc)
        return doc

    async def parse_and_cache_document(
        self,
        db: AsyncSession,
        doc: RepositoryDocument,
        file_bytes: bytes | None = None,
        ocr_engine: str | None = None,
    ) -> None:
        """Extract text, tables, and render page images to pre-cache as Markdown."""
        doc.parse_status = "parsing"
        await db.flush()

        try:
            if file_bytes is None:
                file_bytes = await storage_service.get(doc.storage_path)
                if not file_bytes:
                    raise FileNotFoundError(f"Cannot retrieve file bytes from storage: {doc.storage_path}")

            parser = get_document_parser(doc.file_type)
            parsed = await parser.parse(file_bytes, doc.file_name)

            # Clean and normalize Vietnamese Unicode NFC
            clean_md = clean_markdown_text(parsed.raw_text or "")
            sections = extract_sections_metadata(clean_md)

            preview_pages: list[str] = []
            # If PDF, render page images to MinIO for thumbnail & preview
            if doc.file_type == "pdf":
                preview_pages = await self._render_pdf_pages_to_storage(doc.file_hash, file_bytes)

            doc.parsed_markdown = clean_md
            doc.parse_status = "parsed"
            doc.ocr_engine = ocr_engine or "native"
            metadata = dict(doc.doc_metadata or {})
            metadata.update(
                {
                    "page_count": parsed.page_count,
                    "table_count": len(parsed.tables),
                    "preview_pages": preview_pages,
                    "sections_count": len(sections),
                }
            )
            doc.doc_metadata = metadata
            logger.info("Pre-parsed document %s (%s): %d pages, %d tables.", doc.id, doc.file_name, parsed.page_count, len(parsed.tables))
        except Exception as exc:
            logger.exception("Failed to pre-parse document %s (%s)", doc.id, doc.file_name)
            doc.parse_status = "failed"


            metadata = dict(doc.doc_metadata or {})
            metadata["parse_error"] = str(exc)
            doc.doc_metadata = metadata

        await db.flush()

    async def _render_pdf_pages_to_storage(self, file_hash: str, pdf_bytes: bytes) -> list[str]:
        """Render first few pages of PDF to PNG and store in MinIO for preview."""
        preview_keys: list[str] = []
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            max_pages = min(len(doc), 5)  # Render up to first 5 pages for preview
            for page_idx in range(max_pages):
                page = doc.load_page(page_idx)
                pix = page.get_pixmap(dpi=120)
                img_data = pix.tobytes("png")
                key = f"documents/renders/{file_hash}/page_{page_idx + 1}.png"
                await storage_service.save(key, img_data)
                preview_keys.append(key)
            doc.close()
        except Exception as exc:
            logger.warning("Could not render PDF preview images for %s: %s", file_hash, exc)
        return preview_keys

    async def list_documents(
        self,
        db: AsyncSession,
        search: str | None = None,
        document_type_code: str | None = None,
        file_type: str | None = None,
        parse_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RepositoryDocumentListItem], int]:
        """List repository documents with search, filtering, and usage counts."""
        query = select(RepositoryDocument).where(RepositoryDocument.is_active.is_(True))

        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                (RepositoryDocument.title.ilike(term))
                | (RepositoryDocument.file_name.ilike(term))
                | (RepositoryDocument.document_number.ilike(term))
                | (RepositoryDocument.issuing_authority.ilike(term))
            )

        if document_type_code:
            query = query.where(RepositoryDocument.document_type_code == document_type_code)

        if file_type:
            query = query.where(RepositoryDocument.file_type == file_type.lower())

        if parse_status:
            query = query.where(RepositoryDocument.parse_status == parse_status)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        # Fetch records with eager loaded document_type
        query = (
            query.options(selectinload(RepositoryDocument.document_type))
            .order_by(RepositoryDocument.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        docs = (await db.execute(query)).scalars().all()

        # Count attached knowledge documents per repository document
        doc_ids = [d.id for d in docs]
        usage_map: dict[str, int] = {}
        if doc_ids:
            usage_query = (
                select(KnowledgeDocument.repository_document_id, func.count(KnowledgeDocument.id))
                .where(
                    KnowledgeDocument.repository_document_id.in_(doc_ids),
                    KnowledgeDocument.is_active.is_(True),
                )
                .group_by(KnowledgeDocument.repository_document_id)
            )
            usage_results = (await db.execute(usage_query)).all()
            for r_id, cnt in usage_results:
                if r_id:
                    usage_map[r_id] = cnt

        items = [
            RepositoryDocumentListItem(
                id=d.id,
                title=d.title,
                file_name=d.file_name,
                file_type=d.file_type,
                file_size_bytes=d.file_size_bytes,
                file_hash=d.file_hash,
                document_type_code=d.document_type_code,
                document_type_name=d.document_type.name if d.document_type else None,
                document_number=d.document_number,
                issuing_authority=d.issuing_authority,
                issued_date=d.issued_date,
                effective_date=d.effective_date,
                parse_status=d.parse_status,
                ocr_engine=d.ocr_engine,
                attached_collections_count=usage_map.get(d.id, 0),
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs
        ]
        return items, total

    async def get_document(self, db: AsyncSession, doc_id: str) -> RepositoryDocumentResponse:
        """Get document details including attached Knowledge Collections."""
        stmt = (
            select(RepositoryDocument)
            .where(
                RepositoryDocument.id == doc_id,
                RepositoryDocument.is_active.is_(True),
            )
            .options(
                selectinload(RepositoryDocument.document_type),
            )
        )
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise EntityNotFoundError(f"Tài liệu '{doc_id}' không tồn tại trong kho.")

        kd_stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.repository_document_id == doc_id,
                KnowledgeDocument.is_active.is_(True),
            )
            .options(selectinload(KnowledgeDocument.collection))
        )
        kdocs = (await db.execute(kd_stmt)).scalars().all()
        attached_collections: list[AttachedCollectionInfo] = []
        for kd in kdocs:
            if kd.collection and kd.collection.is_active:
                attached_collections.append(
                    AttachedCollectionInfo(
                        collection_id=kd.collection.id,
                        collection_name=kd.collection.name,
                        document_id=kd.id,
                        index_status=kd.index_status,
                        created_at=kd.created_at,
                    )
                )

        return RepositoryDocumentResponse(
            id=doc.id,
            title=doc.title,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            file_hash=doc.file_hash,
            storage_path=doc.storage_path,
            document_type_code=doc.document_type_code,
            document_type_name=doc.document_type.name if doc.document_type else None,
            document_number=doc.document_number,
            issuing_authority=doc.issuing_authority,
            issued_date=doc.issued_date,
            effective_date=doc.effective_date,
            parse_status=doc.parse_status,
            ocr_engine=doc.ocr_engine,
            parsed_markdown=doc.parsed_markdown,
            doc_metadata=doc.doc_metadata or {},
            is_active=doc.is_active if doc.is_active is not None else True,
            attached_collections=attached_collections,
            attached_collections_count=len(attached_collections),
            created_at=doc.created_at or datetime.now(UTC),
            updated_at=doc.updated_at or datetime.now(UTC),
        )

    async def update_document(
        self,
        db: AsyncSession,
        doc_id: str,
        body: RepositoryDocumentUpdate,
    ) -> RepositoryDocumentResponse:
        """Update administrative metadata of a repository document."""
        stmt = select(RepositoryDocument).where(
            RepositoryDocument.id == doc_id,
            RepositoryDocument.is_active.is_(True),
        )
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise EntityNotFoundError(f"Tài liệu '{doc_id}' không tồn tại trong kho.")

        if body.title is not None:
            doc.title = body.title
        if body.document_type_code is not None:
            doc.document_type_code = body.document_type_code
        if body.document_number is not None:
            doc.document_number = body.document_number
        if body.issuing_authority is not None:
            doc.issuing_authority = body.issuing_authority
        if body.issued_date is not None:
            doc.issued_date = body.issued_date
        if body.effective_date is not None:
            doc.effective_date = body.effective_date
        if body.doc_metadata is not None:
            meta = dict(doc.doc_metadata or {})
            meta.update(body.doc_metadata)
            doc.doc_metadata = meta

        await db.commit()
        return await self.get_document(db, doc_id)

    async def delete_document(
        self,
        db: AsyncSession,
        doc_id: str,
        force: bool = False,
    ) -> bool:
        """Soft-delete document. Rejects deletion if attached to collections unless force=True."""
        stmt = (
            select(RepositoryDocument)
            .where(RepositoryDocument.id == doc_id, RepositoryDocument.is_active.is_(True))
            .options(selectinload(RepositoryDocument.knowledge_documents))
        )
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise EntityNotFoundError(f"Tài liệu '{doc_id}' không tồn tại.")

        active_usages = [kd for kd in doc.knowledge_documents if kd.is_active]
        if active_usages and not force:
            raise ValueError(
                f"Tài liệu đang được sử dụng trong {len(active_usages)} Kho Tri Thức. "
                "Vui lòng gỡ liên kết trước khi xóa hoặc dùng tùy chọn xóa cưỡng bức."
            )

        doc.is_active = False
        await db.commit()
        logger.info("Soft-deleted repository document %s (%s).", doc.id, doc.file_name)
        return True

    async def get_stats(self, db: AsyncSession) -> RepositoryDocumentStatsResponse:
        """Return aggregated KPI metrics for the repository dashboard."""
        total_stmt = select(func.count()).select_from(RepositoryDocument).where(RepositoryDocument.is_active.is_(True))
        total = (await db.execute(total_stmt)).scalar_one()

        parsed_stmt = (
            select(func.count())
            .select_from(RepositoryDocument)
            .where(RepositoryDocument.is_active.is_(True), RepositoryDocument.parse_status == "parsed")
        )
        parsed = (await db.execute(parsed_stmt)).scalar_one()

        pending_stmt = (
            select(func.count())
            .select_from(RepositoryDocument)
            .where(
                RepositoryDocument.is_active.is_(True),
                RepositoryDocument.parse_status.in_(["pending", "parsing"]),
            )
        )
        pending = (await db.execute(pending_stmt)).scalar_one()

        failed_stmt = (
            select(func.count())
            .select_from(RepositoryDocument)
            .where(RepositoryDocument.is_active.is_(True), RepositoryDocument.parse_status == "failed")
        )
        failed = (await db.execute(failed_stmt)).scalar_one()

        size_stmt = (
            select(func.coalesce(func.sum(RepositoryDocument.file_size_bytes), 0))
            .select_from(RepositoryDocument)
            .where(RepositoryDocument.is_active.is_(True))
        )
        total_size = (await db.execute(size_stmt)).scalar_one()

        types_stmt = (
            select(func.count(func.distinct(RepositoryDocument.document_type_code)))
            .select_from(RepositoryDocument)
            .where(RepositoryDocument.is_active.is_(True))
        )
        types_count = (await db.execute(types_stmt)).scalar_one()

        usages_stmt = (
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(KnowledgeDocument.is_active.is_(True), KnowledgeDocument.repository_document_id.is_not(None))
        )
        usages_count = (await db.execute(usages_stmt)).scalar_one()

        return RepositoryDocumentStatsResponse(
            total_documents=total,
            parsed_documents=parsed,
            pending_documents=pending,
            failed_documents=failed,
            total_size_bytes=int(total_size),
            document_types_count=types_count,
            attached_usages_count=usages_count,
        )

    async def get_file_content(self, db: AsyncSession, doc_id: str) -> tuple[bytes, str, str]:
        """Retrieve original file binary from MinIO S3 for downloading."""
        stmt = select(RepositoryDocument).where(
            RepositoryDocument.id == doc_id,
            RepositoryDocument.is_active.is_(True),
        )
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise EntityNotFoundError(f"Tài liệu '{doc_id}' không tồn tại.")

        data = await storage_service.get(doc.storage_path)
        if not data:
            raise EntityNotFoundError(f"Không tìm thấy tệp nhị phân trên MinIO: {doc.storage_path}")

        return data, doc.file_name, doc.file_type


document_repository_service = DocumentRepositoryService()
