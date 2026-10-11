"""Unit and Integration Tests for Long-Lived Knowledge Group Sources (State Machine, Workspace Isolation, Resilient Sync/Retry).

Bao gồm 15 ca kiểm thử bất biến:
1. Binding mới không dùng source_revision_id=None (tránh vi phạm NOT NULL).
2. Binding mới ở status 'pending' trong lúc staging chưa hoàn thành (chưa tham gia retrieval).
3. Staging build thất bại giữ binding ở pending, không cập nhật membership hash.
4. Retry dùng lại pending binding, không tạo binding trùng.
5. Staging ready nhưng chưa publish trả review_required.
6. list_group_sources không ghi đè review_required thành updates_available.
7. Sync lặp lại không build lại khi đã có ready staging cùng source revision.
8. Promote thất bại giữ current source revision và active pointer cũ.
9. Retry promote dùng staging cũ, không build lại.
10. Publish một phần không thành ready, trả items và failed_count.
11. Có một active index nhưng còn tài liệu build lỗi thì source không thành ready.
12. Chỉ thành ready khi tất cả current ready documents có active index đúng revision.
13. Nhóm thứ hai không được chiếm binding của nhóm thứ nhất (DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE).
14. Workspace isolation vẫn hoạt động chặt chẽ.
15. Test persistence thật trên PostgreSQL (bắt lỗi NOT NULL nếu source_revision_id=None).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import AppException
from app.modules.documents.models import (
    DocumentGroup,
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
    AttachGroupSourceRequest,
    DocumentSyncItemResult,
    PreviewGroupSourceDiffItem,
    SyncGroupSourceRequest,
)
from app.modules.knowledge.services.group_source_diff_service import (
    compute_membership_hash,
    populate_failed_items_from_diff,
    resolve_group_source_state,
)
from app.modules.knowledge.services.group_source_service import (
    GroupSourceService,
)
from app.modules.knowledge.services.index_build_service import IndexBuildService


def _execute_result(scalar=None, scalars_list=None, all_rows=None, one_row=None, scalar_one_or_none=...):
    if scalar_one_or_none is not ...:
        effective_scalar = scalar_one_or_none
    elif scalar is not None:
        effective_scalar = scalar
    elif scalars_list and len(scalars_list) > 0:
        effective_scalar = scalars_list[0]
    else:
        effective_scalar = None
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=effective_scalar)
    result.scalar_one = MagicMock(
        return_value=effective_scalar if effective_scalar is not None else len(scalars_list or [])
    )
    result.scalar = MagicMock(return_value=effective_scalar)
    result.one = MagicMock(return_value=one_row if one_row is not None else (0, 0))
    scalars = MagicMock()
    effective_list = (
        scalars_list
        if scalars_list is not None
        else ([effective_scalar] if effective_scalar is not None else [])
    )
    scalars.all = MagicMock(return_value=effective_list)
    result.scalars = MagicMock(return_value=scalars)
    result.all = MagicMock(return_value=all_rows if all_rows is not None else effective_list)
    result.first = MagicMock(return_value=effective_scalar)
    result.rowcount = 1
    return result


def _fresh_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _make_collection(
    col_id: str = "col_test",
    tenant_id: str = "tenant_qnu",
    workspace_id: str = "workspace_qnu",
) -> KnowledgeCollection:
    return KnowledgeCollection(
        id=col_id,
        name="Kho Tri Thức Tuyển Sinh",
        module_code="admissions",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_group(
    grp_id: str = "grp_test",
    tenant_id: str = "tenant_qnu",
    workspace_id: str = "workspace_qnu",
    name: str = "Nhóm Văn Bản Đề Án",
) -> DocumentGroup:
    grp = DocumentGroup(
        id=grp_id,
        name=name,
        description="Nhóm văn bản đề án tuyển sinh",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    grp.member_count = 1
    return grp


def _make_doc_and_revision(
    doc_id: str = "doc_1",
    rev_id: str = "rev_1",
    rev_status: str = "ready",
    tenant_id: str = "tenant_qnu",
    workspace_id: str = "workspace_qnu",
) -> tuple[RepositoryDocument, DocumentRevision]:
    doc = RepositoryDocument(
        id=doc_id,
        title="Quy chế tuyển sinh 2026",
        file_name="quy_che_2026.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        file_hash=f"hash_{doc_id}",
        storage_path=f"storage/{doc_id}.pdf",
        current_revision_id=rev_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        is_active=True,
    )
    rev = DocumentRevision(
        id=rev_id,
        document_id=doc_id,
        revision_no=1,
        status=rev_status,
        source_file_name="quy_che_2026.pdf",
        source_file_type="pdf",
        source_size_bytes=1024,
        source_hash=f"hash_{rev_id}",
        source_storage_path=f"storage/{doc_id}.pdf",
    )
    return doc, rev


# =========================================================================
# TEST CASES
# =========================================================================


@pytest.mark.asyncio
async def test_membership_hash_order_independence():
    """Hash SHA-256 phải bất biến không phụ thuộc thứ tự tài liệu."""
    members_1 = [("doc_a", "rev_1"), ("doc_b", "rev_2"), ("doc_c", "rev_3")]
    members_2 = [("doc_c", "rev_3"), ("doc_a", "rev_1"), ("doc_b", "rev_2")]
    hash_1 = compute_membership_hash(members_1)
    hash_2 = compute_membership_hash(members_2)
    assert hash_1 == hash_2
    assert len(hash_1) == 64


@pytest.mark.asyncio
async def test_attach_new_binding_does_not_use_none_source_revision_id():
    """Ca 1 & 2: Binding mới KHÔNG được dùng source_revision_id=None và phải khởi đầu ở trạng thái pending."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision()

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    query_count = 0
    added_bindings: list[KnowledgeBinding] = []

    def mock_add(obj):
        if isinstance(obj, KnowledgeBinding):
            obj.id = "bnd_1"
            added_bindings.append(obj)

    db.add = MagicMock(side_effect=mock_add)

    idx_rev = KnowledgeIndexRevision(id="idx_rev_1", binding_id="bnd_1", source_revision_id=rev.id, revision_no=1, status="ready")

    def execute_side_effect(stmt):
        nonlocal query_count
        query_count += 1
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalar=idx_rev, scalars_list=[idx_rev])
        if "from knowledge_bindings" in stmt_str and "status in" in stmt_str:
            return _execute_result(scalars_list=added_bindings)
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalar_one_or_none=None)
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.build_staging_index = AsyncMock(return_value=idx_rev)

    service = GroupSourceService(index_build_service=mock_builder)
    req = AttachGroupSourceRequest(group_id=group.id, auto_activate=False)
    res = await service.attach_group_source(db=db, collection_id=col.id, req=req)

    # Invariant: binding mới phải có source_revision_id != None và status == 'pending'
    assert len(added_bindings) >= 1
    binding = added_bindings[0]
    assert binding.source_revision_id == rev.id
    assert binding.status == "pending"
    assert res.status == "review_required"


@pytest.mark.asyncio
async def test_failed_staging_build_keeps_binding_pending_and_no_hash_update():
    """Ca 3: Build thất bại giữ binding ở pending, không cập nhật membership hash."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision()

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_bindings" in stmt_str and "where knowledge_bindings.collection_id" in stmt_str and "repository_document_id" in stmt_str:
            return _execute_result(scalar=None)
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    idx_rev_failed = KnowledgeIndexRevision(id="idx_rev_f", binding_id="bnd_1", source_revision_id=rev.id, revision_no=1, status="failed", failure_code="CORRUPT_PDF", failure_detail="Invalid PDF trailer")
    mock_builder.build_staging_index = AsyncMock(return_value=idx_rev_failed)

    service = GroupSourceService(index_build_service=mock_builder)
    req = AttachGroupSourceRequest(group_id=group.id, auto_activate=False)
    res = await service.attach_group_source(db=db, collection_id=col.id, req=req)

    assert res.status == "failed"
    assert res.failed_count == 1
    # Hash không được cập nhật
    assert res.last_membership_hash is None


@pytest.mark.asyncio
async def test_retry_reuses_pending_binding_no_duplicate():
    """Ca 4: Lần retry sau tìm và tái sử dụng pending binding đã có, không tạo binding trùng."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision()
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="failed")

    # Đã có binding pending từ lần trước
    existing_bnd = KnowledgeBinding(
        id="bnd_existing",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        group_source_id=source.id,
        status="pending",
        active_index_revision_id=None,
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    added_bindings = []
    db.add = MagicMock(side_effect=lambda obj: added_bindings.append(obj) if isinstance(obj, KnowledgeBinding) else None)

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_bindings" in stmt_str and "where knowledge_bindings.collection_id" in stmt_str and "repository_document_id" in stmt_str:
            return _execute_result(scalar=existing_bnd)
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalar=idx_rev_success, scalars_list=[idx_rev_success])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[existing_bnd])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    idx_rev_success = KnowledgeIndexRevision(id="idx_rev_2", binding_id=existing_bnd.id, source_revision_id=rev.id, revision_no=2, status="ready")
    mock_builder.build_staging_index = AsyncMock(return_value=idx_rev_success)

    service = GroupSourceService(index_build_service=mock_builder)
    req = SyncGroupSourceRequest(auto_publish=False)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    # Không thêm binding mới nào (tái sử dụng binding cũ)
    assert len(added_bindings) == 0
    assert res.synced_count == 1
    assert res.status == "review_required"


@pytest.mark.asyncio
async def test_repeated_sync_does_not_rebuild_existing_ready_staging():
    """Ca 7: Sync lặp lại khi đã có ready staging cùng source revision thì tái sử dụng, không build lại."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision()
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="review_required")

    existing_bnd = KnowledgeBinding(
        id="bnd_1",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        group_source_id=source.id,
        status="pending",
    )
    existing_ready_idx = KnowledgeIndexRevision(
        id="idx_rev_already_ready",
        binding_id=existing_bnd.id,
        source_revision_id=rev.id,
        revision_no=1,
        status="ready",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_bindings" in stmt_str and "where knowledge_bindings.collection_id" in stmt_str and "repository_document_id" in stmt_str:
            return _execute_result(scalar=existing_bnd)
        if "from knowledge_index_revisions" in stmt_str and "status = 'ready'" in stmt_str:
            return _execute_result(scalar=existing_ready_idx)
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalars_list=[existing_ready_idx])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[existing_bnd])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.build_staging_index = AsyncMock()

    service = GroupSourceService(index_build_service=mock_builder)
    req = SyncGroupSourceRequest(auto_publish=False)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    # KHÔNG gọi build_staging_index vì đã có ready staging revision!
    mock_builder.build_staging_index.assert_not_called()
    assert res.status == "review_required"


@pytest.mark.asyncio
async def test_list_group_sources_does_not_override_review_required():
    """Ca 6: list_group_sources không ghi đè review_required thành updates_available."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision()
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="review_required")

    bnd = KnowledgeBinding(id="bnd_1", collection_id=col.id, repository_document_id=doc.id, source_revision_id=rev.id, group_source_id=source.id, status="pending")
    ready_idx = KnowledgeIndexRevision(id="idx_1", binding_id=bnd.id, source_revision_id=rev.id, revision_no=1, status="ready")

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from knowledge_group_sources" in stmt_str:
            return _execute_result(all_rows=[(source, group)])
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalars_list=[ready_idx])
        if "count(" in stmt_str:
            return _execute_result(scalar=0)
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[bnd])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    results = await service.list_group_sources(db=db, collection_id=col.id)

    assert len(results) == 1
    # Bất biến: giữ review_required, KHÔNG bị ghi đè thành updates_available!
    assert results[0].status == "review_required"
    assert results[0].awaiting_publish_count == 1
    assert results[0].publishable_count == 1


@pytest.mark.asyncio
async def test_failed_promote_retains_current_source_revision_and_active_pointer():
    """Ca 8: Promote thất bại giữ nguyên binding.source_revision_id cũ và active pointer cũ."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc = RepositoryDocument(id="doc_1", title="Đề án", current_revision_id="rev_2", is_active=True, tenant_id=col.tenant_id, workspace_id=col.workspace_id)
    rev_2 = DocumentRevision(id="rev_2", document_id="doc_1", revision_no=2, status="ready")
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="syncing")

    # Binding đang active revision 1
    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id="rev_1",
        active_index_revision_id="idx_rev_1",
        group_source_id=source.id,
        status="active",
        active_epoch=1,
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev_2)])
        if "from knowledge_bindings" in stmt_str and "where knowledge_bindings.collection_id" in stmt_str and "repository_document_id" in stmt_str:
            return _execute_result(scalar=binding)
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[binding])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    idx_rev_2 = KnowledgeIndexRevision(id="idx_rev_2", binding_id=binding.id, source_revision_id="rev_2", revision_no=2, status="ready")
    mock_builder.build_staging_index = AsyncMock(return_value=idx_rev_2)
    # Promote thất bại!
    mock_builder.promote_index_revision = AsyncMock(side_effect=RuntimeError("Qdrant connection timeout"))

    service = GroupSourceService(index_build_service=mock_builder)
    req = SyncGroupSourceRequest(auto_publish=True)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    assert res.status == "failed"
    # Invariant: binding vẫn trỏ tới rev_1 và idx_rev_1 cũ
    assert binding.source_revision_id == "rev_1"
    assert binding.active_index_revision_id == "idx_rev_1"


@pytest.mark.asyncio
async def test_retry_promote_reuses_existing_staging_revision():
    """Ca 9 (Mục 6): Retry promote dùng staging cũ đã ready, không build lại staging."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc = RepositoryDocument(id="doc_1", title="Đề án", current_revision_id="rev_2", is_active=True, tenant_id=col.tenant_id, workspace_id=col.workspace_id)
    rev_2 = DocumentRevision(id="rev_2", document_id="doc_1", revision_no=2, status="ready")
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="failed")

    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id="rev_1",
        active_index_revision_id="idx_rev_1",
        group_source_id=source.id,
        status="active",
        active_epoch=1,
    )
    ready_staging_2 = KnowledgeIndexRevision(
        id="idx_rev_2",
        binding_id=binding.id,
        source_revision_id="rev_2",
        revision_no=2,
        status="ready",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    diff_before = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc.id, rev_2.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_ready",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 1,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 0,
        "needs_build_count": 0,
        "awaiting_publish_count": 1,
        "publishable_count": 1,
        "ready_active_docs_count": 0,
        "items": [],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [(doc, rev_2, binding, ready_staging_2)],
        "updated_docs": [],
        "conflict_docs": [],
        "removed_bindings": [],
    }
    diff_after = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc.id, rev_2.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_ready",
        "last_membership_hash": "hash_ready",
        "has_changes": False,
        "total_documents_in_group": 1,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 1,
        "not_ready_count": 0,
        "failed_count": 0,
        "needs_build_count": 0,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 1,
        "items": [],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [],
        "removed_bindings": [],
    }

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.build_staging_index = AsyncMock()
    mock_builder.promote_index_revision = AsyncMock()

    service = GroupSourceService(index_build_service=mock_builder)
    service.diff_service.evaluate_group_diff = AsyncMock(side_effect=[diff_before, diff_after])

    req = SyncGroupSourceRequest(auto_publish=True)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    # Invariant: Không build lại staging
    mock_builder.build_staging_index.assert_not_called()
    # Invariant: Promote được gọi đúng một lần với staging cũ
    mock_builder.promote_index_revision.assert_called_once()
    assert mock_builder.promote_index_revision.call_args[1]["index_revision_id"] == "idx_rev_2"
    # Invariant: Binding chỉ đổi pointer sau promote thành công
    assert binding.source_revision_id == "rev_2"
    assert binding.active_index_revision_id == "idx_rev_2"
    assert binding.status == "active"
    # Invariant: Trạng thái cuối là ready
    assert res.status == "ready"
    assert res.published_count == 1


@pytest.mark.asyncio
async def test_publish_partial_does_not_become_ready():
    """Ca 10: Publish một phần không thành ready, trả items và failed_count."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc_1, rev_1 = _make_doc_and_revision("doc_1", "rev_1")
    doc_2, rev_2 = _make_doc_and_revision("doc_2", "rev_2")
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="review_required")

    bnd_1 = KnowledgeBinding(id="bnd_1", collection_id=col.id, repository_document_id="doc_1", source_revision_id="rev_1", group_source_id=source.id, status="pending")
    bnd_2 = KnowledgeBinding(id="bnd_2", collection_id=col.id, repository_document_id="doc_2", source_revision_id="rev_2", group_source_id=source.id, status="pending")

    idx_1 = KnowledgeIndexRevision(id="idx_1", binding_id="bnd_1", source_revision_id="rev_1", revision_no=1, status="ready")
    idx_2 = KnowledgeIndexRevision(id="idx_2", binding_id="bnd_2", source_revision_id="rev_2", revision_no=1, status="ready")

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc_1, rev_1), (doc_2, rev_2)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[bnd_1, bnd_2])
        if "from knowledge_index_revisions" in stmt_str:
            params = getattr(stmt, "compile", lambda: None)().params if hasattr(stmt, "compile") else {}
            bid = params.get("binding_id_1")
            if bid == "bnd_1":
                return _execute_result(scalar_one_or_none=idx_1, scalars_list=[idx_1])
            if bid == "bnd_2":
                return _execute_result(scalar_one_or_none=idx_2, scalars_list=[idx_2])
            return _execute_result(scalars_list=[idx_1, idx_2], scalar_one_or_none=idx_1)
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    # bnd_1 promote thành công, bnd_2 promote thất bại
    async def promote_mock(db, binding_id, **kwargs):
        if binding_id == "bnd_2":
            raise RuntimeError("CAS conflict on bnd_2")

    mock_builder.promote_index_revision = AsyncMock(side_effect=promote_mock)

    service = GroupSourceService(index_build_service=mock_builder)
    res = await service.publish_group_source(db=db, collection_id=col.id, source_id=source.id)

    assert res.published_count == 1
    assert res.failed_count == 1
    assert res.status == "failed"
    assert bnd_1.status == "active"
    assert bnd_2.status == "pending"


@pytest.mark.asyncio
async def test_publish_without_ready_staging_raises_rfc7807():
    """Publish khi không có revision nào sẵn sàng ném RFC 7807 NO_PUBLISHABLE_INDEX_REVISION."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="pending")

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        return _execute_result(scalar=None, scalars_list=[])

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    with pytest.raises(AppException) as exc_info:
        await service.publish_group_source(db=db, collection_id=col.id, source_id=source.id)

    assert exc_info.value.code == "NO_PUBLISHABLE_INDEX_REVISION"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_one_active_index_but_unresolved_error_does_not_become_ready():
    """Ca 11: Có một active index nhưng còn tài liệu khác build lỗi thì source không thành ready."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc_1, rev_1 = _make_doc_and_revision("doc_1", "rev_1")
    doc_2, rev_2 = _make_doc_and_revision("doc_2", "rev_2")
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="review_required")

    bnd_1 = KnowledgeBinding(id="bnd_1", collection_id=col.id, repository_document_id="doc_1", source_revision_id="rev_1", active_index_revision_id="idx_1", group_source_id=source.id, status="active")
    bnd_2 = KnowledgeBinding(id="bnd_2", collection_id=col.id, repository_document_id="doc_2", source_revision_id="rev_2", group_source_id=source.id, status="pending")

    idx_1 = KnowledgeIndexRevision(id="idx_1", binding_id="bnd_1", source_revision_id="rev_1", revision_no=1, status="active")
    # doc_2 staging build bị lỗi
    idx_2 = KnowledgeIndexRevision(id="idx_2", binding_id="bnd_2", source_revision_id="rev_2", revision_no=1, status="failed")

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc_1, rev_1), (doc_2, rev_2)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[bnd_1, bnd_2])
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalars_list=[idx_1, idx_2])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    # Không có ready revision nào để publish
    service = GroupSourceService()
    diff = await service.diff_service.evaluate_group_diff(db=db, collection=col, group=group, source=source)
    state = resolve_group_source_state(
        source_status=source.status,
        total_docs=diff["total_documents_in_group"],
        needs_build_count=diff["needs_build_count"],
        awaiting_publish_count=diff["awaiting_publish_count"],
        ready_active_docs_count=diff["ready_active_docs_count"],
        failed_count=diff["failed_count"],
    )
    # Invariant: vì còn doc_2 chưa active nên không được thành ready!
    assert state != "ready"


@pytest.mark.asyncio
async def test_second_group_cannot_steal_binding_from_first_group():
    """Ca 13: Nhóm thứ hai không được chiếm binding của nhóm thứ nhất (DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE)."""
    db = _fresh_session()
    col = _make_collection()
    group_2 = _make_group(grp_id="grp_2", name="Nhóm 2")
    doc, rev = _make_doc_and_revision()

    # Binding đã thuộc nhóm 1
    existing_bnd = KnowledgeBinding(
        id="bnd_group_1",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        group_source_id="src_group_1",
        status="active",
        active_index_revision_id="idx_1",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group_2 if model is DocumentGroup else None))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_bindings" in stmt_str and "repository_document_id" in stmt_str:
            return _execute_result(scalar=existing_bnd)
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[existing_bnd])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    req = AttachGroupSourceRequest(group_id=group_2.id, auto_activate=False)
    res = await service.attach_group_source(db=db, collection_id=col.id, req=req)

    # Invariant: không chiếm binding, báo lỗi DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE
    assert res.status == "failed"
    assert res.failed_count >= 1
    assert any(item.error_code == "DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE" for item in res.items)
    # Binding vẫn giữ nguyên chủ sở hữu group 1
    assert existing_bnd.group_source_id == "src_group_1"


@pytest.mark.asyncio
async def test_same_tenant_different_workspace_rejected():
    """Ca 14: Workspace isolation vẫn hoạt động chặt chẽ."""
    db = _fresh_session()
    col = _make_collection(workspace_id="ws_finance")
    group = _make_group(workspace_id="ws_admissions")

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    service = GroupSourceService()
    req = AttachGroupSourceRequest(group_id=group.id)
    with pytest.raises(AppException) as exc_info:
        await service.attach_group_source(db=db, collection_id=col.id, req=req)

    assert exc_info.value.code == "DOCUMENT_GROUP_NOT_FOUND"
    assert exc_info.value.status_code == 404


# =========================================================================
# REGRESSION TESTS BỔ SUNG THEO YÊU CẦU KIỂM CHỨNG BẤT BIẾN
# =========================================================================


@pytest.mark.asyncio
async def test_adopt_active_binding_without_owner_without_rebuild():
    """Ca 1: Active binding đúng revision nhưng group_source_id=None được adopt vào source mà không build lại."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision("doc_adopt", "rev_adopt")
    source = KnowledgeGroupSource(id="src_adopt", collection_id=col.id, document_group_id=group.id, status="syncing")

    # Binding mồ côi (chưa thuộc nguồn nào), đang active đúng revision hiện tại
    binding = KnowledgeBinding(
        id="bnd_orphan",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        active_index_revision_id="idx_orphan_active",
        group_source_id=None,
        status="active",
        active_epoch=1,
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    # Diff nhận diện binding này là adoptable_docs
    diff_before = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc.id, rev.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_adopt",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 1,
        "added_count": 1,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 0,
        "needs_build_count": 0,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 0,
        "items": [],
        "added_docs": [],
        "adoptable_docs": [(doc, rev, binding)],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [],
        "removed_bindings": [],
    }
    diff_after = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc.id, rev.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_adopt",
        "last_membership_hash": "hash_adopt",
        "has_changes": False,
        "total_documents_in_group": 1,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 1,
        "not_ready_count": 0,
        "failed_count": 0,
        "needs_build_count": 0,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 1,
        "items": [],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [],
        "removed_bindings": [],
    }

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.build_staging_index = AsyncMock()
    mock_builder.promote_index_revision = AsyncMock()

    service = GroupSourceService(index_build_service=mock_builder)
    service.diff_service.evaluate_group_diff = AsyncMock(side_effect=[diff_before, diff_after])

    req = SyncGroupSourceRequest(auto_publish=False)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    # Invariant: tuyệt đối KHÔNG build lại và KHÔNG promote lại
    mock_builder.build_staging_index.assert_not_called()
    mock_builder.promote_index_revision.assert_not_called()
    # Invariant: binding được nhận vào nguồn
    assert binding.group_source_id == source.id
    assert binding.status == "active"
    assert binding.source_revision_id == rev.id
    assert binding.active_index_revision_id == "idx_orphan_active"
    assert res.status == "ready"


@pytest.mark.asyncio
async def test_ready_staging_of_old_revision_is_not_published():
    """Ca 5: Ready staging của revision cũ không được publish khi document đã sang revision mới."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    # Document trong nhóm hiện tại là rev_3
    doc = RepositoryDocument(id="doc_old", title="Tài liệu", current_revision_id="rev_3", is_active=True, tenant_id=col.tenant_id, workspace_id=col.workspace_id)
    rev_3 = DocumentRevision(id="rev_3", document_id="doc_old", revision_no=3, status="ready")
    source = KnowledgeGroupSource(id="src_old", collection_id=col.id, document_group_id=group.id, status="review_required")

    binding = KnowledgeBinding(
        id="bnd_old",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id="rev_1",
        active_index_revision_id="idx_rev_1",
        group_source_id=source.id,
        status="active",
        active_epoch=1,
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    # Diff phản ánh desired pair hiện tại là rev_3
    diff_before = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc.id, rev_3.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_old",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 1,
        "added_count": 0,
        "updated_count": 1,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 0,
        "needs_build_count": 1,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 0,
        "items": [],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [(doc, rev_3, binding)],
        "conflict_docs": [],
        "removed_bindings": [],
    }

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[binding])
        if "from knowledge_index_revisions" in stmt_str:
            # Trong DB chỉ có staging của rev_2 cũ, không có staging nào khớp với rev_3 hiện tại
            return _execute_result(scalar_one_or_none=None)
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.promote_index_revision = AsyncMock()

    service = GroupSourceService(index_build_service=mock_builder)
    service.diff_service.evaluate_group_diff = AsyncMock(return_value=diff_before)

    # Invariant: Phải từ chối promote revision cũ với lỗi RFC 7807
    with pytest.raises(AppException) as exc_info:
        await service.publish_group_source(db=db, collection_id=col.id, source_id=source.id)

    assert exc_info.value.code == "NO_PUBLISHABLE_INDEX_REVISION"
    assert exc_info.value.status_code == 400
    mock_builder.promote_index_revision.assert_not_called()
    assert binding.source_revision_id == "rev_1"
    assert binding.active_index_revision_id == "idx_rev_1"


@pytest.mark.asyncio
async def test_ready_staging_of_current_revision_is_published():
    """Ca 6: Ready staging đúng current revision được publish thành công."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc = RepositoryDocument(id="doc_cur", title="Tài liệu", current_revision_id="rev_2", is_active=True, tenant_id=col.tenant_id, workspace_id=col.workspace_id)
    rev_2 = DocumentRevision(id="rev_2", document_id="doc_cur", revision_no=2, status="ready")
    source = KnowledgeGroupSource(id="src_cur", collection_id=col.id, document_group_id=group.id, status="review_required")

    binding = KnowledgeBinding(
        id="bnd_cur",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id="rev_1",
        active_index_revision_id="idx_rev_1",
        group_source_id=source.id,
        status="active",
        active_epoch=1,
    )
    staging_rev_2 = KnowledgeIndexRevision(
        id="idx_rev_2",
        binding_id=binding.id,
        source_revision_id="rev_2",
        revision_no=2,
        status="ready",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    diff_before = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc.id, rev_2.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_cur",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 1,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 0,
        "needs_build_count": 0,
        "awaiting_publish_count": 1,
        "publishable_count": 1,
        "ready_active_docs_count": 0,
        "items": [],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [(doc, rev_2, binding, staging_rev_2)],
        "updated_docs": [],
        "conflict_docs": [],
        "removed_bindings": [],
    }
    diff_after = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc.id, rev_2.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_cur",
        "last_membership_hash": "hash_cur",
        "has_changes": False,
        "total_documents_in_group": 1,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 1,
        "not_ready_count": 0,
        "failed_count": 0,
        "needs_build_count": 0,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 1,
        "items": [],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [],
        "removed_bindings": [],
    }

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[binding])
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalar_one_or_none=staging_rev_2, scalars_list=[staging_rev_2])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.promote_index_revision = AsyncMock()

    service = GroupSourceService(index_build_service=mock_builder)
    service.diff_service.evaluate_group_diff = AsyncMock(side_effect=[diff_before, diff_after])

    res = await service.publish_group_source(db=db, collection_id=col.id, source_id=source.id)

    # Invariant: promote thành công, binding trỏ đúng rev_2 và idx_rev_2
    mock_builder.promote_index_revision.assert_called_once()
    assert binding.source_revision_id == "rev_2"
    assert binding.active_index_revision_id == "idx_rev_2"
    assert binding.status == "active"
    assert res.status == "ready"
    assert res.published_count == 1


@pytest.mark.asyncio
async def test_processing_documents_do_not_skew_eligible_document_count():
    """Ca 9: Nhóm có tài liệu đang parsing/processing không làm sai phép đếm eligible documents."""
    state = resolve_group_source_state(
        source_status="syncing",
        eligible_doc_count=1,  # Chỉ 1 tài liệu ready
        needs_build_count=0,
        awaiting_publish_count=0,
        ready_active_docs_count=1,
        failed_count=0,
        removed_count=0,
        conflict_count=0,
        total_docs=3,  # Nhóm có 3 tài liệu, 2 tài liệu đang processing!
    )
    # Invariant: syncing vẫn là syncing
    assert state == "syncing"

    state_after_sync = resolve_group_source_state(
        source_status="pending",
        eligible_doc_count=1,
        needs_build_count=0,
        awaiting_publish_count=0,
        ready_active_docs_count=1,
        failed_count=0,
        removed_count=0,
        conflict_count=0,
    )
    # Invariant: Vì 1/1 eligible documents đã active nên nguồn thành READY, không bị kẹt bởi 2 tài liệu processing!
    assert state_after_sync == "ready"


# =========================================================================
# TEST PERSISTENCE THẬT VỚI POSTGRESQL & VALIDATION URL AN TOÀN
# =========================================================================


def is_safe_test_database_name(db_name: str | None) -> bool:
    """Xác thực tên CSDL chỉ chấp nhận quy ước thử nghiệm an toàn."""
    if not db_name:
        return False
    normalized = db_name.strip().lower()
    return (
        normalized.startswith("test_")
        or normalized.endswith("_test")
        or "_test_" in normalized
    )


def test_safe_test_database_name_validation():
    """Ca 12 & 13: Kiểm chứng quy tắc an toàn TEST_DATABASE_URL từ chối và chấp nhận đúng."""
    # Bị từ chối (không an toàn)
    assert is_safe_test_database_name("latest") is False
    assert is_safe_test_database_name("contest") is False
    assert is_safe_test_database_name("qnu_ai_platform") is False
    assert is_safe_test_database_name("") is False
    assert is_safe_test_database_name(None) is False
    assert is_safe_test_database_name("production_db") is False

    # Được chấp nhận (an toàn)
    assert is_safe_test_database_name("test_qnu") is True
    assert is_safe_test_database_name("qnu_test") is True
    assert is_safe_test_database_name("qnu_test_integration") is True
    assert is_safe_test_database_name("test_qnu_ai_platform") is True
    assert is_safe_test_database_name("qnu_ai_platform_test") is True


@pytest.mark.asyncio
async def test_real_postgresql_persistence_not_null_invariant():
    """Ca 15: Kiểm chứng persistence thật trên PostgreSQL với TEST_DATABASE_URL an toàn."""
    import os
    db_url = os.environ.get("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("Bỏ qua test persistence vì TEST_DATABASE_URL chưa được cấu hình.")

    try:
        parsed_url = make_url(db_url)
        db_name = parsed_url.database
    except Exception as exc:
        pytest.fail(f"TEST_DATABASE_URL không hợp lệ: {exc}")

    if not is_safe_test_database_name(db_name):
        pytest.fail(
            f"TEST_DATABASE_URL ({db_name}) không an toàn. Database name phải bắt đầu 'test_', kết thúc '_test' hoặc chứa '_test_'."
        )

    engine = None
    try:
        try:
            engine = create_async_engine(db_url, pool_pre_ping=True)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:
            pytest.fail(f"TEST_DATABASE_URL được cấu hình nhưng kết nối thất bại: {exc}")

        test_suffix = uuid.uuid4().hex[:8]
        col_id = f"col_persist_{test_suffix}"
        doc_id = f"doc_persist_{test_suffix}"
        rev_id = f"rev_persist_{test_suffix}"
        src_id = f"src_persist_{test_suffix}"
        grp_id = f"grp_persist_{test_suffix}"

        async with session_factory() as session:
            try:
                # 1. Tạo dữ liệu tiền đề trong transaction thật
                col = KnowledgeCollection(
                    id=col_id,
                    name="Kho Tri Thức Persist Test",
                    module_code=f"test_{test_suffix}",
                    tenant_id="tenant_qnu",
                    workspace_id="workspace_qnu",
                )
                session.add(col)

                doc = RepositoryDocument(
                    id=doc_id,
                    title="Tài liệu Persist Test",
                    file_name="persist_test.pdf",
                    file_type="pdf",
                    file_size_bytes=1024,
                    tenant_id="tenant_qnu",
                    workspace_id="workspace_qnu",
                    file_hash=f"hash_{test_suffix}",
                    storage_path=f"path_{test_suffix}",
                )
                session.add(doc)

                rev = DocumentRevision(
                    id=rev_id,
                    document_id=doc_id,
                    revision_no=1,
                    status="ready",
                    source_file_name="persist_test.pdf",
                    source_file_type="pdf",
                    source_size_bytes=1024,
                    source_hash=f"hash_{test_suffix}",
                    source_storage_path=f"path_{test_suffix}",
                )
                session.add(rev)

                grp = DocumentGroup(
                    id=grp_id,
                    name=f"Nhóm Persist Test {test_suffix}",
                    tenant_id="tenant_qnu",
                    workspace_id="workspace_qnu",
                )
                session.add(grp)

                src = KnowledgeGroupSource(
                    id=src_id,
                    collection_id=col_id,
                    document_group_id=grp_id,
                    tenant_id="tenant_qnu",
                    workspace_id="workspace_qnu",
                    status="pending",
                )
                session.add(src)
                await session.flush()

                # 2. Thử nghiệm gắn source_revision_id hợp lệ (thiết kế mới): PHẢI THÀNH CÔNG!
                valid_binding = KnowledgeBinding(
                    id=f"bnd_valid_{test_suffix}",
                    collection_id=col_id,
                    repository_document_id=doc_id,
                    source_revision_id=rev_id,
                    group_source_id=src_id,
                    status="pending",
                    tenant_id="tenant_qnu",
                    workspace_id="workspace_qnu",
                )
                session.add(valid_binding)
                await session.flush()
                assert valid_binding.source_revision_id == rev_id
                assert valid_binding.status == "pending"

                # 3. Cố tình chèn NULL vào NOT NULL: CSDL PostgreSQL THẬT PHẢI NÉM IntegrityError!
                with pytest.raises(IntegrityError):
                    async with session.begin_nested():
                        await session.execute(
                            text(
                                "INSERT INTO knowledge_bindings (id, collection_id, repository_document_id, source_revision_id, tenant_id, workspace_id, status, created_at, updated_at) "
                                "VALUES (:id, :col_id, :doc_id, NULL, 'tenant_qnu', 'workspace_qnu', 'pending', NOW(), NOW())"
                            ),
                            {
                                "id": f"bnd_bad_{test_suffix}",
                                "col_id": col_id,
                                "doc_id": doc_id,
                            },
                        )
            finally:
                await session.rollback()
    finally:
        if engine:
            await engine.dispose()


# =========================================================================
# REGRESSION TESTS CHO 6 VẤN ĐỀ ĐỒNG BỘ NGUỒN NHÓM
# =========================================================================


@pytest.mark.asyncio
async def test_group_with_only_failed_revisions_resolves_to_failed_not_empty():
    """Ca bổ sung 1: Nhóm có tài liệu nhưng revision failed/cancelled phải thành 'failed', không được thành 'empty'."""
    # 1. Resolver thuần túy
    state = resolve_group_source_state(
        source_status="empty",
        eligible_doc_count=0,
        needs_build_count=0,
        awaiting_publish_count=0,
        ready_active_docs_count=0,
        failed_count=1,
        not_ready_count=0,
        total_docs=1,
    )
    assert state == "failed"

    # 2. Attach flow với tài liệu lỗi
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc = RepositoryDocument(
        id="doc_f",
        title="Tài liệu lỗi",
        current_revision_id="rev_f",
        is_active=True,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
    )
    rev_f = DocumentRevision(id="rev_f", document_id="doc_f", revision_no=1, status="failed")

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev_f)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    req = AttachGroupSourceRequest(group_id=group.id, auto_activate=False)
    res = await service.attach_group_source(db=db, collection_id=col.id, req=req)

    assert res.status == "failed"
    assert res.failed_count == 1


@pytest.mark.asyncio
async def test_group_with_only_processing_revisions_resolves_to_pending():
    """Ca bổ sung 2: Nhóm chỉ có tài liệu đang processing/parsing giải quyết thành 'pending', không phải 'empty'."""
    state = resolve_group_source_state(
        source_status="empty",
        eligible_doc_count=0,
        needs_build_count=0,
        awaiting_publish_count=0,
        ready_active_docs_count=0,
        failed_count=0,
        not_ready_count=2,
        total_docs=2,
    )
    assert state == "pending"

    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc = RepositoryDocument(
        id="doc_p",
        title="Tài liệu đang xử lý",
        current_revision_id="rev_p",
        is_active=True,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
    )
    rev_p = DocumentRevision(id="rev_p", document_id="doc_p", revision_no=1, status="processing")

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev_p)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    req = AttachGroupSourceRequest(group_id=group.id, auto_activate=False)
    res = await service.attach_group_source(db=db, collection_id=col.id, req=req)

    assert res.status == "pending"
    assert res.failed_count == 0


@pytest.mark.asyncio
async def test_group_with_no_documents_resolves_to_empty():
    """Ca bổ sung 3: Nhóm thực sự không có tài liệu nào giải quyết thành 'empty'."""
    state = resolve_group_source_state(
        source_status="empty",
        eligible_doc_count=0,
        needs_build_count=0,
        awaiting_publish_count=0,
        ready_active_docs_count=0,
        failed_count=0,
        not_ready_count=0,
        total_docs=0,
    )
    assert state == "empty"

    db = _fresh_session()
    col = _make_collection()
    group = _make_group()

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    req = AttachGroupSourceRequest(group_id=group.id, auto_activate=False)
    res = await service.attach_group_source(db=db, collection_id=col.id, req=req)

    assert res.status == "empty"
    assert res.failed_count == 0


@pytest.mark.asyncio
async def test_preview_attach_detects_conflict_with_another_group_source():
    """Ca bổ sung 8: Preview attach (source=None) phải phát hiện conflict khi binding đã thuộc nhóm khác."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision()

    existing_foreign_bnd = KnowledgeBinding(
        id="bnd_foreign",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        group_source_id="src_other_group",
        status="active",
        active_index_revision_id="idx_foreign",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[existing_foreign_bnd])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    preview = await service.preview_attach_group(db=db, collection_id=col.id, group_id=group.id)

    assert preview.failed_count == 1
    assert preview.added_count == 0
    conflict_item = next((item for item in preview.items if item.document_id == doc.id), None)
    assert conflict_item is not None
    assert conflict_item.category == "failed"
    assert "thuộc nguồn nhóm khác" in conflict_item.reason


@pytest.mark.asyncio
async def test_preview_existing_source_does_not_treat_own_binding_as_conflict():
    """Ca bổ sung 9: Preview source hiện tại không coi binding của chính source là conflict."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision()
    source = KnowledgeGroupSource(id="src_my_group", collection_id=col.id, document_group_id=group.id, status="ready")

    own_bnd = KnowledgeBinding(
        id="bnd_own",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        group_source_id=source.id,
        status="active",
        active_index_revision_id="idx_own",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[own_bnd])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    preview = await service.preview_source_sync(db=db, collection_id=col.id, source_id=source.id)

    assert preview.failed_count == 0
    assert not any(item.category == "failed" for item in preview.items)


@pytest.mark.asyncio
async def test_single_conflict_produces_failed_count_exactly_one():
    """Ca bổ sung 10: Một conflict chỉ tạo failed_count == 1 (không đếm trùng lặp)."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision()
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="syncing")

    foreign_bnd = KnowledgeBinding(
        id="bnd_foreign",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        group_source_id="src_another",
        status="active",
        active_index_revision_id="idx_f",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[foreign_bnd])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    service = GroupSourceService()
    req = SyncGroupSourceRequest(auto_publish=True)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    assert res.failed_count == 1
    assert len([item for item in res.items if item.status == "failed"]) == 1
    assert res.status == "failed"


@pytest.mark.asyncio
async def test_conflict_and_build_failure_produce_failed_count_exactly_two():
    """Ca bổ sung 11: Một conflict và một build failure ở 2 tài liệu tạo failed_count == 2."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc_1, rev_1 = _make_doc_and_revision("doc_conflict", "rev_1")
    doc_2, rev_2 = _make_doc_and_revision("doc_build_fail", "rev_2")
    source = KnowledgeGroupSource(id="src_1", collection_id=col.id, document_group_id=group.id, status="syncing")

    foreign_bnd = KnowledgeBinding(
        id="bnd_foreign",
        collection_id=col.id,
        repository_document_id=doc_1.id,
        source_revision_id=rev_1.id,
        group_source_id="src_other",
        status="active",
        active_index_revision_id="idx_1",
    )
    own_bnd = KnowledgeBinding(
        id="bnd_own",
        collection_id=col.id,
        repository_document_id=doc_2.id,
        source_revision_id="rev_old",
        group_source_id=source.id,
        status="pending",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc_1, rev_1), (doc_2, rev_2)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[foreign_bnd, own_bnd])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.build_staging_index = AsyncMock(
        return_value=KnowledgeIndexRevision(
            id="idx_failed_2",
            binding_id=own_bnd.id,
            source_revision_id=rev_2.id,
            revision_no=2,
            status="failed",
            failure_code="CORRUPT_DATA",
            failure_detail="Cannot parse",
        )
    )

    service = GroupSourceService(index_build_service=mock_builder)
    req = SyncGroupSourceRequest(auto_publish=True)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    assert res.failed_count == 2
    failed_items = [item for item in res.items if item.status == "failed"]
    assert len(failed_items) == 2
    failed_doc_ids = {item.document_id for item in failed_items}
    assert failed_doc_ids == {doc_1.id, doc_2.id}
    assert res.status == "failed"


@pytest.mark.asyncio
async def test_ownerless_outdated_binding_assigned_owner_and_built_on_attach():
    """Ca bổ sung 5 & 7: Binding ownerless revision cũ được gán group_source_id và build staging ngay trong attach."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc = RepositoryDocument(
        id="doc_outdated",
        title="Tài liệu",
        current_revision_id="rev_2",
        is_active=True,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
    )
    rev_2 = DocumentRevision(id="rev_2", document_id="doc_outdated", revision_no=2, status="ready")

    ownerless_bnd = KnowledgeBinding(
        id="bnd_ownerless_old",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id="rev_1",
        active_index_revision_id="idx_1",
        group_source_id=None,
        status="active",
    )

    new_staging = KnowledgeIndexRevision(
        id="idx_staging_rev2",
        binding_id=ownerless_bnd.id,
        source_revision_id=rev_2.id,
        revision_no=2,
        status="ready",
    )

    built = False

    async def mock_build(*args, **kwargs):
        nonlocal built
        built = True
        return new_staging

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev_2)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[ownerless_bnd])
        if "from knowledge_index_revisions" in stmt_str:
            if built:
                return _execute_result(scalar_one_or_none=new_staging, scalars_list=[new_staging])
            return _execute_result(scalar_one_or_none=None)
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.build_staging_index = AsyncMock(side_effect=mock_build)

    service = GroupSourceService(index_build_service=mock_builder)
    req = AttachGroupSourceRequest(group_id=group.id, auto_activate=False)
    res = await service.attach_group_source(db=db, collection_id=col.id, req=req)

    # Invariant: Ownerless binding được gán group_source_id ngay trong attach
    assert ownerless_bnd.group_source_id is not None
    # Staging index được build cho revision 2 mới
    mock_builder.build_staging_index.assert_called_once()
    assert res.status == "review_required"


@pytest.mark.asyncio
async def test_ownerless_binding_with_ready_staging_adopted_and_promoted_without_rebuild():
    """Ca bổ sung 6: Ownerless binding có ready staging được adopt và promote mà không build lại."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc = RepositoryDocument(
        id="doc_staged",
        title="Tài liệu",
        current_revision_id="rev_2",
        is_active=True,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
    )
    rev_2 = DocumentRevision(id="rev_2", document_id="doc_staged", revision_no=2, status="ready")

    ownerless_bnd = KnowledgeBinding(
        id="bnd_ownerless_staged",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id="rev_1",
        active_index_revision_id="idx_1",
        group_source_id=None,
        status="active",
    )
    ready_staging = KnowledgeIndexRevision(
        id="idx_staging_ready",
        binding_id=ownerless_bnd.id,
        source_revision_id=rev_2.id,
        revision_no=2,
        status="ready",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else None))

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from repository_documents" in stmt_str:
            return _execute_result(all_rows=[(doc, rev_2)])
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[ownerless_bnd])
        if "from knowledge_index_revisions" in stmt_str and "status = 'ready'" in stmt_str:
            return _execute_result(scalar_one_or_none=ready_staging, scalar=ready_staging)
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalars_list=[ready_staging])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.build_staging_index = AsyncMock()
    mock_builder.promote_index_revision = AsyncMock()

    service = GroupSourceService(index_build_service=mock_builder)
    req = AttachGroupSourceRequest(group_id=group.id, auto_activate=True)
    res = await service.attach_group_source(db=db, collection_id=col.id, req=req)

    # Invariant: KHÔNG build lại
    mock_builder.build_staging_index.assert_not_called()
    # Invariant: Promote được gọi với staging có sẵn
    mock_builder.promote_index_revision.assert_called_once()
    # Invariant: Ownerless binding được gán group_source_id
    assert ownerless_bnd.group_source_id is not None
    assert res.status == "ready"


# =========================================================================
# REGRESSION TESTS CHO ERROR CODES: CONFLICT VS REVISION FAILED
# =========================================================================


def test_populate_failed_items_upserts_conflict_over_existing_result():
    """Conflict phải thay thế cả success và lỗi tổng quát, không làm response mâu thuẫn."""
    doc, rev = _make_doc_and_revision("doc_conflict_upsert", "rev_conflict_upsert")
    foreign_bnd = KnowledgeBinding(
        id="bnd_conflict_upsert",
        collection_id="col_1",
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        group_source_id="src_foreign",
        status="active",
    )
    diff = {
        "conflict_docs": [(doc, rev, foreign_bnd)],
        "items": [
            PreviewGroupSourceDiffItem(
                document_id=doc.id,
                title=doc.title,
                revision_id=rev.id,
                category="failed",
                reason="Tài liệu đã thuộc nguồn nhóm khác.",
            )
        ],
    }

    for existing_item in (
        DocumentSyncItemResult(document_id=doc.id, status="success"),
        DocumentSyncItemResult(
            document_id=doc.id,
            status="failed",
            error_code="DOCUMENT_REVISION_FAILED",
        ),
    ):
        items = [existing_item]
        failed_document_ids: set[str] = set()

        populate_failed_items_from_diff(diff, items, failed_document_ids)

        assert failed_document_ids == {doc.id}
        assert len(items) == 1
        assert items[0].status == "failed"
        assert items[0].error_code == "DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE"


@pytest.mark.asyncio
async def test_sync_single_conflict_returns_ownership_error_code():
    """Ca 1: Một conflict duy nhất -> failed_count=1, error_code='DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE'."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc, rev = _make_doc_and_revision("doc_conflict", "rev_conflict")
    source = KnowledgeGroupSource(id="src_sync_conflict", collection_id=col.id, document_group_id=group.id, status="syncing")

    foreign_bnd = KnowledgeBinding(
        id="bnd_foreign",
        collection_id=col.id,
        repository_document_id=doc.id,
        source_revision_id=rev.id,
        group_source_id="src_foreign",
        status="active",
        active_index_revision_id="idx_foreign",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    diff_before = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc.id, rev.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_conflict",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 1,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 1,
        "needs_build_count": 0,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 0,
        "items": [
            PreviewGroupSourceDiffItem(
                document_id=doc.id,
                title=doc.title,
                category="failed",
                reason=f"Tài liệu '{doc.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                revision_id=rev.id,
            )
        ],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [(doc, rev, foreign_bnd)],
        "removed_bindings": [],
    }

    mock_builder = MagicMock(spec=IndexBuildService)
    service = GroupSourceService(index_build_service=mock_builder)
    service.diff_service.evaluate_group_diff = AsyncMock(return_value=diff_before)

    req = SyncGroupSourceRequest(auto_publish=False)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    # Invariants
    assert res.failed_count == 1
    assert len(res.items) == 1
    assert res.items[0].document_id == doc.id
    assert res.items[0].error_code == "DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE"
    assert res.status == "failed"


@pytest.mark.asyncio
async def test_sync_single_revision_failed_returns_revision_failed_error_code():
    """Ca 2: Một revision failed thông thường -> error_code='DOCUMENT_REVISION_FAILED'."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc = RepositoryDocument(id="doc_failed", title="Tài liệu lỗi", current_revision_id="rev_failed", is_active=True, tenant_id=col.tenant_id, workspace_id=col.workspace_id)
    rev_failed = DocumentRevision(id="rev_failed", document_id="doc_failed", revision_no=1, status="failed")
    source = KnowledgeGroupSource(id="src_sync_failed", collection_id=col.id, document_group_id=group.id, status="syncing")

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    diff_before = {
        "group": group,
        "collection": col,
        "desired_pairs": [],
        "eligible_doc_count": 0,
        "membership_hash": "hash_failed",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 1,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 1,
        "needs_build_count": 0,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 0,
        "items": [
            PreviewGroupSourceDiffItem(
                document_id=doc.id,
                title=doc.title,
                category="failed",
                reason="Phiên bản tài liệu đang ở trạng thái lỗi (failed).",
                revision_id=rev_failed.id,
            )
        ],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [],
        "removed_bindings": [],
    }

    mock_builder = MagicMock(spec=IndexBuildService)
    service = GroupSourceService(index_build_service=mock_builder)
    service.diff_service.evaluate_group_diff = AsyncMock(return_value=diff_before)

    req = SyncGroupSourceRequest(auto_publish=False)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    # Invariants
    assert res.failed_count == 1
    assert len(res.items) == 1
    assert res.items[0].document_id == doc.id
    assert res.items[0].error_code == "DOCUMENT_REVISION_FAILED"
    assert res.status == "failed"


@pytest.mark.asyncio
async def test_sync_conflict_and_build_failure_keeps_distinct_error_codes():
    """Ca 3: Một conflict và một build failure ở 2 tài liệu -> failed_count=2, mã lỗi phân biệt, không trùng."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc_conflict, rev_conflict = _make_doc_and_revision("doc_conflict", "rev_conflict")
    doc_build, rev_build = _make_doc_and_revision("doc_build", "rev_build")
    source = KnowledgeGroupSource(id="src_sync_both", collection_id=col.id, document_group_id=group.id, status="syncing")

    foreign_bnd = KnowledgeBinding(
        id="bnd_foreign",
        collection_id=col.id,
        repository_document_id=doc_conflict.id,
        source_revision_id=rev_conflict.id,
        group_source_id="src_foreign",
        status="active",
        active_index_revision_id="idx_foreign",
    )
    bnd_build = KnowledgeBinding(
        id="bnd_build",
        collection_id=col.id,
        repository_document_id=doc_build.id,
        source_revision_id=rev_build.id,
        group_source_id=source.id,
        status="pending",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    diff_before = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc_build.id, rev_build.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_mix",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 2,
        "added_count": 1,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 1,
        "needs_build_count": 1,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 0,
        "items": [
            PreviewGroupSourceDiffItem(
                document_id=doc_conflict.id,
                title=doc_conflict.title,
                category="failed",
                reason=f"Tài liệu '{doc_conflict.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                revision_id=rev_conflict.id,
            ),
            PreviewGroupSourceDiffItem(
                document_id=doc_build.id,
                title=doc_build.title,
                category="added",
                reason="Tài liệu mới trong nhóm, cần tạo chỉ mục.",
                revision_id=rev_build.id,
            ),
        ],
        "added_docs": [(doc_build, rev_build)],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [(doc_conflict, rev_conflict, foreign_bnd)],
        "removed_bindings": [],
    }

    diff_after = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc_build.id, rev_build.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_mix",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 2,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 2,
        "needs_build_count": 1,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 0,
        "items": [
            PreviewGroupSourceDiffItem(
                document_id=doc_conflict.id,
                title=doc_conflict.title,
                category="failed",
                reason=f"Tài liệu '{doc_conflict.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                revision_id=rev_conflict.id,
            ),
        ],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [(doc_conflict, rev_conflict, foreign_bnd)],
        "removed_bindings": [],
    }

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalar_one_or_none=bnd_build, scalar=bnd_build, scalars_list=[bnd_build])
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalar_one_or_none=None, scalar=None, scalars_list=[])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    failed_staging = KnowledgeIndexRevision(
        id="idx_staging_fail",
        binding_id=bnd_build.id,
        source_revision_id=rev_build.id,
        revision_no=1,
        status="failed",
        failure_code="STAGING_BUILD_FAILED",
        failure_detail="Xây dựng chỉ mục staging thất bại do lỗi chunking.",
    )

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.build_staging_index = AsyncMock(return_value=failed_staging)

    service = GroupSourceService(index_build_service=mock_builder)
    service.diff_service.evaluate_group_diff = AsyncMock(side_effect=[diff_before, diff_after])

    req = SyncGroupSourceRequest(auto_publish=False)
    res = await service.sync_group_source(db=db, collection_id=col.id, source_id=source.id, req=req)

    # Invariants:
    # 1. failed_count == 2
    assert res.failed_count == 2
    # 2. Mỗi tài liệu xuất hiện đúng một lần trong res.items
    doc_ids_in_items = [it.document_id for it in res.items]
    assert len(doc_ids_in_items) == 2
    assert len(set(doc_ids_in_items)) == 2

    # 3. Conflict giữ mã ownership conflict
    conflict_res = next(it for it in res.items if it.document_id == doc_conflict.id)
    assert conflict_res.error_code == "DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE"

    # 4. Build failure giữ mã build tương ứng
    build_res = next(it for it in res.items if it.document_id == doc_build.id)
    assert build_res.error_code == "STAGING_BUILD_FAILED"


@pytest.mark.asyncio
async def test_publish_with_one_success_and_one_conflict_preserves_error_code():
    """Ca 4: Publish có 1 tài liệu publish được và 1 tài liệu conflict -> conflict không bị thành DOCUMENT_REVISION_FAILED."""
    db = _fresh_session()
    col = _make_collection()
    group = _make_group()
    doc_ok, rev_ok = _make_doc_and_revision("doc_ok", "rev_ok")
    doc_conflict, rev_conflict = _make_doc_and_revision("doc_conflict_pub", "rev_conflict_pub")
    source = KnowledgeGroupSource(id="src_pub_both", collection_id=col.id, document_group_id=group.id, status="review_required")

    bnd_ok = KnowledgeBinding(
        id="bnd_ok",
        collection_id=col.id,
        repository_document_id=doc_ok.id,
        source_revision_id=rev_ok.id,
        group_source_id=source.id,
        status="pending",
    )
    staging_ok = KnowledgeIndexRevision(
        id="idx_staging_ok",
        binding_id=bnd_ok.id,
        source_revision_id=rev_ok.id,
        revision_no=1,
        status="ready",
    )

    foreign_bnd = KnowledgeBinding(
        id="bnd_foreign_pub",
        collection_id=col.id,
        repository_document_id=doc_conflict.id,
        source_revision_id=rev_conflict.id,
        group_source_id="src_other",
        status="active",
        active_index_revision_id="idx_other",
    )

    db.get = AsyncMock(side_effect=lambda model, ident: col if model is KnowledgeCollection else (group if model is DocumentGroup else (source if model is KnowledgeGroupSource else None)))

    diff_before = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc_ok.id, rev_ok.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_pub",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 2,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "not_ready_count": 0,
        "failed_count": 1,
        "needs_build_count": 0,
        "awaiting_publish_count": 1,
        "publishable_count": 1,
        "ready_active_docs_count": 0,
        "items": [
            PreviewGroupSourceDiffItem(
                document_id=doc_conflict.id,
                title=doc_conflict.title,
                category="failed",
                reason=f"Tài liệu '{doc_conflict.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                revision_id=rev_conflict.id,
            ),
        ],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [(doc_ok, rev_ok, bnd_ok, staging_ok)],
        "updated_docs": [],
        "conflict_docs": [(doc_conflict, rev_conflict, foreign_bnd)],
        "removed_bindings": [],
    }

    # Sau publish: doc_ok đã active, doc_conflict vẫn conflict trong diff_after
    diff_after = {
        "group": group,
        "collection": col,
        "desired_pairs": [(doc_ok.id, rev_ok.id)],
        "eligible_doc_count": 1,
        "membership_hash": "hash_pub",
        "last_membership_hash": None,
        "has_changes": True,
        "total_documents_in_group": 2,
        "added_count": 0,
        "updated_count": 0,
        "removed_count": 0,
        "unchanged_count": 1,
        "not_ready_count": 0,
        "failed_count": 1,
        "needs_build_count": 0,
        "awaiting_publish_count": 0,
        "publishable_count": 0,
        "ready_active_docs_count": 1,
        "items": [
            PreviewGroupSourceDiffItem(
                document_id=doc_conflict.id,
                title=doc_conflict.title,
                category="failed",
                reason=f"Tài liệu '{doc_conflict.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                revision_id=rev_conflict.id,
            ),
        ],
        "added_docs": [],
        "adoptable_docs": [],
        "awaiting_publish_docs": [],
        "updated_docs": [],
        "conflict_docs": [(doc_conflict, rev_conflict, foreign_bnd)],
        "removed_bindings": [],
    }

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "from knowledge_bindings" in stmt_str:
            return _execute_result(scalars_list=[bnd_ok])
        if "from knowledge_index_revisions" in stmt_str:
            return _execute_result(scalar_one_or_none=staging_ok, scalars_list=[staging_ok])
        return _execute_result(scalar=None)

    db.execute = AsyncMock(side_effect=execute_side_effect)

    mock_builder = MagicMock(spec=IndexBuildService)
    mock_builder.promote_index_revision = AsyncMock()

    service = GroupSourceService(index_build_service=mock_builder)
    service.diff_service.evaluate_group_diff = AsyncMock(side_effect=[diff_before, diff_after])

    res = await service.publish_group_source(db=db, collection_id=col.id, source_id=source.id)

    # Invariants:
    # 1. published_count == 1
    assert res.published_count == 1
    # 2. failed_count == 1
    assert res.failed_count == 1
    # 3. Conflict doc không bị biến thành DOCUMENT_REVISION_FAILED
    conflict_item = next(it for it in res.items if it.document_id == doc_conflict.id)
    assert conflict_item.error_code == "DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE"
    # 4. Trạng thái phản ánh failed vì có conflict
    assert res.status == "failed"

