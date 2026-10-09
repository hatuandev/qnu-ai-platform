"""Unit and Integration Tests for Knowledge Publishing V2 & Staging Index Build (Phase 3)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import AppException
from app.main import app
from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeFact,
    KnowledgeIndexActivation,
    KnowledgeIndexRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import (
    BindingSelectionItem,
    CreateKnowledgeBindingsRequest,
)
from app.modules.knowledge.services.binding_service import binding_service
from app.modules.knowledge.services.index_build_service import index_build_service


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    result.scalar = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_list or [])
    result.scalars = MagicMock(return_value=scalars)
    result.all = MagicMock(return_value=scalars_list or [])
    result.first = MagicMock(return_value=scalar)
    return result


def _fresh_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _make_document_revision(
    rev_id: str,
    document_id: str,
    revision_no: int = 1,
    status: str = "ready",
    canonical_markdown: str = "# Tiêu đề\nNội dung điều 1.",
) -> DocumentRevision:
    return DocumentRevision(
        id=rev_id,
        document_id=document_id,
        revision_no=revision_no,
        status=status,
        source_file_name="test.pdf",
        source_file_type="pdf",
        source_size_bytes=1024,
        source_hash=f"hash_{rev_id}",
        source_storage_path=f"docs/{rev_id}.pdf",
        canonical_markdown=canonical_markdown,
    )


# =========================================================================
# 1. ORM Model Instantiation & Schema Tests
# =========================================================================


def test_models_v2_instantiation_defaults() -> None:
    """Models instantiate with eager Python defaults without database round-trip."""
    # 1. KnowledgeVectorGeneration
    vg = KnowledgeVectorGeneration(
        collection_id="col_test_1",
        embedding_model="bge-m3:latest",
        embedding_dimension=1024,
    )
    assert vg.id.startswith("vg_")
    assert vg.generation_epoch == 1
    assert vg.status == "active"
    assert vg.tenant_id == "tenant_qnu"
    assert vg.workspace_id == "workspace_qnu"
    assert vg.distance_metric == "cosine"

    # 2. KnowledgeBinding
    bnd = KnowledgeBinding(
        collection_id="col_test_1",
        repository_document_id="rep_doc_1",
        source_revision_id="drev_1",
    )
    assert bnd.id.startswith("bnd_")
    assert bnd.active_epoch == 0
    assert bnd.status == "active"
    assert bnd.chunk_strategy == "ClauseBasedChunker"
    assert bnd.sync_policy == "manual"
    assert bnd.tenant_id == "tenant_qnu"
    assert bnd.workspace_id == "workspace_qnu"

    # 3. KnowledgeIndexRevision
    idx_rev = KnowledgeIndexRevision(
        binding_id=bnd.id,
        source_revision_id="drev_1",
        vector_generation_id=vg.id,
        revision_no=1,
    )
    assert idx_rev.id.startswith("idx_rev_")
    assert idx_rev.status == "building"
    assert idx_rev.chunk_count == 0
    assert idx_rev.point_ids == []
    assert idx_rev.parity_report == {}
    assert idx_rev.lock_version == 1

    # 4. KnowledgeIndexActivation
    act = KnowledgeIndexActivation(
        binding_id=bnd.id,
        from_index_revision_id=None,
        to_index_revision_id=idx_rev.id,
        epoch=1,
    )
    assert act.id.startswith("act_")
    assert act.action == "promote"


def test_chunk_and_collection_expansion_fields() -> None:
    """KnowledgeCollection, KnowledgeChunk, KnowledgeFact include new V2 fields."""
    col = KnowledgeCollection(name="QNU Regulations", module_code="regulations")
    assert getattr(col, "index_epoch", None) == 1
    assert getattr(col, "tenant_id", None) == "tenant_qnu"

    chunk = KnowledgeChunk(
        document_id="doc_1",
        collection_id="col_1",
        chunk_index=0,
        content="Nội dung điều 1",
        binding_id="bnd_123",
        index_revision_id="idx_rev_456",
    )
    assert chunk.binding_id == "bnd_123"
    assert chunk.index_revision_id == "idx_rev_456"

    fact = KnowledgeFact(
        collection_id="col_1",
        document_id="doc_1",
        entity_name="Ngành CNTT",
        entity_type="major",
        attribute_name="điểm chuẩn",
        attribute_value="24.5",
        binding_id="bnd_123",
        index_revision_id="idx_rev_456",
    )
    assert fact.binding_id == "bnd_123"
    assert fact.index_revision_id == "idx_rev_456"


# =========================================================================
# 2. Binding Service Unit Tests
# =========================================================================


@pytest.mark.asyncio
async def test_get_available_documents_success() -> None:
    """Query available repository documents with binding status."""
    db = _fresh_session()
    col = KnowledgeCollection(id="col_test", name="Tuyển sinh", module_code="admissions")
    db.get = AsyncMock(return_value=col)

    rep_doc = RepositoryDocument(
        id="rep_doc_1",
        title="Quy chế tuyển sinh 2026",
        file_name="tuyensinh.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        file_hash="hash_123",
        storage_path="docs/tuyensinh.pdf",
        document_number="123/QĐ-ĐHQN",
        current_revision_id="drev_1",
        latest_revision_no=1,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=1),  # count
            _execute_result(scalars_list=[(rep_doc, None)]),  # rows: (rep_doc, bound_id)
        ]
    )

    resp = await binding_service.get_available_documents(db, "col_test", search="tuyển sinh")
    assert resp.total == 1
    assert len(resp.items) == 1
    item = resp.items[0]
    assert item.id == "rep_doc_1"
    assert item.is_bound is False
    assert item.bound_binding_id is None
    assert item.document_code == "123/QĐ-ĐHQN"


@pytest.mark.asyncio
async def test_create_bindings_success() -> None:
    """Create new knowledge binding with valid repository document and ready revision."""
    db = _fresh_session()
    col = KnowledgeCollection(id="col_test", name="Đào tạo", module_code="training")
    rep_doc = RepositoryDocument(
        id="rep_doc_1",
        title="Quy chế đào tạo",
        file_name="daotao.pdf",
        file_type="pdf",
        file_size_bytes=2048,
        file_hash="hash_abc",
        storage_path="docs/daotao.pdf",
        current_revision_id="drev_1",
        status="active",
    )
    rev = _make_document_revision("drev_1", "rep_doc_1", status="ready")

    db.get = AsyncMock(
        side_effect=lambda model, ident: {
            "col_test": col,
            "rep_doc_1": rep_doc,
            "drev_1": rev,
        }.get(ident)
    )
    # No existing binding
    db.execute = AsyncMock(return_value=_execute_result(scalar=None))

    req = CreateKnowledgeBindingsRequest(
        items=[
            BindingSelectionItem(
                repository_document_id="rep_doc_1",
                target_revision_id="drev_1",
                chunk_strategy="ClauseBasedChunker",
            )
        ]
    )

    res = await binding_service.create_bindings(db, "col_test", req)
    assert res.created_count == 1
    assert res.skipped_count == 0
    assert res.failed_count == 0
    assert len(res.bindings) == 1
    assert res.bindings[0].status == "created"
    assert res.bindings[0].repository_document_id == "rep_doc_1"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_bindings_already_bound_skips() -> None:
    """Skip creation if binding already exists in collection."""
    db = _fresh_session()
    col = KnowledgeCollection(id="col_test", name="Đào tạo", module_code="training")
    db.get = AsyncMock(return_value=col)

    existing = KnowledgeBinding(
        id="bnd_existing",
        collection_id="col_test",
        repository_document_id="rep_doc_1",
        source_revision_id="drev_1",
        status="active",
    )
    db.execute = AsyncMock(return_value=_execute_result(scalar=existing))

    req = CreateKnowledgeBindingsRequest(
        items=[BindingSelectionItem(repository_document_id="rep_doc_1")]
    )
    res = await binding_service.create_bindings(db, "col_test", req)
    assert res.created_count == 0
    assert res.skipped_count == 1
    assert res.bindings[0].status == "already_bound"


@pytest.mark.asyncio
async def test_create_bindings_missing_revision_fails() -> None:
    """Fail item when document has no current_revision_id and none specified."""
    db = _fresh_session()
    col = KnowledgeCollection(id="col_test", name="Đào tạo", module_code="training")
    rep_doc = RepositoryDocument(
        id="rep_doc_1",
        title="Văn bản chưa bóc tách",
        file_name="draft.docx",
        file_type="docx",
        file_size_bytes=512,
        file_hash="hash_draft",
        storage_path="docs/draft.docx",
        current_revision_id=None,
    )
    db.get = AsyncMock(
        side_effect=lambda model, ident: col if ident == "col_test" else rep_doc
    )
    db.execute = AsyncMock(return_value=_execute_result(scalar=None))

    req = CreateKnowledgeBindingsRequest(
        items=[BindingSelectionItem(repository_document_id="rep_doc_1")]
    )
    res = await binding_service.create_bindings(db, "col_test", req)
    assert res.failed_count == 1
    assert res.bindings[0].status == "failed"


# =========================================================================
# 3. Index Build Service & Parity Gate Tests
# =========================================================================


@pytest.mark.asyncio
async def test_build_staging_index_success() -> None:
    """Build staging index, chunks, vector points and pass Parity Gate."""
    db = _fresh_session()
    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id="col_1",
        repository_document_id="rep_doc_1",
        source_revision_id="drev_1",
        chunk_strategy="ClauseBasedChunker",
    )
    col = KnowledgeCollection(
        id="col_1",
        name="Kho Quy chế",
        module_code="regulations",
        index_epoch=1,
    )
    rep_doc = RepositoryDocument(
        id="rep_doc_1",
        title="Quy chế Đào tạo",
        file_name="daotao.pdf",
        file_type="pdf",
        file_size_bytes=4096,
        file_hash="hash_rep_1",
        storage_path="docs/daotao.pdf",
    )
    source_rev = _make_document_revision(
        "drev_1",
        "rep_doc_1",
        status="ready",
        canonical_markdown="""# QUY CHẾ ĐÀO TẠO
Điều 1. Phạm vi áp dụng
Quy định này áp dụng cho toàn thể sinh viên Trường Đại học Quy Nhơn.
Điều 2. Thời gian học tập
Thời gian chuẩn thiết kế đào tạo là 4 năm học.
""",
    )

    db.get = AsyncMock(
        side_effect=lambda model, ident: {
            "bnd_1": binding,
            "col_1": col,
            "rep_doc_1": rep_doc,
            "drev_1": source_rev,
        }.get(ident)
    )

    # 1st execute: binding_stmt with_for_update
    # 2nd execute: max rev_no (0)
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=binding),
            _execute_result(scalar=0),
        ]
    )

    vector_gen = KnowledgeVectorGeneration(
        id="vg_1",
        collection_id=col.id,
        embedding_model="configured-model",
        provider_id="provider_1",
        qdrant_collection_name="knowledge_col_1",
        config_hash="a" * 64,
        embedding_dimension=1024,
    )
    kdoc = MagicMock(id="kdoc_1")
    with (
        patch.object(
            index_build_service,
            "get_or_create_vector_generation",
            AsyncMock(return_value=vector_gen),
        ),
        patch.object(
            index_build_service,
            "_ensure_collection_doc_projection",
            AsyncMock(return_value=kdoc),
        ),
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.index_chunks",
            AsyncMock(side_effect=lambda collection_id, chunks, **kwargs: len(chunks)),
        ),
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.verify_index_revision_parity",
            AsyncMock(side_effect=lambda collection_id, index_revision_id, expected_points: (
                True,
                "verified",
                len(expected_points),
            )),
        ),
    ):
        idx_rev = await index_build_service.build_staging_index(
            db=db,
            binding_id="bnd_1",
            chunk_strategy="ClauseBasedChunker",
            auto_activate=False,
        )

    assert idx_rev.status == "ready"
    assert idx_rev.chunk_count > 0
    assert len(idx_rev.point_ids) == idx_rev.chunk_count
    assert idx_rev.parity_report.get("parity_status") == "passed"
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_build_staging_index_empty_text_fails() -> None:
    """Staging index build fails gracefully with EMPTY_EXTRACTED_TEXT when revision text is empty."""
    db = _fresh_session()
    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id="col_1",
        repository_document_id="rep_doc_1",
        source_revision_id="drev_1",
    )
    col = KnowledgeCollection(id="col_1", name="Kho Test", module_code="test")
    rep_doc = RepositoryDocument(
        id="rep_doc_1",
        title="Empty Doc",
        file_name="empty.pdf",
        file_type="pdf",
        file_size_bytes=100,
        file_hash="hash_empty",
        storage_path="docs/empty.pdf",
    )
    source_rev = _make_document_revision(
        "drev_1",
        "rep_doc_1",
        status="ready",
        canonical_markdown="",
    )

    db.get = AsyncMock(
        side_effect=lambda model, ident: {
            "bnd_1": binding,
            "col_1": col,
            "rep_doc_1": rep_doc,
            "drev_1": source_rev,
        }.get(ident)
    )
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=binding),
            _execute_result(scalar=0),
        ]
    )

    vector_gen = KnowledgeVectorGeneration(
        id="vg_1",
        collection_id=col.id,
        embedding_model="configured-model",
        provider_id="provider_1",
        qdrant_collection_name="knowledge_col_1",
        config_hash="b" * 64,
        embedding_dimension=1024,
    )
    with patch.object(
        index_build_service,
        "get_or_create_vector_generation",
        AsyncMock(return_value=vector_gen),
    ):
        idx_rev = await index_build_service.build_staging_index(db, "bnd_1")
    assert idx_rev.status == "failed"
    assert idx_rev.failure_code == "EMPTY_EXTRACTED_TEXT"


@pytest.mark.asyncio
async def test_promote_index_revision_atomic_pointer_swap() -> None:
    """Promote ready revision, bump epoch, update pointer, and record audit log."""
    db = _fresh_session()
    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id="col_1",
        repository_document_id="rep_doc_1",
        source_revision_id="drev_1",
        active_index_revision_id="idx_rev_old",
        active_epoch=1,
    )
    target_rev = KnowledgeIndexRevision(
        id="idx_rev_new",
        binding_id="bnd_1",
        source_revision_id="drev_2",
        vector_generation_id="vg_1",
        revision_no=2,
        status="ready",
        chunk_count=2,
    )
    old_rev = KnowledgeIndexRevision(
        id="idx_rev_old",
        binding_id="bnd_1",
        source_revision_id="drev_1",
        vector_generation_id="vg_1",
        revision_no=1,
        status="active",
    )

    db.get = AsyncMock(
        side_effect=lambda model, ident: {
            "bnd_1": binding,
            "idx_rev_new": target_rev,
            "idx_rev_old": old_rev,
            "col_1": KnowledgeCollection(id="col_1", name="Test", module_code="test"),
        }.get(ident)
    )
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=binding),
            _execute_result(scalar=1),
        ]
    )

    with (
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.activate_index_revision",
            AsyncMock(return_value=2),
        ),
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.deactivate_index_revision",
            AsyncMock(return_value=None),
        ),
    ):
        act = await index_build_service.promote_index_revision(
            db=db,
            binding_id="bnd_1",
            index_revision_id="idx_rev_new",
            expected_epoch=1,
            reason="Thử nghiệm promote V2",
            activated_by="user_admin",
        )

    assert binding.active_index_revision_id == "idx_rev_new"
    assert binding.active_epoch == 2
    assert target_rev.status == "active"
    assert old_rev.status == "archived"
    assert act.action == "promote"
    assert act.epoch == 2
    assert act.from_index_revision_id == "idx_rev_old"
    assert act.to_index_revision_id == "idx_rev_new"
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_promote_index_revision_invalid_status_rejects() -> None:
    """Reject promotion when target revision is in 'failed' or 'archived' status."""
    db = _fresh_session()
    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id="col_1",
        repository_document_id="rep_doc_1",
        source_revision_id="drev_1",
    )
    target_rev = KnowledgeIndexRevision(
        id="idx_rev_bad",
        binding_id="bnd_1",
        source_revision_id="drev_1",
        vector_generation_id="vg_1",
        revision_no=1,
        status="failed",
    )
    db.get = AsyncMock(
        side_effect=lambda model, ident: binding if ident == "bnd_1" else target_rev
    )
    db.execute = AsyncMock(return_value=_execute_result(scalar=binding))

    with pytest.raises(AppException) as exc_info:
        await index_build_service.promote_index_revision(
            db, "bnd_1", "idx_rev_bad", expected_epoch=0
        )
    assert exc_info.value.code == "INVALID_REVISION_STATUS"


# =========================================================================
# 4. HTTP API Router Endpoints Tests
# =========================================================================


@pytest.mark.asyncio
async def test_api_get_available_documents() -> None:
    """GET /platform/v1alpha1/knowledge/collections/{id}/available-documents returns 200."""
    db = _fresh_session()
    col = KnowledgeCollection(id="col_test", name="Quy chế", module_code="regulations")
    db.get = AsyncMock(return_value=col)
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=col),
            _execute_result(scalar=0),
            _execute_result(scalars_list=[]),
        ]
    )

    app.dependency_overrides[get_db] = lambda: db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(
                "/platform/v1alpha1/knowledge/collections/col_test/available-documents"
            )
            assert res.status_code == 200
            data = res.json()
            assert "items" in data
            assert data["total"] == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_create_bindings_endpoint() -> None:
    """POST /platform/v1alpha1/knowledge/collections/{id}/bindings returns 201."""
    db = _fresh_session()
    col = KnowledgeCollection(id="col_test", name="Quy chế", module_code="regulations")
    rep_doc = RepositoryDocument(
        id="rep_doc_1",
        title="Tài liệu mẫu",
        file_name="sample.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        file_hash="hash_s",
        storage_path="docs/sample.pdf",
        current_revision_id="drev_1",
        status="active",
    )
    rev = _make_document_revision("drev_1", "rep_doc_1", status="ready")

    db.get = AsyncMock(
        side_effect=lambda model, ident: {
            "col_test": col,
            "rep_doc_1": rep_doc,
            "drev_1": rev,
        }.get(ident)
    )
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=col),
            _execute_result(scalar=None),
        ]
    )

    app.dependency_overrides[get_db] = lambda: db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/platform/v1alpha1/knowledge/collections/col_test/bindings",
                json={
                    "items": [
                        {
                            "repository_document_id": "rep_doc_1",
                            "target_revision_id": "drev_1",
                        }
                    ]
                },
            )
            assert res.status_code == 201
            data = res.json()
            assert data["created_count"] == 1
            assert len(data["bindings"]) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_binding_chunks_service_and_api() -> None:
    """GET /platform/v1alpha1/knowledge/bindings/{id}/chunks returns paginated chunks list."""
    db = _fresh_session()
    bnd = KnowledgeBinding(
        id="bnd_chk_test",
        collection_id="col_test",
        repository_document_id="rep_doc_1",
        source_revision_id="drev_1",
        active_index_revision_id="idx_rev_1",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    idx_rev = KnowledgeIndexRevision(
        id="idx_rev_1",
        binding_id=bnd.id,
        source_revision_id=bnd.source_revision_id,
        vector_generation_id="vg_1",
        revision_no=1,
        status="active",
    )
    chk_1 = KnowledgeChunk(
        id="chk_1",
        document_id="doc_1",
        collection_id="col_test",
        binding_id="bnd_chk_test",
        index_revision_id="idx_rev_1",
        chunk_index=0,
        content="Nội dung điều 1 quy chế học vụ.",
        chunk_hash="h1",
        token_count=10,
        section="Điều 1",
        page_number=1,
    )
    chk_2 = KnowledgeChunk(
        id="chk_2",
        document_id="doc_1",
        collection_id="col_test",
        binding_id="bnd_chk_test",
        index_revision_id="idx_rev_1",
        chunk_index=1,
        content="Nội dung điều 2 cảnh báo học vụ.",
        chunk_hash="h2",
        token_count=12,
        section="Điều 2",
        page_number=1,
    )

    db.get = AsyncMock(
        side_effect=lambda model, ident: {
            (KnowledgeBinding, bnd.id): bnd,
            (KnowledgeIndexRevision, idx_rev.id): idx_rev,
        }.get((model, ident))
    )

    count_result = MagicMock()
    count_result.scalar = MagicMock(return_value=2)

    items_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[chk_1, chk_2])
    items_result.scalars = MagicMock(return_value=scalars_mock)

    db.execute = AsyncMock(side_effect=[count_result, items_result, count_result, items_result])

    # 1. Test Service directly
    res_svc = await binding_service.list_binding_chunks(db, binding_id="bnd_chk_test")
    assert res_svc.total == 2
    assert len(res_svc.items) == 2
    assert res_svc.items[0].content == "Nội dung điều 1 quy chế học vụ."
    assert res_svc.index_revision_id == "idx_rev_1"

    # 2. Test API endpoint
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=bnd),
            _execute_result(scalar=idx_rev),
            count_result,
            items_result,
        ]
    )
    app.dependency_overrides[get_db] = lambda: db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/platform/v1alpha1/knowledge/bindings/bnd_chk_test/chunks")
            assert res.status_code == 200
            data = res.json()
            assert data["binding_id"] == "bnd_chk_test"
            assert data["total"] == 2
            assert len(data["items"]) == 2
            assert data["items"][0]["section"] == "Điều 1"
    finally:
        app.dependency_overrides.clear()
