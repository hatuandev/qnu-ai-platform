"""Readiness checks the same immutable serving snapshot as retrieval."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeDocument,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.services.source_artifact import get_structured_review_state
from app.modules.rag.retriever import hybrid_retriever


async def count_ready_sources(db: AsyncSession, collection: KnowledgeCollection) -> int:
    snapshot = await hybrid_retriever.resolve_retrieval_snapshot(
        db, collection.id, tenant_id=collection.tenant_id, workspace_id=collection.workspace_id)
    if snapshot.binding_revisions:
        indexes = (await db.execute(select(KnowledgeIndexRevision).where(
            KnowledgeIndexRevision.id.in_(snapshot.binding_revisions.values())))).scalars().all()
        for index in indexes:
            if index.chunk_count <= 0 or not (index.parity_report or {}).get("parity_passed"):
                raise AppException("Chỉ mục đang phục vụ chưa qua đối soát.", code="PARITY_GATE_FAILED")
            if index.source_revision_v2_id:
                source = await db.get(KnowledgeSourceRevision, index.source_revision_v2_id)
                if (not source or source.binding_id != index.binding_id or source.status != "ready"
                        or get_structured_review_state(source)[1]):
                    raise AppException("Bản nguồn đang phục vụ chưa được duyệt.", code="FACT_SET_REVIEW_REQUIRED")
        if len(indexes) != len(snapshot.binding_revisions):
            raise AppException("Snapshot không đầy đủ.", code="RETRIEVAL_SNAPSHOT_RESOLUTION_FAILED")
        return len(indexes)
    # A revisioned collection must not fall back to unrelated legacy documents.
    bindings = (await db.execute(select(func.count(KnowledgeBinding.id)).where(
        KnowledgeBinding.collection_id == collection.id))).scalar_one()
    if bindings or (collection.collection_metadata or {}).get("active_vector_generation_id"):
        return 0
    return (await db.execute(select(func.count(KnowledgeDocument.id)).where(
        KnowledgeDocument.collection_id == collection.id,
        KnowledgeDocument.index_status == "indexed",
        KnowledgeDocument.is_active.is_(True)))).scalar_one() or 0
