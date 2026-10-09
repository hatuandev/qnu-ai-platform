"""Test Suite for Publishing V2 Cutover & Artifact Garbage Collection (ADR-011 Phase 7).

Covers:
1. Cutover Read Mode 'revisioned' strict snapshot isolation (zero staging/unindexed leak).
2. Deprecation headers & warnings on legacy endpoints (/reindex, /upload).
3. Artifact Garbage Collection (GC) dry-run simulation mode.
4. Artifact Garbage Collection (GC) execution with Rollback Protection (preserves active + 2 historical).
5. Safe zero-reindex rollback to preserved historical revisions.
6. Blocked rollback to pruned revisions (REVISION_ALREADY_PRUNED).
7. REST API endpoint POST /knowledge/collections/{id}/gc.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.schemas import CanaryPolicyResponse, GarbageCollectionReport
from app.modules.knowledge.service import knowledge_service
from app.modules.knowledge.services.gc_service import gc_service
from app.modules.knowledge.services.index_build_service import index_build_service
from app.modules.rag.retriever import RetrievalSnapshot, hybrid_retriever


def utcnow() -> datetime:
    return datetime.now(UTC)


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
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _mock_admin_actor() -> AuthActor:
    return AuthActor(
        actor_id="admin_test",
        username="admin",
        display_name="Admin Test",
        email="admin@qnu.edu.vn",
        user_type="admin",
        tenant_id="tenant_qnu",
        workspace_id="ws_default",
        role="admin",
        roles=["admin"],
        permissions=["*"],
        authenticated=True,
        session_version="v1",
    )


# ==============================================================================
# 1. Cutover Read Mode 'revisioned' Strict Snapshot Isolation
# ==============================================================================
@pytest.mark.asyncio
async def test_cutover_read_mode_revisioned_zero_leak() -> None:
    """Asserts that in 'revisioned' read mode, only chunks belonging to active revisions are returned."""
    session = _fresh_session()
    col_id = "col_cutover_test"
    active_rev_id = "rev_active_v1"

    chunk_active = KnowledgeChunk(
        id="chunk_1",
        collection_id=col_id,
        document_id="doc_1",
        binding_id="bnd_1",
        index_revision_id=active_rev_id,
        content="Nội dung điều 1 quy định tuyển sinh chính thức 2026.",
        chunk_metadata={"document_revision": 1},
    )

    # 1. weighted query execution -> returns chunk_active
    res_weighted = _execute_result(scalars_list=[chunk_active])
    # 2. unaccent fallback -> returns []
    res_uni = _execute_result(scalars_list=[])
    # 3. doc titles lookup -> returns [("doc_1", "Quy định 2026")]
    res_doc_titles = MagicMock()
    res_doc_titles.all = MagicMock(return_value=[("doc_1", "Quy định 2026")])

    session.execute.side_effect = [res_weighted, res_uni, res_doc_titles]

    snapshot = RetrievalSnapshot(
        snapshot_id="snap_cutover_test",
        collection_id=col_id,
        collection_epoch=1,
        binding_revisions={"bnd_1": active_rev_id},
    )

    with patch.object(settings, "RAG_REVISION_READ_MODE", "revisioned"):
        results = await hybrid_retriever.search_sparse_fts(
            db=session,
            collection_id=col_id,
            query="tuyển sinh 2026",
            top_k=5,
            snapshot=snapshot,
        )

        assert len(results) == 1
        assert results[0]["index_revision_id"] == active_rev_id
        assert results[0]["document_revision"] == 1


# ==============================================================================
# 2. Deprecation Headers on Legacy Endpoints
# ==============================================================================
@pytest.mark.asyncio
async def test_legacy_endpoints_deprecation_headers() -> None:
    """Verifies that legacy /reindex and /upload endpoints return RFC deprecation headers."""
    session = _fresh_session()

    async def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_current_actor] = _mock_admin_actor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test POST /collections/{id}/reindex
        with (
            patch.object(knowledge_service, "get_collection", new_callable=AsyncMock),
            patch("app.modules.jobs.service.jobs_service.enqueue_job", new_callable=AsyncMock) as mock_job,
        ):
            from app.modules.jobs.models import JobRecord

            mock_job.return_value = JobRecord(
                id="job_dummy_reindex",
                job_type="reindex",
                status="queued",
                collection_id="col_test",
            )

            res = await client.post(
                f"{settings.API_PREFIX}/knowledge/collections/col_test/reindex",
            )
            assert res.status_code == 200
            assert res.headers.get("Deprecation") == "@2026-10-07"
            assert "ADR-011" in res.headers.get("X-API-Deprecation-Warning", "")
            data = res.json()
            assert "warning" in data

        # 2. Test POST /documents/{id}/reindex
        with patch.object(
            knowledge_service,
            "reindex_document",
            return_value={
                "document_id": "doc_123",
                "indexed_chunks": 5,
                "status": "success",
                "index_status": "indexed",
                "reindexed_documents": ["doc_123"],
                "total_reindexed_chunks": 5,
                "message": "Success",
            },
        ):
            res_doc = await client.post(
                f"{settings.API_PREFIX}/knowledge/documents/doc_123/reindex",
            )
            assert res_doc.status_code == 200
            assert res_doc.headers.get("Deprecation") == "@2026-10-07"
            assert "ADR-011" in res_doc.headers.get("X-API-Deprecation-Warning", "")

    app.dependency_overrides.clear()


# ==============================================================================
# 3. Artifact Garbage Collection (GC) Dry-Run
# ==============================================================================
@pytest.mark.asyncio
async def test_garbage_collection_dry_run() -> None:
    """Verifies dry-run GC calculation without mutating database or vector index."""
    session = _fresh_session()
    col = KnowledgeCollection(id="col_1", name="Kho Test", module_code="test")
    session.get.return_value = col

    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id=col.id,
        active_index_revision_id="rev_1",
        active_epoch=1,
    )

    # Revisions:
    # rev1: active
    # rev2: superseded (keep #1)
    # rev3: superseded (keep #2)
    # rev4: superseded (outside retention window) -> candidate
    # rev5: failed -> candidate
    rev1 = KnowledgeIndexRevision(id="rev_1", binding_id=binding.id, status="active", created_at=utcnow())
    rev2 = KnowledgeIndexRevision(id="rev_2", binding_id=binding.id, status="superseded", created_at=utcnow())
    rev3 = KnowledgeIndexRevision(id="rev_3", binding_id=binding.id, status="superseded", created_at=utcnow())
    rev4 = KnowledgeIndexRevision(id="rev_4", binding_id=binding.id, status="superseded", created_at=utcnow())
    rev5 = KnowledgeIndexRevision(id="rev_5", binding_id=binding.id, status="failed", created_at=utcnow())

    # 1. select KnowledgeBinding
    res_bindings = _execute_result(scalars_list=[binding])
    # 2. select KnowledgeIndexRevision
    res_revs = _execute_result(scalars_list=[rev1, rev2, rev3, rev4, rev5])
    # 3. rev4 chunk count = 2
    res_c4 = _execute_result(scalar=2)
    # 4. rev4 fact count = 1
    res_f4 = _execute_result(scalar=1)
    # 5. rev5 chunk count = 0
    res_c5 = _execute_result(scalar=0)
    # 6. rev5 fact count = 0
    res_f5 = _execute_result(scalar=0)

    session.execute.side_effect = [
        res_bindings,
        res_revs,
        res_c4, res_f4,
        res_c5, res_f5,
    ]

    with patch("app.modules.rag.vector_indexer.vector_indexer.delete_points_by_index_revision", new_callable=AsyncMock) as mock_del:
        report = await gc_service.collect_garbage(
            db=session,
            collection_id=col.id,
            keep_revisions=2,
            dry_run=True,
        )

        assert report.dry_run is True
        assert report.total_bindings_scanned == 1
        assert report.pruned_revisions_count == 2
        assert "rev_4" in report.pruned_revision_ids
        assert "rev_5" in report.pruned_revision_ids
        assert report.pruned_chunks_count == 2
        assert report.pruned_facts_count == 1
        # DB must not commit in dry run
        session.commit.assert_not_called()
        mock_del.assert_not_called()
        # Statuses must remain unchanged
        assert rev4.status == "superseded"
        assert rev5.status == "failed"


# ==============================================================================
# 4. Artifact Garbage Collection (GC) Execution
# ==============================================================================
@pytest.mark.asyncio
async def test_garbage_collection_execution_pruning() -> None:
    """Verifies actual GC pruning updates status to 'pruned', calls delete, and commits."""
    session = _fresh_session()
    col = KnowledgeCollection(id="col_1", name="Kho Test", module_code="test")
    session.get.return_value = col

    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id=col.id,
        active_index_revision_id="rev_1",
        active_epoch=1,
    )

    rev1 = KnowledgeIndexRevision(id="rev_1", binding_id=binding.id, status="active", created_at=utcnow())
    rev2 = KnowledgeIndexRevision(id="rev_2", binding_id=binding.id, status="superseded", created_at=utcnow())
    rev3 = KnowledgeIndexRevision(id="rev_3", binding_id=binding.id, status="superseded", created_at=utcnow())
    rev4 = KnowledgeIndexRevision(id="rev_4", binding_id=binding.id, status="superseded", created_at=utcnow())
    rev5 = KnowledgeIndexRevision(id="rev_5", binding_id=binding.id, status="failed", created_at=utcnow())

    res_bindings = _execute_result(scalars_list=[binding])
    res_revs = _execute_result(scalars_list=[rev1, rev2, rev3, rev4, rev5])
    res_c4 = _execute_result(scalar=2)
    res_f4 = _execute_result(scalar=1)
    res_del_c4 = _execute_result()
    res_del_f4 = _execute_result()
    res_c5 = _execute_result(scalar=0)
    res_f5 = _execute_result(scalar=0)

    session.execute.side_effect = [
        res_bindings,
        res_revs,
        res_c4, res_f4, res_del_c4, res_del_f4,
        res_c5, res_f5,
    ]

    with patch("app.modules.rag.vector_indexer.vector_indexer.delete_points_by_index_revision", new_callable=AsyncMock) as mock_del:
        mock_del.side_effect = [2, 0]

        report = await gc_service.collect_garbage(
            db=session,
            collection_id=col.id,
            keep_revisions=2,
            dry_run=False,
        )

        assert report.dry_run is False
        assert report.pruned_revisions_count == 2
        assert rev4.status == "pruned"
        assert rev5.status == "pruned"
        assert rev1.status == "active"
        assert rev2.status == "superseded"
        assert rev3.status == "superseded"
        session.commit.assert_awaited_once()
        assert mock_del.call_count == 2


# ==============================================================================
# 5. Rollback Protection: Allowed within Retention Window
# ==============================================================================
@pytest.mark.asyncio
async def test_rollback_protection_allowed_within_retention() -> None:
    """Verifies instant rollback to a preserved historical revision succeeds."""
    session = _fresh_session()
    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id="col_1",
        active_index_revision_id="rev_1",
        active_epoch=1,
    )
    rev1 = KnowledgeIndexRevision(id="rev_1", binding_id=binding.id, status="active")
    rev2 = KnowledgeIndexRevision(
        id="rev_2",
        binding_id=binding.id,
        status="superseded",
        revision_no=2,
        chunk_count=2,
    )
    col = KnowledgeCollection(id="col_1", name="Kho Test")

    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeBinding, "bnd_1"): binding,
        (KnowledgeIndexRevision, "rev_2"): rev2,
        (KnowledgeIndexRevision, "rev_1"): rev1,
        (KnowledgeCollection, "col_1"): col,
    }.get((model, obj_id))
    session.execute.side_effect = [
        _execute_result(scalar=binding),
        _execute_result(scalar=1),
    ]

    with patch("app.modules.rag.vector_indexer.vector_indexer.activate_index_revision", new_callable=AsyncMock) as mock_act:
        mock_act.return_value = 2

        resp = await index_build_service.rollback_index_revision(
            db=session,
            binding_id=binding.id,
            target_index_revision_id="rev_2",
            expected_epoch=1,
            reason="Rollback về v2",
        )

        assert resp.action == "rollback"
        assert resp.to_index_revision_id == "rev_2"
        assert resp.epoch == 2
        assert binding.active_index_revision_id == "rev_2"
        assert rev2.status == "active"
        assert rev1.status == "archived"
        session.commit.assert_awaited_once()


# ==============================================================================
# 6. Rollback Protection: Blocked for Pruned Revision
# ==============================================================================
@pytest.mark.asyncio
async def test_rollback_protection_blocked_for_pruned_revision() -> None:
    """Verifies that rollback to a pruned revision is strictly blocked with REVISION_ALREADY_PRUNED."""
    session = _fresh_session()
    binding = KnowledgeBinding(
        id="bnd_1",
        collection_id="col_1",
        active_index_revision_id="rev_1",
        active_epoch=1,
    )
    rev_pruned = KnowledgeIndexRevision(id="rev_4", binding_id=binding.id, status="pruned", revision_no=4)

    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeBinding, "bnd_1"): binding,
        (KnowledgeIndexRevision, "rev_4"): rev_pruned,
    }.get((model, obj_id))
    session.execute.return_value = _execute_result(scalar=binding)

    with pytest.raises(AppException) as exc_info:
        await index_build_service.rollback_index_revision(
            db=session,
            binding_id=binding.id,
            target_index_revision_id="rev_4",
            expected_epoch=1,
        )

    assert exc_info.value.code == "REVISION_ALREADY_PRUNED"
    assert exc_info.value.status_code == 400


# ==============================================================================
# 7. REST API Endpoint POST /knowledge/collections/{id}/gc
# ==============================================================================
@pytest.mark.asyncio
async def test_gc_api_endpoint() -> None:
    """Verifies REST API endpoint POST /knowledge/collections/{id}/gc."""
    session = _fresh_session()

    async def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_current_actor] = _mock_admin_actor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(
            knowledge_service,
            "collect_garbage",
            return_value=GarbageCollectionReport(
                collection_id="col_api_test",
                dry_run=False,
                keep_revisions=2,
                total_bindings_scanned=3,
                pruned_revisions_count=2,
                pruned_revision_ids=["rev_old_1", "rev_old_2"],
                pruned_chunks_count=10,
                pruned_facts_count=2,
                pruned_points_count=10,
                message="Thực thi hoàn tất",
                executed_at=utcnow(),
            ),
        ):
            res = await client.post(
                f"{settings.API_PREFIX}/knowledge/collections/col_api_test/gc",
                json={"keep_revisions": 2, "dry_run": False},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["collection_id"] == "col_api_test"
            assert data["pruned_revisions_count"] == 2
            assert "executed_at" in data

    app.dependency_overrides.clear()


# ==============================================================================
# 8. REST API Endpoints GET & PUT /knowledge/collections/{id}/canary/policy
# ==============================================================================
@pytest.mark.asyncio
async def test_canary_policy_get_and_update_api() -> None:
    """Verifies REST API endpoints GET and PUT /knowledge/collections/{id}/canary/policy."""
    session = _fresh_session()

    async def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_current_actor] = _mock_admin_actor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with (
            patch.object(
                knowledge_service,
                "get_collection_canary_policy",
                return_value=CanaryPolicyResponse(
                    collection_id="col_canary_test",
                    read_mode="system",
                    system_read_mode="revisioned",
                    effective_read_mode="revisioned",
                    retention_revisions=2,
                    last_gc_report=None,
                ),
            ),
            patch.object(
                knowledge_service,
                "update_collection_canary_policy",
                return_value=CanaryPolicyResponse(
                    collection_id="col_canary_test",
                    read_mode="shadow",
                    system_read_mode="revisioned",
                    effective_read_mode="shadow",
                    retention_revisions=4,
                    last_gc_report=None,
                ),
            ),
        ):
            # 1. GET policy
            res_get = await client.get(
                f"{settings.API_PREFIX}/knowledge/collections/col_canary_test/canary/policy"
            )
            assert res_get.status_code == 200
            get_data = res_get.json()
            assert get_data["collection_id"] == "col_canary_test"
            assert get_data["read_mode"] == "system"
            assert get_data["effective_read_mode"] == "revisioned"

            # 2. PUT policy
            res_put = await client.put(
                f"{settings.API_PREFIX}/knowledge/collections/col_canary_test/canary/policy",
                json={"read_mode": "shadow", "retention_revisions": 4},
            )
            assert res_put.status_code == 200
            put_data = res_put.json()
            assert put_data["read_mode"] == "shadow"
            assert put_data["effective_read_mode"] == "shadow"
            assert put_data["retention_revisions"] == 4

    app.dependency_overrides.clear()


# ==============================================================================
# 9. Dynamic Per-Collection Read Mode Resolution in HybridRetriever
# ==============================================================================
@pytest.mark.asyncio
async def test_dynamic_read_mode_resolution_per_collection() -> None:
    """Verifies that HybridRetriever dynamically resolves effective_read_mode from collection metadata."""
    session = _fresh_session()
    col_shadow = KnowledgeCollection(
        id="col_dyn_shadow",
        name="Dynamic Shadow Collection",
        collection_metadata={"canary_policy": {"read_mode": "shadow", "retention_revisions": 3}},
    )
    col_default = KnowledgeCollection(
        id="col_dyn_default",
        name="Dynamic Default Collection",
        collection_metadata={},
    )

    session.get.side_effect = lambda model, obj_id: {
        (KnowledgeCollection, "col_dyn_shadow"): col_shadow,
        (KnowledgeCollection, "col_dyn_default"): col_default,
    }.get((model, obj_id))

    chunk_active = KnowledgeChunk(
        id="chunk_dyn_1",
        collection_id="col_dyn_shadow",
        document_id="doc_1",
        binding_id="bnd_1",
        index_revision_id="rev_active",
        content="Quy định tuyển sinh động 2026",
    )

    res_weighted = _execute_result(scalars_list=[chunk_active])
    res_uni = _execute_result(scalars_list=[])
    res_doc_titles = MagicMock()
    res_doc_titles.all = MagicMock(return_value=[("doc_1", "Quy định 2026")])

    session.execute.side_effect = [
        res_weighted, res_uni, res_doc_titles,
        res_weighted, res_uni, res_doc_titles,
    ]

    snapshot = RetrievalSnapshot(
        snapshot_id="snap_dyn_1",
        collection_id="col_dyn_shadow",
        collection_epoch=1,
        binding_revisions={"bnd_1": "rev_active"},
    )

    # 1. Collection with canary_policy: read_mode='shadow'
    results_shadow = await hybrid_retriever.search_sparse_fts(
        db=session,
        collection_id="col_dyn_shadow",
        query="tuyển sinh 2026",
        top_k=5,
        snapshot=snapshot,
    )
    assert len(results_shadow) == 1
    # Verify session.get was called with col_dyn_shadow
    session.get.assert_any_call(KnowledgeCollection, "col_dyn_shadow")

    # 2. Collection with default policy -> falls back to system settings.RAG_REVISION_READ_MODE
    results_default = await hybrid_retriever.search_sparse_fts(
        db=session,
        collection_id="col_dyn_default",
        query="tuyển sinh 2026",
        top_k=5,
        snapshot=snapshot,
    )
    assert len(results_default) == 1
    session.get.assert_any_call(KnowledgeCollection, "col_dyn_default")
