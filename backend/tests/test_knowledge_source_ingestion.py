"""Unit and integration test suite for ADR-012 Session 4:
Knowledge Source Ingestion Pipeline & Zero-Writeback Invariant.

Verifies:
1. Ingestion pipeline: snapshot source -> parse -> normalize -> validate (Quality Gate) -> ready.
2. Invariant: ZERO writeback to RepositoryDocument or DocumentRevision (clean domain decoupling).
3. Honest failure handling: empty/corrupt files report errors, ZERO fake content.
4. "Parse once, embed many": artifact key reuse skips redundant parsing.
5. Human-in-the-loop: content editing, review/approval workflow.
6. Worker task ARQ integration: task_knowledge_source_ingestion.
7. HTTP REST routes for knowledge source detail, revisions, content update, and review.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.documents.models import RepositoryDocument
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunkSet,
    KnowledgeCollection,
    KnowledgeImportBatch,
    KnowledgeImportItem,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.services.source_extraction import EXTRACTION_VERSION, SourceExtraction
from app.modules.knowledge.services.source_ingestion_service import (
    compute_sha256,
    source_ingestion_service,
)
from app.workers.tasks import task_knowledge_source_ingestion


@pytest.fixture(autouse=True)
def isolate_counter_queries():
    # Counter reconciliation has its own state-machine tests. These tests use
    # bounded execute side effects to verify the ingestion/OCR contract.
    with patch("app.modules.knowledge.services.import_state_service.refresh_batch_counts", new_callable=AsyncMock):
        yield


def _make_actor(
    actor_id: str = "user_officer_01",
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
        permissions=[
            "ai.knowledge.view",
            "ai.knowledge.upload",
            "ai.knowledge.update",
            "ai.knowledge.delete",
        ],
    )


def _make_doc(
    doc_id: str,
    title: str,
    file_name: str,
    file_bytes: bytes,
    tenant_id: str = "tenant_qnu",
    workspace_id: str = "workspace_tuyensinh",
) -> RepositoryDocument:
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return RepositoryDocument(
        id=doc_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        title=title,
        file_name=file_name,
        file_type="pdf",
        file_size_bytes=len(file_bytes),
        file_hash=file_hash,
        storage_path=f"documents/{tenant_id}/{workspace_id}/originals/{file_hash}/{file_name}",
        is_active=True,
        status="active",
        parse_status="stored",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _execute_result(scalar: Any = None, scalars_list: list[Any] | None = None, all_list: list[Any] | None = None):
    mock = MagicMock()
    if scalar is not None:
        mock.scalar_one_or_none.return_value = scalar
        mock.scalar.return_value = scalar
        mock.scalars.return_value.first.return_value = scalar
        mock.scalars.return_value.all.return_value = [scalar]
    else:
        mock.scalar_one_or_none.return_value = None
        mock.scalar.return_value = None
        mock.scalars.return_value.first.return_value = None
        mock.scalars.return_value.all.return_value = []

    if scalars_list is not None:
        mock.scalars.return_value.all.return_value = scalars_list
        mock.scalars.return_value.first.return_value = scalars_list[0] if scalars_list else None

    if all_list is not None:
        mock.all.return_value = all_list
    return mock


# ==============================================================================
# Unit Tests for Source Ingestion Pipeline
# ==============================================================================
@pytest.mark.asyncio
async def test_process_import_item_clean_source_ready_and_zero_writeback() -> None:
    """Verify clean document ingestion reaches 'ready' and respects zero-writeback invariant."""
    coll = KnowledgeCollection(
        id="col_tuyensinh_2026",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho tri thức Tuyển sinh",
    )
    raw_pdf_bytes = b"%PDF-1.4 Mock document bytes for admissions scheme."
    doc = _make_doc("doc_de_an_01", "Đề án Tuyển sinh 2026", "de_an_2026.pdf", raw_pdf_bytes)

    batch = KnowledgeImportBatch(
        id="batch_01",
        collection_id=coll.id,
        tenant_id=coll.tenant_id,
        workspace_id=coll.workspace_id,
        total_count=1,
        queued_count=1,
        processing_count=0,
        parser_profile="standard",
    )
    item = KnowledgeImportItem(
        id="item_01",
        batch_id=batch.id,
        origin_document_id=doc.id,
        origin_file_hash=doc.file_hash,
        origin_title=doc.title,
        origin_file_name=doc.file_name,
        origin_file_type=doc.file_type,
        status="queued",
        phase="snapshot",
    )
    item.batch = batch

    mock_db = AsyncMock()
    # Execute calls:
    # 1. Load item
    # 2. Load doc
    # 3. Lookup binding (None -> create)
    # 4. Revision number lookup (0 -> next 1)
    # 5. Artifact key lookup (None)
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=item),
            _execute_result(scalar=doc),
            _execute_result(scalar=None),
            _execute_result(scalar=0),
            _execute_result(scalar=None),
        ]
    )

    clean_sample_text = (
        "# TRƯỜNG ĐẠI HỌC QUY NHƠN\n\n"
        "## QUY CHẾ TUYỂN SINH NĂM 2026\n\n"
        "Trường Đại học Quy Nhơn thông báo đề án tuyển sinh trình độ đại học chính quy năm 2026. "
        "Phương thức tuyển sinh bao gồm xét tuyển thẳng, xét điểm thi tốt nghiệp THPT, và xét học bạ. "
        "Mọi thắc mắc vui lòng liên hệ Ban Tư vấn Tuyển sinh để được giải đáp chi tiết."
    )
    with patch.object(storage_service, "get", new_callable=AsyncMock) as mock_storage_get, \
         patch.object(storage_service, "save", new_callable=AsyncMock), \
         patch.object(storage_service, "exists", new_callable=AsyncMock, return_value=True), \
         patch("app.modules.knowledge.services.source_ingestion_service.extract_source", new_callable=AsyncMock,
               return_value=SourceExtraction(clean_sample_text, 1)), \
         patch("app.modules.knowledge.services.chunk_set_service.chunk_set_service.get_or_create_chunk_set", new_callable=AsyncMock) as mock_chunk_set_call:

        mock_storage_get.return_value = raw_pdf_bytes
        materialized = KnowledgeChunkSet(
            id="cs_test_01",
            source_revision_id="rev_01",
            chunk_strategy="ClauseBasedChunker",
            chunk_config={"_manifest": []},
            status="ready",
        )

        async def materialize_after_persist(**kwargs):
            assert any(
                isinstance(call.args[0], KnowledgeSourceRevision)
                and call.args[0].id == kwargs["source_revision_id"]
                for call in mock_db.add.call_args_list
            ), "Persist the source revision before querying it for chunking"
            return materialized

        mock_chunk_set_call.side_effect = materialize_after_persist

        source_rev = await source_ingestion_service.process_import_item(
            db=mock_db,
            item_id=item.id,
        )

        assert source_rev.status == "ready"
        assert source_rev.revision_no == 1
        assert "QUY CHẾ TUYỂN SINH" in (source_rev.canonical_markdown or "")
        assert source_rev.quality_report.get("overall_status") == "passed"
        assert item.status == "succeeded"
        assert item.phase == "completed"
        assert batch.succeeded_count == 1
        assert batch.status == "completed"

        # ADR-012 CRITICAL INVARIANT: Zero Writeback to RepositoryDocument
        assert doc.parse_status == "stored", "ADR-012 Violation: doc.parse_status must remain 'stored'!"
        assert not hasattr(doc, "canonical_markdown") or getattr(doc, "canonical_markdown", None) is None


@pytest.mark.asyncio
async def test_process_import_item_empty_file_fails_honestly() -> None:
    """Verify empty/corrupt files fail honestly with RFC 7807 and ZERO fake content."""
    batch = KnowledgeImportBatch(
        id="batch_02",
        collection_id="col_01",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        total_count=1,
        queued_count=1,
    )
    doc = _make_doc("doc_empty", "Tệp rỗng", "rong.pdf", b"")
    item = KnowledgeImportItem(
        id="item_empty",
        batch_id=batch.id,
        origin_document_id=doc.id,
        origin_file_hash=doc.file_hash,
        origin_title=doc.title,
        origin_file_name=doc.file_name,
        origin_file_type=doc.file_type,
        status="queued",
        phase="snapshot",
    )
    item.batch = batch

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=item),
            _execute_result(scalar=doc),
        ]
    )

    with patch.object(storage_service, "get", new_callable=AsyncMock) as mock_storage_get:
        mock_storage_get.return_value = b""  # Empty content!

        with pytest.raises(AppException) as exc_info:
            await source_ingestion_service.process_import_item(
                db=mock_db,
                item_id=item.id,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "FILE_CONTENT_EMPTY"
        assert item.status == "failed"
        assert item.failure_code == "FILE_CONTENT_EMPTY"
        assert batch.failed_count == 1
        assert batch.status == "partial_failed"


@pytest.mark.asyncio
async def test_process_import_item_artifact_reuse_parse_once_embed_many() -> None:
    """Verify artifact key reuse skips redundant parsing and OCR execution."""
    coll = KnowledgeCollection(id="col_01", tenant_id="t1", workspace_id="ws1")
    doc_bytes = b"%PDF content already parsed in system"
    doc = _make_doc("doc_reused", "Tài liệu tái sử dụng", "tai_su_dung.pdf", doc_bytes)

    batch = KnowledgeImportBatch(
        id="batch_03",
        collection_id=coll.id,
        tenant_id="t1",
        workspace_id="ws1",
        total_count=1,
        queued_count=1,
        parser_profile="standard",
    )
    item = KnowledgeImportItem(
        id="item_reused",
        batch_id=batch.id,
        origin_document_id=doc.id,
        origin_file_hash=doc.file_hash,
        origin_title=doc.title,
        origin_file_name=doc.file_name,
        origin_file_type=doc.file_type,
        status="queued",
        phase="snapshot",
    )
    item.batch = batch

    # Existing ready artifact
    artifact_key = compute_sha256(f"{doc.file_hash}:standard:{EXTRACTION_VERSION}")
    existing_artifact_rev = KnowledgeSourceRevision(
        id="ks_rev_existing_111",
        binding_id="bnd_existing",
        revision_no=1,
        origin_document_id="doc_other",
        origin_file_hash=doc.file_hash,
        canonical_markdown="# Nội dung đã bóc tách từ trước",
        canonical_hash=compute_sha256("# Nội dung đã bóc tách từ trước"),
        quality_report={"overall_status": "passed"},
        artifact_key=artifact_key,
        status="ready",
    )

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=item),
            _execute_result(scalar=doc),
            _execute_result(scalar=None),  # binding lookup -> create new
            _execute_result(scalar=0),     # latest rev no -> 1
            _execute_result(scalar=existing_artifact_rev),  # ARTIFACT FOUND!
        ]
    )

    with patch.object(storage_service, "get", new_callable=AsyncMock) as mock_storage_get, \
         patch.object(storage_service, "save", new_callable=AsyncMock), \
         patch.object(storage_service, "exists", new_callable=AsyncMock, return_value=True), \
         patch("app.modules.knowledge.services.source_ingestion_service.extract_source", new_callable=AsyncMock) as mock_get_parser, \
         patch("app.modules.knowledge.services.chunk_set_service.chunk_set_service.get_or_create_chunk_set", new_callable=AsyncMock) as mock_chunk_set_call:

        mock_storage_get.return_value = doc_bytes
        mock_chunk_set_call.return_value = KnowledgeChunkSet(
            id="cs_test_01",
            source_revision_id="rev_01",
            chunk_strategy="ClauseBasedChunker",
            chunk_config={"_manifest": []},
            status="ready",
        )

        source_rev = await source_ingestion_service.process_import_item(
            db=mock_db,
            item_id=item.id,
        )

        # Invariant: parser was NOT called because artifact was reused!
        assert not mock_get_parser.called
        assert source_rev.status == "ready"
        assert source_rev.canonical_markdown == "# Nội dung đã bóc tách từ trước"
        assert source_rev.parse_provenance.get("reused_artifact") is True


# ==============================================================================
# Unit Tests for Content Editing & Human Review
# ==============================================================================
@pytest.mark.asyncio
async def test_source_content_editing_and_human_review() -> None:
    """Verify editing Markdown content re-evaluates Quality Gate and review approvals."""
    binding = KnowledgeBinding(id="bnd_review_test", collection_id="col_01")
    source_rev = KnowledgeSourceRevision(
        id="rev_under_review",
        binding_id=binding.id,
        revision_no=1,
        origin_document_id="doc_01",
        origin_file_hash="hash_01",
        canonical_markdown="Nội dung cần hiệu đính",
        status="review_required",
    )

    mock_db = AsyncMock()

    # 1. Update content
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(),
            _execute_result(),
            _execute_result(scalar=binding),
            _execute_result(scalar=source_rev),
            _execute_result(scalar=1),
        ]
    )
    updated_rev = await source_ingestion_service.update_revision_content(
        db=mock_db,
        collection_id="col_01",
        source_id=binding.id,
        revision_id=source_rev.id,
        new_markdown="Nội dung sau khi được cán bộ hiệu đính kỹ lưỡng.",
    )
    assert updated_rev.canonical_markdown == "Nội dung sau khi được cán bộ hiệu đính kỹ lưỡng."
    assert updated_rev.id != source_rev.id
    assert source_rev.canonical_markdown == "Nội dung cần hiệu đính"

    # 2. Review - Approved
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(),
            _execute_result(),
            _execute_result(scalar=binding),
            _execute_result(scalar=source_rev),
        ]
    )
    approved_rev = await source_ingestion_service.review_source_revision(
        db=mock_db,
        collection_id="col_01",
        source_id=binding.id,
        revision_id=source_rev.id,
        decision="approved",
    )
    assert approved_rev.status == "ready"
    assert binding.active_source_revision_id == source_rev.id

    # 3. Review - Rejected
    source_rev.status = "review_required"
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(),
            _execute_result(),
            _execute_result(scalar=binding),
            _execute_result(scalar=source_rev),
        ]
    )
    rejected_rev = await source_ingestion_service.review_source_revision(
        db=mock_db,
        collection_id="col_01",
        source_id=binding.id,
        revision_id=source_rev.id,
        decision="rejected",
        comment="Bản scan bị nghiêng và mờ",
    )
    assert rejected_rev.status == "failed"
    assert rejected_rev.failure_code == "HUMAN_REVIEW_REJECTED"


# ==============================================================================
# Worker Task ARQ Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_worker_task_knowledge_source_ingestion() -> None:
    """Verify ARQ worker task_knowledge_source_ingestion completes JobRecord lifecycle."""
    job = JobRecord(
        id="job_ks_ingest_01",
        job_type="knowledge_source_ingestion",
        status="queued",
        payload={"item_id": "imp_item_99", "ocr_engine": "tesseract"},
    )
    mock_source_rev = MagicMock()
    mock_source_rev.id = "ks_rev_done_99"
    mock_source_rev.status = "ready"
    mock_source_rev.quality_report = {"overall_status": "passed"}

    with patch("app.workers.tasks.AsyncSessionFactory") as mock_session_factory, \
         patch("app.workers.tasks._load_job", new_callable=AsyncMock) as mock_load_job, \
         patch("app.workers.tasks._set_job", new_callable=AsyncMock) as mock_set_job, \
         patch("app.workers.tasks._check_pre_execution_cancelled", new_callable=AsyncMock, return_value=False), \
         patch("app.workers.tasks._is_cancelled", new_callable=AsyncMock, return_value=False), \
         patch.object(source_ingestion_service, "process_import_item", new_callable=AsyncMock) as mock_process:

        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        mock_load_job.return_value = job
        mock_set_job.return_value = True
        mock_process.return_value = mock_source_rev

        res = await task_knowledge_source_ingestion(ctx={}, job_id=job.id)

        assert res["status"] == "completed"
        assert res["source_revision_id"] == "ks_rev_done_99"
        assert res["source_status"] == "ready"
        assert mock_process.called


# ==============================================================================
# Integration HTTP Route Tests for Source Management
# ==============================================================================
@pytest.mark.asyncio
async def test_http_routes_source_management() -> None:
    """Test REST API routes for knowledge sources, revisions, editing and review."""
    actor = _make_actor()
    coll = KnowledgeCollection(
        id="col_http_source_test",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )
    binding = KnowledgeBinding(
        id="bnd_http_test_01",
        collection_id=coll.id,
        repository_document_id="rep_doc_01",
        status="active",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )
    source_rev = KnowledgeSourceRevision(
        id="rev_http_01",
        binding_id=binding.id,
        revision_no=1,
        origin_document_id="rep_doc_01",
        origin_file_hash="hash_mock",
        canonical_markdown="Nội dung ban đầu",
        status="review_required",
    )
    binding.active_source_revision = source_rev
    binding.source_revisions = [source_rev]

    mock_db = AsyncMock()

    app.dependency_overrides[get_current_actor] = lambda: actor
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /sources/{source_id}
        with (
            patch.object(source_ingestion_service, "get_source", new_callable=AsyncMock) as mock_get_source,
            patch.object(source_ingestion_service, "get_source_revisions", new_callable=AsyncMock) as mock_detail_revisions,
        ):
            mock_get_source.return_value = binding
            mock_detail_revisions.return_value = [source_rev]
            res = await client.get(f"/platform/v1alpha1/knowledge/collections/{coll.id}/sources/{binding.id}")
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == binding.id
            assert data["repository_document_id"] == "rep_doc_01"
            assert data["revisions"][0]["id"] == source_rev.id

        # 2. GET /sources/{source_id}/revisions
        with patch.object(source_ingestion_service, "get_source_revisions", new_callable=AsyncMock) as mock_get_revs:
            mock_get_revs.return_value = [source_rev]
            res = await client.get(f"/platform/v1alpha1/knowledge/collections/{coll.id}/sources/{binding.id}/revisions")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1
            assert data[0]["id"] == source_rev.id

        # 3. PATCH /sources/{source_id}/revisions/{rev_id}/content
        with patch.object(source_ingestion_service, "update_revision_content", new_callable=AsyncMock) as mock_patch:
            source_rev.canonical_markdown = "Nội dung sau hiệu đính"
            mock_patch.return_value = source_rev
            res = await client.patch(
                f"/platform/v1alpha1/knowledge/collections/{coll.id}/sources/{binding.id}/revisions/{source_rev.id}/content",
                json={"canonical_markdown": "Nội dung sau hiệu đính"},
            )
            assert res.status_code == 200
            assert res.json()["canonical_markdown"] == "Nội dung sau hiệu đính"

        # 4. POST /sources/{source_id}/revisions/{rev_id}/review
        with patch.object(source_ingestion_service, "review_source_revision", new_callable=AsyncMock) as mock_review:
            source_rev.status = "ready"
            mock_review.return_value = source_rev
            res = await client.post(
                f"/platform/v1alpha1/knowledge/collections/{coll.id}/sources/{binding.id}/revisions/{source_rev.id}/review",
                json={"decision": "approved", "comment": "Đã kiểm tra kỹ lưỡng"},
            )
            assert res.status_code == 200
            assert res.json()["status"] == "ready"

    app.dependency_overrides.clear()
