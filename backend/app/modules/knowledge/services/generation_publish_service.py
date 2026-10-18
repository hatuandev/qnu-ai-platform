"""Publish immutable generations without invalidating in-flight RAG snapshots."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeIndexActivation,
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
    if not rollback and gen.status not in ("building", "ready", "active"):
        raise AppException("Thế hệ không còn sẵn sàng.", code="GENERATION_RETIRED", status_code=409)
    bindings = list((await db.execute(select(KnowledgeBinding).where(
        KnowledgeBinding.collection_id == col.id, KnowledgeBinding.status == "active",
    ))).scalars().all())
    revs = list((await db.execute(select(KnowledgeIndexRevision).where(
        KnowledgeIndexRevision.binding_id.in_([b.id for b in bindings]),
        KnowledgeIndexRevision.vector_generation_id == gen.id,
        KnowledgeIndexRevision.status.in_(["ready", "active", "archived"] if rollback else ["ready", "active"]),
    ).order_by(KnowledgeIndexRevision.revision_no.desc()))).scalars().all())
    selected = {}
    history = {}
    if rollback and any(rev.source_revision_v2_id for rev in revs):
        activations = list((await db.execute(select(KnowledgeIndexActivation).where(
            KnowledgeIndexActivation.to_index_revision_id.in_([rev.id for rev in revs]),
        ).order_by(KnowledgeIndexActivation.epoch.desc(), KnowledgeIndexActivation.created_at.desc()))).scalars().all())
        for activation in activations:
            history.setdefault(activation.binding_id, activation.to_index_revision_id)
    for binding in bindings:
        matches = [r for r in revs if r.binding_id == binding.id
                   and (rollback or r.source_revision_v2_id == binding.active_source_revision_id)]
        if rollback:
            # A newer staged build in a retired generation was never serving.
            # Legacy archived indexes predate activation history; keep that bridge.
            matches = [rev for rev in matches if rev.id == history.get(binding.id)
                       or (not rev.source_revision_v2_id and rev.status == "archived")]
        if not matches:
            raise AppException("Còn nguồn chưa lập chỉ mục.", code="GENERATION_NOT_READY_FOR_ACTIVATION", status_code=409)
        selected[binding.id] = matches[0]
    if not selected:
        raise AppException("Kho chưa có nguồn sẵn sàng.", code="GENERATION_NOT_READY_FOR_ACTIVATION", status_code=409)
    from app.modules.knowledge.services.generation_candidate import validate_candidate_artifacts

    await validate_candidate_artifacts(db, list(selected.values()))
    from app.modules.knowledge.services.selected_vector_publish import binding_fingerprint

    expected_sources = binding_fingerprint(bindings)
    expected_indexes = {binding_id: rev.source_revision_v2_id for binding_id, rev in selected.items()}
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
    ).order_by(KnowledgeBinding.id).with_for_update().execution_options(populate_existing=True))).scalars().all())
    if (col.index_epoch != epoch or binding_fingerprint(current) != expected_sources
            or (col.collection_metadata or {}).get("active_vector_generation_id") != old_generation):
        await db.rollback()
        raise AppException("Nguồn hoặc chỉ mục đã thay đổi; hãy thử lại.", code="GENERATION_CAS_CONFLICT", status_code=409)
    await db.refresh(gen)
    try:
        if gen.status not in (("retired", "ready") if rollback else ("building", "ready", "active")):
            raise AppException("Trạng thái thế hệ đã thay đổi.", code="GENERATION_CAS_CONFLICT", status_code=409)
        for binding_id, rev in selected.items():
            await db.refresh(rev, with_for_update=True)
            if (rev.binding_id != binding_id or rev.vector_generation_id != gen.id
                    or rev.source_revision_v2_id != expected_indexes[binding_id]
                    or rev.status not in (("ready", "active", "archived") if rollback else ("ready", "active"))):
                raise AppException("Trạng thái chỉ mục đã thay đổi.", code="GENERATION_CAS_CONFLICT", status_code=409)
        await validate_candidate_artifacts(db, list(selected.values()))
    except AppException:
        await db.rollback()
        raise
    if old_generation and old_generation != gen.id:
        previous = await db.get(KnowledgeVectorGeneration, old_generation)
        if previous:
            previous.status = "retired"
    for binding in current:
        rev = selected[binding.id]
        db.add(KnowledgeIndexActivation(
            binding_id=binding.id, from_index_revision_id=binding.active_index_revision_id,
            to_index_revision_id=rev.id, action="rollback" if rollback else "promote",
            epoch=binding.active_epoch + 1, activated_by=getattr(actor, "actor_id", None),
            reason="Rollback thế hệ đã xuất bản" if rollback else "Xuất bản thế hệ đã đối soát",
        ))
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
