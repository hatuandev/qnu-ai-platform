"""Embedding port."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from qnu.ports.provider_execution import ProviderExecution


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    endpoint: str
    model: str
    timeout_seconds: float
    api_key: str = field(repr=False)
    expected_dimension: int | None = None
    execution: ProviderExecution | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: list[list[float]]
    dimension: int
    total_tokens: int | None
    raw_body: bytes = field(repr=False)


@runtime_checkable
class EmbeddingModel(Protocol):
    async def embed(self, texts: list[str], request: EmbeddingRequest) -> EmbeddingResult: ...
