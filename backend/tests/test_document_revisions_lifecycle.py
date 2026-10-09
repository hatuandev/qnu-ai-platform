"""Comprehensive Unit Tests for Document Revisions Lifecycle, Quality Gate & Async Intake (Phase 2)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.storage import storage_service
from app.main import app
from app.modules.documents.intake_service import document_intake_service
from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.documents.quality_gate import evaluate_revision_quality
from app.modules.documents.revision_service import document_revision_service
from app.modules.documents.schemas import (
    ReviewRevisionContentRequest,
    SubmitRevisionReviewRequest,
)


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


# =========================================================================
# 1. Quality Gate Evaluation Tests
# =========================================================================


def test_quality_gate_clean_markdown_passed() -> None:
    """Standard well-formed markdown with table passes quality audit."""
    content = """# QUY CHẾ ĐÀO TẠO ĐẠI HỌC
Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng
Quy chế này quy định về đào tạo trình độ đại học tại Trường Đại học Quy Nhơn.

| Mã học phần | Tên học phần | Số tín chỉ |
|---|---|---|
| CNTT101 | Nhập môn lập trình | 3 |
| TOAN102 | Giải tích đại cương | 4 |
"""
    report = evaluate_revision_quality(
        markdown=content,
        page_count=1,
        tables_count=1,
        file_size_bytes=len(content.encode("utf-8")),
    )
    assert report["overall_status"] == "passed"
    assert report["total_chars"] > 150
    assert report["markdown_tables_count"] >= 1
    assert "mojibake_or_font_corruption_detected" not in report["warning_flags"]


def test_quality_gate_empty_content_failed() -> None:
    """Empty extracted markdown triggers critical failure."""
    report = evaluate_revision_quality(markdown="", page_count=2)
    assert report["overall_status"] == "failed"
    assert report["failure_code"] == "EMPTY_EXTRACTED_CONTENT"
    assert "empty_content" in report["warning_flags"]


def test_quality_gate_low_density_and_mojibake_warning() -> None:
    """Corrupt font and severely low character density triggers warning."""
    content = "Trang 1: \ufffd\ufffd\ufffd ??? unreadable scan text"
    report = evaluate_revision_quality(
        markdown=content,
        page_count=3,
        tables_count=0,
    )
    assert report["overall_status"] == "warning"
    assert "critically_low_text_density" in report["warning_flags"]
    assert "mojibake_or_font_corruption_detected" in report["warning_flags"]


# =========================================================================
# 2. Intake Service Async Ingestion & Deduplication Tests
# =========================================================================


@pytest.mark.asyncio
async def test_intake_service_upload_new_document() -> None:
    """Test async intake endpoint returns 202 payload with queued job."""
    content = b"Van ban quy che 2026 moi tiep nhan vao kho tai lieu."
    filename = "quy_che_moi_2026.txt"

    session = _fresh_session()
    # Mock no existing doc
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with patch.object(storage_service, "save", new_callable=AsyncMock) as mock_save:
        res = await document_intake_service.intake_document(
            db=session,
            file_bytes=content,
            file_name=filename,
            title="Quy chế mới 2026",
            document_number="999/QD-DHQN",
            issuing_authority="Trường Đại học Quy Nhơn",
            issued_date=date(2026, 3, 1),
        )

        assert res.document_id.startswith("rep_doc_")
        assert res.revision_id.startswith("rev_")
        assert res.revision_no == 1
        assert res.status == "queued"
        assert res.deduplicated is False
        assert mock_save.called
        assert session.add.called
        assert session.commit.called


@pytest.mark.asyncio
async def test_intake_service_deduplication() -> None:
    """Test duplicate file intake returns existing document and revision immediately."""
    content = b"Noi dung trung lap da co san trong he thong."
    existing_doc = RepositoryDocument(
        id="rep_doc_existing_99",
        title="Tài liệu có sẵn",
        file_name="existing.txt",
        file_type="txt",
        file_size_bytes=len(content),
        file_hash="dummy_hash_existing",
        storage_path="documents/originals/dummy_hash_existing/existing.txt",
        current_revision_id="rev_existing_99",
        latest_revision_no=1,
        parse_status="parsed",
        is_active=True,
    )

    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=existing_doc))

    res = await document_intake_service.intake_document(
        db=session,
        file_bytes=content,
        file_name="another_name.txt",
    )

    assert res.document_id == "rep_doc_existing_99"
    assert res.revision_id == "rev_existing_99"
    assert res.deduplicated is True
    assert res.status == "parsed"


# =========================================================================
# 3. Revision Review, Edit & Approval Lifecycle Tests
# =========================================================================


@pytest.mark.asyncio
async def test_revision_content_review_and_approval_flow() -> None:
    """Test editing markdown and promoting revision to ready status."""
    doc = RepositoryDocument(
        id="rep_doc_review_test",
        title="Van ban can hieu dinh",
        file_name="van_ban.pdf",
        file_type="pdf",
        file_size_bytes=1000,
        file_hash="hash_doc_test",
        storage_path="path/test.pdf",
        current_revision_id="rev_old",
        latest_revision_no=2,
    )

    rev = DocumentRevision(
        id="rev_review_test",
        document_id=doc.id,
        revision_no=2,
        source_file_name="van_ban.pdf",
        source_file_type="pdf",
        source_size_bytes=1000,
        source_hash="hash_doc_test",
        source_storage_path="path/test.pdf",
        canonical_markdown="# Tieu de chua chuan",
        status="review_required",
        lock_version=1,
    )

    session = _fresh_session()
    # Mock finding document and revision
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=doc),     # 1. check doc in update_revision_content
            _execute_result(scalar=rev),     # 2. find rev in update_revision_content
            _execute_result(scalar=doc),     # 3. check doc in submit_revision_review
            _execute_result(scalar=rev),     # 4. find rev in submit_revision_review
        ]
    )

    # 1. Human reviewer updates content
    reviewed_res = await document_revision_service.update_revision_content(
        db=session,
        document_id=doc.id,
        revision_id=rev.id,
        body=ReviewRevisionContentRequest(
            canonical_markdown="# TIÊU ĐỀ ĐÃ HIỆU ĐÍNH CHUẨN XÁC\n\nNội dung đầy đủ.",
            notes="Đã chỉnh sửa tiêu đề và căn lề.",
            expected_lock_version=1,
        ),
    )
    assert "ĐÃ HIỆU ĐÍNH" in reviewed_res.canonical_markdown
    assert rev.lock_version == 2
    assert len(rev.parse_provenance.get("human_reviews", [])) == 1

    # 2. Human reviewer approves revision
    approved_res = await document_revision_service.submit_revision_review(
        db=session,
        document_id=doc.id,
        revision_id=rev.id,
        body=SubmitRevisionReviewRequest(
            action="approve",
            notes="Phê duyệt ban hành.",
            expected_lock_version=2,
        ),
    )
    assert approved_res.status == "ready"
    assert doc.current_revision_id == rev.id
    assert doc.parsed_markdown == rev.canonical_markdown


# =========================================================================
# 4. API Router Integration Tests
# =========================================================================


@pytest.mark.asyncio
async def test_api_intake_and_revisions_routes() -> None:
    """Test HTTP API router endpoints for Intake and Revisions."""
    now = datetime.now(UTC)
    doc = RepositoryDocument(
        id="rep_doc_router_test",
        title="Router Test Document",
        file_name="test.pdf",
        file_type="pdf",
        file_size_bytes=500,
        file_hash="hash_router_test",
        storage_path="storage/test.pdf",
        parse_status="parsed",
        is_active=True,
    )
    rev = DocumentRevision(
        id="rev_router_test",
        document_id=doc.id,
        revision_no=1,
        source_file_name="test.pdf",
        source_file_type="pdf",
        source_size_bytes=500,
        source_hash="hash_router_test",
        source_storage_path="storage/test.pdf",
        canonical_markdown="# Test Markdown Content",
        status="ready",
        lock_version=1,
        created_at=now,
        updated_at=now,
    )

    mock_db = _fresh_session()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 1: POST /documents/intake (202 Accepted)
        mock_db.execute = AsyncMock(return_value=_execute_result(scalar=None))
        with patch.object(storage_service, "save", new_callable=AsyncMock):
            intake_res = await client.post(
                "/platform/v1alpha1/documents/intake",
                files={"file": ("van_ban.pdf", b"Dummy PDF bytes", "application/pdf")},
                data={"title": "Văn bản thử nghiệm"},
            )
            assert intake_res.status_code == 202
            data = intake_res.json()
            assert "job_id" in data
            assert data["status"] == "queued"

        # Test 2: GET /documents/{id}/revisions
        mock_db.execute = AsyncMock(
            side_effect=[
                _execute_result(scalar=doc),
                _execute_result(scalars_list=[rev]),
            ]
        )
        revs_res = await client.get(f"/platform/v1alpha1/documents/{doc.id}/revisions")
        assert revs_res.status_code == 200
        assert len(revs_res.json()) == 1

        # Test 3: GET /documents/{id}/revisions/{rev_id}
        mock_db.execute = AsyncMock(
            side_effect=[
                _execute_result(scalar=doc),
                _execute_result(scalar=rev),
            ]
        )
        rev_detail_res = await client.get(f"/platform/v1alpha1/documents/{doc.id}/revisions/{rev.id}")
        assert rev_detail_res.status_code == 200
        assert rev_detail_res.json()["canonical_markdown"] == "# Test Markdown Content"

    app.dependency_overrides.clear()
