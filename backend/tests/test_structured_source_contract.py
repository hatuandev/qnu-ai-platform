"""Regression contracts for revision-bound artifacts and real CE scores."""

from datetime import UTC, datetime

import pytest

from app.modules.knowledge.schemas import FactItemResponse
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.reranker import _combine_rrf_and_ce_scores


def test_reranking_retains_provider_score_separate_from_fusion():
    candidates = [FusionCandidate("a", "d", "relevant", 0.03),
                  FusionCandidate("b", "d", "irrelevant", 0.02)]
    ranked = _combine_rrf_and_ce_scores(candidates, {0: 0.89, 1: 0.0001})
    assert [c.chunk_id for c in ranked if c.relevance_score >= 0.4] == ["a"]
    assert ranked[0].rrf_score != ranked[0].relevance_score


def test_invalid_reranker_response_cannot_claim_scored_success():
    with pytest.raises(ValueError):
        _combine_rrf_and_ce_scores([FusionCandidate("a", "d", "text", 0.03)], {0: float("nan")})


def test_new_source_fact_does_not_require_legacy_document():
    item = FactItemResponse(id="f", collection_id="c", document_id=None,
                            binding_id="b", index_revision_id="i", entity_name="Entity",
                            entity_type="table_row", attribute_name="Year 2025",
                            attribute_value="21.5", confidence=0.95, created_at=datetime.now(UTC))
    assert item.binding_id == "b"


def test_table_year_headers_empty_cells_and_multiple_tables_keep_provenance():
    markdown = """<!-- Trang 12 -->
| TT | Ngành | Điểm | |
| --- | --- | --- | --- |
| | | 2024 | 2025 |
| 1 | Công nghệ thông tin | 16.5 | 21.5 |
| 2 | Vật lý | | 0 |

| Chủ thể | Thuộc tính |
| --- | --- |
| Một chủ thể | Giá trị |
"""
    artifact = build_source_artifact(markdown, 14, {})
    facts = artifact["facts"]
    assert any(f["entity_name"] == "Công nghệ thông tin" and f["attribute_name"] == "Điểm / 2025"
               and f["attribute_value"] == "21.5" for f in facts)
    assert not any(f["entity_name"] == "Vật lý" and f["attribute_name"] == "Điểm / 2024" for f in facts)
    assert any(f["entity_name"] == "Vật lý" and f["attribute_value"] == "0" for f in facts)
    assert len(artifact["tables"]) == 2
    assert {f["raw_data"]["page_number"] for f in facts} == {12}
    assert artifact["issues"] == []


def test_edit_invalidates_fact_set_and_flags_conflicting_cells():
    original = "| Thực thể | Giá trị |\n| --- | --- |\n| A entity | 20 |"
    first = build_source_artifact(original, 1, {})
    second = build_source_artifact(original.replace("20", "30"), 1, {})
    assert first["fact_set_hash"] != second["fact_set_hash"]
    ambiguous = build_source_artifact(original + "\n| A entity | 40 |", 1, {})
    assert ambiguous["review"]["status"] == "required"


@pytest.mark.asyncio
async def test_public_reranker_applies_threshold_to_adapter_score_not_fallback():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    import httpx

    from app.modules.rag.reranker import RerankerClient

    client = RerankerClient()
    runtime = SimpleNamespace(provider_type="vllm", api_base_url="http://fixture/v1", model_name="selected-model",
                              api_key=None, timeout_seconds=10, key_id=None, key_lease=lambda: None)
    response = httpx.Response(200, request=httpx.Request("POST", "http://fixture/v1/rerank"),
                             json={"results": [{"index": 0, "relevance_score": 0.89}, {"index": 1, "relevance_score": 0.01}]})
    candidates = [FusionCandidate("a", "d", "relevant", 0.03), FusionCandidate("b", "d", "unrelated", 0.02)]
    with patch.object(client, "_resolve_reranker_runtime", AsyncMock(return_value=runtime)), patch("httpx.AsyncClient.post", AsyncMock(return_value=response)):
        results = await client.rerank("query", candidates, score_threshold=0.4)
    assert [item.chunk_id for item in results] == ["a"]
    assert results[0].relevance_score == 0.89


@pytest.mark.asyncio
async def test_staging_search_rejects_missing_scope_before_provider_call():
    from app.core.exceptions import AppException
    from app.modules.rag.vector_indexer import vector_indexer

    with pytest.raises(AppException) as error:
        await vector_indexer.search_dense("fixture", "query", candidate_mode=True)
    assert error.value.code == "INVALID_CANDIDATE_SNAPSHOT"
