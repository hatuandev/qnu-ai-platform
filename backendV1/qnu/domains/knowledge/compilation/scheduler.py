"""Bounded overlap for independent units of work.

Only independent items are passed here: a part never consumes another part's result.
A failure stops *new* items from starting; items already in flight are allowed to
finish and persist, because their bytes are valid and reusable on resume.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from qnu.domains.modelops.document_processing import (
    DEFAULT_DOCUMENT_CONCURRENCY,
    bounded_limit,
)

STOP_STATUSES = frozenset({"failed", "uncertain", "claim_lost", "missing", "cancelled"})


@dataclass(frozen=True, slots=True)
class Slot:
    """One group model and how many of its calls may be in flight."""

    provider_id: str | None
    limit: int = DEFAULT_DOCUMENT_CONCURRENCY


def effective_concurrency(config: dict) -> int:
    return bounded_concurrency((config.get("segmentation") or {}).get("concurrency"))


def bounded_concurrency(requested: int | None) -> int:
    return bounded_limit(requested)


def group_slots(config: dict) -> list[Slot]:
    """Slots pinned by the run; legacy runs keep one slot for their pinned model."""
    stored = config.get("document_models") or []
    slots = [
        Slot(entry.get("provider_id"), bounded_concurrency(entry.get("concurrency")))
        for entry in stored
        if isinstance(entry, dict)
    ]
    if not slots:
        return [Slot(config.get("provider", {}).get("provider_id"), effective_concurrency(config))]
    return slots


async def run_bounded(
    items: list[str],
    worker: Callable[[str], Awaitable[str]],
    *,
    limit: int,
    on_settled: Callable[[], Awaitable[None]] | None = None,
) -> list[BaseException]:
    """Run ``worker`` over ``items`` with at most ``limit`` in flight.

    Returns the exceptions raised by workers. A worker that returns a status in
    ``STOP_STATUSES`` also prevents queued items from starting.
    """
    bounded = max(1, limit)
    semaphore = asyncio.Semaphore(bounded)
    stop = asyncio.Event()
    failures: list[BaseException] = []

    async def guarded(item: str) -> str:
        if stop.is_set():
            return "skipped"
        async with semaphore:
            if stop.is_set():
                return "skipped"
            try:
                status = await worker(item)
            except BaseException:
                # Close admission before releasing the semaphore to its waiter.
                stop.set()
                raise
            if status in STOP_STATUSES:
                stop.set()
            return status

    tasks = {asyncio.create_task(guarded(item)): item for item in items}
    pending = set(tasks)
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                try:
                    status = task.result()
                except asyncio.CancelledError:
                    continue
                except Exception as exc:
                    failures.append(exc)
                    stop.set()
                    continue
                if status in STOP_STATUSES:
                    stop.set()
            if on_settled is not None:
                await on_settled()
    finally:
        # Cancellation or a failing output writer must also close admission.
        stop.set()
        # Never cancel in-flight work: a cancelled provider call would become an
        # uncertain usage record for bytes that were about to be durable.
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    return failures


async def run_slots(
    items: list[str],
    worker: Callable[[str, str | None], Awaitable[str]],
    slots: list[Slot],
    *,
    on_settled: Callable[[], Awaitable[None]] | None = None,
) -> list[BaseException]:
    """Run ``worker`` over ``items`` across per-model slots.

    Each slot holds ``slot.limit`` workers for its pinned model. A worker that frees
    up takes the next queued item, so the faster model keeps taking parts. A stop
    status or a worker exception closes admission for every slot; calls already in
    flight are never cancelled because their bytes are about to be durable.
    """
    queue: asyncio.Queue[str] = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)
    stop = asyncio.Event()
    settle_lock = asyncio.Lock()
    failures: list[BaseException] = []

    async def settle() -> None:
        if on_settled is None:
            return
        async with settle_lock:
            await on_settled()

    async def pump(slot: Slot) -> None:
        while not stop.is_set():
            try:
                item = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                status = await worker(item, slot.provider_id)
            except BaseException:
                stop.set()
                raise
            if status in STOP_STATUSES:
                stop.set()
            await settle()

    tasks = [
        asyncio.create_task(pump(slot))
        for slot in slots
        for _ in range(max(1, slot.limit))
    ]
    results: list[BaseException | None] = []
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        stop.set()
        pending = [task for task in tasks if not task.done()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException) and not isinstance(
            result, asyncio.CancelledError
        ):
            failures.append(result)
    return failures
