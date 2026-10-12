"""Knowledge Source Ingestion Service (ADR-012).

Responsible for:
1. One-way snapshot ingestion from Repository Document into Knowledge domain.
2. Native / OCR document parsing, Vietnamese normalizer (Unicode NFC), and administrative metadata extraction.
3. Quality Gate evaluation (passed -> ready, warning -> review_required, failed -> failed).
4. Artifact key materialization for "parse once, embed many" reuse.
5. Content editing, review/approval, and retry capabilities.
6. Absolute zero-writeback invariant into RepositoryDocument or DocumentRevision.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.documents.models import RepositoryDocument
from app.modules.documents.quality_gate import evaluate_revision_quality
from app.modules.jobs.ingestion_progress import report_progress
from app.modules.knowledge.cleaner import extract_administrative_metadata
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeImportBatch,
    KnowledgeImportItem,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.services.source_artifact import (
    build_source_artifact,
    get_source_artifact,
)
from app.modules.knowledge.services.source_extraction import (
    EXTRACTION_VERSION,
    SourceExtraction,
    extract_source,
    save_source_preview,
)
from app.modules.knowledge.services.source_pages import (
    manifest_page_count,
    merge_edited_manifest,
    normalize_source_pages,
)
from app.modules.knowledge.services.temporal_metadata import extract_temporal_metadata

logger = logging.getLogger(__name__)


def compute_sha256(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


class SourceIngestionService:
    """Orchestrates source document parsing, normalization and Quality Gate in Knowledge domain."""

    async def process_import_item(
        self,
        db: AsyncSession,
        item_id: str,
        ocr_engine: str | None = None,
    ) -> KnowledgeSourceRevision:
        """Process a single KnowledgeImportItem through the Knowledge ingestion pipeline."""
        # 1. Load item and its batch
        item_res = await db.execute(
            select(KnowledgeImportItem)
            .options(selectinload(KnowledgeImportItem.batch))
            .where(KnowledgeImportItem.id == item_id).with_for_update()
        )
        item = item_res.scalar_one_or_none()
        if not item:
            raise AppException(
                message=f"Không tìm thấy mục nạp tài liệu {item_id}",
                code="IMPORT_ITEM_NOT_FOUND",
                status_code=404,
            )

        batch: KnowledgeImportBatch = item.batch
        if item.status == "skipped" or batch.status == "cancelled":
            raise AppException("Đợt nạp đã bị hủy.", code="IMPORT_CANCELLED", status_code=409)
        if item.status == "succeeded" and item.knowledge_source_revision_id:
            existing = await db.get(KnowledgeSourceRevision, item.knowledge_source_revision_id)
            if existing:
                return existing
        if item.status == "processing":
            raise AppException("Tài liệu đang được xử lý.", code="IMPORT_ITEM_IN_PROGRESS", status_code=409)
        item.status = "processing"
        item.phase = "snapshot"
        if batch.queued_count > 0:
            batch.queued_count -= 1
        batch.processing_count += 1
        await db.commit()

        try:
            # 2. Fetch source repository document
            doc_res = await db.execute(
                select(RepositoryDocument).where(
                    RepositoryDocument.id == item.origin_document_id,
                    RepositoryDocument.tenant_id == batch.tenant_id,
                    RepositoryDocument.workspace_id == batch.workspace_id,
                )
            )
            doc = doc_res.scalar_one_or_none()
            if not doc:
                raise AppException(
                    message=f"Không tìm thấy tài liệu gốc {item.origin_document_id}",
                    code="REPOSITORY_DOCUMENT_NOT_FOUND",
                    status_code=404,
                )

            # 3. Read file bytes from storage
            file_bytes = await storage_service.get((item.origin_metadata or {}).get("_storage_path") or doc.storage_path)
            if not file_bytes:
                raise AppException(
                    message=f"Tệp nguồn không tồn tại hoặc rỗng trên hệ thống lưu trữ: {doc.storage_path}",
                    code="FILE_CONTENT_EMPTY",
                    status_code=400,
                )

            if compute_sha256(file_bytes) != item.origin_file_hash:
                raise AppException("Tệp nguồn đã thay đổi sau khi chọn.", code="SOURCE_HASH_MISMATCH", status_code=409)

            # 4. Lookup or create KnowledgeBinding for this collection
            binding_res = await db.execute(
                select(KnowledgeBinding).where(
                    KnowledgeBinding.collection_id == batch.collection_id,
                    KnowledgeBinding.repository_document_id == doc.id,
                )
            )
            binding = binding_res.scalar_one_or_none()
            if binding and binding.status == "deleting":
                raise AppException("Nguồn đang xóa vĩnh viễn; chờ hoàn tất rồi nạp lại.",
                                   code="SOURCE_DELETING", status_code=409)
            if not binding:
                binding = KnowledgeBinding(
                    id=f"bnd_{uuid.uuid4().hex[:12]}",
                    collection_id=batch.collection_id,
                    repository_document_id=doc.id,
                    source_revision_id=None,
                    status="pending",
                    tenant_id=batch.tenant_id,
                    workspace_id=batch.workspace_id,
                )
                db.add(binding)
                await db.flush()

            item.knowledge_binding_id = binding.id

            # Store independent snapshot in knowledge domain storage
            snapshot_path = f"snapshots/{batch.collection_id}/{binding.id}/{item.origin_file_hash}_{item.origin_file_name}"
            if not await storage_service.exists(snapshot_path):
                await storage_service.save(snapshot_path, file_bytes)

            # Determine next revision number
            rev_count_res = await db.execute(
                select(KnowledgeSourceRevision.revision_no)
                .where(KnowledgeSourceRevision.binding_id == binding.id)
                .order_by(KnowledgeSourceRevision.revision_no.desc())
            )
            latest_no = rev_count_res.scalars().first() or 0
            next_rev_no = latest_no + 1

            # 5. Check artifact key reuse with tenant/workspace isolation ("parse once, embed many")
            parser_profile = batch.parser_profile or "standard"
            from app.modules.knowledge.services.parse_fingerprint import (
                ocr_configuration_fingerprint,
            )

            ocr_config_hash = await ocr_configuration_fingerprint(db)
            artifact_key = compute_sha256(f"{item.origin_file_hash}:{parser_profile}:{ocr_engine}:{ocr_config_hash}:{EXTRACTION_VERSION}")

            existing_artifact_res = await db.execute(
                select(KnowledgeSourceRevision)
                .join(KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id)
                .where(
                    KnowledgeSourceRevision.artifact_key == artifact_key,
                    KnowledgeSourceRevision.binding_id == binding.id,
                    KnowledgeSourceRevision.status == "ready",
                    KnowledgeBinding.tenant_id == batch.tenant_id,
                    KnowledgeBinding.workspace_id == batch.workspace_id,
                    KnowledgeBinding.status != "deleting",
                )
            )
            existing_artifact = existing_artifact_res.scalars().first()

            if existing_artifact and existing_artifact.canonical_markdown:
                logger.info(
                    "Reusing existing parsed source artifact %s for document %s (artifact_key=%s)",
                    existing_artifact.id,
                    doc.id,
                    artifact_key,
                )
                clean_md = existing_artifact.canonical_markdown
                canonical_hash = existing_artifact.canonical_hash or compute_sha256(clean_md)
                page_manifest = list(existing_artifact.page_manifest or [])
                citation_metadata = dict(existing_artifact.citation_metadata or {})
                quality_report = dict(existing_artifact.quality_report or {})
                structured_artifact = get_source_artifact(existing_artifact)
                reused_artifact = True
                ocr_engine = (existing_artifact.parse_provenance or {}).get("ocr_engine") or "native"
                preview_path = (existing_artifact.snapshot_metadata or {}).get("preview_pdf_path")
                if preview_path:
                    preview = await storage_service.get(preview_path)
                    if not preview:
                        raise AppException("Thiếu PDF xem trước của artifact đã lưu.",
                                           code="SOURCE_PREVIEW_UNAVAILABLE", status_code=409)
                    preview_path = await save_source_preview(snapshot_path, SourceExtraction("", 0, preview_pdf=preview))
            else:
                reused_artifact = False

                await self._check_cancelled(db, batch)
                # Phase: parse
                item.phase = "parse"
                await db.commit()
                await report_progress("parse", 20)

                extraction = await extract_source(db, file_bytes, item.origin_file_name,
                                                  item.origin_file_type, parser_profile, ocr_engine, batch.tenant_id)
                preview_path = await save_source_preview(snapshot_path, extraction)
                raw_text = extraction.raw_text
                parsed_page_count = extraction.page_count
                ocr_pages = extraction.pages
                extracted_tables = extraction.tables
                parsed_tables_count = len(extracted_tables)
                ocr_engine = extraction.engine_used

                if not raw_text.strip():
                    raise AppException(
                        message=f"Không thể bóc tách nội dung văn bản từ tệp '{doc.file_name}'. Tệp có thể chứa ảnh quét không rõ hoặc bị khóa.",
                        code="EMPTY_EXTRACTED_TEXT",
                        status_code=422,
                    )

                # Phase: normalize
                item.phase = "normalize"
                await report_progress("normalize", 65)
                await db.flush()
                clean_md, page_manifest = normalize_source_pages(raw_text, parsed_page_count, ocr_pages)
                canonical_hash = compute_sha256(clean_md)
                admin_meta = extract_administrative_metadata(clean_md)

                # Phase: validate (Quality Gate)
                item.phase = "validate"
                await report_progress("validate", 75)
                await db.flush()
                quality_report = evaluate_revision_quality(
                    markdown=clean_md,
                    page_count=parsed_page_count,
                    tables_count=parsed_tables_count,
                    file_size_bytes=doc.file_size_bytes,
                    ocr_engine=ocr_engine,
                )

                citation_metadata = {
                    "document_number": admin_meta.get("document_number") or doc.document_number,
                    "issued_date": str(admin_meta.get("issued_date") or doc.issued_date)
                    if (admin_meta.get("issued_date") or doc.issued_date)
                    else None,
                    "issuing_authority": admin_meta.get("issuing_authority") or doc.issuing_authority,
                    "document_type_code": admin_meta.get("document_type_code") or doc.document_type_code,
                    "subject": admin_meta.get("title"),
                    "signer_name": admin_meta.get("signer"),
                }
                structured_artifact = build_source_artifact(
                    clean_md, parsed_page_count, citation_metadata, extraction.canonical_tables,
                )
                temporal_metadata = extract_temporal_metadata(clean_md, item.origin_file_name)
                structured_artifact["temporal_metadata"] = temporal_metadata
                citation_metadata["issued_date"] = temporal_metadata["issued_date"]["value"]
                if any(page.get("has_tables") for page in ocr_pages) and not structured_artifact["tables"]:
                    structured_artifact["issues"].append({"code": "TABLES_NOT_MATERIALIZED"})
                    structured_artifact["review"] = {"status": "required"}
                if structured_artifact["issues"] and quality_report.get("overall_status") != "failed":
                    quality_report = {**quality_report, "overall_status": "warning",
                                      "structured_issues": structured_artifact["issues"]}

            # 6. Instantiate KnowledgeSourceRevision
            await report_progress("chunk", 85)
            source_rev_id = f"ks_rev_{uuid.uuid4().hex[:12]}"
            source_rev = KnowledgeSourceRevision(
                id=source_rev_id,
                binding_id=binding.id,
                revision_no=next_rev_no,
                origin_document_id=doc.id,
                origin_file_hash=item.origin_file_hash,
                snapshot_storage_path=snapshot_path,
                snapshot_metadata={**dict(item.origin_metadata or {}), "title": item.origin_title,
                                   "file_name": item.origin_file_name, "file_type": item.origin_file_type,
                                   "preview_pdf_path": preview_path},
                canonical_markdown=clean_md,
                canonical_hash=canonical_hash,
                page_manifest=page_manifest,
                citation_metadata=citation_metadata,
                parse_provenance={
                    "parser_profile": parser_profile,
                    "ocr_engine": ocr_engine or "native",
                    "reused_artifact": reused_artifact,
                    "ingested_at": datetime.now(UTC).isoformat(),
                    "structured_artifact": structured_artifact,
                    "ocr_config_hash": ocr_config_hash,
                },
                quality_report=quality_report,
                parser_profile_hash=compute_sha256(parser_profile),
                normalizer_version=EXTRACTION_VERSION,
                artifact_key=artifact_key,
                lock_version=1,
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )

            # Persist before queries/flushes of dependent artifacts.
            db.add(source_rev)
            await db.flush()

            # 7. Quality Gate decision & Post-Ingestion chaining
            overall_status = quality_report.get("overall_status", "passed")
            if overall_status == "passed":
                source_rev.status = "ready"
                binding.active_source_revision_id = source_rev.id
                if binding.status != "paused":
                    binding.status = "active"

                # 7a. Materialize Chunks via ChunkSetService
                from app.modules.knowledge.services.chunk_set_service import chunk_set_service

                await chunk_set_service.get_or_create_chunk_set(
                    db=db,
                    source_revision_id=source_rev.id,
                    chunk_strategy=batch.chunk_strategy or "ClauseBasedChunker",
                    chunk_config=batch.chunk_config or {},
                )

                # 7b. Automatically build staging vector index revision if batch targets a vector generation
                if batch.vector_generation_id:
                    from app.modules.knowledge.services.vector_generation_service import (
                        vector_generation_service,
                    )

                    item.phase = "embed"
                    await report_progress("embed", 90)
                    item.knowledge_source_revision_id = source_rev.id
                    await db.commit()
                    await vector_generation_service.build_generation_for_source(
                        db=db,
                        collection_id=batch.collection_id,
                        generation_id=batch.vector_generation_id,
                        binding_id=binding.id,
                        chunk_strategy=batch.chunk_strategy or "ClauseBasedChunker",
                        chunk_config=batch.chunk_config or {},
                    )
                await self._check_cancelled(db, batch)
                item.status = "succeeded"
                await report_progress("completed", 99)
                item.phase = "completed"
                batch.succeeded_count += 1
            elif overall_status == "warning":
                source_rev.status = "review_required"
                item.status = "review_required"
                item.phase = "validate"
                batch.review_required_count += 1
            else:
                source_rev.status = "failed"
                source_rev.failure_code = quality_report.get("failure_code", "QUALITY_GATE_FAILED")
                source_rev.failure_detail = (
                    f"Quality gate rejected document: {quality_report.get('warning_flags')}"
                )
                item.status = "failed"
                item.phase = "failed"
                item.failure_code = source_rev.failure_code
                item.failure_detail = source_rev.failure_detail
                batch.failed_count += 1

            item.knowledge_source_revision_id = source_rev.id

        except Exception as exc:
            logger.exception("Failed to ingest import item %s", item_id)
            if db.is_active is False:
                await db.rollback()
                await db.refresh(item)
                await db.refresh(batch)
            item.status = "skipped" if getattr(exc, "code", "") == "IMPORT_CANCELLED" else "failed"
            item.phase = "failed"
            item.failure_code = getattr(exc, "code", getattr(exc, "error_code", "INGESTION_ERROR"))
            item.failure_detail = str(exc)
            batch.failed_count += 1
            raise
        finally:
            batch.processing_count = max(0, batch.processing_count - 1)
            # Update batch terminal status if completed
            if batch.status != "cancelled" and batch.queued_count == 0 and batch.processing_count == 0:
                if batch.failed_count > 0:
                    batch.status = "partial_failed"
                elif batch.review_required_count > 0:
                    batch.status = "review_required"
                else:
                    batch.status = "completed"

            await db.commit()
            from app.modules.knowledge.services.import_state_service import refresh_batch_counts

            await refresh_batch_counts(db, batch.id)

        await db.refresh(source_rev)
        return source_rev

    @staticmethod
    async def _check_cancelled(db: AsyncSession, batch: KnowledgeImportBatch) -> None:
        await db.refresh(batch, attribute_names=["status"])
        if batch.status == "cancelled":
            raise AppException("Đợt nạp đã bị hủy.", code="IMPORT_CANCELLED", status_code=409)

    async def get_source(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
    ) -> KnowledgeBinding:
        """Fetch a knowledge source entity with active revision and all historical revisions."""
        res = await db.execute(
            select(KnowledgeBinding)
            .options(
                selectinload(KnowledgeBinding.active_source_revision),
                selectinload(KnowledgeBinding.source_revisions),
            )
            .where(
                KnowledgeBinding.id == source_id,
                KnowledgeBinding.collection_id == collection_id,
                KnowledgeBinding.tenant_id == tenant_id,
                KnowledgeBinding.workspace_id == workspace_id,
                KnowledgeBinding.status.notin_(["detached", "deleting"]),
            )
        )
        binding = res.scalar_one_or_none()
        if not binding:
            raise AppException(
                message=f"Không tìm thấy nguồn tri thức {source_id}",
                code="SOURCE_NOT_FOUND",
                status_code=404,
            )
        return binding

    async def get_source_revisions(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
    ) -> list[KnowledgeSourceRevision]:
        """List all revisions of a specific knowledge source."""
        binding = await self.get_source(db, collection_id, source_id, tenant_id, workspace_id)
        res = await db.execute(
            select(KnowledgeSourceRevision)
            .where(KnowledgeSourceRevision.binding_id == binding.id)
            .order_by(KnowledgeSourceRevision.revision_no.desc())
        )
        return list(res.scalars().all())

    async def update_revision_content(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        revision_id: str,
        new_markdown: str,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        context_edits: Any | None = None,
        actor_id: str | None = None,
    ) -> KnowledgeSourceRevision:
        """Update and re-evaluate canonical Markdown content for a source revision."""
        from app.modules.knowledge.services.source_reparse import ensure_source_idle, lock_source
        await lock_source(db, source_id)
        await ensure_source_idle(db, source_id)
        binding = await self.get_source(db, collection_id, source_id, tenant_id, workspace_id)
        rev_res = await db.execute(
            select(KnowledgeSourceRevision).where(
                KnowledgeSourceRevision.id == revision_id,
                KnowledgeSourceRevision.binding_id == binding.id,
            )
        )
        rev = rev_res.scalar_one_or_none()
        if not rev:
            raise AppException(
                message=f"Không tìm thấy bản sửa đổi nguồn {revision_id}",
                code="SOURCE_REVISION_NOT_FOUND",
                status_code=404,
            )

        if context_edits is not None and get_source_artifact(rev)["fact_set_hash"] != context_edits.expected_fact_set_hash:
            raise AppException("Facts đã thay đổi; hãy tải lại bản nguồn.", code="SOURCE_CONTEXT_CHANGED", status_code=409)

        clean_md, page_manifest = normalize_source_pages(new_markdown, manifest_page_count(rev.page_manifest))
        quality_report = evaluate_revision_quality(
            markdown=clean_md,
            page_count=len(rev.page_manifest) or 1,
            tables_count=0,
            file_size_bytes=len(clean_md.encode("utf-8")),
        )

        # Never edit an artifact that published vectors or another model reuse.
        revision_no = (await db.execute(
            select(KnowledgeSourceRevision.revision_no)
            .where(KnowledgeSourceRevision.binding_id == binding.id)
            .order_by(KnowledgeSourceRevision.revision_no.desc())
        )).scalars().first() or rev.revision_no
        if context_edits is not None and revision_no != rev.revision_no:
            raise AppException("Đã có revision mới hơn; hãy mở bản mới nhất.", code="SOURCE_CONTEXT_CHANGED", status_code=409)
        values = {
            col.key: getattr(rev, col.key)
            for col in KnowledgeSourceRevision.__table__.columns
            if col.key not in {"id", "revision_no", "created_at", "updated_at"}
        }
        new_rev = KnowledgeSourceRevision(
            **values, id=f"ks_rev_{uuid.uuid4().hex[:12]}", revision_no=revision_no + 1,
        )
        new_rev.artifact_key = compute_sha256(f"{new_rev.origin_file_hash}:edited:{compute_sha256(clean_md)}")
        new_rev.canonical_markdown = clean_md
        new_rev.page_manifest = merge_edited_manifest(list(rev.page_manifest or []), page_manifest)
        new_rev.normalizer_version = EXTRACTION_VERSION
        new_rev.canonical_hash = compute_sha256(clean_md)
        new_rev.citation_metadata = {
            **{key: value for key, value in (rev.snapshot_metadata or {}).items()
               if key in {"document_number", "issued_date", "issuing_authority", "document_type_code"}},
            **extract_administrative_metadata(clean_md),
        }
        new_rev.citation_metadata = {key: str(value) if value is not None else None
                                    for key, value in new_rev.citation_metadata.items()}
        new_rev.citation_metadata["subject"] = new_rev.citation_metadata.pop("title", None)
        new_rev.citation_metadata["signer_name"] = new_rev.citation_metadata.pop("signer", None)
        artifact = build_source_artifact(clean_md, manifest_page_count(new_rev.page_manifest), new_rev.citation_metadata)
        artifact["temporal_metadata"] = extract_temporal_metadata(clean_md, (new_rev.snapshot_metadata or {}).get("file_name", ""))
        new_rev.citation_metadata["issued_date"] = artifact["temporal_metadata"]["issued_date"]["value"]
        if context_edits is not None:
            from app.modules.knowledge.services.source_context import apply_context_edits

            if not actor_id:
                raise AppException("Hiệu đính thiếu định danh người sửa.", code="CONTEXT_ACTOR_REQUIRED", status_code=422)
            artifact = apply_context_edits(artifact, context_edits, actor_id, base_artifact=get_source_artifact(rev))
            new_rev.citation_metadata["issued_date"] = artifact["temporal_metadata"]["issued_date"]["value"]
            new_rev.artifact_key = compute_sha256(f"{new_rev.origin_file_hash}:context:{artifact['fact_set_hash']}:{new_rev.id}")
        quality_report = evaluate_revision_quality(markdown=clean_md, page_count=manifest_page_count(new_rev.page_manifest) or 1,
                                                   tables_count=len(artifact["tables"]), file_size_bytes=len(clean_md.encode("utf-8")))
        new_rev.parse_provenance = {**(rev.parse_provenance or {}), "structured_artifact": artifact,
                                    "edited_from_revision_id": rev.id}
        if artifact["issues"] and quality_report.get("overall_status") != "failed":
            quality_report = {**quality_report, "overall_status": "warning", "structured_issues": artifact["issues"]}
        if context_edits is not None and quality_report.get("overall_status") != "failed":
            quality_report = {**quality_report, "overall_status": "warning", "context_review_required": True}
        new_rev.quality_report = quality_report
        new_rev.updated_at = datetime.now(UTC)

        overall_status = quality_report.get("overall_status", "passed")
        if overall_status == "passed":
            new_rev.status = "ready"
        elif overall_status == "warning":
            new_rev.status = "review_required"
        else:
            new_rev.status = "failed"

        db.add(new_rev)
        await db.flush()

        if overall_status == "passed":
            await db.execute(
                update(KnowledgeBinding)
                .where(KnowledgeBinding.id == binding.id)
                .values(
                    active_source_revision_id=new_rev.id,
                    status="paused" if binding.status == "paused" else "active",
                    updated_at=datetime.now(UTC),
                )
            )
        await db.commit()
        await db.refresh(new_rev)
        return new_rev

    async def review_source_revision(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        revision_id: str,
        decision: str,
        comment: str | None = None,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        actor_id: str | None = None,
    ) -> KnowledgeSourceRevision:
        """Approve or reject a review_required source revision."""
        from app.modules.knowledge.services.source_reparse import ensure_source_idle, lock_source
        await lock_source(db, source_id)
        await ensure_source_idle(db, source_id)
        binding = await self.get_source(db, collection_id, source_id, tenant_id, workspace_id)
        rev_res = await db.execute(
            select(KnowledgeSourceRevision).where(
                KnowledgeSourceRevision.id == revision_id,
                KnowledgeSourceRevision.binding_id == binding.id,
            )
        )
        rev = rev_res.scalar_one_or_none()
        if not rev:
            raise AppException(
                message=f"Không tìm thấy bản sửa đổi nguồn {revision_id}",
                code="SOURCE_REVISION_NOT_FOUND",
                status_code=404,
            )

        if rev.status != "review_required":
            raise AppException("Chỉ duyệt bản đang chờ kiểm duyệt.", code="SOURCE_NOT_REVIEWABLE", status_code=409)

        artifact = get_source_artifact(rev)
        if artifact.get("context_audit") and not actor_id:
            raise AppException("Duyệt ngữ cảnh thiếu người duyệt.", code="CONTEXT_ACTOR_REQUIRED", status_code=422)

        if decision == "approved":
            rev.status = "ready"
            rev.failure_code = None
            rev.failure_detail = None
            binding.active_source_revision_id = rev.id
            if binding.status != "paused":
                binding.status = "active"
        elif decision == "rejected":
            rev.status = "failed"
            rev.failure_code = "HUMAN_REVIEW_REJECTED"
            rev.failure_detail = comment or "Cán bộ quản trị đã từ chối bản bóc tách này."
        else:
            raise AppException(
                message="Quyết định duyệt chỉ chấp nhận 'approved' hoặc 'rejected'",
                code="INVALID_DECISION",
                status_code=400,
            )

        rev.updated_at = datetime.now(UTC)
        if artifact.get("context_audit"):
            from app.modules.knowledge.services.source_context import review_context_artifact

            artifact = review_context_artifact(artifact, decision, actor_id, comment)
        artifact["review"] = {"status": decision, "comment": comment, "at": rev.updated_at.isoformat(), "actor_id": actor_id}
        rev.parse_provenance = {**(rev.parse_provenance or {}), "structured_artifact": artifact}
        await db.commit()
        await db.refresh(rev)
        return rev

    async def get_source_studio_data(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        revision_id: str | None = None,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
    ) -> Any:
        """Fetch full Studio OCR verification data for split-screen inspection."""
        from app.modules.knowledge.schemas import (
            StudioBox,
            StudioPageView,
            StudioRegion,
            StudioViewResponse,
        )
        from app.modules.knowledge.services.source_pages import canonical_pages

        binding = await self.get_source(db, collection_id, source_id, tenant_id, workspace_id)
        if revision_id:
            rev_res = await db.execute(
                select(KnowledgeSourceRevision).where(
                    KnowledgeSourceRevision.id == revision_id,
                    KnowledgeSourceRevision.binding_id == binding.id,
                )
            )
            rev = rev_res.scalar_one_or_none()
        else:
            rev = binding.active_source_revision
            if not rev:
                latest_rev_res = await db.execute(
                    select(KnowledgeSourceRevision)
                    .where(KnowledgeSourceRevision.binding_id == binding.id)
                    .order_by(KnowledgeSourceRevision.revision_no.desc())
                )
                rev = latest_rev_res.scalars().first()

        if not rev:
            raise AppException(
                "Chưa có bản bóc tách nào cho nguồn tài liệu này.",
                code="NO_SOURCE_REVISION",
                status_code=404,
            )

        manifest = list(rev.page_manifest or [])
        pages_content = canonical_pages(rev.canonical_markdown or "", len(manifest) or 1)

        pages_views: list[StudioPageView] = []
        for idx, entry in enumerate(manifest):
            page_num = entry.get("page") or entry.get("page_number") or (idx + 1)
            content = ""
            for pc in pages_content:
                if pc.get("page_number") == page_num or (pc.get("page_number") is None and idx == 0):
                    content = pc.get("markdown_content", "")
                    break

            blocks = entry.get("blocks") or []
            boxes: list[StudioBox] = []
            regions: list[StudioRegion] = []
            for b_idx, block in enumerate(blocks):
                coords = block.get("coordinates") or {"is_valid": False}
                reading_order = block.get("order")
                if reading_order is None:
                    reading_order = block.get("reading_order")
                if reading_order is None:
                    reading_order = b_idx + 1
                layout_conf = block.get("layout_confidence")
                text_conf = block.get("text_confidence")
                boxes.append(
                    StudioBox(
                        id=str(block.get("id") or f"box_{page_num}_{b_idx}"),
                        page_number=page_num,
                        type=str(block.get("type", "text")),
                        coordinates=coords,
                        label=str(block.get("type", "text")),
                        confidence=float(layout_conf or 0.0),
                        layout_confidence=float(layout_conf) if layout_conf is not None else None,
                        text_confidence=float(text_conf) if text_conf is not None else None,
                        confidence_source=str(block.get("confidence_source", "unavailable")),
                        content_snippet=str(block.get("text", ""))[:140],
                    )
                )
                regions.append(
                    StudioRegion(
                        id=str(block.get("id") or f"reg_{page_num}_{b_idx}"),
                        page_number=page_num,
                        title=f"Vùng #{reading_order}: {block.get('type', 'text')}",
                        type=str(block.get("type", "text")),
                        confidence=float(layout_conf or 0.0),
                        layout_confidence=float(layout_conf) if layout_conf is not None else None,
                        text_confidence=float(text_conf) if text_conf is not None else None,
                        reading_order=int(reading_order),
                        details=str(block.get("text", "")),
                        coordinates=coords,
                    )
                )

            image_url = (
                f"/platform/v1alpha1/knowledge/collections/{collection_id}"
                f"/sources/{source_id}/pages/{page_num}/image?revision_id={rev.id}"
            )
            words = len(content.split())
            lines = len([l for l in content.split("\n") if l.strip()])
            pages_views.append(
                StudioPageView(
                    page_number=page_num,
                    markdown_content=content,
                    raw_text=content,
                    word_count=words,
                    line_count=lines,
                    image_url=image_url,
                    dimensions=entry.get("dimensions"),
                    has_tables=bool(entry.get("has_tables", False)),
                    bounding_boxes=boxes,
                    regions=regions,
                )
            )

        title = (
            (rev.snapshot_metadata or {}).get("title")
            or getattr(binding, "source_document_title", None)
            or "Tài liệu"
        )
        filename = (rev.snapshot_metadata or {}).get("file_name") or f"{title}.pdf"

        return StudioViewResponse(
            document_id=source_id,
            revision_id=rev.id,
            collection_id=collection_id,
            title=title,
            filename=filename,
            engine=str((rev.parse_provenance or {}).get("ocr_engine", "native")),
            status=rev.status,
            index_status=binding.status,
            total_pages=len(pages_views) or 1,
            file_size_bytes=len((rev.canonical_markdown or "").encode("utf-8")),
            total_chunks=0,
            structured_artifact=get_source_artifact(rev),
            source_metadata=rev.snapshot_metadata or {},
            citation_metadata=rev.citation_metadata or {},
            layout_text_alignment="stale" if any(p.get("layout_text_alignment") == "stale" for p in manifest) else "original",
            pages=pages_views,
        )

    async def get_source_page_image(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        page_number: int,
        revision_id: str | None = None,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
    ) -> tuple[bytes, str]:
        """Render high-resolution JPEG of a specific page directly from isolated snapshot."""
        binding = await self.get_source(db, collection_id, source_id, tenant_id, workspace_id)
        if revision_id:
            rev_res = await db.execute(
                select(KnowledgeSourceRevision).where(
                    KnowledgeSourceRevision.id == revision_id,
                    KnowledgeSourceRevision.binding_id == binding.id,
                )
            )
            rev = rev_res.scalar_one_or_none()
        else:
            rev = binding.active_source_revision
            if not rev:
                latest_rev_res = await db.execute(
                    select(KnowledgeSourceRevision)
                    .where(KnowledgeSourceRevision.binding_id == binding.id)
                    .order_by(KnowledgeSourceRevision.revision_no.desc())
                )
                rev = latest_rev_res.scalars().first()

        if not rev or not rev.snapshot_storage_path:
            raise AppException(
                "Không tìm thấy snapshot tệp gốc cho bản sửa đổi này.",
                code="SNAPSHOT_NOT_FOUND",
                status_code=404,
            )

        file_bytes = await storage_service.get(rev.snapshot_storage_path)
        if not file_bytes:
            raise AppException(
                "Không thể đọc tệp snapshot từ kho lưu trữ.",
                code="SNAPSHOT_READ_FAILED",
                status_code=404,
            )
        filename = ((rev.snapshot_metadata or {}).get("file_name") or "").lower()
        if filename.endswith(".docx"):
            preview_path = (rev.snapshot_metadata or {}).get("preview_pdf_path")
            preview = await storage_service.get(preview_path) if preview_path else None
            if not preview:
                raise AppException("Nguồn chưa có PDF xem trước; hãy bóc tách lại bằng worker.",
                                   code="SOURCE_PREVIEW_UNAVAILABLE", status_code=409)
            file_bytes = preview

        if filename.endswith(".pdf") or file_bytes.startswith(b"%PDF"):
            import pymupdf

            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            if page_number < 1 or page_number > len(doc):
                raise AppException(
                    f"Số trang {page_number} không hợp lệ (tổng số trang: {len(doc)}).",
                    code="PAGE_NOT_FOUND",
                    status_code=404,
                )
            page = doc.load_page(page_number - 1)
            pix = page.get_pixmap(dpi=150)
            return pix.tobytes("jpeg"), "image/jpeg"
        elif filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
            if page_number != 1:
                raise AppException(
                    "Tài liệu ảnh đơn chỉ có trang 1.",
                    code="PAGE_NOT_FOUND",
                    status_code=404,
                )
            media_type = "image/png" if filename.endswith(".png") else "image/jpeg"
            return file_bytes, media_type
        else:
            raise AppException(
                f"Định dạng tệp '{filename}' không hỗ trợ kết xuất ảnh đối chiếu trang.",
                code="UNSUPPORTED_PAGE_IMAGE",
                status_code=400,
            )

    async def reparse_source(
        self, db: AsyncSession, collection_id: str, source_id: str,
        parser_profile: str = "vision_ocr", ocr_engine: str | None = None,
        tenant_id: str = "tenant_qnu", workspace_id: str = "workspace_qnu",
    ) -> KnowledgeSourceRevision:
        from app.modules.knowledge.services.source_reparse import queue_reparse
        return await queue_reparse(db, collection_id, source_id, parser_profile, ocr_engine, tenant_id, workspace_id)

    async def execute_reparse(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        parser_profile: str = "vision_ocr",
        ocr_engine: str | None = None,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        reserved_revision_id: str | None = None,
        job_id: str | None = None,
    ) -> KnowledgeSourceRevision:
        """Reparse an existing source using isolated snapshot storage with strict anti-duplicate locking."""
        binding = await self.get_source(db, collection_id, source_id, tenant_id, workspace_id)

        # 1. Anti-duplicate run invariant
        extracting_check = await db.execute(
            select(KnowledgeSourceRevision.id).where(
                KnowledgeSourceRevision.binding_id == binding.id,
                KnowledgeSourceRevision.status.in_(["extracting", "queued"]),
            )
        )
        if extracting_check.scalars().first() and not reserved_revision_id:
            raise AppException(
                "Nguồn tài liệu đang có tiến trình bóc tách đang thực thi. Vui lòng chờ hoàn tất.",
                code="REPARSE_ALREADY_IN_PROGRESS",
                status_code=409,
            )

        # 2. Retrieve base snapshot
        current_rev = binding.active_source_revision
        if not current_rev:
            all_revs = await self.get_source_revisions(db, collection_id, source_id, tenant_id, workspace_id)
            if all_revs:
                current_rev = all_revs[0]

        if not current_rev or not current_rev.snapshot_storage_path:
            raise AppException(
                "Không tìm thấy snapshot tệp gốc độc lập để thực hiện bóc tách lại.",
                code="SNAPSHOT_NOT_FOUND",
                status_code=404,
            )

        file_bytes = await storage_service.get(current_rev.snapshot_storage_path)
        if not file_bytes:
            raise AppException(
                "Không thể đọc tệp snapshot từ kho lưu trữ để bóc tách lại.",
                code="SNAPSHOT_READ_FAILED",
                status_code=404,
            )
        filename = (
            (current_rev.snapshot_metadata or {}).get("file_name")
            or getattr(binding, "source_document_title", None)
            or "document.pdf"
        )
        file_type = (current_rev.snapshot_metadata or {}).get("file_type") or filename.rsplit(".", 1)[-1].lower()

        # 3. Next revision number
        latest_rev_no_res = await db.execute(
            select(KnowledgeSourceRevision.revision_no)
            .where(KnowledgeSourceRevision.binding_id == binding.id)
            .order_by(KnowledgeSourceRevision.revision_no.desc())
        )
        latest_no = latest_rev_no_res.scalars().first() or current_rev.revision_no
        next_rev_no = latest_no + 1

        # 4. Perform extraction
        extraction = await extract_source(db, file_bytes, filename, file_type,
                                          parser_profile, ocr_engine, tenant_id)
        preview_path = await save_source_preview(current_rev.snapshot_storage_path, extraction)
        raw_text, parsed_page_count, ocr_pages = extraction.raw_text, extraction.page_count, extraction.pages
        parsed_tables_count = len(extraction.tables)
        ocr_engine = extraction.engine_used

        if not raw_text.strip():
            raise AppException(
                message=f"Không thể bóc tách nội dung văn bản từ tệp '{filename}'.",
                code="EMPTY_EXTRACTED_TEXT",
                status_code=422,
            )

        clean_md, page_manifest = normalize_source_pages(raw_text, parsed_page_count, ocr_pages)
        canonical_hash = compute_sha256(clean_md)
        admin_meta = extract_administrative_metadata(clean_md)

        quality_report = evaluate_revision_quality(
            markdown=clean_md,
            page_count=parsed_page_count,
            tables_count=parsed_tables_count,
            file_size_bytes=len(file_bytes),
            ocr_engine=ocr_engine,
        )

        citation_metadata = {
            "document_number": admin_meta.get("document_number")
            or (current_rev.citation_metadata or {}).get("document_number"),
            "issued_date": str(
                admin_meta.get("issued_date")
                or (current_rev.citation_metadata or {}).get("issued_date")
                or ""
            ) or None,
            "issuing_authority": admin_meta.get("issuing_authority")
            or (current_rev.citation_metadata or {}).get("issuing_authority"),
            "document_type_code": admin_meta.get("document_type_code")
            or (current_rev.citation_metadata or {}).get("document_type_code"),
        }

        temporal_metadata = extract_temporal_metadata(clean_md, filename)
        citation_metadata["issued_date"] = temporal_metadata["issued_date"]["value"]
        citation_metadata["subject"] = admin_meta.get("title")
        citation_metadata["signer_name"] = admin_meta.get("signer")
        structured_artifact = build_source_artifact(clean_md, parsed_page_count, citation_metadata, extraction.canonical_tables)
        structured_artifact["temporal_metadata"] = temporal_metadata
        if structured_artifact["issues"] and quality_report.get("overall_status") != "failed":
            quality_report = {**quality_report, "overall_status": "warning", "structured_issues": structured_artifact["issues"]}

        new_rev_id = reserved_revision_id or f"ks_rev_{uuid.uuid4().hex[:12]}"
        new_rev = KnowledgeSourceRevision(
            id=new_rev_id,
            binding_id=binding.id,
            revision_no=next_rev_no,
            origin_document_id=current_rev.origin_document_id,
            origin_file_hash=current_rev.origin_file_hash,
            snapshot_storage_path=current_rev.snapshot_storage_path,
            snapshot_metadata={**dict(current_rev.snapshot_metadata or {}), "preview_pdf_path": preview_path},
            canonical_markdown=clean_md,
            canonical_hash=canonical_hash,
            page_manifest=page_manifest,
            citation_metadata=citation_metadata,
            parse_provenance={
                "parser_profile": parser_profile,
                "ocr_engine": ocr_engine or "auto",
                "reparsed_at": datetime.now(UTC).isoformat(),
                "structured_artifact": structured_artifact,
            },
            quality_report=quality_report,
            parser_profile_hash=compute_sha256(parser_profile),
            normalizer_version=EXTRACTION_VERSION,
            artifact_key=compute_sha256(f"{current_rev.origin_file_hash}:{parser_profile}:{EXTRACTION_VERSION}"),
            lock_version=1,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )

        if reserved_revision_id:
            reserved = await db.get(KnowledgeSourceRevision, reserved_revision_id)
            for col in KnowledgeSourceRevision.__table__.columns:
                if col.key not in {"id", "revision_no", "created_at", "updated_at", "status"}:
                    setattr(reserved, col.key, getattr(new_rev, col.key))
            new_rev = reserved
        else:
            db.add(new_rev)
        overall_status = quality_report.get("overall_status", "passed")
        from app.modules.jobs.service import is_job_cancelled
        cancelled = bool(job_id and await is_job_cancelled(job_id, db=db))
        if cancelled:
            new_rev.status = "cancelled"
        elif overall_status == "passed":
            new_rev.status = "ready"
            binding.active_source_revision_id = new_rev.id
            if binding.status != "paused":
                binding.status = "active"
        elif overall_status == "warning":
            new_rev.status = "review_required"
        else:
            new_rev.status = "failed"
            new_rev.failure_code = quality_report.get("failure_code", "QUALITY_GATE_FAILED")
            new_rev.failure_detail = f"Quality gate rejected document: {quality_report.get('warning_flags')}"

        await db.commit()
        await db.refresh(new_rev)
        return new_rev


source_ingestion_service = SourceIngestionService()
