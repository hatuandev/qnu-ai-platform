"""Reranker port."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class RerankHit:
    index: int
    score: float


@dataclass(frozen=True, slots=True)
class RerankRequest:
    endpoint: str
    model: str
    timeout_seconds: float
    api_key: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class RerankResult:
    hits: list[RerankHit]
    total_tokens: int | None


@runtime_checkable
class Reranker(Protocol):
    async def rerank(
        self, query: str, documents: list[str], top_k: int, request: RerankRequest
    ) -> RerankResult: ...
