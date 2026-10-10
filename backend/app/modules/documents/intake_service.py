"""Intake Service Layer — Asynchronous Document Ingestion Pipeline (ADR-011).

Accepts binary payloads, generates SHA-256 digests, enforces idempotency and deduplication,
registers immutable revisions, and dispatches parsing jobs returning HTTP 202 Accepted.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.documents.models import (
    DocumentGroup,
    DocumentGroupMembership,
    DocumentRevision,
    RepositoryDocument,
)
from app.modules.documents.revision_service import document_revision_service
from app.modules.documents.schemas import AsyncUploadDocumentResponse
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import enqueue_arq_job

logger = logging.getLogger(__name__)

VALID_REVISION_STATUSES: frozenset[str] = frozenset({
    "queued",
    "processing",
    "validating",
    "review_required",
    "ready",
    "failed",
    "cancelled",
})


def compute_sha256(data: bytes) -> str:
    """Compute standard SHA-256 hex digest for binary content."""
    return hashlib.sha256(data).hexdigest()


def sanitize_safe_filename(file_name: str) -> str:
    """Normalize and sanitize filename into a safe ASCII-clean representation preserving extension."""
    if not file_name or not file_name.strip():
        return "document.pdf"
    name = file_name.strip()
    name = name.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_clean = "".join(c for c in nfkd if not unicodedata.combining(c))
    clean = re.sub(r"[^\w.-]+", "_", ascii_clean).lower()
    clean = re.sub(r"_+", "_", clean).strip("._")
    return clean or "document.pdf"


def _resolve_actor_id(actor: Any | None) -> str:
    """Extract audit actor identifier following hierarchy: actor.actor_id -> actor.username -> 'system'."""
    if not actor:
        return "system"
    return getattr(actor, "actor_id", None) or getattr(actor, "username", None) or "system"


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
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        group_id: str | None = None,
        actor: Any | None = None,
    ) -> AsyncUploadDocumentResponse:
        """Intake file asynchronously into repository and optional document group with atomic orchestration."""
        # 1. Resolve scope strictly from actor when available
        resolved_tenant = getattr(actor, "tenant_id", None) or tenant_id or "tenant_qnu"
        resolved_workspace = getattr(actor, "workspace_id", None) or workspace_id or "workspace_qnu"
        resolved_created_by = _resolve_actor_id(actor) if actor else (created_by or "system")

        # 2. Validate Document Group existence and tenant/workspace isolation BEFORE any file persistence
        group: DocumentGroup | None = None
        if group_id:
            group = await db.get(DocumentGroup, group_id)
            if not group:
                raise AppException(
                    message=f"Không tìm thấy kho tài liệu '{group_id}'.",
                    code="DOCUMENT_GROUP_NOT_FOUND",
                    status_code=404,
                )
            if group.tenant_id != resolved_tenant or (
                resolved_workspace and group.workspace_id != resolved_workspace
            ):
                raise AppException(
                    message="Không có quyền truy cập kho tài liệu này trong workspace hiện tại.",
                    code="DOCUMENT_GROUP_ACCESS_DENIED",
                    status_code=403,
                )

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
                    "group_id": group_id,
                    "tenant_id": resolved_tenant,
                    "workspace_id": resolved_workspace,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        )

        # 3. Idempotency check scoped to tenant/workspace
        if idempotency_key:
            idem_stmt = (
                select(DocumentRevision, RepositoryDocument)
                .join(RepositoryDocument, DocumentRevision.document_id == RepositoryDocument.id)
                .where(
                    DocumentRevision.idempotency_key == idempotency_key,
                    RepositoryDocument.tenant_id == resolved_tenant,
                    RepositoryDocument.workspace_id == resolved_workspace,
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

                # Ensure membership exists for group if specified
                if group:
                    mem_check = (
                        select(DocumentGroupMembership)
                        .where(
                            DocumentGroupMembership.group_id == group.id,
                            DocumentGroupMembership.document_id == existing_doc.id,
                        )
                    )
                    mem_exists = (await db.execute(mem_check)).scalar_one_or_none()
                    if not mem_exists:
                        membership = DocumentGroupMembership(
                            group_id=group.id,
                            document_id=existing_doc.id,
                            added_by=resolved_created_by,
                            added_at=datetime.now(UTC),
                        )
                        db.add(membership)
                        group.updated_at = datetime.now(UTC)
                        await db.commit()

                job_stmt = (
                    select(JobRecord)
                    .where(
                        JobRecord.document_id == existing_doc.id,
                        JobRecord.idempotency_key == idempotency_key,
                    )
                    .order_by(JobRecord.created_at.desc())
                    .limit(1)
                )
                existing_job = (await db.execute(job_stmt)).scalar_one_or_none()
                resolved_job_id = (
                    existing_job.id
                    if existing_job and isinstance(getattr(existing_job, "id", None), str)
                    else None
                )
                return AsyncUploadDocumentResponse(
                    document_id=existing_doc.id,
                    revision_id=existing_rev.id,
                    revision_no=existing_rev.revision_no,
                    file_name=existing_rev.source_file_name,
                    file_hash=existing_rev.source_hash,
                    job_id=resolved_job_id,
                    status=existing_rev.status,
                    deduplicated=True,
                    created_at=existing_rev.created_at,
                )

        # 4. Scoped deduplication check: tenant_id + workspace_id + file_hash
        stmt = select(RepositoryDocument).where(
            RepositoryDocument.file_hash == file_hash,
            RepositoryDocument.tenant_id == resolved_tenant,
            RepositoryDocument.workspace_id == resolved_workspace,
            RepositoryDocument.is_active.is_(True),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            logger.info(
                "Intake file '%s' deduplicated with existing document %s in tenant=%s, workspace=%s",
                file_name,
                existing.id,
                resolved_tenant,
                resolved_workspace,
            )
            # Idempotently bind membership to group if specified
            if group:
                mem_stmt = select(DocumentGroupMembership).where(
                    DocumentGroupMembership.group_id == group.id,
                    DocumentGroupMembership.document_id == existing.id,
                )
                existing_mem = (await db.execute(mem_stmt)).scalar_one_or_none()
                if not existing_mem:
                    membership = DocumentGroupMembership(
                        group_id=group.id,
                        document_id=existing.id,
                        added_by=resolved_created_by,
                        added_at=datetime.now(UTC),
                    )
                    db.add(membership)
                    group.updated_at = datetime.now(UTC)
                    await db.commit()

            # Resolve current revision of existing document
            existing_rev = getattr(existing, "current_revision", None)
            if not existing_rev and existing.current_revision_id:
                candidate = await db.get(DocumentRevision, existing.current_revision_id)
                if isinstance(candidate, DocumentRevision) or hasattr(candidate, "revision_no"):
                    existing_rev = candidate
            if not existing_rev:
                rev_stmt = (
                    select(DocumentRevision)
                    .where(DocumentRevision.document_id == existing.id)
                    .order_by(DocumentRevision.revision_no.desc())
                    .limit(1)
                )
                existing_rev = (await db.execute(rev_stmt)).scalar_one_or_none()

            if not existing_rev or existing_rev.status not in VALID_REVISION_STATUSES:
                raise AppException(
                    message=f"Tài liệu trùng lặp '{existing.id}' không có phiên bản hợp lệ trong hệ thống.",
                    code="DOCUMENT_REVISION_INVALID",
                    status_code=409,
                )

            resolved_status = existing_rev.status
            resolved_rev_id = existing_rev.id
            resolved_rev_no = existing_rev.revision_no

            job_stmt = (
                select(JobRecord)
                .where(JobRecord.document_id == existing.id)
                .order_by(JobRecord.created_at.desc())
                .limit(1)
            )
            existing_job = (await db.execute(job_stmt)).scalar_one_or_none()
            resolved_job_id = (
                existing_job.id
                if existing_job and isinstance(getattr(existing_job, "id", None), str)
                else None
            )

            return AsyncUploadDocumentResponse(
                document_id=existing.id,
                revision_id=resolved_rev_id,
                revision_no=resolved_rev_no,
                file_name=existing.file_name,
                file_hash=existing.file_hash,
                job_id=resolved_job_id,
                status=resolved_status,
                deduplicated=True,
                created_at=existing.created_at or datetime.now(UTC),
            )

        # 5. Persist original file in MinIO S3 with scope isolation
        safe_name = sanitize_safe_filename(file_name)
        storage_key = f"documents/{resolved_tenant}/{resolved_workspace}/originals/{file_hash}/{safe_name}"
        await storage_service.save(storage_key, file_bytes)

        # 6. Database Transaction Orchestration with MinIO Compensation
        now = datetime.now(UTC)
        try:
            # 6.1 Create RepositoryDocument record
            doc_id = f"rep_doc_{uuid.uuid4().hex[:12]}"
            doc = RepositoryDocument(
                id=doc_id,
                tenant_id=resolved_tenant,
                workspace_id=resolved_workspace,
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

            # 6.2 Create initial DocumentRevision v1 (flush only, no commit)
            rev = await document_revision_service.create_initial_revision(
                db=db,
                doc=doc,
                file_bytes=file_bytes,
                idempotency_key=idempotency_key,
                created_by=resolved_created_by,
            )
            rev.request_hash = request_hash
            await db.flush()

            # 6.3 Create DocumentGroupMembership if group specified
            if group:
                membership = DocumentGroupMembership(
                    group_id=group.id,
                    document_id=doc.id,
                    added_by=resolved_created_by,
                    added_at=now,
                )
                db.add(membership)
                group.updated_at = now
                await db.flush()

            # 6.4 Create persistent JobRecord in pending state
            job_id = f"job_intake_{uuid.uuid4().hex[:12]}"
            job_record = JobRecord(
                id=job_id,
                job_type="document_revision_parse",
                status="queued",
                document_id=doc.id,
                tenant_id=resolved_tenant,
                workspace_id=resolved_workspace,
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

            # 6.5 Atomic durable commit before broker dispatch
            await db.commit()
        except IntegrityError:
            await db.rollback()
            # Concurrent race condition: another request committed the exact same document
            winner_stmt = select(RepositoryDocument).where(
                RepositoryDocument.file_hash == file_hash,
                RepositoryDocument.tenant_id == resolved_tenant,
                RepositoryDocument.workspace_id == resolved_workspace,
                RepositoryDocument.is_active.is_(True),
            )
            winner_doc = (await db.execute(winner_stmt)).scalar_one_or_none()
            if winner_doc:
                # Do NOT delete storage_key: winner uses this content-addressed artifact
                logger.info("Concurrent race handled: linking to winning document %s", winner_doc.id)
                if group_id:
                    mem_check = select(DocumentGroupMembership).where(
                        DocumentGroupMembership.group_id == group_id,
                        DocumentGroupMembership.document_id == winner_doc.id,
                    )
                    existing_mem = (await db.execute(mem_check)).scalar_one_or_none()
                    if not existing_mem:
                        membership = DocumentGroupMembership(
                            group_id=group_id,
                            document_id=winner_doc.id,
                            added_by=resolved_created_by,
                            added_at=datetime.now(UTC),
                        )
                        db.add(membership)
                        if group:
                            group.updated_at = datetime.now(UTC)
                        await db.commit()

                # Resolve real revision of winning document
                winner_rev = getattr(winner_doc, "current_revision", None)
                if not winner_rev and winner_doc.current_revision_id:
                    candidate = await db.get(DocumentRevision, winner_doc.current_revision_id)
                    if isinstance(candidate, DocumentRevision) or hasattr(candidate, "revision_no"):
                        winner_rev = candidate
                if not winner_rev:
                    rev_stmt = (
                        select(DocumentRevision)
                        .where(DocumentRevision.document_id == winner_doc.id)
                        .order_by(DocumentRevision.revision_no.desc())
                        .limit(1)
                    )
                    winner_rev = (await db.execute(rev_stmt)).scalar_one_or_none()

                # Must have a valid V2 revision; never synthesize fake revision ID or default queued status
                if not winner_rev or winner_rev.status not in VALID_REVISION_STATUSES:
                    raise AppException(
                        message=f"Tài liệu trùng lặp '{winner_doc.id}' không có phiên bản hợp lệ trong hệ thống.",
                        code="DOCUMENT_REVISION_INVALID",
                        status_code=409,
                    )

                # Resolve real job record if one exists
                job_stmt = (
                    select(JobRecord)
                    .where(JobRecord.document_id == winner_doc.id)
                    .order_by(JobRecord.created_at.desc())
                    .limit(1)
                )
                existing_job = (await db.execute(job_stmt)).scalar_one_or_none()
                resolved_job_id = (
                    existing_job.id
                    if existing_job and isinstance(getattr(existing_job, "id", None), str)
                    else None
                )

                return AsyncUploadDocumentResponse(
                    document_id=winner_doc.id,
                    revision_id=winner_rev.id,
                    revision_no=winner_rev.revision_no,
                    file_name=winner_rev.source_file_name or winner_doc.file_name,
                    file_hash=winner_rev.source_hash or winner_doc.file_hash,
                    job_id=resolved_job_id,
                    status=winner_rev.status,
                    deduplicated=True,
                    created_at=winner_rev.created_at or winner_doc.created_at or datetime.now(UTC),
                )

            # If no winner was found, the transaction failed completely: compensation-delete object
            try:
                await storage_service.delete(storage_key)
            except Exception as cleanup_exc:
                logger.warning(
                    "Failed to delete S3 storage_key %s during failed transaction compensation: %s",
                    storage_key,
                    cleanup_exc,
                )
            raise
        except Exception:
            await db.rollback()
            # S3 Compensation: delete uploaded artifact if DB transaction fails
            try:
                await storage_service.delete(storage_key)
            except Exception as cleanup_exc:
                logger.warning(
                    "Failed to delete S3 storage_key %s during rollback compensation: %s",
                    storage_key,
                    cleanup_exc,
                )
            raise

        # 7. Post-commit ARQ dispatch. If Redis is offline, job remains pending for reconciliation.
        try:
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
        except Exception as dispatch_exc:
            logger.warning("ARQ dispatch failed, retaining pending status: %s", dispatch_exc)
            job_record.dispatch_status = "pending"
            job_record.error = f"ARQ Redis offline: {dispatch_exc}"

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
