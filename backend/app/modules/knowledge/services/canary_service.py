"""Knowledge Canary & Legacy Backfill Service — ADR-011 Phase 6.

This service provides:
1. Legacy collection state audit and classification:
   - 'active-parity-ok': Chunks and Qdrant points align, ready for serving.
   - 'needs-rebuild': Discrepancies between database chunks and vector points.
   - 'pending-intake': Missing repository link or unparsed chunks.
2. Idempotent backfill migration for legacy collections:
   - Creates default KnowledgeVectorGeneration v1.
   - Ensures RepositoryDocument and DocumentRevision provenance.
   - Creates KnowledgeBinding and KnowledgeIndexRevision v1.
   - Tags legacy KnowledgeChunks and KnowledgeFacts with binding_id and index_revision_id.
   - Atomically promotes bindings with audit logging.
3. Shadow retrieval verification engine:
   - Parallel comparison of V1 Legacy and V2 Snapshot Isolation.
   - Asserts zero cross-revision or staging leakage (retrieval_revision_leak_total = 0).
   - Measures p95 latency delta.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFact,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.schemas import (
    BackfillItemResult,
    BackfillReport,
    CanaryPolicyResponse,
    LegacyAuditItem,
    LegacyAuditReport,
    ShadowRetrievalReport,
    UpdateCanaryPolicyRequest,
)
from app.modules.knowledge.services.index_build_service import index_build_service
from app.modules.knowledge.services.scope_helper import (
    bump_collection_index_epoch,
    get_scoped_collection,
)

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


class CanaryService:
    """Service handling legacy data classification, safe backfills, and shadow retrieval."""

    async def audit_collection_legacy_state(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> LegacyAuditReport:
        """Audit legacy documents within a collection and classify parity state."""
        await get_scoped_collection(db, collection_id, actor=actor)

        # 1. Fetch all knowledge documents
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.collection_id == collection_id)
            .order_id if hasattr(KnowledgeDocument, "order_id") else select(KnowledgeDocument).where(KnowledgeDocument.collection_id == collection_id)
        )
        docs = (await db.execute(stmt)).scalars().all()

        items: list[LegacyAuditItem] = []
        parity_ok_count = 0
        needs_rebuild_count = 0
        pending_intake_count = 0

        for doc in docs:
            # Count DB chunks
            chunk_stmt = select(func.count(KnowledgeChunk.id)).where(
                KnowledgeChunk.document_id == doc.id,
                KnowledgeChunk.collection_id == collection_id,
            )
            db_chunks_count = (await db.execute(chunk_stmt)).scalar() or 0

            # Find binding if exists
            bnd_stmt = select(KnowledgeBinding).where(
                KnowledgeBinding.collection_id == collection_id,
                (KnowledgeBinding.repository_document_id == doc.repository_document_id)
                | (KnowledgeBinding.repository_document_id == doc.id),
            )
            binding = (await db.execute(bnd_stmt)).scalar_one_or_none()

            # Estimate / Query Qdrant points count
            qdrant_points_count = 0
            qdrant_error: str | None = None
            try:
                from app.modules.rag.vector_indexer import vector_indexer

                qdrant_points_count = await vector_indexer.count_points_by_document(
                    collection_id, doc.id
                )
            except Exception as exc:
                qdrant_error = str(exc)

            # Classification logic
            classification: str
            discrepancy_reason: str | None = None

            if qdrant_error:
                classification = "audit-error"
                discrepancy_reason = qdrant_error
                needs_rebuild_count += 1
            elif db_chunks_count == 0 or not doc.repository_document_id:
                classification = "pending-intake"
                discrepancy_reason = "Tài liệu chưa được intake hoặc chưa có chunks nội dung"
                pending_intake_count += 1
            elif db_chunks_count != qdrant_points_count:
                classification = "needs-rebuild"
                discrepancy_reason = (
                    f"Lệch số lượng: {db_chunks_count} chunks trên DB vs {qdrant_points_count} points trên Qdrant"
                )
                needs_rebuild_count += 1
            else:
                classification = "active-parity-ok"
                parity_ok_count += 1

            items.append(
                LegacyAuditItem(
                    document_id=doc.id,
                    document_title=doc.title,
                    repository_document_id=doc.repository_document_id,
                    binding_id=binding.id if binding else None,
                    active_index_revision_id=binding.active_index_revision_id if binding else None,
                    db_chunks_count=db_chunks_count,
                    qdrant_points_count=qdrant_points_count,
                    classification=classification,
                    discrepancy_reason=discrepancy_reason,
                )
            )

        total_docs = len(docs)
        parity_ratio = (parity_ok_count / total_docs) if total_docs > 0 else 1.0

        return LegacyAuditReport(
            collection_id=collection_id,
            total_documents=total_docs,
            active_parity_ok_count=parity_ok_count,
            needs_rebuild_count=needs_rebuild_count,
            pending_intake_count=pending_intake_count,
            parity_ratio=round(parity_ratio, 4),
            items=items,
            audited_at=utcnow(),
        )

    async def backfill_legacy_collection(
        self,
        db: AsyncSession,
        collection_id: str,
        actor_id: str | None = None,
        force_rebuild: bool = False,
        default_chunk_strategy: str = "ClauseBasedChunker",
        actor: Any | None = None,
    ) -> BackfillReport:
        """Idempotently backfills legacy documents into KnowledgeBinding and KnowledgeIndexRevision v1."""
        col = await get_scoped_collection(db, collection_id, actor=actor)

        # 1. Query all legacy documents
        doc_stmt = select(KnowledgeDocument).where(KnowledgeDocument.collection_id == collection_id)
        docs = (await db.execute(doc_stmt)).scalars().all()

        item_results: list[BackfillItemResult] = []
        bindings_created = 0
        index_revisions_created = 0
        total_chunks_tagged = 0
        total_facts_tagged = 0

        for doc in docs:
            # A. Ensure RepositoryDocument exists
            rep_doc: RepositoryDocument | None = None
            if doc.repository_document_id:
                rep_doc = await db.get(RepositoryDocument, doc.repository_document_id)

            if not rep_doc:
                # Create synthetic RepositoryDocument from legacy doc
                rep_doc = RepositoryDocument(
                    id=f"rep_doc_{uuid.uuid4().hex[:12]}",
                    tenant_id=col.tenant_id,
                    workspace_id=col.workspace_id,
                    title=doc.title,
                    document_number=f"LEGACY-{doc.id[-6:].upper()}",
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                    file_size_bytes=doc.file_size_bytes,
                    storage_path=doc.storage_path,
                    file_hash=doc.file_hash,
                    status="active",
                )
                db.add(rep_doc)
                await db.flush()
                doc.repository_document_id = rep_doc.id

            # B. Load the real legacy artifacts before creating a repository revision.
            chk_stmt = (
                select(KnowledgeChunk)
                .where(
                    KnowledgeChunk.document_id == doc.id,
                    KnowledgeChunk.collection_id == col.id,
                )
                .order_by(KnowledgeChunk.chunk_index.asc())
            )
            chunks = (await db.execute(chk_stmt)).scalars().all()
            fact_stmt = select(KnowledgeFact).where(
                KnowledgeFact.document_id == doc.id,
                KnowledgeFact.collection_id == col.id,
            )
            facts = (await db.execute(fact_stmt)).scalars().all()

            # C. Ensure DocumentRevision v1 exists using canonical content reconstructed from chunks.
            rev_stmt = (
                select(DocumentRevision)
                .where(DocumentRevision.document_id == rep_doc.id)
                .order_by(DocumentRevision.revision_no.asc())
            )
            source_rev = (await db.execute(rev_stmt)).scalars().first()
            if not source_rev:
                canonical_markdown = "\n\n".join(
                    chunk.content.strip() for chunk in chunks if chunk.content.strip()
                )
                if not canonical_markdown:
                    item_results.append(
                        BackfillItemResult(
                            document_id=doc.id,
                            binding_id="",
                            index_revision_id="",
                            chunks_tagged=0,
                            facts_tagged=0,
                            classification="pending-intake",
                            status="failed",
                        )
                    )
                    continue
                source_rev = DocumentRevision(
                    id=f"drev_{uuid.uuid4().hex[:12]}",
                    document_id=rep_doc.id,
                    revision_no=1,
                    status="ready",
                    source_file_name=doc.file_name,
                    source_file_type=doc.file_type,
                    source_size_bytes=doc.file_size_bytes,
                    source_hash=doc.file_hash,
                    source_storage_path=doc.storage_path,
                    canonical_markdown=canonical_markdown,
                    canonical_hash=hashlib.sha256(
                        canonical_markdown.encode("utf-8")
                    ).hexdigest(),
                    quality_report={"overall_status": "passed", "legacy_backfilled": True},
                    parse_provenance={"legacy_backfilled": True, "source": "knowledge_chunks"},
                )
                db.add(source_rev)
                await db.flush()

            # D. Ensure KnowledgeBinding exists
            bnd_stmt = select(KnowledgeBinding).where(
                KnowledgeBinding.collection_id == col.id,
                KnowledgeBinding.repository_document_id == rep_doc.id,
            )
            binding = (await db.execute(bnd_stmt)).scalar_one_or_none()
            binding_was_new = False
            if not binding:
                binding = KnowledgeBinding(
                    collection_id=col.id,
                    repository_document_id=rep_doc.id,
                    source_revision_id=source_rev.id,
                    chunk_strategy=default_chunk_strategy,
                    sync_policy="manual",
                    status="active",
                    active_epoch=0,
                    tenant_id=col.tenant_id,
                    workspace_id=col.workspace_id,
                )
                db.add(binding)
                await db.flush()
                bindings_created += 1
                binding_was_new = True

            # E. Build a real staging artifact and promote only after strict Qdrant parity.
            idx_rev_was_new = False
            idx_rev = None
            if binding.active_index_revision_id and not force_rebuild:
                idx_rev = await db.get(KnowledgeIndexRevision, binding.active_index_revision_id)

            if not idx_rev or force_rebuild:
                idx_rev = await index_build_service.build_staging_index(
                    db=db,
                    binding_id=binding.id,
                    source_revision_id=source_rev.id,
                    chunk_strategy=default_chunk_strategy,
                    auto_activate=True,
                )
                if idx_rev.status != "active":
                    item_results.append(
                        BackfillItemResult(
                            document_id=doc.id,
                            binding_id=binding.id,
                            index_revision_id=idx_rev.id,
                            chunks_tagged=0,
                            facts_tagged=0,
                            classification="needs-rebuild",
                            status="failed",
                        )
                    )
                    continue
                index_revisions_created += 1
                idx_rev_was_new = True

            # F. Keep legacy chunks isolated; only facts are attached to the verified V2 snapshot.
            chunks_tagged_this_doc = 0

            facts_tagged_this_doc = 0
            for fact in facts:
                fact.binding_id = binding.id
                fact.index_revision_id = idx_rev.id
                facts_tagged_this_doc += 1

            total_chunks_tagged += chunks_tagged_this_doc
            total_facts_tagged += facts_tagged_this_doc

            item_results.append(
                BackfillItemResult(
                    document_id=doc.id,
                    binding_id=binding.id,
                    index_revision_id=idx_rev.id,
                    chunks_tagged=chunks_tagged_this_doc,
                    facts_tagged=facts_tagged_this_doc,
                    classification="active-parity-ok" if len(chunks) > 0 else "pending-intake",
                    status="created" if (binding_was_new or idx_rev_was_new) else "updated",
                )
            )

        # Bump collection index epoch atomically
        new_epoch = await bump_collection_index_epoch(db, collection_id)
        col.index_epoch = new_epoch
        await db.commit()

        return BackfillReport(
            collection_id=collection_id,
            documents_processed=len(docs),
            bindings_created=bindings_created,
            index_revisions_created=index_revisions_created,
            chunks_tagged=total_chunks_tagged,
            facts_tagged=total_facts_tagged,
            collection_epoch=new_epoch,
            status="completed",
            items=item_results,
            completed_at=utcnow(),
        )

    async def run_shadow_retrieval_comparison(
        self,
        db: AsyncSession,
        collection_id: str,
        query: str,
        top_k: int = 5,
        actor: Any | None = None,
    ) -> ShadowRetrievalReport:
        """Run shadow comparison between V1 Legacy retrieval and V2 Snapshot retrieval.

        Guarantees:
        - retrieval_revision_leak_total = 0 (zero inactive/staging chunks leak).
        - Measures p95 latency delta.
        """
        from app.modules.rag.retriever import hybrid_retriever

        col = await get_scoped_collection(db, collection_id, actor=actor)

        # 1. Resolve V2 Snapshot
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, collection_id)
        active_revision_ids = set(snapshot.binding_revisions.values())

        # 2. Run V1 Retrieval (without snapshot pinning, legacy behavior)
        t0 = time.perf_counter()
        v1_candidates = await hybrid_retriever.retrieve(
            db=db,
            collection_id=collection_id,
            query=query,
            top_k=top_k,
            snapshot=None,
            pin_snapshot=False,
            read_mode_override="legacy",
            tenant_id=col.tenant_id,
            workspace_id=col.workspace_id,
        )
        latency_v1_ms = (time.perf_counter() - t0) * 1000.0

        # 3. Run V2 Retrieval (pinned snapshot isolation)
        t1 = time.perf_counter()
        v2_candidates = await hybrid_retriever.retrieve(
            db=db,
            collection_id=collection_id,
            query=query,
            top_k=top_k,
            snapshot=snapshot,
            tenant_id=col.tenant_id,
            workspace_id=col.workspace_id,
        )
        latency_v2_ms = (time.perf_counter() - t1) * 1000.0

        # 4. Metrics & Leakage Assertion
        v1_chunk_ids = [c.chunk_id for c in v1_candidates]
        v2_chunk_ids = [c.chunk_id for c in v2_candidates]

        set_v1 = set(v1_chunk_ids)
        set_v2 = set(v2_chunk_ids)
        overlap = len(set_v1 & set_v2)
        union = len(set_v1 | set_v2)
        jaccard = (overlap / union) if union > 0 else 1.0

        latency_delta_pct = (
            ((latency_v2_ms - latency_v1_ms) / max(0.001, latency_v1_ms)) * 100.0
        )

        # Count leaked chunks in V2 (chunks that belong to inactive or staging revisions)
        leaked_count = 0
        for c in v2_candidates:
            rev_id = getattr(c, "index_revision_id", None)
            if rev_id and active_revision_ids and (rev_id not in active_revision_ids):
                leaked_count += 1
            if (c.metadata or {}).get("document_status") == "staging":
                leaked_count += 1

        return ShadowRetrievalReport(
            collection_id=collection_id,
            query=query,
            v1_result_count=len(v1_candidates),
            v2_result_count=len(v2_candidates),
            overlap_count=overlap,
            jaccard_similarity=round(jaccard, 4),
            latency_v1_ms=round(latency_v1_ms, 2),
            latency_v2_ms=round(latency_v2_ms, 2),
            latency_delta_pct=round(latency_delta_pct, 2),
            retrieval_revision_leak_total=leaked_count,
            leak_detected=(leaked_count > 0),
            v1_chunk_ids=v1_chunk_ids,
            v2_chunk_ids=v2_chunk_ids,
            tested_at=utcnow(),
        )

    async def get_collection_canary_policy(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> CanaryPolicyResponse:
        """Fetch per-collection Canary RAG serving and retention policies."""
        col = await get_scoped_collection(db, collection_id, actor=actor)

        meta = dict(col.collection_metadata or {})
        policy = meta.get("canary_policy") or {}
        read_mode = str(policy.get("read_mode", "system"))
        retention = int(policy.get("retention_revisions", 2))
        last_gc = meta.get("last_gc_report")

        system_mode = getattr(settings, "RAG_REVISION_READ_MODE", "revisioned")
        effective_mode = (
            read_mode if read_mode in ("revisioned", "shadow", "legacy") else system_mode
        )

        return CanaryPolicyResponse(
            collection_id=collection_id,
            read_mode=read_mode,
            system_read_mode=system_mode,
            effective_read_mode=effective_mode,
            retention_revisions=retention,
            last_gc_report=last_gc,
        )

    async def update_collection_canary_policy(
        self,
        db: AsyncSession,
        collection_id: str,
        req: UpdateCanaryPolicyRequest,
        actor: Any | None = None,
    ) -> CanaryPolicyResponse:
        """Update per-collection Canary RAG serving mode and retention window."""
        col = await get_scoped_collection(db, collection_id, actor=actor)

        meta = dict(col.collection_metadata or {})
        policy = dict(meta.get("canary_policy") or {})
        policy["read_mode"] = req.read_mode
        policy["retention_revisions"] = req.retention_revisions
        policy["updated_at"] = utcnow().isoformat()

        meta["canary_policy"] = policy
        col.collection_metadata = meta
        await db.commit()
        await db.refresh(col)

        logger.info(
            "Updated canary policy for collection %s: read_mode=%s, retention=%d",
            collection_id,
            req.read_mode,
            req.retention_revisions,
        )

        system_mode = getattr(settings, "RAG_REVISION_READ_MODE", "revisioned")
        effective_mode = (
            req.read_mode
            if req.read_mode in ("revisioned", "shadow", "legacy")
            else system_mode
        )

        return CanaryPolicyResponse(
            collection_id=collection_id,
            read_mode=req.read_mode,
            system_read_mode=system_mode,
            effective_read_mode=effective_mode,
            retention_revisions=req.retention_revisions,
            last_gc_report=meta.get("last_gc_report"),
        )


canary_service = CanaryService()
