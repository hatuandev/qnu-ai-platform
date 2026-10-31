"""Bounded overlap for independent units of work.

Only independent items are passed here: a part never consumes another part's result.
A failure stops *new* items from starting; items already in flight are allowed to
finish and persist, because their bytes are valid and reusable on resume.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from qnu.platform.config import get_settings

STOP_STATUSES = frozenset({"failed", "uncertain", "claim_lost", "missing", "cancelled"})


def effective_concurrency(config: dict) -> int:
    settings = get_settings()
    requested = (config.get("segmentation") or {}).get("concurrency")
    return max(1, min(
        requested or settings.COMPILER_SEGMENT_CONCURRENCY,
        settings.COMPILER_SEGMENT_CONCURRENCY,
        settings.MODEL_CHAT_CONCURRENCY,
    ))


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
