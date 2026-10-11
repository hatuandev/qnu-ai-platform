"""Service for evaluating and querying Repository candidate documents for a KnowledgeCollection.

Implements ADR-012 two-dimensional state classification:
- source_state: not_imported | current | update_available | processing | failed
- vector_state: not_indexed | indexed | indexing | index_failed
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.modules.documents.models import (
    DocumentGroup,
    DocumentGroupMembership,
    RepositoryDocument,
)
from app.modules.documents.schemas import DocumentGroupMinimalItem
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import (
    CandidateGroupItem,
    CandidateGroupListResponse,
    CandidateListResponse,
    RepositoryCandidateItem,
)


def _uuid_str(val: Any) -> str:
    if isinstance(val, UUID):
        return str(val)
    return str(val) if val is not None else ""


class CandidateService:
    """Service to evaluate repository candidates against collection knowledge."""

    async def get_candidate_groups(
        self,
        collection_id: str,
        tenant_id: str,
        workspace_id: str,
        db: AsyncSession,
    ) -> CandidateGroupListResponse:
        """List document groups in workspace with stats on imported documents."""
        # 1. Validate collection
        coll_res = await db.execute(
            select(KnowledgeCollection).where(
                KnowledgeCollection.id == collection_id,
                KnowledgeCollection.tenant_id == tenant_id,
                KnowledgeCollection.workspace_id == workspace_id,
            )
        )
        coll = coll_res.scalar_one_or_none()
        if not coll:
            raise AppException(
                status_code=404,
                error_code="COLLECTION_NOT_FOUND",
                detail=f"Không tìm thấy kho tri thức {collection_id}",
            )

        # 2. Get all groups in workspace
        groups_res = await db.execute(
            select(DocumentGroup)
            .where(
                DocumentGroup.tenant_id == tenant_id,
                DocumentGroup.workspace_id == workspace_id,
            )
            .order_by(DocumentGroup.created_at.desc())
        )
        groups = groups_res.scalars().all()

        if not groups:
            return CandidateGroupListResponse(items=[], total=0)

        # 3. Get all imported repository document IDs in this collection
        bindings_res = await db.execute(
            select(KnowledgeBinding.repository_document_id)
            .where(KnowledgeBinding.collection_id == collection_id)
        )
        imported_doc_ids = {
            r[0] for r in bindings_res.all() if r[0] is not None
        }

        # 4. Count total and imported per group
        group_items: list[CandidateGroupItem] = []
        for g in groups:
            # Query members of this group that are not deleted
            members_res = await db.execute(
                select(DocumentGroupMembership.document_id)
                .join(
                    RepositoryDocument,
                    DocumentGroupMembership.document_id == RepositoryDocument.id,
                )
                .where(
                    DocumentGroupMembership.group_id == g.id,
                    RepositoryDocument.is_active.is_(True),
                )
            )
            member_doc_ids = {r[0] for r in members_res.all()}
            total_docs = len(member_doc_ids)
            imported_count = len(member_doc_ids.intersection(imported_doc_ids))

            group_items.append(
                CandidateGroupItem(
                    id=_uuid_str(g.id),
                    name=g.name,
                    description=g.description,
                    total_documents=total_docs,
                    imported_documents=imported_count,
                    created_at=g.created_at,
                )
            )

        return CandidateGroupListResponse(items=group_items, total=len(group_items))

    async def get_candidate_documents(
        self,
        collection_id: str,
        group_id: str | None = None,
        vector_generation_id: str | None = None,
        source_state_filter: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        db: AsyncSession | None = None,
    ) -> CandidateListResponse:
        """Query repository documents and classify them into 2-dimensional states."""
        assert db is not None, "Database session is required"

        # 1. Validate collection
        coll_res = await db.execute(
            select(KnowledgeCollection).where(
                KnowledgeCollection.id == collection_id,
                KnowledgeCollection.tenant_id == tenant_id,
                KnowledgeCollection.workspace_id == workspace_id,
            )
        )
        coll = coll_res.scalar_one_or_none()
        if not coll:
            raise AppException(
                status_code=404,
                error_code="COLLECTION_NOT_FOUND",
                detail=f"Không tìm thấy kho tri thức {collection_id}",
            )

        # 2. Determine target vector generation
        effective_generation_id = vector_generation_id
        if not effective_generation_id:
            gen_res = await db.execute(
                select(KnowledgeVectorGeneration)
                .where(
                    KnowledgeVectorGeneration.collection_id == collection_id,
                    KnowledgeVectorGeneration.status.in_(["active", "ready", "building"]),
                )
                .order_by(
                    KnowledgeVectorGeneration.status == "active",
                    KnowledgeVectorGeneration.created_at.desc(),
                )
            )
            gen = gen_res.scalars().first()
            if gen:
                effective_generation_id = gen.id

        # 3. Build query for Repository Documents
        query = select(RepositoryDocument).where(
            RepositoryDocument.tenant_id == tenant_id,
            RepositoryDocument.workspace_id == workspace_id,
            RepositoryDocument.is_active.is_(True),
        )

        if group_id:
            query = query.join(
                DocumentGroupMembership,
                DocumentGroupMembership.document_id == RepositoryDocument.id,
            ).where(DocumentGroupMembership.group_id == group_id)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    RepositoryDocument.title.ilike(search_pattern),
                    RepositoryDocument.file_name.ilike(search_pattern),
                )
            )

        query = query.order_by(RepositoryDocument.created_at.desc())
        docs_res = await db.execute(query)
        all_docs = docs_res.scalars().all()

        if not all_docs:
            return CandidateListResponse(
                items=[], total=0, vector_generation_id=effective_generation_id
            )

        doc_ids = [d.id for d in all_docs]

        # 4. Load groups for all candidate documents
        group_memberships_res = await db.execute(
            select(
                DocumentGroupMembership.document_id,
                DocumentGroup.id,
                DocumentGroup.name,
            )
            .join(DocumentGroup, DocumentGroupMembership.group_id == DocumentGroup.id)
            .where(DocumentGroupMembership.document_id.in_(doc_ids))
        )
        doc_groups_map: dict[str, list[DocumentGroupMinimalItem]] = {d_id: [] for d_id in doc_ids}
        for d_id, g_id, g_name in group_memberships_res.all():
            doc_groups_map[d_id].append(
                DocumentGroupMinimalItem(id=_uuid_str(g_id), name=g_name)
            )

        # 5. Load KnowledgeBindings for this collection
        bindings_res = await db.execute(
            select(KnowledgeBinding)
            .options(
                selectinload(KnowledgeBinding.active_source_revision),
                selectinload(KnowledgeBinding.active_index_revision),
            )
            .where(
                KnowledgeBinding.collection_id == collection_id,
                KnowledgeBinding.repository_document_id.in_(doc_ids),
            )
        )
        binding_map: dict[str, KnowledgeBinding] = {
            b.repository_document_id: b for b in bindings_res.scalars().all()
        }

        # 5.1. Load KnowledgeIndexRevisions for effective_generation_id
        index_revs_map: dict[str, list[KnowledgeIndexRevision]] = {b.id: [] for b in binding_map.values()}
        if binding_map and effective_generation_id:
            binding_ids = [b.id for b in binding_map.values()]
            idx_res = await db.execute(
                select(KnowledgeIndexRevision).where(
                    KnowledgeIndexRevision.binding_id.in_(binding_ids),
                    KnowledgeIndexRevision.vector_generation_id == effective_generation_id,
                )
            )
            for ir in idx_res.scalars().all():
                if ir.binding_id in index_revs_map:
                    index_revs_map[ir.binding_id].append(ir)

        # 6. Evaluate 2-dimensional state for each document
        evaluated_items: list[RepositoryCandidateItem] = []

        for doc in all_docs:
            binding = binding_map.get(doc.id)

            if not binding:
                source_state = "not_imported"
                vector_state = "not_indexed"
                knowledge_source_id = None
                imported_file_hash = None
                selectable = True
                unselectable_reason = None
            else:
                knowledge_source_id = binding.id
                active_src_rev = binding.active_source_revision
                imported_file_hash = (
                    active_src_rev.origin_file_hash
                    if (active_src_rev and active_src_rev.origin_file_hash)
                    else (active_src_rev.canonical_hash if active_src_rev else None)
                )

                # Determine source_state
                if active_src_rev and active_src_rev.status in (
                    "queued",
                    "extracting",
                    "normalizing",
                    "validating",
                ):
                    source_state = "processing"
                elif active_src_rev and active_src_rev.status == "failed":
                    source_state = "failed"
                elif imported_file_hash == doc.file_hash:
                    source_state = "current"
                else:
                    source_state = "update_available"

                # Determine vector_state based on effective_generation_id
                if not effective_generation_id:
                    vector_state = "not_indexed"
                else:
                    target_revs = index_revs_map.get(binding.id, [])
                    if not target_revs and binding.active_index_revision:
                        air = binding.active_index_revision
                        if getattr(air, "vector_generation_id", None) == effective_generation_id:
                            target_revs = [air]

                    if any(ir.status == "active" for ir in target_revs):
                        vector_state = "indexed"
                    elif any(ir.status in ("pending", "syncing") for ir in target_revs):
                        vector_state = "indexing"
                    elif any(ir.status == "failed" for ir in target_revs):
                        vector_state = "index_failed"
                    else:
                        vector_state = "not_indexed"

                # Determine selectability
                if source_state in ("not_imported", "update_available"):
                    selectable = True
                    unselectable_reason = None
                elif source_state == "current":
                    if vector_state in ("not_indexed", "index_failed"):
                        selectable = True
                        unselectable_reason = None
                    elif vector_state == "indexed":
                        selectable = False
                        unselectable_reason = "Tài liệu đã có và đã được lập chỉ mục đầy đủ"
                    elif vector_state == "indexing":
                        selectable = False
                        unselectable_reason = "Tài liệu đang trong tiến trình lập chỉ mục"
                    else:
                        selectable = True
                        unselectable_reason = None
                elif source_state == "processing":
                    selectable = False
                    unselectable_reason = "Tài liệu đang trong tiến trình xử lý nguồn"
                elif source_state == "failed":
                    selectable = True
                    unselectable_reason = None
                else:
                    selectable = True
                    unselectable_reason = None

            # Filter by source_state if requested
            if source_state_filter and source_state != source_state_filter:
                continue

            evaluated_items.append(
                RepositoryCandidateItem(
                    document_id=doc.id,
                    title=doc.title,
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                    file_size_bytes=doc.file_size_bytes,
                    file_hash=doc.file_hash,
                    document_type_code=doc.document_type_code,
                    document_number=doc.document_number,
                    issuing_authority=doc.issuing_authority,
                    issued_date=doc.issued_date,
                    groups=doc_groups_map.get(doc.id, []),
                    source_state=source_state,
                    vector_state=vector_state,
                    knowledge_source_id=knowledge_source_id,
                    imported_file_hash=imported_file_hash,
                    selectable=selectable,
                    unselectable_reason=unselectable_reason,
                )
            )

        total_evaluated = len(evaluated_items)
        paginated_items = evaluated_items[offset : offset + limit]

        return CandidateListResponse(
            items=paginated_items,
            total=total_evaluated,
            vector_generation_id=effective_generation_id,
        )


candidate_service = CandidateService()
