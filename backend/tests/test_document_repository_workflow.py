"""Comprehensive Workflow Test Suite for Document Repository (Kho Tài Liệu) & Intake V2.

Verifies the 12 core acceptance requirements defined in AGENTS.md & user specifications:
1. Tạo Kho tài liệu thành công (scoped tenant/workspace, normalized name).
2. Upload vào kho tạo document, revision, membership và job trong cùng 1 transaction (atomic orchestration unit).
3. group_id không tồn tại: không sinh document mồ côi (trả 404 RFC 7807).
4. Sai tenant/workspace: trả 403 RFC 7807 và không rò rỉ document.
5. Upload trùng trong cùng kho: idempotent (deduplicated=True, không tạo duplicate).
6. File đã tồn tại trong workspace nhưng chưa thuộc kho: tạo membership, không upload lại S3.
7. Redis offline: job ở trạng thái pending, không rollback document đã tiếp nhận.
8. Chỉ revision 'ready' được xuất bản vào Kho tri thức.
9. Strict-ready từ chối kho có tài liệu chưa sẵn sàng (STRICT_READY_VIOLATION).
10. Mỗi chunk strategy hợp lệ được factory phân giải đúng class.
11. Strategy không hợp lệ trả lỗi RFC 7807 INVALID_CHUNK_STRATEGY, không fallback âm thầm.
12. Hợp đồng quy trình hoàn chỉnh: Tạo kho → mở chi tiết → upload trực tiếp → preview → đưa vào Kho tri thức.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.exceptions import AppException
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.documents.group_service import document_group_service
from app.modules.documents.intake_service import document_intake_service
from app.modules.documents.models import (
    DocumentGroup,
    DocumentGroupMembership,
    DocumentRevision,
    RepositoryDocument,
)
from app.modules.documents.schemas import (
    AsyncUploadDocumentResponse,
    DocumentGroupCreate,
    RepositoryDocumentResponse,
)
from app.modules.documents.service import document_repository_service
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.chunker import (
    AdmissionsRecordChunker,
    ClauseBasedChunker,
    ImplementationTaskChunker,
    SemanticChunker,
    get_chunker,
)
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.knowledge.schemas import (
    AttachDocumentGroupRequest,
    PreviewDocumentGroupRequest,
)
from app.modules.knowledge.services.binding_service import binding_service

# -----------------------------------------------------------------------------
# Test Fixtures and Helpers
# -----------------------------------------------------------------------------


def _fresh_session() -> AsyncMock:
    """Create a mock database session with tracking for all transactional calls."""
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _execute_result(scalar=None, scalars_list=None):
    """Helper to mock SQLAlchemy execute result."""
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


def _make_actor(
    actor_id: str = "act_admissions_officer",
    tenant_id: str = "tenant_qnu",
    workspace_id: str = "workspace_tuyensinh",
) -> AuthActor:
    return AuthActor(
        actor_id=actor_id,
        username="tuyensinh_officer",
        display_name="Cán bộ Tuyển sinh",
        email="tuyensinh@qnu.edu.vn",
        user_type="officer",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        role="officer",
        roles=["officer", "AI.Admin"],
        permissions=["ai.knowledge.upload", "ai.knowledge.update", "documents:write", "knowledge:write"],
    )


def _make_doc(
    doc_id: str,
    file_name: str,
    file_bytes: bytes,
    tenant_id: str = "tenant_qnu",
    workspace_id: str = "workspace_tuyensinh",
    current_rev_id: str | None = None,
) -> RepositoryDocument:
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return RepositoryDocument(
        id=doc_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        title=file_name.rsplit(".", 1)[0],
        file_name=file_name,
        file_type="pdf",
        file_size_bytes=len(file_bytes),
        file_hash=file_hash,
        storage_path=f"documents/originals/{file_hash}/{file_name}",
        is_active=True,
        status="active",
        parse_status="ready",
        current_revision_id=current_rev_id,
        latest_revision_no=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_rev(
    rev_id: str,
    doc_id: str,
    file_name: str,
    file_bytes: bytes,
    status: str = "ready",
) -> DocumentRevision:
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return DocumentRevision(
        id=rev_id,
        document_id=doc_id,
        revision_no=1,
        source_file_name=file_name,
        source_file_type="pdf",
        source_size_bytes=len(file_bytes),
        source_hash=file_hash,
        source_storage_path=f"documents/originals/{file_hash}/{file_name}",
        status=status,
        lock_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# -----------------------------------------------------------------------------
# Test Cases (1 to 12)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_01_create_document_repository_group_success() -> None:
    """1. Tạo Kho tài liệu 'Tuyển sinh' thành công (scoped tenant/workspace, name normalization)."""
    session = _fresh_session()
    # Mock no existing group with same name
    session.execute.return_value = _execute_result(scalar=None)

    actor = _make_actor()
    req = DocumentGroupCreate(
        name="  Tuyển   sinh   2026  ",
        description="Kho tài liệu đề án tuyển sinh đại học chính quy 2026",
    )

    created = await document_group_service.create_group(
        db=session,
        req=req,
        actor=actor,
    )

    assert created.name == "Tuyển sinh 2026"  # Collapsed whitespace
    assert created.tenant_id == "tenant_qnu"
    assert created.workspace_id == "workspace_tuyensinh"
    assert created.created_by == "act_admissions_officer"
    assert created.total_documents == 0
    assert session.add.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_02_intake_upload_creates_doc_rev_membership_and_job_in_one_transaction() -> None:
    """2. Upload vào kho tạo document, revision, membership và job trong cùng 1 transaction."""
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_tuyensinh_2026"

    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Tuyển sinh 2026",
        lock_version=1,
    )
    session.get.return_value = group
    # Mock no duplicate file in DB
    session.execute.return_value = _execute_result(scalar=None)

    file_bytes = b"%PDF-1.4 De an tuyen sinh Dai hoc Quy Nhon 2026..."
    file_name = "de_an_tuyen_sinh_2026.pdf"

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock) as mock_s3_save, \
         patch("app.modules.documents.intake_service.enqueue_arq_job", new_callable=AsyncMock) as mock_arq:
        mock_arq.return_value = "arq_job_12345"

        resp = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name=file_name,
            group_id=group_id,
            actor=actor,
        )

        assert resp.document_id.startswith("rep_doc_")
        assert resp.revision_id.startswith("rev_")
        assert resp.job_id.startswith("job_intake_")
        assert resp.status == "queued"
        assert resp.deduplicated is False
        assert resp.file_name == file_name

        # Verify S3 persistence was called
        mock_s3_save.assert_awaited_once()

        # Verify atomic orchestration added RepositoryDocument, DocumentRevision, DocumentGroupMembership, JobRecord
        added_entities = [call[0][0] for call in session.add.call_args_list]
        added_types = [type(e) for e in added_entities]

        assert RepositoryDocument in added_types
        assert DocumentRevision in added_types
        assert DocumentGroupMembership in added_types
        assert JobRecord in added_types

        # Verify durable commit occurred
        assert session.commit.called


@pytest.mark.asyncio
async def test_03_intake_nonexistent_group_raises_404_and_no_orphan_doc() -> None:
    """3. group_id không tồn tại: trả 404 và không tạo document mồ côi hay file S3."""
    session = _fresh_session()
    actor = _make_actor()
    # Group does not exist
    session.get.return_value = None

    file_bytes = b"Sample content"

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock) as mock_s3_save:
        with pytest.raises(AppException) as exc_info:
            await document_intake_service.intake_document(
                db=session,
                file_bytes=file_bytes,
                file_name="orphan_test.pdf",
                group_id="grp_non_existent",
                actor=actor,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "DOCUMENT_GROUP_NOT_FOUND"
        # Ensure no S3 save and no DB add occurred
        mock_s3_save.assert_not_called()
        assert not session.add.called


@pytest.mark.asyncio
async def test_04_intake_mismatched_tenant_workspace_raises_403_no_leak() -> None:
    """4. Sai tenant/workspace: trả 403 RFC 7807 và không rò rỉ document."""
    session = _fresh_session()
    # Actor belongs to workspace_tuyensinh
    actor = _make_actor(workspace_id="workspace_tuyensinh")

    # Group belongs to a DIFFERENT workspace (workspace_y_duoc)
    foreign_group = DocumentGroup(
        id="grp_foreign",
        tenant_id="tenant_qnu",
        workspace_id="workspace_y_duoc",
        name="Kho Y Dược",
        lock_version=1,
    )
    session.get.return_value = foreign_group

    file_bytes = b"Unauthorized content"

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock) as mock_s3_save:
        with pytest.raises(AppException) as exc_info:
            await document_intake_service.intake_document(
                db=session,
                file_bytes=file_bytes,
                file_name="unauthorized.pdf",
                group_id="grp_foreign",
                actor=actor,
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.code == "DOCUMENT_GROUP_ACCESS_DENIED"
        mock_s3_save.assert_not_called()
        assert not session.add.called


@pytest.mark.asyncio
async def test_05_intake_duplicate_upload_same_group_idempotent() -> None:
    """5. Upload trùng trong cùng kho: idempotent, không tạo document/revision trùng, deduplicated=True."""
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_tuyensinh_2026"

    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Tuyển sinh 2026",
        lock_version=1,
    )
    session.get.return_value = group

    file_bytes = b"Exact duplicate content in Admissions"
    file_name = "thong_tin_tuyen_sinh.pdf"

    existing_doc = _make_doc("rep_doc_existing_1", file_name, file_bytes)
    rev_obj = _make_rev("rev_existing_1", existing_doc.id, file_name, file_bytes, status="ready")
    existing_doc.current_revision = rev_obj
    existing_mem = DocumentGroupMembership(group_id=group_id, document_id=existing_doc.id)

    # Mock DB query finding existing doc and existing membership and job query
    session.execute.side_effect = [
        _execute_result(scalar=existing_doc),  # scoped deduplication check
        _execute_result(scalar=existing_mem),  # membership check in group
        _execute_result(scalar=None),          # job check
    ]

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock) as mock_s3_save:
        resp = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name=file_name,
            group_id=group_id,
            actor=actor,
        )

        assert resp.deduplicated is True
        assert resp.document_id == existing_doc.id
        assert resp.status == "ready"
        assert resp.job_id is None
        mock_s3_save.assert_not_called()  # Did NOT upload again to S3


@pytest.mark.asyncio
async def test_06_intake_existing_doc_in_workspace_attaches_to_new_group_no_s3_reupload() -> None:
    """6. File đã tồn tại trong workspace nhưng chưa thuộc kho: tạo membership, không upload S3 lần hai."""
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_tuyensinh_2026"

    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Tuyển sinh 2026",
        lock_version=1,
    )
    session.get.return_value = group

    file_bytes = b"Shared guidelines across departments"
    file_name = "quy_che_chung.pdf"

    existing_doc = _make_doc("rep_doc_shared_100", file_name, file_bytes)
    rev_obj = _make_rev("rev_shared_1", existing_doc.id, file_name, file_bytes, status="ready")
    existing_doc.current_revision = rev_obj

    # Scoped dedup finds existing_doc, but membership does NOT exist yet in this group
    session.execute.side_effect = [
        _execute_result(scalar=existing_doc),  # scoped dedup found
        _execute_result(scalar=None),          # membership does NOT exist in grp_tuyensinh_2026
        _execute_result(scalar=None),          # job check
    ]

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock) as mock_s3_save:
        resp = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name=file_name,
            group_id=group_id,
            actor=actor,
        )

        assert resp.deduplicated is True
        assert resp.document_id == existing_doc.id
        assert resp.status == "ready"
        # S3 was NOT re-uploaded
        mock_s3_save.assert_not_called()
        # Membership was added and committed
        added_entities = [call[0][0] for call in session.add.call_args_list]
        memberships_added = [e for e in added_entities if isinstance(e, DocumentGroupMembership)]
        assert len(memberships_added) == 1
        assert memberships_added[0].group_id == group_id
        assert memberships_added[0].document_id == existing_doc.id
        assert session.commit.called


@pytest.mark.asyncio
async def test_07_intake_redis_offline_retains_pending_job_without_rollback() -> None:
    """7. Redis offline: job ở trạng thái pending cho reconciliation, không rollback document."""
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_tuyensinh_2026"

    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Tuyển sinh 2026",
        lock_version=1,
    )
    session.get.return_value = group
    session.execute.return_value = _execute_result(scalar=None)

    file_bytes = b"Document uploaded during Redis maintenance"
    file_name = "ke_hoach_offline.pdf"

    # Simulate Redis connection failure in enqueue_arq_job
    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock), \
         patch("app.modules.documents.intake_service.enqueue_arq_job", side_effect=ConnectionError("Redis connection refused")):

        resp = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name=file_name,
            group_id=group_id,
            actor=actor,
        )

        assert resp.status == "queued"
        # Find the added JobRecord in session
        added_entities = [call[0][0] for call in session.add.call_args_list]
        jobs = [e for e in added_entities if isinstance(e, JobRecord)]
        assert len(jobs) == 1
        # Job must be retained with pending status and error detail recorded
        assert jobs[0].dispatch_status == "pending"
        assert "Redis connection refused" in str(jobs[0].error)
        # Transaction was not rolled back; durable commit succeeded
        assert session.commit.called


@pytest.mark.asyncio
async def test_08_publish_only_ready_revisions_to_knowledge_collection() -> None:
    """8. Chỉ revision 'ready' được xuất bản vào Kho tri thức (khi cho phép partial)."""
    session = _fresh_session()
    group_id = "grp_partial"
    col_id = "col_tuyensinh"

    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho Tài Liệu Tổng Hợp",
        lock_version=1,
    )
    col = KnowledgeCollection(
        id=col_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho Tri Thức Tuyển Sinh",
        is_active=True,
    )

    doc_ready = _make_doc("doc_ready", "san_sang.pdf", b"Ready content", current_rev_id="rev_ready")
    doc_unready = _make_doc("doc_unready", "dang_xu_ly.pdf", b"Processing content", current_rev_id="rev_unready")

    rev_ready = _make_rev("rev_ready", "doc_ready", "san_sang.pdf", b"Ready content", status="ready")
    rev_unready = _make_rev("rev_unready", "doc_unready", "dang_xu_ly.pdf", b"Processing content", status="processing")

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection and obj_id == col_id:
            return col
        if model is DocumentGroup and obj_id == group_id:
            return group
        return None

    session.get.side_effect = _mock_get
    session.execute.side_effect = [
        _execute_result(scalars_list=[doc_ready, doc_unready]),  # 1. group_docs
        _execute_result(scalars_list=[]),                         # 2. bound_doc_ids
        _execute_result(scalars_list=[rev_ready, rev_unready]),  # 3. revs_map
    ]

    # Call attach with strict_ready=False (allow partial publishing)
    req = AttachDocumentGroupRequest(
        group_id=group_id,
        strict_ready=False,
        chunk_strategy="ClauseBasedChunker",
    )

    with patch.object(binding_service, "create_bindings", new_callable=AsyncMock) as mock_create_bindings:
        from app.modules.knowledge.schemas import BindingResultItem, CreateKnowledgeBindingsResponse

        mock_create_bindings.return_value = CreateKnowledgeBindingsResponse(
            collection_id=col_id,
            created_count=1,
            skipped_count=0,
            failed_count=0,
            bindings=[
                BindingResultItem(
                    binding_id="bind_1",
                    repository_document_id="doc_ready",
                    status="created",
                    message="Success",
                )
            ],
        )

        resp = await binding_service.attach_document_group(
            db=session,
            collection_id=col_id,
            req=req,
            tenant_id="tenant_qnu",
            workspace_id="workspace_tuyensinh",
        )

        assert resp.created_count == 1
        assert resp.not_ready_count == 1
        # Ensure create_bindings was called ONLY with doc_ready.id
        call_kwargs = mock_create_bindings.call_args[1]
        batch_items = call_kwargs["req"].items
        bound_doc_ids = [item.repository_document_id for item in batch_items]
        assert bound_doc_ids == ["doc_ready"]
        assert "doc_unready" not in bound_doc_ids


@pytest.mark.asyncio
async def test_09_strict_ready_rejects_publishing_when_unready_revisions_exist() -> None:
    """9. Strict-ready (mặc định) từ chối xuất bản khi còn tài liệu chưa sẵn sàng."""
    session = _fresh_session()
    group_id = "grp_strict_fail"
    col_id = "col_tuyensinh"

    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho Tài Liệu Đang Xử Lý",
        lock_version=1,
    )
    col = KnowledgeCollection(
        id=col_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho Tri Thức Tuyển Sinh",
        is_active=True,
    )

    doc_ready = _make_doc("doc_ready", "san_sang.pdf", b"Ready", current_rev_id="rev_ready")
    doc_unready = _make_doc("doc_unready", "loi.pdf", b"Error", current_rev_id="rev_unready")

    rev_ready = _make_rev("rev_ready", "doc_ready", "san_sang.pdf", b"Ready", status="ready")
    rev_unready = _make_rev("rev_unready", "doc_unready", "loi.pdf", b"Error", status="review_required")

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection and obj_id == col_id:
            return col
        if model is DocumentGroup and obj_id == group_id:
            return group
        return None

    session.get.side_effect = _mock_get
    session.execute.side_effect = [
        _execute_result(scalars_list=[doc_ready, doc_unready]),  # 1. group_docs
        _execute_result(scalars_list=[]),                         # 2. bound_doc_ids
        _execute_result(scalars_list=[rev_ready, rev_unready]),  # 3. revs_map
    ]

    # strict_ready=True by default
    req = AttachDocumentGroupRequest(
        group_id=group_id,
        strict_ready=True,
    )

    with pytest.raises(AppException) as exc_info:
        await binding_service.attach_document_group(
            db=session,
            collection_id=col_id,
            req=req,
            tenant_id="tenant_qnu",
            workspace_id="workspace_tuyensinh",
        )

    assert exc_info.value.code == "STRICT_READY_VIOLATION"
    assert exc_info.value.status_code == 400
    assert "chưa ở trạng thái sẵn sàng" in exc_info.value.message


def test_10_chunk_strategy_factory_resolves_all_canonical_classes() -> None:
    """10. Mỗi chunk strategy hợp lệ được factory phân giải đúng class."""
    strategies_and_expected_types = [
        ("ClauseBasedChunker", ClauseBasedChunker),
        ("clausebasedchunker", ClauseBasedChunker),
        ("clause_based", ClauseBasedChunker),
        ("SemanticChunker", SemanticChunker),
        ("semanticchunker", SemanticChunker),
        ("AdmissionsRecordChunker", AdmissionsRecordChunker),
        ("admissionsrecordchunker", AdmissionsRecordChunker),
        ("admissions", AdmissionsRecordChunker),
        ("ImplementationTaskChunker", ImplementationTaskChunker),
        ("implementationtaskchunker", ImplementationTaskChunker),
        ("implementation_task", ImplementationTaskChunker),
    ]

    for strategy_name, expected_type in strategies_and_expected_types:
        chunker = get_chunker(strategy_name)
        assert isinstance(chunker, expected_type), f"Strategy '{strategy_name}' did not resolve to {expected_type}"


def test_11_invalid_chunk_strategy_raises_rfc7807_no_silent_fallback() -> None:
    """11. Strategy không hợp lệ trả lỗi RFC 7807 INVALID_CHUNK_STRATEGY, không fallback âm thầm."""
    invalid_strategies = [
        "FixedSizeChunker",
        "NonExistentChunker",
        "random_strategy",
        "",
        " ",
    ]

    for invalid in invalid_strategies:
        with pytest.raises(AppException) as exc_info:
            get_chunker(invalid)

        assert exc_info.value.code == "INVALID_CHUNK_STRATEGY"
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_12_e2e_workflow_contract_create_group_intake_preview_and_attach() -> None:
    """12. Hợp đồng quy trình hoàn chỉnh: Tạo kho → mở chi tiết → upload trực tiếp → preview → đưa vào Kho tri thức."""
    session = _fresh_session()
    actor = _make_actor()

    # Step 1: Create Document Repository "Tuyển sinh"
    session.execute.return_value = _execute_result(scalar=None)
    create_req = DocumentGroupCreate(
        name="Tuyển sinh",
        description="Kho tài liệu phục vụ đề án tuyển sinh",
    )
    group_res = await document_group_service.create_group(
        db=session,
        req=create_req,
        actor=actor,
    )
    assert group_res.name == "Tuyển sinh"
    group_id = group_res.id

    # Step 2: Open Detail & Upload document directly to this group via Intake V2
    group_obj = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Tuyển sinh",
        lock_version=1,
    )
    session.get.return_value = group_obj
    session.execute.return_value = _execute_result(scalar=None)

    file_bytes = b"Noi dung van ban de an tuyen sinh..."
    file_name = "de_an_tuyen_sinh.pdf"

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock), \
         patch("app.modules.documents.intake_service.enqueue_arq_job", new_callable=AsyncMock) as mock_arq:
        mock_arq.return_value = "arq_123"

        intake_res = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name=file_name,
            group_id=group_id,
            actor=actor,
        )

        assert intake_res.document_id.startswith("rep_doc_")
        assert intake_res.status == "queued"
        doc_id = intake_res.document_id

    # Step 3: Document parser completes and revision becomes 'ready'
    rev_obj = _make_rev("rev_ts_1", doc_id, file_name, file_bytes, status="ready")
    doc_obj = _make_doc(doc_id, file_name, file_bytes, current_rev_id=rev_obj.id)

    col_id = "col_tuyensinh_target"
    col_obj = KnowledgeCollection(
        id=col_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho Tri Thức Tuyển Sinh",
        is_active=True,
    )

    def _mock_get(model, obj_id):
        if model is KnowledgeCollection and obj_id == col_id:
            return col_obj
        if model is DocumentGroup and obj_id == group_id:
            return group_obj
        return None

    session.get.side_effect = _mock_get

    # Step 4: Preview attaching group to knowledge collection
    session.execute.side_effect = [
        _execute_result(scalars_list=[doc_obj]),  # 1. group docs
        _execute_result(scalars_list=[]),          # 2. bound docs
        _execute_result(scalars_list=[rev_obj]),  # 3. revisions
    ]

    preview_req = PreviewDocumentGroupRequest(group_id=group_id)
    preview = await binding_service.preview_document_group(
        db=session,
        collection_id=col_id,
        req=preview_req,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
    )

    assert preview.total_documents == 1
    assert preview.ready_count == 1
    assert preview.not_ready_count == 0

    # Step 5: Publish all valid documents into Knowledge Collection
    session.execute.side_effect = [
        _execute_result(scalars_list=[doc_obj]),  # 1. group docs
        _execute_result(scalars_list=[]),          # 2. bound docs
        _execute_result(scalars_list=[rev_obj]),  # 3. revisions
    ]

    attach_req = AttachDocumentGroupRequest(
        group_id=group_id,
        strict_ready=True,
        chunk_strategy="ClauseBasedChunker",
    )

    with patch.object(binding_service, "create_bindings", new_callable=AsyncMock) as mock_create_bindings:
        from app.modules.knowledge.schemas import BindingResultItem, CreateKnowledgeBindingsResponse

        mock_create_bindings.return_value = CreateKnowledgeBindingsResponse(
            collection_id=col_id,
            created_count=1,
            skipped_count=0,
            failed_count=0,
            bindings=[
                BindingResultItem(
                    binding_id="bind_ts_1",
                    repository_document_id=doc_id,
                    status="created",
                    message="Success",
                )
            ],
        )

        attach_res = await binding_service.attach_document_group(
            db=session,
            collection_id=col_id,
            req=attach_req,
            tenant_id="tenant_qnu",
            workspace_id="workspace_tuyensinh",
        )

        assert attach_res.created_count == 1
        mock_create_bindings.assert_awaited_once()


@pytest.mark.asyncio
async def test_scope_isolated_storage_key_generation():
    """Requirement 1: Verify storage key is strictly isolated by scope:
    documents/{tenant_id}/{workspace_id}/originals/{file_hash}/{safe_file_name}
    and filenames with Vietnamese diacritics / special characters are safely normalized.
    """
    session = _fresh_session()
    actor = _make_actor(tenant_id="tenant_qnu_admissions", workspace_id="ws_2026")

    group_id = "grp_ts_isolated"
    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu_admissions",
        workspace_id="ws_2026",
        name="Kho Đề Án",
        lock_version=1,
    )
    session.get.return_value = group
    session.execute.return_value = _execute_result(scalar=None)

    file_bytes = b"Noi dung de an tuyen sinh 2026..."
    file_name = "Đề Án Tuyển Sinh & Kế Hoạch 2026.pdf"
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock) as mock_save, \
         patch("app.modules.documents.intake_service.enqueue_arq_job", new_callable=AsyncMock) as mock_arq:
        mock_arq.return_value = "job_test_1"

        res = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name=file_name,
            group_id=group_id,
            actor=actor,
        )

        assert res.document_id.startswith("rep_doc_")
        mock_save.assert_awaited_once()
        saved_key = mock_save.await_args.args[0]

        # Key must follow exact pattern: documents/{tenant_id}/{workspace_id}/originals/{file_hash}/{safe_file_name}
        expected_prefix = f"documents/tenant_qnu_admissions/ws_2026/originals/{file_hash}/"
        assert saved_key.startswith(expected_prefix)
        # Safe filename must not contain spaces or diacritics
        assert " " not in saved_key
        assert saved_key.endswith("de_an_tuyen_sinh_ke_hoach_2026.pdf")


@pytest.mark.asyncio
async def test_compensation_does_not_delete_other_tenant_storage_object():
    """Requirement 1: Verify storage compensation on database error strictly isolates deletion
    to the newly created object in the current tenant/workspace scope, never affecting another tenant's object.
    """
    file_bytes = b"Tai lieu dung chung giua hai phong ban..."
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    tenant_a_key = f"documents/tenant_a/ws_a/originals/{file_hash}/file_chung.pdf"
    tenant_b_key = f"documents/tenant_b/ws_b/originals/{file_hash}/file_chung.pdf"

    # Tenant B attempts upload but DB commit fails
    session_b = _fresh_session()
    actor_b = _make_actor(tenant_id="tenant_b", workspace_id="ws_b")
    group_b = DocumentGroup(
        id="grp_b",
        tenant_id="tenant_b",
        workspace_id="ws_b",
        name="Kho Ban B",
        lock_version=1,
    )
    session_b.get.return_value = group_b
    session_b.execute.return_value = _execute_result(scalar=None)
    # Simulate DB error during commit
    session_b.commit.side_effect = RuntimeError("Database connection lost during commit!")

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock), \
         patch("app.modules.documents.intake_service.storage_service.delete", new_callable=AsyncMock) as mock_delete:

        with pytest.raises(RuntimeError, match="Database connection lost"):
            await document_intake_service.intake_document(
                db=session_b,
                file_bytes=file_bytes,
                file_name="file_chung.pdf",
                group_id="grp_b",
                actor=actor_b,
            )

        # Compensation must ONLY delete tenant B's object
        mock_delete.assert_awaited_once_with(tenant_b_key)
        # Verify tenant A's object was NEVER touched
        deleted_keys = [call.args[0] for call in mock_delete.await_args_list]
        assert tenant_a_key not in deleted_keys


@pytest.mark.asyncio
async def test_deduplication_returns_v2_revision_status_and_real_job_id():
    """Requirement 5: Verify deduplication returns current revision V2 status
    and the real job_id from JobRecord, never returning legacy parse_status or fake strings.
    """
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_dedup_test"
    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho",
        lock_version=1,
    )
    session.get.return_value = group

    file_bytes = b"Van ban da ton tai san trong he thong..."
    doc_id = "rep_doc_existing_123"
    rev_id = "rev_v2_ready_456"
    real_job_id = "job_arq_real_789"

    doc_obj = _make_doc(doc_id, "van_ban.pdf", file_bytes, current_rev_id=rev_id)
    rev_obj = _make_rev(rev_id, doc_id, "van_ban.pdf", file_bytes, status="ready")
    doc_obj.current_revision = rev_obj
    membership = DocumentGroupMembership(group_id=group_id, document_id=doc_id)
    job_obj = JobRecord(id=real_job_id, job_type="document_revision_parse", status="queued")

    # Session execute queries:
    # 1. Existing doc by hash
    # 2. Existing membership in group
    # 3. Latest job query
    session.execute.side_effect = [
        _execute_result(scalar=doc_obj),     # doc found
        _execute_result(scalar=membership),  # membership already exists
        _execute_result(scalar=job_obj),     # job query
    ]

    res = await document_intake_service.intake_document(
        db=session,
        file_bytes=file_bytes,
        file_name="van_ban.pdf",
        group_id=group_id,
        actor=actor,
    )

    assert res.deduplicated is True
    assert res.status == "ready"
    assert res.job_id == real_job_id
    assert res.job_id != "deduplicated"
    assert res.job_id != "idempotent-replay"


@pytest.mark.asyncio
async def test_deduplication_corrupted_revision_raises_app_exception():
    """Requirement 5: When an existing document has a corrupted/unrecognized revision status,
    raise RFC 7807 DOCUMENT_REVISION_INVALID (409) rather than making up a fake status.
    """
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_corrupted_test"
    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho",
        lock_version=1,
    )
    session.get.return_value = group

    file_bytes = b"Corrupted doc test..."
    doc_id = "rep_doc_bad"
    rev_id = "rev_bad"

    doc_obj = _make_doc(doc_id, "bad.pdf", file_bytes, current_rev_id=rev_id)
    rev_obj = _make_rev(rev_id, doc_id, "bad.pdf", file_bytes, status="unknown_bogus_status")
    doc_obj.current_revision = rev_obj
    membership = DocumentGroupMembership(group_id=group_id, document_id=doc_id)

    session.execute.side_effect = [
        _execute_result(scalar=doc_obj),
        _execute_result(scalar=membership),
    ]

    with pytest.raises(AppException) as exc_info:
        await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name="bad.pdf",
            group_id=group_id,
            actor=actor,
        )
    assert exc_info.value.code == "DOCUMENT_REVISION_INVALID"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_concurrent_duplicate_intake_integrity_error_recovery():
    """Requirement: When concurrent requests attempt to insert the same file_hash for the same scope,
    IntegrityError is caught, rolled back, and the existing document is safely linked.
    """
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_race_123"
    group = DocumentGroup(
        id=group_id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho",
        lock_version=1,
    )
    session.get.return_value = group

    file_bytes = b"Concurrent race condition document payload..."
    doc_id = "rep_doc_winner"
    rev_id = "rev_winner"
    doc_obj = _make_doc(doc_id, "race.pdf", file_bytes, current_rev_id=rev_id)
    rev_obj = _make_rev(rev_id, doc_id, "race.pdf", file_bytes, status="queued")
    doc_obj.current_revision = rev_obj

    # In execute:
    # 1. Initial check: scalar=None (race: neither found yet)
    # 2. session.commit fails with IntegrityError
    # 3. recovery query: scalar=doc_obj
    # 4. membership query: scalar=None
    session.execute.side_effect = [
        _execute_result(scalar=None),     # Initial check finds nothing
        _execute_result(scalar=doc_obj),  # Recovery query after IntegrityError finds winner doc
        _execute_result(scalar=None),     # Membership check in winner doc
        _execute_result(scalar=None),     # Job query for winner doc
    ]
    # Commit fails on first attempt with IntegrityError, second commit for membership succeeds
    session.commit.side_effect = [
        IntegrityError("duplicate key value violates unique constraint", params={}, orig=Exception()),
        None,
    ]

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock), \
         patch("app.modules.documents.intake_service.enqueue_arq_job", new_callable=AsyncMock):

        res = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name="race.pdf",
            group_id=group_id,
            actor=actor,
        )

        assert res.document_id == doc_id
        assert res.status == "queued"
        assert res.deduplicated is True


@pytest.mark.asyncio
async def test_http_route_intake_idempotency_header():
    """Requirement 2: Verify HTTP route /documents/intake correctly reads Idempotency-Key header,
    replays response on identical payload, and returns 409 IDEMPOTENCY_KEY_REUSED on mismatched payload.
    """
    transport = ASGITransport(app=app)
    actor = _make_actor()
    session = _fresh_session()

    async def _override_actor():
        return actor

    async def _override_db():
        yield session

    app.dependency_overrides[get_current_actor] = _override_actor
    app.dependency_overrides[get_db] = _override_db

    group_id = "grp_http_idemp"
    group = DocumentGroup(
        id=group_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        name="Kho HTTP",
        lock_version=1,
    )

    diff_group = DocumentGroup(
        id="different_group_999",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        name="Kho Khac",
        lock_version=1,
    )

    def _mock_get(model, obj_id):
        if model is DocumentGroup and obj_id == group_id:
            return group
        if model is DocumentGroup and obj_id == "different_group_999":
            return diff_group
        return None

    session.get.side_effect = _mock_get

    saved_docs: dict[str, RepositoryDocument] = {}
    saved_revs: dict[str, tuple[DocumentRevision, RepositoryDocument]] = {}

    def _tracking_add(obj):
        if isinstance(obj, RepositoryDocument):
            saved_docs[obj.id] = obj
        elif isinstance(obj, DocumentRevision):
            saved_revs[str(obj.idempotency_key)] = (obj, saved_docs.get(obj.document_id))

    session.add.side_effect = _tracking_add

    async def _smart_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt)
        if "idempotency_key" in stmt_str:
            for key, (r, d) in saved_revs.items():
                if key and d is not None:
                    res = MagicMock()
                    res.first.return_value = (r, d)
                    return res
            return _execute_result(scalar=None)
        return _execute_result(scalar=None)

    session.execute.side_effect = _smart_execute

    try:
        with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock), \
             patch("app.modules.documents.intake_service.enqueue_arq_job", new_callable=AsyncMock) as mock_arq:
            mock_arq.return_value = "job_http_1"

            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. First call with Idempotency-Key (HTTP 202 Accepted)
                idemp_key = "idemp-uuid-1111-2222"
                resp1 = await client.post(
                    "/platform/v1alpha1/documents/intake",
                    data={"group_id": group_id},
                    files={"file": ("report.pdf", b"HTTP test content...", "application/pdf")},
                    headers={"Idempotency-Key": idemp_key},
                )
                assert resp1.status_code == 202
                data1 = resp1.json()
                assert data1["status"] == "queued"

                # 2. Retry with SAME key and SAME payload -> idempotent replay (HTTP 202 Accepted)
                resp2 = await client.post(
                    "/platform/v1alpha1/documents/intake",
                    data={"group_id": group_id},
                    files={"file": ("report.pdf", b"HTTP test content...", "application/pdf")},
                    headers={"Idempotency-Key": idemp_key},
                )
                assert resp2.status_code == 202
                data2 = resp2.json()
                assert data2["document_id"] == data1["document_id"]

                # 3. Call with SAME key but DIFFERENT group_id -> 409 IDEMPOTENCY_KEY_REUSED
                resp3 = await client.post(
                    "/platform/v1alpha1/documents/intake",
                    data={"group_id": "different_group_999"},
                    files={"file": ("report.pdf", b"HTTP test content...", "application/pdf")},
                    headers={"Idempotency-Key": idemp_key},
                )
                assert resp3.status_code == 409
                err3 = resp3.json()
                assert err3.get("code") == "IDEMPOTENCY_KEY_REUSED"
    finally:
        app.dependency_overrides.pop(get_current_actor, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_legacy_v1_upload_with_invalid_group_does_not_create_orphan():
    """Requirement 3: Verify legacy /documents/upload when given group_id delegates to intake V2,
    and returns RFC 7807 DOCUMENT_GROUP_NOT_FOUND (404) without creating an orphan document.
    """
    transport = ASGITransport(app=app)
    actor = _make_actor()
    session = _fresh_session()

    async def _override_actor():
        return actor

    async def _override_db():
        yield session

    app.dependency_overrides[get_current_actor] = _override_actor
    app.dependency_overrides[get_db] = _override_db

    # group does not exist
    session.get.return_value = None

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/platform/v1alpha1/documents/upload",
                data={"group_id": "non_existent_group_xyz"},
                files={"file": ("test_orphan.pdf", b"Test orphan content", "application/pdf")},
            )
            assert resp.status_code == 404
            err_data = resp.json()
            assert err_data.get("code") == "DOCUMENT_GROUP_NOT_FOUND"
            # Verify no repository document was added to session
            session.add.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_current_actor, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_concurrent_intake_winner_exists_does_not_delete_storage_object():
    """Requirement 1.1: When concurrent upload loses DB race (IntegrityError) but winner exists,
    storage_service.delete MUST NOT be called because winner depends on the stored artifact.
    """
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_race_safe_storage"
    group = DocumentGroup(
        id=group_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        name="Kho Safe Storage",
        lock_version=1,
    )
    session.get.return_value = group

    file_bytes = b"Safe storage artifact content for race condition test"
    doc_id = "rep_doc_race_winner_safe"
    rev_id = "rev_race_winner_safe"
    doc_obj = _make_doc(doc_id, "safe_race.pdf", file_bytes, current_rev_id=rev_id)
    rev_obj = _make_rev(rev_id, doc_id, "safe_race.pdf", file_bytes, status="ready")
    doc_obj.current_revision = rev_obj

    # 1. Initial check: None
    # 2. Commit raises IntegrityError
    # 3. Recovery query: doc_obj
    # 4. Membership check: None
    session.execute.side_effect = [
        _execute_result(scalar=None),
        _execute_result(scalar=doc_obj),
        _execute_result(scalar=None),
        _execute_result(scalar=None),
    ]
    session.commit.side_effect = [
        IntegrityError("duplicate key", params={}, orig=Exception()),
        None,
    ]

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock), \
         patch("app.modules.documents.intake_service.storage_service.delete", new_callable=AsyncMock) as mock_delete:

        res = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name="safe_race.pdf",
            group_id=group_id,
            actor=actor,
        )

        assert res.document_id == doc_id
        assert res.status == "ready"
        assert res.deduplicated is True
        # Critical assertion: storage_service.delete MUST NOT be called!
        mock_delete.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_intake_integrity_error_no_winner_calls_compensation_delete():
    """Requirement 1.2: When IntegrityError occurs but NO winner document exists (transaction completely failed),
    storage_service.delete MUST be called to clean up the orphaned object.
    """
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_race_no_winner"
    group = DocumentGroup(
        id=group_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        name="Kho No Winner",
        lock_version=1,
    )
    session.get.return_value = group

    file_bytes = b"Artifact for completely failed transaction"

    # 1. Initial check: None
    # 2. Commit raises IntegrityError
    # 3. Recovery query finds NO winner (None)
    session.execute.side_effect = [
        _execute_result(scalar=None),
        _execute_result(scalar=None),
    ]
    session.commit.side_effect = IntegrityError("foreign key or constraint violation", params={}, orig=Exception())

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock), \
         patch("app.modules.documents.intake_service.storage_service.delete", new_callable=AsyncMock) as mock_delete:

        with pytest.raises(IntegrityError):
            await document_intake_service.intake_document(
                db=session,
                file_bytes=file_bytes,
                file_name="no_winner.pdf",
                group_id=group_id,
                actor=actor,
            )

        # Compensation delete MUST be called!
        assert mock_delete.called
        assert "no_winner.pdf" in mock_delete.call_args[0][0]


@pytest.mark.asyncio
async def test_concurrent_intake_corrupted_winner_revision_raises_app_exception():
    """Requirement 1.3: When winner document has no valid revision, intake MUST raise
    AppException with code DOCUMENT_REVISION_INVALID and status 409 (RFC 7807), never return fake status.
    """
    session = _fresh_session()
    actor = _make_actor()

    file_bytes = b"Payload for corrupt winner test"
    doc_id = "rep_doc_corrupt_winner"
    # Winner doc without current_revision
    doc_obj = _make_doc(doc_id, "corrupt.pdf", file_bytes, current_rev_id="rev_missing")
    doc_obj.current_revision = None

    # 1. Initial check: None
    # 2. Commit raises IntegrityError
    # 3. Recovery query: doc_obj
    # 4. db.get / query for revision: None
    session.get.return_value = None
    session.execute.side_effect = [
        _execute_result(scalar=None),
        _execute_result(scalar=doc_obj),
        _execute_result(scalar=None),
    ]
    session.commit.side_effect = IntegrityError("duplicate key", params={}, orig=Exception())

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock):
        with pytest.raises(AppException) as exc_info:
            await document_intake_service.intake_document(
                db=session,
                file_bytes=file_bytes,
                file_name="corrupt.pdf",
                actor=actor,
            )

        assert exc_info.value.code == "DOCUMENT_REVISION_INVALID"
        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_concurrent_intake_winner_membership_not_duplicated():
    """Requirement 1.4: When winner already has membership in group, no duplicate membership is added."""
    session = _fresh_session()
    actor = _make_actor()
    group_id = "grp_membership_exists"
    group = DocumentGroup(
        id=group_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        name="Kho Membership Check",
        lock_version=1,
    )
    session.get.return_value = group

    file_bytes = b"Membership idempotency test payload"
    doc_id = "rep_doc_mem_winner"
    rev_id = "rev_mem_winner"
    doc_obj = _make_doc(doc_id, "mem_test.pdf", file_bytes, current_rev_id=rev_id)
    rev_obj = _make_rev(rev_id, doc_id, "mem_test.pdf", file_bytes, status="ready")
    doc_obj.current_revision = rev_obj

    existing_mem = DocumentGroupMembership(
        group_id=group_id,
        document_id=doc_id,
        added_by=actor.actor_id,
    )

    # 1. Initial check: None
    # 2. Commit raises IntegrityError
    # 3. Recovery query: doc_obj
    # 4. Membership check: existing_mem (already exists!)
    session.execute.side_effect = [
        _execute_result(scalar=None),
        _execute_result(scalar=doc_obj),
        _execute_result(scalar=existing_mem),
        _execute_result(scalar=None),
    ]
    session.commit.side_effect = IntegrityError("duplicate key", params={}, orig=Exception())

    with patch("app.modules.documents.intake_service.storage_service.save", new_callable=AsyncMock):
        res = await document_intake_service.intake_document(
            db=session,
            file_bytes=file_bytes,
            file_name="mem_test.pdf",
            group_id=group_id,
            actor=actor,
        )

        assert res.document_id == doc_id
        assert res.deduplicated is True
        # Verify no duplicate DocumentGroupMembership was added for the winning document
        added_winner_memberships = [
            obj for call_args in session.add.call_args_list
            for obj in call_args[0]
            if isinstance(obj, DocumentGroupMembership) and getattr(obj, "document_id", None) == doc_id
        ]
        assert len(added_winner_memberships) == 0


@pytest.mark.asyncio
async def test_legacy_v1_upload_always_routes_to_intake_v2_with_and_without_group():
    """Requirement 3: Verify /documents/upload always calls document_intake_service.intake_document,
    forwards Idempotency-Key header, and never calls document_repository_service.upload_document.
    """
    transport = ASGITransport(app=app)
    actor = _make_actor()
    session = _fresh_session()

    async def _override_actor():
        return actor

    async def _override_db():
        yield session

    app.dependency_overrides[get_current_actor] = _override_actor
    app.dependency_overrides[get_db] = _override_db

    fake_intake_response = AsyncUploadDocumentResponse(
        document_id="rep_doc_v2_routed",
        revision_id="rev_v2_routed",
        revision_no=1,
        file_name="routed.pdf",
        file_hash="dummy_hash_routed",
        job_id="job_routed_1",
        status="queued",
        deduplicated=False,
        created_at=datetime.now(UTC),
    )

    fake_doc_response = RepositoryDocumentResponse(
        id="rep_doc_v2_routed",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        title="Routed Document",
        file_name="routed.pdf",
        file_type="pdf",
        file_size_bytes=100,
        file_hash="dummy_hash_routed",
        storage_path="documents/routed.pdf",
        status="queued",
        parse_status="pending",
        is_active=True,
        latest_revision_no=1,
        row_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    try:
        with patch.object(document_intake_service, "intake_document", new_callable=AsyncMock) as mock_intake, \
             patch.object(document_repository_service, "get_document", new_callable=AsyncMock) as mock_get_doc, \
             patch.object(document_repository_service, "upload_document", new_callable=AsyncMock) as mock_legacy_upload:

            mock_intake.return_value = fake_intake_response
            mock_get_doc.return_value = fake_doc_response

            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. Test WITHOUT group_id: must route to intake_document
                resp_no_group = await client.post(
                    "/platform/v1alpha1/documents/upload",
                    data={"title": "Doc without group"},
                    files={"file": ("no_group.pdf", b"Content without group", "application/pdf")},
                    headers={"Idempotency-Key": "idemp-no-group-123"},
                )
                assert resp_no_group.status_code == 201
                assert mock_intake.called
                assert mock_intake.call_args.kwargs.get("idempotency_key") == "idemp-no-group-123"
                assert mock_intake.call_args.kwargs.get("group_id") is None
                # Synchronous upload_document MUST NOT be called!
                mock_legacy_upload.assert_not_called()

                # 2. Test WITH group_id: must route to intake_document with group_id
                mock_intake.reset_mock()
                resp_with_group = await client.post(
                    "/platform/v1alpha1/documents/upload",
                    data={"title": "Doc with group", "group_id": "grp_existing_target"},
                    files={"file": ("with_group.pdf", b"Content with group", "application/pdf")},
                    headers={"Idempotency-Key": "idemp-with-group-456"},
                )
                assert resp_with_group.status_code == 201
                assert mock_intake.called
                assert mock_intake.call_args.kwargs.get("idempotency_key") == "idemp-with-group-456"
                assert mock_intake.call_args.kwargs.get("group_id") == "grp_existing_target"
                mock_legacy_upload.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_current_actor, None)
        app.dependency_overrides.pop(get_db, None)


