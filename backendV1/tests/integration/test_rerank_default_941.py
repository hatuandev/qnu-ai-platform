"""Default hybrid_rerank degrades to hybrid fusion when no rerank model exists."""

from tests.integration.index_support import execute_index
from tests.integration.test_index_api_647 import indexed as indexed_fixture

indexed = indexed_fixture


def test_default_mode_without_rerank_model_returns_hybrid_results_with_trace(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    body = {"query": "Chỉ tiêu tuyển sinh", "candidate_k": 10}
    default = client.post(indexed["base"] + "/search", json=body)
    assert default.status_code == 200, default.text
    result = default.json()
    assert result["trace"]["mode"] == "hybrid_rerank"
    assert result["trace"]["rerank_skipped"] == "model_not_configured"
    assert result["hits"]
    hybrid = client.post(indexed["base"] + "/search", json={**body, "mode": "hybrid"})
    assert hybrid.status_code == 200, hybrid.text
    assert [h["chunk_id"] for h in result["hits"]] == [h["chunk_id"] for h in hybrid.json()["hits"]]
