"""Preparation intent: durable handoff from an accepted source to a ready draft.

Every helper drives the real HTTP stack. Workers are invoked through their real
service entry points against the real container, so the database row and its
pinned hashes — not the queue — decide what may run next.
"""

from sqlalchemy import func, select

from qnu.domains.knowledge.compilation.models import CompilationInput, CompilationRun
from qnu.domains.knowledge.preparation import service as preparation
from qnu.domains.knowledge.preparation.models import PreparationIntent
from qnu.domains.knowledge.publication.models import CompiledDocument, PublicationDecision
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.review.models import TextVersion
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
)
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    OUTSIDER,
    PLATFORM,
    as_actor,
    create_collection,
    upload_source,
    workspace_with_editor,
)
from tests.integration.ocr_support import (
    FakeJobQueue,
    FakeNemotron,
    execute_now,
    real_pdf,
    request_run,
    setup_ocr_provider,
    use_queue,
)
from tests.integration.test_ocr_text_review_651 import edit_body, save


def _intent_url(data: dict) -> str:
    return (
        f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
        f"/sources/{data['source']['id']}/preparation-intents"
    )


def _status_url(data: dict, intent_id: str) -> str:
    return (
        f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
        f"/preparation-intents/{intent_id}"
    )


def _review_url(data: dict, run_id: str) -> str:
    return (
        f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
        f"/sources/{data['source']['id']}/revisions/{data['revision']['id']}"
        f"/processing-runs/{run_id}/text-review"
    )


def create_intent(client, data: dict, *, key: str = "prep-one", **body):
    use_queue(body.pop("queue", None))
    return client.post(_intent_url(data), json=body, headers={"Idempotency-Key": key})


def advance(client, intent_id: str, queue=None) -> str:
    async def _run():
        async with AsyncSessionFactory() as db:
            return await preparation.execute_intent(
                db, app.state.container.blob_store, queue, intent_id, "prep-test"
            )

    return client.portal.call(_run)


def count(client, model) -> int:
    async def _run():
        async with AsyncSessionFactory() as db:
            return await db.scalar(select(func.count()).select_from(model))

    return client.portal.call(_run)


def mutate(client, model, row_id: str, **values) -> None:
    async def _run():
        async with AsyncSessionFactory() as db:
            row = await db.get(model, row_id, populate_existing=True)
            for key, value in values.items():
                setattr(row, key, value)
            await db.commit()

    client.portal.call(_run)


def prepared_workspace(client, code: str, ocr_api: FakeNemotron) -> dict:
    workspace = workspace_with_editor(client, code)
    as_actor(EDITOR)
    ocr_provider = setup_ocr_provider(client, workspace["id"], ocr_api.base_url)
    collection = create_collection(client, workspace["id"], "Chuẩn bị nội dung")
    response = upload_source(
        client,
        workspace["id"],
        collection["id"],
        payload=real_pdf(["PHỤ LỤC 01"]),
        filename="de-an.pdf",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "workspace": workspace,
        "collection": collection,
        "source": body["source"],
        "revision": body["revision"],
        "ocr_provider": ocr_provider,
    }


def test_golden_path_reaches_ready_without_opening_ocr_or_compiler(client):
    with FakeNemotron() as ocr_api, FakeChat() as chat_api:
        data = prepared_workspace(client, "prep-golden", ocr_api)
        chat_api.mode = "http_error"  # source mode must not need the AI endpoint
        chat_provider(client, data, chat_api.base_url, secret=None)
        queue = FakeJobQueue()
        created = create_intent(client, data, queue=queue)
        assert created.status_code == 201, created.text
        body = created.json()
        intent = body["intent"]
        assert body["created"] is True and body["dispatched"] is True
        assert intent["status"] == "queued" and intent["mode"] == "source"
        assert intent["revision_no"] == 1 and len(intent["revision_sha256"]) == 64

        assert advance(client, intent["id"], queue) == "waiting_ocr"
        phase = client.get(_status_url(data, intent["id"])).json()
        assert phase["status"] == "waiting_ocr" and phase["ocr_run_id"]
        assert execute_now(client, phase["ocr_run_id"]).status == "completed"

        assert advance(client, intent["id"], queue) == "compiling"
        phase = client.get(_status_url(data, intent["id"])).json()
        assert phase["compilation_run_id"]
        assert execute_compile(client, phase["compilation_run_id"]) == "completed"

        assert advance(client, intent["id"], queue) == "ready"
        final = client.get(_status_url(data, intent["id"])).json()
        assert final["status"] == "ready" and final["error_code"] is None
        assert final["compilation_run_id"] == phase["compilation_run_id"]
        assert not ocr_api.requests  # native text page; never calls OCR
        assert not chat_api.requests  # source-first; never calls the model
        assert count(client, OcrProcessingRun) == 1
        assert count(client, CompilationRun) == 1
        # Completion is not registration or publication.
        assert count(client, CompiledDocument) == 0
        assert count(client, PublicationDecision) == 0

        history = client.get(
            f"{API}/workspaces/{data['workspace']['id']}/collections"
            f"/{data['collection']['id']}/sources/{data['source']['id']}/preparation-intents"
        )
        assert history.status_code == 200, history.text
        assert [row["id"] for row in history.json()] == [intent["id"]]


def test_replay_keeps_one_intent_and_changed_body_is_rejected(client):
    with FakeNemotron() as ocr_api:
        data = prepared_workspace(client, "prep-replay", ocr_api)
        queue = FakeJobQueue()
        first = create_intent(client, data, key="prep-replay", topic="Chủ đề A", queue=queue)
        assert first.status_code == 201, first.text
        replay = create_intent(client, data, key="prep-replay", topic="Chủ đề A", queue=queue)
        assert replay.status_code == 200, replay.text
        assert replay.json()["created"] is False
        assert replay.json()["intent"]["id"] == first.json()["intent"]["id"]
        changed = create_intent(client, data, key="prep-replay", topic="Chủ đề B")
        assert changed.status_code == 409
        assert changed.json()["code"] == "idempotency_conflict"
        assert count(client, PreparationIntent) == 1


def test_queue_outage_keeps_durable_intent_and_reconcile_recovers(client):
    with FakeNemotron() as ocr_api:
        data = prepared_workspace(client, "prep-queue", ocr_api)
        created = create_intent(client, data, key="prep-queue", queue=FakeJobQueue(failing=True))
        assert created.status_code == 201, created.text
        assert created.json()["dispatched"] is False
        status = client.get(_status_url(data, created.json()["intent"]["id"]))
        assert status.json()["status"] == "queued"

        recovery = FakeJobQueue()

        async def _reconcile():
            async with AsyncSessionFactory() as db:
                return await preparation.reconcile(db, recovery)

        assert client.portal.call(_reconcile) == 1
        assert [job["function"] for job in recovery.jobs] == ["preparation_job"]
        assert recovery.jobs[0]["args"] == (created.json()["intent"]["id"],)
        assert client.get(_status_url(data, created.json()["intent"]["id"])).json()["status"] == (
            "queued"
        )
        assert advance(client, created.json()["intent"]["id"], recovery) == "waiting_ocr"


def test_duplicate_delivery_cannot_create_a_second_run(client):
    with FakeNemotron() as ocr_api, FakeChat() as chat_api:
        data = prepared_workspace(client, "prep-duplicate", ocr_api)
        chat_provider(client, data, chat_api.base_url, secret=None)
        queue = FakeJobQueue()
        created = create_intent(client, data, key="prep-duplicate", queue=queue)
        intent_id = created.json()["intent"]["id"]

        assert advance(client, intent_id, queue) == "waiting_ocr"
        assert advance(client, intent_id, queue) == "waiting_ocr"
        assert count(client, OcrProcessingRun) == 1

        run_id = client.get(_status_url(data, intent_id)).json()["ocr_run_id"]
        assert execute_now(client, run_id).status == "completed"
        assert advance(client, intent_id, queue) == "compiling"
        assert advance(client, intent_id, queue) == "compiling"
        assert count(client, CompilationRun) == 1
        compilation_id = client.get(_status_url(data, intent_id)).json()["compilation_run_id"]

        # A worker crash after the compilation run was created but before the pin
        # was stored must replay the run-level idempotency key, not infer again.
        mutate(client, PreparationIntent, intent_id, compilation_run_id=None)
        assert advance(client, intent_id, queue) == "compiling"
        assert client.get(_status_url(data, intent_id)).json()["compilation_run_id"] == (
            compilation_id
        )
        assert count(client, CompilationRun) == 1

        assert execute_compile(client, compilation_id) == "completed"
        assert advance(client, intent_id, queue) == "ready"
        assert advance(client, intent_id, queue) == "not_claimed"
        assert count(client, CompilationRun) == 1
        assert not chat_api.requests


def test_cancel_and_revoked_membership_block_the_next_step(client):
    with FakeNemotron() as ocr_api:
        data = prepared_workspace(client, "prep-stop", ocr_api)
        queue = FakeJobQueue()
        created = create_intent(client, data, key="prep-stop", queue=queue)
        intent_id = created.json()["intent"]["id"]
        cancelled = client.post(_status_url(data, intent_id) + "/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
        assert advance(client, intent_id, queue) == "not_claimed"
        assert count(client, OcrProcessingRun) == 0

        second = create_intent(client, data, key="prep-revoked", queue=queue).json()["intent"]["id"]
        as_actor(PLATFORM)
        members = client.get(f"{API}/workspaces/{data['workspace']['id']}/members").json()["items"]
        member_id = next(m["id"] for m in members if m["actor_ref"] == EDITOR.actor_id)
        removed = client.delete(f"{API}/workspaces/{data['workspace']['id']}/members/{member_id}")
        assert removed.status_code in (200, 204), removed.text
        as_actor(EDITOR)
        assert advance(client, second, queue) == "failed"
        as_actor(PLATFORM)
        failed = client.get(_status_url(data, second)).json()
        assert failed["error_code"] in {"workspace_not_found", "workspace_forbidden"}
        assert count(client, OcrProcessingRun) == 0


def test_new_revision_does_not_switch_the_pinned_input(client):
    with FakeNemotron() as ocr_api:
        data = prepared_workspace(client, "prep-pinned", ocr_api)
        queue = FakeJobQueue()
        intent_id = create_intent(client, data, key="prep-pinned", queue=queue).json()["intent"]["id"]
        second = client.post(
            f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
            f"/sources/{data['source']['id']}/revisions",
            files={"file": ("de-an.pdf", real_pdf(["PHỤ LỤC 02"]), "application/pdf")},
        )
        assert second.status_code == 201, second.text
        assert second.json()["source"]["current_revision_no"] == 2

        assert advance(client, intent_id, queue) == "waiting_ocr"
        phase = client.get(_status_url(data, intent_id)).json()
        assert phase["revision_no"] == 1
        run_id = phase["ocr_run_id"]

        async def pinned_run():
            async with AsyncSessionFactory() as db:
                row = await db.get(OcrProcessingRun, run_id)
                return row.revision_id, row.revision_no

        assert client.portal.call(pinned_run) == (data["revision"]["id"], 1)


def test_revision_hash_mismatch_fails_before_any_model_call(client):
    with FakeNemotron() as ocr_api, FakeChat() as chat_api:
        data = prepared_workspace(client, "prep-tampered", ocr_api)
        chat_provider(client, data, chat_api.base_url, secret=None)
        queue = FakeJobQueue()
        intent_id = create_intent(client, data, key="prep-tampered", queue=queue).json()["intent"][
            "id"
        ]
        mutate(client, PreparationIntent, intent_id, revision_sha256="0" * 64)
        assert advance(client, intent_id, queue) == "failed"
        failed = client.get(_status_url(data, intent_id)).json()
        assert failed["error_code"] == "preparation_source_changed"
        assert count(client, OcrProcessingRun) == 0
        assert count(client, CompilationRun) == 0
        assert not chat_api.requests


def test_completed_run_and_saved_text_version_are_reused(client):
    with FakeNemotron() as ocr_api, FakeChat() as chat_api:
        data = prepared_workspace(client, "prep-reuse", ocr_api)
        chat_provider(client, data, chat_api.base_url, secret=None)
        requested = request_run(
            client,
            data["workspace"]["id"],
            data["collection"]["id"],
            data["source"]["id"],
            data["revision"]["id"],
            queue=FakeJobQueue(),
        )
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_now(client, run_id).status == "completed"
        ocr_calls = len(ocr_api.requests)

        review = client.get(_review_url(data, run_id)).json()
        saved = save(client, _review_url(data, run_id), edit_body(review, review["units"][0], "ĐÃ SỬA"))
        assert saved.status_code == 200, saved.text
        version = saved.json()

        queue = FakeJobQueue()
        created = create_intent(
            client, data, key="prep-reuse", ocr_run_id=run_id, text_version=1, queue=queue
        )
        assert created.status_code == 201, created.text
        intent = created.json()["intent"]
        assert intent["text_version"] == 1
        assert intent["text_version_id"] == version["version_id"]
        assert intent["text_canonical_sha256"] == version["canonical_sha256"]

        assert advance(client, intent["id"], queue) == "compiling"
        assert count(client, OcrProcessingRun) == 1
        assert len(ocr_api.requests) == ocr_calls
        compilation_id = client.get(_status_url(data, intent["id"])).json()["compilation_run_id"]
        assert execute_compile(client, compilation_id) == "completed"
        assert advance(client, intent["id"], queue) == "ready"

        async def pinned_binding():
            async with AsyncSessionFactory() as db:
                return await db.scalar(
                    select(CompilationInput.text_version_id).where(
                        CompilationInput.run_id == compilation_id
                    )
                )

        assert client.portal.call(pinned_binding) == version["version_id"]


def test_text_version_must_be_saved_and_still_match(client):
    with FakeNemotron() as ocr_api:
        data = prepared_workspace(client, "prep-text", ocr_api)
        missing_run = create_intent(client, data, key="prep-text-a", text_version=1)
        assert missing_run.status_code == 422

        requested = request_run(
            client,
            data["workspace"]["id"],
            data["collection"]["id"],
            data["source"]["id"],
            data["revision"]["id"],
            queue=FakeJobQueue(),
        )
        run_id = requested.json()["run"]["id"]
        not_ready = create_intent(
            client, data, key="prep-text-b", ocr_run_id=run_id, text_version=1
        )
        assert not_ready.status_code == 409
        assert not_ready.json()["code"] == "preparation_text_version_not_ready"

        assert execute_now(client, run_id).status == "completed"
        absent = create_intent(client, data, key="prep-text-c", ocr_run_id=run_id, text_version=1)
        assert absent.status_code == 404
        assert absent.json()["code"] == "preparation_text_version_not_found"

        review = client.get(_review_url(data, run_id)).json()
        saved = save(
            client, _review_url(data, run_id), edit_body(review, review["units"][0], "ĐÃ SỬA")
        )
        assert saved.status_code == 200, saved.text
        queue = FakeJobQueue()
        created = create_intent(
            client, data, key="prep-text-d", ocr_run_id=run_id, text_version=1, queue=queue
        )
        assert created.status_code == 201, created.text
        mutate(
            client,
            TextVersion,
            saved.json()["version_id"],
            canonical_sha256="f" * 64,
        )
        assert advance(client, created.json()["intent"]["id"], queue) == "failed"
        failed = client.get(_status_url(data, created.json()["intent"]["id"])).json()
        assert failed["error_code"] == "preparation_text_version_invalid"
        assert count(client, CompilationRun) == 0


def test_ai_mode_uses_modelops_and_requires_a_grant(client):
    with FakeNemotron() as ocr_api, FakeChat() as chat_api:
        data = prepared_workspace(client, "prep-ai", ocr_api)
        provider = chat_provider(client, data, chat_api.base_url)
        as_actor(PLATFORM)
        extra = client.post(
            f"{API}/modelops/providers",
            json={
                "name": "chat-not-granted",
                "provider_type": "openai_compatible",
                "base_url": chat_api.base_url,
                "model_name": "test-chat",
                "capabilities": ["chat"],
                "timeout_seconds": 5,
                "token_limits": {"context_window_tokens": 131072, "max_output_tokens": 8192},
            },
        )
        assert extra.status_code == 201, extra.text
        as_actor(EDITOR)
        denied = create_intent(
            client, data, key="prep-ai-denied", mode="ai", provider_id=extra.json()["id"]
        )
        assert denied.status_code == 404, denied.text
        assert denied.json()["code"] == "provider_not_found"
        mismatch = create_intent(
            client, data, key="prep-ai-ocr", mode="ai", provider_id=data["ocr_provider"]["id"]
        )
        assert mismatch.status_code == 409, mismatch.text
        assert mismatch.json()["code"] == "provider_capability_mismatch"

        queue = FakeJobQueue()
        created = create_intent(
            client, data, key="prep-ai", mode="ai", provider_id=provider["id"], queue=queue
        )
        assert created.status_code == 201, created.text
        intent_id = created.json()["intent"]["id"]
        assert advance(client, intent_id, queue) == "waiting_ocr"
        run_id = client.get(_status_url(data, intent_id)).json()["ocr_run_id"]
        assert execute_now(client, run_id).status == "completed"

        assert advance(client, intent_id, queue) == "compiling"
        compilation_id = client.get(_status_url(data, intent_id)).json()["compilation_run_id"]
        assert execute_compile(client, compilation_id) == "completed"
        assert advance(client, intent_id, queue) == "ready"
        assert len(chat_api.requests) == 1
        draft = client.get(
            f"{API}/workspaces/{data['workspace']['id']}/collections"
            f"/{data['collection']['id']}/compilation-runs/{compilation_id}/draft"
        )
        assert draft.status_code == 200, draft.text
        run = client.get(
            f"{API}/workspaces/{data['workspace']['id']}/collections"
            f"/{data['collection']['id']}/compilation-runs/{compilation_id}"
        )
        assert run.status_code == 200, run.text
        assert run.json()["ai_supplement"] is True
        assert run.json()["source_first"] is False


def test_outsider_cannot_read_or_cancel_an_intent(client):
    with FakeNemotron() as ocr_api:
        data = prepared_workspace(client, "prep-scope", ocr_api)
        intent_id = create_intent(client, data, key="prep-scope").json()["intent"]["id"]
        as_actor(OUTSIDER)
        assert client.get(_status_url(data, intent_id)).status_code == 404
        assert client.post(_status_url(data, intent_id) + "/cancel").status_code == 404
        listing = client.get(_intent_url(data))
        assert listing.status_code == 404
