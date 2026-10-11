"""Unit & Acceptance Tests for ChunkSet & Multi-Vector Generation Engine (ADR-012 Phiên 5).

Verifies:
1. 'Parse Once, Chunk Once, Embed Many': Materializes KnowledgeChunkSet once and strictly reuses it.
2. Re-embedding into a new model/generation NEVER invokes document parsers or OCR engines.
3. Parity Gate Enforcement: 100% parity verification between PostgreSQL chunks and Qdrant points.
4. Atomic Pointer Swap (CAS): Vector generation activation safely retires prior spaces and bumps epoch.
5. HTTP REST APIs for vector generations and chunk sets.
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
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunkSet,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import (
    BuildVectorGenerationResponse,
)
from app.modules.knowledge.services.chunk_set_service import (
    chunk_set_service,
)
from app.modules.knowledge.services.vector_generation_service import (
    vector_generation_service,
)
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
        mock.scalars.return_value.first.return_value = None
        mock.scalars.return_value.all.return_value = []

    if scalars_list is not None:
        mock.scalars.return_value.all.return_value = scalars_list
        mock.scalars.return_value.first.return_value = scalars_list[0] if scalars_list else None

    if all_list is not None:
        mock.all.return_value = all_list
    return mock


# ==============================================================================
# Unit Tests for ChunkSetService
# ==============================================================================
@pytest.mark.asyncio
async def test_chunk_set_materialization_and_reuse() -> None:
    """Verify ChunkSet is materialized once from canonical Markdown and reused identically."""
    clean_markdown = (
        "# TRƯỜNG ĐẠI HỌC QUY NHƠN\n\n"
        "## QUY CHẾ TUYỂN SINH ĐẠI HỌC CHÍNH QUY\n\n"
        "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng.\n"
        "Quy chế này quy định về công tác tuyển sinh đại học chính quy của Trường Đại học Quy Nhơn.\n\n"
        "Điều 2. Phương thức tuyển sinh.\n"
        "Nhà trường áp dụng các phương thức: xét điểm thi THPT, xét học bạ, và xét tuyển thẳng."
    )
    canonical_hash = hashlib.sha256(clean_markdown.encode("utf-8")).hexdigest()

    source_rev = KnowledgeSourceRevision(
        id="ks_rev_01",
        binding_id="bind_01",
        revision_no=1,
        origin_document_id="doc_01",
        origin_file_hash="hash_01",
        snapshot_storage_path="path_01",
        canonical_markdown=clean_markdown,
        canonical_hash=canonical_hash,
        status="ready",
    )

    mock_db = AsyncMock()
    # Call 1: New chunk set
    # 1. Fetch source_rev -> source_rev
    # 2. Check existing with config_hash -> None
    # 3. Check existing with set_key -> None
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=source_rev),
            _execute_result(scalar=None),
            _execute_result(scalar=None),
        ]
    )

    chunk_set = await chunk_set_service.get_or_create_chunk_set(
        db=mock_db,
        source_revision_id=source_rev.id,
        chunk_strategy="ClauseBasedChunker",
        chunk_config={"chunk_size": 500},
    )

    assert chunk_set.status == "ready"
    assert chunk_set.source_revision_id == source_rev.id
    assert chunk_set.chunk_strategy == "ClauseBasedChunker"
    assert chunk_set.chunk_count >= 2
    assert chunk_set.manifest_hash is not None
    assert "_manifest" in chunk_set.chunk_config
    assert len(chunk_set.chunk_config["_manifest"]) == chunk_set.chunk_count

    # Call 2: Existing chunk set with identical config
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=source_rev),
            _execute_result(scalar=chunk_set),  # Found ready!
        ]
    )
    reused_set = await chunk_set_service.get_or_create_chunk_set(
        db=mock_db,
        source_revision_id=source_rev.id,
        chunk_strategy="ClauseBasedChunker",
        chunk_config={"chunk_size": 500},
    )

    assert reused_set.id == chunk_set.id
    assert reused_set.config_hash == chunk_set.config_hash


@pytest.mark.asyncio
async def test_chunk_set_rejects_unready_source_revision() -> None:
    """Verify chunk set creation is blocked if source revision has not passed Quality Gate."""
    source_rev = KnowledgeSourceRevision(
        id="ks_rev_unready",
        binding_id="bind_01",
        revision_no=1,
        origin_document_id="doc_01",
        origin_file_hash="hash_01",
        snapshot_storage_path="path_01",
        status="review_required",  # Not ready!
    )

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_execute_result(scalar=source_rev))

    with pytest.raises(AppException) as exc_info:
        await chunk_set_service.get_or_create_chunk_set(
            db=mock_db,
            source_revision_id=source_rev.id,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "SOURCE_REVISION_NOT_READY"


# ==============================================================================
# Unit Tests for VectorGenerationService & 'Embed Many' Invariant
# ==============================================================================
@pytest.mark.asyncio
async def test_reembed_model_does_not_call_parser_or_ocr() -> None:
    """CRITICAL INVARIANT: Re-embedding into a new vector generation NEVER calls parser/OCR."""
    col = KnowledgeCollection(
        id="col_tuyensinh",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho Tuyển sinh",
        collection_metadata={},
    )
    source_rev = KnowledgeSourceRevision(
        id="ks_rev_admissions",
        binding_id="bind_01",
        revision_no=1,
        origin_document_id="doc_01",
        origin_file_hash="hash_01",
        snapshot_storage_path="path_01",
        status="ready",
    )
    binding = KnowledgeBinding(
        id="bind_01",
        collection_id=col.id,
        tenant_id=col.tenant_id,
        workspace_id=col.workspace_id,
        repository_document_id="doc_01",
        status="active",
        active_source_revision_id=source_rev.id,
    )
    binding.active_source_revision = source_rev

    # Pre-materialized chunk set with 3 chunks
    manifest = [
        {"index": 0, "content": "Chunk 1: Giới thiệu chung", "chunk_hash": "h1"},
        {"index": 1, "content": "Chunk 2: Tiêu chuẩn tuyển sinh", "chunk_hash": "h2"},
        {"index": 2, "content": "Chunk 3: Học phí và học bổng", "chunk_hash": "h3"},
    ]
    chunk_set = KnowledgeChunkSet(
        id="chk_set_admissions",
        source_revision_id=source_rev.id,
        chunk_strategy="ClauseBasedChunker",
        chunk_config={"_manifest": manifest},
        config_hash="conf_hash_01",
        chunk_count=3,
        status="ready",
    )

    new_gen = KnowledgeVectorGeneration(
        id="gen_bge_m3",
        collection_id=col.id,
        embedding_model="BAAI/bge-m3",
        provider_id="provider_local",
        embedding_dimension=1024,
        generation_epoch=2,
        status="building",
        config_hash="conf_bge_m3",
        qdrant_collection_name="col_tuyensinh",
    )

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=col)
    # 1. Fetch binding
    # 2. Fetch generation
    # 3. Check existing index revision -> None
    # 4. Rev no max stmt -> 0 (next 1)
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=col),  # collection lock before source build reservation
            _execute_result(scalar=binding),
            _execute_result(scalar=new_gen),
            _execute_result(scalar=None),
            _execute_result(scalar=0),
        ]
    )

    with patch("app.modules.knowledge.services.vector_generation_service.chunk_set_service.get_or_create_chunk_set", new_callable=AsyncMock) as mock_get_chunk_set, \
         patch.object(vector_indexer, "index_chunks", new_callable=AsyncMock) as mock_index_chunks, \
         patch.object(vector_indexer, "verify_index_revision_parity", new_callable=AsyncMock) as mock_verify_parity, \
         patch("app.modules.knowledge.parsers.get_document_parser") as mock_parser_getter:

        mock_get_chunk_set.return_value = chunk_set
        mock_index_chunks.return_value = 3  # Indexed 3 points
        mock_verify_parity.return_value = (True, "", 3)

        idx_rev = await vector_generation_service.build_generation_for_source(
            db=mock_db,
            collection_id=col.id,
            binding_id=binding.id,
            generation_id=new_gen.id,
        )

        assert idx_rev.status == "ready"
        assert idx_rev.chunk_set_id == chunk_set.id
        assert idx_rev.vector_generation_id == new_gen.id
        assert idx_rev.chunk_count == 3
        assert idx_rev.parity_report["parity_passed"] is True

        # INVARIANT VERIFICATION: Parser is ZERO times called!
        assert mock_parser_getter.call_count == 0
        assert mock_get_chunk_set.call_count == 1
        assert mock_index_chunks.call_count == 1


@pytest.mark.asyncio
async def test_parity_gate_failure_marks_revision_failed() -> None:
    """Verify that if Qdrant points count mismatches chunks count, Parity Gate fails honestly."""
    col = KnowledgeCollection(id="col_01", tenant_id="t1", workspace_id="ws1", name="C1")
    source_rev = KnowledgeSourceRevision(id="ks_01", binding_id="b1", revision_no=1, status="ready")
    binding = KnowledgeBinding(id="b1", collection_id="col_01", tenant_id="t1", workspace_id="ws1", status="active")
    binding.active_source_revision = source_rev

    manifest = [{"index": 0, "content": "Chunk 1", "chunk_hash": "h1"}]
    chunk_set = KnowledgeChunkSet(
        id="cs_01",
        source_revision_id="ks_01",
        chunk_config={"_manifest": manifest},
        chunk_count=1,
        status="ready",
    )
    gen = KnowledgeVectorGeneration(id="gen_01", collection_id="col_01", embedding_model="m1", status="building")

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=col)
    mock_db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=col),  # collection lock before source build reservation
            _execute_result(scalar=binding),
            _execute_result(scalar=gen),
            _execute_result(scalar=None),
            _execute_result(scalar=0),
        ]
    )

    with patch("app.modules.knowledge.services.vector_generation_service.chunk_set_service.get_or_create_chunk_set", new_callable=AsyncMock) as mock_get_chunk_set, \
         patch.object(vector_indexer, "index_chunks", new_callable=AsyncMock) as mock_index_chunks:

        mock_get_chunk_set.return_value = chunk_set
        mock_index_chunks.return_value = 0  # 0 points indexed while 1 chunk expected!

        with pytest.raises(AppException) as exc_info:
            await vector_generation_service.build_generation_for_source(
                db=mock_db,
                collection_id="col_01",
                binding_id="b1",
                generation_id="gen_01",
            )

        assert exc_info.value.code == "PARITY_GATE_FAILED"
        assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_vector_generation_lifecycle_and_cas_activation() -> None:
    """Verify Check-And-Set (CAS) atomic pointer swap activates generation and retires old generation."""
    col = KnowledgeCollection(
        id="col_01",
        tenant_id="tenant_qnu",
        workspace_id="workspace_tuyensinh",
        name="Kho Tuyển sinh",
        collection_metadata={"index_epoch": 1, "active_vector_generation_id": "gen_old"},
    )
    old_gen = KnowledgeVectorGeneration(
        id="gen_old",
        collection_id=col.id,
        embedding_model="text-embedding-3-small",
        generation_epoch=1,
        status="active",
    )
    new_gen = KnowledgeVectorGeneration(
        id="gen_new",
        collection_id=col.id,
        embedding_model="BAAI/bge-m3",
        generation_epoch=2,
        status="ready",
    )

    binding = KnowledgeBinding(id="bind_01", collection_id=col.id, status="active")

    rev = KnowledgeIndexRevision(
        id="idx_new", binding_id=binding.id, vector_generation_id=new_gen.id,
        source_revision_v2_id=None, revision_no=1, status="ready", chunk_count=1,
    )
    mock_db = AsyncMock()
    mock_db.get.side_effect = lambda cls, key: {"gen_new": new_gen, "gen_old": old_gen}.get(key)
    mock_db.execute.side_effect = [
        _execute_result(scalars_list=[binding]),
        _execute_result(scalars_list=[rev]),
        _execute_result(scalars_list=[binding]),
    ]
    with patch("app.modules.knowledge.services.generation_publish_service.get_scoped_collection", new_callable=AsyncMock, return_value=col), \
         patch.object(vector_indexer, "activate_index_revision", autospec=True, return_value=1), \
         patch.object(vector_indexer, "deactivate_index_revision", autospec=True) as deactivate:
        resp = await vector_generation_service.activate_vector_generation(mock_db, col.id, new_gen.id)
        assert resp.activated_generation_id == new_gen.id
        assert resp.previous_generation_id == old_gen.id
        assert resp.new_epoch == 2
        assert old_gen.status == "retired"
        assert binding.active_index_revision_id == rev.id
        deactivate.assert_not_called()


# ==============================================================================
# HTTP Routes Integration Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_http_routes_vector_generations() -> None:
    """Verify HTTP REST endpoints for vector generation operations."""
    gen = KnowledgeVectorGeneration(
        id="gen_http_01",
        collection_id="col_01",
        embedding_model="text-embedding-3-small",
        provider_id="provider_openai",
        embedding_dimension=1536,
        distance_metric="cosine",
        generation_epoch=1,
        status="active",
        config_hash="conf_hash_01",
        created_at=datetime.now(UTC),
    )
    chunk_set = KnowledgeChunkSet(
        id="cs_http_01",
        source_revision_id="ks_01",
        chunk_strategy="ClauseBasedChunker",
        chunk_config={"chunk_size": 500},
        config_hash="conf_01",
        chunk_count=5,
        fact_count=0,
        status="ready",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_actor] = lambda: _make_actor()

    try:
        # 1. GET /vector-generations
        with patch.object(vector_generation_service, "list_vector_generations", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [gen]
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.get("/platform/v1alpha1/knowledge/collections/col_01/vector-generations")
                assert res.status_code == 200
                data = res.json()
                assert len(data) == 1
                assert data[0]["id"] == "gen_http_01"
                assert data[0]["embedding_model"] == "text-embedding-3-small"

        # 2. POST /vector-generations
        with patch.object(vector_generation_service, "create_vector_generation", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = gen
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post(
                    "/platform/v1alpha1/knowledge/collections/col_01/vector-generations",
                    json={"embedding_model": "text-embedding-3-small"},
                )
                assert res.status_code == 201
                assert res.json()["id"] == "gen_http_01"

        # 3. POST /vector-generations/{id}/build
        with patch.object(vector_generation_service, "build_all_sources_for_generation", new_callable=AsyncMock) as mock_build:
            mock_build.return_value = BuildVectorGenerationResponse(
                collection_id="col_01",
                generation_id=gen.id,
                total_sources=2,
                built_count=2,
                reused_count=0,
                failed_count=0,
                status="ready",
            )
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post(
                    f"/platform/v1alpha1/knowledge/collections/col_01/vector-generations/{gen.id}/build",
                    json={"chunk_strategy": "ClauseBasedChunker"},
                )
                assert res.status_code == 200
                assert res.json()["built_count"] == 2
                assert res.json()["status"] == "ready"

        # 4. GET /sources/{id}/chunk-sets
        with patch.object(chunk_set_service, "list_chunk_sets_for_source", new_callable=AsyncMock) as mock_list_cs:
            mock_list_cs.return_value = [chunk_set]
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.get("/platform/v1alpha1/knowledge/collections/col_01/sources/src_01/chunk-sets")
                assert res.status_code == 200
                assert len(res.json()) == 1
                assert res.json()[0]["id"] == "cs_http_01"
                assert res.json()[0]["chunk_count"] == 5

    finally:
        app.dependency_overrides.clear()
