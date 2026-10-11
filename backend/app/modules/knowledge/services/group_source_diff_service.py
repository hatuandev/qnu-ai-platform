"""Knowledge Group Source Diff Service — Evaluates snapshots, membership diffs, previews, and resolves state."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.documents.models import (
    DocumentGroup,
    DocumentGroupMembership,
    DocumentRevision,
    RepositoryDocument,
)
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeGroupSource,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.schemas import (
    DocumentSyncItemResult,
    PreviewGroupSourceDiffItem,
    PreviewGroupSourceDiffResponse,
)
from app.modules.knowledge.services.scope_helper import (
    get_scoped_collection,
)

logger = logging.getLogger(__name__)


def compute_membership_hash(members: list[tuple[str, str]]) -> str:
    """Compute stable SHA-256 hash independent of document ordering.

    members: list of (document_id, current_revision_id)
    """
    sorted_members = sorted(members, key=lambda x: (x[0], x[1]))
    raw_str = "|".join(f"{d}:{r}" for d, r in sorted_members)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def resolve_group_source_state(
    source_status: str,
    eligible_doc_count: int = 0,
    needs_build_count: int = 0,
    awaiting_publish_count: int = 0,
    ready_active_docs_count: int = 0,
    failed_count: int = 0,
    removed_count: int = 0,
    conflict_count: int = 0,
    not_ready_count: int = 0,
    total_docs: int | None = None,
) -> str:
    """Resolve honest group source state strictly honoring priority invariants:

    1. syncing
    2. failed (if source marked failed, has unresolved failure, or has conflict)
    3. review_required (if ready staging revisions await publishing, NEVER overridden by updates_available)
    4. updates_available (if new documents or revisions need staging build, or documents removed)
    5. ready (if ALL eligible documents are active on current revision, no errors, no pending staging)
    6. pending (if no eligible documents exist but some documents are processing/parsing)
    7. empty (only if group truly has NO eligible documents, NO processing/parsing docs, and NO failed docs)
    """
    effective_eligible = eligible_doc_count if eligible_doc_count > 0 else (total_docs or 0)

    if source_status == "syncing":
        return "syncing"
    if source_status == "failed" or failed_count > 0 or conflict_count > 0:
        return "failed"
    if awaiting_publish_count > 0 or source_status == "review_required":
        return "review_required"
    if needs_build_count > 0 or removed_count > 0:
        return "updates_available"
    if (
        effective_eligible > 0
        and ready_active_docs_count == effective_eligible
        and failed_count == 0
        and needs_build_count == 0
        and awaiting_publish_count == 0
    ):
        return "ready"
    if effective_eligible == 0 and not_ready_count > 0:
        return "pending"
    if effective_eligible == 0 and not_ready_count == 0 and failed_count == 0:
        return "empty"
    return "pending"


class GroupSourceDiffService:
    """Evaluates differential changes between Document Groups and Knowledge Collections."""

    async def evaluate_group_diff(
        self,
        db: AsyncSession,
        collection: KnowledgeCollection,
        group: DocumentGroup,
        source: KnowledgeGroupSource | None = None,
    ) -> dict[str, Any]:
        """Evaluate set difference between group members and collection bindings.

        Enforces strict workspace isolation across collection, group, documents, and bindings.
        """
        # Workspace isolation invariant check
        if group.tenant_id != collection.tenant_id or (
            collection.workspace_id and group.workspace_id != collection.workspace_id
        ):
            raise AppException(
                message=f"Không tìm thấy nhóm tài liệu '{group.id}'.",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 1. Query all active documents in group
        doc_stmt = (
            select(RepositoryDocument, DocumentRevision)
            .join(
                DocumentGroupMembership,
                DocumentGroupMembership.document_id == RepositoryDocument.id,
            )
            .outerjoin(
                DocumentRevision,
                DocumentRevision.id == RepositoryDocument.current_revision_id,
            )
            .where(
                DocumentGroupMembership.group_id == group.id,
                RepositoryDocument.is_active.is_(True),
                RepositoryDocument.tenant_id == collection.tenant_id,
            )
            .order_by(DocumentGroupMembership.added_at.asc())
        )
        if collection.workspace_id:
            doc_stmt = doc_stmt.where(RepositoryDocument.workspace_id == collection.workspace_id)

        rows = (await db.execute(doc_stmt)).all()
        group_doc_map: dict[str, tuple[RepositoryDocument, DocumentRevision | None]] = {
            doc.id: (doc, rev) for doc, rev in rows
        }

        # 2. Query existing active and pending bindings for this collection/source
        bnd_stmt = select(KnowledgeBinding).where(
            KnowledgeBinding.collection_id == collection.id,
            KnowledgeBinding.status.in_(["active", "pending"]),
            KnowledgeBinding.tenant_id == collection.tenant_id,
        )
        if collection.workspace_id:
            bnd_stmt = bnd_stmt.where(KnowledgeBinding.workspace_id == collection.workspace_id)

        all_collection_bindings = (await db.execute(bnd_stmt)).scalars().all()
        bound_map: dict[str, KnowledgeBinding] = {b.repository_document_id: b for b in all_collection_bindings}

        # 2b. Batch query newest index revisions for existing bindings to detect ready staging indexes
        binding_ids = [b.id for b in all_collection_bindings]
        idx_revisions_map: dict[str, list[KnowledgeIndexRevision]] = {}
        if binding_ids:
            idx_stmt = (
                select(KnowledgeIndexRevision)
                .where(KnowledgeIndexRevision.binding_id.in_(binding_ids))
                .order_by(KnowledgeIndexRevision.revision_no.desc())
            )
            idx_rows = (await db.execute(idx_stmt)).scalars().all()
            for idx_rev in idx_rows:
                idx_revisions_map.setdefault(idx_rev.binding_id, []).append(idx_rev)

        # 3. Categorize items
        items: list[PreviewGroupSourceDiffItem] = []
        desired_pairs: list[tuple[str, str]] = []

        added_docs: list[tuple[RepositoryDocument, DocumentRevision]] = []
        updated_docs: list[tuple[RepositoryDocument, DocumentRevision, KnowledgeBinding]] = []
        adoptable_docs: list[tuple[RepositoryDocument, DocumentRevision, KnowledgeBinding]] = []
        awaiting_publish_docs: list[
            tuple[RepositoryDocument, DocumentRevision, KnowledgeBinding, KnowledgeIndexRevision]
        ] = []
        conflict_docs: list[tuple[RepositoryDocument, DocumentRevision, KnowledgeBinding]] = []
        removed_bindings: list[KnowledgeBinding] = []

        unchanged_count = 0
        not_ready_count = 0
        failed_count = 0
        needs_build_count = 0
        awaiting_publish_count = 0
        publishable_count = 0
        ready_active_docs_count = 0

        # Traverse group members
        for doc_id, (doc, rev) in group_doc_map.items():
            binding = bound_map.get(doc_id)
            doc_file_name = getattr(doc, "file_name", None) or getattr(doc, "title", "document.pdf")

            if not rev or rev.status != "ready":
                if rev and rev.status in ("failed", "cancelled"):
                    failed_count += 1
                    items.append(
                        PreviewGroupSourceDiffItem(
                            document_id=doc.id,
                            title=doc.title,
                            file_name=doc_file_name,
                            revision_id=rev.id if rev else None,
                            revision_status=rev.status if rev else None,
                            category="failed",
                            reason=f"Phiên bản tài liệu bị lỗi ({rev.status if rev else 'chưa có'}).",
                        )
                    )
                else:
                    not_ready_count += 1
                    status_label = rev.status if rev else "chưa có phiên bản"
                    items.append(
                        PreviewGroupSourceDiffItem(
                            document_id=doc.id,
                            title=doc.title,
                            file_name=doc_file_name,
                            revision_id=rev.id if rev else None,
                            revision_status=rev.status if rev else None,
                            category="not_ready",
                            reason=f"Tài liệu chưa sẵn sàng (trạng thái: {status_label}).",
                        )
                    )
            else:
                # Revision is ready in RepositoryDocument: candidate pair for membership hash
                desired_pairs.append((doc.id, rev.id))

                # Check conflict: does this document belong to a different group source in this collection?
                if (
                    binding
                    and binding.group_source_id is not None
                    and (source is None or binding.group_source_id != source.id)
                    and binding.status in ("active", "pending")
                ):
                    conflict_docs.append((doc, rev, binding))
                    failed_count += 1
                    items.append(
                        PreviewGroupSourceDiffItem(
                            document_id=doc.id,
                            title=doc.title,
                            file_name=doc_file_name,
                            revision_id=rev.id,
                            revision_status="ready",
                            category="failed",
                            reason=f"Tài liệu '{doc.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                        )
                    )
                    continue

                if not binding:
                    # New document without binding: needs build
                    needs_build_count += 1
                    added_docs.append((doc, rev))
                    items.append(
                        PreviewGroupSourceDiffItem(
                            document_id=doc.id,
                            title=doc.title,
                            file_name=doc_file_name,
                            revision_id=rev.id,
                            revision_status="ready",
                            category="added",
                            reason="Tài liệu mới trong nhóm, sẵn sàng đưa vào kho tri thức.",
                        )
                    )
                else:
                    # Document already bound in collection
                    bnd_idx_list = idx_revisions_map.get(binding.id, [])
                    ready_staging = next(
                        (r for r in bnd_idx_list if r.source_revision_id == rev.id and r.status == "ready"),
                        None,
                    )
                    is_active_up_to_date = (
                        binding.status == "active"
                        and binding.active_index_revision_id is not None
                        and binding.source_revision_id == rev.id
                    )

                    # Distinct handling: Does binding already belong to THIS source?
                    is_already_owned_by_source = bool(source and binding.group_source_id == source.id)

                    if binding.group_source_id is None and is_active_up_to_date:
                        # Ownerless binding already active on current revision: adopt into source without rebuild!
                        adoptable_docs.append((doc, rev, binding))
                        items.append(
                            PreviewGroupSourceDiffItem(
                                document_id=doc.id,
                                title=doc.title,
                                file_name=doc_file_name,
                                revision_id=rev.id,
                                revision_status="ready",
                                category="added",
                                reason="Tài liệu đã có chỉ mục hoạt động, sẵn sàng tiếp nhận vào nguồn nhóm.",
                            )
                        )
                    elif is_already_owned_by_source and is_active_up_to_date:
                        unchanged_count += 1
                        ready_active_docs_count += 1
                        items.append(
                            PreviewGroupSourceDiffItem(
                                document_id=doc.id,
                                title=doc.title,
                                file_name=doc_file_name,
                                revision_id=rev.id,
                                revision_status="ready",
                                category="unchanged",
                                reason="Đã đồng bộ với phiên bản hiện tại.",
                            )
                        )
                    elif ready_staging:
                        # Staging index already built for current revision, waiting for publication
                        awaiting_publish_count += 1
                        publishable_count += 1
                        awaiting_publish_docs.append((doc, rev, binding, ready_staging))
                        items.append(
                            PreviewGroupSourceDiffItem(
                                document_id=doc.id,
                                title=doc.title,
                                file_name=doc_file_name,
                                revision_id=rev.id,
                                revision_status="ready",
                                category="updated",
                                reason="Đã xây dựng chỉ mục staging sẵn sàng xuất bản.",
                            )
                        )
                    else:
                        # Needs staging build
                        needs_build_count += 1
                        updated_docs.append((doc, rev, binding))
                        reason_msg = (
                            f"Có phiên bản mới ({rev.revision_no}) cần xây dựng chỉ mục staging."
                            if binding.source_revision_id != rev.id
                            else "Chỉ mục staging chưa được xây dựng thành công."
                        )
                        items.append(
                            PreviewGroupSourceDiffItem(
                                document_id=doc.id,
                                title=doc.title,
                                file_name=doc_file_name,
                                revision_id=rev.id,
                                revision_status="ready",
                                category="updated",
                                reason=reason_msg,
                            )
                        )

        # Traverse bindings to find removed documents
        for doc_id, binding in bound_map.items():
            if source and binding.group_source_id == source.id and doc_id not in group_doc_map:
                removed_bindings.append(binding)
                rep_doc = await db.get(RepositoryDocument, doc_id)
                items.append(
                    PreviewGroupSourceDiffItem(
                        document_id=doc_id,
                        title=rep_doc.title if rep_doc else doc_id,
                        file_name=(getattr(rep_doc, "file_name", None) or getattr(rep_doc, "title", None) or doc_id) if rep_doc else doc_id,
                        revision_id=binding.source_revision_id,
                        revision_status="removed",
                        category="removed",
                        reason="Tài liệu không còn thuộc nhóm tài liệu này (chờ xác nhận gỡ bỏ).",
                    )
                )

        current_hash = compute_membership_hash(desired_pairs)
        last_hash = getattr(source, "last_membership_hash", None)
        has_changes = (
            (last_hash != current_hash)
            or bool(added_docs)
            or bool(updated_docs)
            or bool(adoptable_docs)
            or bool(removed_bindings)
            or (awaiting_publish_count > 0)
        )

        return {
            "group": group,
            "collection": collection,
            "desired_pairs": desired_pairs,
            "eligible_doc_count": len(desired_pairs),
            "membership_hash": current_hash,
            "last_membership_hash": last_hash,
            "has_changes": has_changes,
            "total_documents_in_group": len(group_doc_map),
            "added_count": len(added_docs) + len(adoptable_docs),
            "updated_count": len(updated_docs),
            "removed_count": len(removed_bindings),
            "unchanged_count": unchanged_count,
            "not_ready_count": not_ready_count,
            "failed_count": failed_count,
            "needs_build_count": needs_build_count,
            "awaiting_publish_count": awaiting_publish_count,
            "publishable_count": publishable_count,
            "ready_active_docs_count": ready_active_docs_count,
            "items": items,
            "added_docs": added_docs,
            "adoptable_docs": adoptable_docs,
            "awaiting_publish_docs": awaiting_publish_docs,
            "updated_docs": updated_docs,
            "conflict_docs": conflict_docs,
            "removed_bindings": removed_bindings,
            "group_doc_map": group_doc_map,
            "bound_map": bound_map,
            "idx_revisions_map": idx_revisions_map,
        }

    async def preview_attach_group(
        self,
        db: AsyncSession,
        collection_id: str,
        group_id: str,
        actor: Any | None = None,
    ) -> PreviewGroupSourceDiffResponse:
        """Preview document classification before attaching a group."""
        col = await get_scoped_collection(db, collection_id, actor=actor)
        group = await db.get(DocumentGroup, group_id)
        if (
            not group
            or group.tenant_id != col.tenant_id
            or (col.workspace_id and group.workspace_id != col.workspace_id)
        ):
            raise AppException(
                message=f"Không tìm thấy nhóm tài liệu '{group_id}'.",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        diff = await self.evaluate_group_diff(db=db, collection=col, group=group, source=None)

        return PreviewGroupSourceDiffResponse(
            source_id=None,
            collection_id=col.id,
            group_id=group.id,
            group_name=group.name,
            membership_hash=diff["membership_hash"],
            last_membership_hash=None,
            has_changes=diff["has_changes"],
            total_documents_in_group=diff["total_documents_in_group"],
            added_count=diff["added_count"],
            updated_count=diff["updated_count"],
            removed_count=diff["removed_count"],
            unchanged_count=diff["unchanged_count"],
            not_ready_count=diff["not_ready_count"],
            failed_count=diff["failed_count"],
            needs_build_count=diff["needs_build_count"],
            awaiting_publish_count=diff["awaiting_publish_count"],
            publishable_count=diff["publishable_count"],
            items=diff["items"],
        )

    async def preview_source_sync(
        self,
        db: AsyncSession,
        collection_id: str,
        source_id: str,
        actor: Any | None = None,
    ) -> PreviewGroupSourceDiffResponse:
        """Preview incremental diff for an already attached group source."""
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

        diff = await self.evaluate_group_diff(db=db, collection=col, group=group, source=source)

        return PreviewGroupSourceDiffResponse(
            source_id=source.id,
            collection_id=col.id,
            group_id=group.id,
            group_name=group.name,
            membership_hash=diff["membership_hash"],
            last_membership_hash=diff["last_membership_hash"],
            has_changes=diff["has_changes"],
            total_documents_in_group=diff["total_documents_in_group"],
            added_count=diff["added_count"],
            updated_count=diff["updated_count"],
            removed_count=diff["removed_count"],
            unchanged_count=diff["unchanged_count"],
            not_ready_count=diff["not_ready_count"],
            failed_count=diff["failed_count"],
            needs_build_count=diff["needs_build_count"],
            awaiting_publish_count=diff["awaiting_publish_count"],
            publishable_count=diff["publishable_count"],
            items=diff["items"],
        )


group_source_diff_service = GroupSourceDiffService()


def _upsert_failed_item(
    items: list[DocumentSyncItemResult],
    failed_item: DocumentSyncItemResult,
    *,
    replace_failed: bool,
) -> None:
    """Keep one result per document and promote the most relevant failure."""
    for index, existing_item in enumerate(items):
        if existing_item.document_id != failed_item.document_id:
            continue
        if replace_failed or existing_item.status != "failed":
            items[index] = failed_item
        return
    items.append(failed_item)


def populate_failed_items_from_diff(
    diff: dict[str, Any],
    items: list[DocumentSyncItemResult],
    failed_document_ids: set[str],
) -> None:
    """Bổ sung các lỗi từ diff vào items và failed_document_ids với độ ưu tiên đúng.

    Độ ưu tiên bất biến:
    1. Conflict ownership (DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE) - Lỗi chuyên biệt cao nhất
    2. Document revision failed/cancelled (DOCUMENT_REVISION_FAILED) - Lỗi phiên bản văn bản
    """
    conflict_docs = diff.get("conflict_docs", [])
    conflict_doc_ids = {doc.id for doc, _, _ in conflict_docs}

    # 1. Ưu tiên cao: Conflict ownership
    for doc, rev, existing_bnd in conflict_docs:
        failed_document_ids.add(doc.id)
        _upsert_failed_item(
            items,
            DocumentSyncItemResult(
                document_id=doc.id,
                binding_id=existing_bnd.id if existing_bnd else None,
                source_revision_id=rev.id if rev else None,
                status="failed",
                error_code="DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE",
                error_message=f"Tài liệu '{getattr(doc, 'title', doc.id)}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
            ),
            replace_failed=True,
        )

    # 2. Ưu tiên thường: Revision failed/cancelled
    for itm in diff.get("items", []):
        if getattr(itm, "category", None) != "failed" or itm.document_id in conflict_doc_ids:
            continue
        failed_document_ids.add(itm.document_id)
        _upsert_failed_item(
            items,
            DocumentSyncItemResult(
                document_id=itm.document_id,
                source_revision_id=getattr(itm, "revision_id", None),
                status="failed",
                error_code="DOCUMENT_REVISION_FAILED",
                error_message=getattr(itm, "reason", None) or "Phiên bản tài liệu bị lỗi.",
            ),
            replace_failed=False,
        )
