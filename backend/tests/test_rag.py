"""Unit & Integration Tests for Hybrid RAG Engine, RRF Fusion, Citation Guard and Facts."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.knowledge.models import KnowledgeFact
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.composer import answer_format_planner
from app.modules.rag.facts import fact_layer
from app.modules.rag.fusion import FusionCandidate, reciprocal_rank_fusion
from app.modules.rag.reranker import reranker_client
from app.modules.rag.schemas import RetrievalSnapshot


@pytest.fixture(autouse=True)
def _pin_rag_snapshot_for_unit_tests():
    async def resolve(*args, **kwargs):
        collection_id = args[1] if len(args) > 1 else kwargs["collection_id"]
        return RetrievalSnapshot(
            snapshot_id=f"snap_{collection_id}_test",
            collection_id=collection_id,
            collection_epoch=1,
            binding_revisions={"bnd_test": "idx_test"},
            tenant_id=kwargs.get("tenant_id"),
            workspace_id=kwargs.get("workspace_id"),
        )

    with patch(
        "app.modules.rag.service.hybrid_retriever.resolve_retrieval_snapshot",
        new=AsyncMock(side_effect=resolve),
    ):
        yield


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


def test_reciprocal_rank_fusion_legal_priority_boost():
    """Verify legal priority weighting (priority 10 vs 5) breaks ties and boosts authoritative docs."""
    # c1 (standard, priority 5) and c2 (core regulation, priority 10) both appear at rank 1 in their respective lists
    dense = [
        {"chunk_id": "c1", "content": "Tin tức chung", "document_id": "d1", "metadata": {"priority": 5}},
    ]
    sparse = [
        {"chunk_id": "c2", "content": "Quy chế Đào tạo", "document_id": "d2", "metadata": {"priority": 10}},
    ]
    fused = reciprocal_rank_fusion(dense, sparse, k=60)
    # Both have base RRF score 1/(60+1) = 0.016393...
    # But c2 has priority 10 -> multiplier 1.0 + (10-5)*0.02 = 1.10 (+10%)
    # Thus c2 MUST rank first over c1!
    assert fused[0].chunk_id == "c2"
    assert fused[0].rrf_score > fused[1].rrf_score
    assert fused[0].rrf_score == pytest.approx(fused[1].rrf_score * 1.10)



@pytest.mark.asyncio
async def test_reranker_fallback():
    """Verify Reranker falls back to RRF ordering when external service is offline."""
    from unittest.mock import AsyncMock, patch

    from app.modules.modelops.services.model_runtime_resolver import ModelRuntimeConfig

    candidates = [
        FusionCandidate(chunk_id="c1", document_id="d1", content="Nội dung 1", rrf_score=0.03),
        FusionCandidate(chunk_id="c2", document_id="d1", content="Nội dung 2", rrf_score=0.02),
    ]
    runtime = ModelRuntimeConfig(
        provider_id="prov_cloudflare",
        provider_type="cloudflare",
        model_name="@cf/baai/bge-reranker-base",
        api_base_url=None,
        api_key="test-token",
        account_id="test-account",
        timeout_seconds=3,
    )
    with (
        patch.object(
            reranker_client,
            "_resolve_reranker_runtime",
            new_callable=AsyncMock,
            return_value=runtime,
        ),
        patch.object(
            reranker_client,
            "_rerank_cloudflare",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Cloudflare API offline"),
        ),
    ):
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
async def test_cloudflare_embedding_fails_closed_without_credentials():
    """Cloudflare configuration failures must fail closed."""
    from unittest.mock import AsyncMock, patch

    from app.core.exceptions import AppException
    from app.modules.modelops.services.model_runtime_resolver import ModelRuntimeConfig
    from app.modules.rag.vector_indexer import VectorIndexer

    indexer = VectorIndexer()
    runtime = ModelRuntimeConfig(
        provider_id="prov_cloudflare",
        provider_type="cloudflare",
        model_name="@cf/baai/bge-m3",
        api_base_url=None,
        api_key=None,
        account_id=None,
        timeout_seconds=20,
    )
    with (
        patch.object(
            indexer,
            "_resolve_embedding_runtime",
            new_callable=AsyncMock,
            return_value=runtime,
        ),
        pytest.raises(AppException) as exc_info,
    ):
        await indexer.embed_texts(["hoc phi"])

    assert exc_info.value.code == "EMBEDDING_PROVIDER_NOT_CONFIGURED"


def test_fit_dim_strict_dimension_invariant():
    """Model vectors must match exactly the Qdrant dimension. Truncation or padding is strictly rejected."""
    from app.core.exceptions import AppException
    from app.modules.rag.vector_indexer import VectorIndexer

    indexer = VectorIndexer()
    assert len(indexer._fit_dim([0.5] * indexer.vector_size)) == indexer.vector_size

    with pytest.raises(AppException) as exc_info:
        indexer._fit_dim([0.5] * (indexer.vector_size + 100))
    assert exc_info.value.code == "VECTOR_DIMENSION_MISMATCH"

    with pytest.raises(AppException) as exc_info:
        indexer._fit_dim([0.5] * 10)
    assert exc_info.value.code == "VECTOR_DIMENSION_MISMATCH"


def test_citation_guard_no_answer():
    """Verify CitationGuard returns polite rejection policy when context is insufficient."""
    msg_admissions = citation_guard.get_no_answer_response("admissions")
    assert "0256.3846.156" in msg_admissions
    assert "tuyensinh@qnu.edu.vn" in msg_admissions


def test_citation_guard_strict_filtering_zero_false_positive():
    """Verify CitationGuard returns 0 citations when answer does not contain evidence from candidate quote."""
    from app.modules.rag.schemas import Citation

    candidates = [
        Citation(
            source_id="doc_1",
            title="Quy chế đào tạo",
            quote="Sinh viên phải tích lũy tối thiểu 120 tín chỉ để được xét tốt nghiệp đại học.",
        ),
        Citation(
            source_id="doc_2",
            title="Quy định thư viện",
            quote="Mỗi sinh viên được mượn tối đa 5 cuốn sách trong vòng 14 ngày.",
        ),
    ]

    # Case 1: Hallucinated / completely off-topic answer with no word overlap
    hallucinated_answer = "Món phở bò tái lăn Hà Nội thơm ngon đậm đà hành lá và gừng tươi."
    filtered = citation_guard.filter_evidence_citations(candidates, hallucinated_answer)
    assert filtered == []  # Zero false-positive citations!

    # Case 2: Refusal answer should return zero citations
    refusal_answer = "Thông tin này hiện chưa có trong tài liệu chính thức, vui lòng liên hệ hotline."
    filtered_refusal = citation_guard.filter_evidence_citations(candidates, refusal_answer)
    assert filtered_refusal == []

    # Case 3: Evidenced answer with sufficient word overlap
    evidenced_answer = "Theo quy chế, sinh viên phải tích lũy tối thiểu 120 tín chỉ để tốt nghiệp."
    filtered_evidenced = citation_guard.filter_evidence_citations(candidates, evidenced_answer)
    assert len(filtered_evidenced) == 1
    assert filtered_evidenced[0].source_id == "doc_1"


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


@pytest.mark.asyncio
async def test_api_rag_ask_with_modelops_synthesis():
    """Verify RagService.ask calls ModelOps generate and returns synthesized answer with citations."""
    from unittest.mock import AsyncMock, patch

    from app.core.database import get_db
    from app.modules.modelops.schemas import LLMGenerateResponse
    from app.modules.modelops.service import modelops_service
    from app.modules.rag.fusion import FusionCandidate

    payload = {
        "question": "Học phí ngành CNTT năm 2024?",
        "collection_id": "col_admissions",
        "module_code": "admissions",
    }

    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    candidate = FusionCandidate(
        chunk_id="chk_1",
        document_id="doc_1",
        content="Học phí ngành Công nghệ thông tin là 16.500.000 VNĐ một năm.",
        rrf_score=0.95,
        section="Học phí",
        page_number=3,
        metadata={"title": "Thông báo Học phí QNU"},
    )

    mock_llm_res = LLMGenerateResponse(
        content="Dựa trên thông báo chính thức của QNU, học phí ngành CNTT là 16.500.000 VNĐ/năm.",
        provider="openai",
        model="gpt-4o-mini",
        prompt_tokens=150,
        completion_tokens=30,
        total_tokens=180,
    )

    app.dependency_overrides[get_db] = override_get_db
    try:
        with (
            patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock, return_value=None),
            patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_ret,
            patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_facts,
            patch.object(modelops_service, "generate", new_callable=AsyncMock) as mock_gen,
        ):
            mock_ret.return_value = [candidate]
            mock_facts.return_value = []
            mock_gen.return_value = mock_llm_res

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/platform/v1alpha1/rag/ask", json=payload)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "16.500.000 VNĐ" in data["answer"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["source_id"] == "doc_1"
    mock_gen.assert_awaited_once()


@pytest.mark.asyncio
async def test_rag_ask_dynamic_fallback_model():
    """Verify RagService invokes fallback_model when primary_model generation fails."""
    from unittest.mock import AsyncMock, patch

    from app.core.database import get_db
    from app.modules.modelops.schemas import LLMGenerateRequest, LLMGenerateResponse
    from app.modules.modelops.service import modelops_service
    from app.modules.rag.fusion import FusionCandidate

    payload = {
        "question": "Học phí ngành CNTT năm 2024?",
        "collection_id": "col_admissions",
        "module_code": "admissions",
        "preferred_model_name": "gpt-4o-mini",
        "fallback_model": "gemini-1.5-flash",
    }

    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    candidate = FusionCandidate(
        chunk_id="chk_1",
        document_id="doc_1",
        content="Học phí ngành Công nghệ thông tin là 16.500.000 VNĐ một năm.",
        rrf_score=0.95,
        section="Học phí",
        page_number=3,
        metadata={"title": "Thông báo Học phí QNU"},
    )

    fallback_llm_res = LLMGenerateResponse(
        content="Theo tài liệu chính thức, học phí ngành CNTT là 16.500.000 VNĐ/năm.",
        provider="google",
        model="gemini-1.5-flash",
        prompt_tokens=150,
        completion_tokens=30,
        total_tokens=180,
    )

    async def side_effect_generate(db: object, req: LLMGenerateRequest):
        if req.preferred_model_name == "gpt-4o-mini":
            raise RuntimeError("Primary OpenAI service 503 Rate Limit")
        return fallback_llm_res

    app.dependency_overrides[get_db] = override_get_db
    try:
        with (
            patch("app.modules.rag.service.semantic_cache.get", new_callable=AsyncMock, return_value=None),
            patch("app.modules.rag.service.hybrid_retriever.retrieve", new_callable=AsyncMock) as mock_ret,
            patch("app.modules.rag.service.fact_layer.lookup_facts", new_callable=AsyncMock) as mock_facts,
            patch.object(modelops_service, "generate", new_callable=AsyncMock, side_effect=side_effect_generate) as mock_gen,
        ):
            mock_ret.return_value = [candidate]
            mock_facts.return_value = []

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/platform/v1alpha1/rag/ask", json=payload)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "16.500.000 VNĐ" in data["answer"]
    # ModelOps was called twice: 1st for primary (failed), 2nd for fallback (succeeded)
    assert mock_gen.await_count == 2


@pytest.mark.asyncio
async def test_fact_layer_filters_by_document_approval_lifecycle():
    """Verify FactLayer constructs query with KnowledgeDocument outerjoin and lifecycle filters."""
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.knowledge.models import KnowledgeFact
    from app.modules.rag.facts import FactLayer

    layer = FactLayer()
    mock_db = AsyncMock()
    mock_res = MagicMock()

    fake_fact = KnowledgeFact(
        id="fct_test",
        collection_id="col_admissions",
        document_id="doc_approved_1",
        entity_name="Công nghệ thông tin",
        entity_type="major",
        attribute_name="điểm chuẩn",
        attribute_value="24.5",
        confidence=1.0,
    )
    mock_res.scalars.return_value.all.return_value = [fake_fact]
    mock_db.execute.return_value = mock_res

    results = await layer.lookup_facts(
        db=mock_db,
        collection_id="col_admissions",
        keywords=["Công nghệ thông tin"],
    )

    assert len(results) == 1
    assert results[0].entity_name == "Công nghệ thông tin"

    assert mock_db.execute.called
    called_query = mock_db.execute.call_args[0][0]
    compiled_sql = str(called_query.compile())

    # Verify KnowledgeDocument join and status filters exist in compiled SQL
    assert "knowledge_documents" in compiled_sql
    assert "knowledge_facts.document_id = knowledge_documents.id" in compiled_sql
    assert "knowledge_documents.is_active" in compiled_sql
    assert "knowledge_collections" in compiled_sql


@pytest.mark.asyncio
async def test_sparse_fts_handles_empty_or_short_query_without_unbound_local():
    """Verify search_sparse_fts never crashes with UnboundLocalError on short or stop-word-only queries."""
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.rag.retriever import hybrid_retriever

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    # Query with 1 character (meaningful_tokens is empty)
    res_short = await hybrid_retriever.search_sparse_fts(
        db=mock_db,
        collection_id="col_admissions",
        query="a",
        top_k=5,
    )
    assert isinstance(res_short, list)
    assert len(res_short) == 0

    # Query with only stop syllables
    res_stop = await hybrid_retriever.search_sparse_fts(
        db=mock_db,
        collection_id="col_admissions",
        query="như thế nào",
        top_k=5,
    )
    assert isinstance(res_stop, list)


@pytest.mark.asyncio
async def test_search_dense_gracefully_degrades_when_embedding_fails():
    """Verify search_dense catches embedding exceptions and returns empty list for graceful degradation."""
    from unittest.mock import AsyncMock, patch

    from app.modules.rag.vector_indexer import vector_indexer

    with patch.object(
        vector_indexer,
        "embed_texts",
        new_callable=AsyncMock,
        side_effect=Exception("Embedding model offline / GPU out of memory"),
    ):
        results = await vector_indexer.search_dense(
            collection_id="col_admissions",
            query="Điểm chuẩn ngành công nghệ thông tin",
            top_k=5,
        )
        assert results == []


def test_extract_suggested_questions_cleans_passive_boilerplate_and_parses_block():
    """Verify extract_suggested_questions strips boilerplate trailing questions and extracts suggestions."""
    from app.modules.rag.composer import extract_suggested_questions

    # Case 1: Passive trailing question converted and stripped
    raw_1 = (
        "Chào bạn! Ngành Công nghệ thông tin xét tuyển các môn: Toán, Lý, Hóa.\n\n"
        "Bạn có muốn mình chia sẻ thêm về chỉ tiêu tuyển sinh hoặc các phương thức xét tuyển áp dụng cho các ngành này không?"
    )
    clean_1, sugs_1 = extract_suggested_questions(raw_1)
    assert "Bạn có muốn mình chia sẻ thêm" not in clean_1
    assert len(sugs_1) == 2
    assert "phương thức" in sugs_1[0].lower() or "chỉ tiêu" in sugs_1[0].lower()

    # Case 2: Explicit [GỢI Ý] block parsed and stripped
    raw_2 = (
        "Chào bạn! Điểm chuẩn ngành Sư phạm Toán là 26.5 điểm.\n\n"
        "[GỢI Ý]:\n"
        "- \"Học phí ngành Sư phạm Toán năm 2026 là bao nhiêu?\"\n"
        "- \"Trường có chính sách học bổng nào cho ngành này không?\""
    )
    clean_2, sugs_2 = extract_suggested_questions(raw_2)
    assert "[GỢI Ý]" not in clean_2
    assert "26.5 điểm." in clean_2
    assert len(sugs_2) == 2
    assert sugs_2[0] == "Học phí ngành Sư phạm Toán năm 2026 là bao nhiêu?"
    assert sugs_2[1] == "Trường có chính sách học bổng nào cho ngành này không?"


def test_extract_weighted_tokens_and_information_density():
    """Verify that extract_weighted_tokens prioritizes high-entropy codes, numbers, and acronyms."""
    from app.modules.rag.retriever import extract_weighted_tokens, select_ilike_tokens

    # Case 1: Query with alphanumeric combinations X06, X07, X25 and document number 123
    q1 = "Theo Thông báo số 123/TB-ĐHQN về việc quy đổi tương đương các môn xét tuyển, các tổ hợp xét tuyển X06, X07, X25 được quy đổi tương đương sang các tổ hợp gốc nào?"
    tokens_w = extract_weighted_tokens(q1, limit=10)
    token_dict = dict(tokens_w)

    assert "x06" in token_dict and token_dict["x06"] >= 3.5
    assert "x07" in token_dict and token_dict["x07"] >= 3.5
    assert "x25" in token_dict and token_dict["x25"] >= 3.5
    # Institutional acronym 'đhqn' is filtered into ILIKE_STOP_SYLLABLES to avoid matching every school document
    assert "đhqn" not in token_dict

    # Ensure top 3 tokens in select_ilike_tokens are the high-entropy alphanumeric codes
    top_ilike = select_ilike_tokens(q1, limit=5)
    assert "x06" in top_ilike
    assert "x07" in top_ilike
    assert "x25" in top_ilike

    # Case 2: Query with field-specific acronym CNTT and year 2026
    q_acr = "Học phí ngành CNTT năm 2026"
    tokens_acr = dict(extract_weighted_tokens(q_acr))
    assert "cntt" in tokens_acr and tokens_acr["cntt"] >= 2.5
    assert "2026" in tokens_acr and tokens_acr["2026"] >= 3.0

    # Case 3: Query with Year numbers 2025 vs 2026
    q2 = "Báo cáo thực hiện chỉ tiêu tuyển sinh năm 2025 so với năm 2026"
    tokens_q2 = dict(extract_weighted_tokens(q2))
    assert "2025" in tokens_q2 and tokens_q2["2025"] >= 3.0
    assert "2026" in tokens_q2 and tokens_q2["2026"] >= 3.0

