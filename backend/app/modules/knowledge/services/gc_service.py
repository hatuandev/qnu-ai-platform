"""Knowledge Artifact Garbage Collection (GC) Service — ADR-011 Phase 7 Cutover.

This service implements automated, safe pruning of superseded, archived, or failed
knowledge index revisions while strictly preserving Rollback Protection:
1. Active index revisions currently serving traffic are NEVER pruned.
2. A configurable retention window (default: keep_revisions=2) of the latest superseded
   revisions per binding is always preserved, guaranteeing instant zero-reindex rollback capability.
3. Older superseded revisions beyond retention window, as well as failed/cancelled artifacts,
   are safely pruned:
   - Status updated to 'pruned'
   - KnowledgeChunk records in PostgreSQL deleted
   - KnowledgeFact records in PostgreSQL deleted
   - Dense vector points in Qdrant deleted
4. Full dry-run simulation mode supported for operational audit.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeFact,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.schemas import (
    GarbageCollectionReport,
    SystemDecommissioningAuditReport,
    SystemGarbageCollectionReport,
)
from app.modules.rag.vector_indexer import vector_indexer

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


class KnowledgeArtifactGCService:
    """Service for safely pruning obsolete knowledge index artifacts with rollback protection."""

    async def collect_garbage(
        self,
        db: AsyncSession,
        collection_id: str,
        keep_revisions: int = 2,
        dry_run: bool = False,
        actor: Any | None = None,
        job_id: str | None = None,
    ) -> GarbageCollectionReport:
        """Scan and prune obsolete index revisions for a collection.

        Args:
            db: Async database session.
            collection_id: Target collection identifier.
            keep_revisions: Number of recent historical revisions to preserve per binding for rollback.
            dry_run: If True, calculates impacted counts without mutating database or vector index.
            actor: Optional AuthActor for tenant and workspace authorization scoping.
            job_id: Optional background job identifier for cooperative cancellation.

        Returns:
            GarbageCollectionReport detailing pruned items and freed resources.
        """
        from app.modules.jobs.service import is_job_cancelled
        from app.modules.knowledge.services.scope_helper import (
            get_scoped_collection,
        )

        col = await get_scoped_collection(db, collection_id, actor=actor)

        # Checkpoint: Cancel check before start
        if job_id and await is_job_cancelled(job_id, db=db):
            raise AppException("Tác vụ Garbage Collection đã bị hủy.", code="JOB_CANCELLED", status_code=409)

        # 1. Fetch all bindings for this collection
        stmt_bindings = select(KnowledgeBinding).where(
            KnowledgeBinding.collection_id == collection_id,
            KnowledgeBinding.status != "detached",
        )
        res_bindings = await db.execute(stmt_bindings)
        bindings = list(res_bindings.scalars().all())

        total_bindings = len(bindings)
        pruned_revisions_count = 0
        pruned_revision_ids: list[str] = []
        pruned_chunks_total = 0
        pruned_facts_total = 0
        pruned_points_total = 0

        for binding in bindings:
            # Checkpoint: Cancel check per binding
            if job_id and await is_job_cancelled(job_id, db=db):
                raise AppException("Tác vụ Garbage Collection đã bị hủy.", code="JOB_CANCELLED", status_code=409)

            # Fetch all revisions for this binding ordered by newest first
            stmt_revs = (
                select(KnowledgeIndexRevision)
                .where(KnowledgeIndexRevision.binding_id == binding.id)
                .order_by(desc(KnowledgeIndexRevision.created_at))
            )
            res_revs = await db.execute(stmt_revs)
            revs = list(res_revs.scalars().all())

            active_id = binding.active_index_revision_id

            # Separate revisions by category
            preserved_historical_count = 0
            eligible_for_gc: list[KnowledgeIndexRevision] = []

            for rev in revs:
                # Rule 1: Active revision is NEVER pruned
                if rev.id == active_id:
                    continue

                # Rule 2: In-flight revisions (building, staging, ready) are NEVER pruned
                if rev.status in ("building", "staging", "ready"):
                    continue

                # Rule 3: Already pruned revisions need no action
                if rev.status == "pruned":
                    continue

                # Rule 4: Historical superseded/archived revisions preserve up to keep_revisions
                if (
                    rev.status in ("superseded", "archived")
                    and preserved_historical_count < keep_revisions
                ):
                    preserved_historical_count += 1
                    continue

                # Any older superseded/archived beyond keep_revisions OR failed/cancelled are eligible
                if rev.status in ("superseded", "archived", "failed", "cancelled"):
                    eligible_for_gc.append(rev)

            # Process candidates for this binding
            for rev in eligible_for_gc:
                # Checkpoint: Cancel check before pruning candidate revision
                if job_id and await is_job_cancelled(job_id):
                    raise AppException("Tác vụ Garbage Collection đã bị hủy.", code="JOB_CANCELLED", status_code=409)

                # Count chunks
                chunk_cnt_stmt = select(func.count(KnowledgeChunk.id)).where(
                    KnowledgeChunk.index_revision_id == rev.id
                )
                chunk_cnt = (await db.execute(chunk_cnt_stmt)).scalar_one() or 0

                # Count facts
                fact_cnt_stmt = select(func.count(KnowledgeFact.id)).where(
                    KnowledgeFact.index_revision_id == rev.id
                )
                fact_cnt = (await db.execute(fact_cnt_stmt)).scalar_one() or 0

                pruned_chunks_total += chunk_cnt
                pruned_facts_total += fact_cnt
                pruned_revisions_count += 1
                pruned_revision_ids.append(rev.id)

                if not dry_run:
                    # Checkpoint: Cancel check before external Qdrant deletion
                    if job_id and await is_job_cancelled(job_id):
                        raise AppException("Tác vụ Garbage Collection đã bị hủy.", code="JOB_CANCELLED", status_code=409)

                    # 1. Delete external vector artifacts first and verify exact parity.
                    points_deleted = await vector_indexer.delete_points_by_index_revision(
                        collection_id=collection_id,
                        index_revision_id=rev.id,
                    )
                    if points_deleted != chunk_cnt:
                        raise AppException(
                            f"GC Qdrant mismatch cho revision '{rev.id}': "
                            f"đã xóa {points_deleted}/{chunk_cnt} points.",
                            code="GC_VECTOR_DELETE_MISMATCH",
                            status_code=409,
                        )
                    pruned_points_total += points_deleted

                    # Checkpoint: Cancel check before PostgreSQL DB deletion
                    if job_id and await is_job_cancelled(job_id):
                        raise AppException("Tác vụ Garbage Collection đã bị hủy.", code="JOB_CANCELLED", status_code=409)

                    # 2. Delete database artifacts only after Qdrant confirmed deletion.
                    if chunk_cnt > 0:
                        await db.execute(
                            delete(KnowledgeChunk).where(KnowledgeChunk.index_revision_id == rev.id)
                        )
                    if fact_cnt > 0:
                        await db.execute(
                            delete(KnowledgeFact).where(KnowledgeFact.index_revision_id == rev.id)
                        )

                    # 3. Mark the immutable artifact as pruned.
                    rev.status = "pruned"
                    rev.updated_at = utcnow()

                    logger.info(
                        "Pruned index revision %s (binding %s): %d chunks, %d facts, %d points deleted",
                        rev.id,
                        binding.id,
                        chunk_cnt,
                        fact_cnt,
                        points_deleted,
                    )
                else:
                    # In dry run, estimate points from chunk count
                    pruned_points_total += chunk_cnt

        mode_str = "Mô phỏng (Dry-run)" if dry_run else "Thực thi hoàn tất"
        message = (
            f"{mode_str}: Đã rà soát {total_bindings} liên kết. "
            f"Dọn dẹp {pruned_revisions_count} phiên bản chỉ mục cũ "
            f"(bảo lưu {keep_revisions} bản lịch sử cho rollback), "
            f"giải phóng {pruned_chunks_total} chunks, {pruned_facts_total} facts, {pruned_points_total} vector points."
        )

        report = GarbageCollectionReport(
            collection_id=collection_id,
            dry_run=dry_run,
            keep_revisions=keep_revisions,
            total_bindings_scanned=total_bindings,
            pruned_revisions_count=pruned_revisions_count,
            pruned_revision_ids=pruned_revision_ids,
            pruned_chunks_count=pruned_chunks_total,
            pruned_facts_count=pruned_facts_total,
            pruned_points_count=pruned_points_total,
            message=message,
            executed_at=utcnow(),
        )

        if not dry_run:
            meta = dict(col.collection_metadata or {})
            meta["last_gc_report"] = report.model_dump(mode="json")
            col.collection_metadata = meta
            await db.commit()

        return report

    async def collect_garbage_system_wide(
        self,
        db: AsyncSession,
        default_keep_revisions: int = 2,
        dry_run: bool = False,
        actor: Any | None = None,
        job_id: str | None = None,
    ) -> SystemGarbageCollectionReport:
        """Execute or simulate artifact garbage collection across scoped knowledge collections."""
        from app.modules.knowledge.services.scope_helper import apply_actor_scope

        stmt = select(KnowledgeCollection)
        stmt = apply_actor_scope(stmt, KnowledgeCollection, actor)
        cols_res = await db.execute(stmt)
        cols = list(cols_res.scalars().all())

        reports: list[GarbageCollectionReport] = []
        total_bindings = 0
        total_pruned_revs = 0
        total_pruned_chunks = 0
        total_pruned_facts = 0
        total_pruned_points = 0

        for col in cols:
            policy = (col.collection_metadata or {}).get("canary_policy") or {}
            keep_revs = int(policy.get("retention_revisions", default_keep_revisions))
            rep = await self.collect_garbage(
                db=db,
                collection_id=col.id,
                keep_revisions=keep_revs,
                dry_run=dry_run,
                actor=actor,
                job_id=job_id,
            )
            reports.append(rep)
            total_bindings += rep.total_bindings_scanned
            total_pruned_revs += rep.pruned_revisions_count
            total_pruned_chunks += rep.pruned_chunks_count
            total_pruned_facts += rep.pruned_facts_count
            total_pruned_points += rep.pruned_points_count

        mode_str = "Mô phỏng (Dry-run)" if dry_run else "Thực thi toàn hệ thống"
        message = (
            f"{mode_str}: Đã rà soát {len(cols)} kho tri thức, {total_bindings} liên kết. "
            f"Dọn dẹp {total_pruned_revs} phiên bản chỉ mục cũ, "
            f"giải phóng {total_pruned_chunks} chunks, {total_pruned_facts} facts, {total_pruned_points} vector points."
        )

        return SystemGarbageCollectionReport(
            total_collections_scanned=len(cols),
            total_bindings_scanned=total_bindings,
            total_pruned_revisions_count=total_pruned_revs,
            total_pruned_chunks_count=total_pruned_chunks,
            total_pruned_facts_count=total_pruned_facts,
            total_pruned_points_count=total_pruned_points,
            dry_run=dry_run,
            reports=reports,
            message=message,
            executed_at=utcnow(),
        )

    async def audit_system_decommissioning(
        self,
        db: AsyncSession,
        actor: Any | None = None,
    ) -> SystemDecommissioningAuditReport:
        """Scan system-wide V1 vs V2 adoption, read modes, and legacy cleanup readiness."""
        from app.core.config import settings
        from app.modules.knowledge.models import KnowledgeDocument
        from app.modules.knowledge.services.scope_helper import apply_actor_scope

        # 1. Total collections
        stmt_col = apply_actor_scope(select(KnowledgeCollection), KnowledgeCollection, actor)
        col_res = await db.execute(stmt_col)
        cols = list(col_res.scalars().all())

        # 2. Total legacy documents
        stmt_doc = apply_actor_scope(select(func.count(KnowledgeDocument.id)), KnowledgeDocument, actor)
        doc_count_res = await db.execute(stmt_doc)
        total_docs = int(doc_count_res.scalar() or 0)

        # 3. Total V2 bindings
        stmt_bnd = apply_actor_scope(select(func.count(KnowledgeBinding.id)), KnowledgeBinding, actor)
        bnd_count_res = await db.execute(stmt_bnd)
        total_bindings = int(bnd_count_res.scalar() or 0)

        # 4. Mode counts
        rev_mode_count = 0
        shadow_mode_count = 0
        legacy_mode_count = 0
        sys_default_mode = getattr(settings, "RAG_REVISION_READ_MODE", "revisioned")

        for col in cols:
            policy = (col.collection_metadata or {}).get("canary_policy") or {}
            mode = policy.get("read_mode", "system")
            eff_mode = sys_default_mode if mode == "system" else mode
            if eff_mode == "revisioned":
                rev_mode_count += 1
            elif eff_mode == "shadow":
                shadow_mode_count += 1
            else:
                legacy_mode_count += 1

        # 5. Prunable revisions estimate
        prunable_res = await db.execute(
            select(func.count(KnowledgeIndexRevision.id)).where(
                KnowledgeIndexRevision.status.in_(["superseded", "failed"])
            )
        )
        total_prunable = int(prunable_res.scalar() or 0)

        total_assets = total_docs + total_bindings
        adoption_pct = (total_bindings / total_assets * 100.0) if total_assets > 0 else 100.0

        return SystemDecommissioningAuditReport(
            total_collections=len(cols),
            total_legacy_documents=total_docs,
            total_v2_bindings=total_bindings,
            v2_adoption_rate_pct=round(adoption_pct, 1),
            collections_in_revisioned_mode=rev_mode_count,
            collections_in_shadow_mode=shadow_mode_count,
            collections_in_legacy_mode=legacy_mode_count,
            total_prunable_revisions_estimate=total_prunable,
            audited_at=utcnow(),
        )


gc_service = KnowledgeArtifactGCService()
