"""Blob storage port."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class BlobObject:
    key: str
    size: int
    modified_at: datetime
    version: str


@runtime_checkable
class BlobStore(Protocol):
    async def purge(self, key: str) -> None:
        """Permanently remove the exact key, including S3 object versions/delete markers."""
        ...

    driver: str

    async def put_bytes(self, key: str, payload: bytes, content_type: str | None = None) -> str: ...

    async def get_bytes(self, key: str) -> bytes: ...

    async def exists(self, key: str) -> bool: ...

    async def delete(self, key: str) -> None: ...

    @property
    def target_hash(self) -> str: ...

    async def list_objects(self, prefix: str, limit: int = 10000) -> list[BlobObject]: ...

    async def delete_if_unchanged(self, item: BlobObject, sha256: str) -> str: ...
