"""Unit & Integration Tests for Hybrid RAG Engine, RRF Fusion, Citation Guard and Facts."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.knowledge.models import KnowledgeFact
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.composer import answer_format_planner
from app.modules.rag.facts import fact_layer
from app.modules.rag.fusion import FusionCandidate, reciprocal_rank_fusion
from app.modules.rag.reranker import reranker_client


def test_reciprocal_rank_fusion():
    """Verify RRF fusion formula correctly merges dense and sparse rankings."""
    dense = [
        {
            "chunk_id": "c1",
            "content": "Ngành Công nghệ thông tin điểm chuẩn 24.5",
            "document_id": "d1",
        },
        {"chunk_id": "c2", "content": "Ngành Sư phạm Toán điểm chuẩn 26.0", "document_id": "d1"},
    ]
    sparse = [
        {"chunk_id": "c2", "content": "Ngành Sư phạm Toán điểm chuẩn 26.0", "document_id": "d1"},
        {"chunk_id": "c3", "content": "Ngành Ngôn ngữ Anh điểm chuẩn 22.0", "document_id": "d2"},
    ]

    fused = reciprocal_rank_fusion(dense, sparse, k=60)
    assert len(fused) == 3
    # c2 appears in both lists (dense rank 2, sparse rank 1), so it must have the highest RRF score!
    assert fused[0].chunk_id == "c2"
    assert fused[0].rrf_score > fused[1].rrf_score


@pytest.mark.asyncio
async def test_reranker_fallback():
    """Verify Reranker falls back to RRF ordering when external service is offline."""
    candidates = [
        FusionCandidate(chunk_id="c1", document_id="d1", content="Nội dung 1", rrf_score=0.03),
        FusionCandidate(chunk_id="c2", document_id="d1", content="Nội dung 2", rrf_score=0.02),
    ]
    reranked = await reranker_client.rerank("câu hỏi", candidates, top_k=1)
    assert len(reranked) == 1
    assert reranked[0].chunk_id == "c1"


def test_fact_markdown_formatting():
    """Verify FactLayer transforms fact entities into a clear Markdown table."""
    facts = [
        KnowledgeFact(
            collection_id="col_1",
            document_id="d1",
            entity_name="Công nghệ thông tin",
            entity_type="major",
            attribute_name="Điểm chuẩn 2024",
            attribute_value="24.5",
        ),
        KnowledgeFact(
            collection_id="col_1",
            document_id="d1",
            entity_name="Công nghệ thông tin",
            entity_type="major",
            attribute_name="Chỉ tiêu",
            attribute_value="180",
        ),
    ]
    md = fact_layer.format_facts_as_markdown(facts)
    assert "| Công nghệ thông tin | Điểm chuẩn 2024 | **24.5** |" in md
    assert "| Công nghệ thông tin | Chỉ tiêu | **180** |" in md


def test_answer_format_planner():
    """Verify AnswerFormatPlanner plans formats accurately according to user query."""
    assert (
        answer_format_planner.plan_format("Cho tôi bảng điểm chuẩn các ngành năm 2024")
        == "markdown_table"
    )
    assert answer_format_planner.plan_format("Khi nào hết hạn nộp hồ sơ xét tuyển?") == "timeline"
    assert (
        answer_format_planner.plan_format("Hồ sơ và quy trình nhập học gồm những gì?")
        == "checklist"
    )
    assert answer_format_planner.plan_format("Giới thiệu ngành Kỹ thuật phần mềm") == "bullet_list"


def test_mock_embedding_deterministic():
    """Mock vectors must be deterministic, normalized and correctly sized."""
    import math

    from app.modules.rag.vector_indexer import VectorIndexer

    vec_a = VectorIndexer.generate_embedding("Điểm chuẩn Công nghệ thông tin", 1024)
    vec_b = VectorIndexer.generate_embedding("Điểm chuẩn Công nghệ thông tin", 1024)
    assert len(vec_a) == 1024
    assert vec_a == vec_b
    assert math.isclose(sum(x * x for x in vec_a), 1.0, rel_tol=1e-6)


@pytest.mark.asyncio
async def test_embed_texts_falls_back_without_model():
    """embed_texts must return mock vectors (never crash) when ST is missing."""
    from unittest.mock import patch

    from app.modules.rag.vector_indexer import VectorIndexer

    indexer = VectorIndexer()
    with patch("app.modules.rag.vector_indexer._get_embedding_model", return_value=None):
        vectors = await indexer.embed_texts(["hoc phi", "chi tieu"])
    assert len(vectors) == 2
    assert all(len(v) == indexer.vector_size for v in vectors)
    assert vectors[0] != vectors[1]


def test_fit_dim_pads_and_truncates():
    """Model vectors must be fitted exactly to the Qdrant dimension."""
    from app.modules.rag.vector_indexer import VectorIndexer

    indexer = VectorIndexer()
    assert len(indexer._fit_dim([0.5] * 2048)) == indexer.vector_size
    assert len(indexer._fit_dim([0.5] * 10)) == indexer.vector_size


def test_citation_guard_no_answer():
    """Verify CitationGuard returns polite rejection policy when context is insufficient."""
    msg_admissions = citation_guard.get_no_answer_response("admissions")
    assert "0256.3846.156" in msg_admissions
    assert "tuyensinh@qnu.edu.vn" in msg_admissions


@pytest.mark.asyncio
async def test_api_rag_ask_no_context():
    """Verify POST /platform/v1alpha1/rag/ask enforces refusal policy when DB has no chunks."""
    from unittest.mock import AsyncMock, patch

    from app.core.database import get_db

    payload = {
        "question": "Điểm chuẩn ngành Trí tuệ nhân tạo năm 2030 là bao nhiêu?",
        "collection_id": "col_empty_test",
        "module_code": "admissions",
    }

    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with (
            patch(
                "app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock
            ) as mock_ret,
            patch(
                "app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock
            ) as mock_facts,
        ):
            mock_ret.return_value = []
            mock_facts.return_value = []

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/platform/v1alpha1/rag/ask", json=payload)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_context"
    assert "0256.3846.156" in data["answer"]  # Returns polite QNU admissions hotline
