"""Reciprocal Rank Fusion (RRF) Algorithm for Hybrid Search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FusionCandidate:
    """Candidate chunk aggregated from multiple retrieval search engines."""

    chunk_id: str
    document_id: str
    content: str
    rrf_score: float
    dense_rank: int = -1
    sparse_rank: int = -1
    section: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = None


def _merge_ranked_list(
    scores: dict[str, float],
    candidates: dict[str, FusionCandidate],
    results: list[dict[str, Any]],
    k: int,
    weight: float,
    rank_field: str,
) -> None:
    """Add one ranked list into shared RRF scores (1-indexed ranks)."""
    for rank, item in enumerate(results, start=1):
        cid = str(item["chunk_id"])
        scores[cid] = scores.get(cid, 0.0) + (weight / (k + rank))
        if cid not in candidates:
            candidates[cid] = FusionCandidate(
                chunk_id=cid,
                document_id=str(item.get("document_id", "")),
                content=str(item.get("content", "")),
                rrf_score=0.0,
                section=item.get("section"),
                page_number=item.get("page_number"),
                metadata=item.get("metadata", {}),
            )
            setattr(candidates[cid], rank_field, rank)
        elif getattr(candidates[cid], rank_field, -1) == -1:
            setattr(candidates[cid], rank_field, rank)


def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    sparse_results: list[dict[str, Any]],
    k: int = 60,
    dense_weight: float = 1.0,
    sparse_weight: float = 1.0,
    extra_lists: list[tuple[list[dict[str, Any]], float]] | None = None,
) -> list[FusionCandidate]:
    """Fuse rankings from Dense Vector Search and Sparse Lexical (FTS) Search using RRF.

    Formula: RRF_Score(d) = dense_w / (k + rank_dense(d)) + sparse_w / (k + rank_sparse(d)).
    Intent-tailored weights let exact lookups trust lexical precision while narrative
    questions lean on semantic similarity. Defaults keep legacy balanced behavior.
    `extra_lists` carries discounted variant queries (multi-query sparse fusion).
    """
    scores: dict[str, float] = {}
    candidates: dict[str, FusionCandidate] = {}

    # 1. Process Dense Vector rankings (1-indexed)
    _merge_ranked_list(scores, candidates, dense_results, k, dense_weight, "dense_rank")

    # 2. Process Sparse FTS rankings (1-indexed)
    _merge_ranked_list(scores, candidates, sparse_results, k, sparse_weight, "sparse_rank")

    # 3. Discounted variant query lists (e.g. keyword-form rewrite of the question)
    for variant_results, variant_weight in extra_lists or []:
        _merge_ranked_list(scores, candidates, variant_results, k, variant_weight, "sparse_rank")

    # 3. Assign merged RRF scores with legal priority weighting and sort descending
    for cid, cand in candidates.items():
        base_score = scores[cid]
        # Legal priority weighting: priority ranges 1-10 (default 5).
        # Priority 10 (e.g. Quy chế, Quyết định) receives an intentional boost (+10%),
        # ensuring authoritative regulatory documents rank higher when relevance is close.
        priority = 5
        if cand.metadata and isinstance(cand.metadata, dict):
            raw_p = (
                cand.metadata.get("priority")
                or cand.metadata.get("document_priority")
                or cand.metadata.get("doc_priority")
            )
            if raw_p is not None:
                try:
                    priority = int(raw_p)
                except (ValueError, TypeError):
                    priority = 5
        priority = max(1, min(10, priority))
        priority_multiplier = 1.0 + (priority - 5) * 0.02
        cand.rrf_score = base_score * priority_multiplier

    sorted_candidates = sorted(candidates.values(), key=lambda x: x.rrf_score, reverse=True)
    return sorted_candidates
