"""Strict vLLM/Cohere-style rerank transport; no implicit retry or fallback."""

import math

import httpx

from qnu.adapters.providers.failures import tag_failure
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.ports.reranker import RerankHit, RerankRequest, RerankResult


def fail(code: str, status: int = 502) -> AppException:
    return AppException("Không nhận được kết quả rerank hợp lệ.", code=code, status_code=status)


def decode(data: object, count: int, top_k: int, model: str) -> RerankResult:
    if (
        not isinstance(data, dict)
        or data.get("model", model) != model
        or not isinstance(data.get("results"), list)
    ):
        raise fail("rerank_response_invalid")
    rows, seen = [], set()
    for item in data["results"]:
        if not isinstance(item, dict):
            raise fail("rerank_response_invalid")
        index, score = item.get("index"), item.get("relevance_score")
        if (
            type(index) is not int
            or index in seen
            or not 0 <= index < count
            or type(score) not in (int, float)
            or not math.isfinite(score)
        ):
            raise fail("rerank_response_invalid")
        seen.add(index)
        rows.append(RerankHit(index, float(score)))
    if len(rows) != min(count, top_k):
        raise fail("rerank_response_invalid")
    usage = data.get("usage")
    tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
    return RerankResult(
        sorted(rows, key=lambda h: (-h.score, h.index)),
        tokens if type(tokens) is int and tokens >= 0 else None,
    )


class ModelOpsReranker:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def rerank(
        self, query: str, documents: list[str], top_k: int, request: RerankRequest
    ) -> RerankResult:
        if not query.strip() or not documents or not request.api_key:
            raise fail("rerank_input_invalid", 422)
        base = request.endpoint.rstrip("/")
        url = (
            base
            if base.endswith("/rerank")
            else base + ("/rerank" if base.endswith("/v1") else "/v1/rerank")
        )
        assert_allowed_endpoint(url, allow_private=not get_settings().is_production)
        try:
            async with httpx.AsyncClient(
                timeout=request.timeout_seconds,
                trust_env=False,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": "Bearer " + request.api_key},
                    json={
                        "model": request.model,
                        "query": query,
                        "documents": documents,
                        "top_n": top_k,
                    },
                )
        except httpx.RequestError as exc:
            raise fail("rerank_uncertain", 504) from exc
        if response.status_code in (401, 403):
            raise tag_failure(fail("rerank_auth_failed"), response)
        if response.status_code != 200:
            raise tag_failure(fail("rerank_unavailable", 503), response)
        try:
            data = response.json()
        except ValueError as exc:
            raise fail("rerank_response_invalid") from exc
        return decode(data, len(documents), top_k, request.model)
