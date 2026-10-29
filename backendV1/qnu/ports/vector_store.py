"""Vector store port (read + lifecycle only; writes belong to knowledge/index)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class VectorHit:
    point_id: str
    score: float
    payload: dict


@runtime_checkable
class VectorStore(Protocol):
    @property
    def target_hash(self) -> str: ...
    async def collection_exists(self, collection: str) -> bool: ...

    async def ensure_collection(
        self, collection: str, size: int, distance: str = "Cosine"
    ) -> None: ...

    async def upsert(self, collection: str, points: list[dict]) -> None: ...

    async def delete_collection(self, collection: str) -> None: ...

    async def delete_points(self, collection: str, point_ids: list[str]) -> None: ...

    async def count(self, collection: str) -> int: ...

    async def search(
        self, collection: str, vector: list[float], limit: int, scope: dict
    ) -> list[VectorHit]: ...
