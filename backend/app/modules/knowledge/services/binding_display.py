"""Display metadata is independent of approved/serving source pointers."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeImportBatch,
    KnowledgeImportItem,
    KnowledgeSourceRevision,
)


async def load_binding_display_metadata(db: AsyncSession, bindings: list[KnowledgeBinding]) -> dict[str, dict[str, Any]]:
    """Read latest revision/import snapshots in bulk, only within verified bindings."""
    if not bindings:
        return {}
    ids = [binding.id for binding in bindings]
    revisions = (await db.execute(
        select(KnowledgeSourceRevision.binding_id, KnowledgeSourceRevision.snapshot_metadata)
        .where(KnowledgeSourceRevision.binding_id.in_(ids))
        .distinct(KnowledgeSourceRevision.binding_id)
        .order_by(KnowledgeSourceRevision.binding_id, KnowledgeSourceRevision.revision_no.desc(), KnowledgeSourceRevision.created_at.desc())
    )).all()
    metadata = {binding_id: dict(snapshot or {}) for binding_id, snapshot in revisions}
    pending_ids = [binding.id for binding in bindings if not metadata.get(binding.id, {}).get("title") or not metadata.get(binding.id, {}).get("file_name")]
    if not pending_ids:
        return metadata
    items = (await db.execute(
        select(KnowledgeImportItem)
        .join(KnowledgeImportBatch, KnowledgeImportItem.batch_id == KnowledgeImportBatch.id)
        .join(KnowledgeBinding, KnowledgeImportItem.knowledge_binding_id == KnowledgeBinding.id)
        .where(KnowledgeBinding.id.in_(pending_ids),
               KnowledgeImportBatch.collection_id == KnowledgeBinding.collection_id)
        .distinct(KnowledgeImportItem.knowledge_binding_id)
        .order_by(KnowledgeImportItem.knowledge_binding_id, KnowledgeImportItem.created_at.desc(), KnowledgeImportItem.id.desc())
    )).scalars().all()
    for item in items:
        snapshot = metadata.setdefault(item.knowledge_binding_id, {})
        snapshot["title"] = snapshot.get("title") or item.origin_title or item.origin_file_name
        snapshot["file_name"] = snapshot.get("file_name") or item.origin_file_name
    return metadata


def resolve_binding_display_metadata(active: dict[str, Any] | None, latest: dict[str, Any] | None) -> dict[str, Any]:
    """Empty draft fields must not erase already evidenced active metadata."""
    return {**(active or {}), **{key: value for key, value in (latest or {}).items() if value}}
