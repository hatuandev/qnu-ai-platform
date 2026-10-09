"""Unit Tests for vLLM & TEI Native Integration (Reranker, Embedding, LLM Adapter)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.providers.openai_adapter import OpenAIAdapter
from app.modules.modelops.services.model_runtime_resolver import ModelRuntimeConfig
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.reranker import reranker_client
from app.modules.rag.vector_indexer import vector_indexer


@pytest.mark.asyncio
async def test_reranker_vllm_native_scoring():
    """Verify that vLLM /v1/rerank response is correctly parsed and fused."""
    candidates = [
        FusionCandidate(
            chunk_id="c1",
            document_id="d1",
            content="Hà Nội là thủ đô của Việt Nam.",
            rrf_score=0.03,
        ),
        FusionCandidate(
            chunk_id="c2",
            document_id="d1",
            content="Trường Đại học Quy Nhơn tọa lạc tại thành phố Quy Nhơn.",
            rrf_score=0.02,
        ),
    ]
    runtime = ModelRuntimeConfig(
        provider_id="prov_vllm_server",
        provider_type="vllm",
        model_name="bge-reranker-v2-m3",
        api_base_url="http://tormemrtxproto.tail0924dd.ts.net:8002/v1",
        api_key=None,
        account_id=None,
        timeout_seconds=5,
    )
    mock_post_resp = AsyncMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "results": [
            {"index": 1, "relevance_score": 0.999855},
            {"index": 0, "relevance_score": 0.009544},
        ]
    }

    with (
        patch.object(
            reranker_client,
            "_resolve_reranker_runtime",
            new_callable=AsyncMock,
            return_value=runtime,
        ),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_post_resp),
    ):
        ranked = await reranker_client.rerank(
            "Trường Đại học Quy Nhơn nằm ở đâu?", candidates, top_k=2
        )

    assert len(ranked) == 2
    assert ranked[0].chunk_id == "c2"
    assert ranked[0].rrf_score > ranked[1].rrf_score
    assert ranked[1].chunk_id == "c1"


def test_vllm_llm_adapter_factory():
    """Verify get_llm_adapter supports provider_type='vllm'."""
    adapter = get_llm_adapter(
        provider_type="vllm",
        model_name="Qwen/Qwen2.5-7B-Instruct",
        base_url="http://127.0.0.1:8000/v1",
    )
    assert isinstance(adapter, OpenAIAdapter)
    assert adapter.provider_type == "vllm"
    assert adapter.model_name == "Qwen/Qwen2.5-7B-Instruct"


@pytest.mark.asyncio
async def test_vllm_embedding_generation():
    """Verify vector_indexer calls /v1/embeddings for vLLM provider."""
    runtime = ModelRuntimeConfig(
        provider_id="prov_vllm_embed",
        provider_type="vllm",
        model_name="bge-m3",
        api_base_url="http://tormemrtxproto.tail0924dd.ts.net:8001/v1",
        api_key=None,
        account_id=None,
        timeout_seconds=5,
    )
    mock_post_resp = AsyncMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "data": [
            {"index": 0, "embedding": [0.1] * 1024},
            {"index": 1, "embedding": [0.2] * 1024},
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_post_resp) as mock_post:
        vectors = await vector_indexer.embed_texts(["văn bản 1", "văn bản 2"], runtime=runtime)

    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    assert vectors[0][0] == pytest.approx(0.1)
    assert vectors[1][0] == pytest.approx(0.2)
    mock_post.assert_called_once()
    assert "/v1/embeddings" in mock_post.call_args[0][0]


def test_vllm_seed_provider_config():
    """Verify prov_rtx5090_vllm is configured with BGE-M3, BGE-Reranker-v2-M3, and Qwen3-Embedding-4B."""
    from app.modules.modelops.services.provider_service import STANDARD_QNU_PROVIDERS

    provider_ids = [p["id"] for p in STANDARD_QNU_PROVIDERS]
    assert "prov_rtx5090_ollama" not in provider_ids, "prov_rtx5090_ollama must be removed"
    assert "prov_rtx5090_vllm" in provider_ids, "prov_rtx5090_vllm must be present"

    vllm_prov = next(p for p in STANDARD_QNU_PROVIDERS if p["id"] == "prov_rtx5090_vllm")
    assert vllm_prov["provider_type"] == "vllm"
    assert "bge-m3" in vllm_prov["models"]
    assert "bge-reranker-v2-m3" in vllm_prov["models"]
    assert "qwen3-embedding-4b" in vllm_prov["models"]

    specs = vllm_prov["extra_config"]["model_specs"]
    assert specs["bge-m3"]["type"] == "embedding"
    assert specs["bge-reranker-v2-m3"]["type"] == "reranker"
    assert specs["qwen3-embedding-4b"]["type"] == "embedding"
