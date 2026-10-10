"""Document Group Service — Manages logical document groups and memberships."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.documents.models import (
    DocumentGroup,
    DocumentGroupMembership,
    DocumentRevision,
    RepositoryDocument,
)
from app.modules.documents.schemas import (
    AddGroupDocumentsRequest,
    AddGroupDocumentsResponse,
    AddGroupDocumentsResultItem,
    DocumentGroupCreate,
    DocumentGroupListItem,
    DocumentGroupListResponse,
    DocumentGroupResponse,
    DocumentGroupUpdate,
    GroupDocumentItem,
    GroupDocumentsResponse,
)

logger = logging.getLogger(__name__)


def _resolve_actor_id(actor: Any | None) -> str:
    """Extract audit actor identifier following hierarchy: actor.actor_id -> actor.username -> 'system'."""
    if not actor:
        return "system"
    return getattr(actor, "actor_id", None) or getattr(actor, "username", None) or "system"


class DocumentGroupService:
    """Service handling logical grouping of repository documents."""

    async def _resolve_scope(
        self,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> tuple[str, str]:
        resolved_tenant = getattr(actor, "tenant_id", None) or tenant_id or "tenant_qnu"
        resolved_workspace = getattr(actor, "workspace_id", None) or workspace_id or "workspace_qnu"
        return resolved_tenant, resolved_workspace

    async def create_group(
        self,
        db: AsyncSession,
        req: DocumentGroupCreate,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> DocumentGroupResponse:
        """Create a new logical document group with tenant/workspace scoping."""
        r_tenant, r_workspace = await self._resolve_scope(tenant_id, workspace_id, actor)

        # Check name conflict
        existing_stmt = select(DocumentGroup).where(
            DocumentGroup.tenant_id == r_tenant,
            DocumentGroup.workspace_id == r_workspace,
            func.lower(DocumentGroup.name) == req.name.strip().lower(),
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            raise AppException(
                message=f"Tên kho tài liệu '{req.name.strip()}' đã tồn tại trong workspace này.",
                code="DOCUMENT_GROUP_NAME_CONFLICT",
                status_code=status.HTTP_409_CONFLICT,
            )

        group_id = f"doc_grp_{uuid.uuid4().hex[:12]}"
        user_id = _resolve_actor_id(actor)

        group = DocumentGroup(
            id=group_id,
            tenant_id=r_tenant,
            workspace_id=r_workspace,
            name=req.name.strip(),
            description=req.description.strip() if req.description else None,
            created_by=user_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            lock_version=1,
        )
        db.add(group)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise AppException(
                message=f"Tên kho tài liệu '{req.name.strip()}' đã tồn tại trong workspace này.",
                code="DOCUMENT_GROUP_NAME_CONFLICT",
                status_code=status.HTTP_409_CONFLICT,
            )
        await db.refresh(group)

        return DocumentGroupResponse(
            id=group.id,
            tenant_id=group.tenant_id,
            workspace_id=group.workspace_id,
            name=group.name,
            description=group.description,
            created_by=group.created_by,
            created_at=group.created_at,
            updated_at=group.updated_at,
            lock_version=group.lock_version,
            total_documents=0,
            ready_documents=0,
            processing_documents=0,
            error_documents=0,
        )

    async def get_group(
        self,
        db: AsyncSession,
        group_id: str,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> DocumentGroupResponse:
        """Get group details including document counts and status breakdown."""
        r_tenant, r_workspace = await self._resolve_scope(tenant_id, workspace_id, actor)

        group = await db.get(DocumentGroup, group_id)
        if not group:
            raise AppException(
                message=f"Không tìm thấy kho tài liệu '{group_id}'",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if group.tenant_id != r_tenant or (r_workspace and group.workspace_id != r_workspace):
            raise AppException(
                message="Không có quyền truy cập kho tài liệu này.",
                code="DOCUMENT_GROUP_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Compute document KPIs for this group
        # Join memberships with documents and their current revisions
        kpi_stmt = (
            select(
                DocumentRevision.status,
                func.count(RepositoryDocument.id),
            )
            .select_from(DocumentGroupMembership)
            .join(RepositoryDocument, RepositoryDocument.id == DocumentGroupMembership.document_id)
            .outerjoin(DocumentRevision, DocumentRevision.id == RepositoryDocument.current_revision_id)
            .where(
                DocumentGroupMembership.group_id == group.id,
                RepositoryDocument.is_active.is_(True),
                RepositoryDocument.tenant_id == r_tenant,
                RepositoryDocument.workspace_id == r_workspace,
            )
            .group_by(DocumentRevision.status)
        )
        rows = (await db.execute(kpi_stmt)).all()

        total = 0
        ready = 0
        processing = 0
        error = 0
        for rev_status, cnt in rows:
            total += cnt
            if rev_status == "ready":
                ready += cnt
            elif rev_status in ("queued", "processing", "validating", "review_required"):
                processing += cnt
            elif rev_status in ("failed", "cancelled"):
                error += cnt
            else:
                # If rev_status is None, count as queued/processing
                processing += cnt

        return DocumentGroupResponse(
            id=group.id,
            tenant_id=group.tenant_id,
            workspace_id=group.workspace_id,
            name=group.name,
            description=group.description,
            created_by=group.created_by,
            created_at=group.created_at,
            updated_at=group.updated_at,
            lock_version=group.lock_version,
            total_documents=total,
            ready_documents=ready,
            processing_documents=processing,
            error_documents=error,
        )

    async def list_groups(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
        actor: Any | None = None,
    ) -> DocumentGroupListResponse:
        """List document groups in scope with summary KPIs."""
        r_tenant, r_workspace = await self._resolve_scope(tenant_id, workspace_id, actor)

        stmt = select(DocumentGroup).where(
            DocumentGroup.tenant_id == r_tenant,
        )
        if r_workspace:
            stmt = stmt.where(DocumentGroup.workspace_id == r_workspace)

        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    DocumentGroup.name.ilike(term),
                    DocumentGroup.description.ilike(term),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(DocumentGroup.updated_at.desc())
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)
        groups = (await db.execute(stmt)).scalars().all()

        if not groups:
            return DocumentGroupListResponse(items=[], total=total)

        group_ids = [g.id for g in groups]

        # Aggregate counts per group
        stats_stmt = (
            select(
                DocumentGroupMembership.group_id,
                DocumentRevision.status,
                func.count(RepositoryDocument.id),
            )
            .select_from(DocumentGroupMembership)
            .join(RepositoryDocument, RepositoryDocument.id == DocumentGroupMembership.document_id)
            .outerjoin(DocumentRevision, DocumentRevision.id == RepositoryDocument.current_revision_id)
            .where(
                DocumentGroupMembership.group_id.in_(group_ids),
                RepositoryDocument.is_active.is_(True),
                RepositoryDocument.tenant_id == r_tenant,
                RepositoryDocument.workspace_id == r_workspace,
            )
            .group_by(DocumentGroupMembership.group_id, DocumentRevision.status)
        )
        stats_rows = (await db.execute(stats_stmt)).all()

        stats_map: dict[str, dict[str, int]] = {
            g_id: {"total": 0, "ready": 0, "processing": 0, "error": 0} for g_id in group_ids
        }
        for g_id, rev_status, cnt in stats_rows:
            if g_id not in stats_map:
                continue
            stats_map[g_id]["total"] += cnt
            if rev_status == "ready":
                stats_map[g_id]["ready"] += cnt
            elif rev_status in ("queued", "processing", "validating", "review_required"):
                stats_map[g_id]["processing"] += cnt
            elif rev_status in ("failed", "cancelled"):
                stats_map[g_id]["error"] += cnt
            else:
                stats_map[g_id]["processing"] += cnt

        items = [
            DocumentGroupListItem(
                id=g.id,
                tenant_id=g.tenant_id,
                workspace_id=g.workspace_id,
                name=g.name,
                description=g.description,
                created_by=g.created_by,
                created_at=g.created_at,
                updated_at=g.updated_at,
                lock_version=g.lock_version,
                total_documents=stats_map[g.id]["total"],
                ready_documents=stats_map[g.id]["ready"],
                processing_documents=stats_map[g.id]["processing"],
                error_documents=stats_map[g.id]["error"],
            )
            for g in groups
        ]
        return DocumentGroupListResponse(items=items, total=total)

    async def update_group(
        self,
        db: AsyncSession,
        group_id: str,
        req: DocumentGroupUpdate,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> DocumentGroupResponse:
        """Update group details with atomic optimistic locking."""
        r_tenant, r_workspace = await self._resolve_scope(tenant_id, workspace_id, actor)

        update_values: dict[str, Any] = {
            "lock_version": DocumentGroup.lock_version + 1,
            "updated_at": datetime.now(UTC),
        }
        if req.name is not None:
            update_values["name"] = req.name.strip()
        if req.description is not None:
            update_values["description"] = req.description.strip() if req.description else None

        stmt = (
            update(DocumentGroup)
            .where(
                DocumentGroup.id == group_id,
                DocumentGroup.tenant_id == r_tenant,
                DocumentGroup.workspace_id == r_workspace,
                DocumentGroup.lock_version == req.expected_lock_version,
            )
            .values(**update_values)
        )

        try:
            result = await db.execute(stmt)
            if result.rowcount == 0:
                # Phân biệt nguyên nhân thất bại
                check_group = await db.get(DocumentGroup, group_id)
                if not check_group:
                    raise AppException(
                        message=f"Không tìm thấy kho tài liệu '{group_id}'",
                        code="DOCUMENT_GROUP_NOT_FOUND",
                        status_code=status.HTTP_404_NOT_FOUND,
                    )
                if check_group.tenant_id != r_tenant or (
                    r_workspace and check_group.workspace_id != r_workspace
                ):
                    raise AppException(
                        message="Không có quyền truy cập kho tài liệu này.",
                        code="DOCUMENT_GROUP_ACCESS_DENIED",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )
                raise AppException(
                    message=f"Xung đột phiên bản: Kho tài liệu đã bị sửa đổi bởi phiên khác (hiện tại: lock={check_group.lock_version}, yêu cầu: {req.expected_lock_version}).",
                    code="OPTIMISTIC_LOCK_CONFLICT",
                    status_code=status.HTTP_409_CONFLICT,
                )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise AppException(
                message=f"Tên kho tài liệu '{req.name}' đã tồn tại trong workspace này.",
                code="DOCUMENT_GROUP_NAME_CONFLICT",
                status_code=status.HTTP_409_CONFLICT,
            )

        return await self.get_group(
            db, group_id, tenant_id=r_tenant, workspace_id=r_workspace, actor=actor
        )

    async def delete_group(
        self,
        db: AsyncSession,
        group_id: str,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> None:
        """Delete group and its memberships. Repository documents and bindings remain untouched."""
        r_tenant, r_workspace = await self._resolve_scope(tenant_id, workspace_id, actor)

        group = await db.get(DocumentGroup, group_id)
        if not group:
            raise AppException(
                message=f"Không tìm thấy kho tài liệu '{group_id}'",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if group.tenant_id != r_tenant or (r_workspace and group.workspace_id != r_workspace):
            raise AppException(
                message="Không có quyền truy cập kho tài liệu này.",
                code="DOCUMENT_GROUP_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Delete memberships explicitly (and cascade helps as well)
        await db.execute(
            delete(DocumentGroupMembership).where(DocumentGroupMembership.group_id == group_id)
        )
        await db.delete(group)
        await db.commit()

    async def get_group_documents(
        self,
        db: AsyncSession,
        group_id: str,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        search: str | None = None,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 50,
        actor: Any | None = None,
    ) -> GroupDocumentsResponse:
        """List documents contained within a group with revision statuses."""
        r_tenant, r_workspace = await self._resolve_scope(tenant_id, workspace_id, actor)

        group = await db.get(DocumentGroup, group_id)
        if not group:
            raise AppException(
                message=f"Không tìm thấy kho tài liệu '{group_id}'",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if group.tenant_id != r_tenant or (r_workspace and group.workspace_id != r_workspace):
            raise AppException(
                message="Không có quyền truy cập kho tài liệu này.",
                code="DOCUMENT_GROUP_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        stmt = (
            select(
                RepositoryDocument,
                DocumentGroupMembership.added_at,
                DocumentGroupMembership.added_by,
                DocumentRevision.status.label("rev_status"),
            )
            .select_from(DocumentGroupMembership)
            .join(RepositoryDocument, RepositoryDocument.id == DocumentGroupMembership.document_id)
            .outerjoin(DocumentRevision, DocumentRevision.id == RepositoryDocument.current_revision_id)
            .where(
                DocumentGroupMembership.group_id == group_id,
                RepositoryDocument.is_active.is_(True),
                RepositoryDocument.tenant_id == r_tenant,
                RepositoryDocument.workspace_id == r_workspace,
            )
        )

        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    RepositoryDocument.title.ilike(term),
                    RepositoryDocument.file_name.ilike(term),
                    RepositoryDocument.document_number.ilike(term),
                )
            )

        if status_filter and status_filter.strip():
            sf = status_filter.strip().lower()
            if sf == "ready":
                stmt = stmt.where(DocumentRevision.status == "ready")
            elif sf == "processing":
                stmt = stmt.where(DocumentRevision.status.in_(["processing", "validating"]))
            elif sf == "queued":
                stmt = stmt.where(DocumentRevision.status == "queued")
            elif sf == "review_required":
                stmt = stmt.where(DocumentRevision.status == "review_required")
            elif sf in ("error", "failed", "cancelled"):
                stmt = stmt.where(DocumentRevision.status.in_(["failed", "cancelled"]))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(DocumentGroupMembership.added_at.desc())
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)

        rows = (await db.execute(stmt)).all()
        items: list[GroupDocumentItem] = []
        for doc, added_at, added_by, rev_status in rows:
            items.append(
                GroupDocumentItem(
                    id=doc.id,
                    title=doc.title,
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                    file_size_bytes=doc.file_size_bytes,
                    file_hash=doc.file_hash,
                    document_type_code=doc.document_type_code,
                    document_number=doc.document_number,
                    issuing_authority=doc.issuing_authority,
                    issued_date=doc.issued_date,
                    parse_status=doc.parse_status,
                    current_revision_id=doc.current_revision_id,
                    latest_revision_no=doc.latest_revision_no,
                    revision_status=rev_status or "queued",
                    added_at=added_at,
                    added_by=added_by,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                )
            )

        return GroupDocumentsResponse(
            group_id=group.id,
            items=items,
            total=total,
        )

    async def add_documents_to_group(
        self,
        db: AsyncSession,
        group_id: str,
        req: AddGroupDocumentsRequest,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> AddGroupDocumentsResponse:
        """Batch add documents to a group idempotently with individual outcome reporting."""
        r_tenant, r_workspace = await self._resolve_scope(tenant_id, workspace_id, actor)

        group = await db.get(DocumentGroup, group_id)
        if not group:
            raise AppException(
                message=f"Không tìm thấy kho tài liệu '{group_id}'",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if group.tenant_id != r_tenant or (r_workspace and group.workspace_id != r_workspace):
            raise AppException(
                message="Không có quyền truy cập kho tài liệu này.",
                code="DOCUMENT_GROUP_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        user_id = _resolve_actor_id(actor)
        results: list[AddGroupDocumentsResultItem] = []
        added_count = 0
        skipped_existing_count = 0
        failed_count = 0

        # Unique doc ids in request
        unique_doc_ids = list(dict.fromkeys(req.document_ids))

        # Check existing memberships
        existing_stmt = select(DocumentGroupMembership.document_id).where(
            DocumentGroupMembership.group_id == group.id,
            DocumentGroupMembership.document_id.in_(unique_doc_ids),
        )
        existing_doc_ids = set((await db.execute(existing_stmt)).scalars().all())

        # Check document validity & tenant match
        doc_stmt = select(RepositoryDocument).where(
            RepositoryDocument.id.in_(unique_doc_ids),
            RepositoryDocument.is_active.is_(True),
        )
        valid_docs = {d.id: d for d in (await db.execute(doc_stmt)).scalars().all()}

        now = datetime.now(UTC)
        for doc_id in unique_doc_ids:
            if doc_id in existing_doc_ids:
                results.append(
                    AddGroupDocumentsResultItem(
                        document_id=doc_id,
                        status="skipped_existing",
                        message="Tài liệu đã tồn tại trong kho tài liệu này.",
                    )
                )
                skipped_existing_count += 1
                continue

            doc = valid_docs.get(doc_id)
            if not doc:
                results.append(
                    AddGroupDocumentsResultItem(
                        document_id=doc_id,
                        status="failed",
                        message="Tài liệu không tồn tại hoặc đã bị vô hiệu hóa.",
                    )
                )
                failed_count += 1
                continue

            if doc.tenant_id != r_tenant or (r_workspace and doc.workspace_id != r_workspace):
                results.append(
                    AddGroupDocumentsResultItem(
                        document_id=doc_id,
                        status="failed",
                        message="Tài liệu không thuộc tenant/workspace của kho tài liệu này.",
                    )
                )
                failed_count += 1
                continue

            # Add membership
            membership = DocumentGroupMembership(
                group_id=group.id,
                document_id=doc.id,
                added_by=user_id,
                added_at=now,
            )
            db.add(membership)
            results.append(
                AddGroupDocumentsResultItem(
                    document_id=doc.id,
                    status="added",
                    message="Thêm vào kho tài liệu thành công.",
                )
            )
            added_count += 1

        if added_count > 0:
            group.updated_at = now
            await db.commit()

        return AddGroupDocumentsResponse(
            group_id=group.id,
            added_count=added_count,
            skipped_existing_count=skipped_existing_count,
            failed_count=failed_count,
            items=results,
        )

    async def remove_document_from_group(
        self,
        db: AsyncSession,
        group_id: str,
        document_id: str,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> None:
        """Remove a single document membership from a group."""
        r_tenant, r_workspace = await self._resolve_scope(tenant_id, workspace_id, actor)

        group = await db.get(DocumentGroup, group_id)
        if not group:
            raise AppException(
                message=f"Không tìm thấy kho tài liệu '{group_id}'",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if group.tenant_id != r_tenant or (r_workspace and group.workspace_id != r_workspace):
            raise AppException(
                message="Không có quyền truy cập kho tài liệu này.",
                code="DOCUMENT_GROUP_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        del_stmt = delete(DocumentGroupMembership).where(
            DocumentGroupMembership.group_id == group_id,
            DocumentGroupMembership.document_id == document_id,
        )
        result = await db.execute(del_stmt)
        if result.rowcount > 0:
            group.updated_at = datetime.now(UTC)
            await db.commit()


document_group_service = DocumentGroupService()
