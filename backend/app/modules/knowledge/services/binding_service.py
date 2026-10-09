"""Knowledge Binding Service — Manages bindings between Repository Documents and Knowledge Collections."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
)
from app.modules.knowledge.schemas import (
    AvailableRepositoryDocumentItem,
    AvailableRepositoryDocumentsResponse,
    BindingChunksListResponse,
    BindingResultItem,
    CreateKnowledgeBindingsRequest,
    CreateKnowledgeBindingsResponse,
    KnowledgeBindingResponse,
    KnowledgeChunkItemResponse,
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


binding_service = BindingService()
