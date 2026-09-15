"""ARQ Background Worker Configuration and Lifecycle for QNU AI Platform."""

from __future__ import annotations

from typing import Any

import structlog
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks import (
    task_document_ingestion,
    task_export_document,
    task_reindex_collection,
)

logger = structlog.get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook: initialize database pools or model weights."""
    logger.info("arq_worker_starting_up", redis_url=settings.REDIS_URL)


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook: clean up open connections."""
    logger.info("arq_worker_shutting_down")


class WorkerSettings:
    """ARQ Worker configuration class."""

    functions = [
        task_document_ingestion,
        task_reindex_collection,
        task_export_document,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    retry_jobs = True
    max_retries = 3
