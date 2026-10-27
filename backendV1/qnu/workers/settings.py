"""ARQ worker settings for backendV1 (own queue, no legacy jobs)."""

from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from qnu.platform.config import get_settings
from qnu.workers.tasks.compilation import (
    compilation_reconcile,
    compile_run,
    compiler_review_job,
    compiler_review_reconcile,
)
from qnu.workers.tasks.indexing import index_reconcile, index_run
from qnu.workers.tasks.ocr import ocr_process_run, ocr_reconcile_queued, shutdown, startup
from qnu.workers.tasks.operations import (
    evidence_backup_delete,
    evidence_backup_job,
    operations_reconcile,
)

settings = get_settings()


class WorkerSettings:
    """Consumes only ``QUEUE_NAME`` of backendV1."""

    functions: list = [
        ocr_process_run,
        ocr_reconcile_queued,
        compile_run,
        compilation_reconcile,
        compiler_review_job,
        compiler_review_reconcile,
        index_run,
        index_reconcile,
        evidence_backup_job,
        evidence_backup_delete,
        operations_reconcile,
    ]
    # The reconcile cron only picks up v1 runs from the v1 table and enqueues them on the
    # v1 queue, so it can never touch a legacy job; the flag is the documented kill switch.
    cron_jobs: list = (
        [
            cron(ocr_reconcile_queued, minute=set(range(0, 60, 5))),
            cron(compilation_reconcile, minute=set(range(0, 60, 5))),
            cron(compiler_review_reconcile, minute=set(range(0, 60, 5))),
            cron(index_reconcile, minute=set(range(0, 60, 5))),
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
