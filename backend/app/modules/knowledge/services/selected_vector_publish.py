"""Publish selected immutable indexes while preserving other serving documents."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexActivation,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import ActivateVectorGenerationResponse, PublishVectorItem
from app.modules.knowledge.services.scope_helper import get_scoped_collection
from app.modules.knowledge.services.source_artifact import get_structured_review_state
from app.modules.rag.vector_indexer import vector_indexer


@dataclass
class SelectedPublication:
    collection: KnowledgeCollection
    generation: KnowledgeVectorGeneration
    bindings: list[KnowledgeBinding]
    indexes: dict[str, KnowledgeIndexRevision]


def binding_fingerprint(bindings: list[KnowledgeBinding]) -> dict[str, tuple[Any, ...]]:
    return {
        binding.id: (binding.active_source_revision_id, binding.active_index_revision_id, binding.active_epoch)
        for binding in bindings
    }


async def resolve_selected_publication(
    db: AsyncSession, collection_id: str, generation_id: str,
    items: list[PublishVectorItem], actor: Any,
) -> SelectedPublication:
    from app.modules.knowledge.services.generation_candidate import validate_candidate_artifacts

    collection = await get_scoped_collection(db, collection_id, actor=actor)
    generation = await db.get(KnowledgeVectorGeneration, generation_id)
    if not generation or generation.collection_id != collection.id:
        raise AppException("Không tìm thấy chỉ mục.", code="VECTOR_GENERATION_NOT_FOUND", status_code=404)
    if generation.status not in ("building", "ready", "active"):
        raise AppException("Chỉ mục đã lưu trữ.", code="GENERATION_RETIRED", status_code=409)
    targets = {item.binding_id: item for item in items}
    if not targets or len(targets) != len(items):
        raise AppException("Danh sách nguồn rỗng hoặc bị lặp.", code="INVALID_PUBLISH_SELECTION", status_code=422)
    bindings = list((await db.scalars(select(KnowledgeBinding).where(
        KnowledgeBinding.collection_id == collection.id,


        KnowledgeBinding.status == "active",
    ))).all())
    binding_map = {binding.id: binding for binding in bindings}
    if not targets.keys() <= binding_map.keys():
        raise AppException("Nguồn không thuộc kho hoặc không hoạt động.", code="SOURCE_NOT_FOUND", status_code=404)
    current_generation = (collection.collection_metadata or {}).get("active_vector_generation_id")
    serving_ids = {binding.id for binding in bindings if binding.active_index_revision_id}
    if current_generation != generation.id and not serving_ids <= targets.keys():
        raise AppException(
            "Đổi chỉ mục cần nạp và chọn tất cả nguồn đang phục vụ; nguồn chưa xuất bản có thể để sau.",
            code="GENERATION_SWITCH_REQUIRES_SERVING_SOURCES", status_code=409,
        )
    revisions = list((await db.scalars(select(KnowledgeIndexRevision).where(
        KnowledgeIndexRevision.id.in_([item.index_revision_id for item in items]),
        KnowledgeIndexRevision.binding_id.in_(targets),
        KnowledgeIndexRevision.vector_generation_id == generation.id,
        KnowledgeIndexRevision.status.in_(["ready", "active"]),
    ))).all())
    index_map = {index.id: index for index in revisions}
    selected = {}
    for binding_id, item in targets.items():
        binding = binding_map[binding_id]
        index = index_map.get(item.index_revision_id)
        if (binding.active_source_revision_id != item.source_revision_id or not index
                or index.binding_id != binding_id or index.source_revision_v2_id != item.source_revision_id):
            raise AppException("Bản nguồn hoặc vector đã thay đổi; hãy làm mới.", code="SOURCE_REVISION_CHANGED", status_code=409)
        source = await db.get(KnowledgeSourceRevision, item.source_revision_id)
        if not source or source.binding_id != binding_id or source.status != "ready":
            raise AppException("Nguồn chưa sẵn sàng.", code="SOURCE_NOT_READY", status_code=409)
        if get_structured_review_state(source)[1]:
            raise AppException("Nguồn đã chọn cần duyệt dữ liệu cấu trúc.", code="FACT_SET_REVIEW_REQUIRED", status_code=409)
        if index.chunk_count <= 0 or not (index.parity_report or {}).get("parity_passed"):
            raise AppException("Vector chưa qua đối soát.", code="PARITY_GATE_FAILED", status_code=409)
        selected[binding_id] = index
    await validate_candidate_artifacts(db, list(selected.values()))
    return SelectedPublication(collection, generation, bindings, selected)


async def publish_selected_vectors(
    db: AsyncSession, collection_id: str, generation_id: str,
    items: list[PublishVectorItem], actor: Any,
) -> ActivateVectorGenerationResponse:
    plan = await resolve_selected_publication(db, collection_id, generation_id, items, actor)
    col, gen = plan.collection, plan.generation
    epoch = col.index_epoch
    previous_id = (col.collection_metadata or {}).get("active_vector_generation_id")
    expected = binding_fingerprint(plan.bindings)
    expected_sources = {binding_id: index.source_revision_v2_id for binding_id, index in plan.indexes.items()}
    if previous_id == gen.id and all(expected[key][1] == index.id for key, index in plan.indexes.items()):
        return ActivateVectorGenerationResponse(
            collection_id=col.id, activated_generation_id=gen.id,
            previous_generation_id=previous_id, new_epoch=epoch,
        )
    await db.commit()
    for index in plan.indexes.values():
        await vector_indexer.activate_index_revision(
            col.id, index.id, index.chunk_count, qdrant_collection_name=gen.qdrant_collection_name,
        )
    col = await get_scoped_collection(db, collection_id, actor=actor, for_update=True)
    await db.refresh(col)
    current = list((await db.scalars(select(KnowledgeBinding).where(
        KnowledgeBinding.collection_id == col.id,


        KnowledgeBinding.status == "active",
    ).order_by(KnowledgeBinding.id).with_for_update().execution_options(populate_existing=True))).all())
    if (col.index_epoch != epoch or binding_fingerprint(current) != expected
            or (col.collection_metadata or {}).get("active_vector_generation_id") != previous_id):
        await db.rollback()
        raise AppException("Nguồn hoặc chỉ mục đã thay đổi; hãy thử lại.", code="GENERATION_CAS_CONFLICT", status_code=409)
    await db.refresh(gen)
    if gen.status not in ("building", "ready", "active"):
        await db.rollback()
        raise AppException("Chỉ mục đã lưu trữ.", code="GENERATION_RETIRED", status_code=409)
    for binding_id, index in plan.indexes.items():
        await db.refresh(index)
        source = await db.get(KnowledgeSourceRevision, index.source_revision_v2_id)
        if source:
            await db.refresh(source)
        if (index.binding_id != binding_id or index.vector_generation_id != gen.id
                or index.source_revision_v2_id != expected_sources[binding_id]
                or index.status not in ("ready", "active") or not source or source.status != "ready"
                or get_structured_review_state(source)[1]):
            await db.rollback()
            raise AppException("Nguồn không còn đủ điều kiện xuất bản.", code="SOURCE_NOT_READY", status_code=409)
    from app.modules.knowledge.services.generation_candidate import validate_candidate_artifacts

    try:
        await validate_candidate_artifacts(db, list(plan.indexes.values()))
    except AppException:
        await db.rollback()
        raise
    if previous_id and previous_id != gen.id:
        previous = await db.get(KnowledgeVectorGeneration, previous_id)
        if previous:
            previous.status = "retired"
    for binding in current:
        index = plan.indexes.get(binding.id)
        if not index:
            continue
        db.add(KnowledgeIndexActivation(
            binding_id=binding.id, from_index_revision_id=binding.active_index_revision_id,
            to_index_revision_id=index.id, action="promote", epoch=binding.active_epoch + 1,
            reason="Xuất bản nguồn đã chọn", activated_by=getattr(actor, "actor_id", None),
        ))
        binding.active_index_revision_id = index.id
        binding.active_epoch += 1
        index.status = "active"
    gen.status = "active"
    col.index_epoch = epoch + 1
    col.collection_metadata = {
        **(col.collection_metadata or {}), "active_vector_generation_id": gen.id,
        "embedding_model": gen.embedding_model, "embedding_provider_id": gen.provider_id,
        "embedding_dimension": gen.embedding_dimension,
    }
    await db.commit()
    return ActivateVectorGenerationResponse(
        collection_id=col.id, activated_generation_id=gen.id,
        previous_generation_id=previous_id, new_epoch=epoch + 1,
    )
