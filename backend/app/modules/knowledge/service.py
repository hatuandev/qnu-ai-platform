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
from app.modules.knowledge.facts import fact_extractor
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
    CollectionUpdateRequest,
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
    ) -> tuple[str, str, int, bool, dict[int, list[dict]]]:
        """Rescue blank parses (scanned PDFs/images) via OCR auto-routing.

        Returns (markdown_text, engine_used, page_count, rescued, page_blocks).
        Never raises: OCR failure only means the document stays pending.
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
            return "", "none", 0, False, {}
        rescued = bool((ocr_result.raw_text or "").strip())
        page_blocks: dict[int, list[dict]] = {}
        for page in ocr_result.pages:
            if page.blocks:
                page_blocks[page.page_number] = [dict(b) for b in page.blocks]
        return (
            ocr_result.raw_text,
            ocr_result.engine_used,
            ocr_result.total_pages,
            rescued,
            page_blocks,
        )

    @staticmethod
    def _group_blocks_by_page(blocks: list[dict]) -> dict[int, list[dict]]:
        """Group flat parser blocks {page_number, ...} per page."""
        grouped: dict[int, list[dict]] = {}
        for block in blocks:
            try:
                page_number = int(block.get("page_number", 1))
            except (TypeError, ValueError):
                page_number = 1
            item = {k: v for k, v in block.items() if k != "page_number"}
            grouped.setdefault(page_number, []).append(item)
        return grouped

    @staticmethod
    def chunk_strategy_for(module_code: str) -> str:
        """Clause-based chunking for regulations, semantic otherwise."""
        return "clause" if module_code == "regulations" else "semantic"

    async def prepare_ingestion(
        self,
        db: AsyncSession,
        module_code: str,
        file_bytes: bytes,
        file_name: str,
        ocr_engine: str | None = None,
    ) -> dict:
        """Parse (+OCR rescue), clean and chunk a file without persisting.

        Shared by the sync upload path and background reprocessing tasks so
        both produce identical chunks, facts metadata and geometry.
        """
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"

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
            ocr_text, ocr_engine_used, ocr_pages, rescued, ocr_blocks = await self._run_ocr_rescue(
                db, file_bytes, file_name, ocr_engine
            )
            if rescued:
                parsed = ParsedContent(
                    raw_text=ocr_text,
                    page_count=ocr_pages,
                    tables=[],
                    metadata={"ocr_engine": ocr_engine_used},
                )
                parsed.blocks = [
                    {"page_number": page_number, **block}
                    for page_number, items in ocr_blocks.items()
                    for block in items
                ]
                ocr_method = ocr_engine_used
                ocr_fallback = True
                logger.info("OCR rescue succeeded for file='%s' via %s", file_name, ocr_method)

        # 3. Clean and normalize text
        cleaned_text = clean_markdown_text(parsed.raw_text)

        # 4. Chunking strategy
        chunker = get_chunker(self.chunk_strategy_for(module_code))
        chunk_drafts = chunker.chunk(cleaned_text)
        return {
            "ext": ext,
            "parsed": parsed,
            "cleaned_text": cleaned_text,
            "chunk_drafts": chunk_drafts,
            "ocr_method": ocr_method,
            "ocr_fallback": ocr_fallback,
        }

    async def persist_chunks_facts(
        self,
        db: AsyncSession,
        doc: KnowledgeDocument,
        collection_id: str,
        prepared: dict,
    ) -> int:
        """Persist chunks + facts for a document (no commit; caller commits)."""
        parsed = prepared["parsed"]
        chunk_drafts = prepared["chunk_drafts"]
        for draft in chunk_drafts:
            db.add(
                KnowledgeChunk(
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
            )
        for fact_data in fact_extractor.extract(
            tables=parsed.tables,
            collection_id=collection_id,
            document_id=doc.id,
        ):
            db.add(KnowledgeFact(**fact_data))
        return len(chunk_drafts)

    async def replace_document_content(
        self,
        db: AsyncSession,
        doc: KnowledgeDocument,
        collection_id: str,
        module_code: str,
        prepared: dict,
    ) -> int:
        """Replace chunks/facts/metadata of a document (background reprocessing)."""
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id))
        await db.execute(delete(KnowledgeFact).where(KnowledgeFact.document_id == doc.id))
        await db.flush()
        count = await self.persist_chunks_facts(db, doc, collection_id, prepared)
        metadata = dict(doc.doc_metadata or {})
        metadata.update(
            {
                "page_count": prepared["parsed"].page_count,
                "table_count": len(prepared["parsed"].tables),
                "chunk_count": count,
                "ocr_method": prepared["ocr_method"],
                "ocr_fallback": prepared["ocr_fallback"],
                "page_blocks": self._group_blocks_by_page(prepared["parsed"].blocks),
            }
        )
        doc.doc_metadata = metadata
        doc.status = "pending"
        await db.commit()
        await db.refresh(doc)
        return count

    async def update_collection(
        self, db: AsyncSession, collection_id: str, req: CollectionUpdateRequest
    ) -> KnowledgeCollection:
        col = await self.get_collection(db, collection_id)
        updates = req.model_dump(exclude_unset=True)
        if "metadata" in updates:
            merged = dict(col.collection_metadata or {})
            merged.update(updates.pop("metadata") or {})
            col.collection_metadata = merged
        for field, value in updates.items():
            if hasattr(col, field):
                setattr(col, field, value)
        await db.commit()
        await db.refresh(col)
        return col

    async def delete_collection(self, db: AsyncSession, collection_id: str) -> None:
        col = await self.get_collection(db, collection_id)
        await db.delete(col)
        await db.commit()
        logger.info("Permanently deleted collection id=%s", collection_id)

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

        # 2-4. Parse (+OCR rescue), clean and chunk via shared preparation
        prepared = await self.prepare_ingestion(
            db=db,
            module_code=col.module_code,
            file_bytes=file_bytes,
            file_name=file_name,
            ocr_engine=ocr_engine,
        )
        # 5. Persist Document entity (pending review -> approve indexes to Qdrant)
        parsed = prepared["parsed"]
        chunk_drafts = prepared["chunk_drafts"]
        doc = KnowledgeDocument(
            collection_id=collection_id,
            title=title or file_name.rsplit(".", 1)[0],
            file_name=file_name,
            file_type=prepared["ext"],
            file_size_bytes=file_size,
            file_hash=file_hash,
            storage_path=storage_rel_path,
            doc_metadata={
                "page_count": parsed.page_count,
                "table_count": len(parsed.tables),
                "chunk_count": len(chunk_drafts),
                "ocr_method": prepared["ocr_method"],
                "ocr_fallback": prepared["ocr_fallback"],
                "page_blocks": self._group_blocks_by_page(parsed.blocks),
            },
            status="pending",
            is_active=True,
        )
        db.add(doc)
        await db.flush()  # populate doc.id

        # 6-7. Persist chunks + structured facts (shared helper)
        await self.persist_chunks_facts(db, doc, collection_id, prepared)

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
            ocr_text, ocr_engine_used, ocr_pages, rescued, _ocr_blocks = (
                await self._run_ocr_rescue(db, file_bytes, file_name, ocr_engine)
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

    # Default box confidence per engine block type (documented engine default:
    # neither PyMuPDF geometry nor this Docling API version exposes per-block
    # confidence, so boxes never invent precision — see StudioBox contract).
    DEFAULT_BOX_CONFIDENCE: dict[str, float] = {
        "table": 0.95,
        "header": 0.92,
        "text": 0.90,
        "stamp": 0.88,
    }

    def build_studio_pages(
        self,
        chunks: list[dict],
        page_blocks: dict,
        document_id: str,
    ) -> list[dict]:
        """Pure builder: chunks + stored geometry -> per-page studio views."""
        by_page: dict[int, list[dict]] = {}
        for chunk in chunks:
            try:
                page_number = int(chunk.get("page_number") or 1)
            except (TypeError, ValueError):
                page_number = 1
            by_page.setdefault(page_number, []).append(chunk)
        for group in by_page.values():
            group.sort(key=lambda c: int(c.get("chunk_index", 0)))

        blocks_by_page: dict[int, list[dict]] = {}
        for raw_key, items in (page_blocks or {}).items():
            try:
                page_number = int(raw_key)
            except (TypeError, ValueError):
                continue
            if isinstance(items, list):
                blocks_by_page[page_number] = items

        page_numbers = sorted(set(by_page) | set(blocks_by_page)) or [1]
        pages: list[dict] = []
        for page_number in page_numbers:
            group = by_page.get(page_number, [])
            markdown = "\n\n".join(str(c.get("content", "")) for c in group).strip()
            boxes: list[dict] = []
            for idx, block in enumerate(blocks_by_page.get(page_number, []), start=1):
                box_type = str(block.get("type", "text"))
                coords = block.get("coordinates") or {}
                boxes.append(
                    {
                        "id": f"box_{document_id}_p{page_number}_{idx}",
                        "page_number": page_number,
                        "type": box_type,
                        "coordinates": {
                            "x": float(coords.get("x", 0)),
                            "y": float(coords.get("y", 0)),
                            "width": float(coords.get("width", 0)),
                            "height": float(coords.get("height", 0)),
                        },
                        "label": str(block.get("label", f"Khối {idx}")),
                        "confidence": float(
                            block.get(
                                "confidence",
                                self.DEFAULT_BOX_CONFIDENCE.get(box_type, 0.90),
                            )
                        ),
                        "content_snippet": str(block.get("content_snippet", ""))[:160],
                    }
                )
            regions = [
                {
                    "id": f"reg_{document_id}_p{page_number}_{idx}",
                    "page_number": page_number,
                    "title": box["label"],
                    "type": box["type"],
                    "confidence": box["confidence"],
                    "reading_order": idx,
                    "details": box["content_snippet"] or f"Khối {box['type']} #{idx}",
                }
                for idx, box in enumerate(boxes, start=1)
            ]
            words = markdown.split() if markdown else []
            pages.append(
                {
                    "page_number": page_number,
                    "markdown_content": markdown,
                    "raw_text": markdown,
                    "word_count": len(words),
                    "line_count": markdown.count("\n") + 1 if markdown else 0,
                    "image_url": None,  # filled by the router (page-image endpoint)
                    "bounding_boxes": boxes,
                    "regions": regions,
                }
            )
        return pages

    async def get_studio_view(self, db: AsyncSession, document_id: str) -> dict:
        """Assemble the verification studio view from stored chunks + geometry."""
        doc = await self.get_document(db, document_id)
        chunks = [
            {
                "content": c.content,
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
            }
            for c in sorted(
                doc.chunks, key=lambda c: ((c.page_number or 1), c.chunk_index)
            )
        ]
        pages = self.build_studio_pages(
            chunks=chunks,
            page_blocks=(doc.doc_metadata or {}).get("page_blocks", {}),
            document_id=doc.id,
        )
        metadata = doc.doc_metadata or {}
        total_pages = max(
            [p["page_number"] for p in pages] + [int(metadata.get("page_count", 0) or 0), 1]
        )
        return {
            "document_id": doc.id,
            "collection_id": doc.collection_id,
            "title": doc.title,
            "filename": doc.file_name,
            "engine": str(metadata.get("ocr_method", "PyMuPdfParser")),
            "total_pages": total_pages,
            "file_size_bytes": doc.file_size_bytes or 0,
            "total_chunks": len(chunks),
            "pages": pages,
        }

    # Office formats convertible to PDF via Gotenberg (LibreOffice) for preview.
    OFFICE_CONVERTIBLE = ("doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "rtf")
    RENDERABLE_DIRECT = ("pdf", "png", "jpg", "jpeg", "webp", "bmp")

    async def _convert_office_to_pdf(self, file_bytes: bytes, file_name: str) -> bytes:
        """Convert an office document to PDF bytes via Gotenberg LibreOffice."""
        import httpx

        from app.core.config import get_settings

        gotenberg_url = get_settings().GOTENBERG_URL.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{gotenberg_url}/forms/libreoffice/convert",
                    files={"files": (file_name, file_bytes)},
                )
        except Exception as exc:
            raise AppException(
                f"Không kết nối được dịch vụ chuyển đổi tài liệu (Gotenberg): {exc}",
                code="gotenberg_unreachable",
                status_code=503,
            ) from exc
        if response.status_code != 200:
            raise AppException(
                f"Chuyển đổi '{file_name}' sang PDF thất bại (HTTP {response.status_code}).",
                code="office_convert_failed",
                status_code=422,
            )
        return response.content

    async def render_page_image(
        self, db: AsyncSession, document_id: str, page_number: int
    ) -> bytes:
        """Render a document page to PNG (cached in storage).

        PDFs/images render directly; office docs (Word/Excel/PowerPoint) are
        converted via Gotenberg LibreOffice first. Anything else -> honest 404.
        """
        import pymupdf as fitz

        doc = await self.get_document(db, document_id)
        if doc.file_type not in self.RENDERABLE_DIRECT + self.OFFICE_CONVERTIBLE:
            raise AppException(
                f"Tài liệu '{doc.file_name}' không hỗ trợ xem trước ảnh trang.",
                code="page_preview_unsupported",
                status_code=404,
            )
        cache_key = f"previews/{doc.id}/page_{page_number}.png"
        cached = await storage_service.get(cache_key)
        if cached:
            return cached

        original = await storage_service.get(doc.storage_path)
        if not original:
            raise EntityNotFoundError(
                f"Không tìm thấy tệp gốc của tài liệu '{document_id}'.",
                details={"document_id": document_id},
            )
        if doc.file_type in self.OFFICE_CONVERTIBLE:
            pdf_bytes = await self._convert_office_to_pdf(original, doc.file_name)
            filetype = "pdf"
        else:
            pdf_bytes = original
            filetype = doc.file_type if doc.file_type != "bmp" else "png"
        try:
            pdf = fitz.open(stream=pdf_bytes, filetype=filetype)
        except Exception as exc:
            raise AppException(
                f"Không đọc được tệp gốc của tài liệu '{document_id}'.",
                code="page_render_failed",
                status_code=422,
                details={"reason": str(exc)},
            ) from exc
        if page_number < 1 or page_number > len(pdf):
            raise EntityNotFoundError(
                f"Trang {page_number} không tồn tại (tài liệu có {len(pdf)} trang).",
                details={"document_id": document_id, "page_number": page_number},
            )
        try:
            png_bytes = pdf[page_number - 1].get_pixmap(dpi=150).tobytes("png")
        finally:
            pdf.close()
        try:
            await storage_service.save(cache_key, png_bytes)
        except Exception as exc:
            logger.warning("Could not cache page preview %s: %s", cache_key, exc)
        return png_bytes

    async def batch_approve_documents(
        self,
        db: AsyncSession,
        document_ids: list[str],
    ) -> dict:
        """Approve many documents; per-item failures never abort the batch."""
        approved: list[str] = []
        failed: list[dict] = []
        indexed_chunks = 0
        for document_id in dict.fromkeys(document_ids):
            try:
                result = await self.approve_document(db, document_id, pages=None)
            except Exception as exc:
                logger.warning("Batch approve failed for %s: %s", document_id, exc)
                failed.append({"document_id": document_id, "error": str(exc)[:500]})
                continue
            approved.append(result["document_id"])
            indexed_chunks += int(result.get("indexed_chunks", 0))
        return {"approved": approved, "failed": failed, "indexed_chunks": indexed_chunks}

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
