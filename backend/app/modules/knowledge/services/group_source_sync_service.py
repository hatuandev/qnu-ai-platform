"""Knowledge Group Source Sync Service — Handles binding lifecycle, staging builds, and resilient sync retries."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.documents.models import DocumentGroup, DocumentRevision, RepositoryDocument
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeGroupSource,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.schemas import (
    AttachGroupSourceRequest,
    DocumentSyncItemResult,
    KnowledgeGroupSourceResponse,
    SyncGroupSourceRequest,
    SyncGroupSourceResponse,
)
from app.modules.knowledge.services.group_source_diff_service import (
    group_source_diff_service,
    populate_failed_items_from_diff,
    resolve_group_source_state,
)
from app.modules.knowledge.services.index_build_service import IndexBuildService
from app.modules.knowledge.services.scope_helper import (
    get_scoped_collection,
)

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class _SyncExecutionOutcome:
    diff_after: dict[str, Any]
    items: list[DocumentSyncItemResult] = field(default_factory=list)
    failed_document_ids: set[str] = field(default_factory=set)
    published_count: int = 0
    synced_count: int = 0
    review_required_count: int = 0
    detached_count: int = 0


async def _adopt_active_binding(
    db: AsyncSession,
    binding: KnowledgeBinding,
    source_id: str,
    chunk_strategy: str,
    sync_policy: str,
    target_revision_id: str,
) -> None:
    """Adopt an ownerless binding that is already active on the target revision without rebuild."""
    binding.group_source_id = source_id
    binding.chunk_strategy = chunk_strategy
    binding.sync_policy = sync_policy
    binding.source_revision_id = target_revision_id
    binding.status = "active"
    await db.flush()


async def _reuse_or_build_staging(
    db: AsyncSession,
    index_builder: IndexBuildService,
    binding: KnowledgeBinding,
    source_revision_id: str,
    chunk_strategy: str,
    actor: Any | None = None,
) -> KnowledgeIndexRevision:
    """Find existing ready staging index revision for target revision or build a new staging index."""
    ready_idx_stmt = (
        select(KnowledgeIndexRevision)
        .where(
            KnowledgeIndexRevision.binding_id == binding.id,
            KnowledgeIndexRevision.source_revision_id == source_revision_id,
            KnowledgeIndexRevision.status == "ready",
        )
        .order_by(KnowledgeIndexRevision.revision_no.desc())
        .limit(1)
    )
    existing_ready = (await db.execute(ready_idx_stmt)).scalar_one_or_none()
    if existing_ready:
        return existing_ready

    return await index_builder.build_staging_index(
        db=db,
        binding_id=binding.id,
        source_revision_id=source_revision_id,
        chunk_strategy=chunk_strategy,
        auto_activate=False,
        actor=actor,
    )


async def _promote_ready_revision(
    db: AsyncSession,
    index_builder: IndexBuildService,
    binding: KnowledgeBinding,
    idx_rev: KnowledgeIndexRevision,
    target_revision_id: str,
    reason: str,
    actor: Any | None = None,
) -> None:
    """Promote a validated staging revision to active RAG, updating binding pointers upon success."""
    await index_builder.promote_index_revision(
        db=db,
        binding_id=binding.id,
        index_revision_id=idx_rev.id,
        expected_epoch=binding.active_epoch,
        reason=reason,
        activated_by=getattr(actor, "actor_id", None) or "system_sync",
        actor=actor,
    )
    binding.source_revision_id = target_revision_id
    binding.status = "active"
    binding.active_index_revision_id = idx_rev.id
    await db.flush()


class GroupSourceSyncService:
    """Manages binding creation, staging index compilation, and resilient sync retries."""

    def __init__(
        self,
        index_build_service: IndexBuildService | None = None,
        diff_service: Any | None = None,
    ) -> None:
        self.index_builder = index_build_service or IndexBuildService()
        self.diff_service = diff_service or group_source_diff_service

    async def _execute_group_sync(
        self,
        db: AsyncSession,
        col: KnowledgeCollection,
        group: DocumentGroup,
        source: KnowledgeGroupSource,
        chunk_strategy: str,
        sync_policy: str,
        auto_publish: bool,
        confirm_detach_removed: bool,
        actor: Any | None = None,
    ) -> _SyncExecutionOutcome:
        """Unified internal pipeline executing differential synchronization for a group source."""
        diff = await self.diff_service.evaluate_group_diff(
            db=db, collection=col, group=group, source=source
        )

        items: list[DocumentSyncItemResult] = []
        failed_document_ids: set[str] = set()
        published_count = 0
        synced_count = 0
        review_required_count = 0
        detached_count = 0

        # Fast path: Empty or non-ready group
        if not diff["desired_pairs"]:
            populate_failed_items_from_diff(
                diff=diff,
                items=items,
                failed_document_ids=failed_document_ids,
            )

            total_failed = len(failed_document_ids)
            source.status = resolve_group_source_state(
                source_status="pending",
                eligible_doc_count=0,
                needs_build_count=diff["needs_build_count"],
                awaiting_publish_count=diff["awaiting_publish_count"],
                ready_active_docs_count=0,
                failed_count=total_failed,
                removed_count=diff["removed_count"],
                conflict_count=len(diff["conflict_docs"]),
                not_ready_count=diff["not_ready_count"],
            )
            if total_failed == 0:
                source.last_membership_hash = diff["membership_hash"]
                source.last_synced_at = utcnow()
            source.updated_at = utcnow()
            await db.flush()

            return _SyncExecutionOutcome(
                diff_after=diff,
                items=items,
                failed_document_ids=failed_document_ids,
            )

        # 1. Handle conflicts (already bound to another group source)
        for doc, rev, existing_bnd in diff["conflict_docs"]:
            failed_document_ids.add(doc.id)
            items.append(
                DocumentSyncItemResult(
                    document_id=doc.id,
                    binding_id=existing_bnd.id,
                    source_revision_id=rev.id,
                    status="failed",
                    error_code="DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE",
                    error_message=f"Tài liệu '{doc.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                )
            )

        # 2. Process Adoptable Documents (ownerless + already active on current revision)
        for doc, rev, binding in diff.get("adoptable_docs", []):
            await _adopt_active_binding(
                db=db,
                binding=binding,
                source_id=source.id,
                chunk_strategy=chunk_strategy,
                sync_policy=sync_policy,
                target_revision_id=rev.id,
            )
            published_count += 1
            synced_count += 1
            items.append(
                DocumentSyncItemResult(
                    document_id=doc.id,
                    binding_id=binding.id,
                    source_revision_id=rev.id,
                    staging_revision_id=binding.active_index_revision_id,
                    status="success",
                )
            )

        # 3. Process Awaiting Publish Documents (ready staging on current revision - reuse, DO NOT rebuild)
        for doc, rev, binding, ready_staging in diff.get("awaiting_publish_docs", []):
            if binding.group_source_id is None:
                binding.group_source_id = source.id
                binding.chunk_strategy = chunk_strategy
                binding.sync_policy = sync_policy
                await db.flush()

            if auto_publish:
                try:
                    await _promote_ready_revision(
                        db=db,
                        index_builder=self.index_builder,
                        binding=binding,
                        idx_rev=ready_staging,
                        target_revision_id=rev.id,
                        reason="Tự động xuất bản chỉ mục staging có sẵn khi đồng bộ",
                        actor=actor,
                    )
                    published_count += 1
                    synced_count += 1
                    items.append(
                        DocumentSyncItemResult(
                            document_id=doc.id,
                            binding_id=binding.id,
                            source_revision_id=rev.id,
                            staging_revision_id=ready_staging.id,
                            status="success",
                        )
                    )
                except Exception as p_err:
                    failed_document_ids.add(doc.id)
                    logger.exception("Promote failed for doc %s (awaiting_publish)", doc.id)
                    items.append(
                        DocumentSyncItemResult(
                            document_id=doc.id,
                            binding_id=binding.id,
                            source_revision_id=binding.source_revision_id,
                            staging_revision_id=ready_staging.id,
                            status="failed",
                            error_code="PROMOTE_FAILED",
                            error_message=str(p_err),
                        )
                    )
            else:
                review_required_count += 1
                synced_count += 1
                await db.flush()
                items.append(
                    DocumentSyncItemResult(
                        document_id=doc.id,
                        binding_id=binding.id,
                        source_revision_id=rev.id,
                        staging_revision_id=ready_staging.id,
                        status="success",
                    )
                )

        # 4. Helper for building and optionally promoting added/updated documents
        async def _build_and_handle_staging(
            target_binding: KnowledgeBinding,
            target_doc: RepositoryDocument,
            target_rev: DocumentRevision,
        ) -> None:
            nonlocal published_count, synced_count, review_required_count
            try:
                idx_rev = await _reuse_or_build_staging(
                    db=db,
                    index_builder=self.index_builder,
                    binding=target_binding,
                    source_revision_id=target_rev.id,
                    chunk_strategy=chunk_strategy,
                    actor=actor,
                )

                if idx_rev.status == "ready":
                    if auto_publish:
                        try:
                            await _promote_ready_revision(
                                db=db,
                                index_builder=self.index_builder,
                                binding=target_binding,
                                idx_rev=idx_rev,
                                target_revision_id=target_rev.id,
                                reason="Tự động xuất bản sau khi đồng bộ thành công",
                                actor=actor,
                            )
                            published_count += 1
                            synced_count += 1
                            items.append(
                                DocumentSyncItemResult(
                                    document_id=target_doc.id,
                                    binding_id=target_binding.id,
                                    source_revision_id=target_rev.id,
                                    staging_revision_id=idx_rev.id,
                                    status="success",
                                )
                            )
                        except Exception as p_err:
                            failed_document_ids.add(target_doc.id)
                            logger.exception("Promote failed for doc %s", target_doc.id)
                            items.append(
                                DocumentSyncItemResult(
                                    document_id=target_doc.id,
                                    binding_id=target_binding.id,
                                    source_revision_id=target_binding.source_revision_id,
                                    staging_revision_id=idx_rev.id,
                                    status="failed",
                                    error_code="PROMOTE_FAILED",
                                    error_message=str(p_err),
                                )
                            )
                    else:
                        review_required_count += 1
                        synced_count += 1
                        items.append(
                            DocumentSyncItemResult(
                                document_id=target_doc.id,
                                binding_id=target_binding.id,
                                source_revision_id=target_rev.id,
                                staging_revision_id=idx_rev.id,
                                status="success",
                            )
                        )
                else:
                    failed_document_ids.add(target_doc.id)
                    items.append(
                        DocumentSyncItemResult(
                            document_id=target_doc.id,
                            binding_id=target_binding.id,
                            source_revision_id=target_binding.source_revision_id,
                            staging_revision_id=idx_rev.id,
                            status="failed",
                            error_code=idx_rev.failure_code or "STAGING_BUILD_FAILED",
                            error_message=idx_rev.failure_detail or "Xây dựng chỉ mục staging thất bại",
                        )
                    )
            except Exception as exc:
                failed_document_ids.add(target_doc.id)
                logger.exception("Failed to build staging index for doc %s", target_doc.id)
                items.append(
                    DocumentSyncItemResult(
                        document_id=target_doc.id,
                        binding_id=target_binding.id,
                        source_revision_id=target_binding.source_revision_id,
                        status="failed",
                        error_code="STAGING_BUILD_EXCEPTION",
                        error_message=str(exc),
                    )
                )

        # 5. Process Added Documents (brand new to collection or existing pending binding)
        for doc, rev in diff["added_docs"]:
            b_stmt = select(KnowledgeBinding).where(
                KnowledgeBinding.collection_id == col.id,
                KnowledgeBinding.repository_document_id == doc.id,
            )
            existing_bnd = (await db.execute(b_stmt)).scalar_one_or_none()
            if existing_bnd:
                if (
                    existing_bnd.group_source_id is not None
                    and existing_bnd.group_source_id != source.id
                    and existing_bnd.status in ("active", "pending")
                ):
                    failed_document_ids.add(doc.id)
                    items.append(
                        DocumentSyncItemResult(
                            document_id=doc.id,
                            binding_id=existing_bnd.id,
                            source_revision_id=rev.id,
                            status="failed",
                            error_code="DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE",
                            error_message=f"Tài liệu '{doc.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                        )
                    )
                    continue
                binding = existing_bnd
                binding.group_source_id = source.id
                binding.chunk_strategy = chunk_strategy
                binding.sync_policy = sync_policy
                if not binding.active_index_revision_id:
                    binding.source_revision_id = rev.id
                    binding.status = "pending"
            else:
                binding = KnowledgeBinding(
                    collection_id=col.id,
                    repository_document_id=doc.id,
                    source_revision_id=rev.id,
                    group_source_id=source.id,
                    chunk_strategy=chunk_strategy,
                    sync_policy=sync_policy,
                    status="pending",
                    tenant_id=col.tenant_id,
                    workspace_id=col.workspace_id,
                )
                db.add(binding)

            await db.flush()
            await _build_and_handle_staging(binding, doc, rev)

        # 6. Process Updated Documents (new revision or needs rebuild)
        for doc, rev, binding in diff["updated_docs"]:
            if binding.group_source_id is None:
                binding.group_source_id = source.id
                binding.chunk_strategy = chunk_strategy
                binding.sync_policy = sync_policy
                await db.flush()

            await _build_and_handle_staging(binding, doc, rev)

        # 7. Process Removed Documents
        if confirm_detach_removed:
            for binding in diff.get("removed_bindings", []):
                binding.status = "detached"
                detached_count += 1
            await db.flush()

        # 8. Post-sync state re-evaluation
        diff_after = await self.diff_service.evaluate_group_diff(
            db=db, collection=col, group=group, source=source
        )

        populate_failed_items_from_diff(
            diff=diff_after,
            items=items,
            failed_document_ids=failed_document_ids,
        )

        total_failed = len(failed_document_ids)
        source.status = resolve_group_source_state(
            source_status="pending",
            eligible_doc_count=diff_after["eligible_doc_count"],
            needs_build_count=diff_after["needs_build_count"],
            awaiting_publish_count=diff_after["awaiting_publish_count"],
            ready_active_docs_count=diff_after["ready_active_docs_count"],
            failed_count=total_failed,
            removed_count=diff_after["removed_count"],
            conflict_count=len(diff_after["conflict_docs"]),
            not_ready_count=diff_after["not_ready_count"],
        )

        if total_failed == 0:
            source.last_membership_hash = diff_after["membership_hash"]
            source.last_synced_at = utcnow()

        source.updated_at = utcnow()
        await db.flush()

        return _SyncExecutionOutcome(
            diff_after=diff_after,
            items=items,
            failed_document_ids=failed_document_ids,
            published_count=published_count,
            synced_count=synced_count,
            review_required_count=review_required_count,
            detached_count=detached_count,
        )

    async def attach_group_source(
        self,
        db: AsyncSession,
        collection_id: str,
        req: AttachGroupSourceRequest,
        actor: Any | None = None,
    ) -> KnowledgeGroupSourceResponse:
        """Attach a document group as a persistent source, building staging indexes."""
        col = await get_scoped_collection(db, collection_id, actor=actor)
        group = await db.get(DocumentGroup, req.group_id)
        if (
            not group
            or group.tenant_id != col.tenant_id
            or (col.workspace_id and group.workspace_id != col.workspace_id)
        ):
            raise AppException(
                message=f"Không tìm thấy nhóm tài liệu '{req.group_id}'.",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Check existing source
        stmt = select(KnowledgeGroupSource).where(
            KnowledgeGroupSource.collection_id == col.id,
            KnowledgeGroupSource.document_group_id == group.id,
        )
        existing_source = (await db.execute(stmt)).scalar_one_or_none()

        if existing_source and existing_source.status != "detached":
            diff = await self.diff_service.evaluate_group_diff(
                db=db, collection=col, group=group, source=existing_source
            )
            pub_stmt = select(func.count(KnowledgeBinding.id)).where(
                KnowledgeBinding.group_source_id == existing_source.id,
                KnowledgeBinding.status == "active",
                KnowledgeBinding.active_index_revision_id.is_not(None),
            )
            published_count = (await db.execute(pub_stmt)).scalar() or 0
            resolved_status = resolve_group_source_state(
                source_status=existing_source.status,
                eligible_doc_count=diff["eligible_doc_count"],
                needs_build_count=diff["needs_build_count"],
                awaiting_publish_count=diff["awaiting_publish_count"],
                ready_active_docs_count=diff["ready_active_docs_count"],
                failed_count=diff["failed_count"],
                removed_count=diff["removed_count"],
                conflict_count=len(diff["conflict_docs"]),
                not_ready_count=diff["not_ready_count"],
            )
            return KnowledgeGroupSourceResponse(
                id=existing_source.id,
                collection_id=existing_source.collection_id,
                document_group_id=existing_source.document_group_id,
                group_name=group.name,
                group_description=group.description,
                sync_policy=existing_source.sync_policy,
                chunk_strategy=existing_source.chunk_strategy,
                status=resolved_status,
                last_synced_at=existing_source.last_synced_at,
                last_membership_hash=existing_source.last_membership_hash,
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
                created_at=existing_source.created_at,
                updated_at=existing_source.updated_at,
            )

        if existing_source:
            source = existing_source
            source.status = "syncing"
            source.sync_policy = req.sync_policy
            source.chunk_strategy = req.chunk_strategy
            source.updated_at = utcnow()
        else:
            source = KnowledgeGroupSource(
                collection_id=col.id,
                document_group_id=group.id,
                sync_policy=req.sync_policy,
                chunk_strategy=req.chunk_strategy,
                status="syncing",
                tenant_id=col.tenant_id,
                workspace_id=col.workspace_id,
            )
            db.add(source)
            await db.flush()

        res = await self._execute_group_sync(
            db=db,
            col=col,
            group=group,
            source=source,
            chunk_strategy=req.chunk_strategy,
            sync_policy=req.sync_policy,
            auto_publish=req.auto_activate,
            confirm_detach_removed=False,
            actor=actor,
        )

        await db.commit()
        await db.refresh(source)

        return KnowledgeGroupSourceResponse(
            id=source.id,
            collection_id=source.collection_id,
            document_group_id=source.document_group_id,
            group_name=group.name,
            group_description=group.description,
            sync_policy=source.sync_policy,
            chunk_strategy=source.chunk_strategy,
            status=source.status,
            last_synced_at=source.last_synced_at,
            last_membership_hash=source.last_membership_hash,
            total_documents=res.diff_after["total_documents_in_group"],
            published_count=res.published_count,
            new_revision_count=len(res.diff_after["updated_docs"]),
            new_document_count=len(res.diff_after["added_docs"]),
            not_ready_count=res.diff_after["not_ready_count"],
            failed_count=len(res.failed_document_ids),
            needs_build_count=res.diff_after["needs_build_count"],
            awaiting_publish_count=res.diff_after["awaiting_publish_count"],
            publishable_count=res.diff_after["publishable_count"],
            has_updates=res.diff_after["has_changes"] or (source.status == "failed"),
            items=res.items,
            created_at=source.created_at,
            updated_at=source.updated_at,
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
        col = await get_scoped_collection(db, collection_id, actor=actor)
        source = await db.get(KnowledgeGroupSource, source_id)
        if (
            not source
            or source.collection_id != col.id
            or source.tenant_id != col.tenant_id
            or (col.workspace_id and source.workspace_id != col.workspace_id)
            or source.status == "detached"
        ):
            raise AppException(
                message=f"Không tìm thấy nguồn nhóm tài liệu '{source_id}'.",
                code="GROUP_SOURCE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        group = await db.get(DocumentGroup, source.document_group_id)
        if (
            not group
            or group.tenant_id != col.tenant_id
            or (col.workspace_id and group.workspace_id != col.workspace_id)
        ):
            raise AppException(
                message=f"Nhóm tài liệu gốc '{source.document_group_id}' không tồn tại.",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        source.status = "syncing"
        await db.flush()

        chunk_strategy = req.chunk_strategy or source.chunk_strategy
        res = await self._execute_group_sync(
            db=db,
            col=col,
            group=group,
            source=source,
            chunk_strategy=chunk_strategy,
            sync_policy=source.sync_policy,
            auto_publish=req.auto_publish,
            confirm_detach_removed=req.confirm_detach_removed,
            actor=actor,
        )

        total_errors = len(res.failed_document_ids)
        if total_errors > 0:
            message = f"Đồng bộ hoàn tất với {total_errors} lỗi lập chỉ mục. Vui lòng bấm 'Thử lại'."
        elif source.status == "review_required":
            message = f"Đã lập chỉ mục {res.synced_count} tài liệu ở staging. Vui lòng bấm 'Xuất bản' để áp dụng cho RAG."
        elif source.status == "updates_available":
            message = f"Đồng bộ {res.synced_count} tài liệu. Vẫn còn tài liệu cần xây dựng chỉ mục hoặc chờ gỡ bỏ."
        elif source.status == "ready":
            message = f"Đồng bộ và xuất bản thành công {res.published_count} tài liệu. Nguồn đã sẵn sàng."
        elif source.status == "empty":
            message = "Nguồn nhóm chưa có tài liệu nào đủ điều kiện."
        else:
            message = "Nguồn nhóm tài liệu đã ở trạng thái mới nhất."

        await db.commit()
        await db.refresh(source)

        return SyncGroupSourceResponse(
            source_id=source.id,
            collection_id=col.id,
            status=source.status,
            synced_count=res.synced_count,
            detached_count=res.detached_count,
            failed_count=total_errors,
            review_required_count=res.review_required_count,
            published_count=res.published_count,
            new_membership_hash=source.last_membership_hash,
            message=message,
            items=res.items,
        )


group_source_sync_service = GroupSourceSyncService()
