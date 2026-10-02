"""Reranker adapter and resilience client for Cloudflare Workers AI."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.database import AsyncSessionFactory
from app.modules.modelops.services.model_runtime_resolver import (
    ModelRuntimeConfig,
    model_runtime_resolver,
)
from app.modules.modelops.services.provider_key_rotation_service import (
    provider_key_rotation_service,
)
from app.modules.rag.fusion import FusionCandidate

logger = logging.getLogger(__name__)


def _combine_rrf_and_ce_scores(
    candidates: list[FusionCandidate],
    ce_score_map: dict[int, float],
    k: int = 60,
    ce_multiplier: float = 1.2,
) -> list[FusionCandidate]:
    """Fuse initial RRF ordering with Cross-Encoder (CE) relevance scores."""
    ce_ranked_indices = sorted(
        range(len(candidates)),
        key=lambda idx: ce_score_map.get(idx, -999.0),
        reverse=True,
    )
    ce_rank_map = {orig_idx: rank for rank, orig_idx in enumerate(ce_ranked_indices, start=1)}

    scored_candidates: list[FusionCandidate] = []
    for orig_idx, cand in enumerate(candidates):
        rrf_rank = orig_idx + 1
        ce_rank = ce_rank_map.get(orig_idx, len(candidates))
        cand.rrf_score = (1.0 / (k + rrf_rank)) + (ce_multiplier / (k + ce_rank))
        scored_candidates.append(cand)

    scored_candidates.sort(key=lambda x: x.rrf_score, reverse=True)
    return scored_candidates


class RerankerClient:
    """Client for Cross-Encoder Reranking with automatic fallback to RRF order."""

    def __init__(self, endpoint_url: str | None = None, api_key: str | None = None):
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    async def _rerank_cloudflare(
        self,
        query: str,
        candidates: list[FusionCandidate],
        runtime: ModelRuntimeConfig,
        top_k: int = 5,
    ) -> list[FusionCandidate]:
        """Rerank candidates using Cloudflare Workers AI @cf/baai/bge-reranker-base."""
        import httpx

        account_id = runtime.account_id
        token = runtime.api_key
        if not account_id or not token:
            return candidates[:top_k]

        raw_model = runtime.model_name.strip()
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

        async with httpx.AsyncClient(timeout=float(runtime.timeout_seconds)) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json().get("result", {})
                response_items = data.get("response", [])
                score_map = {
                    item["id"]: float(item["score"])
                    for item in response_items
                    if "id" in item and "score" in item
                }
                scored = _combine_rrf_and_ce_scores(candidates, score_map)
                return scored[:top_k]
            resp.raise_for_status()
            raise RuntimeError("Cloudflare reranker returned an empty response.")

    async def _resolve_reranker_runtime(
        self, *, excluded_key_ids: set[str] | None = None
    ) -> ModelRuntimeConfig:
        """Load the current reranker provider and model from ModelOps."""
        async with AsyncSessionFactory() as db:
            return await model_runtime_resolver.resolve(
                db, "reranker", excluded_key_ids=excluded_key_ids
            )

    @staticmethod
    async def _finish_runtime_key(
        runtime: ModelRuntimeConfig, error: Exception | None = None
    ) -> None:
        lease = runtime.key_lease()
        if lease is None:
            return
        async with AsyncSessionFactory() as db:
            if error is None:
                await provider_key_rotation_service.complete_success(db, lease)
            else:
                await provider_key_rotation_service.complete_failure(db, lease, error)

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

        # 1. Resolve Cloudflare Workers AI Cross-Encoder from ModelOps.
        excluded: set[str] = set()
        while True:
            runtime: ModelRuntimeConfig | None = None
            try:
                runtime = await self._resolve_reranker_runtime(
                    excluded_key_ids=excluded
                )
                if runtime.provider_type == "cloudflare" and runtime.api_key and runtime.account_id:
                    ranked = await self._rerank_cloudflare(query, candidates, runtime, top_k)
                    await self._finish_runtime_key(runtime)
                    provider = "cloudflare"
                    logger.info(
                        "Rerank provider=%s latency_ms=%.2f in=%d out=%d",
                        provider,
                        (time.perf_counter() - start_time) * 1000,
                        len(candidates),
                        len(ranked),
                    )
                    return ranked
                await self._finish_runtime_key(runtime)
                break
            except asyncio.CancelledError:
                if runtime is not None and runtime.key_lease() is not None:
                    async with AsyncSessionFactory() as db:
                        await provider_key_rotation_service.release(db, runtime.key_lease())
                raise
            except Exception as exc:
                if runtime is not None:
                    await self._finish_runtime_key(runtime, exc)
                    if runtime.key_id:
                        excluded.add(runtime.key_id)
                        continue
                logger.warning(
                    "ModelOps reranker unavailable: %s. Falling back to RRF score.", exc
                )
                break

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
                        score_map = {idx: float(score) for idx, score in enumerate(scores)}
                        scored_candidates = _combine_rrf_and_ce_scores(candidates, score_map)
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
