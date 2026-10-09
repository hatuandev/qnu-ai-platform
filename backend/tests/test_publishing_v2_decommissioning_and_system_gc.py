"""Tests for Knowledge Publishing V2 — Safe Legacy Decommissioning & System-wide Garbage Collection.

Phiên 12 (Kế Hoạch 11 / ADR-011):
- Enforce Single Source of Truth: Direct Upload blocked with RFC 7807 when KNOWLEDGE_ALLOW_DIRECT_UPLOAD=False
- System-wide Artifact Garbage Collection (dry_run & execution across multiple collections)
- ARQ worker task task_knowledge_garbage_collection
- System Decommissioning Audit Report
- REST API endpoints for System-wide GC and Decommissioning Audit
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeCollection,
)
from app.modules.knowledge.schemas import (
    GarbageCollectionReport,
    SystemDecommissioningAuditReport,
    SystemGarbageCollectionReport,
)
from app.modules.knowledge.service import knowledge_service
from app.modules.knowledge.services.gc_service import gc_service
from app.workers.tasks import task_knowledge_garbage_collection


def utcnow() -> datetime:
    return datetime.now(UTC)


def _mock_admin_actor() -> AuthActor:
    return AuthActor(
        username="admin",
        email="admin@qnu.edu.vn",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        role="admin",
        roles=["admin"],
        permissions=["*"],
    )


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    result.scalar_one = MagicMock(return_value=scalar)
    result.scalar = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_list or [])
    scalars.first = MagicMock(return_value=scalar or (scalars_list[0] if scalars_list else None))
    result.scalars = MagicMock(return_value=scalars)
    result.all = MagicMock(return_value=scalars_list or [])
    result.first = MagicMock(return_value=scalar or (scalars_list[0] if scalars_list else None))
    return result


def _fresh_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


# ==============================================================================
# 1. Enforce Single Source of Truth: Direct Upload Blocked vs Allowed
# ==============================================================================
@pytest.mark.asyncio
async def test_direct_upload_blocked_when_flag_disabled(monkeypatch) -> None:
    """Verify legacy direct upload is blocked when KNOWLEDGE_ALLOW_DIRECT_UPLOAD is False (default)."""
    monkeypatch.setattr(settings, "KNOWLEDGE_ALLOW_DIRECT_UPLOAD", False)

    session = _fresh_session()

    async def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_current_actor] = _mock_admin_actor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("test_doc.txt", io.BytesIO(b"Noi dung test"), "text/plain")}
        res = await client.post(
            f"{settings.API_PREFIX}/knowledge/collections/col_decom_1/upload",
            files=files,
        )

        assert res.status_code == 400
        body = res.json()
        assert body["code"] == "DIRECT_UPLOAD_DEPRECATED_USE_CENTRAL_REPOSITORY"
        assert "vô hiệu hóa" in body["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_direct_upload_allowed_when_flag_enabled(monkeypatch) -> None:
    """Verify legacy direct upload is allowed when KNOWLEDGE_ALLOW_DIRECT_UPLOAD is temporarily enabled."""
    monkeypatch.setattr(settings, "KNOWLEDGE_ALLOW_DIRECT_UPLOAD", True)

    session = _fresh_session()

    async def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_current_actor] = _mock_admin_actor

    mock_doc = MagicMock()
    mock_doc.id = "doc_legacy_allowed"
    mock_doc.collection_id = "col_decom_2"
    mock_doc.document_type_code = None
    mock_doc.title = "Test Doc"
    mock_doc.file_name = "test_doc.txt"
    mock_doc.file_type = "txt"
    mock_doc.file_size_bytes = 12
    mock_doc.file_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    mock_doc.version = 1
    mock_doc.status = "queued"
    mock_doc.index_status = "pending"
    mock_doc.index_error = None
    mock_doc.is_active = True
    mock_doc.created_at = utcnow()
    mock_doc.updated_at = utcnow()
    mock_doc.chunk_count = 0
    mock_doc.ocr_method = "PyMuPDF"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(knowledge_service, "ingest_document", return_value=mock_doc):
            files = {"file": ("test_doc.txt", io.BytesIO(b"Noi dung test"), "text/plain")}
            res = await client.post(
                f"{settings.API_PREFIX}/knowledge/collections/col_decom_2/upload",
                files=files,
            )

            assert res.status_code == 201
            assert res.headers.get("Deprecation") == "@2026-10-07"
            assert "X-API-Deprecation-Warning" in res.headers

    app.dependency_overrides.clear()


# ==============================================================================
# 2. System-wide Garbage Collection (Dry-run & Execution)
# ==============================================================================
@pytest.mark.asyncio
async def test_system_wide_garbage_collection_dry_run() -> None:
    """Verify collect_garbage_system_wide iterates all collections and calculates pruned totals in dry-run mode."""
    session = _fresh_session()

    col1 = KnowledgeCollection(
        id="col_sys_gc_1",
        name="Kho Sys GC 1",
        collection_metadata={"canary_policy": {"retention_revisions": 1}},
    )
    col2 = KnowledgeCollection(
        id="col_sys_gc_2",
        name="Kho Sys GC 2",
        collection_metadata={"canary_policy": {"retention_revisions": 2}},
    )

    session.execute.side_effect = [
        _execute_result(scalars_list=[col1, col2]),
    ]

    rep1 = GarbageCollectionReport(
        collection_id="col_sys_gc_1",
        dry_run=True,
        keep_revisions=1,
        total_bindings_scanned=2,
        pruned_revisions_count=3,
        pruned_revision_ids=["r1", "r2", "r3"],
        pruned_chunks_count=6,
        pruned_facts_count=2,
        pruned_points_count=6,
        message="Dry-run col1",
        executed_at=utcnow(),
    )
    rep2 = GarbageCollectionReport(
        collection_id="col_sys_gc_2",
        dry_run=True,
        keep_revisions=2,
        total_bindings_scanned=1,
        pruned_revisions_count=1,
        pruned_revision_ids=["r4"],
        pruned_chunks_count=2,
        pruned_facts_count=0,
        pruned_points_count=2,
        message="Dry-run col2",
        executed_at=utcnow(),
    )

    with patch.object(gc_service, "collect_garbage", side_effect=[rep1, rep2]):
        report = await gc_service.collect_garbage_system_wide(
            db=session,
            dry_run=True,
        )

    assert report.dry_run is True
    assert report.total_collections_scanned == 2
    assert report.total_bindings_scanned == 3
    assert report.total_pruned_revisions_count == 4
    assert report.total_pruned_chunks_count == 8
    assert report.total_pruned_facts_count == 2
    assert report.total_pruned_points_count == 8
    assert len(report.reports) == 2


@pytest.mark.asyncio
async def test_system_wide_garbage_collection_execution() -> None:
    """Verify collect_garbage_system_wide executes real pruning when dry_run=False."""
    session = _fresh_session()
    col = KnowledgeCollection(
        id="col_sys_exec",
        name="Kho Exec",
        collection_metadata={},
    )
    session.execute.return_value = _execute_result(scalars_list=[col])

    rep = GarbageCollectionReport(
        collection_id="col_sys_exec",
        dry_run=False,
        keep_revisions=2,
        total_bindings_scanned=5,
        pruned_revisions_count=2,
        pruned_revision_ids=["rev_old_1", "rev_old_2"],
        pruned_chunks_count=10,
        pruned_facts_count=4,
        pruned_points_count=10,
        message="Executed col",
        executed_at=utcnow(),
    )

    with patch.object(gc_service, "collect_garbage", return_value=rep):
        report = await gc_service.collect_garbage_system_wide(
            db=session,
            default_keep_revisions=2,
            dry_run=False,
        )

    assert report.dry_run is False
    assert report.total_collections_scanned == 1
    assert report.total_pruned_revisions_count == 2
    assert report.total_pruned_chunks_count == 10
    assert "Thực thi toàn hệ thống" in report.message


# ==============================================================================
# 3. System Decommissioning Audit Report
# ==============================================================================
@pytest.mark.asyncio
async def test_system_decommissioning_audit_report() -> None:
    """Verify audit_system_decommissioning aggregates collections, read modes, and legacy ratios."""
    session = _fresh_session()

    col1 = KnowledgeCollection(
        id="col_aud_1",
        name="Kho Revisioned",
        collection_metadata={"canary_policy": {"read_mode": "revisioned"}},
    )
    col2 = KnowledgeCollection(
        id="col_aud_2",
        name="Kho Shadow",
        collection_metadata={"canary_policy": {"read_mode": "shadow"}},
    )
    col3 = KnowledgeCollection(
        id="col_aud_3",
        name="Kho System Default",
        collection_metadata={},
    )

    res_cols = _execute_result(scalars_list=[col1, col2, col3])
    res_docs = _execute_result(scalar=10)
    res_bnds = _execute_result(scalar=40)
    res_prun = _execute_result(scalar=8)

    session.execute.side_effect = [res_cols, res_docs, res_bnds, res_prun]

    report = await gc_service.audit_system_decommissioning(db=session)

    assert report.total_collections == 3
    assert report.total_legacy_documents == 10
    assert report.total_v2_bindings == 40
    # 40 / 50 = 80.0%
    assert report.v2_adoption_rate_pct == 80.0
    # col1 = revisioned, col2 = shadow, col3 = system default (revisioned)
    assert report.collections_in_revisioned_mode == 2
    assert report.collections_in_shadow_mode == 1
    assert report.total_prunable_revisions_estimate == 8


# ==============================================================================
# 4. ARQ Worker Task: task_knowledge_garbage_collection
# ==============================================================================
@pytest.mark.asyncio
async def test_worker_task_knowledge_garbage_collection() -> None:
    """Verify task_knowledge_garbage_collection executes as an ARQ background job."""
    session = _fresh_session()

    job = JobRecord(
        id="job_gc_worker_test",
        job_type="knowledge_garbage_collection",
        status="pending",
        payload={"collection_id": "col_123", "dry_run": True, "keep_revisions": 2},
    )

    session.execute.return_value = _execute_result(scalar=job)

    mock_rep = GarbageCollectionReport(
        collection_id="col_123",
        dry_run=True,
        keep_revisions=2,
        total_bindings_scanned=2,
        pruned_revisions_count=1,
        pruned_revision_ids=["r_pruned"],
        pruned_chunks_count=5,
        pruned_facts_count=1,
        pruned_points_count=5,
        message="Dry run worker",
        executed_at=utcnow(),
    )

    with (
        patch("app.workers.tasks.AsyncSessionFactory", return_value=session),
        patch.object(gc_service, "collect_garbage", return_value=mock_rep),
    ):
        session.__aenter__.return_value = session
        result = await task_knowledge_garbage_collection({}, job_id="job_gc_worker_test")

    assert result["status"] == "completed"
    assert result["job_id"] == "job_gc_worker_test"
    assert result["result"]["pruned_revisions_count"] == 1


# ==============================================================================
# 5. REST API Endpoints: System-wide GC & Decommissioning Audit
# ==============================================================================
@pytest.mark.asyncio
async def test_rest_api_system_wide_gc_and_decommissioning_audit() -> None:
    """Verify REST API endpoints POST /knowledge/gc/system-wide and GET /knowledge/decommissioning/audit."""
    session = _fresh_session()

    async def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_current_actor] = _mock_admin_actor

    mock_sys_gc = SystemGarbageCollectionReport(
        total_collections_scanned=4,
        total_bindings_scanned=12,
        total_pruned_revisions_count=6,
        total_pruned_chunks_count=18,
        total_pruned_facts_count=3,
        total_pruned_points_count=18,
        dry_run=True,
        reports=[],
        message="Dry-run system complete",
        executed_at=utcnow(),
    )

    mock_audit = SystemDecommissioningAuditReport(
        total_collections=5,
        total_legacy_documents=2,
        total_v2_bindings=20,
        v2_adoption_rate_pct=90.9,
        collections_in_revisioned_mode=4,
        collections_in_shadow_mode=1,
        collections_in_legacy_mode=0,
        total_prunable_revisions_estimate=15,
        audited_at=utcnow(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with (
            patch.object(knowledge_service, "collect_garbage_system_wide", return_value=mock_sys_gc),
            patch.object(knowledge_service, "audit_system_decommissioning", return_value=mock_audit),
        ):
            # 1. POST /knowledge/gc/system-wide
            gc_res = await client.post(
                f"{settings.API_PREFIX}/knowledge/gc/system-wide",
                json={"dry_run": True, "default_keep_revisions": 2},
            )
            assert gc_res.status_code == 200
            gc_data = gc_res.json()
            assert gc_data["total_collections_scanned"] == 4
            assert gc_data["total_pruned_revisions_count"] == 6

            # 2. GET /knowledge/decommissioning/audit
            aud_res = await client.get(
                f"{settings.API_PREFIX}/knowledge/decommissioning/audit"
            )
            assert aud_res.status_code == 200
            aud_data = aud_res.json()
            assert aud_data["total_collections"] == 5
            assert aud_data["v2_adoption_rate_pct"] == 90.9
            assert aud_data["collections_in_revisioned_mode"] == 4

    app.dependency_overrides.clear()
