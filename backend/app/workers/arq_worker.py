"""ARQ Background Worker Configuration and Lifecycle for QNU AI Platform."""

from __future__ import annotations

import sys
from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings

# Force UTF-8 encoding on standard output for Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.core.config import settings
from app.core.logging import configure_logging
from app.modules.backups.coordination import guard_worker
from app.modules.backups.scheduler import task_backup_schedule
from app.workers.tasks import (
    task_document_ingestion,
    task_document_revision_parse,
    task_export_document,
    task_knowledge_garbage_collection,
    task_knowledge_index_build,
    task_knowledge_source_ingestion,
    task_knowledge_source_purge,
    task_knowledge_source_reparse,
    task_reconcile_pending_jobs,
    task_reindex_collection,
)
from app.workers.workflow_recovery import task_reconcile_workflow_executions

# Preserve ARQ task names while holding the cross-process backup barrier for their
# entire execution, including periodic reconciliation and garbage collection.
task_document_ingestion = guard_worker(task_document_ingestion)
task_reindex_collection = guard_worker(task_reindex_collection)
task_export_document = guard_worker(task_export_document)
task_document_revision_parse = guard_worker(task_document_revision_parse)
task_knowledge_source_ingestion = guard_worker(task_knowledge_source_ingestion)
task_knowledge_source_reparse = guard_worker(task_knowledge_source_reparse)
task_knowledge_source_purge = guard_worker(task_knowledge_source_purge)
task_knowledge_index_build = guard_worker(task_knowledge_index_build)
task_knowledge_garbage_collection = guard_worker(task_knowledge_garbage_collection)
task_reconcile_pending_jobs = guard_worker(task_reconcile_pending_jobs, periodic=True)
task_reconcile_workflow_executions = guard_worker(task_reconcile_workflow_executions, periodic=True)

logger = structlog.get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook: initialize database pools or model weights."""
    configure_logging()
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
        task_document_revision_parse,
        task_knowledge_source_ingestion,
        task_knowledge_source_purge,
        task_knowledge_source_reparse,
        task_knowledge_index_build,
        task_knowledge_garbage_collection,
    ]
    cron_jobs = [
        cron(task_reconcile_pending_jobs, second={0, 15, 30, 45}),
        cron(task_reconcile_workflow_executions, second={5, 35}),
        cron(task_backup_schedule, second={10, 40}),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = settings.WORKER_MAX_JOBS
    health_check_interval = 15
    job_timeout = settings.WORKER_JOB_TIMEOUT_SECONDS
    retry_jobs = True
    max_tries = settings.WORKER_MAX_TRIES
