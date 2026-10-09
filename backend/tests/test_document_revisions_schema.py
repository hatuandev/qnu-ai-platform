"""Unit Tests for Document Revision Data Models and Schemas (ADR-011 Phase 1)."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.documents.models import DocumentRevision, RepositoryDocument
from app.modules.documents.schemas import (
    AsyncUploadDocumentResponse,
    DocumentRevisionListItem,
    DocumentRevisionResponse,
    ReviewRevisionContentRequest,
    SubmitRevisionReviewRequest,
)


def test_document_revision_model_defaults_and_attributes() -> None:
    """Verify DocumentRevision model instantiation, defaults and relationships."""
    doc = RepositoryDocument(
        id="rep_doc_unit_test_01",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        title="Quy định kiểm tra đánh giá",
        file_name="quy_dinh_danh_gia.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        file_hash="hash_pdf_sample_01",
        storage_path="documents/originals/hash_pdf_sample_01/quy_dinh_danh_gia.pdf",
    )

    rev1 = DocumentRevision(
        id="rev_unit_test_01",
        document_id=doc.id,
        revision_no=1,
        source_file_name=doc.file_name,
        source_file_type=doc.file_type,
        source_size_bytes=doc.file_size_bytes,
        source_hash=doc.file_hash,
        source_storage_path=doc.storage_path,
        canonical_markdown="# Chương I: Quy định chung",
        canonical_hash="hash_md_01",
        status="ready",
        lock_version=1,
        page_manifest=[{"page": 1, "chars": 120}],
        citation_metadata={"doc_code": "01/QD-DHQN"},
        parse_provenance={"engine": "native_pdf"},
        quality_report={"status": "passed", "page_count": 1},
    )

    doc.revisions.append(rev1)
    doc.current_revision = rev1
    doc.current_revision_id = rev1.id
    doc.latest_revision_no = 1

    assert rev1.document == doc
    assert rev1.revision_no == 1
    assert rev1.status == "ready"
    assert rev1.lock_version == 1
    assert doc.current_revision_id == "rev_unit_test_01"
    assert doc.latest_revision_no == 1
    assert len(doc.revisions) == 1

    # Revision 2 based on Revision 1
    rev2 = DocumentRevision(
        id="rev_unit_test_02",
        document_id=doc.id,
        revision_no=2,
        based_on_revision_id=rev1.id,
        based_on=rev1,
        source_file_name=doc.file_name,
        source_file_type=doc.file_type,
        source_size_bytes=doc.file_size_bytes,
        source_hash=doc.file_hash,
        source_storage_path=doc.storage_path,
        canonical_markdown="# Chương I: Quy định chung (Sửa đổi 2026)",
        status="queued",
        lock_version=1,
    )
    doc.revisions.append(rev2)
    doc.latest_revision_no = 2

    assert rev2.based_on == rev1
    assert rev2.revision_no == 2
    assert rev2.status == "queued"
    assert rev2.lock_version == 1
    assert len(doc.revisions) == 2
    assert doc.latest_revision_no == 2


def test_document_revision_pydantic_schemas() -> None:
    """Verify DTO validation and serialisation for Revision endpoints."""
    now = datetime.now(UTC)

    # 1. DocumentRevisionListItem
    list_item = DocumentRevisionListItem(
        id="rev_abc123",
        document_id="rep_doc_abc",
        revision_no=1,
        source_file_name="test.docx",
        source_file_type="docx",
        source_size_bytes=2048,
        source_hash="sha256_mock_source",
        status="ready",
        quality_report={"status": "passed"},
        created_at=now,
        updated_at=now,
    )
    assert list_item.revision_no == 1
    assert list_item.status == "ready"

    # 2. DocumentRevisionResponse
    rev_response = DocumentRevisionResponse(
        id="rev_abc123",
        document_id="rep_doc_abc",
        revision_no=1,
        source_file_name="test.docx",
        source_file_type="docx",
        source_size_bytes=2048,
        source_hash="sha256_mock_source",
        source_storage_path="documents/originals/xxx/test.docx",
        canonical_markdown="# Tieu de van ban",
        canonical_hash="sha256_md_hash",
        page_manifest=[{"page": 1, "chars": 50}],
        citation_metadata={"so_hieu": "10/QD"},
        parse_provenance={"engine": "native_docx"},
        quality_report={"status": "passed"},
        status="ready",
        created_at=now,
        updated_at=now,
    )
    assert rev_response.canonical_markdown == "# Tieu de van ban"
    assert rev_response.lock_version == 1

    # 3. ReviewRevisionContentRequest
    review_req = ReviewRevisionContentRequest(
        canonical_markdown="# Noi dung sua doi hop le",
        notes="Sua loi chinh ta chuong 2",
        expected_lock_version=1,
    )
    assert len(review_req.canonical_markdown) > 0

    # Test validation error on empty markdown
    with pytest.raises(ValidationError):
        ReviewRevisionContentRequest(canonical_markdown="", expected_lock_version=1)

    # 4. SubmitRevisionReviewRequest
    submit_req = SubmitRevisionReviewRequest(
        action="approve",
        notes="Phe duyet ban hanh",
        expected_lock_version=1,
    )
    assert submit_req.action == "approve"

    # 5. AsyncUploadDocumentResponse
    async_res = AsyncUploadDocumentResponse(
        document_id="rep_doc_111",
        revision_id="rev_222",
        revision_no=1,
        file_name="van_ban.pdf",
        file_hash="hash_333",
        job_id="job_intake_444",
        status="queued",
        created_at=now,
    )
    assert async_res.status == "queued"
    assert async_res.deduplicated is False


def test_alembic_migration_module_integrity() -> None:
    """Verify that Alembic migration 20261007_document_revisions exists and loads cleanly."""
    migration_path = (
        Path(__file__).resolve().parent.parent
        / "alembic"
        / "versions"
        / "20261007_document_revisions.py"
    )
    assert migration_path.exists(), f"Migration file not found at {migration_path}"

    spec = importlib.util.spec_from_file_location("migration_20261007", migration_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "20261007_document_revisions"
    assert mod.down_revision == "20261007_document_repository"
    assert callable(mod.upgrade)
    assert callable(mod.downgrade)
