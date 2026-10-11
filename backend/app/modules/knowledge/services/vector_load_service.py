"""Reserve selected Markdown revisions for durable ARQ vector loading."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import enqueue_arq_job, jobs_service
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.schemas import VectorLoadRequest
from app.modules.knowledge.services.scope_helper import get_scoped_collection
from app.modules.knowledge.services.vector_generation_service import vector_generation_service


async def queue_vector_load(
    db: AsyncSession, collection_id: str, request: VectorLoadRequest, actor: Any,
) -> list[JobRecord]:
    """Validate the entire selection before committing; retries reuse pending jobs."""
    collection = await get_scoped_collection(db, collection_id, actor=actor, for_update=True)
    generation = await vector_generation_service.get_vector_generation(
        db, collection_id, request.generation_id, actor=actor,
    )
    if generation.status not in ("building", "ready", "active"):
        raise AppException("Chỉ mục này đã lưu trữ; hãy tạo chỉ mục mới.", code="GENERATION_RETIRED", status_code=409)
    jobs: list[JobRecord] = []
    selected = {item.binding_id: item.source_revision_id for item in request.items}
    if len(selected) != len(request.items):
        raise AppException("Nguồn bị chọn trùng.", code="DUPLICATE_SOURCE_SELECTION", status_code=422)
    for binding_id, revision_id in selected.items():
        binding = await db.scalar(select(KnowledgeBinding).where(
            KnowledgeBinding.id == binding_id, KnowledgeBinding.collection_id == collection_id,
            KnowledgeBinding.tenant_id == collection.tenant_id,
            KnowledgeBinding.workspace_id == collection.workspace_id,
        ).with_for_update())
        if not binding or binding.status != "active":
            raise AppException("Nguồn không thuộc kho hoặc không hoạt động.", code="SOURCE_NOT_FOUND", status_code=404)
        revision = await db.get(KnowledgeSourceRevision, revision_id)
        if not revision or revision.binding_id != binding_id or binding.active_source_revision_id != revision_id:
            raise AppException("Markdown đã thay đổi; hãy tải lại.", code="SOURCE_REVISION_CHANGED", status_code=409)
        if revision.status != "ready":
            raise AppException("Markdown chưa đủ điều kiện nạp vector.", code="SOURCE_REVISION_NOT_READY", status_code=409)
        existing = await db.scalar(select(JobRecord).where(
            JobRecord.collection_id == collection_id,
            JobRecord.tenant_id == collection.tenant_id,
            JobRecord.workspace_id == collection.workspace_id,
            JobRecord.job_type == "knowledge_index_build",
            JobRecord.status.in_(["queued", "running"]),
            JobRecord.payload["binding_id"].astext == binding_id,
        ).limit(1))
        if existing:
            if existing.payload.get("generation_id") != request.generation_id or existing.payload.get("source_revision_id") != revision_id:
                raise AppException("Nguồn đang nạp vector khác; hãy chờ hoàn tất.", code="SOURCE_INDEX_BUSY", status_code=409)
            jobs.append(existing)
            continue
        job = JobRecord(
            job_type="knowledge_index_build", collection_id=collection_id, status="queued",
            tenant_id=collection.tenant_id, workspace_id=collection.workspace_id,
            payload={"binding_id": binding_id, "source_revision_id": revision_id,
                     "generation_id": request.generation_id, "chunk_strategy": binding.chunk_strategy},
        )
        db.add(job)
        jobs.append(job)
    await db.commit()
    for job in jobs:
        if job.dispatch_status == "dispatched":
            continue
        broker = await enqueue_arq_job("task_knowledge_index_build", job.id,
                                       broker_job_id=jobs_service._broker_job_id(job))
        if broker:
            job.arq_job_id, job.dispatch_status = broker, "dispatched"
            job.error = None
        else:
            job.error = "Đang chờ kết nối hàng đợi worker."
        await db.commit()
    return jobs


async def get_vector_load_state(db: AsyncSession, collection_id: str, actor: Any) -> dict:
    from app.modules.jobs.schemas import JobResponse
    from app.modules.knowledge.schemas import VectorSourceIndexStatus

    col = await get_scoped_collection(db, collection_id, actor=actor)
    jobs = list((await db.scalars(select(JobRecord).where(
        JobRecord.collection_id == col.id, JobRecord.tenant_id == col.tenant_id,
        JobRecord.workspace_id == col.workspace_id, JobRecord.job_type == "knowledge_index_build",
    ).order_by(JobRecord.created_at.desc()).limit(500))).all())
    indexes = list((await db.scalars(select(KnowledgeIndexRevision).join(
        KnowledgeBinding, KnowledgeIndexRevision.binding_id == KnowledgeBinding.id,
    ).where(
        KnowledgeBinding.collection_id == col.id, KnowledgeBinding.tenant_id == col.tenant_id,
        KnowledgeBinding.workspace_id == col.workspace_id, KnowledgeBinding.status == "active",
        KnowledgeIndexRevision.vector_generation_id.is_not(None),
        KnowledgeIndexRevision.status != "pruned",
    ).order_by((KnowledgeIndexRevision.id == KnowledgeBinding.active_index_revision_id).desc(),
               KnowledgeIndexRevision.revision_no.desc()))).all())
    latest = {}
    for index in indexes:
        key = (index.binding_id, index.vector_generation_id, index.source_revision_v2_id)
        latest.setdefault(key, index)
    return {"jobs": [JobResponse.model_validate(job) for job in jobs],
            "indexes": [VectorSourceIndexStatus.model_validate(index) for index in latest.values()]}
