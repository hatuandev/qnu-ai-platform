"""Manual reviews acknowledge durable intent before dispatching inference."""

import asyncio
from threading import Event

from qnu.domains.knowledge.compilation.review.execution import run_queued
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from tests.integration.knowledge_support import EDITOR, MEMBER, as_actor
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.test_compiler_review_652 import prepared


def enqueue(client, data, key="manual-852"):
    response = client.post(
        data["review_url"] + "?background=true",
        json={},
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def consume(review_id, model=None):
    container = app.state.container
    async with AsyncSessionFactory() as db:
        return await run_queued(db, container.blob_store, model or container.chat_model, review_id)


def test_enqueue_replay_and_worker_execute_once(client):
    with prepared(client) as (data, chat):
        queue = FakeJobQueue()
        use_queue(queue)
        before = len(chat.requests)
        row = enqueue(client, data)
        assert row["status"] == "queued"
        assert enqueue(client, data)["id"] == row["id"]
        assert len(chat.requests) == before
        assert [(job["function"], job["args"]) for job in queue.jobs] == [
            ("manual_compiler_review_job", (row["id"],)),
        ]
        assert client.portal.call(consume, row["id"]) == "completed"
        assert client.portal.call(consume, row["id"]) == "not_claimed"
        assert len(chat.requests) == before + 1


def test_stop_queued_is_authorized_idempotent_and_prevents_dispatch(client):
    with prepared(client) as (data, chat):
        use_queue(FakeJobQueue(failing=True))
        before = len(chat.requests)
        row = enqueue(client, data)
        url = f"{data['review_url']}/{row['id']}"
        as_actor(MEMBER)
        assert client.post(url + "/cancel").status_code == 403
        as_actor(EDITOR)
        for _ in range(2):
            assert client.post(url + "/cancel").json()["status"] == "cancelled"
        assert enqueue(client, data)["status"] == "cancelled"
        assert client.get(url + "/progress").json()["cancelled"] == 1
        assert client.portal.call(consume, row["id"]) == "not_claimed"
        assert len(chat.requests) == before


def test_stop_running_cancels_local_wait_without_report(client):
    class BlockingModel:
        async def complete(self, messages, request):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                interrupted.set()

    started, interrupted = Event(), Event()
    with prepared(client) as (data, _):
        use_queue(FakeJobQueue())
        row = enqueue(client, data)
        url = f"{data['review_url']}/{row['id']}"
        task = client.portal.start_task_soon(consume, row["id"], BlockingModel())
        try:
            assert started.wait(10)
            assert client.post(url + "/cancel").json()["status"] == "cancelled"
            assert task.result(timeout=10) == "cancelled"
        finally:
            if not task.done():
                task.cancel()
        assert interrupted.is_set()
        assert client.get(url + "/progress").json()["status"] == "cancelled"
        assert client.get(url + "/report").status_code != 200
