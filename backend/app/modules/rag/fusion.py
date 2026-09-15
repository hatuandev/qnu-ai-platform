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


def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    sparse_results: list[dict[str, Any]],
    k: int = 60,
) -> list[FusionCandidate]:
    """Fuse rankings from Dense Vector Search and Sparse Lexical (FTS) Search using RRF.

    Formula: RRF_Score(d) = sum(1 / (k + rank(d))) across all retrieval lists.
    """
    scores: dict[str, float] = {}
    candidates: dict[str, FusionCandidate] = {}

    # 1. Process Dense Vector rankings (1-indexed)
    for rank, item in enumerate(dense_results, start=1):
        cid = str(item["chunk_id"])
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank))
        if cid not in candidates:
            candidates[cid] = FusionCandidate(
                chunk_id=cid,
                document_id=str(item.get("document_id", "")),
                content=str(item.get("content", "")),
                rrf_score=0.0,
                dense_rank=rank,
                section=item.get("section"),
                page_number=item.get("page_number"),
                metadata=item.get("metadata", {}),
            )
        else:
            candidates[cid].dense_rank = rank

    # 2. Process Sparse FTS rankings (1-indexed)
    for rank, item in enumerate(sparse_results, start=1):
        cid = str(item["chunk_id"])
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank))
        if cid not in candidates:
            candidates[cid] = FusionCandidate(
                chunk_id=cid,
                document_id=str(item.get("document_id", "")),
                content=str(item.get("content", "")),
                rrf_score=0.0,
                sparse_rank=rank,
                section=item.get("section"),
                page_number=item.get("page_number"),
                metadata=item.get("metadata", {}),
            )
        else:
            candidates[cid].sparse_rank = rank

    # 3. Assign merged RRF scores and sort descending
    for cid, cand in candidates.items():
        cand.rrf_score = scores[cid]

    sorted_candidates = sorted(candidates.values(), key=lambda x: x.rrf_score, reverse=True)
    return sorted_candidates
