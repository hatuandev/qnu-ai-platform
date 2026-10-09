"""Resilience, Concurrency, and Cancellation Tests for Publishing V2:
- Atomic CAS Concurrency for Collection Index Epoch (SQL RETURNING index_epoch)
- Strict ModelOps Dynamic Vector Dimension Resolution (No Silent 1024 Default)
- Support for Custom Model Dimensions (!= 1024)
- Cooperative Ingestion/Build Cancellation with Qdrant Partial Points Cleanup
- Cooperative GC Pruning Cancellation Checkpoints
- Worker Task Pre-Run Cancellation Guard (No Status Flip to Running)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.services.gc_service import KnowledgeArtifactGCService
from app.modules.knowledge.services.index_build_service import IndexBuildService
from app.modules.knowledge.services.scope_helper import (
    bump_collection_index_epoch,
    get_scoped_binding,
)
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.services.model_catalog_service import model_catalog_service
from app.workers.tasks import task_document_revision_parse, task_knowledge_index_build


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    result.scalar = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_list or [])
    scalars.first = MagicMock(return_value=scalar)
    result.scalars = MagicMock(return_value=scalars)
    result.all = MagicMock(return_value=scalars_list or [])
    result.first = MagicMock(return_value=scalar)
    result.rowcount = len(scalars_list or [])
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


# ==============================================================================
# 1. Atomic CAS Concurrency for Collection Index Epoch
# ==============================================================================


@pytest.mark.asyncio
async def test_bump_collection_index_epoch_atomic_success():
    """bump_collection_index_epoch executes SQL UPDATE ... RETURNING index_epoch atomically."""
    db = _fresh_session()
    db.execute.return_value = _execute_result(scalar=6)

    new_epoch = await bump_collection_index_epoch(db, "col_test_123")

    assert new_epoch == 6
    db.execute.assert_called_once()
    executed_stmt = db.execute.call_args[0][0]
    assert "knowledge_collections" in str(executed_stmt)


@pytest.mark.asyncio
async def test_bump_collection_index_epoch_missing_collection_raises_404():
    """If collection does not exist, bump_collection_index_epoch raises EntityNotFoundError."""
    db = _fresh_session()
    db.execute.return_value = _execute_result(scalar=None)

    with pytest.raises(EntityNotFoundError) as exc_info:
        await bump_collection_index_epoch(db, "col_nonexistent")

    assert "col_nonexistent" in str(exc_info.value)


@pytest.mark.asyncio
async def test_bump_collection_index_epoch_rejects_non_integer_returning_value():
    """Epoch allocation must never reconstruct a value outside UPDATE ... RETURNING."""
    db = _fresh_session()
    db.execute.return_value = _execute_result(scalar="6")

    with pytest.raises(AppException) as exc_info:
        await bump_collection_index_epoch(db, "col_invalid_epoch")

    assert exc_info.value.code == "INVALID_INDEX_EPOCH"
    db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_scoped_binding_for_update_never_uses_unlocked_identity_lookup():
    """Internal calls without actor must still acquire the requested row lock."""
    db = _fresh_session()
    binding = KnowledgeBinding(
        id="bnd_locked",
        collection_id="col_1",
        repository_document_id="doc_1",
        source_revision_id="rev_1",
    )
    db.execute.return_value = _execute_result(scalar=binding)

    result = await get_scoped_binding(db, binding.id, for_update=True)

    assert result is binding
    db.get.assert_not_awaited()
    assert "FOR UPDATE" in str(db.execute.await_args.args[0])


# ==============================================================================
# 2. Strict Dynamic Vector Dimension Resolution from ModelOps DB
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_vector_dimension_from_modelops_db_custom_dimension():
    """Vector dimension is resolved strictly from ModelOps DB (e.g. 768 for custom model)."""
    service = IndexBuildService()
    db = _fresh_session()

    col = KnowledgeCollection(
        id="col_custom_dim",
        tenant_id="tenant_qnu",
        workspace_id="ws_qnu",
        index_epoch=1,
        collection_metadata={
            "data_processing": {
                "embedding_provider_id": "prov_ollama_local",
                "embedding_model": "nomic-embed-text",
            }
        },
    )

    prov_cfg = ModelProviderConfig(
        id="prov_ollama_local",
        name="Ollama Local",
        provider_type="custom",
        extra_config={
            "model_specs": {
                "nomic-embed-text": {
                    "dimension": 768,
                }
            }
        },
    )

    # In get_or_create_vector_generation:
    # 1. prov_stmt (select ModelProviderConfig) -> prov_cfg
    # 2. lock collection (select KnowledgeCollection.id ... with_for_update) -> "col_custom_dim"
    # 3. active_stmt (select KnowledgeVectorGeneration) -> None
    # 4. max_epoch_stmt (select coalesce(max(...))) -> 0
    db.execute.side_effect = [
        _execute_result(scalar=prov_cfg),          # provider config
        _execute_result(scalar="col_custom_dim"),  # lock collection
        _execute_result(scalar=None),              # no active gen
        _execute_result(scalar=0),                 # max epoch
    ]

    with patch("app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults") as mock_defaults:
        mock_defaults.return_value = MagicMock(
            default_embedding_provider_id="prov_ollama_local",
            default_embedding_model="nomic-embed-text",
        )
        gen = await service.get_or_create_vector_generation(db, col)

    assert gen.embedding_dimension == 768
    assert gen.embedding_model == "nomic-embed-text"
    assert gen.provider_id == "prov_ollama_local"
    assert gen.status == "active"


@pytest.mark.asyncio
async def test_resolve_vector_dimension_missing_raises_fail_fast():
    """If neither ModelOps DB nor metadata configures dimension, must raise EMBEDDING_DIMENSION_NOT_CONFIGURED (no silent fallback)."""
    service = IndexBuildService()
    db = _fresh_session()

    col = KnowledgeCollection(
        id="col_no_dim",
        tenant_id="tenant_qnu",
        workspace_id="ws_qnu",
        index_epoch=1,
        collection_metadata={
            "data_processing": {
                "embedding_provider_id": "prov_empty",
                "embedding_model": "unknown-embed-model",
            }
        },
    )

    prov_cfg = ModelProviderConfig(
        id="prov_empty",
        name="Empty Provider",
        provider_type="custom",
        extra_config={},  # No dimension configured
    )

    # 1. prov_stmt -> prov_cfg with no dimension
    db.execute.side_effect = [
        _execute_result(scalar=prov_cfg),
    ]

    with patch("app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults") as mock_defaults:
        mock_defaults.return_value = MagicMock(
            default_embedding_provider_id="prov_empty",
            default_embedding_model="unknown-embed-model",
        )
        with pytest.raises(AppException) as exc_info:
            await service.get_or_create_vector_generation(db, col)

    assert exc_info.value.code == "EMBEDDING_DIMENSION_NOT_CONFIGURED"
    assert exc_info.value.status_code == 400
    assert "unknown-embed-model" in str(exc_info.value)


@pytest.mark.asyncio
async def test_resolve_vector_dimension_rejects_stale_collection_metadata():
    """A collection snapshot cannot silently override the current ModelOps vector space."""
    db = _fresh_session()
    provider = ModelProviderConfig(
        id="prov_embed",
        name="Embedding Provider",
        provider_type="custom",
        model_name="embed-v1",
        is_active=True,
        extra_config={"model_specs": {"embed-v1": {"dimension": 768}}},
    )
    db.execute.return_value = _execute_result(scalar=provider)

    with pytest.raises(AppException) as exc_info:
        await model_catalog_service.resolve_embedding_dimension(
            db,
            provider.id,
            "embed-v1",
            metadata_dimension=1024,
        )

    assert exc_info.value.code == "EMBEDDING_DIMENSION_MISMATCH"
    assert exc_info.value.status_code == 409


# ==============================================================================
# 3. Cooperative Cancellation & Side-effect Prevention
# ==============================================================================


@pytest.mark.asyncio
async def test_build_staging_index_cooperative_cancellation_pre_check():
    """If job is already cancelled before starting, build_staging_index aborts immediately with 409."""
    service = IndexBuildService()
    db = _fresh_session()
    db.execute.return_value = _execute_result(scalar=None)

    with patch("app.modules.jobs.service.is_job_cancelled", new=AsyncMock(return_value=True)), \
         pytest.raises(AppException) as exc_info:
        await service.build_staging_index(
            db,
            binding_id="bind_1",
            job_id="job_pre_cancelled",
        )

    assert exc_info.value.code == "JOB_CANCELLED"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_build_staging_index_cancellation_cleans_up_qdrant_points():
    """If cancellation occurs after uploading points, cleanup_index_revision_points is triggered."""
    service = IndexBuildService()
    db = _fresh_session()
    db.execute.return_value = _execute_result(scalar=None)

    idx_rev = KnowledgeIndexRevision(
        id="rev_test_cleanup",
        binding_id="bind_1",
        status="building",
        point_ids=["pt_1", "pt_2"],
    )

    with patch("app.modules.jobs.service.is_job_cancelled", new=AsyncMock(return_value=True)), \
         patch("app.modules.rag.vector_indexer.vector_indexer.client.delete", new=AsyncMock()) as mock_delete:

        is_cancelled = await service._check_job_cancelled(
            db,
            job_id="job_cancelled_midway",
            idx_rev=idx_rev,
            col_id="col_123",
            point_ids=["pt_1", "pt_2"],
        )

    assert is_cancelled is True
    assert idx_rev.status == "failed"
    assert idx_rev.failure_code == "JOB_CANCELLED"
    mock_delete.assert_called_once()


# ==============================================================================
# 4. Cooperative GC Pruning Cancellation Checkpoints
# ==============================================================================


@pytest.mark.asyncio
async def test_gc_service_cancellation_aborts_pruning():
    """KnowledgeArtifactGCService must stop pruning immediately when is_job_cancelled is True."""
    service = KnowledgeArtifactGCService()
    db = _fresh_session()

    col = KnowledgeCollection(
        id="col_gc_cancel",
        tenant_id="tenant_qnu",
        workspace_id="ws_qnu",
        index_epoch=3,
    )

    db.execute.side_effect = [
        _execute_result(scalar=col),  # get collection
    ]

    with patch("app.modules.jobs.service.is_job_cancelled", new=AsyncMock(return_value=True)), \
         pytest.raises(AppException) as exc_info:
        await service.collect_garbage(
            db,
            collection_id="col_gc_cancel",
            keep_revisions=2,
            job_id="job_gc_cancel_1",
        )

    assert exc_info.value.code == "JOB_CANCELLED"
    assert exc_info.value.status_code == 409


# ==============================================================================
# 5. Worker Task Pre-Run Cancellation Guard
# ==============================================================================


@pytest.mark.asyncio
async def test_worker_tasks_prerun_cancellation_guard():
    """Worker task must exit before running and never mutate state if already cancelled."""
    db = _fresh_session()
    cancelled_job = JobRecord(
        id="job_prerun_cancelled",
        status="cancelled",
        cancel_requested=True,
        payload={"revision_id": "rev_x", "binding_id": "bind_x", "source_revision_id": "rev_src"},
    )
    db.execute.return_value = _execute_result(scalar=cancelled_job)

    with patch("app.workers.tasks.is_job_cancelled", new=AsyncMock(return_value=True)), \
         patch("app.workers.tasks.AsyncSessionFactory", return_value=AsyncMock(__aenter__=AsyncMock(return_value=db), __aexit__=AsyncMock())):
        res_parse = await task_document_revision_parse({}, "job_prerun_cancelled")
        assert res_parse["status"] == "cancelled"

        res_build = await task_knowledge_index_build({}, "job_prerun_cancelled")
        assert res_build["status"] == "cancelled"
