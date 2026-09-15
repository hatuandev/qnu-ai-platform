"""Reranker Adapter & Resilience Client (BGE-Reranker-v2-m3)."""

from __future__ import annotations

import logging

from app.modules.rag.fusion import FusionCandidate

logger = logging.getLogger(__name__)


class RerankerClient:
    """Client for Cross-Encoder Reranking with automatic fallback to RRF order."""

    def __init__(self, endpoint_url: str | None = None, api_key: str | None = None):
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    async def rerank(
        self,
        query: str,
        candidates: list[FusionCandidate],
        top_k: int = 5,
    ) -> list[FusionCandidate]:
        """Rerank candidates using cross-encoder relevance scoring.

        Graceful Degradation: If reranker service fails or is unconfigured,
        falls back smoothly to RRF fused score ordering.
        """
        if not candidates:
            return []

        # If reranker endpoint is not configured, return top_k candidates by RRF score
        if not self.endpoint_url:
            return candidates[:top_k]

        try:
            import httpx

            async with httpx.AsyncClient(timeout=3.0) as client:
                payload = {
                    "query": query,
                    "documents": [c.content for c in candidates],
                }
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                resp = await client.post(
                    f"{self.endpoint_url}/rerank", json=payload, headers=headers
                )
                if resp.status_code == 200:
                    scores = resp.json().get("scores", [])
                    # Pair candidates with their rerank scores
                    scored_candidates = []
                    for idx, score in enumerate(scores):
                        if idx < len(candidates):
                            cand = candidates[idx]
                            cand.rrf_score = float(score)  # Update with cross-encoder score
                            scored_candidates.append(cand)
                    scored_candidates.sort(key=lambda x: x.rrf_score, reverse=True)
                    return scored_candidates[:top_k]
        except Exception as exc:
            logger.warning(
                "Reranker invocation failed or timed out: %s. Falling back to RRF score.", exc
            )

        # Fallback to top_k by initial RRF score
        return candidates[:top_k]


reranker_client = RerankerClient()
