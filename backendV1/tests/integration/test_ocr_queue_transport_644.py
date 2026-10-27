"""One actual Redis/ARQ delivery on a unique test queue; OCR stays a loopback mock."""

import asyncio
import os
import uuid
from urllib.parse import urlsplit

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import create_worker

from qnu.adapters.queue.arq_queue import ArqJobQueue
from qnu.domains.ocr.execution import job_id_for
from qnu.platform.config import get_settings
from qnu.workers.settings import WorkerSettings
from qnu.workers.tasks.ocr import shutdown
from tests.integration.ocr_support import FakeNemotron, use_queue
from tests.integration.test_ocr_observability_644 import prepare


def test_real_queue_delivers_persisted_run_once(client, monkeypatch):
    redis_url = os.environ.get("TEST_REDIS_URL", "")
    if not redis_url:
        pytest.skip("NOT RUN: TEST_REDIS_URL is required for actual queue delivery.")
    assert urlsplit(redis_url).hostname in {"127.0.0.1", "localhost", "::1"}
    queue_name = "qnu:v1:test:ocr:" + uuid.uuid4().hex
    monkeypatch.setattr(get_settings(), "QUEUE_NAME", queue_name)
    monkeypatch.setattr(get_settings(), "REDIS_URL", redis_url)
    queue = ArqJobQueue(redis_url, queue_name)
    with FakeNemotron() as fake:
        run, url, _revision, _provider = prepare(client, fake, "real-queue-644")
        use_queue(queue)
        try:
            assert client.post(url + "/dispatch").status_code == 202

            # Duplicate delivery before processing is rejected by the real Redis adapter.
            async def duplicate():
                return await queue.enqueue(
                    "ocr_process_run", run["id"], job_id=job_id_for(run["id"], 1)
                )

            assert client.portal.call(duplicate) is False

            async def consume():
                pool = await create_pool(
                    RedisSettings.from_dsn(redis_url), default_queue_name=queue_name
                )
                worker = create_worker(
                    WorkerSettings,
                    redis_pool=pool,
                    queue_name=queue_name,
                    cron_jobs=[],
                    burst=True,
                    max_burst_jobs=1,
                    max_jobs=1,
                    handle_signals=False,
                    keep_result=0,
                    poll_delay=0.05,
                )
                try:
                    await asyncio.wait_for(worker.async_run(), timeout=30)
                    return worker.jobs_complete, worker.jobs_failed
                finally:
                    # Explicit lifecycle cleanup works on Windows without Unix signals.
                    if "container" in worker.ctx:
                        await shutdown(worker.ctx)
                    await pool.delete(queue_name, queue_name + ":health-check")
                    await pool.aclose()

            assert client.portal.call(consume) == (1, 0)
            assert client.get(url).json()["status"] == "completed"
            assert len(fake.requests) == 1
            # Calling the actual task again cannot claim a completed run.
            from tests.integration.ocr_support import execute_now

            assert execute_now(client, run["id"]).status == "not_claimed"
            assert len(fake.requests) == 1
        finally:

            async def cleanup():
                pool = await queue._get_pool()
                job_id = job_id_for(run["id"], 1)
                keys = [queue_name, queue_name + ":health-check"]
                keys += [
                    prefix + job_id
                    for prefix in (
                        "arq:job:",
                        "arq:result:",
                        "arq:retry:",
                        "arq:in-progress:",
                    )
                ]
                await pool.delete(*keys)
                assert await pool.exists(*keys) == 0
                await queue.close()

            client.portal.call(cleanup)
