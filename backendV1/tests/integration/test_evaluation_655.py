"""Fair retrieval comparisons reject stale/foreign labels and preserve errors in denominators."""

from tests.integration.index_support import execute_index
from tests.integration.test_hybrid_655 import FakeRerank, setup_rerank
from tests.integration.test_index_api_647 import indexed as indexed_fixture

indexed = indexed_fixture


def test_evaluation_freezes_snapshot_and_uses_same_fusion_candidates(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    with FakeRerank() as fake:
        setup_rerank(client, indexed, fake.base_url)
        search = client.post(
            indexed["base"] + "/search", json={"query": "Chỉ tiêu", "mode": "hybrid"}
        ).json()
        body = {
            "index_run_id": search["index_run_id"],
            "manifest_sha256": search["trace"]["manifest_sha256"],
            "label_version": "fixture/v1",
            "label_author": "fixture-author",
            "top_k": 1,
            "candidate_k": 10,
            "include_rerank": True,
            "queries": [
                {
                    "id": "one",
                    "query": "Chỉ tiêu",
                    "gold_chunk_ids": [search["hits"][0]["chunk_id"]],
                }
            ],
        }
        response = client.post(indexed["base"] + "/retrieval-evaluations", json=body)
        assert response.status_code == 200, response.text
        result = response.json()
        assert len(result["records"]) == 3
        assert all(r["status"] == "completed" for r in result["records"])
        assert (
            result["records"][1]["candidate_trace"]["candidate_sha256"]
            == result["records"][2]["candidate_trace"]["candidate_sha256"]
        )
        assert result["answer_evaluation"] == "NOT RUN" and not result["publication_approval"]
        fake.mode = "auth"
        failed = client.post(indexed["base"] + "/retrieval-evaluations", json=body)
        assert failed.status_code == 200, failed.text
        assert failed.json()["summary"]["hybrid_rerank"]["errors"] == 1
        body["queries"][0]["gold_chunk_ids"] = ["foreign-chunk"]
        assert (
            client.post(indexed["base"] + "/retrieval-evaluations", json=body).json()["code"]
            == "evaluation_gold_mismatch"
        )
        body["manifest_sha256"] = "0" * 64
        assert (
            client.post(indexed["base"] + "/retrieval-evaluations", json=body).json()["code"]
            == "evaluation_snapshot_mismatch"
        )
