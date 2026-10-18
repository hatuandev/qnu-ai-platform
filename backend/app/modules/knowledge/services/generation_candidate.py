"""Scope and revision coherence gates shared by candidate preview and publication."""

import json
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeFact, KnowledgeSourceRevision
from app.modules.knowledge.schemas import PublishVectorItem
from app.modules.knowledge.services.source_artifact import (
    get_source_artifact,
    get_structured_review_state,
)


async def validate_candidate_artifacts(db: AsyncSession, revisions: list[Any]) -> None:
    """New builds pin facts and vectors to the same reviewed canonical revision.

    Legacy builds remain readable; reindex upgrades their manifest without OCR.
    """
    for index in revisions:
        report = index.parity_report or {}
        if not report.get("fact_set_hash") and not index.chunk_set_id:
            continue
        source = await db.get(KnowledgeSourceRevision, index.source_revision_v2_id)
        if not source or source.status != "ready":
            raise AppException("Nguồn chưa sẵn sàng để xuất bản.", code="SOURCE_NOT_READY", status_code=409)
        artifact = get_source_artifact(source)
        if source.binding_id != index.binding_id:
            raise AppException("Nguồn không thuộc bản chỉ mục.", code="SOURCE_REVISION_CHANGED", status_code=409)
        from app.modules.knowledge.services.derived_bundle import validate_index_bundle

        bundle_collection_id = await validate_index_bundle(db, index, source, artifact)
        artifact = get_source_artifact(source)
        if not report.get("fact_set_hash"):
            continue
        _, requires_structured_review, _ = get_structured_review_state(source)
        if requires_structured_review:
            raise AppException("Cần duyệt dữ liệu có cấu trúc.", code="FACT_SET_REVIEW_REQUIRED", status_code=409)
        facts = list((await db.execute(select(KnowledgeFact).where(
            KnowledgeFact.index_revision_id == index.id,
            KnowledgeFact.binding_id == index.binding_id,
        ).with_for_update().execution_options(populate_existing=True))).scalars().all())
        actual_count = len(facts)
        if (report.get("source_content_hash") != source.canonical_hash
                or report["fact_set_hash"] != artifact["fact_set_hash"]
                or actual_count != len(artifact["facts"]) or actual_count != index.fact_count):
            raise AppException("Facts và vector không khớp bản nguồn.", code="FACT_SET_PARITY_FAILED", status_code=409)
        fields = ("entity_name", "entity_type", "attribute_name", "attribute_value", "confidence")
        identity_fields = ("entity_key", "entity_label", "entity_text")
        if all(all(field in fact for field in identity_fields) for fact in artifact["facts"]):
            fields += identity_fields
        expected = Counter(tuple(f[field] for field in fields) + (json.dumps(f["raw_data"], sort_keys=True),) for f in artifact["facts"])
        actual = Counter(tuple(getattr(f, field) for field in fields) + (json.dumps({key: value for key, value in f.raw_data.items()
                  if key not in {"source_revision_id", "fact_set_hash"}}, sort_keys=True),) for f in facts)
        if report.get("derived_bundle_hash") and any(
            f.raw_data.get("source_revision_id") != source.id or f.raw_data.get("fact_set_hash") != artifact["fact_set_hash"]
            or f.collection_id != bundle_collection_id
            for f in facts
        ):
            raise AppException("Facts trỏ sai revision.", code="FACT_SET_PARITY_FAILED", status_code=409)
        if actual != expected:
            raise AppException("Nội dung facts khác tập đã duyệt.", code="FACT_SET_PARITY_FAILED", status_code=409)


async def resolve_candidate_snapshot(db: AsyncSession, collection_id: str, generation_id: str,
                                     actor: Any, items: list[PublishVectorItem] | None = None) -> Any:
    from app.modules.knowledge.models import (
        KnowledgeBinding,
        KnowledgeIndexRevision,
        KnowledgeVectorGeneration,
    )
    from app.modules.knowledge.services.scope_helper import get_scoped_collection
    from app.modules.rag.schemas import RetrievalSnapshot

    if items is not None:
        from app.modules.knowledge.services.selected_vector_publish import (
            resolve_selected_publication,
        )

        plan = await resolve_selected_publication(db, collection_id, generation_id, items, actor)
        serving = {binding.id: binding.active_index_revision_id for binding in plan.bindings
                   if binding.active_index_revision_id}
        serving.update({binding_id: index.id for binding_id, index in plan.indexes.items()})
        return RetrievalSnapshot(
            snapshot_id=f"candidate_{generation_id}", collection_id=plan.collection.id,
            collection_epoch=plan.collection.index_epoch, tenant_id=plan.collection.tenant_id,
            workspace_id=plan.collection.workspace_id, binding_revisions=serving,
            vector_generations={binding_id: generation_id for binding_id in serving},
        )

    collection = await get_scoped_collection(db, collection_id, actor=actor)
    generation = await db.get(KnowledgeVectorGeneration, generation_id)
    if not generation or generation.collection_id != collection.id:
        raise AppException("Không tìm thấy chỉ mục.", code="VECTOR_GENERATION_NOT_FOUND", status_code=404)
    bindings = list((await db.execute(select(KnowledgeBinding).where(
        KnowledgeBinding.collection_id == collection.id,


        KnowledgeBinding.status == "active",
    ))).scalars().all())
    selected = []
    for binding in bindings:
        index = (await db.execute(select(KnowledgeIndexRevision).where(
            KnowledgeIndexRevision.binding_id == binding.id,
            KnowledgeIndexRevision.vector_generation_id == generation.id,
            KnowledgeIndexRevision.source_revision_v2_id == binding.active_source_revision_id,
            KnowledgeIndexRevision.status.in_(["ready", "active"]),
        ).order_by(KnowledgeIndexRevision.revision_no.desc()))).scalars().first()
        if not index:
            raise AppException("Còn nguồn chưa nạp vector.", code="GENERATION_NOT_READY_FOR_ACTIVATION", status_code=409)
        selected.append(index)
    if not selected:
        raise AppException("Kho chưa có nguồn sẵn sàng.", code="GENERATION_NOT_READY_FOR_ACTIVATION", status_code=409)
    await validate_candidate_artifacts(db, selected)
    return RetrievalSnapshot(snapshot_id=f"candidate_{generation.id}", collection_id=collection.id,
                             collection_epoch=collection.index_epoch, tenant_id=collection.tenant_id,
                             workspace_id=collection.workspace_id,
                             binding_revisions={r.binding_id: r.id for r in selected},
                             vector_generations={r.binding_id: generation.id for r in selected})


async def ask_candidate(db: AsyncSession, collection_id: str, generation_id: str,
                        question: str, module_code: str, actor: Any,
                        items: list[PublishVectorItem] | None = None) -> Any:
    from app.modules.rag.schemas import AskRequest
    from app.modules.rag.service import rag_service

    snapshot = await resolve_candidate_snapshot(db, collection_id, generation_id, actor, items)
    return await rag_service.ask(db, AskRequest(question=question, collection_id=collection_id,
                                               module_code=module_code, tenant_id=snapshot.tenant_id,
                                               workspace_id=snapshot.workspace_id), candidate_snapshot=snapshot)
