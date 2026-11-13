"""Review jobs persist independently, consume at most one model reply and recover safely."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from tests.integration.workflow_support import base_url, mutate, prepared, run_review


def test_auto_review_runs_once_on_its_own_job(client):
    with prepared(client) as (data, chat):
        before = client.get(base_url(data) + "/draft").content
        assert client.get(base_url(data) + "/auto-review").json()["status"] == "queued"
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: run_review(client, data["run_id"]), range(2)))
        assert sorted(results) == ["completed", "not_claimed"]
        row = client.get(base_url(data) + "/auto-review").json()
        assert row["status"] == "completed" and row["review_id"]
        assert len(chat.requests) == 2
        assert run_review(client, data["run_id"]) == "not_claimed"
        assert client.get(base_url(data) + "/draft").content == before
        assert (
            client.get(base_url(data) + "/reviews/" + row["review_id"] + "/report").status_code
            == 200
        )


@pytest.mark.parametrize("mode", ["http_error", "schema"])
def test_review_error_keeps_compiler_complete_and_does_not_resend(client, mode):
    with prepared(client) as (data, chat):
        chat.mode = mode
        assert run_review(client, data["run_id"]) == "failed"
        status = client.get(base_url(data) + "/auto-review").json()
        assert status["error_code"] and status["review_id"]
        assert client.get(base_url(data)).json()["status"] == "completed"
        assert run_review(client, data["run_id"]) == "not_claimed"
        assert len(chat.requests) == 2


def test_recovery_observes_existing_review_without_new_model_call(client):
    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.compilation.workflow.models import AutoReviewJob

    with prepared(client) as (data, chat):
        assert run_review(client, data["run_id"]) == "completed"
        mutate(
            client,
            AutoReviewJob,
            data["run_id"],
            status="running",
            finished_at=None,
            lease_expires_at=utcnow() - timedelta(seconds=1),
        )
        assert run_review(client, data["run_id"]) == "completed"
        assert len(chat.requests) == 2


def test_revoked_provider_fails_only_review_before_http(client):
    from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor

    with prepared(client) as (data, chat):
        as_actor(PLATFORM)
        result = client.put(f"{API}/modelops/defaults", json={"chat_provider_id": None})
        assert result.status_code == 200, result.text
        as_actor(EDITOR)
        assert run_review(client, data["run_id"]) == "failed"
        assert len(chat.requests) == 1
        assert client.get(base_url(data)).json()["status"] == "completed"


def test_outbox_reconciles_after_queue_failure_without_recompiling(client):
    from qnu.main import app
    from qnu.workers.tasks.compilation import compiler_review_reconcile
    from tests.integration.ocr_support import FakeJobQueue

    with prepared(client) as (data, chat):
        old = app.state.container.job_queue
        try:
            app.state.container.job_queue = FakeJobQueue(failing=True)
            assert (
                client.portal.call(compiler_review_reconcile, {"container": app.state.container})
                == 0
            )
            app.state.container.job_queue = FakeJobQueue()
            assert (
                client.portal.call(compiler_review_reconcile, {"container": app.state.container})
                == 1
            )
            assert (
                client.portal.call(compiler_review_reconcile, {"container": app.state.container})
                == 0
            )
            assert run_review(client, data["run_id"]) == "completed"
            assert len(chat.requests) == 2
        finally:
            app.state.container.job_queue = old


def test_uncertain_review_stays_uncertain_after_expired_job_recovery(client):
    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.compilation.workflow.models import AutoReviewJob
    from qnu.main import app
    from qnu.platform.errors import AppException

    class Uncertain:
        calls = 0

        async def complete(self, messages, request):
            self.calls += 1
            raise AppException(
                "Kết quả model chưa xác định.", code="chat_provider_uncertain", status_code=504
            )

    with prepared(client) as (data, _):
        old, chat = app.state.container.chat_model, Uncertain()
        app.state.container.chat_model = chat
        try:
            assert run_review(client, data["run_id"]) == "uncertain"
            mutate(
                client,
                AutoReviewJob,
                data["run_id"],
                status="running",
                finished_at=None,
                lease_expires_at=utcnow() - timedelta(seconds=1),
            )
            assert run_review(client, data["run_id"]) == "uncertain"
            assert chat.calls == 1
        finally:
            app.state.container.chat_model = old
