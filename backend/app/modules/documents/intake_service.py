"""Intake Service Layer — Asynchronous Document Ingestion Pipeline (ADR-011).

Accepts binary payloads, generates SHA-256 digests, enforces idempotency and deduplication,
registers immutable revisions, and dispatches parsing jobs returning HTTP 202 Accepted.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.documents.revision_service import document_revision_service
from app.modules.documents.schemas import AsyncUploadDocumentResponse
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import enqueue_arq_job

logger = logging.getLogger(__name__)


def compute_sha256(data: bytes) -> str:
    """Compute standard SHA-256 hex digest for binary content."""
    return hashlib.sha256(data).hexdigest()


class DocumentIntakeService:
    """Service handling asynchronous document intake and job dispatching."""

    async def intake_document(
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
        idempotency_key: str | None = None,
        created_by: str | None = None,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
    ) -> AsyncUploadDocumentResponse:
        """Intake file asynchronously, returns 202 Accepted job payload."""
        file_size = len(file_bytes)
        file_hash = compute_sha256(file_bytes)
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"

        request_hash = compute_sha256(
            json.dumps(
                {
                    "file_hash": file_hash,
                    "file_name": file_name,
                    "title": title,
                    "document_type_code": document_type_code,
                    "document_number": document_number,
                    "issuing_authority": issuing_authority,
                    "issued_date": issued_date.isoformat() if issued_date else None,
                    "effective_date": effective_date.isoformat() if effective_date else None,
                    "ocr_engine": ocr_engine,
                    "tenant_id": tenant_id,
                    "workspace_id": workspace_id,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        )

        # Idempotency is scoped to tenant/workspace and rejects key reuse with another payload.
        if idempotency_key:
            idem_stmt = (
                select(DocumentRevision, RepositoryDocument)
                .join(RepositoryDocument, DocumentRevision.document_id == RepositoryDocument.id)
                .where(
                    DocumentRevision.idempotency_key == idempotency_key,
                    RepositoryDocument.tenant_id == tenant_id,
                    RepositoryDocument.workspace_id == workspace_id,
                )
            )
            existing_row = (await db.execute(idem_stmt)).first()
            if existing_row:
                existing_rev, existing_doc = existing_row
                if existing_rev.request_hash != request_hash:
                    raise AppException(
                        "Idempotency key đã được dùng cho một yêu cầu khác.",
                        code="IDEMPOTENCY_KEY_REUSED",
                        status_code=409,
                    )
                job_stmt = select(JobRecord).where(
                    JobRecord.document_id == existing_doc.id,
                    JobRecord.idempotency_key == idempotency_key,
                )
                existing_job = (await db.execute(job_stmt)).scalar_one_or_none()
                return AsyncUploadDocumentResponse(
                    document_id=existing_doc.id,
                    revision_id=existing_rev.id,
                    revision_no=existing_rev.revision_no,
                    file_name=existing_rev.source_file_name,
                    file_hash=existing_rev.source_hash,
                    job_id=existing_job.id if existing_job else "idempotent-replay",
                    status=existing_rev.status,
                    deduplicated=True,
                    created_at=existing_rev.created_at,
                )

        # 1. Deduplication check
        stmt = select(RepositoryDocument).where(
            RepositoryDocument.file_hash == file_hash,
            RepositoryDocument.is_active.is_(True),
            RepositoryDocument.tenant_id == tenant_id,
            RepositoryDocument.workspace_id == workspace_id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            logger.info("Intake file '%s' deduplicated with existing document %s", file_name, existing.id)
            current_rev_id = existing.current_revision_id or f"rev_{existing.id.replace('rep_doc_', '')[:12]}"
            return AsyncUploadDocumentResponse(
                document_id=existing.id,
                revision_id=current_rev_id,
                revision_no=existing.latest_revision_no or 1,
                file_name=existing.file_name,
                file_hash=existing.file_hash,
                job_id="deduplicated",
                status=existing.parse_status or "parsed",
                deduplicated=True,
                created_at=existing.created_at or datetime.now(UTC),
            )

        # 2. Persist original file in MinIO S3
        safe_name = file_name.replace(" ", "_")
        storage_key = f"documents/originals/{file_hash}/{safe_name}"
        await storage_service.save(storage_key, file_bytes)

        # 3. Create RepositoryDocument record
        doc_id = f"rep_doc_{uuid.uuid4().hex[:12]}"
        doc = RepositoryDocument(
            id=doc_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
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
            status="active",
            is_active=True,
            doc_metadata={
                "original_filename": file_name,
                "upload_channel": "async_intake_vault",
            },
        )
        db.add(doc)
        await db.flush()

        # 4. Create initial DocumentRevision v1
        rev = await document_revision_service.create_initial_revision(
            db=db,
            doc=doc,
            file_bytes=file_bytes,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )
        rev.request_hash = request_hash
        await db.flush()

        # 5. Create persistent JobRecord
        job_id = f"job_intake_{uuid.uuid4().hex[:12]}"
        job_record = JobRecord(
            id=job_id,
            job_type="document_revision_parse",
            status="queued",
            document_id=doc.id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            dispatch_status="pending",
            payload={
                "document_id": doc.id,
                "revision_id": rev.id,
                "ocr_engine": ocr_engine,
                "file_name": file_name,
            },
        )
        db.add(job_record)
        await db.flush()

        # 6. Commit the durable job/outbox record before broker dispatch.
        await db.commit()

        # 7. Dispatch ARQ. A failed dispatch remains pending for reconciliation.
        arq_job_id = await enqueue_arq_job(
            "task_document_revision_parse",
            job_record.id,
            broker_job_id=f"{job_record.id}:attempt:{job_record.attempt or 0}",
        )
        if arq_job_id:
            job_record.arq_job_id = arq_job_id
            job_record.dispatch_status = "dispatched"
            job_record.error = None
        else:
            job_record.dispatch_status = "pending"
            job_record.error = "ARQ Redis offline — job remains pending for reconciliation"

        await db.commit()
        await db.refresh(rev)

        return AsyncUploadDocumentResponse(
            document_id=doc.id,
            revision_id=rev.id,
            revision_no=rev.revision_no,
            file_name=file_name,
            file_hash=file_hash,
            job_id=job_id,
            status="queued",
            deduplicated=False,
            created_at=rev.created_at or datetime.now(UTC),
        )

document_intake_service = DocumentIntakeService()
