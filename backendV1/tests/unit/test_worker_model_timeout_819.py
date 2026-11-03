"""Model task deadline is explicit and independent from maintenance task limits."""

import pytest
from arq.worker import Function
from pydantic import ValidationError

from qnu.platform.config import Settings
from qnu.workers.settings import WorkerSettings, settings


def test_model_jobs_use_configured_long_deadline_and_keep_single_attempt():
    functions = {f.name: f for f in WorkerSettings.functions if isinstance(f, Function)}
    assert set(functions) == {
        "ocr_process_run",
        "compile_run",
        "compiler_review_job",
        "manual_compiler_review_job",
        "index_run",
    }
    assert all(f.timeout_s == settings.WORKER_MODEL_JOB_TIMEOUT_SECONDS for f in functions.values())
    assert Settings(_env_file=None).WORKER_MODEL_JOB_TIMEOUT_SECONDS == 86400
    assert WorkerSettings.retry_jobs is False and WorkerSettings.max_tries == 1
    assert WorkerSettings.job_timeout == 1800  # maintenance tasks stay bounded


def test_model_deadline_can_be_configured_without_using_zero_as_infinity():
    assert Settings(_env_file=None, WORKER_MODEL_JOB_TIMEOUT_SECONDS=172800).WORKER_MODEL_JOB_TIMEOUT_SECONDS == 172800
    with pytest.raises(ValidationError):
        Settings(_env_file=None, WORKER_MODEL_JOB_TIMEOUT_SECONDS=0)
