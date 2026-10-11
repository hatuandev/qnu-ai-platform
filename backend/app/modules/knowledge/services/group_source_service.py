"""Knowledge Group Source Service — Facade managing long-lived document group sources for knowledge collections."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models import DocumentGroup
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeGroupSource,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.schemas import (
    AttachGroupSourceRequest,
    CollectionSummaryMetrics,
    DetachGroupSourceRequest,
    DetachGroupSourceResponse,
    KnowledgeGroupSourceResponse,
    PreviewGroupSourceDiffResponse,
    PublishGroupSourceResponse,
    SyncGroupSourceRequest,
    SyncGroupSourceResponse,
)
from app.modules.knowledge.services.group_source_diff_service import (
    GroupSourceDiffService,
    compute_membership_hash,
    resolve_group_source_state,
)
from app.modules.knowledge.services.group_source_publish_service import (
    GroupSourcePublishService,
)
from app.modules.knowledge.services.group_source_sync_service import (
    GroupSourceSyncService,
)
from app.modules.knowledge.services.index_build_service import IndexBuildService
from app.modules.knowledge.services.scope_helper import (
    get_scoped_collection,
)

logger = logging.getLogger(__name__)

# Re-export compute_membership_hash for backwards compatibility
__all__ = ["GroupSourceService", "compute_membership_hash", "group_source_service"]


class GroupSourceService:
    """Facade orchestrating differential analysis, synchronization, and publication of group sources."""

    def __init__(
        self,
        index_build_service: IndexBuildService | None = None,
        diff_service: GroupSourceDiffService | None = None,
    ) -> None:
        self.index_builder = index_build_service or IndexBuildService()
        self._diff_service = diff_service or GroupSourceDiffService()
        self.sync_service = GroupSourceSyncService(self.index_builder, self._diff_service)
        self.publish_service = GroupSourcePublishService(self.index_builder, self._diff_service)

    @property
    def diff_service(self) -> Any:
        return self._diff_service

    @diff_service.setter
    def diff_service(self, value: Any) -> None:
        self._diff_service = value
        if hasattr(self, "sync_service"):
            self.sync_service.diff_service = value
        if hasattr(self, "publish_service"):
            self.publish_service.diff_service = value

    async def _evaluate_group_diff(
        self,
        db: AsyncSession,
        collection: KnowledgeCollection,
        group: DocumentGroup,
        source: KnowledgeGroupSource | None = None,
    ) -> dict[str, Any]:
        """Internal helper evaluating set difference between group members and collection bindings."""
        return await self.diff_service.evaluate_group_diff(
            db=db, collection=collection, group=group, source=source
        )

    async def preview_attach_group(
        self,
        db: AsyncSession,
        collection_id: str,
        group_id: str,
        actor: Any | None = None,
    ) -> PreviewGroupSourceDiffResponse:
        """Preview document classification before attaching a group."""
        return await self.diff_service.preview_attach_group(
            db=db, collection_id=collection_id, group_id=group_id, actor=actor
        )

    async def preview_source_sync(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        actor: Any | None = None,
    ) -> PreviewGroupSourceDiffResponse:
        """Preview incremental diff for an already attached group source."""
        return await self.diff_service.preview_source_sync(
            db=db, collection_id=collection_id, source_id=source_id, actor=actor
        )

    async def attach_group_source(
        self,
        db: AsyncSession,
        collection_id: str,
        req: AttachGroupSourceRequest,
        actor: Any | None = None,
    ) -> KnowledgeGroupSourceResponse:
        """Attach a document group as a persistent source, building staging indexes."""
        return await self.sync_service.attach_group_source(
            db=db, collection_id=collection_id, req=req, actor=actor
        )

    async def sync_group_source(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        req: SyncGroupSourceRequest,
        actor: Any | None = None,
    ) -> SyncGroupSourceResponse:
        """Synchronize group source changes into bindings and staging index revisions."""
        return await self.sync_service.sync_group_source(
            db=db, collection_id=collection_id, source_id=source_id, req=req, actor=actor
        )

    async def publish_group_source(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        actor: Any | None = None,
    ) -> PublishGroupSourceResponse:
        """Promote all validated staging index revisions for a group source to active."""
        return await self.publish_service.publish_group_source(
            db=db, collection_id=collection_id, source_id=source_id, actor=actor
        )

    async def detach_group_source(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        req: DetachGroupSourceRequest,
        actor: Any | None = None,
    ) -> DetachGroupSourceResponse:
        """Detach a document group source from a collection."""
        return await self.publish_service.detach_group_source(
            db=db, collection_id=collection_id, source_id=source_id, req=req, actor=actor
        )

    async def list_group_sources(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> list[KnowledgeGroupSourceResponse]:
        """List all active group sources for a collection with dynamic status and metrics."""
        col = await get_scoped_collection(db, collection_id, actor=actor)

        stmt = (
            select(KnowledgeGroupSource, DocumentGroup)
            .join(DocumentGroup, DocumentGroup.id == KnowledgeGroupSource.document_group_id)
            .where(
                KnowledgeGroupSource.collection_id == col.id,
                KnowledgeGroupSource.status != "detached",
                KnowledgeGroupSource.tenant_id == col.tenant_id,
            )
            .order_by(KnowledgeGroupSource.created_at.asc())
        )
        if col.workspace_id:
            stmt = stmt.where(KnowledgeGroupSource.workspace_id == col.workspace_id)

        rows = (await db.execute(stmt)).all()
        results: list[KnowledgeGroupSourceResponse] = []

        for src, group in rows:
            # Evaluate current diff against group
            diff = await self.diff_service.evaluate_group_diff(
                db=db, collection=col, group=group, source=src
            )

            # Query published bindings count for this source
            pub_stmt = (
                select(func.count(KnowledgeBinding.id))
                .where(
                    KnowledgeBinding.group_source_id == src.id,
                    KnowledgeBinding.status == "active",
                    KnowledgeBinding.active_index_revision_id.is_not(None),
                    KnowledgeBinding.tenant_id == col.tenant_id,
                )
            )
            if col.workspace_id:
                pub_stmt = pub_stmt.where(KnowledgeBinding.workspace_id == col.workspace_id)

            published_count = (await db.execute(pub_stmt)).scalar() or 0

            # Compute effective status strictly honoring invariant priority
            effective_status = resolve_group_source_state(
                source_status=src.status,
                eligible_doc_count=diff["eligible_doc_count"],
                needs_build_count=diff["needs_build_count"],
                awaiting_publish_count=diff["awaiting_publish_count"],
                ready_active_docs_count=diff["ready_active_docs_count"],
                failed_count=diff["failed_count"],
                removed_count=diff["removed_count"],
                conflict_count=len(diff["conflict_docs"]),
                not_ready_count=diff["not_ready_count"],
            )

            results.append(
                KnowledgeGroupSourceResponse(
                    id=src.id,
                    collection_id=src.collection_id,
                    document_group_id=src.document_group_id,
                    group_name=group.name,
                    group_description=group.description,
                    sync_policy=src.sync_policy,
                    chunk_strategy=src.chunk_strategy,
                    status=effective_status,
                    last_synced_at=src.last_synced_at,
                    last_membership_hash=src.last_membership_hash,
                    total_documents=diff["total_documents_in_group"],
                    published_count=published_count,
                    new_revision_count=len(diff["updated_docs"]),
                    new_document_count=len(diff["added_docs"]),
                    not_ready_count=diff["not_ready_count"],
                    failed_count=diff["failed_count"],
                    needs_build_count=diff["needs_build_count"],
                    awaiting_publish_count=diff["awaiting_publish_count"],
                    publishable_count=diff["publishable_count"],
                    has_updates=diff["has_changes"],
                    items=[],
                    created_at=src.created_at,
                    updated_at=src.updated_at,
                )
            )

        return results

    async def get_collection_summary_metrics(
        self,
        db: AsyncSession,
        collection_id: str,
        actor: Any | None = None,
    ) -> CollectionSummaryMetrics:
        """Calculate real business status and metrics from sources and active index revisions."""
        col = await get_scoped_collection(db, collection_id, actor=actor)

        # 1. Total sources
        src_stmt = select(KnowledgeGroupSource).where(
            KnowledgeGroupSource.collection_id == col.id,
            KnowledgeGroupSource.status != "detached",
            KnowledgeGroupSource.tenant_id == col.tenant_id,
        )
        if col.workspace_id:
            src_stmt = src_stmt.where(KnowledgeGroupSource.workspace_id == col.workspace_id)

        sources = (await db.execute(src_stmt)).scalars().all()
        total_sources = len(sources)

        # 2. Published documents count & active chunks count
        pub_stmt = (
            select(
                func.count(KnowledgeBinding.id),
                func.coalesce(func.sum(KnowledgeIndexRevision.chunk_count), 0),
            )
            .join(
                KnowledgeIndexRevision,
                KnowledgeIndexRevision.id == KnowledgeBinding.active_index_revision_id,
            )
            .where(
                KnowledgeBinding.collection_id == col.id,
                KnowledgeBinding.status == "active",
                KnowledgeBinding.tenant_id == col.tenant_id,
            )
        )
        if col.workspace_id:
            pub_stmt = pub_stmt.where(KnowledgeBinding.workspace_id == col.workspace_id)

        pub_row = (await db.execute(pub_stmt)).one()
        published_docs_count = pub_row[0] or 0
        active_chunks_count = pub_row[1] or 0

        # 3. Documents needing sync count
        needing_sync_total = 0
        any_syncing = any(s.status == "syncing" for s in sources)
        any_failed = any(s.status == "failed" for s in sources)
        any_review = any(s.status == "review_required" for s in sources)
        any_updates = False

        for src in sources:
            group = await db.get(DocumentGroup, src.document_group_id)
            if group and group.tenant_id == col.tenant_id and (
                not col.workspace_id or group.workspace_id == col.workspace_id
            ):
                diff = await self.diff_service.evaluate_group_diff(
                    db=db, collection=col, group=group, source=src
                )
                if diff["has_changes"]:
                    any_updates = True
                needing_sync_total += (
                    len(diff["added_docs"])
                    + len(diff["updated_docs"])
                    + len(diff["removed_bindings"])
                )

        # 4. Collection status calculation
        if total_sources == 0 and published_docs_count == 0:
            col_status = "empty"
        elif any_syncing:
            col_status = "syncing"
        elif any_failed:
            col_status = "failed"
        elif any_review:
            col_status = "review_required"
        elif any_updates:
            col_status = "updates_available"
        elif published_docs_count > 0:
            col_status = "ready"
        else:
            col_status = "pending"

        meta = col.collection_metadata or {}
        dp = meta.get("data_processing") or {}
        model_name = dp.get("embedding_model")

        return CollectionSummaryMetrics(
            collection_id=col.id,
            total_sources=total_sources,
            published_documents_count=published_docs_count,
            documents_needing_sync_count=needing_sync_total,
            active_chunks_count=active_chunks_count,
            collection_status=col_status,
            configured_embedding_model=model_name,
            default_chunk_strategy=dp.get("chunk_strategy") or "ClauseBasedChunker",
        )


group_source_service = GroupSourceService()
