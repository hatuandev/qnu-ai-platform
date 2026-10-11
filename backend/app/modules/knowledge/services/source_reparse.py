"""Durable reparse requests: reserve a revision atomically before dispatch."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import enqueue_arq_job
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision


async def lock_source(db: AsyncSession, source_id: str) -> None:
    await db.execute(
        select(KnowledgeBinding.id).where(KnowledgeBinding.id == source_id).with_for_update()
    )


async def ensure_source_idle(db: AsyncSession, source_id: str) -> None:
    pending = await db.execute(
        select(KnowledgeSourceRevision.id)
        .where(
            KnowledgeSourceRevision.binding_id == source_id,
            KnowledgeSourceRevision.status.in_(
                ["queued", "extracting", "normalizing", "validating"]
            ),
        )
        .limit(1)
    )
    if pending.scalar_one_or_none():
        raise AppException(
            "Nguồn đang bóc tách; vui lòng chờ hoàn tất.",
            code="REPARSE_ALREADY_IN_PROGRESS",
            status_code=409,
        )


async def queue_reparse(
    db: AsyncSession,
    collection_id: str,
    source_id: str,
    parser_profile: str,
    ocr_engine: str | None,
    tenant_id: str,
    workspace_id: str,
) -> KnowledgeSourceRevision:
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

    await lock_source(db, source_id)
    binding = await source_ingestion_service.get_source(
        db, collection_id, source_id, tenant_id, workspace_id
    )
    await ensure_source_idle(db, source_id)
    base = binding.active_source_revision
    if not base:
        revisions = await source_ingestion_service.get_source_revisions(
            db, collection_id, source_id, tenant_id, workspace_id
        )
        base = revisions[0] if revisions else None
    if not base or not base.snapshot_storage_path:
        raise AppException(
            "Không tìm thấy snapshot độc lập.", code="SNAPSHOT_NOT_FOUND", status_code=404
        )
    number = (
        await db.execute(
            select(func.max(KnowledgeSourceRevision.revision_no)).where(
                KnowledgeSourceRevision.binding_id == source_id
            )
        )
    ).scalar() or 0
    revision = KnowledgeSourceRevision(
        binding_id=source_id,
        revision_no=number + 1,
        origin_document_id=base.origin_document_id,
        origin_file_hash=base.origin_file_hash,
        snapshot_storage_path=base.snapshot_storage_path,
        snapshot_metadata=dict(base.snapshot_metadata or {}),
        status="queued",
        page_manifest=[],
        quality_report={},
        citation_metadata={},
        parse_provenance={"parser_profile": parser_profile, "ocr_engine": ocr_engine or "auto"},
    )
    db.add(revision)
    await db.flush()
    job = JobRecord(
        job_type="knowledge_source_reparse",
        collection_id=collection_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        status="queued",
        payload={
            "source_id": source_id,
            "revision_id": revision.id,
            "parser_profile": parser_profile,
            "ocr_engine": ocr_engine,
        },
    )
    db.add(job)
    await db.commit()
    broker_id = await enqueue_arq_job(
        "task_knowledge_source_reparse", job.id, broker_job_id=f"reparse_{job.id}"
    )
    if broker_id:
        job.arq_job_id, job.dispatch_status = broker_id, "dispatched"
        await db.commit()
    await db.refresh(revision)
    return revision


async def run_reparse(db: AsyncSession, job: JobRecord) -> KnowledgeSourceRevision:
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

    payload = dict(job.payload)
    collection_id, tenant_id, workspace_id = job.collection_id, job.tenant_id, job.workspace_id
    job_id = job.id
    revision = (
        await db.execute(
            select(KnowledgeSourceRevision)
            .where(
                KnowledgeSourceRevision.id == payload["revision_id"],
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if not revision:
        raise AppException(
            "Không tìm thấy bản bóc tách.", code="SOURCE_REVISION_NOT_FOUND", status_code=404
        )
    if revision.status in ("ready", "review_required", "failed", "cancelled"):
        return revision
    revision.status = "extracting"
    revision.started_at = datetime.now(UTC)
    try:
        return await source_ingestion_service.execute_reparse(
            db,
            collection_id,
            payload["source_id"],
            parser_profile=payload["parser_profile"],
            ocr_engine=payload.get("ocr_engine"),
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            reserved_revision_id=revision.id,
            job_id=job_id,
        )
    except Exception as exc:
        await db.rollback()
        revision = await db.get(KnowledgeSourceRevision, payload["revision_id"])
        revision.status = "failed"
        revision.failure_code = getattr(exc, "code", "OCR_REPARSE_FAILED")
        revision.failure_detail = str(exc)[:500]
        revision.finished_at = datetime.now(UTC)
        await db.commit()
        raise
