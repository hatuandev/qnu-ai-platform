"""Same-generation sealed revision swaps for the existing per-source endpoints."""

from typing import Any

from sqlalchemy import select

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeChunkSet,
    KnowledgeIndexActivation,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import IndexActivationResponse
from app.modules.knowledge.services.generation_candidate import validate_candidate_artifacts
from app.modules.knowledge.services.scope_helper import (
    get_scoped_binding,
    get_scoped_collection,
    get_scoped_index_revision,
)
from app.modules.rag.vector_indexer import vector_indexer


async def is_sealed_revision(db: Any, index: Any) -> bool:
    if (index.parity_report or {}).get("derived_bundle_hash"):
        return True
    chunk_set = await db.get(KnowledgeChunkSet, index.chunk_set_id) if index.chunk_set_id else None
    return bool(chunk_set and (chunk_set.chunk_config or {}).get("_bundle"))


async def swap_sealed_revision(db: Any, binding_id: str, index_id: str, expected_epoch: int,
                               actor: Any, *, rollback: bool, reason: str | None = None) -> IndexActivationResponse:
    # The old endpoint has only performed reads. Reacquire locks in the common
    # collection -> binding order used by generation publication, avoiding inversion.
    await db.commit()
    binding = await get_scoped_binding(db, binding_id, actor=actor)
    col = await get_scoped_collection(db, binding.collection_id, actor=actor, for_update=True)
    binding = await get_scoped_binding(db, binding_id, actor=actor, for_update=True)
    await db.refresh(binding)
    if binding.status != "active" or binding.active_epoch != expected_epoch:
        raise AppException("Nguồn đã thay đổi hoặc ngừng dùng.", code="CAS_EPOCH_CONFLICT", status_code=409)
    index = await get_scoped_index_revision(db, index_id, binding_id=binding.id, actor=actor, for_update=True)
    await db.refresh(index)
    generation = await db.get(KnowledgeVectorGeneration, index.vector_generation_id, with_for_update=True, populate_existing=True)
    if (not generation or generation.collection_id != col.id or generation.status != "active"
            or (col.collection_metadata or {}).get("active_vector_generation_id") != generation.id):
        raise AppException("Đổi thế hệ cần dùng xuất bản/rollback chỉ mục tại kho tri thức.",
                           code="GENERATION_SWITCH_REQUIRED", status_code=409)
    allowed = ("ready", "active", "archived") if rollback else ("ready", "active")
    if index.status not in allowed or index.chunk_count <= 0:
        raise AppException("Bản chỉ mục không còn sẵn sàng.", code="INVALID_REVISION_STATUS", status_code=409)
    if not rollback and index.source_revision_v2_id != binding.active_source_revision_id:
        raise AppException("Bản nguồn đã thay đổi.", code="SOURCE_REVISION_CHANGED", status_code=409)
    if rollback:
        previous = await db.scalar(select(KnowledgeIndexActivation.id).where(
            KnowledgeIndexActivation.binding_id == binding.id,
            KnowledgeIndexActivation.to_index_revision_id == index.id,
        ).limit(1))
        if not previous:
            raise AppException("Bản này chưa từng xuất bản; không phải đích rollback.", code="INVALID_ROLLBACK_TARGET", status_code=409)
    await validate_candidate_artifacts(db, [index])
    # Locks protect this bounded remote operation. Old points remain available
    # to frozen retrieval snapshots; GC, not publication, owns their removal.
    await vector_indexer.activate_index_revision(col.id, index.id, index.chunk_count,
                                                qdrant_collection_name=generation.qdrant_collection_name)
    await validate_candidate_artifacts(db, [index])
    audit = KnowledgeIndexActivation(
        binding_id=binding.id, from_index_revision_id=binding.active_index_revision_id,
        to_index_revision_id=index.id, action="rollback" if rollback else "promote",
        epoch=binding.active_epoch + 1, reason=reason or "Chuyển bản dẫn xuất đã đối soát",
        activated_by=getattr(actor, "actor_id", None),
    )
    binding.active_index_revision_id = index.id
    binding.active_epoch += 1
    col.index_epoch += 1
    index.status = "active"
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return IndexActivationResponse.model_validate(audit)
