"""Annotated retrieval metrics; no heuristic stand-in for answer correctness."""


def retrieval_metrics(ranked_ids: list[str], gold_ids: list[str], top_k: int) -> dict:
    if len(set(ranked_ids)) != len(ranked_ids):
        raise ValueError("Duplicate ranked IDs")
    selected, gold = ranked_ids[:top_k], set(gold_ids)
    relevant = [i for i, value in enumerate(selected, 1) if value in gold]
    return {
        "hit_at_k": int(bool(relevant)) if gold else None,
        "annotated_recall_at_k": len(relevant) / len(gold) if gold else None,
        "mrr_at_k": 1 / relevant[0] if relevant else (0.0 if gold else None),
        "annotated_precision_at_k": len(relevant) / len(selected) if selected and gold else None,
        "empty_gold": not bool(gold),
        "retrieved_count": len(selected),
        "answer_correctness": None,
        "answer_groundedness": None,
    }


def aggregate(records: list[dict]) -> dict:
    result = {}
    for strategy in sorted({r["strategy"] for r in records}):
        rows = [r for r in records if r["strategy"] == strategy]
        completed = [r for r in rows if r["status"] == "completed"]
        means = {}
        for key in ("hit_at_k", "annotated_recall_at_k", "mrr_at_k", "annotated_precision_at_k"):
            values = [r["metrics"][key] for r in completed if r["metrics"][key] is not None]
            means[key] = sum(values) / len(values) if values else None
        result[strategy] = {
            "expected": len(rows),
            "completed": len(completed),
            "errors": len(rows) - len(completed),
            "completed_only_metrics": means,
            "acceptance": "not_determined",
        }
    return result
