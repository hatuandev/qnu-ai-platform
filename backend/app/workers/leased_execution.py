"""Execution locks and heartbeat for durable ingestion jobs across workers."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

import httpx
from arq import Retry
from sqlalchemy import update

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.exceptions import AppException
from app.modules.jobs.ingestion_progress import current_job
from app.modules.jobs.models import JobRecord

logger = logging.getLogger(__name__)


def execution_key(job_id: str) -> str:
    return f"qnu:job-execution:{job_id}"


def is_retryable_failure(error: BaseException) -> bool:
    visited: set[int] = set()
    while error is not None and id(error) not in visited:
        visited.add(id(error))
        if isinstance(error, (TimeoutError, ConnectionError, httpx.RequestError)):
            return True
        if isinstance(error, httpx.HTTPStatusError) and (error.response.status_code >= 500 or error.response.status_code == 429):
            return True
        if isinstance(error, AppException) and error.code in {
            "OCR_SERVICE_TIMEOUT", "OCR_SERVICE_UNAVAILABLE",
            "PROVIDER_CAPACITY_TIMEOUT", "PROVIDER_CAPACITY_UNAVAILABLE",
            "EMBEDDING_PROVIDER_UNAVAILABLE",
        }:
            return True
        error = error.__cause__ or error.__context__
    return False


def leased_execution(function: Callable[..., Awaitable[dict[str, Any]]]) -> Callable[..., Awaitable[dict[str, Any]]]:
    @wraps(function)
    async def wrapped(ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
        redis = ctx.get("redis")
        if redis is None:
            # In-process unit harnesses have no broker; ARQ always supplies it.
            return await function(ctx, job_id)
        async with AsyncSessionFactory() as db:
            job = await db.get(JobRecord, job_id)
            if not job or job.status in ("completed", "cancelled"):
                return {"status": job.status if job else "missing", "job_id": job_id}
            attempt = job.attempt or 0
            resource = job.document_id or (job.payload or {}).get("binding_id") or job_id
            resource_key = f"qnu:source-execution:{job.tenant_id}:{job.workspace_id}:{job.collection_id}:{resource}"
        ttl = settings.WORKER_JOB_TIMEOUT_SECONDS + 120
        lock = redis.lock(execution_key(job_id), timeout=ttl, blocking_timeout=0)
        resource_lock = redis.lock(resource_key, timeout=ttl, blocking_timeout=0)
        if not await lock.acquire(blocking=False):
            raise Retry(defer=5)
        try:
            if not await resource_lock.acquire(blocking=True, blocking_timeout=120):
                raise Retry(defer=5)
        except BaseException:
            await lock.release()
            raise
        owner = asyncio.current_task()

        async def heartbeat() -> None:
            try:
                while True:
                    await asyncio.sleep(15)
                    await lock.extend(ttl, replace_ttl=True)
                    await resource_lock.extend(ttl, replace_ttl=True)
                    async with AsyncSessionFactory() as db:
                        await db.execute(update(JobRecord).where(
                            JobRecord.id == job_id, JobRecord.attempt == attempt,
                            JobRecord.status == "running",
                        ).values(heartbeat_at=datetime.now(UTC)))
                        await db.commit()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Worker lease heartbeat failed", extra={"job_id": job_id})
                if owner:
                    owner.cancel()

        token = current_job.set((job_id, attempt))
        pulse = asyncio.create_task(heartbeat())
        try:
            return await function(ctx, job_id)
        except asyncio.CancelledError as exc:
            # A timeout/lost lease must not be retried directly against an item
            # still marked processing. Durable recovery resets it under lock.
            async with AsyncSessionFactory() as db:
                await db.execute(update(JobRecord).where(
                    JobRecord.id == job_id, JobRecord.attempt == attempt,
                    JobRecord.status == "running", JobRecord.cancel_requested.is_(False),
                ).values(status="failed", error="Worker bị gián đoạn; đang chờ phục hồi.",
                         result={"retryable": True}))
                await db.commit()
            raise AppException("Worker bị gián đoạn.", code="WORKER_INTERRUPTED", status_code=503) from exc
        except Exception as exc:
            retryable = is_retryable_failure(exc)
            if retryable:
                async with AsyncSessionFactory() as db:
                    await db.execute(update(JobRecord).where(
                        JobRecord.id == job_id, JobRecord.attempt == attempt,
                        JobRecord.status == "failed",
                    ).values(result={"retryable": True, "retry_after": (
                        datetime.now(UTC) + timedelta(seconds=min(60, 5 * 2 ** attempt))
                    ).isoformat()}))
                    await db.commit()
            raise
        finally:
            current_job.reset(token)
            pulse.cancel()
            with suppress(asyncio.CancelledError):
                await pulse
            for held in (resource_lock, lock):
                try:
                    await held.release()
                except Exception:
                    logger.warning("Worker lease release failed", extra={"job_id": job_id})
    return wrapped
