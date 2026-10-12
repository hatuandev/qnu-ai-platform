"""Stop new retrieval without deleting immutable source/index artifacts."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import KnowledgeIndexRevision
from app.modules.knowledge.schemas import KnowledgeBindingResponse
from app.modules.knowledge.services.binding_service import binding_service
from app.modules.knowledge.services.scope_helper import get_scoped_binding, get_scoped_collection
from app.modules.knowledge.services.source_reparse import ensure_source_idle


async def pause_source(
    db: AsyncSession, binding_id: str, actor: Any | None = None,
) -> KnowledgeBindingResponse:
    binding = await get_scoped_binding(db, binding_id, actor=actor)
    collection = await get_scoped_collection(db, binding.collection_id, actor=actor, for_update=True)
    binding = await get_scoped_binding(db, binding_id, actor=actor, for_update=True)
    if binding.status == "paused":
        return await binding_service.get_binding(db, binding_id, actor=actor)
    if binding.status not in ("active", "pending"):
        raise AppException("Nguồn không hoạt động.", code="SOURCE_NOT_ACTIVE", status_code=409)
    await ensure_source_idle(db, binding_id)
    index = await db.scalar(select(KnowledgeIndexRevision.id).where(
        KnowledgeIndexRevision.binding_id == binding_id,
        KnowledgeIndexRevision.status.in_(["building", "validating"]),
    ).limit(1))
    job = await db.scalar(select(JobRecord.id).where(
        JobRecord.collection_id == collection.id,
        JobRecord.tenant_id == collection.tenant_id,
        JobRecord.workspace_id == collection.workspace_id,
        JobRecord.status.in_(["queued", "running"]),
        JobRecord.payload["binding_id"].astext == binding_id,
    ).limit(1))
    if index or job:
        raise AppException("Nguồn đang xử lý; hãy chờ hoàn tất.", code="SOURCE_INDEX_BUSY", status_code=409)
    binding.status = "paused"
    binding.active_epoch += 1
    collection.index_epoch += 1
    # New snapshots exclude non-active bindings; epoch isolates all old cache
    # entries. Preserve Qdrant artifacts for already pinned in-flight requests.
    await db.commit()
    return await binding_service.get_binding(db, binding_id, actor=actor)
