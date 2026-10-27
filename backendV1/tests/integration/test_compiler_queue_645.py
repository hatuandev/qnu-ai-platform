"""Actual Redis/ARQ delivery and reconcile on a dedicated, disposable queue."""

import asyncio
import os
import uuid
from urllib.parse import urlsplit

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import create_worker

from qnu.adapters.queue.arq_queue import ArqJobQueue
from qnu.main import app
from qnu.platform.config import get_settings
from qnu.workers.settings import WorkerSettings
from qnu.workers.tasks.compilation import compilation_reconcile
from qnu.workers.tasks.ocr import shutdown
from tests.integration.compiler_support import (
    chat_provider,
    processed_input,
    request_compile,
)
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.test_compiler_review_652 import ReviewChat


def test_compiler_reconcile_delivers_durable_run_on_real_arq(client, monkeypatch):
    redis_url = os.environ.get("TEST_REDIS_URL", "")
    if not redis_url:
        pytest.skip("NOT RUN: TEST_REDIS_URL is required for actual ARQ delivery.")
    assert urlsplit(redis_url).hostname in {"127.0.0.1", "localhost", "::1"}
    queue_name = "qnu:v1:test:compiler:" + uuid.uuid4().hex
    monkeypatch.setattr(get_settings(), "QUEUE_NAME", queue_name)
    monkeypatch.setattr(get_settings(), "REDIS_URL", redis_url)
    queue = ArqJobQueue(redis_url, queue_name)
    data = processed_input(client)
    with ReviewChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue(failing=True))
        result = request_compile(client, data)
        assert result.status_code == 201, result.text
        assert result.json()["dispatched"] is False
        run_id = result.json()["run"]["id"]
        from qnu.domains.knowledge.compilation.models import utcnow

        job_id = f"qnu:v1:compile:{run_id}:reconcile:{int(utcnow().timestamp()) // 300}"
        old_queue = app.state.container.job_queue
        app.state.container.job_queue = queue
        try:

            async def consume():
                assert await compilation_reconcile({"container": app.state.container}) == 1
                assert await compilation_reconcile({"container": app.state.container}) == 0
                pool = await create_pool(
                    RedisSettings.from_dsn(redis_url), default_queue_name=queue_name
                )
                try:
                    completed, failed = 0, 0
                    # Burst mode may see an empty queue while the Compiler is still
                    # running. Consume each persisted stage in a fresh burst.
                    for _ in range(2):
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
                            completed += worker.jobs_complete
                            failed += worker.jobs_failed
                        finally:
                            if "container" in worker.ctx:
                                await shutdown(worker.ctx)
                    return completed, failed
                finally:
                    await pool.aclose()

            assert client.portal.call(consume) == (2, 0)
            assert client.get(data["url"] + "/" + run_id).json()["status"] == "completed"
            assert len(chat.requests) == 2
            assert (
                client.get(data["url"] + "/" + run_id + "/auto-review").json()["status"]
                == "completed"
            )
        finally:
            app.state.container.job_queue = old_queue

            async def cleanup():
                pool = await queue._get_pool()
                keys = [queue_name, queue_name + ":health-check"]
                job_ids = [job_id] + [
                    item.job_id for item in await pool.queued_jobs(queue_name=queue_name)
                ]
                bucket = int(utcnow().timestamp()) // 300
                job_ids += [
                    f"qnu:v1:compiler-review:{run_id}:{b}" for b in (bucket - 1, bucket, bucket + 1)
                ]
                keys += [
                    prefix + owned_job_id
                    for owned_job_id in job_ids
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
