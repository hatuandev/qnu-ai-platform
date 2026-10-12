"""Read-only table evidence for legacy published snapshots lacking a fact manifest."""

import hashlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.knowledge.services.source_pages import manifest_page_count
from app.modules.rag.schemas import RetrievalSnapshot

logger = logging.getLogger(__name__)


async def load_snapshot_table_evidence(db: AsyncSession, snapshot: RetrievalSnapshot) -> list[dict[str, Any]]:
    if not snapshot.binding_revisions or not snapshot.tenant_id or not snapshot.workspace_id:
        return []
    query = (select(KnowledgeSourceRevision, KnowledgeIndexRevision, KnowledgeBinding)
             .join(KnowledgeIndexRevision, KnowledgeIndexRevision.source_revision_v2_id == KnowledgeSourceRevision.id)
             .join(KnowledgeBinding, KnowledgeIndexRevision.binding_id == KnowledgeBinding.id)
             .join(KnowledgeCollection, KnowledgeBinding.collection_id == KnowledgeCollection.id)
             .where(KnowledgeIndexRevision.id.in_(snapshot.binding_revisions.values()),
                    KnowledgeBinding.collection_id == snapshot.collection_id, KnowledgeBinding.status == "active",
                    KnowledgeBinding.tenant_id == snapshot.tenant_id, KnowledgeBinding.workspace_id == snapshot.workspace_id,
                    KnowledgeCollection.tenant_id == snapshot.tenant_id, KnowledgeCollection.workspace_id == snapshot.workspace_id,
                    KnowledgeSourceRevision.status == "ready"))
    try:
        records = (await db.execute(query)).all()
    except Exception as exc:
        logger.exception("Published table evidence lookup failed")
        raise AppException("Không thể đối chiếu bảng trong bản nguồn đã xuất bản.", code="TABLE_EVIDENCE_UNAVAILABLE", status_code=503) from exc
    facts = []
    for source, index, binding in records:
        if snapshot.binding_revisions.get(binding.id) != index.id:
            continue
        # Never recompute a reviewed/materialized fact set and bypass human corrections.
        if (index.parity_report or {}).get("fact_set_hash"):
            continue
        markdown = source.canonical_markdown or ""
        if not markdown or hashlib.sha256(markdown.encode("utf-8")).hexdigest() != source.canonical_hash:
            continue
        artifact = build_source_artifact(markdown, manifest_page_count(source.page_manifest), source.citation_metadata or {})
        # Bad-width/empty-header cells were excluded by extraction. Value conflicts
        # are evaluated on the requested tuple, not unrelated tables in the document.
        for fact in artifact["facts"]:
            facts.append({**fact, "id": f"evidence_{source.id}_{fact['id']}", "binding_id": binding.id,
                          "index_revision_id": index.id, "source_title": (source.snapshot_metadata or {}).get("title") or binding.id,
                          "raw_data": {**fact["raw_data"], "source_revision_id": source.id,
                                       "evidence_origin": "published_canonical_table"}})
    return facts
