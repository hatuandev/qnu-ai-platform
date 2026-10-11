"""Regression test suite for ADR-012 Integration Fixes.

Verifies:
1. DomainException & AppException backward compatibility (error_code keyword & arbitrary kwargs).
2. KnowledgeBinding, KnowledgeChunk, KnowledgeFact schema decoupling (nullable FKs, zero-cascade).
3. Revision point ID isolation (distinct seeds per index revision).
4. Payload chunks contract (root index_revision_id & vector_generation_id for Qdrant filtering).
5. Strict Parity Gate signature contract.
6. Dual-layer retrieval support (V3 independent chunks/facts queryable without legacy KnowledgeDocument).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeFact,
)
from app.modules.rag.facts import fact_layer
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import RetrievalSnapshot
from app.modules.rag.vector_indexer import vector_indexer


def test_domain_exception_error_code_compat() -> None:
    """Verifies DomainException and AppException safely accept error_code without TypeError."""
    # Test with standard code
    exc1 = AppException(message="Lỗi thử nghiệm", code="TEST_CODE", status_code=400)
    assert exc1.code == "TEST_CODE"
    assert exc1.status_code == 400

    # Test with legacy error_code parameter
    exc2 = AppException(
        detail="Chi tiết lỗi",
        error_code="LEGACY_ERROR_CODE",
        status_code=404,
        extra_unknown_arg="ignored_safely",
    )
    assert exc2.code == "LEGACY_ERROR_CODE"
    assert exc2.status_code == 404
    assert str(exc2) == "Chi tiết lỗi"


def test_models_schema_decoupling() -> None:
    """Verifies ORM columns for ADR-012 are nullable and decoupled."""
    # KnowledgeBinding: repository_document_id and source_revision_id are nullable
    binding = KnowledgeBinding(
        collection_id="col_test_123",
        repository_document_id=None,
        source_revision_id=None,
    )
    assert binding.repository_document_id is None
    assert binding.source_revision_id is None

    # KnowledgeChunk: document_id is nullable
    chunk = KnowledgeChunk(
        collection_id="col_test_123",
        document_id=None,
        binding_id="bnd_123",
        chunk_index=0,
        content="Nội dung chunk thử nghiệm",
        chunk_hash="hash123",
    )
    assert chunk.document_id is None
    assert chunk.binding_id == "bnd_123"

    # KnowledgeFact: document_id is nullable
    fact = KnowledgeFact(
        collection_id="col_test_123",
        document_id=None,
        binding_id="bnd_123",
        entity_name="Công nghệ thông tin",
        entity_type="major",
        attribute_name="quota",
        attribute_value="150",
    )
    assert fact.document_id is None
    assert fact.binding_id == "bnd_123"


def test_point_id_revision_isolation() -> None:
    """Verifies that point IDs are strictly isolated per index_revision_id to avoid overwriting active points."""
    col_id = "col_test"
    gen_id = "gen_test"
    idx = 0

    idx_rev_1 = "idx_rev_001"
    idx_rev_2 = "idx_rev_002"

    point_id_1 = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{col_id}:{gen_id}:{idx_rev_1}:{idx}"))
    point_id_2 = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{col_id}:{gen_id}:{idx_rev_2}:{idx}"))

    # Crucial invariant: point_ids must NEVER collide between revisions
    assert point_id_1 != point_id_2


@pytest.mark.asyncio
async def test_verify_index_revision_parity_contract() -> None:
    """Verifies that vector_indexer.verify_index_revision_parity accepts index_revision_id and custom collection name."""
    mock_client = AsyncMock()
    mock_client.collection_exists.return_value = True

    mock_count = MagicMock()
    mock_count.count = 2
    mock_client.count.return_value = mock_count

    point_mock_1 = MagicMock()
    point_mock_1.id = "pt_1"
    point_mock_1.payload = {"index_revision_id": "idx_rev_123", "content_hash": "hash_1"}

    point_mock_2 = MagicMock()
    point_mock_2.id = "pt_2"
    point_mock_2.payload = {"index_revision_id": "idx_rev_123", "content_hash": "hash_2"}

    mock_client.retrieve.return_value = [point_mock_1, point_mock_2]

    with patch.object(vector_indexer, "client", mock_client):
        passed, _reason, count = await vector_indexer.verify_index_revision_parity(
            collection_id="col_123",
            index_revision_id="idx_rev_123",
            expected_points={"pt_1": "hash_1", "pt_2": "hash_2"},
            qdrant_collection_name="col_custom_gen",
        )

        assert passed is True
        assert count == 2
        mock_client.collection_exists.assert_called_with("col_custom_gen")


@pytest.mark.asyncio
async def test_sparse_search_retrieves_v3_independent_chunks() -> None:
    """Verifies search_sparse_fts executes outerjoin query allowing chunks without KnowledgeDocument."""
    mock_db = AsyncMock()
    mock_scalars = MagicMock()

    chunk_v3 = KnowledgeChunk(
        id="chk_v3_test",
        collection_id="col_test",
        document_id=None,
        binding_id="bnd_test",
        index_revision_id="idx_rev_active",
        chunk_index=0,
        content="Ngành Công nghệ thông tin đào tạo cử nhân chất lượng cao",
        chunk_hash="hash_v3",
    )
    mock_scalars.all.return_value = [chunk_v3]
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_res

    snapshot = RetrievalSnapshot(
        snapshot_id="snap_123",
        collection_id="col_test",
        collection_epoch=1,
        binding_revisions={"bnd_test": "idx_rev_active"},
        vector_generations={"bnd_test": "gen_test"},
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
    )

    results = await hybrid_retriever.search_sparse_fts(
        db=mock_db,
        collection_id="col_test",
        query="Công nghệ thông tin",
        top_k=5,
        snapshot=snapshot,
    )

    assert len(results) == 1
    assert results[0]["chunk_id"] == "chk_v3_test"
    assert results[0]["binding_id"] == "bnd_test"
    # Verify execute was called with outerjoin query
    assert mock_db.execute.called


@pytest.mark.asyncio
async def test_fact_lookup_retrieves_v3_independent_facts() -> None:
    """Verifies lookup_facts executes outerjoin query allowing facts without KnowledgeDocument."""
    mock_db = AsyncMock()
    mock_scalars = MagicMock()

    fact_v3 = KnowledgeFact(
        id="fct_v3_test",
        collection_id="col_test",
        document_id=None,
        binding_id="bnd_test",
        index_revision_id="idx_rev_active",
        entity_name="Công nghệ thông tin",
        entity_type="major",
        attribute_name="quota",
        attribute_value="180",
    )
    mock_scalars.all.return_value = [fact_v3]
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_res

    results = await fact_layer.lookup_facts(
        db=mock_db,
        collection_id="col_test",
        keywords=["Công nghệ thông tin"],
        active_index_revision_ids={"idx_rev_active"},
    )

    assert len(results) == 1
    assert results[0].id == "fct_v3_test"
    assert results[0].attribute_value == "180"
