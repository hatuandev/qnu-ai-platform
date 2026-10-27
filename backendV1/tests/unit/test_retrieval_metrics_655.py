import pytest

from qnu.adapters.providers.reranker import decode
from qnu.domains.evaluation.metrics import retrieval_metrics


def test_metrics_keep_annotated_and_unknown_distinct():
    result = retrieval_metrics(["x", "b", "a"], ["a", "b", "c"], 2)
    assert result["annotated_recall_at_k"] == 1 / 3 and result["mrr_at_k"] == 0.5
    assert result["answer_correctness"] is None
    assert retrieval_metrics(["x"], [], 2)["hit_at_k"] is None
    with pytest.raises(ValueError):
        retrieval_metrics(["x", "x"], ["x"], 2)


@pytest.mark.parametrize("index,score", [(True, 1.0), (0, float("nan")), (0, "1.0"), (-1, 1.0)])
def test_rerank_response_rejects_bad_indices_scores(index, score):
    from qnu.platform.errors import AppException

    with pytest.raises(AppException):
        decode({"results": [{"index": index, "relevance_score": score}]}, 1, 1, "test")
