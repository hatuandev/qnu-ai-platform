"""Knowledge Group Source Publish Service — Validates, promotes staging revisions, and detaches sources."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.documents.models import DocumentGroup
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeGroupSource,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.schemas import (
    DetachGroupSourceRequest,
    DetachGroupSourceResponse,
    DocumentSyncItemResult,
    PublishGroupSourceResponse,
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


class GroupSourcePublishService:
    """Manages publication promotions to active index and clean source detachment."""

    def __init__(
        self,
        index_build_service: IndexBuildService | None = None,
        diff_service: Any | None = None,
    ) -> None:
        self.index_builder = index_build_service or IndexBuildService()
        self.diff_service = diff_service or group_source_diff_service

    async def publish_group_source(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        actor: Any | None = None,
    ) -> PublishGroupSourceResponse:
        """Promote all validated staging index revisions for a group source to active RAG index."""
        # 1. Enforce workspace isolation
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

        # 2. Evaluate diff to get map of eligible documents and current target revisions
        diff_before = await self.diff_service.evaluate_group_diff(
            db=db, collection=col, group=group, source=source
        )
        current_rev_map: dict[str, str] = dict(diff_before["desired_pairs"])

        # 3. Query all bindings for this source (both active and pending)
        b_stmt = select(KnowledgeBinding).where(
            KnowledgeBinding.group_source_id == source.id,
            KnowledgeBinding.status.in_(["active", "pending"]),
            KnowledgeBinding.tenant_id == col.tenant_id,
        )
        if col.workspace_id:
            b_stmt = b_stmt.where(KnowledgeBinding.workspace_id == col.workspace_id)

        bindings = (await db.execute(b_stmt)).scalars().all()

        # 4. Find 'ready' staging revisions strictly matching CURRENT document revision
        ready_revisions: list[tuple[KnowledgeBinding, KnowledgeIndexRevision]] = []
        for binding in bindings:
            current_target_rev = current_rev_map.get(binding.repository_document_id)
            if not current_target_rev:
                # Document is not in current ready desired pairs of group (e.g. removed or not ready)
                continue

            rev_stmt = (
                select(KnowledgeIndexRevision)
                .where(
                    KnowledgeIndexRevision.binding_id == binding.id,
                    KnowledgeIndexRevision.source_revision_id == current_target_rev,
                    KnowledgeIndexRevision.status == "ready",
                )
                .order_by(KnowledgeIndexRevision.revision_no.desc())
                .limit(1)
            )
            ready_rev = (await db.execute(rev_stmt)).scalar_one_or_none()
            if ready_rev and (
                binding.status != "active"
                or binding.source_revision_id != current_target_rev
                or binding.active_index_revision_id != ready_rev.id
            ):
                ready_revisions.append((binding, ready_rev))

        # INVARIANT: If no publishable revision exists matching CURRENT revision, reject with RFC 7807 error
        if not ready_revisions:
            raise AppException(
                message="Không có phiên bản chỉ mục nào ở trạng thái chờ xuất bản khớp với phiên bản tài liệu hiện tại.",
                code="NO_PUBLISHABLE_INDEX_REVISION",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 5. Promote each validated ready revision
        published_count = 0
        failed_document_ids: set[str] = set()
        items: list[DocumentSyncItemResult] = []

        for binding, ready_rev in ready_revisions:
            try:
                await self.index_builder.promote_index_revision(
                    db=db,
                    binding_id=binding.id,
                    index_revision_id=ready_rev.id,
                    expected_epoch=binding.active_epoch,
                    reason="Xuất bản chỉ mục nguồn nhóm tài liệu",
                    activated_by=getattr(actor, "actor_id", None) or "admin_publish",
                    actor=actor,
                )
                # INVARIANT: Only after promotion succeeds, update binding pointers and status
                binding.source_revision_id = ready_rev.source_revision_id
                binding.status = "active"
                binding.active_index_revision_id = ready_rev.id
                await db.flush()

                published_count += 1
                items.append(
                    DocumentSyncItemResult(
                        document_id=binding.repository_document_id,
                        binding_id=binding.id,
                        source_revision_id=ready_rev.source_revision_id,
                        staging_revision_id=ready_rev.id,
                        status="success",
                    )
                )
            except Exception as exc:
                failed_document_ids.add(binding.repository_document_id)
                logger.exception(
                    "Failed to promote staging index %s for binding %s",
                    ready_rev.id,
                    binding.id,
                )
                items.append(
                    DocumentSyncItemResult(
                        document_id=binding.repository_document_id,
                        binding_id=binding.id,
                        source_revision_id=binding.source_revision_id,
                        staging_revision_id=ready_rev.id,
                        status="failed",
                        error_code="PROMOTE_FAILED",
                        error_message=str(exc),
                    )
                )

        # 6. Determine source readiness against full group membership invariants
        diff_after = await self.diff_service.evaluate_group_diff(
            db=db, collection=col, group=group, source=source
        )
        total_eligible = diff_after["eligible_doc_count"]

        populate_failed_items_from_diff(
            diff=diff_after,
            items=items,
            failed_document_ids=failed_document_ids,
        )

        total_failed = len(failed_document_ids)
        source.status = resolve_group_source_state(
            source_status="pending",
            eligible_doc_count=total_eligible,
            needs_build_count=diff_after["needs_build_count"],
            awaiting_publish_count=diff_after["awaiting_publish_count"],
            ready_active_docs_count=diff_after["ready_active_docs_count"],
            failed_count=total_failed,
            removed_count=diff_after["removed_count"],
            conflict_count=len(diff_after["conflict_docs"]),
            not_ready_count=diff_after["not_ready_count"],
        )

        if total_failed > 0:
            message = f"Xuất bản gặp {total_failed} lỗi. Vui lòng bấm 'Thử lại'."
        elif source.status == "ready":
            message = f"Đã xuất bản thành công {published_count} tài liệu lên chỉ mục hoạt động. Nguồn đã sẵn sàng."
        elif source.status == "review_required":
            message = f"Đã xuất bản {published_count} tài liệu. Còn {diff_after['awaiting_publish_count']} tài liệu chờ xuất bản."
        elif source.status == "updates_available":
            message = f"Đã xuất bản {published_count} tài liệu. Có tài liệu mới cần xây dựng chỉ mục."
        else:
            message = f"Đã xuất bản thành công {published_count} tài liệu."

        source.updated_at = utcnow()
        await db.commit()
        await db.refresh(source)

        return PublishGroupSourceResponse(
            source_id=source.id,
            collection_id=col.id,
            status=source.status,
            published_count=published_count,
            failed_count=total_failed,
            message=message,
            items=items,
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
        col = await get_scoped_collection(db, collection_id, actor=actor)
        source = await db.get(KnowledgeGroupSource, source_id)
        if (
            not source
            or source.collection_id != col.id
            or source.tenant_id != col.tenant_id
            or (col.workspace_id and source.workspace_id != col.workspace_id)
        ):
            raise AppException(
                message=f"Không tìm thấy nguồn nhóm tài liệu '{source_id}'.",
                code="GROUP_SOURCE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        source.status = "detached"
        source.updated_at = utcnow()

        detached_bindings_count = 0
        if req.detach_bindings:
            b_stmt = select(KnowledgeBinding).where(
                KnowledgeBinding.group_source_id == source.id,
                KnowledgeBinding.status.in_(["active", "pending"]),
                KnowledgeBinding.tenant_id == col.tenant_id,
            )
            if col.workspace_id:
                b_stmt = b_stmt.where(KnowledgeBinding.workspace_id == col.workspace_id)
            bindings = (await db.execute(b_stmt)).scalars().all()
            for b in bindings:
                b.status = "detached"
                detached_bindings_count += 1

        await db.commit()

        return DetachGroupSourceResponse(
            source_id=source.id,
            collection_id=col.id,
            status="detached",
            detached_bindings_count=detached_bindings_count,
            message=f"Đã gỡ liên kết nguồn nhóm và hủy kích hoạt {detached_bindings_count} liên kết.",
        )


group_source_publish_service = GroupSourcePublishService()
