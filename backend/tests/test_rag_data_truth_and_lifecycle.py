"""Test Suite: RAG Data Truth, Document Lifecycle State Machine & 4-Layer Parity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.http import models as qmodels

from app.core.exceptions import AppException
from app.core.redis import SemanticCache
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeCollection, KnowledgeDocument
from app.modules.knowledge.services.ingestion_service import IngestionService
from app.modules.knowledge.services.reconciliation_service import ReconciliationService
from app.modules.rag.facts import FactLayer
from app.modules.rag.retriever import HybridRetriever
from app.modules.rag.vector_indexer import VectorIndexer

# ============================================================================
# 1. VectorIndexer Validation & Positive Allowlist Tests
# ============================================================================


@pytest.mark.asyncio
async def test_indexer_rejects_missing_metadata():
    """VectorIndexer must fail-fast with INVALID_POINT_PAYLOAD if any of 11 fields is missing."""
    indexer = VectorIndexer()

    # Missing 'document_revision' and 'payload_schema_version'
    invalid_chunks = [
        {
            "id": "c1",
            "content": "Nội dung quy chế tuyển sinh",
            "document_id": "doc1",
            "collection_id": "col1",
            "tenant_id": "tenant_qnu",
            "workspace_id": "ws_default",
            "document_status": "ready",
            "is_retrievable": True,
            "content_hash": "hash123",
            "embedding_model": "text-embedding-3-small",
            # Missing document_revision, payload_schema_version
        }
    ]

    with pytest.raises(AppException) as exc_info:
        await indexer.index_chunks("col1", invalid_chunks)

    assert exc_info.value.code == "INVALID_POINT_PAYLOAD"
    assert exc_info.value.status_code == 400
    assert "document_revision" in exc_info.value.detail or "payload_schema_version" in exc_info.value.detail


@pytest.mark.asyncio
async def test_indexer_accepts_valid_v1_payload():
    """VectorIndexer must successfully validate and upsert chunks with all 11 required fields."""
    indexer = VectorIndexer()
    indexer.client = AsyncMock()
    indexer._embeddings = AsyncMock()
    indexer._embeddings.aembed_documents = AsyncMock(return_value=[[0.1] * 1536])

    valid_chunks = [
        {
            "id": "c1",
            "chunk_id": "c1",
            "content": "Chỉ tiêu tuyển sinh ngành CNTT",
            "document_id": "doc1",
            "collection_id": "col1",
            "tenant_id": "tenant_qnu",
            "workspace_id": "ws_default",
            "document_revision": 1,
            "document_status": "ready",
            "is_retrievable": True,
            "content_hash": "hash_cntt_001",
            "embedding_model": "text-embedding-3-small",
            "payload_schema_version": "v1",
        }
    ]

    with patch.object(indexer, "ensure_collection", new_callable=AsyncMock, return_value="col_col1"):
        count = await indexer.index_chunks("col1", valid_chunks)

    assert count == 1
    indexer.client.upsert.assert_awaited_once()
    call_args = indexer.client.upsert.call_args[1]
    points = call_args["points"]
    assert len(points) == 1
    p = points[0].payload
    assert p["tenant_id"] == "tenant_qnu"
    assert p["workspace_id"] == "ws_default"
    assert p["document_revision"] == 1
    assert p["payload_schema_version"] == "v1"
    assert p["is_retrievable"] is True
    assert p["document_status"] == "ready"


@pytest.mark.asyncio
async def test_search_dense_positive_allowlist():
    """Dense search must enforce positive allowlist filters and NO must_not exclusions."""
    indexer = VectorIndexer()
    indexer.client = AsyncMock()
    indexer._embeddings = AsyncMock()
    indexer._embeddings.aembed_query = AsyncMock(return_value=[0.1] * 1536)

    mock_hit = MagicMock()
    mock_hit.id = "p1"
    mock_hit.score = 0.95
    mock_hit.payload = {
        "chunk_id": "c1",
        "document_id": "d1",
        "content": "Quy chế đào tạo tín chỉ",
        "document_status": "ready",
        "is_retrievable": True,
        "tenant_id": "tenant_qnu",
        "workspace_id": "ws_default",
    }
    indexer.client.query_points = AsyncMock(return_value=MagicMock(points=[mock_hit]))
    indexer.client.search = AsyncMock(return_value=[mock_hit])

    results = await indexer.search_dense(
        collection_id="col1",
        query="tín chỉ",
        tenant_id="tenant_qnu",
        workspace_id="ws_default",
        top_k=5,
    )

    assert len(results) == 1
    if indexer.client.query_points.await_count > 0:
        call_args = indexer.client.query_points.call_args[1]
    else:
        call_args = indexer.client.search.call_args[1]
    query_filter = call_args["query_filter"]

    # Must be a Filter with positive must conditions
    assert isinstance(query_filter, qmodels.Filter)
    assert query_filter.must is not None
    assert query_filter.must_not is None or len(query_filter.must_not) == 0

    # Inspect the must clauses:
    field_conditions = {
        cond.key: cond.match.value for cond in query_filter.must if hasattr(cond, "match") and hasattr(cond.match, "value")
    }
    assert field_conditions.get("is_active") is True
    assert field_conditions.get("is_retrievable") is True
    assert field_conditions.get("tenant_id") == "tenant_qnu"
    assert field_conditions.get("workspace_id") == "ws_default"

    # Status must match Any ["ready", "approved"]
    status_cond = [
        cond for cond in query_filter.must if getattr(cond, "key", None) == "document_status"
    ]
    assert len(status_cond) == 1
    assert set(status_cond[0].match.any) == {"ready", "approved"}


# ============================================================================
# 2. Sparse Retriever & Facts Layer Positive Allowlist Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sparse_fts_positive_allowlist():
    """HybridRetriever.search_sparse_fts must only retrieve chunks from documents with status in ('ready', 'approved')."""
    retriever = HybridRetriever()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    )

    await retriever.search_sparse_fts(
        db=mock_db,
        collection_id="col1",
        query="học bổng",
        tenant_id="tenant_qnu",
        workspace_id="ws_default",
    )

    # Check query SQL criteria
    assert mock_db.execute.await_count >= 1
    for call in mock_db.execute.call_args_list:
        stmt = call[0][0]
        compiled = str(stmt.compile())
        assert "knowledge_documents.status" in compiled


@pytest.mark.asyncio
async def test_facts_layer_positive_allowlist():
    """FactLayer must only retrieve facts from documents with status in ('ready', 'approved')."""
    fact_layer = FactLayer()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    )

    await fact_layer.lookup_facts(
        db=mock_db,
        collection_id="col1",
        keywords=["học phí"],
        tenant_id="tenant_qnu",
        workspace_id="ws_default",
    )

    assert mock_db.execute.await_count >= 1
    call_stmt = mock_db.execute.call_args[0][0]
    compiled = str(call_stmt.compile())
    assert "knowledge_documents.status" in compiled


# ============================================================================
# 3. Semantic Cache Key Partitioning Tests
# ============================================================================


def test_semantic_cache_key_partition():
    """SemanticCache key must include tenant, workspace, collection and policy version."""
    cache = SemanticCache()

    key_v1 = cache._make_key(
        collection_id="col_admissions",
        query="điểm chuẩn CNTT",
        preferred_model="default",
        tenant_id="tenant_qnu",
        workspace_id="ws_main",
        policy_version="v1",
    )
    assert key_v1.startswith("rag:cache:tenant_qnu:ws_main:col_admissions:default:v1:")

    # Isolation check: different workspace yields different key
    key_other_ws = cache._make_key(
        collection_id="col_admissions",
        query="điểm chuẩn CNTT",
        preferred_model="default",
        tenant_id="tenant_qnu",
        workspace_id="ws_secondary",
        policy_version="v1",
    )
    assert key_v1 != key_other_ws


# ============================================================================
# 4. Document Ingestion Lifecycle State Machine Tests
# ============================================================================


@pytest.mark.asyncio
async def test_document_approval_lifecycle_to_ready():
    """Document approval must advance to 'ready' upon successful vector indexing."""
    service = IngestionService()
    mock_db = AsyncMock()

    doc = KnowledgeDocument(
        id="doc_test_1",
        collection_id="col_test",
        title="Quy chế đào tạo",
        file_name="quy_che.pdf",
        file_type="pdf",
        file_hash="hash_qc_1",
        storage_path="col_test/quy_che.pdf",
        status="review_pending",
        index_status="pending",
        is_active=True,
        version=1,
    )
    col = KnowledgeCollection(
        id="col_test",
        name="Đào tạo",
        module_code="regulations",
        tenant_id="tenant_qnu",
        workspace_id="ws_default",
    )
    chunk = KnowledgeChunk(
        id="c1",
        document_id=doc.id,
        collection_id=col.id,
        chunk_index=0,
        content="Nội dung điều 1",
        chunk_hash="h1",
    )

    service._call_get_document = AsyncMock(return_value=doc)
    service._call_get_collection = AsyncMock(return_value=col)

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None), all=MagicMock(return_value=[chunk]))))
    )

    with patch("app.modules.rag.vector_indexer.vector_indexer.index_chunks", new_callable=AsyncMock) as mock_index:
        mock_index.return_value = 1
        with patch("app.core.redis.semantic_cache.invalidate_collection", new_callable=AsyncMock):
            res = await service.approve_document(mock_db, doc.id)

    # Document must reach 'ready' and 'indexed'
    assert res["status"] == "ready"
    assert res["index_status"] == "indexed"
    assert doc.status == "ready"
    assert doc.index_status == "indexed"


@pytest.mark.asyncio
async def test_document_approval_fails_indexing_stays_approved():
    """If indexing returns 0 or fails, document must remain 'approved' with index_status='index_failed'."""
    service = IngestionService()
    mock_db = AsyncMock()

    doc = KnowledgeDocument(
        id="doc_test_fail",
        collection_id="col_test",
        title="Quy chế bị lỗi index",
        file_name="quy_che_fail.pdf",
        file_type="pdf",
        file_hash="hash_qc_fail",
        storage_path="col_test/quy_che_fail.pdf",
        status="review_pending",
        index_status="pending",
        is_active=True,
        version=1,
    )
    col = KnowledgeCollection(
        id="col_test",
        name="Đào tạo",
        module_code="regulations",
        tenant_id="tenant_qnu",
        workspace_id="ws_default",
    )
    chunk = KnowledgeChunk(
        id="c_fail",
        document_id=doc.id,
        collection_id=col.id,
        chunk_index=0,
        content="Nội dung",
        chunk_hash="h_fail",
    )

    service._call_get_document = AsyncMock(return_value=doc)
    service._call_get_collection = AsyncMock(return_value=col)

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None), all=MagicMock(return_value=[chunk]))))
    )

    with patch("app.modules.rag.vector_indexer.vector_indexer.index_chunks", new_callable=AsyncMock) as mock_index:
        mock_index.side_effect = RuntimeError("Qdrant connection timeout")

        res = await service.approve_document(mock_db, doc.id)

    # Must stay 'approved' so human review is preserved, but index_status is 'index_failed'
    assert res["status"] == "approved"
    assert res["index_status"] == "index_failed"
    assert doc.status == "approved"
    assert doc.index_status == "index_failed"


# ============================================================================
# 5. 4-Layer Reconciliation Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reconciliation_detects_discrepancies():
    """ReconciliationService must detect orphan points, legacy schemas, and missing points."""
    service = ReconciliationService()
    mock_db = AsyncMock()

    col = KnowledgeCollection(
        id="col_rec",
        name="Bộ sưu tập",
        tenant_id="tenant_qnu",
        workspace_id="ws_default",
    )
    doc = KnowledgeDocument(
        id="doc_rec_1",
        collection_id=col.id,
        title="Tài liệu 1",
        file_name="doc_rec_1.pdf",
        file_type="pdf",
        file_hash="hash_rec_1",
        storage_path="col_rec/doc_rec_1.pdf",
        status="ready",
        index_status="indexed",
        is_active=True,
        version=1,
    )
    chunk = KnowledgeChunk(
        id="chunk_db_1",
        document_id=doc.id,
        collection_id=col.id,
        chunk_index=0,
        content="Nội dung chunk",
        chunk_hash="hash_1",
    )

    service._get_collection = AsyncMock(return_value=col)

    # Mock DB query results for docs and chunks
    mock_docs_res = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[doc]))))
    mock_chunks_res = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[chunk]))))
    mock_db.execute = AsyncMock(side_effect=[mock_docs_res, mock_chunks_res])

    # Mock Qdrant points: 1 legacy point without tenant_id, 1 orphan point
    point_legacy = MagicMock(
        id="pt_legacy",
        payload={
            "chunk_id": chunk.id,
            "document_id": doc.id,
            # Missing payload_schema_version and tenant_id
        },
    )
    point_orphan = MagicMock(
        id="pt_orphan",
        payload={
            "chunk_id": "non_existent_chunk",
            "document_id": "non_existent_doc",
            "payload_schema_version": "v1",
            "tenant_id": "tenant_qnu",
            "workspace_id": "ws_default",
            "is_retrievable": True,
            "document_status": "ready",
        },
    )

    with patch("app.modules.rag.vector_indexer.vector_indexer.client") as mock_qdrant_client:
        mock_qdrant_client.count = AsyncMock(return_value=MagicMock(count=2))
        mock_qdrant_client.scroll = AsyncMock(return_value=([point_legacy, point_orphan], None))

        with patch("app.core.storage.storage_service.exists", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = True

            report = await service.reconcile_collection(mock_db, col.id)

    assert report["db_documents_count"] == 1
    assert report["db_chunks_count"] == 1
    assert report["qdrant_points_count"] == 2

    disc_types = [d["type"] for d in report["discrepancies"]]
    assert "legacy_payload_schema" in disc_types
    assert "orphan_qdrant_point" in disc_types
