"""Unit and Integration Tests for Logical Document Groups and Knowledge Group Attachment."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.auth.schemas import AuthActor
from app.modules.documents.group_service import document_group_service
from app.modules.documents.models import (
    DocumentGroup,
    DocumentRevision,
    RepositoryDocument,
)
from app.modules.documents.schemas import (
    AddGroupDocumentsRequest,
    DocumentGroupCreate,
    DocumentGroupUpdate,
)
from app.modules.documents.service import document_repository_service
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.knowledge.schemas import (
    AttachDocumentGroupRequest,
    BindingResultItem,
    CreateKnowledgeBindingsResponse,
    PreviewDocumentGroupRequest,
)
from app.modules.knowledge.services.binding_service import binding_service


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    result.scalar_one = MagicMock(return_value=scalar if scalar is not None else len(scalars_list or []))
    result.scalar = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_list or [])
    result.scalars = MagicMock(return_value=scalars)
    result.all = MagicMock(return_value=scalars_list or [])
    result.first = MagicMock(return_value=scalar)
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


def _make_document(
    doc_id: str,
    title: str = "Tài liệu mẫu",
    tenant_id: str = "tenant_qnu",
    workspace_id: str = "workspace_qnu",
    current_revision_id: str | None = None,
) -> RepositoryDocument:
    doc = RepositoryDocument(
        id=doc_id,
        title=title,
        file_name=f"{doc_id}.pdf",
        file_type="pdf",
        file_size_bytes=10240,
        file_hash=f"hash_{doc_id}",
        storage_path=f"storage/{doc_id}.pdf",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        is_active=True,
        status="active",
        parse_status="parsed",
        current_revision_id=current_revision_id,
        latest_revision_no=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return doc


def _make_revision(
    rev_id: str,
    doc_id: str,
    status: str = "ready",
) -> DocumentRevision:
    rev = DocumentRevision(
        id=rev_id,
        document_id=doc_id,
        revision_no=1,
        source_file_name=f"{doc_id}.pdf",
        source_file_type="pdf",
        source_size_bytes=10240,
        source_hash=f"hash_{doc_id}",
        source_storage_path=f"storage/{doc_id}.pdf",
        status=status,
        lock_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return rev


def _make_collection(
    col_id: str = "col_tuyensinh",
    tenant_id: str = "tenant_qnu",
    workspace_id: str = "workspace_qnu",
) -> KnowledgeCollection:
    col = KnowledgeCollection(
        id=col_id,
        name="Kho Tuyển sinh 2026",
        module_code="admissions",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return col


# =========================================================================
# 0. Regression Test: Verify singleton mock is never leaked
# =========================================================================
def test_binding_service_create_bindings_unmocked() -> None:
    """Verify that binding_service.create_bindings is the real method, not an AsyncMock."""
    assert not isinstance(binding_service.create_bindings, (Mock, AsyncMock))


# =========================================================================
# 1. Test CRUD Group Lifecycle & Atomic Optimistic Locking
# =========================================================================
@pytest.mark.asyncio
async def test_group_crud_lifecycle() -> None:
    session = _fresh_session()
    session.execute.return_value = _execute_result(scalar=None)

    # 1. Create group
    req = DocumentGroupCreate(name="Tuyển sinh 2026", description="Nhóm tài liệu đề án tuyển sinh")
    created = await document_group_service.create_group(
        db=session,
        req=req,
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )
    assert created.name == "Tuyển sinh 2026"
    assert created.total_documents == 0
    assert session.add.called
    assert session.commit.called

    # 2. Get group
    group_obj = DocumentGroup(
        id=created.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Tuyển sinh 2026",
        lock_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.get.return_value = group_obj
    session.execute.return_value = _execute_result(scalars_list=[])
    detail = await document_group_service.get_group(
        db=session,
        group_id=created.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )
    assert detail.id == created.id

    # 3. Atomic update group with lock_version
    group_updated_obj = DocumentGroup(
        id=created.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Tuyển sinh 2026 Đã Đổi Tên",
        description="Mô tả mới",
        lock_version=2,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.execute.return_value = _execute_result(scalar=None)
    session.get.return_value = group_updated_obj
    update_req = DocumentGroupUpdate(
        name="Tuyển sinh 2026 Đã Đổi Tên",
        description="Mô tả mới",
        expected_lock_version=1,
    )
    updated = await document_group_service.update_group(
        db=session,
        group_id=created.id,
        req=update_req,
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )
    assert updated.name == "Tuyển sinh 2026 Đã Đổi Tên"
    assert updated.lock_version == 2

    # 4. Delete group
    await document_group_service.delete_group(
        db=session,
        group_id=created.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )
    assert session.delete.called


# =========================================================================
# 2. Test Atomic Optimistic Locking Conflict (Concurrent Updates)
# =========================================================================
@pytest.mark.asyncio
async def test_atomic_optimistic_locking_conflict() -> None:
    session = _fresh_session()
    group = DocumentGroup(
        id="grp_01",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Gốc",
        lock_version=2,  # Current DB version is 2
    )
    session.get.return_value = group

    # Mock execute rowcount = 0 (simulating update failure because expected_lock_version was 1)
    res_zero = MagicMock()
    res_zero.rowcount = 0
    session.execute.return_value = res_zero

    update_req = DocumentGroupUpdate(
        name="Nhóm Đổi Tên Lỗi",
        expected_lock_version=1,  # Stale version
    )

    with pytest.raises(AppException) as exc:
        await document_group_service.update_group(
            db=session,
            group_id="grp_01",
            req=update_req,
            tenant_id="tenant_qnu",
            workspace_id="workspace_qnu",
        )
    assert exc.value.code == "OPTIMISTIC_LOCK_CONFLICT"
    assert exc.value.status_code == 409


# =========================================================================
# 3. Test Group Name Normalization & Case-Insensitive Uniqueness
# =========================================================================
@pytest.mark.asyncio
async def test_group_name_normalization_and_uniqueness() -> None:
    # 1. Validation test: whitespace only rejected
    with pytest.raises(ValidationError):
        DocumentGroupCreate(name="   ")

    with pytest.raises(ValidationError):
        DocumentGroupCreate(name="")

    # 2. Normalization test: excessive spaces collapsed, trimmed
    req = DocumentGroupCreate(name="  Tuyển   sinh   2026  ")
    assert req.name == "Tuyển sinh 2026"

    # 3. Duplicate name check in DB (case-insensitive)
    session = _fresh_session()
    existing_group = DocumentGroup(
        id="grp_existing",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Tuyển sinh 2026",
        lock_version=1,
    )
    session.execute.return_value = _execute_result(scalar=existing_group)

    with pytest.raises(AppException) as exc_dup:
        await document_group_service.create_group(
            db=session,
            req=DocumentGroupCreate(name="tuyển sinh 2026"),  # lower case duplicate
            tenant_id="tenant_qnu",
            workspace_id="workspace_qnu",
        )
    assert exc_dup.value.code == "DOCUMENT_GROUP_NAME_CONFLICT"
    assert exc_dup.value.status_code == 409

    # 4. IntegrityError catch when unique functional index triggers
    session_ie = _fresh_session()
    session_ie.execute.return_value = _execute_result(scalar=None)  # pass Python pre-check
    session_ie.commit.side_effect = IntegrityError("duplicate key", params={}, orig=Exception())

    with pytest.raises(AppException) as exc_ie:
        await document_group_service.create_group(
            db=session_ie,
            req=DocumentGroupCreate(name="Tuyển sinh 2026"),
            tenant_id="tenant_qnu",
            workspace_id="workspace_qnu",
        )
    assert exc_ie.value.code == "DOCUMENT_GROUP_NAME_CONFLICT"
    assert exc_ie.value.status_code == 409
    assert session_ie.rollback.called


# =========================================================================
# 4. Test Audit Actor Identifier Hierarchy
# =========================================================================
@pytest.mark.asyncio
async def test_audit_actor_identification() -> None:
    session = _fresh_session()
    session.execute.return_value = _execute_result(scalar=None)

    # Actor with actor_id
    actor = AuthActor(
        actor_id="act_officer_42",
        username="officer_tuan",
        display_name="Cán bộ Tuấn",
        email="tuan@qnu.edu.vn",
        user_type="admin",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        role="admin",
        roles=["admin"],
        permissions=["*"],
    )

    created = await document_group_service.create_group(
        db=session,
        req=DocumentGroupCreate(name="Nhóm Kiểm Tra Audit"),
        actor=actor,
    )
    assert created.created_by == "act_officer_42"

    # Add document to group with actor
    group = DocumentGroup(
        id="grp_audit",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Audit",
        lock_version=1,
    )
    doc = _make_document("doc_audit")
    session.get.return_value = group
    session.execute.side_effect = [
        _execute_result(scalars_list=[]),  # existing check
        _execute_result(scalars_list=[doc]),  # valid doc check
    ]
    add_res = await document_group_service.add_documents_to_group(
        db=session,
        group_id="grp_audit",
        req=AddGroupDocumentsRequest(document_ids=["doc_audit"]),
        actor=actor,
    )
    assert add_res.added_count == 1
    # Check added membership in session
    added_membership = session.add.call_args[0][0]
    assert added_membership.added_by == "act_officer_42"


# =========================================================================
# 5. Test Tenant & Workspace Isolation in List Documents
# =========================================================================
@pytest.mark.asyncio
async def test_list_documents_tenant_and_workspace_isolation() -> None:
    session = _fresh_session()
    actor_a = AuthActor(
        actor_id="act_a",
        username="admin_a",
        display_name="Admin A",
        email="a@qnu.edu.vn",
        user_type="admin",
        tenant_id="tenant_qnu",
        workspace_id="workspace_engineering",
        role="admin",
        roles=["admin"],
        permissions=["*"],
    )

    # 1. Foreign workspace group filter is denied
    foreign_group = DocumentGroup(
        id="grp_medical",
        tenant_id="tenant_qnu",
        workspace_id="workspace_medical",  # Different workspace!
        name="Nhóm Y Dược",
        lock_version=1,
    )
    session.get.return_value = foreign_group

    with pytest.raises(AppException) as exc:
        await document_repository_service.list_documents(
            db=session,
            group_id="grp_medical",
            actor=actor_a,
        )
    assert exc.value.code == "DOCUMENT_GROUP_ACCESS_DENIED"
    assert exc.value.status_code == 403

    # 2. Listing documents with exclude_group_id works
    session.get.return_value = None
    session.execute.side_effect = [
        _execute_result(scalar=0),  # total count
        _execute_result(scalars_list=[]),  # docs query
    ]
    items, total = await document_repository_service.list_documents(
        db=session,
        exclude_group_id="grp_engineering",
        actor=actor_a,
    )
    assert items == []
    assert total == 0


# =========================================================================
# 6. Test Server-side Preview Document Group (Read-Only)
# =========================================================================
@pytest.mark.asyncio
async def test_preview_document_group_server_side() -> None:
    session = _fresh_session()
    col = _make_collection("col_qnu")
    group = DocumentGroup(
        id="grp_preview",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Preview",
        lock_version=1,
    )

    doc_ready = _make_document("doc_ready", current_revision_id="rev_ready")
    doc_unready = _make_document("doc_unready", current_revision_id="rev_unready")
    doc_bound = _make_document("doc_bound", current_revision_id="rev_bound")

    rev_ready = _make_revision("rev_ready", "doc_ready", status="ready")
    rev_unready = _make_revision("rev_unready", "doc_unready", status="review_required")
    rev_bound = _make_revision("rev_bound", "doc_bound", status="ready")

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection:
            return col if obj_id == "col_qnu" else None
        if model is DocumentGroup:
            return group if obj_id == "grp_preview" else None
        return None

    session.get.side_effect = _mock_get
    session.execute.side_effect = [
        _execute_result(scalars_list=[doc_ready, doc_unready, doc_bound]),  # group_docs
        _execute_result(scalars_list=["doc_bound"]),  # bound_doc_ids
        _execute_result(scalars_list=[rev_ready, rev_unready, rev_bound]),  # revs_map
    ]

    req = PreviewDocumentGroupRequest(group_id="grp_preview")
    res = await binding_service.preview_document_group(
        db=session,
        collection_id="col_qnu",
        req=req,
    )

    assert res.collection_id == "col_qnu"
    assert res.group_id == "grp_preview"
    assert res.group_name == "Nhóm Preview"
    assert res.total_documents == 3
    assert res.ready_count == 1
    assert res.already_bound_count == 1
    assert res.not_ready_count == 1
    assert res.failed_count == 0
    assert len(res.items) == 3
    # Verify no DB commit or mutations took place
    assert not session.commit.called


# =========================================================================
# 7. Test Attach Group Ready Revisions Only (with monkeypatch)
# =========================================================================
@pytest.mark.asyncio
async def test_attach_group_ready_revisions_only(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _fresh_session()
    col = _make_collection("col_qnu")
    group = DocumentGroup(
        id="grp_mixed",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Đan Xen",
        lock_version=1,
    )

    doc_ready = _make_document("doc_ready", current_revision_id="rev_ready")
    doc_unready = _make_document("doc_unready", current_revision_id="rev_unready")

    rev_ready = _make_revision("rev_ready", "doc_ready", status="ready")
    rev_unready = _make_revision("rev_unready", "doc_unready", status="review_required")

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection:
            return col if obj_id == "col_qnu" else None
        if model is DocumentGroup:
            return group if obj_id == "grp_mixed" else None
        return None

    session.get.side_effect = _mock_get
    session.execute.side_effect = [
        _execute_result(scalars_list=[doc_ready, doc_unready]),  # group_docs
        _execute_result(scalars_list=[]),  # bound_doc_ids (none bound yet)
        _execute_result(scalars_list=[rev_ready, rev_unready]),  # revs
    ]

    mock_binding_res = CreateKnowledgeBindingsResponse(
        collection_id="col_qnu",
        created_count=1,
        skipped_count=0,
        failed_count=0,
        bindings=[
            BindingResultItem(
                binding_id="bnd_01",
                repository_document_id="doc_ready",
                source_revision_id="rev_ready",
                status="created",
                message="Liên kết thành công",
            )
        ],
    )
    monkeypatch.setattr(
        binding_service,
        "create_bindings",
        AsyncMock(return_value=mock_binding_res),
    )

    req = AttachDocumentGroupRequest(group_id="grp_mixed")
    res = await binding_service.attach_document_group(
        db=session,
        collection_id="col_qnu",
        req=req,
    )

    assert res.total_documents == 2
    assert res.created_count == 1
    assert res.not_ready_count == 1
    assert any(item.document_id == "doc_ready" and item.status == "created" for item in res.items)
    assert any(item.document_id == "doc_unready" and item.status == "not_ready" for item in res.items)


# =========================================================================
# 8. Test Attach Group Idempotent (with monkeypatch)
# =========================================================================
@pytest.mark.asyncio
async def test_attach_group_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _fresh_session()
    col = _make_collection("col_qnu")
    group = DocumentGroup(
        id="grp_repeat",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Lặp",
        lock_version=1,
    )
    doc = _make_document("doc_01", current_revision_id="rev_01")
    rev = _make_revision("rev_01", "doc_01", status="ready")

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection:
            return col if obj_id == "col_qnu" else None
        if model is DocumentGroup:
            return group if obj_id == "grp_repeat" else None
        return None

    session.get.side_effect = _mock_get
    session.execute.side_effect = [
        _execute_result(scalars_list=[doc]),  # group_docs
        _execute_result(scalars_list=["doc_01"]),  # bound_doc_ids: already bound!
        _execute_result(scalars_list=[rev]),  # revs
    ]

    req = AttachDocumentGroupRequest(group_id="grp_repeat")
    res = await binding_service.attach_document_group(
        db=session,
        collection_id="col_qnu",
        req=req,
    )
    assert res.total_documents == 1
    assert res.created_count == 0
    assert res.already_bound_count == 1
    assert res.items[0].status == "already_bound"


# =========================================================================
# 9. Test Attach Group Manual Snapshot Boundary (with monkeypatch)
# =========================================================================
@pytest.mark.asyncio
async def test_attach_group_manual_snapshot_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _fresh_session()
    col = _make_collection("col_qnu")
    group = DocumentGroup(
        id="grp_snap",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Snapshot",
        lock_version=1,
    )

    doc1 = _make_document("doc_01", current_revision_id="rev_01")
    rev1 = _make_revision("rev_01", "doc_01", status="ready")

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection:
            return col if obj_id == "col_qnu" else None
        if model is DocumentGroup:
            return group if obj_id == "grp_snap" else None
        return None

    session.get.side_effect = _mock_get
    session.execute.side_effect = [
        _execute_result(scalars_list=[doc1]),
        _execute_result(scalars_list=[]),  # not yet bound
        _execute_result(scalars_list=[rev1]),
    ]

    monkeypatch.setattr(
        binding_service,
        "create_bindings",
        AsyncMock(
            return_value=CreateKnowledgeBindingsResponse(
                collection_id="col_qnu",
                created_count=1,
                skipped_count=0,
                failed_count=0,
                bindings=[
                    BindingResultItem(
                        binding_id="bnd_01",
                        repository_document_id="doc_01",
                        source_revision_id="rev_01",
                        status="created",
                    )
                ],
            )
        ),
    )

    req = AttachDocumentGroupRequest(group_id="grp_snap")
    res1 = await binding_service.attach_document_group(db=session, collection_id="col_qnu", req=req)
    assert res1.created_count == 1
    assert len(res1.items) == 1
    assert res1.items[0].document_id == "doc_01"


# =========================================================================
# 10. Test Breakdown Counts Reporting (with monkeypatch)
# =========================================================================
@pytest.mark.asyncio
async def test_attach_group_breakdown_counts_reporting(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _fresh_session()
    col = _make_collection("col_qnu")
    group = DocumentGroup(
        id="grp_counts",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Đếm",
        lock_version=1,
    )

    d1 = _make_document("d1", current_revision_id="r1")
    d2 = _make_document("d2", current_revision_id="r2")
    d3 = _make_document("d3", current_revision_id="r3")
    r1 = _make_revision("r1", "d1", status="ready")
    r2 = _make_revision("r2", "d2", status="ready")
    r3 = _make_revision("r3", "d3", status="failed")

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection:
            return col if obj_id == "col_qnu" else None
        if model is DocumentGroup:
            return group if obj_id == "grp_counts" else None
        return None

    session.get.side_effect = _mock_get
    session.execute.side_effect = [
        _execute_result(scalars_list=[d1, d2, d3]),
        _execute_result(scalars_list=["d2"]),  # d2 is already bound
        _execute_result(scalars_list=[r1, r2, r3]),
    ]

    monkeypatch.setattr(
        binding_service,
        "create_bindings",
        AsyncMock(
            return_value=CreateKnowledgeBindingsResponse(
                collection_id="col_qnu",
                created_count=1,
                skipped_count=0,
                failed_count=0,
                bindings=[
                    BindingResultItem(binding_id="b1", repository_document_id="d1", status="created"),
                ],
            )
        ),
    )

    res = await binding_service.attach_document_group(
        db=session,
        collection_id="col_qnu",
        req=AttachDocumentGroupRequest(group_id="grp_counts"),
    )
    assert res.total_documents == 3
    assert res.created_count == 1
    assert res.already_bound_count == 1
    assert res.failed_count == 1
    assert next(item for item in res.items if item.document_id == "d3").status == "failed"


# =========================================================================
# 11. Test Empty Group and Not Found RFC 7807 Errors
# =========================================================================
@pytest.mark.asyncio
async def test_attach_group_empty_and_not_found_errors() -> None:
    session = _fresh_session()
    col = _make_collection("col_qnu")

    # 1. Group not found
    def _mock_get_no_group(model, obj_id):
        if model is KnowledgeCollection:
            return col if obj_id == "col_qnu" else None
        if model is DocumentGroup:
            return None
        return None

    session.get.side_effect = _mock_get_no_group

    with pytest.raises(AppException) as exc_grp:
        await binding_service.attach_document_group(
            db=session,
            collection_id="col_qnu",
            req=AttachDocumentGroupRequest(group_id="grp_non_existent"),
        )
    assert exc_grp.value.code == "DOCUMENT_GROUP_NOT_FOUND"

    # 2. Empty group
    group_empty = DocumentGroup(
        id="grp_empty",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Trống",
        lock_version=1,
    )

    def _mock_get_empty_group(model, obj_id):
        if model is KnowledgeCollection:
            return col if obj_id == "col_qnu" else None
        if model is DocumentGroup:
            return group_empty if obj_id == "grp_empty" else None
        return None

    session.get.side_effect = _mock_get_empty_group
    session.execute.side_effect = [
        _execute_result(scalars_list=[]),  # group members empty
    ]

    with pytest.raises(AppException) as exc_empty:
        await binding_service.attach_document_group(
            db=session,
            collection_id="col_qnu",
            req=AttachDocumentGroupRequest(group_id="grp_empty"),
        )
    assert exc_empty.value.code == "DOCUMENT_GROUP_EMPTY"

    # 3. Collection not found
    session.get.side_effect = lambda model, obj_id: None
    with pytest.raises(EntityNotFoundError) as exc_col:
        await binding_service.attach_document_group(
            db=session,
            collection_id="col_non_existent",
            req=AttachDocumentGroupRequest(group_id="grp_01"),
        )
    assert exc_col.value.code == "entity_not_found"


# =========================================================================
# 12. Test Strict Ready Mode Rejects Unready Documents with Details
# =========================================================================
@pytest.mark.asyncio
async def test_attach_group_strict_ready_rejects_unready() -> None:
    session = _fresh_session()
    col = _make_collection("col_qnu")
    group = DocumentGroup(
        id="grp_strict",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        name="Nhóm Strict",
        lock_version=1,
    )

    d1 = _make_document("d1", current_revision_id="r1")
    d2 = _make_document("d2", current_revision_id="r2")
    r1 = _make_revision("r1", "d1", status="ready")
    r2 = _make_revision("r2", "d2", status="review_required")

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection:
            return col if obj_id == "col_qnu" else None
        if model is DocumentGroup:
            return group if obj_id == "grp_strict" else None
        return None

    session.get.side_effect = _mock_get
    session.execute.side_effect = [
        _execute_result(scalars_list=[d1, d2]),
        _execute_result(scalars_list=[]),  # none bound
        _execute_result(scalars_list=[r1, r2]),
    ]

    with pytest.raises(AppException) as exc_strict:
        await binding_service.attach_document_group(
            db=session,
            collection_id="col_qnu",
            req=AttachDocumentGroupRequest(group_id="grp_strict", strict_ready=True),
        )
    assert exc_strict.value.code == "STRICT_READY_VIOLATION"
    assert exc_strict.value.status_code == 400
    assert exc_strict.value.details.get("total_documents") == 2
    assert exc_strict.value.details.get("ready_count") == 1
    assert exc_strict.value.details.get("not_ready_count") == 1

@pytest.mark.asyncio
async def test_upload_with_group_id_calls_add_documents_to_group():
    from unittest.mock import patch

    from fastapi import UploadFile

    from app.modules.documents.router import upload_document
    from app.modules.documents.schemas import AsyncUploadDocumentResponse

    session = _fresh_session()
    actor = AuthActor(sub="user_1", username="admin_qnu", tenant_id="tenant_qnu", workspace_id="ws_default", roles=["admin"])
    mock_file = AsyncMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=b'%PDF-1.4 test')
    mock_file.filename = 'tuyensinh_2026.pdf'

    mock_intake_res = AsyncUploadDocumentResponse(
        document_id='doc_ts_1',
        revision_id='rev_1',
        revision_no=1,
        file_name='tuyensinh_2026.pdf',
        file_hash='hash_123',
        job_id='job_1',
        status='queued',
        deduplicated=False,
        created_at=datetime.now(UTC),
    )

    with (
        patch('app.modules.documents.router.document_intake_service.intake_document', new_callable=AsyncMock) as mock_intake,
        patch('app.modules.documents.router.document_repository_service.get_document', new_callable=AsyncMock) as mock_repo_get,
    ):
        mock_intake.return_value = mock_intake_res
        mock_repo_get.return_value = MagicMock(id='doc_ts_1')

        res = await upload_document(
            file=mock_file,
            group_id='grp_ts',
            db=session,
            actor=actor,
        )

        assert res.id == 'doc_ts_1'
        mock_intake.assert_awaited_once()
        call_kwargs = mock_intake.await_args.kwargs
        assert call_kwargs['group_id'] == 'grp_ts'
        assert call_kwargs['actor'] == actor
