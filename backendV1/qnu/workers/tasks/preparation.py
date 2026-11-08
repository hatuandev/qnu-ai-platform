"""ARQ tasks for durable preparation intents on the existing v1 queue."""

from __future__ import annotations

from qnu.domains.knowledge.preparation import service
from qnu.platform.database import AsyncSessionFactory


async def preparation_job(ctx: dict, intent_id: str) -> str:
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        return await service.execute_intent(
            db,
            container.blob_store,
            container.job_queue,
            intent_id,
            ctx.get("worker_id", "arq"),
        )


async def preparation_reconcile(ctx: dict) -> int:
    container = ctx["container"]
    async with AsyncSessionFactory() as db:
        return await service.reconcile(db, container.job_queue)
