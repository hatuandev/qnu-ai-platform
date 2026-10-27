"""Job queue port: domains enqueue durable work without importing a queue library."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class JobQueue(Protocol):
    async def enqueue(self, function: str, *args: object, job_id: str | None = None) -> bool:
        """Enqueue one job; return False when the same job id is already pending."""
        ...


__all__ = ["JobQueue"]
