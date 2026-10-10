"""Knowledge Binding Service — Manages bindings between Repository Documents and Knowledge Collections."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.documents.models import (
    DocumentGroup,
    DocumentGroupMembership,
    DocumentRevision,
    RepositoryDocument,
)
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
)
from app.modules.knowledge.schemas import (
    AttachDocumentGroupItemResult,
    AttachDocumentGroupRequest,
    AttachDocumentGroupResponse,
    AvailableRepositoryDocumentItem,
    AvailableRepositoryDocumentsResponse,
    BindingChunksListResponse,
    BindingResultItem,
    BindingSelectionItem,
    CreateKnowledgeBindingsRequest,
    CreateKnowledgeBindingsResponse,
    KnowledgeBindingResponse,
    KnowledgeChunkItemResponse,
    PreviewDocumentGroupItem,
    PreviewDocumentGroupRequest,
    PreviewDocumentGroupResponse,
)
from app.modules.knowledge.services.scope_helper import (
    get_scoped_binding,
    get_scoped_collection,
    get_scoped_index_revision,
)

logger = logging.getLogger(__name__)


class BindingService:
    """Service managing Knowledge Collections to Repository Documents bindings."""

    async def get_available_documents(
        self,
        db: AsyncSession,
        collection_id: str,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        actor: Any | None = None,
    ) -> AvailableRepositoryDocumentsResponse:
        """List repository documents with binding status for a given collection."""
        # 1. Verify collection exists in actor's scope
        col = await get_scoped_collection(db, collection_id, actor=actor)

        # 2. Build base query
        # Left join with KnowledgeBinding for this collection
        stmt = (
            select(RepositoryDocument, KnowledgeBinding.id.label("binding_id"))
            .outerjoin(
                KnowledgeBinding,
                (KnowledgeBinding.repository_document_id == RepositoryDocument.id)
                & (KnowledgeBinding.collection_id == collection_id)
                & (KnowledgeBinding.status != "detached"),
            )
            .where(
                RepositoryDocument.status == "active",
                RepositoryDocument.tenant_id == col.tenant_id,
            )
        )
        if col.workspace_id:
            stmt = stmt.where(RepositoryDocument.workspace_id == col.workspace_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    RepositoryDocument.title.ilike(term),
                    RepositoryDocument.file_name.ilike(term),
                    RepositoryDocument.document_number.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Pagination & order
        stmt = stmt.order_by(RepositoryDocument.created_at.desc())
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)

        rows = (await db.execute(stmt)).all()

        items: list[AvailableRepositoryDocumentItem] = []
        for rep_doc, bound_id in rows:
            items.append(
                AvailableRepositoryDocumentItem(
                    id=rep_doc.id,
                    document_code=rep_doc.document_number or rep_doc.id,
                    title=rep_doc.title,
                    file_name=rep_doc.file_name,
                    file_type=rep_doc.file_type,
                    file_size_bytes=rep_doc.file_size_bytes or 0,
                    current_revision_id=rep_doc.current_revision_id,
                    current_revision_no=rep_doc.latest_revision_no or 0,
                    revision_count=rep_doc.latest_revision_no or 0,
                    status=rep_doc.status,
                    is_bound=bound_id is not None,
                    bound_binding_id=bound_id,
                    created_at=rep_doc.created_at,
                    updated_at=rep_doc.updated_at,
                )
            )


        return AvailableRepositoryDocumentsResponse(items=items, total=total)

    async def create_bindings(
        self,
        db: AsyncSession,
        collection_id: str,
        req: CreateKnowledgeBindingsRequest,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> CreateKnowledgeBindingsResponse:
        """Create bindings from repository documents to a knowledge collection."""
        col = await get_scoped_collection(db, collection_id, actor=actor)

        resolved_tenant_id = getattr(actor, "tenant_id", None) or tenant_id or col.tenant_id
        resolved_workspace_id = getattr(actor, "workspace_id", None) or workspace_id or col.workspace_id

        results: list[BindingResultItem] = []
        created_count = 0
        skipped_count = 0
        failed_count = 0

        for item in req.items:
            # 1. Check existing binding
            existing_stmt = select(KnowledgeBinding).where(
                KnowledgeBinding.collection_id == collection_id,
                KnowledgeBinding.repository_document_id == item.repository_document_id,
            )
            existing_bnd = (await db.execute(existing_stmt)).scalar_one_or_none()
            if existing_bnd and existing_bnd.status != "detached":
                results.append(
                    BindingResultItem(
                        binding_id=existing_bnd.id,
                        repository_document_id=item.repository_document_id,
                        source_revision_id=existing_bnd.source_revision_id,
                        status="already_bound",
                        message="Tài liệu đã được liên kết vào bộ sưu tập.",
                        index_revision_id=existing_bnd.active_index_revision_id,
                    )
                )
                skipped_count += 1
                continue

            # 2. Check repository document
            rep_doc = await db.get(RepositoryDocument, item.repository_document_id)
            if not rep_doc:
                results.append(
                    BindingResultItem(
                        repository_document_id=item.repository_document_id,
                        status="failed",
                        message=f"Không tìm thấy tài liệu kho lưu trữ '{item.repository_document_id}'",
                    )
                )
                failed_count += 1
                continue
            if (
                rep_doc.tenant_id != resolved_tenant_id
                or (resolved_workspace_id and rep_doc.workspace_id != resolved_workspace_id)
            ):
                results.append(
                    BindingResultItem(
                        repository_document_id=item.repository_document_id,
                        status="failed",
                        message="Tài liệu không thuộc tenant/workspace của bộ sưu tập.",
                    )
                )
                failed_count += 1
                continue

            # 3. Resolve target revision
            target_rev_id = item.target_revision_id or rep_doc.current_revision_id
            if not target_rev_id:
                results.append(
                    BindingResultItem(
                        repository_document_id=item.repository_document_id,
                        status="failed",
                        message="Tài liệu chưa có phiên bản bóc tách nào trong kho lưu trữ.",
                    )
                )
                failed_count += 1
                continue

            rev = await db.get(DocumentRevision, target_rev_id)
            if not rev or rev.document_id != rep_doc.id or rev.status != "ready":
                results.append(
                    BindingResultItem(
                        repository_document_id=item.repository_document_id,
                        source_revision_id=target_rev_id,
                        status="failed",
                        message=f"Phiên bản '{target_rev_id}' không hợp lệ, chưa ready hoặc không thuộc tài liệu này.",
                    )
                )
                failed_count += 1
                continue

            # 4. Create or re-activate binding
            if existing_bnd and existing_bnd.status == "detached":
                existing_bnd.status = "active"
                existing_bnd.source_revision_id = target_rev_id
                existing_bnd.chunk_strategy = item.chunk_strategy or "ClauseBasedChunker"
                existing_bnd.sync_policy = item.sync_policy or "manual"
                binding = existing_bnd
            else:
                binding = KnowledgeBinding(
                    collection_id=collection_id,
                    repository_document_id=rep_doc.id,
                    source_revision_id=target_rev_id,
                    chunk_strategy=item.chunk_strategy or "ClauseBasedChunker",
                    sync_policy=item.sync_policy or "manual",
                    tenant_id=resolved_tenant_id,
                    workspace_id=resolved_workspace_id or "default",
                    status="active",
                )
                db.add(binding)

            await db.flush()

            index_revision_id = None
            if item.auto_activate:
                try:
                    from app.modules.knowledge.services.index_build_service import (
                        index_build_service,
                    )
                    idx_rev = await index_build_service.build_staging_index(
                        db=db,
                        binding_id=binding.id,
                        source_revision_id=target_rev_id,
                        chunk_strategy=item.chunk_strategy,
                        auto_activate=True,
                        actor=actor,
                    )
                    index_revision_id = idx_rev.id
                except Exception as exc:
                    logger.warning("Auto-activation for binding %s failed: %s", binding.id, exc)

            results.append(
                BindingResultItem(
                    binding_id=binding.id,
                    repository_document_id=rep_doc.id,
                    source_revision_id=target_rev_id,
                    status="created",
                    message="Liên kết thành công.",
                    index_revision_id=index_revision_id,
                )
            )
            created_count += 1

        await db.commit()

        return CreateKnowledgeBindingsResponse(
            collection_id=collection_id,
            created_count=created_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            bindings=results,
        )

    async def list_bindings(
        self,
        db: AsyncSession,
        collection_id: str,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        actor: Any | None = None,
    ) -> list[KnowledgeBindingResponse]:
        """List active bindings in a knowledge collection with document metadata."""
        col = await get_scoped_collection(db, collection_id, actor=actor)

        stmt = (
            select(KnowledgeBinding, RepositoryDocument)
            .join(
                RepositoryDocument,
                KnowledgeBinding.repository_document_id == RepositoryDocument.id,
            )
            .where(
                KnowledgeBinding.collection_id == collection_id,
                KnowledgeBinding.tenant_id == col.tenant_id,
            )
        )
        if col.workspace_id:
            stmt = stmt.where(KnowledgeBinding.workspace_id == col.workspace_id)

        if status:
            stmt = stmt.where(KnowledgeBinding.status == status)
        else:
            stmt = stmt.where(KnowledgeBinding.status != "detached")

        stmt = stmt.order_by(KnowledgeBinding.created_at.desc())
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)

        rows = (await db.execute(stmt)).all()
        items: list[KnowledgeBindingResponse] = []
        for bnd, rep_doc in rows:
            items.append(
                KnowledgeBindingResponse(
                    id=bnd.id,
                    collection_id=bnd.collection_id,
                    repository_document_id=bnd.repository_document_id,
                    source_revision_id=bnd.source_revision_id,
                    active_index_revision_id=bnd.active_index_revision_id,
                    active_epoch=bnd.active_epoch,
                    chunk_strategy=bnd.chunk_strategy,
                    sync_policy=bnd.sync_policy,
                    status=bnd.status,
                    document_title=rep_doc.title,
                    document_code=rep_doc.document_number or rep_doc.id,
                    file_name=rep_doc.file_name,
                    created_at=bnd.created_at,
                    updated_at=bnd.updated_at,
                )
            )
        return items

    async def get_binding(
        self,
        db: AsyncSession,
        binding_id: str,
        actor: Any | None = None,
    ) -> KnowledgeBindingResponse:
        """Get detail of a single knowledge binding."""
        bnd = await get_scoped_binding(db, binding_id, actor=actor)
        rep_doc = await db.get(RepositoryDocument, bnd.repository_document_id)
        if not rep_doc:
            raise EntityNotFoundError(f"Không tìm thấy tài liệu kho cho binding '{binding_id}'")

        return KnowledgeBindingResponse(
            id=bnd.id,
            collection_id=bnd.collection_id,
            repository_document_id=bnd.repository_document_id,
            source_revision_id=bnd.source_revision_id,
            active_index_revision_id=bnd.active_index_revision_id,
            active_epoch=bnd.active_epoch,
            chunk_strategy=bnd.chunk_strategy,
            sync_policy=bnd.sync_policy,
            status=bnd.status,
            document_title=rep_doc.title,
            document_code=rep_doc.document_number or rep_doc.id,
            file_name=rep_doc.file_name,
            created_at=bnd.created_at,
            updated_at=bnd.updated_at,
        )

    async def detach_binding(
        self,
        db: AsyncSession,
        binding_id: str,
        actor: Any | None = None,
    ) -> KnowledgeBindingResponse:
        """Detach a binding from a collection (soft delete)."""
        bnd = await get_scoped_binding(db, binding_id, actor=actor)
        bnd.status = "detached"
        await db.commit()
        return await self.get_binding(db, binding_id, actor=actor)

    async def list_binding_chunks(
        self,
        db: AsyncSession,
        binding_id: str,
        index_revision_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
        actor: Any | None = None,
    ) -> BindingChunksListResponse:
        """List chunks associated with a binding or a specific index revision."""
        bnd = await get_scoped_binding(db, binding_id, actor=actor)

        target_rev_id = index_revision_id or bnd.active_index_revision_id

        if target_rev_id:
            await get_scoped_index_revision(
                db, target_rev_id, binding_id=binding_id, actor=actor
            )

        # Base filter
        stmt = select(KnowledgeChunk)
        count_stmt = select(func.count(KnowledgeChunk.id))

        if target_rev_id:
            stmt = stmt.where(
                KnowledgeChunk.binding_id == binding_id,
                KnowledgeChunk.index_revision_id == target_rev_id,
            )
            count_stmt = count_stmt.where(
                KnowledgeChunk.binding_id == binding_id,
                KnowledgeChunk.index_revision_id == target_rev_id,
            )
        else:
            stmt = stmt.where(KnowledgeChunk.binding_id == binding_id)
            count_stmt = count_stmt.where(KnowledgeChunk.binding_id == binding_id)

        # Count total
        total = (await db.execute(count_stmt)).scalar() or 0

        # Pagination & ordering
        stmt = stmt.order_by(KnowledgeChunk.chunk_index.asc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()

        items = [
            KnowledgeChunkItemResponse(
                id=c.id,
                chunk_index=c.chunk_index,
                content=c.content,
                token_count=c.token_count,
                section=c.section,
                page_number=c.page_number,
                chunk_metadata=c.chunk_metadata or {},
                index_revision_id=c.index_revision_id,
            )
            for c in rows
        ]

        return BindingChunksListResponse(
            binding_id=binding_id,
            index_revision_id=target_rev_id,
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )

    async def _evaluate_group_members(
        self,
        db: AsyncSession,
        collection_id: str,
        group_id: str,
        actor: Any | None = None,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Internal helper evaluating group members for collection binding without modifying state."""
        # 1. Verify scoped collection
        col = await get_scoped_collection(db, collection_id, actor=actor)
        resolved_tenant_id = getattr(actor, "tenant_id", None) or tenant_id or col.tenant_id
        resolved_workspace_id = getattr(actor, "workspace_id", None) or workspace_id or col.workspace_id

        # 2. Verify scoped document group
        group = await db.get(DocumentGroup, group_id)
        if not group:
            raise AppException(
                message=f"Không tìm thấy nhóm tài liệu '{group_id}'",
                code="DOCUMENT_GROUP_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if group.tenant_id != resolved_tenant_id or (
            resolved_workspace_id and group.workspace_id != resolved_workspace_id
        ):
            raise AppException(
                message="Không có quyền truy cập nhóm tài liệu này trong workspace hiện tại.",
                code="DOCUMENT_GROUP_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 3. Read group members from server database (tenant-isolated)
        doc_stmt = (
            select(RepositoryDocument)
            .join(
                DocumentGroupMembership,
                DocumentGroupMembership.document_id == RepositoryDocument.id,
            )
            .where(
                DocumentGroupMembership.group_id == group.id,
                RepositoryDocument.is_active.is_(True),
                RepositoryDocument.tenant_id == resolved_tenant_id,
            )
            .order_by(DocumentGroupMembership.added_at.asc())
        )
        if resolved_workspace_id:
            doc_stmt = doc_stmt.where(RepositoryDocument.workspace_id == resolved_workspace_id)
        group_docs = (await db.execute(doc_stmt)).scalars().all()

        if not group_docs:
            return {
                "collection": col,
                "group": group,
                "group_docs": [],
                "total_documents": 0,
                "ready_count": 0,
                "already_bound_count": 0,
                "not_ready_count": 0,
                "failed_count": 0,
                "preview_items": [],
                "ready_selection_items": [],
                "doc_map": {},
            }

        doc_ids = [d.id for d in group_docs]

        # 4. Check active bindings in collection
        bnd_stmt = select(KnowledgeBinding.repository_document_id).where(
            KnowledgeBinding.collection_id == col.id,
            KnowledgeBinding.repository_document_id.in_(doc_ids),
            KnowledgeBinding.status == "active",
        )
        bound_doc_ids = set((await db.execute(bnd_stmt)).scalars().all())

        # 5. Preload current revisions
        current_rev_ids = [d.current_revision_id for d in group_docs if d.current_revision_id]
        revs_map: dict[str, DocumentRevision] = {}
        if current_rev_ids:
            rev_stmt = select(DocumentRevision).where(DocumentRevision.id.in_(current_rev_ids))
            revs_map = {r.id: r for r in (await db.execute(rev_stmt)).scalars().all()}

        # 6. Evaluate members
        ready_count = 0
        already_bound_count = 0
        not_ready_count = 0
        failed_count = 0
        preview_items: list[PreviewDocumentGroupItem] = []
        ready_selection_items: list[tuple[RepositoryDocument, DocumentRevision]] = []
        doc_map = {d.id: d for d in group_docs}

        for doc in group_docs:
            rev = revs_map.get(doc.current_revision_id) if doc.current_revision_id else None
            is_bound = doc.id in bound_doc_ids

            if is_bound:
                already_bound_count += 1
                preview_items.append(
                    PreviewDocumentGroupItem(
                        document_id=doc.id,
                        title=doc.title,
                        file_name=doc.file_name,
                        current_revision_id=doc.current_revision_id,
                        revision_status=rev.status if rev else None,
                        already_bound=True,
                        eligible_for_binding=False,
                        reason="Tài liệu đã có liên kết đang hoạt động trong kho tri thức này.",
                    )
                )
            elif not rev or rev.status != "ready":
                if rev and rev.status in ("failed", "cancelled"):
                    failed_count += 1
                    preview_items.append(
                        PreviewDocumentGroupItem(
                            document_id=doc.id,
                            title=doc.title,
                            file_name=doc.file_name,
                            current_revision_id=doc.current_revision_id,
                            revision_status=rev.status,
                            already_bound=False,
                            eligible_for_binding=False,
                            reason=f"Phiên bản tài liệu bị lỗi ({rev.status}).",
                        )
                    )
                else:
                    not_ready_count += 1
                    status_desc = rev.status if rev else "chưa có phiên bản"
                    preview_items.append(
                        PreviewDocumentGroupItem(
                            document_id=doc.id,
                            title=doc.title,
                            file_name=doc.file_name,
                            current_revision_id=doc.current_revision_id,
                            revision_status=rev.status if rev else None,
                            already_bound=False,
                            eligible_for_binding=False,
                            reason=f"Tài liệu chưa sẵn sàng (trạng thái: {status_desc}).",
                        )
                    )
            else:
                ready_count += 1
                ready_selection_items.append((doc, rev))
                preview_items.append(
                    PreviewDocumentGroupItem(
                        document_id=doc.id,
                        title=doc.title,
                        file_name=doc.file_name,
                        current_revision_id=rev.id,
                        revision_status="ready",
                        already_bound=False,
                        eligible_for_binding=True,
                        reason="Sẵn sàng đưa vào kho tri thức.",
                    )
                )

        return {
            "collection": col,
            "group": group,
            "group_docs": group_docs,
            "total_documents": len(group_docs),
            "ready_count": ready_count,
            "already_bound_count": already_bound_count,
            "not_ready_count": not_ready_count,
            "failed_count": failed_count,
            "preview_items": preview_items,
            "ready_selection_items": ready_selection_items,
            "doc_map": doc_map,
        }

    async def preview_document_group(
        self,
        db: AsyncSession,
        collection_id: str,
        req: PreviewDocumentGroupRequest,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> PreviewDocumentGroupResponse:
        """Preview attaching a document group to a knowledge collection without modifying state."""
        eval_res = await self._evaluate_group_members(
            db=db,
            collection_id=collection_id,
            group_id=req.group_id,
            actor=actor,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
        )

        return PreviewDocumentGroupResponse(
            collection_id=collection_id,
            group_id=eval_res["group"].id,
            group_name=eval_res["group"].name,
            total_documents=eval_res["total_documents"],
            ready_count=eval_res["ready_count"],
            already_bound_count=eval_res["already_bound_count"],
            not_ready_count=eval_res["not_ready_count"],
            failed_count=eval_res["failed_count"],
            items=eval_res["preview_items"],
        )

    async def attach_document_group(
        self,
        db: AsyncSession,
        collection_id: str,
        req: AttachDocumentGroupRequest,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        actor: Any | None = None,
    ) -> AttachDocumentGroupResponse:
        """Attach all ready documents in a group to a knowledge collection idempotently.

        This is a manual snapshot operation. Documents added to the group in the future
        will not be automatically synced or indexed into this collection.
        """
        eval_res = await self._evaluate_group_members(
            db=db,
            collection_id=collection_id,
            group_id=req.group_id,
            actor=actor,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
        )

        group = eval_res["group"]
        group_docs = eval_res["group_docs"]
        total_documents = eval_res["total_documents"]
        ready_count = eval_res["ready_count"]
        already_bound_count = eval_res["already_bound_count"]
        not_ready_count = eval_res["not_ready_count"]
        failed_count = eval_res["failed_count"]
        ready_selection_items = eval_res["ready_selection_items"]
        doc_map = eval_res["doc_map"]

        if total_documents == 0:
            raise AppException(
                message=f"Kho tài liệu '{group.name}' không có tài liệu nào.",
                code="DOCUMENT_GROUP_EMPTY",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if req.strict_ready and (not_ready_count > 0 or failed_count > 0):
            raise AppException(
                message=f"Chế độ strict_ready được bật: Phát hiện {not_ready_count + failed_count}/{total_documents} tài liệu trong kho tài liệu chưa ở trạng thái sẵn sàng (ready).",
                code="STRICT_READY_VIOLATION",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={
                    "total_documents": total_documents,
                    "ready_count": ready_count,
                    "not_ready_count": not_ready_count + failed_count,
                },
            )

        if not ready_selection_items:
            if already_bound_count == total_documents:
                # All documents are already bound
                results = [
                    AttachDocumentGroupItemResult(
                        document_id=d.id,
                        document_title=d.title,
                        source_revision_id=d.current_revision_id,
                        status="already_bound",
                        message="Tài liệu đã có liên kết đang hoạt động trong kho tri thức này.",
                    )
                    for d in group_docs
                ]
                return AttachDocumentGroupResponse(
                    collection_id=collection_id,
                    group_id=group.id,
                    group_name=group.name,
                    total_documents=total_documents,
                    created_count=0,
                    already_bound_count=already_bound_count,
                    not_ready_count=not_ready_count,
                    failed_count=failed_count,
                    items=results,
                )
            raise AppException(
                message="Không có tài liệu nào trong kho tài liệu có phiên bản ready để đưa vào kho tri thức.",
                code="NO_READY_DOCUMENTS",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Delegate ready items to create_bindings
        binding_items = [
            BindingSelectionItem(
                repository_document_id=doc.id,
                target_revision_id=rev.id,
                chunk_strategy=req.chunk_strategy,
                sync_policy=req.sync_policy,
                auto_activate=req.auto_activate,
            )
            for doc, rev in ready_selection_items
        ]

        resolved_tenant_id = (
            getattr(actor, "tenant_id", None) or tenant_id or eval_res["collection"].tenant_id
        )
        resolved_workspace_id = (
            getattr(actor, "workspace_id", None) or workspace_id or eval_res["collection"].workspace_id
        )

        batch_req = CreateKnowledgeBindingsRequest(items=binding_items)
        binding_res = await self.create_bindings(
            db=db,
            collection_id=collection_id,
            req=batch_req,
            tenant_id=resolved_tenant_id,
            workspace_id=resolved_workspace_id,
            actor=actor,
        )

        results_map: dict[str, AttachDocumentGroupItemResult] = {}
        for p_item in eval_res["preview_items"]:
            if p_item.already_bound:
                results_map[p_item.document_id] = AttachDocumentGroupItemResult(
                    document_id=p_item.document_id,
                    document_title=p_item.title,
                    source_revision_id=p_item.current_revision_id,
                    status="already_bound",
                    message=p_item.reason,
                )
            elif not p_item.eligible_for_binding:
                item_status = (
                    "failed"
                    if p_item.revision_status in ("failed", "rejected")
                    else "not_ready"
                )
                results_map[p_item.document_id] = AttachDocumentGroupItemResult(
                    document_id=p_item.document_id,
                    document_title=p_item.title,
                    source_revision_id=p_item.current_revision_id,
                    status=item_status,
                    message=p_item.reason,
                )

        for b_item in binding_res.bindings:
            doc = doc_map.get(b_item.repository_document_id)
            results_map[b_item.repository_document_id] = AttachDocumentGroupItemResult(
                document_id=b_item.repository_document_id,
                document_title=doc.title if doc else None,
                source_revision_id=b_item.source_revision_id,
                binding_id=b_item.binding_id,
                status=b_item.status,
                message=b_item.message,
                index_revision_id=b_item.index_revision_id,
            )

        ordered_items = [results_map[d.id] for d in group_docs if d.id in results_map]

        return AttachDocumentGroupResponse(
            collection_id=collection_id,
            group_id=group.id,
            group_name=group.name,
            total_documents=total_documents,
            created_count=binding_res.created_count,
            already_bound_count=already_bound_count + binding_res.skipped_count,
            not_ready_count=not_ready_count,
            failed_count=failed_count + binding_res.failed_count,
            items=ordered_items,
        )


binding_service = BindingService()
