"""Revision Service Layer — Immutable Document Content Revisions & Quality Lifecycle."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, EntityNotFoundError, ValidationException
from app.core.storage import storage_service
from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.documents.quality_gate import evaluate_revision_quality
from app.modules.documents.schemas import (
    DocumentRevisionListItem,
    DocumentRevisionResponse,
    ReviewRevisionContentRequest,
    SubmitRevisionReviewRequest,
)
from app.modules.knowledge.cleaner import (
    clean_markdown_text,
    extract_administrative_metadata,
    extract_sections_metadata,
)
from app.modules.knowledge.parsers import get_document_parser

logger = logging.getLogger(__name__)


def compute_sha256(data: bytes | str) -> str:
    """Compute standard SHA-256 hex digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class DocumentRevisionService:
    """Manages the lifecycle of immutable document revisions."""

    @staticmethod
    def _to_response_dto(rev: DocumentRevision) -> DocumentRevisionResponse:
        provenance = dict(rev.parse_provenance or {})
        review_decision = provenance.get("review_decision") or {}
        human_reviews = provenance.get("human_reviews") or []
        notes = review_decision.get("notes")
        if not notes and human_reviews:
            notes = human_reviews[-1].get("notes")
        dto = DocumentRevisionResponse.model_validate(rev)
        dto.review_notes = notes
        return dto

    @staticmethod
    def _promote_revision_to_document(
        doc: RepositoryDocument,
        rev: DocumentRevision,
    ) -> None:
        """Move the logical document pointer and legacy projection to a ready revision."""
        doc.current_revision_id = rev.id
        doc.file_name = rev.source_file_name
        doc.file_type = rev.source_file_type
        doc.file_size_bytes = rev.source_size_bytes
        doc.file_hash = rev.source_hash
        doc.storage_path = rev.source_storage_path
        doc.parsed_markdown = rev.canonical_markdown
        doc.parse_status = "parsed"
        provenance = rev.parse_provenance or {}
        doc.ocr_engine = provenance.get("ocr_engine") or doc.ocr_engine
        doc.row_version = (doc.row_version or 1) + 1

    async def create_initial_revision(
        self,
        db: AsyncSession,
        doc: RepositoryDocument,
        file_bytes: bytes,
        idempotency_key: str | None = None,
        created_by: str | None = None,
    ) -> DocumentRevision:
        """Create the genesis v1 revision for a newly registered repository document."""
        rev_id = f"rev_{uuid.uuid4().hex[:12]}"
        rev = DocumentRevision(
            id=rev_id,
            document_id=doc.id,
            revision_no=1,
            based_on_revision_id=None,
            source_file_name=doc.file_name,
            source_file_type=doc.file_type,
            source_size_bytes=doc.file_size_bytes,
            source_hash=doc.file_hash,
            source_storage_path=doc.storage_path,
            status="queued",
            idempotency_key=idempotency_key,
            created_by=created_by,
            lock_version=1,
            quality_report={},
            page_manifest=[],
            citation_metadata={},
            parse_provenance={"trigger": "initial_upload"},
        )
        db.add(rev)
        doc.latest_revision_no = 1
        await db.flush()
        return rev

    async def _get_scoped_document(
        self,
        db: AsyncSession,
        document_id: str,
        actor: Any | None = None,
        for_update: bool = False,
    ) -> RepositoryDocument:
        stmt = select(RepositoryDocument).where(
            RepositoryDocument.id == document_id,
            RepositoryDocument.is_active.is_(True),
        )
        if actor:
            tenant_id = getattr(actor, "tenant_id", None)
            if tenant_id:
                stmt = stmt.where(RepositoryDocument.tenant_id == tenant_id)
            workspace_id = getattr(actor, "workspace_id", None)
            if workspace_id:
                stmt = stmt.where(RepositoryDocument.workspace_id == workspace_id)
        if for_update:
            stmt = stmt.with_for_update()
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise EntityNotFoundError(
                f"Tài liệu '{document_id}' không tồn tại trong phạm vi được cấp quyền."
            )
        return doc

    async def _get_scoped_revision(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        actor: Any | None = None,
        for_update: bool = False,
    ) -> tuple[RepositoryDocument, DocumentRevision]:
        doc = await self._get_scoped_document(
            db, document_id, actor=actor, for_update=for_update
        )
        stmt = select(DocumentRevision).where(
            DocumentRevision.id == revision_id,
            DocumentRevision.document_id == doc.id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        rev = (await db.execute(stmt)).scalar_one_or_none()
        if not rev:
            raise EntityNotFoundError(
                f"Bản sửa đổi '{revision_id}' không tồn tại trong tài liệu '{document_id}'."
            )
        return doc, rev

    async def create_new_revision(
        self,
        db: AsyncSession,
        doc_id: str,
        file_bytes: bytes,
        file_name: str,
        idempotency_key: str | None = None,
        created_by: str | None = None,
        actor: Any | None = None,
    ) -> DocumentRevision:
        """Create an updated revision (v2, v3, ...) based on the current active revision."""
        doc = await self._get_scoped_document(db, doc_id, actor=actor, for_update=True)

        file_hash = compute_sha256(file_bytes)
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"
        safe_name = file_name.replace(" ", "_")
        storage_key = f"documents/originals/{file_hash}/{safe_name}"
        await storage_service.save(storage_key, file_bytes)

        next_rev_no = (doc.latest_revision_no or 0) + 1
        rev_id = f"rev_{uuid.uuid4().hex[:12]}"

        rev = DocumentRevision(
            id=rev_id,
            document_id=doc.id,
            revision_no=next_rev_no,
            based_on_revision_id=doc.current_revision_id,
            source_file_name=file_name,
            source_file_type=ext,
            source_size_bytes=len(file_bytes),
            source_hash=file_hash,
            source_storage_path=storage_key,
            status="queued",
            idempotency_key=idempotency_key,
            created_by=created_by,
            lock_version=1,
            quality_report={},
            page_manifest=[],
            citation_metadata={},
            parse_provenance={
                "trigger": "new_revision_upload",
                "previous_revision_id": doc.current_revision_id,
            },
        )
        db.add(rev)
        doc.latest_revision_no = next_rev_no
        doc.row_version = (doc.row_version or 1) + 1
        await db.flush()
        return rev

    async def process_revision(
        self,
        db: AsyncSession,
        revision_id: str,
        document_id: str | None = None,
        actor: Any | None = None,
        ocr_engine: str | None = None,
    ) -> DocumentRevision:
        """Execute document parsing, OCR, text cleaning, and Quality Gate evaluation."""
        if document_id:
            doc, rev = await self._get_scoped_revision(
                db, document_id, revision_id, actor=actor, for_update=True
            )
        else:
            rev_stmt = select(DocumentRevision).where(DocumentRevision.id == revision_id)
            rev = (await db.execute(rev_stmt)).scalar_one_or_none()
            if not rev:
                raise EntityNotFoundError(f"Bản sửa đổi '{revision_id}' không tồn tại.")
            doc = await self._get_scoped_document(
                db, rev.document_id, actor=actor, for_update=True
            )

        if rev.status not in ("queued", "failed"):
            raise AppException(
                f"Không thể xử lý lại revision ở trạng thái '{rev.status}'.",
                code="REVISION_NOT_PROCESSABLE",
                status_code=409,
            )

        rev.status = "processing"
        rev.started_at = datetime.now(UTC)
        await db.flush()

        try:
            # 1. Fetch source binary from storage
            file_bytes = await storage_service.get(rev.source_storage_path)
            if not file_bytes:
                raise FileNotFoundError(
                    f"Không thể đọc tệp nguồn từ MinIO: {rev.source_storage_path}"
                )

            # 2. Parse text content
            parser = get_document_parser(rev.source_file_type)
            parsed = await parser.parse(file_bytes, rev.source_file_name)

            # 3. Clean text and extract metadata
            raw_text = parsed.raw_text or ""
            clean_md = clean_markdown_text(raw_text)
            sections = extract_sections_metadata(clean_md)
            admin_meta = extract_administrative_metadata(clean_md)

            # Auto-fill admin metadata onto document if unset
            if not doc.issued_date and admin_meta.get("issued_date"):
                doc.issued_date = admin_meta["issued_date"]  # type: ignore[assignment]
            if not doc.document_number and admin_meta.get("document_number"):
                doc.document_number = str(admin_meta["document_number"])
            if not doc.document_type_code and admin_meta.get("document_type_code"):
                doc.document_type_code = str(admin_meta["document_type_code"])
            if (not doc.title or doc.title == doc.file_name.rsplit(".", 1)[0]) and admin_meta.get("title"):
                doc.title = str(admin_meta["title"])
            if not doc.issuing_authority and admin_meta.get("issuing_authority"):
                doc.issuing_authority = str(admin_meta["issuing_authority"])

            # 4. Render PDF previews if PDF format
            preview_pages: list[str] = []
            if rev.source_file_type == "pdf":
                preview_pages = await self._render_pdf_previews(rev.source_hash, file_bytes)

            # 5. Evaluate Quality Gate
            quality_report = evaluate_revision_quality(
                markdown=clean_md,
                page_count=parsed.page_count,
                tables_count=len(parsed.tables),
                file_size_bytes=rev.source_size_bytes,
                ocr_engine=ocr_engine,
            )

            # 6. Populate Revision manifests
            rev.canonical_markdown = clean_md
            rev.canonical_hash = compute_sha256(clean_md)
            rev.page_manifest = [
                {"page": i + 1, "chars": len(clean_md) // max(1, parsed.page_count)}
                for i in range(parsed.page_count)
            ]
            rev.citation_metadata = {
                "document_number": doc.document_number,
                "issued_date": str(doc.issued_date) if doc.issued_date else None,
                "issuing_authority": doc.issuing_authority,
                "document_type_code": doc.document_type_code,
                "sections_count": len(sections),
            }
            provenance = dict(rev.parse_provenance or {})
            provenance.update(
                {
                    "ocr_engine": ocr_engine or "native",
                    "page_count": parsed.page_count,
                    "table_count": len(parsed.tables),
                    "preview_pages": preview_pages,
                }
            )
            rev.parse_provenance = provenance
            rev.quality_report = quality_report
            rev.finished_at = datetime.now(UTC)

            # 7. State Machine Decision
            overall_status = quality_report.get("overall_status")
            if overall_status == "passed":
                rev.status = "ready"
                self._promote_revision_to_document(doc, rev)
            elif overall_status == "warning":
                rev.status = "review_required"
                if not doc.current_revision_id:
                    doc.parse_status = "pending"
            else:
                rev.status = "failed"
                rev.failure_code = quality_report.get("failure_code", "QUALITY_GATE_FAILED")
                rev.failure_detail = f"Quality gate failed with flags: {quality_report.get('warning_flags')}"
                if not doc.current_revision_id:
                    doc.parse_status = "failed"

            logger.info(
                "Revision %s (%s) processed: status=%s, overall_quality=%s",
                rev.id,
                doc.file_name,
                rev.status,
                overall_status,
            )
        except Exception as exc:
            logger.exception("Failed processing revision %s", revision_id)
            rev.status = "failed"
            rev.failure_code = "PARSE_ERROR"
            rev.failure_detail = str(exc)
            rev.finished_at = datetime.now(UTC)
            if not doc.current_revision_id:
                doc.parse_status = "failed"

        await db.commit()
        await db.refresh(rev)
        return rev

    async def _render_pdf_previews(self, file_hash: str, pdf_bytes: bytes) -> list[str]:
        """Render first few pages to PNG for preview."""
        keys: list[str] = []
        try:
            import fitz

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            max_pages = min(len(doc), 5)
            for page_idx in range(max_pages):
                page = doc.load_page(page_idx)
                pix = page.get_pixmap(dpi=120)
                key = f"documents/renders/{file_hash}/page_{page_idx + 1}.png"
                await storage_service.save(key, pix.tobytes("png"))
                keys.append(key)
            doc.close()
        except Exception as exc:
            logger.warning("Could not render preview PNGs for hash %s: %s", file_hash, exc)
        return keys

    async def list_document_revisions(
        self,
        db: AsyncSession,
        document_id: str,
        actor: Any | None = None,
    ) -> list[DocumentRevisionListItem]:
        """List all revisions of a document sorted by revision_no descending."""
        doc = await self._get_scoped_document(db, document_id, actor=actor)

        stmt = (
            select(DocumentRevision)
            .where(DocumentRevision.document_id == doc.id)
            .order_by(DocumentRevision.revision_no.desc())
        )
        revisions = (await db.execute(stmt)).scalars().all()
        return [DocumentRevisionListItem.model_validate(r) for r in revisions]

    async def get_document_revision(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        actor: Any | None = None,
    ) -> DocumentRevisionResponse:
        """Get full details of a specific revision."""
        _, rev = await self._get_scoped_revision(
            db, document_id, revision_id, actor=actor
        )
        return self._to_response_dto(rev)

    async def update_revision_content(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        body: ReviewRevisionContentRequest,
        actor: Any | None = None,
    ) -> DocumentRevisionResponse:
        """Allow reviewers to edit canonical markdown during review phase."""
        doc, rev = await self._get_scoped_revision(
            db, document_id, revision_id, actor=actor, for_update=True
        )

        if rev.status != "review_required":
            raise ValidationException(
                f"Không thể hiệu đính bản sửa đổi ở trạng thái '{rev.status}'."
            )

        if rev.lock_version != body.expected_lock_version:
            raise AppException(
                "Bản sửa đổi đã thay đổi bởi một phiên làm việc khác.",
                code="REVISION_LOCK_CONFLICT",
                status_code=409,
            )

        clean_content = clean_markdown_text(body.canonical_markdown)
        rev.canonical_markdown = clean_content
        rev.canonical_hash = compute_sha256(clean_content)
        rev.lock_version = (rev.lock_version or 1) + 1

        provenance = dict(rev.parse_provenance or {})
        reviews = list(provenance.get("human_reviews", []))
        reviews.append(
            {
                "edited_at": datetime.now(UTC).isoformat(),
                "notes": body.notes,
                "content_length": len(clean_content),
            }
        )
        provenance["human_reviews"] = reviews
        rev.parse_provenance = provenance

        # Re-evaluate quality gate with reviewed markdown
        quality_report = evaluate_revision_quality(
            markdown=clean_content,
            page_count=len(rev.page_manifest or []) or 1,
            tables_count=provenance.get("table_count", 0),
            file_size_bytes=rev.source_size_bytes,
        )
        rev.quality_report = quality_report

        # Sync to parent document legacy preview using already scoped & locked entity
        if doc.current_revision_id == rev.id:
            doc.parsed_markdown = clean_content

        await db.commit()
        await db.refresh(rev)
        return self._to_response_dto(rev)

    async def submit_revision_review(
        self,
        db: AsyncSession,
        document_id: str,
        revision_id: str,
        body: SubmitRevisionReviewRequest,
        actor: Any | None = None,
    ) -> DocumentRevisionResponse:
        """Finalize review decision (approve -> ready, or reject -> review_required)."""
        doc, rev = await self._get_scoped_revision(
            db, document_id, revision_id, actor=actor, for_update=True
        )

        if rev.status != "review_required":
            raise AppException(
                f"Chỉ revision 'review_required' mới được duyệt (hiện tại: {rev.status}).",
                code="INVALID_REVISION_REVIEW_STATE",
                status_code=409,
            )
        if rev.lock_version != body.expected_lock_version:
            raise AppException(
                "Bản sửa đổi đã thay đổi bởi một phiên làm việc khác.",
                code="REVISION_LOCK_CONFLICT",
                status_code=409,
            )

        if body.action == "approve":
            quality_status = (rev.quality_report or {}).get("overall_status")
            if quality_status not in ("passed", "warning") or not rev.canonical_markdown:
                raise AppException(
                    "Revision chưa vượt Quality Gate hoặc không có nội dung chuẩn hóa.",
                    code="REVISION_QUALITY_GATE_NOT_PASSED",
                    status_code=409,
                )
            rev.status = "ready"
            self._promote_revision_to_document(doc, rev)
            logger.info("Revision %s approved and promoted to current revision.", rev.id)
        elif body.action == "reject":
            rev.status = "review_required"
            logger.info("Revision %s rejected by reviewer.", rev.id)
        else:
            raise ValidationException(f"Hành động '{body.action}' không hợp lệ (approve hoặc reject).")

        provenance = dict(rev.parse_provenance or {})
        provenance["review_decision"] = {
            "action": body.action,
            "notes": body.notes,
            "decided_at": datetime.now(UTC).isoformat(),
        }
        rev.parse_provenance = provenance
        rev.lock_version = (rev.lock_version or 1) + 1

        await db.commit()
        await db.refresh(rev)
        return DocumentRevisionResponse.model_validate(rev)


document_revision_service = DocumentRevisionService()
