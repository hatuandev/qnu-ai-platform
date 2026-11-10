"""ARQ worker settings for backendV1 (own queue, no legacy jobs)."""

from __future__ import annotations

from arq import cron, func
from arq.connections import RedisSettings

from qnu.domains.lifecycle.purge import source_purge_job
from qnu.platform.config import get_settings
from qnu.workers.tasks.compilation import (
    compilation_reconcile,
    compile_run,
    compiler_review_job,
    compiler_review_reconcile,
    manual_compiler_review_job,
)
from qnu.workers.tasks.indexing import index_maintenance, index_reconcile, index_run, index_sync
from qnu.workers.tasks.ocr import (
    ocr_process_run,
    ocr_reconcile_queued,
    shutdown,
    spelling_check_job,
    startup,
)
from qnu.workers.tasks.operations import (
    evidence_backup_delete,
    evidence_backup_job,
    operations_reconcile,
)
from qnu.workers.tasks.preparation import preparation_job, preparation_reconcile

settings = get_settings()


class WorkerSettings:
    """Consumes only ``QUEUE_NAME`` of backendV1."""

    functions: list = [
        func(ocr_process_run, timeout=settings.WORKER_MODEL_JOB_TIMEOUT_SECONDS),
        ocr_reconcile_queued,
        func(spelling_check_job, timeout=settings.WORKER_MODEL_JOB_TIMEOUT_SECONDS),
        func(compile_run, timeout=settings.WORKER_MODEL_JOB_TIMEOUT_SECONDS),
        compilation_reconcile,
        func(compiler_review_job, timeout=settings.WORKER_MODEL_JOB_TIMEOUT_SECONDS),
        func(manual_compiler_review_job, timeout=settings.WORKER_MODEL_JOB_TIMEOUT_SECONDS),
        compiler_review_reconcile,
        preparation_job,
        preparation_reconcile,
        func(index_run, timeout=settings.WORKER_MODEL_JOB_TIMEOUT_SECONDS),
        index_reconcile,
        index_sync,
        index_maintenance,
        evidence_backup_job,
        evidence_backup_delete,
        operations_reconcile,
        source_purge_job,
    ]
    # The reconcile cron only picks up v1 runs from the v1 table and enqueues them on the
    # v1 queue, so it can never touch a legacy job; the flag is the documented kill switch.
    cron_jobs: list = (
        [
            cron(ocr_reconcile_queued, minute=set(range(0, 60, 5))),
            cron(compilation_reconcile, minute=set(range(0, 60, 5))),
            cron(compiler_review_reconcile, minute=set(range(0, 60, 5))),
            cron(preparation_reconcile, minute=set(range(0, 60, 5))),
            cron(index_reconcile, minute=set(range(0, 60, 5))),
            cron(index_maintenance, minute=set(range(60)), run_at_startup=True),
            cron(operations_reconcile, minute=set(range(0, 60, 5))),
        ]
        if settings.OWN_RECONCILE
        else []
    )
    on_startup = startup
    on_shutdown = shutdown
    queue_name = settings.QUEUE_NAME
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 5
    job_timeout = 1800
    # Retry is decided by the run row (bounded attempts, never for an uncertain call),
    # not by the queue, so a failure is never retried twice at two layers.
    retry_jobs = False
    max_tries = 1
