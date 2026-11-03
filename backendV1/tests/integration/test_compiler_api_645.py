"""Compiler API boundaries exercised against PostgreSQL and the real OCR pipeline."""

import hashlib
from datetime import timedelta

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    OUTSIDER,
    PLATFORM,
    as_actor,
    create_collection,
)
from tests.integration.ocr_support import FakeJobQueue, set_quota, use_queue


def mutate_run(client, run_id, **values):
    from qnu.domains.knowledge.compilation.models import CompilationRun
    from qnu.platform.database import AsyncSessionFactory

    async def mutate():
        async with AsyncSessionFactory() as db:
            run = await db.get(CompilationRun, run_id)
            for key, value in values.items():
                setattr(run, key, value)
            await db.commit()

    client.portal.call(mutate)


def test_compiler_request_is_durable_and_idempotent(client):
    data = processed_input(client)
    chat_provider(client, data, "http://127.0.0.1:20128/v1")
    use_queue(FakeJobQueue(failing=True))
    first = request_compile(client, data)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["created"] is True
    assert body["dispatched"] is False
    assert body["run"]["status"] == "queued"
    second = request_compile(client, data)
    assert second.status_code == 200, second.text
    assert second.json()["run"]["id"] == body["run"]["id"]
    conflict = request_compile(client, data, topic="Khác nội dung")
    assert conflict.status_code == 409


def test_compiler_draft_retains_tables_citations_raw_and_single_delivery(client):
    data = processed_input(client)
    with FakeChat() as chat:
        provider = chat_provider(client, data, chat.base_url)
        queue = FakeJobQueue()
        use_queue(queue)
        created = request_compile(client, data)
        assert created.status_code == 201, created.text
        run_id = created.json()["run"]["id"]
        assert queue.jobs[0]["function"] == "compile_run"
        assert execute_compile(client, run_id) == "completed"
        assert execute_compile(client, run_id) == "not_claimed"
        assert len(chat.requests) == 1
        request = chat.requests[0]
        assert request["path"] == "/v1/chat/completions"
        assert request["authorization"] == "Bearer compiler-test-secret"
        assert request["body"]["model"] == "test-chat"
        url = data["url"] + "/" + run_id
        status = client.get(url).json()
        assert status["status"] == "completed"
        assert status["usage_tokens"] == 173
        response = client.get(url + "/draft")
        assert response.status_code == 200, response.text
        draft = response.json()
        assert draft["publication_status"] == "draft" and draft["requires_review"]
        assert draft["validation"]["semantic_faithfulness"] == "not_evaluated"
        refs = draft["sections"][0]["paragraphs"][0]["citations"]
        assert all(ref in draft["citations"] for ref in refs)
        assert all(draft["citations"][ref]["revision_id"] == data["revision"]["id"] for ref in refs)
        table = draft["source_tables"][0]["table"]
        texts = [cell["text"] for row in table["rows"] for cell in row]
        assert "0" in texts and "-" in texts and "" in texts and "150" in texts
        raw = client.get(url + "/raw")
        assert raw.content == chat.last_raw
        assert raw.headers["etag"] == '"' + hashlib.sha256(raw.content).hexdigest() + '"'
        assert raw.headers["cache-control"] == "private, no-store"
        assert client.get(url + "/markdown").status_code == 200
        listing = client.get(data["url"]).json()
        assert [r["id"] for r in listing] == [run_id]
        assert provider["id"] == status["provider_id"]


@pytest.mark.parametrize(
    "mode,code",
    [
        ("bad_citation", "compilation_citation_invalid"),
        ("bad_schema", "compilation_draft_invalid"),
        ("truncated", "compilation_refinement_atomic_limit"),
        ("http_error", "chat_provider_unavailable"),
    ],
)
def test_invalid_draft_never_succeeds_and_raw_is_preserved(client, mode, code):
    data = processed_input(client)
    with FakeChat() as chat:
        chat.mode = mode
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        requested = request_compile(client, data)
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_compile(client, run_id) == "failed"
        url = data["url"] + "/" + run_id
        assert client.get(url).json()["error_code"] == code
        assert client.get(url + "/draft").status_code == 409
        raw = client.get(url + "/raw")
        if mode == "truncated":
            assert raw.json()["choices"][0]["finish_reason"] == "length"
        else:
            assert raw.content == chat.last_raw
        assert execute_compile(client, run_id) == "not_claimed"
        assert 1 < len(chat.requests) <= 5 if mode == "truncated" else len(chat.requests) == 1


def test_compiler_access_is_checked_at_api_and_worker(client):
    data = processed_input(client)
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        as_actor(MEMBER)
        assert request_compile(client, data).status_code == 403
        as_actor(OUTSIDER)
        assert client.get(data["url"]).status_code == 404
        as_actor(None)
        assert request_compile(client, data).status_code == 401
        as_actor(EDITOR)
        run_id = request_compile(client, data).json()["run"]["id"]
        as_actor(OUTSIDER)
        assert client.get(data["url"] + "/" + run_id).status_code == 404
        as_actor(PLATFORM)
        workspace = data["workspace"]["id"]
        members = client.get(f"{API}/workspaces/{workspace}/members").json()["items"]
        member_id = next(m["id"] for m in members if m["actor_ref"] == EDITOR.actor_id)
        result = client.delete(f"{API}/workspaces/{workspace}/members/{member_id}")
        assert result.status_code in {200, 204}, result.text
        assert execute_compile(client, run_id) == "failed"
        assert not chat.requests


def test_compiler_rejects_ocr_from_another_collection(client):
    data = processed_input(client)
    chat_provider(client, data, "http://127.0.0.1:20128")
    other = create_collection(client, data["workspace"]["id"], "Other collection")
    wrong = {**data, "url": data["url"].replace(data["collection"]["id"], other["id"])}
    assert request_compile(client, wrong).status_code == 404


def test_compiler_rechecks_provider_and_quota_before_http(client):
    data = processed_input(client)
    with FakeChat() as chat:
        provider = chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run_id = request_compile(client, data).json()["run"]["id"]
        as_actor(PLATFORM)
        assert (
            client.patch(
                f"{API}/modelops/providers/{provider['id']}", json={"is_active": False}
            ).status_code
            == 200
        )
        assert execute_compile(client, run_id) == "failed"
        assert not chat.requests
        assert (
            client.patch(
                f"{API}/modelops/providers/{provider['id']}", json={"is_active": True}
            ).status_code
            == 200
        )
        as_actor(EDITOR)
        second = request_compile(client, data, key="quota-probe").json()["run"]["id"]
        assert set_quota(client, data["workspace"]["id"], 0).status_code == 200
        assert execute_compile(client, second) == "completed"
        assert chat.requests


def test_compiler_expired_inflight_request_is_not_resent(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.compilation.models import CompilationSegment, utcnow
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client)
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run_id = request_compile(client, data).json()["run"]["id"]
        mutate_run(
            client,
            run_id,
            status="running",
            worker_id="dead-worker",
            request_started_at=utcnow(),
            lease_expires_at=utcnow() - timedelta(seconds=10),
        )

        async def mark_durable_leaf_inflight():
            # New runs dispatch from leaf checkpoints, not the legacy run marker.
            async with AsyncSessionFactory() as db:
                leaf = await db.scalar(
                    select(CompilationSegment).where(
                        CompilationSegment.run_id == run_id,
                    )
                )
                leaf.status, leaf.request_started_at = "running", utcnow()
                await db.commit()

        client.portal.call(mark_durable_leaf_inflight)
        assert execute_compile(client, run_id) == "uncertain"
        assert not chat.requests
        assert execute_compile(client, run_id) == "not_claimed"


def test_compiler_pins_model_before_http(client):
    data = processed_input(client)
    with FakeChat() as chat:
        provider = chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run_id = request_compile(client, data).json()["run"]["id"]
        as_actor(PLATFORM)
        assert (
            client.patch(
                f"{API}/modelops/providers/{provider['id']}",
                json={
                    "model_name": "different-chat",
                    "token_limits": {
                        "context_window_tokens": 131072,
                        "max_output_tokens": 8192,
                    },
                },
            ).status_code
            == 200
        )
        assert execute_compile(client, run_id) == "failed"
        as_actor(EDITOR)
        assert (
            client.get(data["url"] + "/" + run_id).json()["error_code"]
            == "compilation_provider_changed"
        )
        assert not chat.requests


def test_compiler_model_timeout_stays_uncertain(client):
    from qnu.platform.errors import AppException

    class UncertainModel:
        calls = 0

        async def complete(self, messages, request):
            self.calls += 1
            raise AppException(
                "Chưa xác định kết quả.", code="chat_provider_uncertain", status_code=504
            )

    data = processed_input(client)
    chat_provider(client, data, "http://127.0.0.1:20128")
    use_queue(FakeJobQueue())
    run_id = request_compile(client, data).json()["run"]["id"]
    model = UncertainModel()
    assert execute_compile(client, run_id, model=model) == "uncertain"
    assert execute_compile(client, run_id, model=model) == "not_claimed"
    assert model.calls == 1


def test_compiler_concurrent_idempotency_creates_one_run(client):
    from concurrent.futures import ThreadPoolExecutor

    data = processed_input(client)
    chat_provider(client, data, "http://127.0.0.1:20128")
    use_queue(FakeJobQueue())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: request_compile(client, data), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 201]
    assert len({r.json()["run"]["id"] for r in responses}) == 1


def test_compiler_invalid_client_options_and_incomplete_ocr_are_rejected(client):
    from qnu.domains.ocr.models import OcrProcessingRun
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client)
    chat_provider(client, data, "http://127.0.0.1:20128")
    assert request_compile(client, data, endpoint="http://untrusted.invalid").status_code == 422

    async def incomplete():
        async with AsyncSessionFactory() as db:
            run = await db.get(OcrProcessingRun, data["ocr_run_id"])
            run.status = "failed"
            await db.commit()

    client.portal.call(incomplete)
    assert request_compile(client, data).status_code == 409


def test_compiler_checksum_failure_stops_before_http(client):
    from qnu.domains.knowledge.compilation.artifacts import artifact
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client)
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run_id = request_compile(client, data).json()["run"]["id"]

        async def corrupt_snapshot():
            async with AsyncSessionFactory() as db:
                stored = await artifact(db, run_id, "input_snapshot")
                await app.state.container.blob_store.put_bytes(stored.blob_key, b"tampered")

        client.portal.call(corrupt_snapshot)
        assert execute_compile(client, run_id) == "failed"
        assert (
            client.get(data["url"] + "/" + run_id).json()["error_code"]
            == "compilation_artifact_mismatch"
        )
        assert not chat.requests


def test_compiler_recovers_saved_raw_without_another_llm_request(client):
    from qnu.domains.knowledge.compilation.models import utcnow

    data = processed_input(client)
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run_id = request_compile(client, data).json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        mutate_run(
            client,
            run_id,
            status="running",
            worker_id="interrupted-after-save",
            lease_expires_at=utcnow() - timedelta(seconds=10),
            finished_at=None,
        )
        assert execute_compile(client, run_id) == "completed"
        assert len(chat.requests) == 1


def test_compiler_stale_worker_cannot_commit_model_response(client):
    from qnu.domains.knowledge.compilation.models import CompilationRun
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client)
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run_id = request_compile(client, data).json()["run"]["id"]

        class ReplacedWorker:
            async def complete(self, messages, request):
                result = await app.state.container.chat_model.complete(messages, request)
                async with AsyncSessionFactory() as db:
                    run = await db.get(CompilationRun, run_id)
                    run.worker_id = "other-worker"
                    await db.commit()
                return result

        assert execute_compile(client, run_id, model=ReplacedWorker()) == "not_claimed"
        url = data["url"] + "/" + run_id
        assert client.get(url + "/raw").status_code == 404
        assert client.get(url + "/draft").status_code == 409
        assert len(chat.requests) == 1
