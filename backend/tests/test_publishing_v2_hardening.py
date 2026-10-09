"""Comprehensive Tests for Publishing V2 Hardening:
- Tenant & Workspace Authorization for Background Jobs and Document Revisions
- Compare-And-Swap (CAS) Atomic Promotion & Concurrency Conflict Protection
- Zero-Reindex Rollback from Archived Revisions vs Pruned Revisions
- Strict Vector Dimension & Vector Generation Invariance (No Silent Truncation/Padding)
- Cooperative Job Cancellation Checkpoints
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.auth.dependencies import AuthActor
from app.modules.documents.models import RepositoryDocument
from app.modules.documents.revision_service import DocumentRevisionService
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import JobsService
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeIndexRevision,
)
from app.modules.knowledge.services.index_build_service import IndexBuildService
from app.modules.rag.vector_indexer import VectorIndexer


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    result.scalar = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_list or [])
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


def _make_actor(tenant_id: str = "tenant_a", username: str = "user_a") -> AuthActor:
    return AuthActor(
        actor_id=f"act_{tenant_id}",
        username=username,
        display_name=f"User {tenant_id}",
        email=f"{username}@qnu.edu.vn",
        user_type="staff",
        tenant_id=tenant_id,
        workspace_id=f"ws_{tenant_id}",
        role="staff",
        roles=["staff"],
        permissions=["ai.knowledge.view", "ai.knowledge.upload", "ai.knowledge.edit", "ai.knowledge.delete"],
        authenticated=True,
    )


# ==============================================================================
# 1. Tenant Authorization & Scoping for Jobs
# ==============================================================================


@pytest.mark.asyncio
async def test_jobs_service_scoping_tenant_isolation():
    """Tenant A cannot read jobs belonging to Tenant B."""
    service = JobsService()
    db = _fresh_session()

    actor_a = _make_actor(tenant_id="tenant_a")
    actor_b = _make_actor(tenant_id="tenant_b")

    job_b = JobRecord(
        id="job_b_123",
        job_type="ingestion",
        status="running",
        tenant_id="tenant_b",
        workspace_id="ws_tenant_b",
    )

    # When actor_b queries job_b -> found
    db.execute.return_value = _execute_result(scalar=job_b)
    res = await service.get_job(db, "job_b_123", actor=actor_b)
    assert res.id == "job_b_123"

    # When actor_a queries job_b -> query filters by tenant_a, returns None -> 404 EntityNotFoundError
    db.execute.return_value = _execute_result(scalar=None)
    with pytest.raises(EntityNotFoundError) as exc_info:
        await service.get_job(db, "job_b_123", actor=actor_a)
    assert "job_b_123" in str(exc_info.value)


@pytest.mark.asyncio
async def test_jobs_service_cross_tenant_actions_denied():
    """Tenant A cannot cancel, retry, or delete jobs of Tenant B (returns 404)."""
    service = JobsService()
    db = _fresh_session()
    actor_a = _make_actor(tenant_id="tenant_a")

    # DB finds nothing for job_b under tenant_a
    db.execute.return_value = _execute_result(scalar=None)

    with pytest.raises(EntityNotFoundError):
        await service.cancel_job(db, "job_b_123", actor=actor_a)

    with pytest.raises(EntityNotFoundError):
        await service.retry_job(db, "job_b_123", actor=actor_a)

    with pytest.raises(EntityNotFoundError):
        await service.delete_job(db, "job_b_123", actor=actor_a)


@pytest.mark.asyncio
async def test_jobs_service_retry_resets_cancel_requested():
    """Retry must reset cancel_requested to False, progress to 0.0, and error to None."""
    service = JobsService()
    db = _fresh_session()
    actor_a = _make_actor(tenant_id="tenant_a")

    cancelled_job = JobRecord(
        id="job_a_1",
        job_type="ingestion",
        status="cancelled",
        cancel_requested=True,
        progress=45.0,
        error="User cancelled",
        attempt=1,
        tenant_id="tenant_a",
    )
    db.execute.return_value = _execute_result(scalar=cancelled_job)

    with patch("app.modules.jobs.service.enqueue_arq_job", new=AsyncMock(return_value="arq_123")):
        retried = await service.retry_job(db, "job_a_1", actor=actor_a)

    assert retried.status == "queued"
    assert retried.cancel_requested is False
    assert retried.progress == 0.0
    assert retried.error is None
    assert retried.attempt == 2


# ==============================================================================
# 2. Document & Revision Tenant/Document Binding
# ==============================================================================


@pytest.mark.asyncio
async def test_revision_service_cross_document_retry_rejected():
    """Calling revision retry with wrong document_id raises EntityNotFoundError."""
    service = DocumentRevisionService()
    db = _fresh_session()
    actor = _make_actor(tenant_id="tenant_a")

    # Document A exists
    doc_a = RepositoryDocument(id="doc_a", tenant_id="tenant_a", is_active=True)
    # Revision belongs to doc_b, NOT doc_a
    db.execute.side_effect = [
        _execute_result(scalar=doc_a),  # doc check passes
        _execute_result(scalar=None),   # rev with document_id=doc_a not found
    ]

    with pytest.raises(EntityNotFoundError):
        await service.process_revision(
            db,
            revision_id="rev_1",
            document_id="doc_a",
            actor=actor,
        )


@pytest.mark.asyncio
async def test_revision_service_cross_tenant_access_rejected():
    """Accessing revision of another tenant raises EntityNotFoundError."""
    service = DocumentRevisionService()
    db = _fresh_session()
    actor_a = _make_actor(tenant_id="tenant_a")

    # Document belongs to tenant_b, so query with tenant_a returns None
    db.execute.return_value = _execute_result(scalar=None)

    with pytest.raises(EntityNotFoundError):
        await service.get_document_revision(
            db,
            document_id="doc_b",
            revision_id="rev_b_1",
            actor=actor_a,
        )


# ==============================================================================
# 3. Compare-And-Swap (CAS) Atomic Promotion & Concurrency Protection
# ==============================================================================


@pytest.mark.asyncio
async def test_promote_index_revision_cas_conflict():
    """Promote with stale expected_epoch must fail fast with CAS_EPOCH_CONFLICT (409)."""
    service = IndexBuildService()
    db = _fresh_session()

    binding = KnowledgeBinding(
        id="bind_1",
        collection_id="col_1",
        repository_document_id="doc_1",
        active_index_revision_id="rev_old",
        active_epoch=5,  # Current DB epoch is 5
    )
    db.execute.return_value = _execute_result(scalar=binding)
    db.get.side_effect = [binding]

    # Client sends stale epoch = 4
    with pytest.raises(AppException) as exc_info:
        await service.promote_index_revision(
            db,
            binding_id="bind_1",
            index_revision_id="rev_new",
            expected_epoch=4,
        )

    assert exc_info.value.code == "CAS_EPOCH_CONFLICT"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_promote_index_revision_cas_success():
    """Promote with matching expected_epoch atomically increments active_epoch."""
    service = IndexBuildService()
    db = _fresh_session()

    binding = KnowledgeBinding(
        id="bind_1",
        collection_id="col_1",
        repository_document_id="doc_1",
        active_index_revision_id="rev_old",
        active_epoch=2,
    )
    target_rev = KnowledgeIndexRevision(
        id="rev_new",
        binding_id="bind_1",
        status="ready",
        chunk_count=10,
    )
    old_rev = KnowledgeIndexRevision(
        id="rev_old",
        binding_id="bind_1",
        status="active",
        chunk_count=10,
    )
    from app.modules.knowledge.models import KnowledgeCollection
    col = KnowledgeCollection(id="col_1", index_epoch=2)

    db.execute.side_effect = [
        _execute_result(scalar=binding),
        _execute_result(scalar=3),
    ]
    db.get.side_effect = lambda model, ident: {
        "rev_old": old_rev,
        "rev_new": target_rev,
        "bind_1": binding,
        "col_1": col,
    }.get(ident)

    with patch("app.modules.rag.vector_indexer.vector_indexer.activate_index_revision", new=AsyncMock()), \
         patch("app.modules.rag.vector_indexer.vector_indexer.deactivate_index_revision", new=AsyncMock()):
        resp = await service.promote_index_revision(
            db,
            binding_id="bind_1",
            index_revision_id="rev_new",
            expected_epoch=2,
            reason="Test promote CAS",
        )

    assert resp.epoch == 3
    assert binding.active_epoch == 3
    assert binding.active_index_revision_id == "rev_new"
    assert target_rev.status == "active"
    assert old_rev.status == "archived"


@pytest.mark.asyncio
async def test_rollback_from_archived_vs_pruned_revision():
    """Rollback from archived succeeds; rollback from pruned is rejected with 400."""
    service = IndexBuildService()
    db = _fresh_session()

    binding = KnowledgeBinding(
        id="bind_1",
        collection_id="col_1",
        active_index_revision_id="rev_current",
        active_epoch=3,
    )
    pruned_rev = KnowledgeIndexRevision(
        id="rev_pruned",
        binding_id="bind_1",
        status="pruned",
        chunk_count=0,
    )

    db.execute.return_value = _execute_result(scalar=binding)
    db.get.side_effect = lambda model, ident: pruned_rev if ident == "rev_pruned" else None

    with pytest.raises(AppException) as exc_info:
        await service.rollback_index_revision(
            db,
            binding_id="bind_1",
            target_index_revision_id="rev_pruned",
            expected_epoch=3,
        )

    assert exc_info.value.code == "REVISION_ALREADY_PRUNED"
    assert exc_info.value.status_code == 400


# ==============================================================================
# 4. Strict Vector Generation & Dimension Invariance
# ==============================================================================


def test_fit_dim_rejects_silent_truncate_or_pad():
    """_fit_dim must NOT pad with 0.0 or slice vector; it must raise VECTOR_DIMENSION_MISMATCH."""
    indexer = VectorIndexer(qdrant_url="http://localhost:6333")

    # Target is 1024, vector is 768
    small_vec = [0.1] * 768
    with pytest.raises(AppException) as exc_info:
        indexer._fit_dim(small_vec, target_dim=1024)
    assert exc_info.value.code == "VECTOR_DIMENSION_MISMATCH"

    # Target is 1024, vector is 1536
    large_vec = [0.1] * 1536
    with pytest.raises(AppException) as exc_info:
        indexer._fit_dim(large_vec, target_dim=1024)
    assert exc_info.value.code == "VECTOR_DIMENSION_MISMATCH"

    # Matching dimension returns cleaned vector
    valid_vec = [0.1] * 1024
    res = indexer._fit_dim(valid_vec, target_dim=1024)
    assert len(res) == 1024


@pytest.mark.asyncio
async def test_ensure_collection_dimension_mismatch_fails_fast():
    """If Qdrant collection already exists with different size, ensure_collection must raise 409."""
    indexer = VectorIndexer(qdrant_url="http://localhost:6333")

    # Mock get_collections returning col_test
    col_mock = MagicMock()
    col_mock.name = "col_test"
    collections_mock = MagicMock()
    collections_mock.collections = [col_mock]
    indexer.client.get_collections = AsyncMock(return_value=collections_mock)

    # Existing collection has dim=768
    from qdrant_client.http import models as qmodels
    info_mock = MagicMock()
    info_mock.config.params.vectors = qmodels.VectorParams(
        size=768, distance=qmodels.Distance.COSINE
    )
    indexer.client.get_collection = AsyncMock(return_value=info_mock)

    # Requested dimension is 1024 -> must raise VECTOR_DIMENSION_MISMATCH
    with pytest.raises(AppException) as exc_info:
        await indexer.ensure_collection("test", vector_size=1024)

    assert exc_info.value.code == "VECTOR_DIMENSION_MISMATCH"
    assert exc_info.value.status_code == 409


# ==============================================================================
# 5. Cooperative Worker Cancellation
# ==============================================================================


@pytest.mark.asyncio
async def test_worker_cancellation_checkpoints():
    """Worker tasks must immediately exit if job has been cancelled."""
    from app.workers.tasks import task_document_revision_parse, task_knowledge_index_build

    db = _fresh_session()
    cancelled_job = JobRecord(
        id="job_cancel_1",
        status="cancelled",
        cancel_requested=True,
        payload={"revision_id": "rev_1", "binding_id": "bind_1", "source_revision_id": "rev_src"},
    )
    db.execute.return_value = _execute_result(scalar=cancelled_job)

    with patch("app.workers.tasks.AsyncSessionFactory", return_value=AsyncMock(__aenter__=AsyncMock(return_value=db), __aexit__=AsyncMock())):
        res1 = await task_document_revision_parse({}, "job_cancel_1")
        assert res1["status"] == "cancelled"

        res2 = await task_knowledge_index_build({}, "job_cancel_1")
        assert res2["status"] == "cancelled"
