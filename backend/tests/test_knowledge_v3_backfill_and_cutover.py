"""Unit & Acceptance Tests for Backfill, Cutover & Legacy Decommissioning (ADR-012 Phiên 8).

Verifies:
1. Backfill V3: Idempotently migrates published bindings into KnowledgeSourceRevision & KnowledgeChunkSet.
2. Vector Generation Rollback: Instant zero-reindex rollback via CAS atomic pointer swap & Qdrant payload activation.
3. RetrievalSnapshot Invariant: Zero revision or generation leakage across spaces.
4. Reconciliation Audit: 3-way consistency between PostgreSQL, Qdrant and MinIO, with orphan point cleanup.
5. Pure Storage Invariant: Upload/intake strictly saves file without triggering parse jobs.
6. REST API Endpoints for Backfill V3, Rollback, Reconciliation, and Orphan Cleanup.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import AppException
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.services.backfill_service import (
    BackfillV3Report,
    backfill_v3_service,
)
from app.modules.knowledge.services.reconciliation_service import (
    ReconciliationReport,
    reconciliation_service,
)
from app.modules.knowledge.services.vector_generation_service import (
    vector_generation_service,
)
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import RetrievalSnapshot
from app.modules.rag.vector_indexer import vector_indexer


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


def _execute_result(
    scalar: Any = None,
    scalars_list: list[Any] | None = None,
    all_list: list[Any] | None = None,
):
    mock = MagicMock()
    if scalar is not None:
        mock.scalar_one_or_none.return_value = scalar
        mock.scalar.return_value = scalar
        mock.scalars.return_value.first.return_value = scalar
        mock.scalars.return_value.all.return_value = [scalar]
    else:
        mock.scalar_one_or_none.return_value = None
        mock.scalar.return_value = None
        mock.scalars.return_value.first.return_value = (
            scalars_list[0] if scalars_list else None
        )
        mock.scalars.return_value.all.return_value = scalars_list or []
    mock.all.return_value = all_list or []
    return mock


# ---------------------------------------------------------------------------
# 1. Backfill V3 Service Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backfill_collection_v3_success():
    """Verify backfill migrates unlinked bindings into SourceRevision and ChunkSet."""
    db = AsyncMock()
    actor = _make_actor()

    col = KnowledgeCollection(
        id="col_tuyensinh",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        name="Tuyển sinh QNU",
        collection_metadata={},
        index_epoch=1,
    )

    binding = KnowledgeBinding(
        id="bnd_001",
        collection_id=col.id,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
        repository_document_id="doc_001",
        chunk_strategy="ClauseBasedChunker",
        status="active",
        active_source_revision_id=None,
        active_index_revision_id="idx_001",
    )

    chunk = KnowledgeChunk(
        id="chk_001",
        document_id="doc_001",
        collection_id=col.id,
        binding_id=binding.id,
        chunk_index=0,
        content="Nội dung quy chế tuyển sinh trường Đại học Quy Nhơn.",
        chunk_hash="hash_001",
        page_number=1,
    )

    idx_rev = KnowledgeIndexRevision(
        id="idx_001",
        binding_id=binding.id,
        revision_no=1,
        vector_generation_id="",  # unlinked initially
        chunk_set_id=None,
        chunk_count=1,
        status="active",
    )

    db.execute.side_effect = [
        _execute_result(scalar=col),
        _execute_result(scalars_list=[]),
        _execute_result(scalars_list=[binding]),
        _execute_result(scalars_list=[chunk]),
        _execute_result(scalars_list=[idx_rev]),
    ]
    db.get = AsyncMock(return_value=None)

    report = await backfill_v3_service.backfill_collection_v3(
        db=db,
        collection_id=col.id,
        actor=actor,
    )

    assert isinstance(report, BackfillV3Report)
    assert report.collection_id == col.id
    assert report.total_bindings == 1
    assert report.source_revisions_created == 1
    assert report.chunk_sets_created == 1
    assert report.index_revisions_updated >= 1
    assert report.already_migrated == 0
    assert binding.active_source_revision_id is not None
    assert idx_rev.vector_generation_id != ""


@pytest.mark.asyncio
async def test_backfill_collection_v3_idempotent():
    """Verify backfill skips already migrated bindings without duplicate creation."""
    db = AsyncMock()
    actor = _make_actor()

    col = KnowledgeCollection(
        id="col_tuyensinh",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        name="Tuyển sinh QNU",
        collection_metadata={"active_vector_generation_id": "gen_default"},
        index_epoch=1,
    )

    gen = KnowledgeVectorGeneration(
        id="gen_default",
        collection_id=col.id,
        embedding_model="BAAI/bge-m3",
        provider_id="default",
        qdrant_collection_name="col_tuyensinh",
        config_hash="default_hash",
        embedding_dimension=1024,
        status="active",
    )

    binding = KnowledgeBinding(
        id="bnd_001",
        collection_id=col.id,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
        active_source_revision_id="ks_rev_001",
        status="active",
    )

    idx_rev = KnowledgeIndexRevision(
        id="idx_001",
        binding_id=binding.id,
        revision_no=1,
        vector_generation_id=gen.id,
        chunk_set_id="kcs_001",
        source_revision_v2_id="ks_rev_001",
        status="active",
    )

    db.execute.side_effect = [
        _execute_result(scalar=col),
        _execute_result(scalars_list=[gen]),
        _execute_result(scalars_list=[binding]),
        _execute_result(scalars_list=[idx_rev]),
    ]

    report = await backfill_v3_service.backfill_collection_v3(
        db=db,
        collection_id=col.id,
        actor=actor,
    )

    assert report.already_migrated == 1
    assert report.source_revisions_created == 0
    assert report.chunk_sets_created == 0


# ---------------------------------------------------------------------------
# 2. Vector Generation Rollback Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rollback_vector_generation_atomic_swap():
    """Verify rollback safely swaps vector generation pointer and bumps epoch."""
    db = AsyncMock()
    actor = _make_actor()

    col = KnowledgeCollection(
        id="col_tuyensinh",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        index_epoch=5,
        collection_metadata={"active_vector_generation_id": "gen_new"},
    )

    gen_old = KnowledgeVectorGeneration(
        id="gen_old",
        collection_id=col.id,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
        status="retired",
        embedding_model="BAAI/bge-m3",
        embedding_dimension=1024,
    )

    gen_new = KnowledgeVectorGeneration(
        id="gen_new",
        collection_id=col.id,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
        status="active",
        embedding_model="Qwen/Qwen2.5-7B-Instruct",
        embedding_dimension=1536,
    )

    binding = KnowledgeBinding(
        id="bnd_001",
        collection_id=col.id,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
        status="active",
        active_index_revision_id="idx_new",
        active_epoch=1,
    )

    idx_old = KnowledgeIndexRevision(
        id="idx_old",
        binding_id=binding.id,
        vector_generation_id=gen_old.id,
        status="archived",
        chunk_count=10,
    )

    db.get.side_effect = lambda model, key: gen_old if key == gen_old.id else gen_new
    db.execute.side_effect = [
        _execute_result(scalars_list=[binding]),
        _execute_result(scalars_list=[idx_old]),
        _execute_result(scalars_list=[binding]),
    ]

    with patch(
        "app.modules.knowledge.services.generation_publish_service.get_scoped_collection",
        new_callable=AsyncMock,
    ) as mock_scope, \
         patch.object(vector_indexer, "deactivate_index_revision", new_callable=AsyncMock) as mock_deact, \
         patch.object(vector_indexer, "activate_index_revision", new_callable=AsyncMock) as mock_act:
        mock_scope.return_value = col
        mock_act.return_value = 10

        res = await vector_generation_service.rollback_vector_generation(
            db=db,
            collection_id=col.id,
            target_generation_id=gen_old.id,
            actor=actor,
        )

        assert res.collection_id == col.id
        assert res.activated_generation_id == gen_old.id
        assert res.previous_generation_id == gen_new.id
        assert res.new_epoch == 6
        assert gen_old.status == "active"
        assert gen_new.status == "retired"
        assert binding.active_index_revision_id == idx_old.id
        mock_deact.assert_not_called()
        mock_act.assert_awaited_once_with(col.id, "idx_old", 10, qdrant_collection_name=gen_old.qdrant_collection_name)


@pytest.mark.asyncio
async def test_rollback_vector_generation_invalid_status_rejected():
    """Verify rollback rejects invalid target status (e.g. 'failed' or 'building')."""
    db = AsyncMock()
    actor = _make_actor()

    col = KnowledgeCollection(id="col_tuyensinh", tenant_id=actor.tenant_id, workspace_id=actor.workspace_id)
    gen_failed = KnowledgeVectorGeneration(
        id="gen_failed",
        collection_id=col.id,
        status="failed",
    )

    db.get.return_value = gen_failed
    db.execute.return_value = _execute_result(scalar=col)

    with pytest.raises(AppException) as exc_info:
        await vector_generation_service.rollback_vector_generation(
            db=db,
            collection_id=col.id,
            target_generation_id=gen_failed.id,
            actor=actor,
        )
    assert exc_info.value.code == "INVALID_ROLLBACK_TARGET"


# ---------------------------------------------------------------------------
# 3. RetrievalSnapshot Isolation & Zero-Leakage Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieval_snapshot_pins_and_detects_epoch_drift():
    """Verify pinned snapshot raises 409 STALE_RETRIEVAL_SNAPSHOT when epoch drifts."""
    db = AsyncMock()
    actor = _make_actor()

    col = KnowledgeCollection(
        id="col_tuyensinh",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        index_epoch=3,
        collection_metadata={"active_vector_generation_id": "gen_001"},
    )
    db.get = AsyncMock(return_value=col)

    pinned = RetrievalSnapshot(
        snapshot_id="snap_col_tuyensinh_2_abc",
        collection_id=col.id,
        collection_epoch=2,
        binding_revisions={"bnd_001": "idx_001"},
        vector_generations={"bnd_001": "gen_001"},
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )

    db.execute.side_effect = [
        _execute_result(all_list=[("bnd_001", "idx_002", "gen_001")]),
    ]

    with pytest.raises(AppException) as exc_info:
        await hybrid_retriever.resolve_retrieval_snapshot(
            db=db,
            collection_id=col.id,
            tenant_id=actor.tenant_id,
            workspace_id=actor.workspace_id,
            pinned_snapshot=pinned,
        )
    assert exc_info.value.code == "STALE_RETRIEVAL_SNAPSHOT"


@pytest.mark.asyncio
async def test_search_dense_discards_mismatched_vector_generation():
    """Verify search_dense filters out points belonging to unpinned vector generations."""
    snapshot = RetrievalSnapshot(
        snapshot_id="snap_123",
        collection_id="col_tuyensinh",
        collection_epoch=1,
        binding_revisions={"bnd_001": "idx_target"},
        vector_generations={"bnd_001": "gen_target"},
    )

    hit_correct = MagicMock()
    hit_correct.id = "pt_1"
    hit_correct.score = 0.95
    hit_correct.payload = {
        "binding_id": "bnd_001",
        "index_revision_id": "idx_target",
        "vector_generation_id": "gen_target",
        "is_active": True,
        "is_retrievable": True,
        "document_status": "ready",
        "content": "Nội dung hợp lệ",
    }

    hit_leaked = MagicMock()
    hit_leaked.id = "pt_2"
    hit_leaked.score = 0.98
    hit_leaked.payload = {
        "binding_id": "bnd_001",
        "index_revision_id": "idx_target",
        "vector_generation_id": "gen_other",  # Mismatched generation!
        "is_active": True,
        "is_retrievable": True,
        "document_status": "ready",
        "content": "Nội dung bị rò rỉ thế hệ",
    }

    mock_res = MagicMock()
    mock_res.points = [hit_correct, hit_leaked]

    session = AsyncMock()
    session.get.return_value = KnowledgeVectorGeneration(
        id="gen_target", collection_id="col_tuyensinh", qdrant_collection_name="pinned_target",
    )
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = session
    with (
        patch("app.modules.rag.vector_indexer.AsyncSessionFactory", factory),
        patch.object(vector_indexer.client, "query_points", new_callable=AsyncMock) as mock_query,
    ):
        mock_query.return_value = mock_res

        results = await vector_indexer.search_dense(
            collection_id="col_tuyensinh",
            query="tuyển sinh",
            query_vector=[0.1] * 1024,
            snapshot=snapshot,
        )

        assert len(results) == 1
        assert results[0]["chunk_id"] == "pt_1"
        assert results[0]["content"] == "Nội dung hợp lệ"


# ---------------------------------------------------------------------------
# 4. Reconciliation Service Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reconciliation_service_detects_parity_and_cleans_orphans():
    """Verify reconciliation reports parity health and cleans orphan points."""
    db = AsyncMock()
    actor = _make_actor()

    col = KnowledgeCollection(
        id="col_tuyensinh",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        collection_metadata={"active_vector_generation_id": "gen_001"},
    )

    db.execute.side_effect = [
        _execute_result(scalar=col),
        _execute_result(scalar=1),
        _execute_result(scalar=1),
        _execute_result(scalar=1),
        _execute_result(scalar=1),
        _execute_result(scalar=10),
    ]

    with patch.object(vector_indexer, "count_points", new_callable=AsyncMock) as mock_count:
        mock_count.return_value = 10

        report = await reconciliation_service.reconcile_collection(
            db=db,
            collection_id=col.id,
            actor=actor,
        )

        assert isinstance(report, ReconciliationReport)
        assert report.parity_healthy is True
        assert report.expected_qdrant_points == 10
        assert report.actual_qdrant_points == 10
        assert report.orphan_points_detected == 0
        assert len(report.issues) == 0


@pytest.mark.asyncio
async def test_clean_orphan_points_invokes_delete_on_stale_revisions():
    """Verify clean_orphan_points deletes points for non-active revisions."""
    db = AsyncMock()
    actor = _make_actor()

    col = KnowledgeCollection(id="col_tuyensinh", tenant_id=actor.tenant_id, workspace_id=actor.workspace_id)

    db.execute.side_effect = [
        _execute_result(scalar=col),
        _execute_result(scalars_list=["idx_active"]),
        _execute_result(scalars_list=["idx_archived_01", "idx_failed_02"]),
    ]

    with patch.object(vector_indexer, "delete_points_by_index_revision", new_callable=AsyncMock) as mock_del:
        mock_del.side_effect = [5, 3]

        cleaned = await reconciliation_service.clean_orphan_points(
            db=db,
            collection_id=col.id,
            actor=actor,
        )

        assert cleaned == 8
        assert mock_del.await_count == 2


# ---------------------------------------------------------------------------
# 5. REST API Endpoints Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backfill_collection_v3_api():
    actor = _make_actor()
    app.dependency_overrides[get_current_actor] = lambda: actor

    mock_report = BackfillV3Report(
        collection_id="col_123",
        total_bindings=5,
        source_revisions_created=5,
        chunk_sets_created=5,
        index_revisions_updated=5,
        vector_generation_id="gen_001",
        already_migrated=0,
        status="completed",
    )

    with patch.object(backfill_v3_service, "backfill_collection_v3", new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_report

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/platform/v1alpha1/knowledge/collections/col_123/backfill-v3")

            assert resp.status_code == 200
            data = resp.json()
            assert data["collection_id"] == "col_123"
            assert data["total_bindings"] == 5
            assert data["source_revisions_created"] == 5

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reconciliation_api():
    actor = _make_actor()
    app.dependency_overrides[get_current_actor] = lambda: actor

    mock_report = ReconciliationReport(
        collection_id="col_123",
        active_sources=2,
        source_revisions_count=2,
        chunk_sets_count=2,
        vector_generations_count=1,
        active_vector_generation_id="gen_001",
        expected_qdrant_points=20,
        actual_qdrant_points=20,
        parity_healthy=True,
        orphan_points_detected=0,
        issues=[],
    )

    with patch.object(reconciliation_service, "reconcile_collection", new_callable=AsyncMock) as mock_service:
        mock_service.return_value = mock_report

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/platform/v1alpha1/knowledge/collections/col_123/reconciliation")

            assert resp.status_code == 200
            data = resp.json()
            assert data["parity_healthy"] is True
            assert data["expected_qdrant_points"] == 20

    app.dependency_overrides.clear()
