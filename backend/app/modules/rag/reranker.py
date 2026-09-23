"""Reranker Adapter & Resilience Client (Cloudflare BGE-Reranker & BGE-Reranker-v2-m3)."""

from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.modules.rag.fusion import FusionCandidate

logger = logging.getLogger(__name__)
settings = get_settings()


class RerankerClient:
    """Client for Cross-Encoder Reranking with automatic fallback to RRF order."""

    def __init__(self, endpoint_url: str | None = None, api_key: str | None = None):
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    async def _rerank_cloudflare(
        self,
        query: str,
        candidates: list[FusionCandidate],
        top_k: int = 5,
    ) -> list[FusionCandidate]:
        """Rerank candidates using Cloudflare Workers AI @cf/baai/bge-reranker-base."""
        import httpx

        account_id = settings.CLOUDFLARE_ACCOUNT_ID
        token = settings.CLOUDFLARE_API_TOKEN or settings.CLOUDFLARE_API_KEY
        if not account_id or not token:
            return candidates[:top_k]

        raw_model = settings.RERANKER_MODEL.strip()
        if raw_model.startswith("@cf/"):
            model = raw_model
        elif "/" in raw_model:
            model = f"@cf/{raw_model}"
        else:
            model = f"@cf/baai/{raw_model}"
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "contexts": [{"text": c.content} for c in candidates],
        }

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json().get("result", {})
                response_items = data.get("response", [])
                score_map = {
                    item["id"]: float(item["score"])
                    for item in response_items
                    if "id" in item and "score" in item
                }
                scored_candidates = []
                for idx, cand in enumerate(candidates):
                    if idx in score_map:
                        cand.rrf_score = score_map[idx]
                    scored_candidates.append(cand)
                scored_candidates.sort(key=lambda x: x.rrf_score, reverse=True)
                return scored_candidates[:top_k]
            else:
                logger.warning(
                    "Cloudflare rerank returned HTTP %d: %s", resp.status_code, resp.text[:200]
                )

        return candidates[:top_k]

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

        start_time = time.perf_counter()
        provider = "rrf_fallback"

        # 1. Try Cloudflare Workers AI Cross-Encoder if configured
        if (
            getattr(settings, "RERANKER_PROVIDER", "").lower() == "cloudflare"
            and (settings.CLOUDFLARE_API_TOKEN or settings.CLOUDFLARE_API_KEY)
            and settings.CLOUDFLARE_ACCOUNT_ID
            and not settings.CLOUDFLARE_ACCOUNT_ID.startswith("cf-acc-")
        ):
            try:
                ranked = await self._rerank_cloudflare(query, candidates, top_k)
                provider = "cloudflare"
                logger.info(
                    "Rerank provider=%s latency_ms=%.2f in=%d out=%d",
                    provider,
                    (time.perf_counter() - start_time) * 1000,
                    len(candidates),
                    len(ranked),
                )
                return ranked
            except Exception as exc:
                logger.warning(
                    "Cloudflare reranker failed or timed out: %s. Falling back to RRF score.", exc
                )

        # 2. Custom external HTTP reranker endpoint (if configured)
        if self.endpoint_url:
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
                        scored_candidates = []
                        for idx, score in enumerate(scores):
                            if idx < len(candidates):
                                cand = candidates[idx]
                                cand.rrf_score = float(score)
                                scored_candidates.append(cand)
                        scored_candidates.sort(key=lambda x: x.rrf_score, reverse=True)
                        provider = "custom"
                        logger.info(
                            "Rerank provider=%s latency_ms=%.2f in=%d out=%d",
                            provider,
                            (time.perf_counter() - start_time) * 1000,
                            len(candidates),
                            len(scored_candidates[:top_k]),
                        )
                        return scored_candidates[:top_k]
            except Exception as exc:
                logger.warning(
                    "Custom reranker invocation failed: %s. Falling back to RRF score.", exc
                )

        # Fallback to top_k by initial RRF score
        logger.info(
            "Rerank provider=%s latency_ms=%.2f in=%d out=%d",
            provider,
            (time.perf_counter() - start_time) * 1000,
            len(candidates),
            len(candidates[:top_k]),
        )
        return candidates[:top_k]


reranker_client = RerankerClient()
