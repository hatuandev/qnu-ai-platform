"""Tests for Retrieval Engine V2 & Consistency Guarantees (ADR-011 Phase 4)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeCollection
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.fusion import FusionCandidate, reciprocal_rank_fusion
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import (
    AskRequest,
    RetrievalSnapshot,
    SearchRequest,
)
from app.modules.rag.service import RagService
from app.modules.rag.vector_indexer import vector_indexer
from app.workers.tasks import task_knowledge_index_build


def test_retrieval_snapshot_schema():
    """Verify RetrievalSnapshot schema initialization and immutability attributes."""
    snap = RetrievalSnapshot(
        snapshot_id="snap_col_test_1_abc123",
        collection_id="col_test",
        collection_epoch=2,
        binding_revisions={"bnd_1": "idx_rev_1", "bnd_2": "idx_rev_2"},
    )
    assert snap.snapshot_id == "snap_col_test_1_abc123"
    assert snap.collection_id == "col_test"
    assert snap.collection_epoch == 2
    assert snap.binding_revisions["bnd_1"] == "idx_rev_1"
    assert snap.binding_revisions["bnd_2"] == "idx_rev_2"
    assert snap.created_at is not None


@pytest.mark.asyncio
async def test_resolve_retrieval_snapshot_pinned():
    """Verify a pinned snapshot is honored only after current-state validation."""
    existing_snap = RetrievalSnapshot(
        snapshot_id="snap_pinned_123",
        collection_id="col_admissions",
        collection_epoch=3,
        binding_revisions={"bnd_adm": "idx_rev_adm_1"},
    )
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.get.return_value = KnowledgeCollection(
        id="col_admissions",
        name="Tuyển sinh",
        index_epoch=3,
    )
    bindings_result = MagicMock()
    bindings_result.all.return_value = [
        ("bnd_adm", "idx_rev_adm_1", None),
    ]
    mock_db.execute.return_value = bindings_result
    resolved = await hybrid_retriever.resolve_retrieval_snapshot(
        mock_db, "col_admissions", pinned_snapshot=existing_snap
    )
    assert resolved == existing_snap
    assert resolved.snapshot_id == "snap_pinned_123"
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_retrieval_snapshot_from_db():
    """Verify dynamic snapshot resolution from DB with epoch and active bindings."""
    mock_db = AsyncMock(spec=AsyncSession)

    mock_db.get.return_value = KnowledgeCollection(
        id="col_target",
        name="Target",
        index_epoch=5,
    )

    mock_bindings_res = MagicMock()
    mock_bindings_res.all.return_value = [
        ("bnd_doc1", "idx_rev_doc1_active", "vg_1"),
        ("bnd_doc2", "idx_rev_doc2_active", "vg_1"),
    ]
    mock_db.execute.return_value = mock_bindings_res

    snap = await hybrid_retriever.resolve_retrieval_snapshot(mock_db, "col_target")
    assert snap.collection_id == "col_target"
    assert snap.collection_epoch == 5
    assert snap.binding_revisions == {
        "bnd_doc1": "idx_rev_doc1_active",
        "bnd_doc2": "idx_rev_doc2_active",
    }
    assert snap.snapshot_id.startswith("snap_col_target_5_")


def test_fusion_candidate_and_rrf_with_revision_metadata():
    """Verify reciprocal_rank_fusion preserves binding and revision metadata."""
    dense_results = [
        {
            "chunk_id": "chk_1",
            "document_id": "doc_1",
            "content": "Quy định về xét tuyển thẳng",
            "section": "Điều 1",
            "page_number": 2,
            "metadata": {"doc_priority": 8},
            "binding_id": "bnd_1",
            "index_revision_id": "idx_rev_active_1",
            "document_revision": 2,
        }
    ]
    sparse_results = [
        {
            "chunk_id": "chk_1",
            "document_id": "doc_1",
            "content": "Quy định về xét tuyển thẳng",
            "binding_id": "bnd_1",
            "index_revision_id": "idx_rev_active_1",
            "document_revision": 2,
        },
        {
            "chunk_id": "chk_2",
            "document_id": "doc_2",
            "content": "Chỉ tiêu tuyển sinh năm 2026",
            "binding_id": "bnd_2",
            "index_revision_id": "idx_rev_active_2",
            "document_revision": 1,
        },
    ]

    fused = reciprocal_rank_fusion(dense_results, sparse_results)
    assert len(fused) == 2
    top = fused[0]
    assert top.chunk_id == "chk_1"
    assert top.binding_id == "bnd_1"
    assert top.index_revision_id == "idx_rev_active_1"
    assert top.document_revision == 2

    second = fused[1]
    assert second.chunk_id == "chk_2"
    assert second.binding_id == "bnd_2"
    assert second.index_revision_id == "idx_rev_active_2"
    assert second.document_revision == 1


def test_citation_guard_build_citations_with_revisions():
    """Verify CitationGuard builds Citations with auditable revision IDs."""
    candidates = [
        FusionCandidate(
            chunk_id="chk_abc",
            document_id="doc_xyz",
            content="Mức học phí năm học 2026 là 15 triệu/kỳ.",
            rrf_score=0.85,
            section="Khoản 2 Điều 10",
            page_number=5,
            metadata={"source_revision_id": "drev_source_001"},
            binding_id="bnd_finance",
            index_revision_id="idx_rev_finance_3",
            document_revision=3,
        )
    ]

    citations = citation_guard.build_citations(candidates)
    assert len(citations) == 1
    cit = citations[0]
    assert cit.source_id == "doc_xyz"
    assert cit.binding_id == "bnd_finance"
    assert cit.index_revision_id == "idx_rev_finance_3"
    assert cit.source_revision_id == "drev_source_001"
    assert cit.revision_no == 3


@pytest.mark.asyncio
async def test_vector_indexer_search_dense_snapshot_filtering():
    """Verify search_dense filters out points from non-active index revisions (Snapshot Isolation)."""
    hit_active = MagicMock()
    hit_active.id = "p1"
    hit_active.score = 0.88
    hit_active.payload = {
        "chunk_id": "chk_active",
        "document_id": "doc_1",
        "content": "Văn bản mới nhất",
        "binding_id": "bnd_1",
        "index_revision_id": "idx_rev_active",
        "document_revision": 2,
        "document_status": "ready",
        "is_active": True,
        "is_retrievable": True,
    }

    hit_staging = MagicMock()
    hit_staging.id = "p2"
    hit_staging.score = 0.95
    hit_staging.payload = {
        "chunk_id": "chk_staging",
        "document_id": "doc_1",
        "content": "Văn bản đang staging chưa kích hoạt",
        "binding_id": "bnd_1",
        "index_revision_id": "idx_rev_staging",
        "document_revision": 3,
        "document_status": "staging",
        "is_active": True,
        "is_retrievable": False,
    }

    hit_legacy = MagicMock()
    hit_legacy.id = "p3"
    hit_legacy.score = 0.75
    hit_legacy.payload = {
        "chunk_id": "chk_legacy",
        "document_id": "doc_legacy",
        "content": "Văn bản legacy không có binding_id",
        "binding_id": None,
        "index_revision_id": None,
        "document_status": "ready",
        "is_active": True,
        "is_retrievable": True,
    }

    mock_client = MagicMock()
    mock_client.search = AsyncMock(return_value=[hit_staging, hit_active, hit_legacy])
    mock_res = MagicMock()
    mock_res.points = [hit_staging, hit_active, hit_legacy]
    mock_client.query_points = AsyncMock(return_value=mock_res)

    snapshot = RetrievalSnapshot(
        snapshot_id="snap_test",
        collection_id="col_test",
        collection_epoch=1,
        binding_revisions={"bnd_1": "idx_rev_active"},
    )

    with patch.object(vector_indexer, "client", mock_client), \
         patch.object(vector_indexer, "_resolve_embedding_runtime", AsyncMock(return_value=None)), \
         patch.object(vector_indexer, "embed_texts", AsyncMock(return_value=[[0.1] * 10])):
        results = await vector_indexer.search_dense(
            collection_id="col_test",
            query="test",
            score_threshold=0.5,
            snapshot=snapshot,
        )

    # hit_staging must be filtered out because idx_rev_staging != idx_rev_active
    assert len(results) == 1
    chunk_ids = [r["chunk_id"] for r in results]
    assert "chk_staging" not in chunk_ids
    assert "chk_active" in chunk_ids
    assert "chk_legacy" not in chunk_ids


@pytest.mark.asyncio
async def test_rag_service_search_includes_snapshot():
    """Verify RagService.search returns retrieval_snapshot and revision fields."""
    rag_service = RagService()
    mock_db = AsyncMock(spec=AsyncSession)

    req = SearchRequest(
        collection_id="col_demo",
        query="hướng dẫn nộp hồ sơ",
        top_k=5,
    )

    fake_snapshot = RetrievalSnapshot(
        snapshot_id="snap_demo_1",
        collection_id="col_demo",
        collection_epoch=1,
        binding_revisions={"bnd_1": "idx_rev_1"},
    )

    fake_candidate = FusionCandidate(
        chunk_id="chk_demo",
        document_id="doc_demo",
        content="Nộp hồ sơ trực tuyến",
        rrf_score=0.9,
        binding_id="bnd_1",
        index_revision_id="idx_rev_1",
        document_revision=1,
    )

    with patch.object(hybrid_retriever, "resolve_retrieval_snapshot", AsyncMock(return_value=fake_snapshot)), \
         patch.object(hybrid_retriever, "retrieve", AsyncMock(return_value=[fake_candidate])):
        resp = await rag_service.search(mock_db, req)

    assert resp.retrieval_snapshot is not None
    assert resp.retrieval_snapshot.snapshot_id == "snap_demo_1"
    assert resp.total_found == 1
    assert resp.items[0].binding_id == "bnd_1"
    assert resp.items[0].index_revision_id == "idx_rev_1"
    assert resp.items[0].document_revision == 1


@pytest.mark.asyncio
async def test_rag_service_ask_includes_snapshot_even_on_no_answer():
    """Verify RagService.ask retains retrieval_snapshot during no-answer policy."""
    rag_service = RagService()
    mock_db = AsyncMock(spec=AsyncSession)

    req = AskRequest(
        collection_id="col_empty",
        question="câu hỏi không có trong kho",
        module_code="admissions",
    )

    fake_snapshot = RetrievalSnapshot(
        snapshot_id="snap_empty_col_1",
        collection_id="col_empty",
        collection_epoch=1,
        binding_revisions={},
    )

    with patch.object(hybrid_retriever, "resolve_retrieval_snapshot", AsyncMock(return_value=fake_snapshot)), \
         patch.object(hybrid_retriever, "retrieve", AsyncMock(return_value=[])), \
         patch("app.modules.rag.service.semantic_cache.get", AsyncMock(return_value=None)):
        resp = await rag_service.ask(mock_db, req)

    assert resp.status == "insufficient_context"
    assert resp.retrieval_snapshot is not None
    assert resp.retrieval_snapshot.snapshot_id == "snap_empty_col_1"
    assert "0256.3846.156" in resp.answer


@pytest.mark.asyncio
async def test_worker_task_knowledge_index_build_missing_payload():
    """Verify task_knowledge_index_build fails honestly when parameters are missing."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_job = MagicMock()
    mock_job.id = "job_123"
    mock_job.payload = {}  # missing binding_id and source_revision_id

    with patch("app.workers.tasks.AsyncSessionFactory", return_value=mock_db), \
         patch("app.workers.tasks._load_job", AsyncMock(return_value=mock_job)), \
         patch("app.workers.tasks._set_job", AsyncMock()) as mock_set:
        result = await task_knowledge_index_build({}, "job_123")

    assert result["status"] == "failed"
    assert "Missing" in result["error"]
    mock_set.assert_called_once()
