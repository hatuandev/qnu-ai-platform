"""Read-only migration inventory. Never a purge approval or substitute for a full backup."""

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.assistants.models import AssistantModel
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)


async def build_inventory(db: AsyncSession, collection_id: str) -> dict:
    collection = await db.get(KnowledgeCollection, collection_id)
    if collection is None:
        raise AppException("Không tìm thấy kho cần kiểm kê.", code="COLLECTION_NOT_FOUND", status_code=404)
    bindings = list((await db.execute(select(KnowledgeBinding).where(
        KnowledgeBinding.collection_id == collection_id))).scalars().all())
    revisions = list((await db.execute(select(KnowledgeSourceRevision).join(
        KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id).where(
        KnowledgeBinding.collection_id == collection_id))).scalars().all())
    indexes = list((await db.execute(select(KnowledgeIndexRevision).join(
        KnowledgeBinding, KnowledgeIndexRevision.binding_id == KnowledgeBinding.id).where(
        KnowledgeBinding.collection_id == collection_id))).scalars().all())
    assistants = list((await db.execute(select(AssistantModel).where(
        AssistantModel.collection_id == collection_id))).scalars().all())
    jobs = list((await db.execute(select(JobRecord.id, JobRecord.job_type, JobRecord.status).where(
        JobRecord.collection_id == collection_id, JobRecord.status.in_(["queued", "running"])))).all())
    chunks = await db.scalar(select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.collection_id == collection_id))
    return {"format": "qnu-standard-migration-inventory/v1", "created_at": datetime.now(UTC).isoformat(),
        "collection_id": collection_id, "index_epoch": collection.index_epoch,
        "binding_status_counts": dict(Counter(binding.status for binding in bindings)),
        "source_format_counts": dict(Counter((rev.parse_provenance or {}).get("canonical_format", "legacy") for rev in revisions)),
        "bindings": [{"id": binding.id, "repository_document_id": binding.repository_document_id,
            "status": binding.status, "active_source_revision_id": binding.active_source_revision_id,
            "active_index_revision_id": binding.active_index_revision_id} for binding in bindings],
        "revisions": [{"id": rev.id, "binding_id": rev.binding_id, "status": rev.status,
            "canonical_hash": rev.canonical_hash, "origin_file_hash": rev.origin_file_hash,
            "qnu_status": ((rev.snapshot_metadata or {}).get("qnu_markdown") or {}).get("status")} for rev in revisions],
        "index_status_counts": dict(Counter(index.status for index in indexes)), "chunk_count": chunks,
        "busy_jobs": [{"id": row.id, "type": row.job_type, "status": row.status} for row in jobs],
        "assistants": [{"id": assistant.id, "models": {key: value for key, value in
            ((assistant.config or {}).get("models") or {}).items() if key in {
                "preferred_provider_id", "fallback_provider_id", "primary_model", "fallback_model",
                "temperature", "max_tokens", "thinking_budget"}}} for assistant in assistants],
        "source_bound_rules_present": any(key in (collection.collection_metadata or {})
            for key in ("score_conversion_registry", "score_conversion_rules")),
        "preserved": ["repository", "original_files", "assistant_configuration", "modelops", "glossary", "audit", "other_collections"],
        "backup": {"mode": "operator_ui_full_backup", "verified_by_this_inventory": False,
                   "requires_verified_full_backup_before_purge": True},
        "writes_performed": False, "purge_authorized": False}
