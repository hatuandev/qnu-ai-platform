# ruff: noqa: F811
"""Lifecycle behavior crosses HTTP, persistent state, worker fences and actual local Qdrant."""

import asyncio

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.index_support import execute_index
from tests.integration.knowledge_support import API, EDITOR, MEMBER, PLATFORM, add_member, as_actor
from tests.integration.ocr_support import (
    TABLE_RESPONSE,
    FakeJobQueue,
    FakeNemotron,
    execute_now,
    real_pdf,
    request_run,
    setup_ocr_provider,
    use_queue,
)
from tests.integration.test_answers_api_648 import ready  # noqa: F401
from tests.integration.test_conversations_649 import chat_session, send  # noqa: F401
from tests.integration.test_index_api_647 import indexed  # noqa: F401
from tests.integration.test_lifecycle_659 import accept, lifecycle, preview
from tests.integration.test_publication_646 import decision


@pytest.mark.parametrize("kind", ["source", "document"])
def test_archive_excludes_evidence_and_restore_preserves_original_index(client, chat_session, kind):
    data = chat_session
    first = send(client, data)
    assert first.status_code == 200, first.text
    before = len(data["embedding"].requests)
    as_actor(PLATFORM)
    resource_id = data["source"]["id"] if kind == "source" else data["compiled"]["document"]["id"]
    result = accept(
        client, data["workspace"], preview(client, data["workspace"], kind, resource_id, "archive")
    )
    assert result.status_code == 200, result.text
    response = client.post(data["base"] + "/search", json={"query": "Q"})
    assert response.status_code == 200, response.text
    assert not response.json()["hits"]
    assert len(data["embedding"].requests) == before
    as_actor(EDITOR)
    history = client.get(data["conversation_url"] + "/turns").json()
    assert history[0]["result"] is None and history[0]["source_status"] == "unavailable"
    as_actor(PLATFORM)
    restored = accept(
        client,
        data["workspace"],
        preview(client, data["workspace"], kind, resource_id, "restore"),
        "restore",
    )
    assert restored.status_code == 200, restored.text
    assert client.post(data["base"] + "/search", json={"query": "Q"}).json()["hits"]


def test_pause_resume_and_delete_assistant_keep_owned_conversations(client, chat_session):
    data = chat_session
    workspace, assistant_id = data["workspace"], data["assistant"]["id"]
    as_actor(PLATFORM)
    assert (
        accept(
            client, workspace, preview(client, workspace, "assistant", assistant_id, "pause")
        ).status_code
        == 200
    )
    as_actor(EDITOR)
    assert send(client, data).json()["code"] == "assistant_inactive"
    as_actor(PLATFORM)
    assert (
        accept(
            client,
            workspace,
            preview(client, workspace, "assistant", assistant_id, "resume"),
            "resume",
        ).status_code
        == 200
    )
    as_actor(EDITOR)
    assert send(client, data).status_code == 200
    as_actor(PLATFORM)
    assert (
        accept(
            client,
            workspace,
            preview(client, workspace, "assistant", assistant_id, "delete"),
            "delete",
        ).status_code
        == 200
    )
    assistant_url = f"{API}/workspaces/{workspace['id']}/assistants"
    assert not client.get(assistant_url).json()
    as_actor(EDITOR)
    assert client.get(data["conversation_url"] + "/turns").status_code == 404
    as_actor(PLATFORM)
    assert (
        accept(
            client,
            workspace,
            preview(client, workspace, "assistant", assistant_id, "restore"),
            "restore",
        ).status_code
        == 200
    )
    assert not client.get(assistant_url + "/" + assistant_id).json()["is_active"]
    assert (
        accept(
            client,
            workspace,
            preview(client, workspace, "assistant", assistant_id, "resume"),
            "resume-again",
        ).status_code
        == 200
    )
    as_actor(EDITOR)
    assert client.get(data["conversation_url"] + "/turns").json()[0]["result"]


def test_deleted_conversation_is_private_and_cannot_be_reopened_through_old_api(
    client, chat_session
):
    data = chat_session
    p = preview(client, data["workspace"], "conversation", data["conversation"]["id"], "delete")
    assert accept(client, data["workspace"], p).status_code == 200
    assert (
        client.put(data["conversation_url"], json={"title": "Q", "status": "active"}).status_code
        == 404
    )
    assert client.get(lifecycle(data["workspace"]) + "/resources").json()["items"]
    as_actor(MEMBER)
    assert not client.get(lifecycle(data["workspace"]) + "/resources").json()["items"]
    assert (
        preview(
            client, data["workspace"], "conversation", data["conversation"]["id"], "restore"
        ).status_code
        == 404
    )


def test_cancel_queued_index_is_durable_and_worker_never_calls_model(client, indexed):
    data = indexed
    as_actor(PLATFORM)
    p = preview(
        client, data["workspace"], "job", data["index_run"]["id"], "cancel", job_kind="index"
    )
    result = accept(client, data["workspace"], p)
    assert result.status_code == 200, result.text
    assert execute_index(client, data["index_run"]["id"]) == "not_claimed"
    assert not data["embedding"].requests
    response = client.get(data["base"] + "/indexing-runs/" + data["index_run"]["id"])
    assert response.json()["status"] == "cancelled"
    again = client.post(
        data["base"] + "/indexing-runs", json={}, headers={"Idempotency-Key": "fresh-after-cancel"}
    )
    assert again.status_code == 201, again.text


def test_late_answer_after_pause_is_discarded_and_turn_stays_cancelled(
    client, chat_session, monkeypatch
):
    from qnu.main import app

    data = chat_session
    original = app.state.container.chat_model

    class PauseDuringChat:
        async def complete(self, messages, request):
            result = await original.complete(messages, request)

            def pause():
                as_actor(PLATFORM)
                result = accept(
                    client,
                    data["workspace"],
                    preview(
                        client, data["workspace"], "assistant", data["assistant"]["id"], "pause"
                    ),
                )
                assert result.status_code == 200, result.text

            await asyncio.to_thread(pause)
            return result

    monkeypatch.setattr(app.state.container, "chat_model", PauseDuringChat())
    response = send(client, data)
    assert response.status_code == 409, response.text
    as_actor(EDITOR)
    turn = client.get(data["conversation_url"] + "/turns").json()[0]
    assert turn["status"] == "cancelled" and turn["result"] is None


def staged_version(client, data):
    """Prepare a new real PDF revision with synthetic OCR/Compiler HTTP providers."""
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    with FakeNemotron() as ocr, FakeChat() as chat:
        ocr.responses = [TABLE_RESPONSE]
        data["ocr_provider"] = setup_ocr_provider(client, data["workspace"]["id"], ocr.base_url)
        as_actor(EDITOR)
        source_url = data["base"] + "/sources/" + data["source"]["id"]
        uploaded = client.post(
            source_url + "/revisions",
            files={
                "file": ("replacement.pdf", real_pdf(["Replacement revision"]), "application/pdf")
            },
            # This fixture deliberately stages first, then explicitly requests OCR.
            data={"staged": "true", "auto_extract": "false"},
        )
        assert uploaded.status_code == 201, uploaded.text
        revision = uploaded.json()["revision"]
        assert uploaded.json()["source"]["serving_revision_no"] == 1
        requested = request_run(
            client,
            data["workspace"]["id"],
            data["collection"]["id"],
            data["source"]["id"],
            revision["id"],
            queue=FakeJobQueue(),
        )
        assert requested.status_code == 201, requested.text
        ocr_id = requested.json()["run"]["id"]
        assert execute_now(client, ocr_id).status == "completed"
        as_actor(PLATFORM)
        provider = next(
            p
            for p in client.get(f"{API}/modelops/providers").json()
            if p["name"] == "chat-" + data["workspace"]["id"]
        )
        changed = client.patch(
            f"{API}/modelops/providers/{provider['id']}",
            json={
                "base_url": chat.base_url,
                "token_limits": {"context_window_tokens": 131072, "max_output_tokens": 8192},
            },
        )
        assert changed.status_code == 200, changed.text
        assert (
            client.put(
                f"{API}/workspaces/{data['workspace']['id']}/allowed-providers",
                json={
                    "provider_ids": [data["ocr_provider"]["id"], provider["id"]],
                    "defaults": {"ocr": data["ocr_provider"]["id"], "chat": provider["id"]},
                },
            ).status_code
            == 200
        )
        as_actor(EDITOR)
        use_queue(FakeJobQueue())
        compiled = request_compile(client, {**data, "ocr_run_id": ocr_id}, key="new-compiler")
        assert compiled.status_code == 201, compiled.text
        run_id = compiled.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        registered = client.post(
            data["document_url"] + "/versions",
            json={"compilation_run_id": run_id},
            headers={"Idempotency-Key": "new-version"},
        )
        assert registered.status_code == 201, registered.text
        version_id = registered.json()["version"]["id"]
        as_actor(PLATFORM)
        assert (
            decision(
                client,
                data["document_url"] + "/versions/" + version_id,
                "approve",
                key="approve-staged",
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"{API}/workspaces/{data['workspace']['id']}/allowed-providers",
                json={
                    "provider_ids": [
                        data["ocr_provider"]["id"],
                        data["embedding_provider"]["id"],
                        provider["id"],
                    ],
                    "defaults": {
                        "ocr": data["ocr_provider"]["id"],
                        "embedding": data["embedding_provider"]["id"],
                        "chat": provider["id"],
                    },
                },
            ).status_code
            == 200
        )
    return version_id


@pytest.mark.parametrize("failure", [False, True])
def test_replacement_keeps_old_serving_until_index_completes(client, indexed, failure):
    data = indexed
    assert execute_index(client, data["index_run"]["id"]) == "completed"
    version_id = staged_version(client, data)
    old_id = data["compiled"]["version"]["id"]
    assert client.get(data["document_url"] + "/published").json()["version"]["id"] == old_id
    assert client.post(data["base"] + "/search", json={"query": "Q"}).json()["hits"]
    p = preview(
        client,
        data["workspace"],
        "document",
        data["compiled"]["document"]["id"],
        "replace",
        replacement_version_id=version_id,
    )
    result = accept(client, data["workspace"], p)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "pending"
    run_id = result.json()["result"]["index_run_id"]
    assert client.get(data["document_url"] + "/published").json()["version"]["id"] == old_id
    if failure:
        data["embedding"].mode = "auth_error"
    status = execute_index(client, run_id)
    assert status == ("failed" if failure else "completed"), client.get(
        data["base"] + "/indexing-runs/" + run_id
    ).json()
    receipt = client.get(lifecycle(data["workspace"]) + "/actions/" + result.json()["id"]).json()
    assert receipt["status"] == ("failed" if failure else "completed")
    active_id = client.get(data["document_url"] + "/published").json()["version"]["id"]
    assert active_id == (old_id if failure else version_id)
    readiness = client.get(data["document_url"] + "/index-readiness")
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["status"] == "ready"
    assert readiness.json()["version_id"] == active_id
    if not failure:
        # Candidate index is requested before its atomic publication decision.
        # Readiness must follow the binding, not requested_at >= published_at.
        assert readiness.json()["index_run_id"] == run_id
    data["embedding"].mode = "ok"
    hits = client.post(data["base"] + "/search", json={"query": "Q"}).json()["hits"]
    assert hits and all(h["version_id"] == active_id for h in hits)


def test_cleanup_rejects_active_index_and_retries_only_owned_inactive_generation(
    client, indexed, monkeypatch
):
    from qnu.main import app

    data = indexed
    assert execute_index(client, data["index_run"]["id"]) == "completed"
    as_actor(PLATFORM)
    assert (
        preview(client, data["workspace"], "index", data["index_run"]["id"], "cleanup").status_code
        == 409
    )
    as_actor(EDITOR)
    second = client.post(
        data["base"] + "/indexing-runs", json={}, headers={"Idempotency-Key": "second"}
    ).json()["run"]
    assert execute_index(client, second["id"]) == "completed"
    as_actor(PLATFORM)
    p = preview(client, data["workspace"], "index", data["index_run"]["id"], "cleanup")
    original = app.state.container.vector_store.delete_collection

    async def unavailable(name):
        from qnu.platform.errors import DependencyUnavailable

        raise DependencyUnavailable("Synthetic outage", code="vector_unavailable")

    monkeypatch.setattr(app.state.container.vector_store, "delete_collection", unavailable)
    assert accept(client, data["workspace"], p).status_code == 503
    monkeypatch.setattr(app.state.container.vector_store, "delete_collection", original)
    response = accept(client, data["workspace"], p)
    assert response.status_code == 200 and response.json()["status"] == "completed", response.text
    assert (
        client.post(data["base"] + "/search", json={"query": "Q"}).json()["index_run_id"]
        == second["id"]
    )


def measured_usage(client, request_prefix):
    from sqlalchemy import select

    from qnu.domains.modelops.models import ModelUsageRecord
    from qnu.platform.database import AsyncSessionFactory

    async def load():
        async with AsyncSessionFactory() as db:
            records = list(
                (
                    await db.scalars(
                        select(ModelUsageRecord).where(
                            ModelUsageRecord.request_id.startswith(request_prefix)
                        )
                    )
                ).all()
            )
            assert records and all(
                r.total_tokens is not None and r.total_tokens > 0 and r.status == "failed"
                for r in records
            )

    client.portal.call(load)


def test_cancellation_during_embedding_accounts_for_usage_and_never_activates(client, indexed):
    from qnu.main import app

    data = indexed
    original = app.state.container.embedding_model

    class CancelDuringEmbedding:
        async def embed(self, texts, request):
            result = await original.embed(texts, request)

            def cancel():
                as_actor(PLATFORM)
                p = preview(
                    client,
                    data["workspace"],
                    "job",
                    data["index_run"]["id"],
                    "cancel",
                    job_kind="index",
                )
                response = accept(client, data["workspace"], p)
                assert response.status_code == 200, response.text

            await asyncio.to_thread(cancel)
            return result

    assert (
        execute_index(client, data["index_run"]["id"], model=CancelDuringEmbedding())
        == "not_claimed"
    )
    status = client.get(data["base"] + "/indexing-runs/" + data["index_run"]["id"]).json()
    assert status["status"] == "cancelled" and not status["is_active"]
    measured_usage(client, "index:" + data["index_run"]["id"])


def test_cancellation_during_compiler_retains_cancelled_status_and_usage(client):
    from qnu.main import app

    data = processed_input(client, code="cancel-compiler")
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        response = request_compile(client, data)
        assert response.status_code == 201, response.text
        run_id = response.json()["run"]["id"]
        original = app.state.container.chat_model

        class CancelDuringCompiler:
            async def complete(self, messages, request):
                result = await original.complete(messages, request)

                def cancel():
                    as_actor(PLATFORM)
                    p = preview(
                        client, data["workspace"], "job", run_id, "cancel", job_kind="compiler"
                    )
                    cancelled = accept(client, data["workspace"], p)
                    assert cancelled.status_code == 200, cancelled.text

                await asyncio.to_thread(cancel)
                return result

        assert execute_compile(client, run_id, model=CancelDuringCompiler()) == "not_claimed"
    assert client.get(data["url"] + "/" + run_id).json()["status"] == "cancelled"
    assert client.get(data["url"] + "/" + run_id + "/draft").status_code == 409
    measured_usage(client, "compile:" + run_id)


def test_last_source_can_retire_and_clean_index_but_restore_needs_reindex(client, indexed):
    data = indexed
    assert execute_index(client, data["index_run"]["id"]) == "completed"
    as_actor(PLATFORM)
    assert (
        accept(
            client,
            data["workspace"],
            preview(client, data["workspace"], "source", data["source"]["id"], "archive"),
        ).status_code
        == 200
    )
    p = preview(client, data["workspace"], "index", data["index_run"]["id"], "cleanup")
    assert p.status_code == 200 and p.json()["impact"]["retires_active_index"], p.text
    assert accept(client, data["workspace"], p, "cleanup").status_code == 200
    restore = preview(client, data["workspace"], "source", data["source"]["id"], "restore")
    assert restore.status_code == 200 and restore.json()["impact"]["restore_requires_new_index"], (
        restore.text
    )
    assert accept(client, data["workspace"], restore, "restore").status_code == 200
    as_actor(EDITOR)
    response = client.post(
        data["base"] + "/indexing-runs", json={}, headers={"Idempotency-Key": "rebuild"}
    )
    assert response.status_code == 201, response.text
    assert execute_index(client, response.json()["run"]["id"]) == "completed"
    assert client.post(data["base"] + "/search", json={"query": "Q"}).json()["hits"]


def test_replacement_rolls_back_publication_on_manifest_failure_and_reuses_embeddings(
    client, indexed, monkeypatch
):
    from qnu.main import app

    data = indexed
    assert execute_index(client, data["index_run"]["id"]) == "completed"
    version_id = staged_version(client, data)
    p = preview(
        client,
        data["workspace"],
        "document",
        data["compiled"]["document"]["id"],
        "replace",
        replacement_version_id=version_id,
    )
    accepted = accept(client, data["workspace"], p)
    assert accepted.status_code == 200, accepted.text
    run_id = accepted.json()["result"]["index_run_id"]
    blob = app.state.container.blob_store
    original = blob.put_bytes

    async def fail_manifest(key, content, content_type):
        if f"/index/{run_id}/manifest/" in key:
            raise OSError("Synthetic manifest storage outage")
        return await original(key, content, content_type)

    monkeypatch.setattr(blob, "put_bytes", fail_manifest)
    assert execute_index(client, run_id) == "queued"
    assert (
        client.get(data["document_url"] + "/published").json()["version"]["id"]
        == data["compiled"]["version"]["id"]
    )
    assert (
        client.get(data["document_url"] + "/versions/" + version_id).json()["status"] == "approved"
    )
    before = len(data["embedding"].requests)
    monkeypatch.setattr(blob, "put_bytes", original)
    assert execute_index(client, run_id) == "completed"
    assert len(data["embedding"].requests) == before
    assert client.get(data["document_url"] + "/published").json()["version"]["id"] == version_id


def test_cancel_auto_review_between_claim_and_child_creation_never_calls_model(client, monkeypatch):
    from qnu.domains.knowledge.compilation.workflow import automatic
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client, code="cancel-auto-review")
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        response = request_compile(client, data)
        assert response.status_code == 201, response.text
        run_id = response.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        original = automatic.execute
        before = len(chat.requests)

        async def cancel_before_child(*args, **kwargs):
            def cancel():
                as_actor(PLATFORM)
                p = preview(
                    client, data["workspace"], "job", run_id, "cancel", job_kind="auto_review"
                )
                result = accept(client, data["workspace"], p)
                assert result.status_code == 200, result.text

            await asyncio.to_thread(cancel)
            return await original(*args, **kwargs)

        monkeypatch.setattr(automatic, "execute", cancel_before_child)

        async def execute():
            async with AsyncSessionFactory() as db:
                return await automatic.execute_job(
                    db,
                    app.state.container.blob_store,
                    app.state.container.chat_model,
                    run_id,
                    "cancel-race",
                )

        client.portal.call(execute)
        assert len(chat.requests) == before
    state = client.get(data["url"] + "/" + run_id + "/auto-review").json()
    assert state["status"] == "cancelled"
