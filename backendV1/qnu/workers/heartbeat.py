"""Short-lived worker evidence scoped by the configured v1 queue and cache namespace."""

import asyncio
import hashlib
import json
from contextlib import suppress

from sqlalchemy import text

from qnu.domains.operations.recovery.service import HEAD
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.logging import get_logger


async def start(ctx: dict) -> None:
    if ctx.get("redis") is None:
        return
    settings = get_settings()
    async with AsyncSessionFactory() as db:
        observed_head = await db.scalar(text("SELECT version_num FROM alembic_version_backendv1"))
    prefix = (
        settings.CACHE_NAMESPACE
        + "worker:"
        + hashlib.sha256(settings.QUEUE_NAME.encode()).hexdigest()[:16]
        + ":"
    )
    ctx["heartbeat_key"] = prefix + hashlib.sha256(ctx["worker_id"].encode()).hexdigest()[:16]

    async def pulse() -> None:
        while True:
            try:
                await ctx["redis"].set(
                    ctx["heartbeat_key"],
                    json.dumps({"schema_head": observed_head, "code_head": HEAD}),
                    ex=90,
                )
            except Exception:
                get_logger(__name__).warning("worker_heartbeat_unavailable")
            await asyncio.sleep(30)

    ctx["heartbeat_task"] = asyncio.create_task(pulse())


async def stop(ctx: dict) -> None:
    task = ctx.pop("heartbeat_task", None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        try:
            await ctx["redis"].delete(ctx["heartbeat_key"])
        except Exception:
            get_logger(__name__).warning("worker_heartbeat_cleanup_unavailable")
