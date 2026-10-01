"""Unit tests for Phase 2: Dynamic Specificity, Document Anchor Scoping, and RRF-CE Fusion."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.reranker import reranker_client
from app.modules.rag.retriever import (
    RE_ACRONYM,
    RE_ALPHANUMERIC,
    RE_NUMERIC_CODE,
    extract_weighted_tokens,
    hybrid_retriever,
    select_ilike_tokens,
)


def test_token_information_density_weighting():
    """Verify that information density scoring correctly prioritizes alphanumeric codes, numbers, and acronyms."""
    query = "Theo Thông báo số 123/TB-ĐHQN về việc quy đổi tương đương các môn xét tuyển, các tổ hợp xét tuyển X06, X07, X25 được quy đổi tương đương sang các tổ hợp gốc nào?"
    weighted = extract_weighted_tokens(query, limit=12)
    token_dict = dict(weighted)

    # 1. Alphanumeric codes get highest weight (4.0)
    assert token_dict.get("x06") == 4.0
    assert token_dict.get("x07") == 4.0
    assert token_dict.get("x25") == 4.0

    # 2. Document number gets weight 3.5
    assert token_dict.get("123") == 3.5

    # 3. Announcement & university boilerplate are stripped
    assert "thông" not in token_dict
    assert "báo" not in token_dict
    assert "đhqn" not in token_dict
    assert "tổ" not in token_dict
    assert "các" not in token_dict
    assert "xét" not in token_dict
    assert "tuyển" not in token_dict

    # 4. Long descriptive words get 1.2 or 1.8, short syllables get 0.2
    assert token_dict.get("tương") == 1.2
    assert token_dict.get("đương") == 1.2
    assert token_dict.get("gốc") == 0.2
    assert token_dict.get("đổi") == 0.2

    # 5. Top ILIKE tokens are the high-entropy codes
    top_ilike = select_ilike_tokens(query, limit=4)
    assert "x06" in top_ilike
    assert "x07" in top_ilike
    assert "x25" in top_ilike
    assert "123" in top_ilike


def test_morphology_regex_patterns():
    """Verify regex pattern classification for domain entities."""
    # Alphanumeric codes
    for code in ["X06", "x07", "X25", "PT1", "PT2", "BC03", "TB123"]:
        assert RE_ALPHANUMERIC.match(code), f"Expected {code} to match RE_ALPHANUMERIC"

    # Numeric codes (3-8 digits)
    for num in ["123", "1897", "2025", "2026", "7480201", "5028"]:
        assert RE_NUMERIC_CODE.match(num), f"Expected {num} to match RE_NUMERIC_CODE"

    # Acronyms
    for acr in ["CNTT", "GDĐT", "KHTN", "KHXH", "VSTEP", "IELTS"]:
        assert RE_ACRONYM.match(acr), f"Expected {acr} to match RE_ACRONYM"


@pytest.mark.asyncio
async def test_search_sparse_fts_constructs_document_anchor_boost():
    """Verify search_sparse_fts creates SQL statement with Document Anchor Scoping."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    query = "Báo cáo 1897 điều kiện giảng viên"
    await hybrid_retriever.search_sparse_fts(
        db=mock_db,
        collection_id="col_admissions",
        query=query,
        top_k=5,
    )

    assert mock_db.execute.called
    # The first execute call is the primary weighted ILIKE search with document anchor scoping
    primary_query = mock_db.execute.call_args_list[0][0][0]
    compiled_sql = str(primary_query.compile())

    # Verify joins on documents and collections exist
    assert "knowledge_documents" in compiled_sql
    assert "knowledge_collections" in compiled_sql
    # Verify both content and filename/title are queried
    assert "knowledge_chunks.content" in compiled_sql
    assert "knowledge_documents.file_name" in compiled_sql or "file_name" in compiled_sql


@pytest.mark.asyncio
async def test_rrf_ce_rank_fusion_preserves_tabular_rank():
    """Verify RRF-CE rank fusion prevents Cloudflare Cross-Encoder from dropping tabular chunks."""
    from unittest.mock import patch

    from app.modules.modelops.services.model_runtime_resolver import ModelRuntimeConfig

    # Candidate 1: Markdown table chunk with exact codes (Rank 1 in RRF, but penalized by Cross-Encoder to rank 7)
    c1 = FusionCandidate(
        chunk_id="chk_table",
        document_id="doc_1",
        content="| STT | Mã tổ hợp | Tên môn | Tổ hợp gốc tương đương |\n| 10 | X06 | Toán, Tin học, Tiếng Anh | A01 |",
        rrf_score=0.035,
    )
    # Candidate 2: Prose narrative chunk (Rank 2 in RRF, favored by Cross-Encoder to rank 1)
    c2 = FusionCandidate(
        chunk_id="chk_prose",
        document_id="doc_1",
        content="Điểm quy đổi được tính tương đương sang tổ hợp gốc theo công thức chính thức của trường.",
        rrf_score=0.034,
    )
    # Candidate 3: Irrelevant document chunk (Rank 5 in RRF, middle in Cross-Encoder)
    c3 = FusionCandidate(
        chunk_id="chk_irrelevant",
        document_id="doc_2",
        content="Quy định chung về hoạt động sinh viên trong năm học.",
        rrf_score=0.020,
    )

    candidates = [c1, c2, c3]

    # Mock Cloudflare response where CE gives c2 high score (0.95), c3 medium (0.40), and c1 low score (0.01)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": {
            "response": [
                {"id": 0, "score": 0.01},  # c1 (table)
                {"id": 1, "score": 0.95},  # c2 (prose)
                {"id": 2, "score": 0.40},  # c3 (irrelevant)
            ]
        }
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    runtime = ModelRuntimeConfig(
        provider_id="prov_cf",
        provider_type="cloudflare",
        model_name="bge-reranker-base",
        api_base_url="https://api.cloudflare.com",
        api_key="fake_key",
        account_id="fake_account",
        timeout_seconds=10,
    )

    with (
        patch.object(reranker_client, "_resolve_reranker_runtime", new_callable=AsyncMock, return_value=runtime),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        reranked = await reranker_client.rerank(
            query="Tổ hợp X06 quy đổi sang tổ hợp gốc nào?",
            candidates=candidates,
            top_k=2,
        )

    assert len(reranked) == 2
    reranked_ids = [c.chunk_id for c in reranked]
    # In old behavior, c1 would be dropped because score 0.01 placed it last (behind c3).
    # With RRF-CE rank fusion, c1 MUST be in the top 2!
    assert "chk_table" in reranked_ids
    assert "chk_prose" in reranked_ids
