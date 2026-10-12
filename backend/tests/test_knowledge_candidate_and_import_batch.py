"""Unit and integration test suite for ADR-012 Session 3:
Candidate Diffing & Snapshot Import Batch Engine.

Verifies:
1. Candidate groups statistics (total_documents, imported_documents).
2. 2-Dimensional state classification (source_state & vector_state).
3. Selectable rule and reason invariants.
4. Snapshot import batch creation, per-item provenance, and strict idempotency.
5. Batch item retry and cancellation.
6. Zero KnowledgeGroupSource creation invariant.
7. HTTP REST routes for candidate-groups, candidate-documents, and imports.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor


@pytest.fixture(autouse=True)
def isolate_admission_from_unit_session_stubs():
    with patch("app.modules.jobs.ingestion_admission.check_ingestion_capacity", AsyncMock()):
        yield
from app.modules.documents.models import (
    DocumentGroup,
    RepositoryDocument,
)
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeGroupSource,
    KnowledgeImportBatch,
    KnowledgeImportItem,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import KnowledgeImportBatchCreateRequest
from app.modules.knowledge.services.candidate_service import candidate_service
from app.modules.knowledge.services.import_batch_service import import_batch_service


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
    else:
        mock.scalar_one_or_none.return_value = None
        mock.scalar.return_value = None

    if scalars_list is not None:
        mock.scalars.return_value.all.return_value = scalars_list
        mock.scalars.return_value.first.return_value = scalars_list[0] if scalars_list else None
    elif scalar is not None:
        mock.scalars.return_value.all.return_value = [scalar]

    if all_list is not None:
        mock.all.return_value = all_list
    return mock


# ==============================================================================
# Unit Tests for CandidateService
# ==============================================================================
@pytest.mark.asyncio
async def test_candidate_service_get_candidate_groups() -> None:
    """Test get_candidate_groups returns correct stats of total and imported documents."""
    coll = KnowledgeCollection(
        id="col_tuyensinh_2026",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho tri thức Tuyển sinh",
    )
    group1 = DocumentGroup(
        id="grp_de_an_01",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Đề án Tuyển sinh 2026",
    )
    mock_db = AsyncMock()

    # Call sequences:
    # 1. coll check
    # 2. groups in workspace
    # 3. imported doc IDs in collection
    # 4. members for group1
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=coll),
            _execute_result(scalars_list=[group1]),
            _execute_result(all_list=[("doc_01",)]),
            _execute_result(all_list=[("doc_01",), ("doc_02",)]),
        ]
    )

    res = await candidate_service.get_candidate_groups(
        collection_id=coll.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        db=mock_db,
    )

    assert res.total == 1
    assert len(res.items) == 1
    item = res.items[0]
    assert item.id == "grp_de_an_01"
    assert item.name == "Đề án Tuyển sinh 2026"
    assert item.total_documents == 2
    assert item.imported_documents == 1


@pytest.mark.asyncio
async def test_candidate_service_state_classification_all_combinations() -> None:
    """Verify 2-dimensional state evaluation: source_state, vector_state, and selectability."""
    coll = KnowledgeCollection(
        id="col_tuyensinh_2026",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho tri thức Tuyển sinh",
    )
    vec_gen = KnowledgeVectorGeneration(
        id="gen_bge_m3_v1",
        collection_id=coll.id,
        embedding_model="bge-m3",
        provider_id="prov_rtx5090_vllm",
        qdrant_collection_name="col_tuyensinh_2026_bge_m3",
        config_hash="cfg_hash_bge_m3",
        embedding_dimension=1024,
        status="active",
    )

    doc_new = _make_doc("doc_new", "Tài liệu mới", "moi.pdf", b"moi")
    doc_current = _make_doc("doc_current", "Tài liệu đã có", "hientai.pdf", b"hientai")
    doc_outdated = _make_doc("doc_outdated", "Tài liệu cần cập nhật", "capnhat.pdf", b"capnhat_moi")

    # Bindings
    binding_current = KnowledgeBinding(
        id="bind_01",
        collection_id=coll.id,
        repository_document_id=doc_current.id,
        source_revision_id="rev_01",
    )
    binding_current.active_source_revision = KnowledgeSourceRevision(
        id="src_rev_01",
        binding_id=binding_current.id,
        origin_file_hash=doc_current.file_hash,
        status="ready",
    )
    binding_current.index_revisions = [
        KnowledgeIndexRevision(
            id="idx_rev_01",
            binding_id=binding_current.id,
            vector_generation_id=vec_gen.id,
            status="active",
        )
    ]

    binding_outdated = KnowledgeBinding(
        id="bind_02",
        collection_id=coll.id,
        repository_document_id=doc_outdated.id,
        source_revision_id="rev_02",
    )
    binding_outdated.active_source_revision = KnowledgeSourceRevision(
        id="src_rev_02",
        binding_id=binding_outdated.id,
        origin_file_hash="hash_cu_da_thay_doi",
        status="ready",
    )

    idx_rev = KnowledgeIndexRevision(
        id="idx_rev_01",
        binding_id=binding_current.id,
        vector_generation_id=vec_gen.id,
        status="active",
    )
    binding_current.active_index_revision = idx_rev

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=coll),
            _execute_result(scalar=vec_gen),
            _execute_result(scalars_list=[doc_new, doc_current, doc_outdated]),
            _execute_result(all_list=[]),  # group memberships
            _execute_result(scalars_list=[binding_current, binding_outdated]),
            _execute_result(scalars_list=[idx_rev]),  # index revisions query
        ]
    )

    res = await candidate_service.get_candidate_documents(
        collection_id=coll.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        db=mock_db,
    )

    assert res.total == 3
    items = {it.document_id: it for it in res.items}

    # 1. doc_new: not_imported & not_indexed -> selectable
    assert items["doc_new"].source_state == "not_imported"
    assert items["doc_new"].vector_state == "not_indexed"
    assert items["doc_new"].selectable is True

    # 2. doc_current: current & indexed -> NOT selectable
    assert items["doc_current"].source_state == "current"
    assert items["doc_current"].vector_state == "indexed"
    assert items["doc_current"].selectable is False
    assert items["doc_current"].unselectable_reason is not None

    # 3. doc_outdated: update_available -> selectable
    assert items["doc_outdated"].source_state == "update_available"
    assert items["doc_outdated"].selectable is True


# ==============================================================================
# Unit Tests for ImportBatchService
# ==============================================================================
@pytest.mark.asyncio
async def test_import_batch_service_lifecycle_and_idempotency() -> None:
    """Test creating an import batch, per-item provenance, and strict idempotency replay."""
    coll = KnowledgeCollection(
        id="col_tuyensinh_2026",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho tri thức Tuyển sinh",
    )
    doc1 = _make_doc("doc_01", "Văn bản 1", "vb1.pdf", b"vb1_bytes")
    doc2 = _make_doc("doc_02", "Văn bản 2", "vb2.pdf", b"vb2_bytes")

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(return_value=None)  # no source currently reserved for purge
    # 1. Coll check
    # 2. Idempotency check (None)
    # 3. Docs check
    # 4. Active gen check
    # 5. Memberships lookup
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=coll),
            _execute_result(scalar=None),
            _execute_result(scalars_list=[doc1, doc2]),
            _execute_result(scalar=None),
            _execute_result(all_list=[("doc_01", "grp_01")]),
        ]
    )

    payload = KnowledgeImportBatchCreateRequest(
        document_ids=["doc_01", "doc_02"],
        parser_profile="standard",
        chunk_strategy="ClauseBasedChunker",
        chunk_config={"chunk_size": 1000},
    )

    batch = await import_batch_service.create_import_batch(
        collection_id=coll.id,
        payload=payload,
        idempotency_key="idem_batch_key_999",
        created_by="user_officer_01",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        db=mock_db,
    )

    assert batch.id.startswith("imp_batch_")
    assert batch.total_count == 2
    assert batch.queued_count == 2
    assert batch.status == "queued"
    assert batch.idempotency_key == "idem_batch_key_999"
    assert len(batch.items) == 2

    # Check items provenance
    item1 = next(it for it in batch.items if it.origin_document_id == "doc_01")
    assert item1.origin_title == "Văn bản 1"
    assert item1.origin_file_name == "vb1.pdf"
    assert item1.origin_file_hash == doc1.file_hash
    assert item1.origin_group_id == "grp_01"
    assert item1.phase == "snapshot"
    assert item1.status == "queued"

    # Test Idempotency Replay
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=coll),
            _execute_result(scalar=batch),  # Found existing by idempotency_key!
        ]
    )
    replay_batch = await import_batch_service.create_import_batch(
        collection_id=coll.id,
        payload=payload,
        idempotency_key="idem_batch_key_999",
        created_by="user_officer_01",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        db=mock_db,
    )
    assert replay_batch.id == batch.id


@pytest.mark.asyncio
async def test_import_batch_retry_and_cancellation() -> None:
    """Test retry_failed_items resets failed items, cancel_import_batch marks items skipped."""
    coll = KnowledgeCollection(
        id="col_tuyensinh_2026",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
    )
    batch = KnowledgeImportBatch(
        id="imp_batch_test",
        collection_id=coll.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        total_count=2,
        failed_count=1,
        queued_count=1,
        status="partial_failed",
    )
    item_ok = KnowledgeImportItem(
        id="it_1",
        batch_id=batch.id,
        origin_document_id="doc_1",
        origin_file_hash="h1",
        origin_title="T1",
        origin_file_name="f1",
        origin_file_type="pdf",
        status="succeeded",
    )
    item_failed = KnowledgeImportItem(
        id="it_2",
        batch_id=batch.id,
        origin_document_id="doc_2",
        origin_file_hash="h2",
        origin_title="T2",
        origin_file_name="f2",
        origin_file_type="pdf",
        status="failed",
        failure_code="OCR_FAILED",
    )
    batch.items = [item_ok, item_failed]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_execute_result(scalar=batch))
    mock_db.scalars = AsyncMock(return_value=MagicMock(all=list))

    # 1. Retry failed items
    retried_batch = await import_batch_service.retry_failed_items(
        collection_id=coll.id,
        batch_id=batch.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        db=mock_db,
    )
    assert item_failed.status == "queued"
    assert item_failed.phase == "snapshot"
    assert item_failed.failure_code is None
    assert item_failed.retry_count == 1
    assert retried_batch.status == "queued"

    # 2. Cancel batch
    cancelled_batch = await import_batch_service.cancel_import_batch(
        collection_id=coll.id,
        batch_id=batch.id,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        db=mock_db,
    )
    assert cancelled_batch.status == "cancelled"
    assert item_failed.status == "skipped"
    assert item_failed.failure_code == "BATCH_CANCELLED"


@pytest.mark.asyncio
async def test_adr012_zero_knowledge_group_source_created() -> None:
    """Verify ADR-012 invariant: batch import NEVER creates KnowledgeGroupSource."""
    coll = KnowledgeCollection(
        id="col_tuyensinh_2026",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
    )
    doc = _make_doc("doc_01", "Văn bản", "vb.pdf", b"bytes")

    added_entities: list[Any] = []
    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(return_value=None)  # no source currently reserved for purge
    mock_db.add.side_effect = lambda obj: added_entities.append(obj)
    mock_db.add_all.side_effect = lambda objs: added_entities.extend(objs)

    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=coll),
            _execute_result(scalar=None),
            _execute_result(scalars_list=[doc]),
            _execute_result(scalar=None),
            _execute_result(all_list=[]),
        ]
    )

    payload = KnowledgeImportBatchCreateRequest(document_ids=["doc_01"])
    await import_batch_service.create_import_batch(
        collection_id=coll.id,
        payload=payload,
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        db=mock_db,
    )

    # Invariant assertion
    for entity in added_entities:
        assert not isinstance(
            entity, KnowledgeGroupSource
        ), "ADR-012 Violation: KnowledgeGroupSource must never be instantiated during batch import!"


# ==============================================================================
# Integration HTTP Route Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_api_candidate_and_imports_routes() -> None:
    """Test full HTTP endpoints contract for candidate and import batch APIs."""
    actor = _make_actor()
    coll = KnowledgeCollection(
        id="col_test_api_01",
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        name="Kho Tri Thức API Test",
    )
    batch = KnowledgeImportBatch(
        id="imp_batch_http_test",
        collection_id=coll.id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        total_count=1,
        queued_count=1,
        status="queued",
    )
    batch.items = [
        KnowledgeImportItem(
            id="imp_item_http_test",
            batch_id=batch.id,
            origin_document_id="doc_01",
            origin_file_hash="mock_hash",
            origin_title="Tài liệu test",
            origin_file_name="test.pdf",
            origin_file_type="pdf",
            status="queued",
            phase="snapshot",
        )
    ]

    mock_db = AsyncMock()

    app.dependency_overrides[get_current_actor] = lambda: actor
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /candidate-groups
        with patch.object(candidate_service, "get_candidate_groups", new_callable=AsyncMock) as mock_get_groups:
            from app.modules.knowledge.schemas import CandidateGroupListResponse
            mock_get_groups.return_value = CandidateGroupListResponse(items=[], total=0)
            res_groups = await client.get(f"/platform/v1alpha1/knowledge/collections/{coll.id}/candidate-groups")
            assert res_groups.status_code == 200
            assert res_groups.json()["total"] == 0

        # 2. GET /candidate-documents
        with patch.object(candidate_service, "get_candidate_documents", new_callable=AsyncMock) as mock_get_candidates:
            from app.modules.knowledge.schemas import CandidateListResponse
            mock_get_candidates.return_value = CandidateListResponse(items=[], total=0)
            res_candidates = await client.get(f"/platform/v1alpha1/knowledge/collections/{coll.id}/candidate-documents")
            assert res_candidates.status_code == 200
            assert res_candidates.json()["total"] == 0

        # 3. POST /imports
        with patch.object(import_batch_service, "create_import_batch", new_callable=AsyncMock) as mock_create_batch:
            mock_create_batch.return_value = batch
            res_create = await client.post(
                f"/platform/v1alpha1/knowledge/collections/{coll.id}/imports",
                headers={"Idempotency-Key": "test_idem_header_123"},
                json={"document_ids": ["doc_01"]},
            )
            assert res_create.status_code == 201
            data = res_create.json()
            assert data["id"] == batch.id
            assert data["total_count"] == 1
            assert len(data["items"]) == 1

        # 4. GET /imports/{batch_id}
        with patch.object(import_batch_service, "get_import_batch", new_callable=AsyncMock) as mock_get_batch:
            mock_get_batch.return_value = batch
            res_get_batch = await client.get(f"/platform/v1alpha1/knowledge/collections/{coll.id}/imports/{batch.id}")
            assert res_get_batch.status_code == 200
            assert res_get_batch.json()["id"] == batch.id

        # 5. POST /imports/{batch_id}/retry-failed
        with patch.object(import_batch_service, "retry_failed_items", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = batch
            res_retry = await client.post(f"/platform/v1alpha1/knowledge/collections/{coll.id}/imports/{batch.id}/retry-failed")
            assert res_retry.status_code == 200

        # 6. POST /imports/{batch_id}/cancel
        with patch.object(import_batch_service, "cancel_import_batch", new_callable=AsyncMock) as mock_cancel:
            batch.status = "cancelled"
            mock_cancel.return_value = batch
            res_cancel = await client.post(f"/platform/v1alpha1/knowledge/collections/{coll.id}/imports/{batch.id}/cancel")
            assert res_cancel.status_code == 200
            assert res_cancel.json()["status"] == "cancelled"

    app.dependency_overrides.clear()
