"""Unit Tests for Central Document Repository and Knowledge Ingestion Linking."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.storage import storage_service
from app.main import app
from app.modules.documents.models import RepositoryDocument
from app.modules.documents.schemas import (
    AttachedCollectionInfo,
    RepositoryDocumentListItem,
    RepositoryDocumentResponse,
    RepositoryDocumentStatsResponse,
    RepositoryDocumentUpdate,
)
from app.modules.documents.service import document_repository_service
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.knowledge.services.ingestion_service import IngestionService


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    result.scalar = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_list or [])
    result.scalars = MagicMock(return_value=scalars)
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


@pytest.mark.asyncio
async def test_document_repository_upload_and_storage_lifecycle() -> None:
    """Test upload, storage key creation and markdown extraction."""
    content = b"# Quy che dao tao dai hoc QNU\n\nDieu 1. Pham vi ap dung cho tat ca sinh vien."
    filename = "quy_che_dao_tao_2026.md"

    session = _fresh_session()
    # Mock no existing doc with the same hash
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    doc = await document_repository_service.upload_document(
        db=session,
        file_bytes=content,
        file_name=filename,
        title="Quy chế đào tạo đại học chính quy 2026",
        document_number="1234/QD-DHQN",
        issuing_authority="Trường Đại học Quy Nhơn",
        issued_date=date(2026, 1, 15),
        auto_parse=True,
    )

    assert doc.id.startswith("rep_doc_")
    assert doc.file_name == filename
    assert doc.parse_status == "parsed"
    assert doc.parsed_markdown is not None
    assert "Quy che dao tao" in doc.parsed_markdown
    assert session.add.called
    assert session.commit.called
    assert await storage_service.exists(doc.storage_path)


@pytest.mark.asyncio
async def test_document_repository_deduplication() -> None:
    """Test that uploading identical content returns existing document without duplicate storage."""
    content = b"Van ban quy che thi tuyen sinh nam 2026 tai Dai hoc Quy Nhon."
    existing_doc = RepositoryDocument(
        id="rep_doc_existing_123",
        title="Existing Document",
        file_name="existing.txt",
        file_size_bytes=len(content),
        file_type="txt",
        file_hash="dummy_hash",
        storage_path="documents/originals/dummy_hash/existing.txt",
        parse_status="parsed",
        parsed_markdown=content.decode("utf-8"),
    )

    session = _fresh_session()
    # Mock existing doc found by hash
    session.execute = AsyncMock(return_value=_execute_result(scalar=existing_doc))

    doc = await document_repository_service.upload_document(
        db=session,
        file_bytes=content,
        file_name="another_upload.txt",
        auto_parse=True,
    )

    assert doc.id == existing_doc.id
    assert not session.add.called  # Did not insert duplicate record


@pytest.mark.asyncio
async def test_document_repository_update_and_stats() -> None:
    """Test updating administrative metadata and computing aggregated stats."""
    existing_doc = RepositoryDocument(
        id="rep_doc_target",
        title="Cũ",
        file_name="target.txt",
        file_size_bytes=1024,
        file_type="txt",
        file_hash="dummy_hash",
        storage_path="documents/originals/dummy/target.txt",
        parse_status="parsed",
    )

    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=existing_doc))

    # Update document
    updated = await document_repository_service.update_document(
        db=session,
        doc_id="rep_doc_target",
        body=RepositoryDocumentUpdate(
            title="Quy chế sửa đổi mới 2026",
            issuing_authority="Ban Giám Hiệu QNU",
        ),
    )
    assert updated.title == "Quy chế sửa đổi mới 2026"
    assert updated.issuing_authority == "Ban Giám Hiệu QNU"
    assert session.commit.called

    # Get stats
    call_count = 0

    async def mock_stats_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock_res = MagicMock()
        if call_count == 1:
            mock_res.one = MagicMock(return_value=(10, 8, 1, 1, 50000, 3))
        else:
            mock_res.scalar_one = MagicMock(return_value=5)
        return mock_res

    session.execute = AsyncMock(side_effect=mock_stats_execute)
    stats = await document_repository_service.get_stats(db=session)
    assert stats.total_documents == 10
    assert stats.parsed_documents == 8
    assert stats.pending_documents == 1
    assert stats.failed_documents == 1
    assert stats.total_size_bytes == 50000
    assert stats.document_types_count == 3
    assert stats.attached_usages_count == 5


@pytest.mark.asyncio
async def test_attach_repository_document_to_collection() -> None:
    """Test attaching parsed repository document directly into Knowledge Collection without re-OCR."""
    repo_doc = RepositoryDocument(
        id="rep_doc_source_777",
        title="Sổ tay sinh viên 2026",
        file_name="so_tay_sinh_vien.md",
        file_size_bytes=2048,
        file_type="md",
        file_hash="hash_777",
        storage_path="documents/originals/hash_777/so_tay_sinh_vien.md",
        parse_status="parsed",
        parsed_markdown="# So tay sinh vien QNU\n\nNoi dung huong dan hoc vu cho sinh vien khoa 47.",
    )

    collection = KnowledgeCollection(
        id="col_student_guide",
        name="Kho Sổ Tay Học Vụ",
        module_code="regulations",
        collection_metadata={"chunking_strategy": "SemanticChunker"},
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )

    session = _fresh_session()

    async def mock_exec(stmt):
        s_str = str(stmt)
        if "knowledge_collections" in s_str:
            return _execute_result(scalar=collection)
        if "repository_documents" in s_str:
            return _execute_result(scalars_list=[repo_doc])
        if "knowledge_documents" in s_str:
            return _execute_result(scalar=None)
        return _execute_result()

    session.execute = AsyncMock(side_effect=mock_exec)

    ingestion = IngestionService()
    created = await ingestion.attach_repository_documents(
        db=session,
        collection_id=collection.id,
        document_ids=[repo_doc.id],
        auto_approve=False,
    )

    assert len(created) == 1
    kdoc = created[0]
    assert kdoc.collection_id == collection.id
    assert kdoc.repository_document_id == repo_doc.id
    assert kdoc.title == repo_doc.title
    assert kdoc.doc_metadata.get("chunk_count", 0) > 0
    assert session.commit.called


@pytest.mark.asyncio
async def test_document_repository_api_endpoints() -> None:
    """Test API router endpoints with mocked service responses."""
    fake_list_item = RepositoryDocumentListItem(
        id="rep_doc_1",
        title="Hướng dẫn học vụ",
        file_name="huong_dan.pdf",
        file_type="pdf",
        file_size_bytes=10240,
        file_hash="hash_1",
        parse_status="parsed",
        attached_collections_count=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    fake_detail = RepositoryDocumentResponse(
        id="rep_doc_1",
        title="Hướng dẫn học vụ",
        file_name="huong_dan.pdf",
        file_type="pdf",
        file_size_bytes=10240,
        file_hash="hash_1",
        storage_path="documents/originals/hash_1/huong_dan.pdf",
        parse_status="parsed",
        parsed_markdown="# Hướng dẫn",
        doc_metadata={},
        attached_collections_count=1,
        attached_collections=[
            AttachedCollectionInfo(
                collection_id="col_1",
                collection_name="Kho Quy Chế",
                document_id="doc_k_1",
                index_status="indexed",
                created_at=datetime.now(UTC),
            )
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    fake_stats = RepositoryDocumentStatsResponse(
        total_documents=10,
        parsed_documents=9,
        pending_documents=0,
        failed_documents=1,
        total_size_bytes=1048576,
        document_types_count=4,
        attached_usages_count=4,
    )

    async def override_get_db():
        yield _fresh_session()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with (
            patch.object(
                document_repository_service,
                "list_documents",
                new=AsyncMock(return_value=([fake_list_item], 1)),
            ),
            patch.object(
                document_repository_service,
                "get_document",
                new=AsyncMock(return_value=fake_detail),
            ),
            patch.object(
                document_repository_service,
                "get_stats",
                new=AsyncMock(return_value=fake_stats),
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # 1. GET /documents
                res1 = await client.get("/platform/v1alpha1/documents")
                assert res1.status_code == 200
                data1 = res1.json()
                assert data1["total"] == 1
                assert data1["items"][0]["id"] == "rep_doc_1"

                # 2. GET /documents/{id}
                res2 = await client.get("/platform/v1alpha1/documents/rep_doc_1")
                assert res2.status_code == 200
                data2 = res2.json()
                assert data2["id"] == "rep_doc_1"
                assert data2["attached_collections_count"] == 1

                # 3. GET /documents/stats
                res3 = await client.get("/platform/v1alpha1/documents/stats")
                assert res3.status_code == 200
                data3 = res3.json()
                assert data3["total_documents"] == 10
                assert data3["parsed_documents"] == 9
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_document_repository_auto_detect_nd30_metadata() -> None:
    """Test Decree 30 administrative metadata auto-detection when user provides no metadata."""
    sample_legal_text = (
        "BỘ GIÁO DỤC VÀ ĐÀO TẠO\n"
        "TRƯỜNG ĐẠI HỌC QUY NHƠN\n"
        "Số: 2139/QĐ-ĐHQN\n\n"
        "Quy Nhơn, ngày 15 tháng 8 năm 2025\n\n"
        "QUYẾT ĐỊNH\n"
        "V/v: Ban hành quy chế tổ chức đào tạo đại học năm học 2025 - 2026\n\n"
        "Điều 1. Ban hành kèm theo Quyết định này Quy chế đào tạo đại học...\n\n"
        "Nơi nhận:\n"
        "- Ban Giám hiệu;\n"
        "- Lưu: VT, ĐT.\n\n"
        "HIỆU TRƯỞNG\n"
        "Đỗ Ngọc Mỹ"
    ).encode()

    filename = "quyet_dinh_2139.txt"
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    doc = await document_repository_service.upload_document(
        db=session,
        file_bytes=sample_legal_text,
        file_name=filename,
        # Intentionally passing NO metadata to test auto-detection:
        title=None,
        document_number=None,
        issuing_authority=None,
        issued_date=None,
        document_type_code=None,
        auto_parse=True,
    )

    assert doc.document_number == "2139/QĐ-ĐHQN"
    assert doc.issued_date == date(2025, 8, 15)
    assert doc.document_type_code == "quyet_dinh"
    assert doc.title == "Ban hành quy chế tổ chức đào tạo đại học năm học 2025 - 2026"
    assert doc.issuing_authority == "Trường Đại học Quy Nhơn"
    assert doc.parse_status == "parsed"
