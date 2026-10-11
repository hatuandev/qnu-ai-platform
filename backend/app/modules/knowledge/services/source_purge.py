"""Durable Knowledge-only deletion; external cleanup precedes the final DB commit."""

from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import enqueue_arq_job, jobs_service
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeChunkSet,
    KnowledgeFact,
    KnowledgeImportBatch,
    KnowledgeImportItem,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.services.scope_helper import get_scoped_binding, get_scoped_collection
from app.modules.knowledge.services.source_reparse import ensure_source_idle
from app.modules.rag.vector_indexer import vector_indexer

PURGE_JOB = "knowledge_source_purge"


async def request_purge(db: AsyncSession, binding_id: str, actor: Any = None) -> JobRecord:
    binding = await get_scoped_binding(db, binding_id, actor=actor, allow_deleting=True)
    collection = await get_scoped_collection(db, binding.collection_id, actor=actor, for_update=True)
    binding = await get_scoped_binding(db, binding_id, actor=actor, for_update=True, allow_deleting=True)
    existing = await db.scalar(select(JobRecord).where(
        JobRecord.job_type == PURGE_JOB, JobRecord.collection_id == collection.id,
        JobRecord.tenant_id == binding.tenant_id, JobRecord.workspace_id == binding.workspace_id,
        JobRecord.payload["binding_id"].astext == binding_id,
    ).order_by(JobRecord.created_at.desc()).limit(1))
    if existing and existing.status in ("queued", "running"):
        return existing
    if existing and existing.status in ("failed", "cancelled"):
        return await jobs_service.retry_job(db, existing.id, actor=actor)
    await ensure_source_idle(db, binding_id)
    busy = await db.scalar(select(KnowledgeImportItem.id).join(KnowledgeImportBatch).where(
        KnowledgeImportBatch.collection_id == collection.id,
        KnowledgeImportItem.origin_document_id == binding.repository_document_id,
        KnowledgeImportItem.status.in_(["queued", "processing"]),
    ).limit(1))
    index_busy = await db.scalar(select(KnowledgeIndexRevision.id).where(
        KnowledgeIndexRevision.binding_id == binding_id,
        KnowledgeIndexRevision.status.in_(["building", "validating"]),
    ).limit(1))
    if busy or index_busy:
        raise AppException("Nguồn đang xử lý; vui lòng chờ hoàn tất.", code="SOURCE_BUSY", status_code=409)
    binding.status = "deleting"
    binding.active_index_revision_id = None
    binding.active_epoch += 1
    collection.index_epoch += 1
    job = JobRecord(job_type=PURGE_JOB, collection_id=collection.id,
                    tenant_id=binding.tenant_id, workspace_id=binding.workspace_id,
                    payload={"binding_id": binding_id})
    db.add(job)
    await db.commit()
    broker_id = await enqueue_arq_job("task_knowledge_source_purge", job.id,
                                     broker_job_id=jobs_service._broker_job_id(job))
    if broker_id:
        job.arq_job_id, job.dispatch_status = broker_id, "dispatched"
        await db.commit()
    await db.refresh(job)
    return job


async def run_purge(db: AsyncSession, job: JobRecord) -> None:
    """Retry-safe cleanup. Never delete Repository rows, paths, or a Qdrant collection."""
    if job.status == "completed":
        return
    collection = await get_scoped_collection(db, job.collection_id, for_update=True)
    binding = await db.scalar(select(KnowledgeBinding).where(
        KnowledgeBinding.id == job.payload["binding_id"],
        KnowledgeBinding.collection_id == job.collection_id,
        KnowledgeBinding.tenant_id == job.tenant_id,
        KnowledgeBinding.workspace_id == job.workspace_id,
    ).with_for_update())
    await db.refresh(job)
    if job.status == "completed":
        return
    if not binding or binding.status != "deleting":
        raise AppException("Nguồn chưa được xác nhận xóa.", code="SOURCE_PURGE_NOT_RESERVED", status_code=409)
    revisions = list((await db.scalars(select(KnowledgeSourceRevision).where(
        KnowledgeSourceRevision.binding_id == binding.id,
    ))).all())
    revision_ids = [r.id for r in revisions]
    chunk_ids = list((await db.scalars(select(KnowledgeChunkSet.id).where(
        KnowledgeChunkSet.source_revision_id.in_(revision_ids),
    ))).all())
    index_ids = list((await db.scalars(select(KnowledgeIndexRevision.id).where(
        KnowledgeIndexRevision.binding_id == binding.id,
    ))).all())
    # A malformed cross-source reference must not be silently cascade-deleted.
    shared = await db.scalar(select(KnowledgeIndexRevision.id).where(
        KnowledgeIndexRevision.binding_id != binding.id,
        or_(KnowledgeIndexRevision.source_revision_v2_id.in_(revision_ids),
            KnowledgeIndexRevision.source_revision_id.in_(revision_ids),
            KnowledgeIndexRevision.chunk_set_id.in_(chunk_ids)),
    ).limit(1))
    shared_pointer = await db.scalar(select(KnowledgeBinding.id).where(
        KnowledgeBinding.id != binding.id,
        or_(KnowledgeBinding.active_source_revision_id.in_(revision_ids),
            KnowledgeBinding.active_index_revision_id.in_(index_ids)),
    ).limit(1))
    if shared or shared_pointer:
        raise AppException("Dữ liệu đang được nguồn khác tham chiếu.", code="SOURCE_ARTIFACT_SHARED", status_code=409)
    namespaces = set((await db.scalars(select(KnowledgeVectorGeneration.qdrant_collection_name).where(
        KnowledgeVectorGeneration.collection_id == collection.id,
        KnowledgeVectorGeneration.tenant_id == job.tenant_id,
        KnowledgeVectorGeneration.workspace_id == job.workspace_id,
    ))).all())
    # Legacy index artifacts can use the collection's default namespace.
    namespaces.add(vector_indexer._get_collection_name(collection.id))
    for namespace in sorted(namespaces):
        await vector_indexer.delete_source_points(collection.id, binding.id, namespace,
                                                 tenant_id=job.tenant_id, workspace_id=job.workspace_id)
    prefix = f"snapshots/{collection.id}/{binding.id}/"
    paths = {r.snapshot_storage_path for r in revisions if r.snapshot_storage_path}
    paths.update((r.snapshot_metadata or {}).get("preview_pdf_path") for r in revisions)
    for path in sorted(p for p in paths if p):
        if not path.startswith(prefix) or ".." in path.split("/") or "\\" in path:
            raise AppException("Đường dẫn snapshot ngoài phạm vi nguồn.", code="UNSAFE_PURGE_PATH", status_code=409)
        referenced = await db.scalar(select(func.count()).select_from(KnowledgeSourceRevision).where(
            or_(KnowledgeSourceRevision.snapshot_storage_path == path,
                KnowledgeSourceRevision.snapshot_metadata["preview_pdf_path"].astext == path),
            KnowledgeSourceRevision.binding_id != binding.id,
        ))
        if not referenced:
            try:
                await storage_service.delete_confirmed(path)
            except Exception as exc:
                raise AppException("Không thể xóa snapshot; tác vụ có thể thử lại.",
                                   code="SOURCE_SNAPSHOT_DELETE_FAILED", status_code=503) from exc
    # External operations are idempotent. Keep DB rows until all of them succeed.
    binding.active_source_revision_id = None
    binding.active_index_revision_id = None
    await db.flush()
    item_filter = or_(
        KnowledgeImportItem.knowledge_binding_id == binding.id,
        KnowledgeImportItem.knowledge_source_revision_id.in_(revision_ids),
    )
    batch_ids = list((await db.scalars(select(KnowledgeImportItem.batch_id).where(item_filter).distinct())).all())
    await db.execute(update(KnowledgeImportItem).where(item_filter).values(knowledge_binding_id=None, knowledge_source_revision_id=None,
              index_revision_id=None, status="skipped", phase="purged",
              failure_code="SOURCE_PURGED", failure_detail=None))
    for model in (KnowledgeChunk, KnowledgeFact):
        await db.execute(delete(model).where(or_(model.binding_id == binding.id,
                                                model.index_revision_id.in_(index_ids))))
    await db.execute(delete(KnowledgeIndexRevision).where(KnowledgeIndexRevision.binding_id == binding.id))
    await db.execute(delete(KnowledgeChunkSet).where(KnowledgeChunkSet.id.in_(chunk_ids)))
    await db.execute(delete(KnowledgeSourceRevision).where(KnowledgeSourceRevision.binding_id == binding.id))
    await db.execute(delete(KnowledgeBinding).where(KnowledgeBinding.id == binding.id))
    for batch_id in batch_ids:
        counts = dict((await db.execute(select(KnowledgeImportItem.status, func.count()).where(
            KnowledgeImportItem.batch_id == batch_id,
        ).group_by(KnowledgeImportItem.status))).all())
        batch = await db.get(KnowledgeImportBatch, batch_id)
        for state in ("queued", "processing", "review_required", "succeeded", "failed", "skipped"):
            setattr(batch, f"{state}_count", counts.get(state, 0))
    job.status, job.phase, job.progress = "completed", "completed", 100
    job.result = {"binding_id": binding.id, "source_revisions_deleted": len(revisions),
                  "chunk_sets_deleted": len(chunk_ids), "repository_preserved": True}
    job.error = None
    await db.commit()
