"""Publish immutable generations without invalidating in-flight RAG snapshots."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeIndexRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import ActivateVectorGenerationResponse
from app.modules.knowledge.services.scope_helper import get_scoped_collection
from app.modules.rag.vector_indexer import vector_indexer


async def publish_generation(
    db: AsyncSession, collection_id: str, generation_id: str,
    actor: Any | None = None, rollback: bool = False,
) -> ActivateVectorGenerationResponse:
    col = await get_scoped_collection(db, collection_id, actor=actor)
    epoch = col.index_epoch
    gen = await db.get(KnowledgeVectorGeneration, generation_id)
    if not gen or gen.collection_id != col.id:
        raise AppException("Không tìm thấy thế hệ vector.", code="VECTOR_GENERATION_NOT_FOUND", status_code=404)
    if rollback and gen.status not in ("retired", "ready"):
        raise AppException("Không thể rollback thế hệ này.", code="INVALID_ROLLBACK_TARGET", status_code=409)
    bindings = list((await db.execute(select(KnowledgeBinding).where(
        KnowledgeBinding.collection_id == col.id, KnowledgeBinding.status == "active",
    ))).scalars().all())
    revs = list((await db.execute(select(KnowledgeIndexRevision).where(
        KnowledgeIndexRevision.binding_id.in_([b.id for b in bindings]),
        KnowledgeIndexRevision.vector_generation_id == gen.id,
        KnowledgeIndexRevision.status.in_(["ready", "active", "archived"] if rollback else ["ready", "active"]),
    ).order_by(KnowledgeIndexRevision.revision_no.desc()))).scalars().all())
    selected = {}
    for binding in bindings:
        matches = [r for r in revs if r.binding_id == binding.id
                   and (rollback or r.source_revision_v2_id == binding.active_source_revision_id)]
        if not matches:
            raise AppException("Còn nguồn chưa lập chỉ mục.", code="GENERATION_NOT_READY_FOR_ACTIVATION", status_code=409)
        selected[binding.id] = matches[0]
    if not selected:
        raise AppException("Kho chưa có nguồn sẵn sàng.", code="GENERATION_NOT_READY_FOR_ACTIVATION", status_code=409)
    from app.modules.knowledge.services.generation_candidate import validate_candidate_artifacts

    await validate_candidate_artifacts(db, list(selected.values()))
    expected_sources = {b.id: b.active_source_revision_id for b in bindings}
    old_generation = (col.collection_metadata or {}).get("active_vector_generation_id")
    # Release the read transaction before remote I/O. Extra retrievable staging
    # points are invisible to the serving snapshot until the DB pointer commits.
    await db.commit()
    for rev in selected.values():
        await vector_indexer.activate_index_revision(
            collection_id, rev.id, rev.chunk_count,
            qdrant_collection_name=gen.qdrant_collection_name,
        )
    col = await get_scoped_collection(db, collection_id, actor=actor, for_update=True)
    await db.refresh(col)
    current = list((await db.execute(select(KnowledgeBinding).where(
        KnowledgeBinding.collection_id == col.id, KnowledgeBinding.status == "active",
    ).execution_options(populate_existing=True))).scalars().all())
    if col.index_epoch != epoch or {b.id: b.active_source_revision_id for b in current} != expected_sources:
        await db.rollback()
        raise AppException("Nguồn hoặc chỉ mục đã thay đổi; hãy thử lại.", code="GENERATION_CAS_CONFLICT", status_code=409)
    if old_generation and old_generation != gen.id:
        previous = await db.get(KnowledgeVectorGeneration, old_generation)
        if previous:
            previous.status = "retired"
    for binding in current:
        rev = selected[binding.id]
        binding.active_index_revision_id = rev.id
        binding.active_epoch += 1
        rev.status = "active"
    gen.status = "active"
    col.index_epoch = epoch + 1
    col.collection_metadata = {
        **(col.collection_metadata or {}),
        "active_vector_generation_id": gen.id,
        "embedding_model": gen.embedding_model,
        "embedding_provider_id": gen.provider_id,
        "embedding_dimension": gen.embedding_dimension,
    }
    await db.commit()
    # Do not deactivate old points here: frozen in-flight snapshots and rollback
    # still need them. Revision-aware retention/GC owns eventual deletion.
    return ActivateVectorGenerationResponse(
        collection_id=collection_id, activated_generation_id=gen.id,
        previous_generation_id=old_generation, new_epoch=epoch + 1,
    )
