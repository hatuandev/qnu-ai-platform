"""Text editing crosses the HTTP, authorization, persistence and blob boundaries."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.integration.compiler_support import FakeChat, chat_provider, processed_input
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, add_member, as_actor
from tests.integration.ocr_support import FakeJobQueue, use_queue


def review_url(data):
    return (
        f"/platform/v1alpha1/workspaces/{data['workspace']['id']}"
        f"/collections/{data['collection']['id']}/sources/{data['source']['id']}"
        f"/revisions/{data['revision']['id']}/processing-runs/{data['ocr_run_id']}/text-review"
    )


def test_readable_ocr_review(client):
    data = processed_input(client, code="text-review")
    response = client.get(review_url(data))
    assert response.status_code == 200, response.text
    document = response.json()
    assert document["version"] == 0
    assert any(unit["text"] == "PHỤ LỤC 01" for unit in document["units"])
    assert any(unit["kind"] == "table_cell" for unit in document["units"])


def edit_body(current, unit, after):
    return {
        "expected_version": current["version"],
        "expected_sha256": current["canonical_sha256"],
        "changes": [{"evidence_id": unit["evidence_id"], "before": unit["text"], "after": after}],
    }


def save(client, url, body, key="save-one"):
    return client.post(url, json=body, headers={"Idempotency-Key": key})


def test_save_updates_both_files_preserves_original_and_replays(client):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    original_json = client.get(url.removesuffix("/text-review") + "/document").content
    body = edit_body(current, current["units"][0], "Phụ lục đã được người dùng sửa")
    response = save(client, url, body)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["version"] == 1
    assert saved["units"][0]["text"] == body["changes"][0]["after"]
    assert saved["units"][0]["original_text"] == "PHỤ LỤC 01"
    assert (
        client.get(url + "/document").json()["pages"][0]["blocks"][0]["text"]
        == body["changes"][0]["after"]
    )
    assert body["changes"][0]["after"] in client.get(url + "/markdown").text
    assert client.get(url.removesuffix("/text-review") + "/document").content == original_json
    again = save(client, url, body)
    assert again.status_code == 200 and again.json()["version_id"] == saved["version_id"]
    assert client.get(url + "?version=0").json()["units"][0]["text"] == "PHỤ LỤC 01"
    assert (
        save(
            client, url, edit_body(saved, saved["units"][0], "Bản sửa thứ hai"), "save-two"
        ).status_code
        == 200
    )
    assert save(client, url, body).json()["version"] == 1
    assert client.get(url).json()["version"] == 2


def test_table_cell_save_keeps_structure_numbers_and_updates_projection(client):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    unit = next(u for u in current["units"] if u["text"] == "Chỉ tiêu tuyển sinh")
    old = client.get(url + "/document").json()
    response = save(client, url, edit_body(current, unit, "Chỉ tiêu tuyển sinh đại học"))
    assert response.status_code == 200, response.text
    changed = client.get(url + "/document").json()
    table = changed["pages"][0]["blocks"][1]["table"]
    before = old["pages"][0]["blocks"][1]["table"]
    before["rows"][1][1]["text"] = "Chỉ tiêu tuyển sinh đại học"
    assert table == before
    assert "Chỉ tiêu tuyển sinh đại học" in changed["pages"][0]["blocks"][1]["text"]
    assert ">0<" in client.get(url + "/markdown").text


def test_conflicts_do_not_overwrite_newer_edits(client):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    body = edit_body(current, current["units"][0], "Bản thứ nhất")
    assert save(client, url, body).status_code == 200
    assert save(client, url, body, "stale").json()["code"] == "ocr_text_version_conflict"
    body["changes"][0]["after"] = "Nội dung khác"
    assert save(client, url, body).json()["code"] == "idempotency_conflict"
    assert client.get(url).json()["units"][0]["text"] == "Bản thứ nhất"


@pytest.mark.parametrize("mode", ["foreign", "before", "empty", "duplicate", "extra"])
def test_invalid_edits_rejected(client, mode):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    body = edit_body(current, current["units"][0], "Bản sửa")
    if mode == "foreign":
        body["changes"][0]["evidence_id"] = "foreign:span"
    elif mode == "before":
        body["changes"][0]["before"] = "không phải đoạn hiện tại"
    elif mode == "empty":
        body["changes"][0]["after"] = " "
    elif mode == "duplicate":
        body["changes"] *= 2
    else:
        body["pages"] = []
    assert save(client, url, body).status_code in {409, 422}
    assert client.get(url).json()["version"] == 0


def test_members_cannot_save_or_call_model_and_other_workspace_cannot_read(client):
    from qnu.domains.identity.actor import AuthActor

    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/workspaces/{data['workspace']['id']}/members",
        json={"actor_ref": "reader-text", "display_name": "Reader", "role": "member"},
    )
    assert response.status_code == 201, response.text
    as_actor(AuthActor(username="reader-text", actor_id="reader-text", roles=[], permissions=[]))
    assert client.get(url).status_code == 200
    assert save(client, url, edit_body(current, current["units"][0], "Bản sửa")).status_code == 403
    as_actor(AuthActor(username="outsider", actor_id="outsider", roles=[], permissions=[]))
    assert client.get(url).status_code == 404
    as_actor(EDITOR)
    assert client.get(url.replace(data["source"]["id"], "unknown-source")).status_code == 404


def test_failed_second_file_does_not_make_partial_version_visible(client, monkeypatch):
    from qnu.main import app

    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    blob = app.state.container.blob_store
    original_put = blob.put_bytes

    async def fail_markdown(key, payload, content_type=None):
        if key.startswith("ocr-text/") and key.endswith(".md"):
            raise OSError("simulated storage failure")
        return await original_put(key, payload, content_type)

    monkeypatch.setattr(blob, "put_bytes", fail_markdown)
    response = save(client, url, edit_body(current, current["units"][0], "Bản sửa"))
    assert response.status_code == 502, response.text
    assert client.get(url).json()["version"] == 0
    assert "Bản sửa" not in client.get(url + "/markdown").text


class FakeSpeller(FakeChat):
    def _respond(self, index):
        incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        unit = incoming["units"][0]
        suggestion = {
            "evidence_id": unit["evidence_id"],
            "start": 0,
            "end": 3,
            "original": unit["text"][:3],
            "replacement": "Phụ",
            "reason": "Gợi ý kiểm tra chữ",
            "context_before": unit["text"],
            "context_after": "Phụ" + unit["text"][3:],
        }
        if self.mode == "foreign":
            suggestion["evidence_id"] = "not-in-document"
        elif self.mode == "span":
            suggestion["original"] = "không khớp"
        elif self.mode == "number":
            suggestion["replacement"] = "Phụ 2026"
        elif self.mode == "overlap":
            pass
        suggestions = [suggestion] * (2 if self.mode == "overlap" else 1)
        body = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({"suggestions": suggestions}),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
        }
        return (
            (503, b'{"error":"unavailable"}')
            if self.mode == "http_error"
            else (200, json.dumps(body).encode())
        )


def detect(client, data, current, key="check-one"):
    return client.post(
        review_url(data) + "/checks",
        headers={"Idempotency-Key": key},
        json={
            "expected_version": current["version"],
            "expected_sha256": current["canonical_sha256"],
            "evidence_ids": [current["units"][0]["evidence_id"]],
        },
    )


@pytest.mark.parametrize("first_error", ["output_limit", "quarantined_suggestion"])
def test_automatic_review_preserves_coverage_after_batch_error(client, monkeypatch, first_error):
    from qnu.domains.ocr.review import automatic
    from qnu.main import app
    from qnu.workers.tasks.ocr import spelling_check_job

    batch_size = 2 if first_error == "output_limit" else 1
    monkeypatch.setattr(automatic, "BATCH_SIZE", batch_size)
    data = processed_input(client, code="automatic-spelling-batches")
    url = review_url(data)
    original = client.get(url).json()
    expected = [unit["evidence_id"] for unit in original["units"]]
    poisoned = False

    class BatchSpeller(FakeChat):
        def _respond(self, index):
            nonlocal poisoned
            request = self.requests[index]["body"]["messages"][-1]["content"]
            units = json.loads(request)["units"]
            ids = [unit["evidence_id"] for unit in units]
            suggestions = []
            truncated = False
            if first_error == "output_limit":
                # Batches run concurrently: poison the batch that owns the first
                # unit, never whichever request happens to arrive first.
                if not poisoned and expected[0] in ids:
                    poisoned = truncated = len(units) > 1
            elif expected[1] in ids:
                unit = units[0]
                suggestions.append(
                    {
                        "evidence_id": unit["evidence_id"],
                        "start": 0,
                        "end": 1,
                        "original": unit["text"][0],
                        "replacement": "1234",
                        "reason": "Invalid numeric change",
                        "context_before": unit["text"],
                        "context_after": "1234" + unit["text"][1:],
                    }
                )
            payload = {
                "choices": [
                    {
                        "message": {"content": json.dumps({"suggestions": suggestions})},
                        "finish_reason": "length" if truncated else "stop",
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
            }
            return 200, json.dumps(payload).encode()

    with BatchSpeller() as model:
        chat_provider(client, data, model.base_url)
        context = {"container": app.state.container}
        assert client.portal.call(spelling_check_job, context, data["ocr_run_id"]) == "completed"
        checks = client.get(url + "/checks?version=0").json()
        assert len(checks) == 1
        (check,) = checks
        assert len(expected) > 2
        assert check["total_evidence_count"] == len(expected)
        assert check["status"] == "completed"
        if first_error == "output_limit":
            assert check["checked_evidence_ids"] == expected
            assert len(model.requests) == (len(expected) + 1) // 2 + 2
        else:
            assert check["error_code"] is None
            assert check["checked_evidence_ids"] == expected
            assert check["suggestions"] == []
            assert check["rejected_suggestions"] == [
                {"evidence_id": expected[1], "reason": "numeric_change", "start": 0, "end": 1}
            ]
            assert len(model.requests) == len(expected)
        sent = len(model.requests)
        assert client.portal.call(spelling_check_job, context, data["ocr_run_id"]) == "completed"
        assert len(model.requests) == sent
    assert client.get(url).json() == original


@pytest.mark.parametrize(
    ("switch_model", "missing_aggregate"), [(False, False), (False, True), (True, False)]
)
def test_automatic_retry_reuses_only_compatible_progress(
    client, monkeypatch, switch_model, missing_aggregate
):
    from qnu.domains.ocr.review import automatic
    from qnu.domains.ocr.review.models import SpellingRun
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from qnu.workers.tasks.ocr import spelling_check_job

    monkeypatch.setattr(automatic, "BATCH_SIZE", 1)
    data = processed_input(client, code="spelling-retry-progress")
    url = review_url(data)
    original = client.get(url).json()
    expected = [unit["evidence_id"] for unit in original["units"]]
    target = expected[0]

    async def lose_parent_aggregate(check_id):
        async with AsyncSessionFactory() as db:
            row = await db.get(SpellingRun, check_id)
            row.checked_evidence_ids = []
            row.suggestions = []
            await db.commit()

    class PartialSpeller(FakeSpeller):
        def _respond(self, index):
            request = self.requests[index]["body"]["messages"][-1]["content"]
            unit = json.loads(request)["units"][0]
            payload = {"suggestions": []}
            if unit["evidence_id"] == target:
                if not self.recover:
                    payload = {"unexpected": []}
            elif unit["evidence_id"] == expected[1]:
                text = unit["text"]
                payload["suggestions"].append(
                    {
                        "evidence_id": unit["evidence_id"],
                        "start": 0,
                        "end": 1,
                        "original": text[0],
                        "replacement": text[0].swapcase(),
                        "reason": "Kiểm tra chữ hoa thường",
                        "context_before": text,
                        "context_after": text[0].swapcase() + text[1:],
                    }
                )
            return 200, json.dumps(
                {
                    "choices": [
                        {
                            "message": {"content": json.dumps(payload)},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
                }
            ).encode()

    with PartialSpeller() as model:
        model.recover = False
        provider = chat_provider(client, data, model.base_url)
        context = {"container": app.state.container}
        assert client.portal.call(spelling_check_job, context, data["ocr_run_id"]) == "failed"
        (failed,) = client.get(url + "/checks?version=0").json()
        assert failed["checked_evidence_ids"] == expected[1:]
        assert len(failed["suggestions"]) == 1
        if missing_aggregate:
            client.portal.call(lose_parent_aggregate, failed["id"])
        (prior_snapshot,) = client.get(url + "/checks?version=0").json()
        previous_request_count = len(model.requests)
        model.recover = True
        if switch_model:
            as_actor(PLATFORM)
            updated = client.patch(
                f"{API}/modelops/providers/{provider['id']}",
                json={
                    "model_name": "other-chat",
                    "token_limits": {"context_window_tokens": 131072, "max_output_tokens": 8192},
                },
            )
            assert updated.status_code == 200, updated.text
            as_actor(EDITOR)
        assert (
            client.portal.call(spelling_check_job, context, data["ocr_run_id"], 0, True)
            == "completed"
        )
        retried, previous = client.get(url + "/checks?version=0").json()
        retried_ids = [
            json.loads(req["body"]["messages"][-1]["content"])["units"][0]["evidence_id"]
            for req in model.requests[previous_request_count:]
        ]
        assert sorted(retried_ids) == sorted(expected if switch_model else [target])
        assert retried["checked_evidence_ids"] == expected
        assert retried["suggestions"] == failed["suggestions"]
        assert previous == prior_snapshot
        assert (
            client.portal.call(spelling_check_job, context, data["ocr_run_id"], 0, True)
            == "completed"
        )
        assert len(model.requests) == previous_request_count + len(retried_ids)
    assert client.get(url).json() == original


def test_suggestions_are_exact_readable_and_only_applied_on_save(client):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        response = detect(client, data, current)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "completed" and len(result["suggestions"]) == 1
        assert client.get(url).json()["version"] == 0
        replay = detect(client, data, current)
        assert replay.json()["id"] == result["id"] and len(model.requests) == 1
        suggestion = result["suggestions"][0]
        unit = current["units"][0]
        after = (
            unit["text"][: suggestion["start"]]
            + suggestion["replacement"]
            + unit["text"][suggestion["end"] :]
        )
        assert save(client, url, edit_body(current, unit, after)).status_code == 200
        assert after in client.get(url + "/markdown").text
        assert client.get(url + "/checks/" + result["id"]).json()["usage_id"] == result["usage_id"]


@pytest.mark.parametrize(
    "mode,reason,kept",
    [
        ("foreign", "unknown_evidence", 0),
        ("span", "source_text_missing", 0),
        ("number", "numeric_change", 0),
        ("overlap", "overlap", 1),
    ],
)
def test_bad_suggestions_are_quarantined_without_changing_files_or_resend(
    client, mode, reason, kept
):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        model.mode = mode
        chat_provider(client, data, model.base_url)
        response = detect(client, data, current)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "completed"
        assert len(result["suggestions"]) == kept
        assert [item["reason"] for item in result["rejected_suggestions"]] == [reason]
        assert client.get(url).json()["version"] == 0
        replay = detect(client, data, current)
        assert replay.status_code == 200 and replay.json()["id"] == result["id"]
        assert len(model.requests) == 1


def test_provider_errors_never_change_files_or_resend(client):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        model.mode = "http_error"
        chat_provider(client, data, model.base_url)
        response = detect(client, data, current)
        assert response.status_code in {502, 503}, response.text
        assert client.get(url).json()["version"] == 0
        replay = detect(client, data, current)
        assert replay.status_code == 200 and replay.json()["status"] == "failed", replay.text
        assert len(model.requests) == 1


@pytest.mark.parametrize("change", ["text", "membership", "provider"])
def test_change_during_model_call_rejects_stale_or_unauthorized_suggestions(client, change):
    from sqlalchemy import select

    from qnu.domains.modelops.models import Provider
    from qnu.domains.workspaces.models import WorkspaceMember
    from qnu.platform.database import AsyncSessionFactory

    started, release = threading.Event(), threading.Event()

    class SlowSpeller(FakeSpeller):
        def _respond(self, index):
            started.set()
            assert release.wait(4)
            return super()._respond(index)

    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    with SlowSpeller() as model:
        provider = chat_provider(client, data, model.base_url)

        async def change_state():
            async with AsyncSessionFactory() as db:
                if change == "membership":
                    member = await db.scalar(
                        select(WorkspaceMember).where(
                            WorkspaceMember.workspace_id == data["workspace"]["id"],
                            WorkspaceMember.actor_ref == EDITOR.actor_id,
                        )
                    )
                    member.status = "revoked"
                else:
                    row = await db.get(Provider, provider["id"])
                    row.is_active = False
                await db.commit()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(detect, client, data, current)
            try:
                assert started.wait(4)
                if change == "text":
                    result = save(
                        client,
                        url,
                        edit_body(current, current["units"][0], "Bản sửa trong lúc kiểm tra"),
                    )
                    assert result.status_code == 200, result.text
                else:
                    client.portal.call(change_state)
            finally:
                release.set()
            response = future.result(timeout=10)
            assert response.status_code in {403, 404, 409, 503}, response.text
        assert len(model.requests) == 1


@pytest.mark.parametrize("mode", ["success", "http_error"])
def test_late_spelling_response_never_recreates_raw_evidence_after_purge(client, mode):
    from sqlalchemy import select

    from qnu.domains.lifecycle.purge import execute
    from qnu.domains.ocr.review.models import SpellingRun
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from tests.integration.knowledge_support import add_member
    from tests.integration.ocr_support import FakeJobQueue, use_queue
    from tests.integration.test_lifecycle_659 import accept, preview

    started, release = threading.Event(), threading.Event()

    class BlockedSpeller(FakeSpeller):
        def _respond(self, index):
            started.set()
            assert release.wait(8)
            return super()._respond(index)

    data = processed_input(client, code="spelling-late-" + mode)
    url = review_url(data)
    current = client.get(url).json()
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    with BlockedSpeller() as model:
        if mode == "http_error":
            model.mode = "http_error"
        chat_provider(client, data, model.base_url)
        use_queue(FakeJobQueue())

        async def newest_check():
            async with AsyncSessionFactory() as db:
                return await db.scalar(
                    select(SpellingRun.id)
                    .where(SpellingRun.workspace_id == data["workspace"]["id"])
                    .order_by(SpellingRun.created_at.desc())
                    .limit(1)
                )

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(detect, client, data, current)
            try:
                assert started.wait(8)
                check_id = client.portal.call(newest_check)
                assert check_id
                as_actor(PLATFORM)
                proposal = preview(
                    client, data["workspace"], "source", data["source"]["id"], "delete"
                )
                assert proposal.status_code == 200, proposal.text
                pending = accept(client, data["workspace"], proposal, "purge-spelling-" + mode)
                assert pending.status_code == 200, pending.text
                action_id = pending.json()["id"]

                async def worker():
                    async with AsyncSessionFactory() as db:
                        return await execute(
                            db,
                            app.state.container.blob_store,
                            app.state.container.vector_store,
                            action_id,
                        )

                assert client.portal.call(worker) == "completed"
            finally:
                release.set()
            late = future.result(timeout=15)
        assert late.status_code in {404, 409, 502, 503}, late.text

    key = f"ocr-spelling/{data['workspace']['id']}/{check_id}/raw-response"
    assert not client.portal.call(app.state.container.blob_store.exists, key)
    receipt = client.get(
        f"{API}/workspaces/{data['workspace']['id']}/lifecycle/actions/{action_id}"
    ).json()
    assert receipt["status"] == "completed"


def test_concurrent_saves_only_one_wins(client):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    with ThreadPoolExecutor(max_workers=2) as executor:
        calls = [
            executor.submit(
                save,
                client,
                url,
                edit_body(current, current["units"][0], f"Bản sửa {i}"),
                f"save-{i}",
            )
            for i in range(2)
        ]
        results = [call.result(timeout=10) for call in calls]
    assert sorted(r.status_code for r in results) == [200, 409]
    assert client.get(url).json()["version"] == 1


def rerun_url(data):
    return review_url(data) + "/checks/rerun"


def test_rerun_queues_unique_spelling_job_for_version(client):
    data = processed_input(client, code="spelling-rerun")
    queue = FakeJobQueue()
    use_queue(queue)
    response = client.post(rerun_url(data), json={"version": 0})
    assert response.status_code == 202, response.text
    assert response.json() == {"run_id": data["ocr_run_id"], "version": 0, "status": "queued"}
    assert queue.jobs == [
        {
            "function": "spelling_check_job",
            "args": (data["ocr_run_id"], 0, False),
            "job_id": f"qnu:v1:spelling:{data['ocr_run_id']}:0",
        }
    ]
    replay = client.post(rerun_url(data), json={"version": 0})
    assert replay.status_code == 202, replay.text
    assert len(queue.jobs) == 1


def test_rerun_completed_check_is_terminal(client):
    data = processed_input(client, code="spelling-rerun-completed")
    current = client.get(review_url(data)).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        assert detect(client, data, current).json()["status"] == "completed"
        queue = FakeJobQueue()
        use_queue(queue)
        for retry in (False, True):
            response = client.post(rerun_url(data), json={"version": 0, "retry": retry})
            assert response.status_code == 202, response.text
            assert response.json()["status"] == "completed"
        assert queue.jobs == []


def test_rerun_retries_failed_check_with_retry_job(client):
    data = processed_input(client, code="spelling-rerun-retry")
    current = client.get(review_url(data)).json()
    with FakeSpeller() as model:
        model.mode = "http_error"
        chat_provider(client, data, model.base_url)
        failed = detect(client, data, current)
        assert failed.status_code in {502, 503}, failed.text
        checks = client.get(review_url(data) + "/checks?version=0").json()
        assert [item["status"] for item in checks] == ["failed"]
        queue = FakeJobQueue()
        use_queue(queue)
        response = client.post(rerun_url(data), json={"version": 0, "retry": True})
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "queued"
        assert queue.jobs == [
            {
                "function": "spelling_check_job",
                "args": (data["ocr_run_id"], 0, True),
                "job_id": f"qnu:v1:spelling:{data['ocr_run_id']}:0:retry:{checks[0]['id']}",
            }
        ]
        replay = client.post(rerun_url(data), json={"version": 0, "retry": True})
        assert replay.status_code == 202, replay.text
        assert len(queue.jobs) == 1


def test_rerun_requires_write_role_and_existing_version(client):
    from qnu.domains.identity.actor import AuthActor

    data = processed_input(client, code="spelling-rerun-auth")
    queue = FakeJobQueue()
    use_queue(queue)
    missing = client.post(rerun_url(data), json={"version": 5})
    assert missing.status_code == 404, missing.text
    add_member(client, data["workspace"]["id"], "reader-rerun", "member")
    as_actor(AuthActor(username="reader-rerun", actor_id="reader-rerun", roles=[], permissions=[]))
    forbidden = client.post(rerun_url(data), json={"version": 0})
    assert forbidden.status_code == 403, forbidden.text
    assert queue.jobs == []


def test_rerun_reports_unavailable_queue(client):
    data = processed_input(client, code="spelling-rerun-queue")
    use_queue(None)
    unavailable = client.post(rerun_url(data), json={"version": 0})
    assert unavailable.status_code == 503, unavailable.text
    assert unavailable.json()["code"] == "spelling_queue_unavailable"
    use_queue(FakeJobQueue(failing=True))
    failed = client.post(rerun_url(data), json={"version": 0})
    assert failed.status_code == 503, failed.text
    assert failed.json()["code"] == "spelling_rerun_failed"


def disposition(client, data, check_id, suggestion, ignored=True):
    return client.post(
        review_url(data) + f"/checks/{check_id}/dispositions",
        json={
            "evidence_id": suggestion["evidence_id"],
            "start": suggestion["start"],
            "end": suggestion["end"],
            "ignored": ignored,
        },
    )


def test_ignored_suggestions_persist_per_check_without_touching_text(client):
    data = processed_input(client, code="spelling-dispositions")
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        check = detect(client, data, current).json()
    (suggestion,) = check["suggestions"]
    ignored = {
        "evidence_id": suggestion["evidence_id"],
        "start": suggestion["start"],
        "end": suggestion["end"],
    }
    response = disposition(client, data, check["id"], suggestion)
    assert response.status_code == 200, response.text
    assert response.json()["ignored_suggestions"] == [ignored]
    assert client.get(url + "/checks?version=0").json()[0]["ignored_suggestions"] == [ignored]
    assert client.get(url + "/checks/" + check["id"]).json()["ignored_suggestions"] == [ignored]
    assert disposition(client, data, check["id"], suggestion).status_code == 200
    assert client.get(url).json()["version"] == 0
    undone = disposition(client, data, check["id"], suggestion, ignored=False)
    assert undone.status_code == 200, undone.text
    assert undone.json()["ignored_suggestions"] == []
    assert client.get(url + "/checks/" + check["id"]).json()["ignored_suggestions"] == []


def test_disposition_rejects_unknown_spans_checks_and_unfinished_runs(client):
    from sqlalchemy import select

    from qnu.domains.ocr.review.models import SpellingRun
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client, code="spelling-dispositions-reject")
    other = processed_input(client, code="spelling-dispositions-other")
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        check = detect(client, data, current).json()
    (suggestion,) = check["suggestions"]
    wrong_span = {**suggestion, "end": suggestion["end"] + 1}
    missing = disposition(client, data, check["id"], wrong_span)
    assert missing.status_code == 404, missing.text
    assert missing.json()["code"] == "ocr_spelling_suggestion_not_found"
    cross = disposition(client, other, check["id"], suggestion)
    assert cross.status_code == 404, cross.text

    async def mark(mode):
        async with AsyncSessionFactory() as db:
            row = await db.scalar(select(SpellingRun).where(SpellingRun.id == check["id"]))
            if mode == "failed":
                row.status = "failed"
            else:
                row.trace = {**row.trace, "automatic_parent": "spl_parent"}
            await db.commit()

    client.portal.call(mark, "failed")
    not_ready = disposition(client, data, check["id"], suggestion)
    assert not_ready.status_code == 409, not_ready.text
    assert not_ready.json()["code"] == "ocr_spelling_check_not_ready"
    client.portal.call(mark, "child")
    hidden = disposition(client, data, check["id"], suggestion)
    assert hidden.status_code == 409, hidden.text
    assert hidden.json()["code"] == "ocr_spelling_check_not_reviewable"


def test_dispositions_require_write_role(client):
    from qnu.domains.identity.actor import AuthActor

    data = processed_input(client, code="spelling-dispositions-role")
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        check = detect(client, data, current).json()
    (suggestion,) = check["suggestions"]
    add_member(client, data["workspace"]["id"], "reader-ignore", "member")
    as_actor(
        AuthActor(username="reader-ignore", actor_id="reader-ignore", roles=[], permissions=[])
    )
    forbidden = disposition(client, data, check["id"], suggestion)
    assert forbidden.status_code == 403, forbidden.text
    as_actor(EDITOR)
    assert client.get(url + "/checks/" + check["id"]).json()["ignored_suggestions"] == []


def test_versions_report_saved_history_and_current_draft(client):
    data = processed_input(client, code="spelling-versions")
    url = review_url(data)
    versions_url = url + "/versions"
    assert client.get(versions_url).json() == [
        {
            "version": 0,
            "version_id": None,
            "saved_at": None,
            "change_count": 0,
            "is_current": True,
        }
    ]
    current = client.get(url).json()
    first = save(client, url, edit_body(current, current["units"][0], "Bản sửa một"), "v-one")
    assert first.status_code == 200, first.text
    saved = first.json()
    second = save(client, url, edit_body(saved, saved["units"][0], "Bản sửa hai"), "v-two")
    assert second.status_code == 200, second.text
    history = client.get(versions_url).json()
    assert [(row["version"], row["change_count"], row["is_current"]) for row in history] == [
        (2, 1, True),
        (1, 1, False),
        (0, 0, False),
    ]
    assert history[0]["version_id"] == second.json()["version_id"]
    assert history[1]["version_id"] == saved["version_id"]


def test_purge_source_with_disposition_completes(client):
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from tests.integration.test_lifecycle_659 import accept, preview

    data = processed_input(client, code="spelling-disposition-purge")
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        check = detect(client, data, current).json()
    (suggestion,) = check["suggestions"]
    assert disposition(client, data, check["id"], suggestion).status_code == 200
    reviewed = save(
        client, url, complete_body(current, [], check["id"]), "review-disposition-purge"
    )
    assert reviewed.status_code == 200, reviewed.text
    use_queue(FakeJobQueue())
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    proposal = preview(client, data["workspace"], "source", data["source"]["id"], "delete")
    assert proposal.status_code == 200, proposal.text
    pending = accept(client, data["workspace"], proposal, "purge-disposition")
    assert pending.status_code == 200, pending.text
    action_id = pending.json()["id"]

    async def worker():
        async with AsyncSessionFactory() as db:
            return await execute(
                db,
                app.state.container.blob_store,
                app.state.container.vector_store,
                action_id,
            )

    assert client.portal.call(worker) == "completed"
    assert client.get(url).status_code == 404


def test_concurrent_checks_share_one_durable_request_and_quota(client, monkeypatch):
    from qnu.domains.modelops.usage.service import usage_service

    data = processed_input(client)
    current = client.get(review_url(data)).json()
    reserved, release = threading.Event(), threading.Event()
    original_reserve = usage_service.reserve
    calls = 0

    async def pause_first_reserve(*args, **kwargs):
        nonlocal calls
        result = await original_reserve(*args, **kwargs)
        calls += 1
        if calls == 1:
            reserved.set()
            assert await asyncio.to_thread(release.wait, 4)
        return result

    monkeypatch.setattr(usage_service, "reserve", pause_first_reserve)
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(detect, client, data, current)
            try:
                assert reserved.wait(4)
                second = detect(client, data, current)
                assert second.status_code == 200, second.text
            finally:
                release.set()
            first_response = first.result(timeout=10)
        assert first_response.status_code == 200, first_response.text
        assert first_response.json()["id"] == second.json()["id"]
        assert len(model.requests) == 1
        assert calls == 1


def complete_body(current, changes, check_id):
    return {
        "expected_version": current["version"],
        "expected_sha256": current["canonical_sha256"],
        "changes": changes,
        "review_check_id": check_id,
    }


def apply_suggestion(unit, suggestion):
    return (
        unit["text"][: suggestion["start"]]
        + suggestion["replacement"]
        + unit["text"][suggestion["end"] :]
    )


def test_completing_review_records_approval_and_replays(client):
    data = processed_input(client, code="spelling-review-complete")
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        check = detect(client, data, current).json()
    (suggestion,) = check["suggestions"]
    unit = current["units"][0]
    changes = [
        {
            "evidence_id": unit["evidence_id"],
            "before": unit["text"],
            "after": apply_suggestion(unit, suggestion),
        }
    ]
    body = complete_body(current, changes, check["id"])
    response = save(client, url, body, "complete-one")
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["version"] == 1
    reviewed = client.get(url + "/checks/" + check["id"]).json()
    assert reviewed["reviewed_version"] == 1
    assert reviewed["reviewed_sha256"] == saved["canonical_sha256"]
    assert reviewed["reviewed_by"] == EDITOR.actor_id
    assert reviewed["reviewed_at"]
    assert client.get(url + "/checks?version=0").json()[0]["reviewed_version"] == 1
    replay = save(client, url, body, "complete-one")
    assert replay.status_code == 200
    assert replay.json()["version_id"] == saved["version_id"]
    assert client.get(url + "/versions").json()[0]["version"] == 1
    repeated = save(
        client,
        url,
        {
            **body,
            "expected_version": saved["version"],
            "expected_sha256": saved["canonical_sha256"],
        },
        "complete-two",
    )
    assert repeated.status_code == 409, repeated.text
    assert repeated.json()["code"] == "ocr_spelling_review_exists"


def test_completing_review_with_every_suggestion_ignored_keeps_text(client):
    data = processed_input(client, code="spelling-review-ignored")
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        check = detect(client, data, current).json()
    (suggestion,) = check["suggestions"]
    assert disposition(client, data, check["id"], suggestion).status_code == 200
    body = complete_body(current, [], check["id"])
    response = save(client, url, body, "complete-ignored")
    assert response.status_code == 200, response.text
    document = response.json()
    assert document["version"] == 0 and document["version_id"] is None
    reviewed = client.get(url + "/checks/" + check["id"]).json()
    assert reviewed["reviewed_version"] == 0
    assert reviewed["reviewed_sha256"] == current["canonical_sha256"]
    assert client.get(url + "/versions").json() == [
        {
            "version": 0,
            "version_id": None,
            "saved_at": None,
            "change_count": 0,
            "is_current": True,
        }
    ]
    replay = save(client, url, body, "complete-ignored")
    assert replay.status_code == 200
    assert replay.json()["canonical_sha256"] == current["canonical_sha256"]


def test_completing_review_requires_pending_suggestions_and_current_check(client):
    data = processed_input(client, code="spelling-review-pending")
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        check = detect(client, data, current).json()
    pending = save(client, url, complete_body(current, [], check["id"]), "complete-pending")
    assert pending.status_code == 409, pending.text
    assert pending.json()["code"] == "ocr_spelling_suggestions_pending"
    assert client.get(url).json()["version"] == 0
    saved = save(
        client,
        url,
        edit_body(current, current["units"][0], "Bản sửa trước khi duyệt"),
        "pre-review-save",
    )
    assert saved.status_code == 200, saved.text
    stale = save(client, url, complete_body(saved.json(), [], check["id"]), "complete-stale")
    assert stale.status_code == 409, stale.text
    assert stale.json()["code"] == "ocr_spelling_check_stale"


def test_completing_review_requires_each_span_in_the_same_unit(client):
    data = processed_input(client, code="spelling-review-two-spans")
    url = review_url(data)
    current = client.get(url).json()
    unit = current["units"][0]
    text = unit["text"]

    class TwoSpanSpeller(FakeSpeller):
        def _respond(self, index):
            suggestions = [
                {
                    "evidence_id": unit["evidence_id"],
                    "start": start,
                    "end": start + 1,
                    "original": text[start],
                    "replacement": text[start].swapcase(),
                    "reason": "Kiểm tra chữ hoa thường",
                    "context_before": text,
                    "context_after": text[:start] + text[start].swapcase() + text[start + 1 :],
                }
                for start in (0, 4)
            ]
            return 200, json.dumps(
                {
                    "choices": [
                        {
                            "message": {"content": json.dumps({"suggestions": suggestions})},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
                }
            ).encode()

    with TwoSpanSpeller() as model:
        chat_provider(client, data, model.base_url)
        detected = detect(client, data, current)
    assert detected.status_code == 200, detected.text
    check = detected.json()
    first, second = sorted(check["suggestions"], key=lambda item: item["start"])
    partial = edit_body(current, unit, apply_suggestion(unit, first))
    partial["review_check_id"] = check["id"]
    pending = save(client, url, partial, "complete-partial")
    assert pending.status_code == 409, pending.text
    assert pending.json()["code"] == "ocr_spelling_suggestions_pending"
    assert client.get(url).json()["version"] == 0

    partial["changes"][0]["spelling_edits"] = [
        {"start": first["start"], "end": first["end"], "replacement": "Ph"},
        {"start": second["start"], "end": second["end"], "replacement": "Lạ"},
    ]
    invalid = save(client, url, partial, "complete-mismatched-spans")
    assert invalid.status_code == 409, invalid.text
    assert invalid.json()["code"] == "ocr_spelling_edit_invalid"
    after = "Ph" + text[1:4] + "Lạ" + text[5:]
    partial["changes"][0]["after"] = after
    saved = save(client, url, partial, "complete-both")
    assert saved.status_code == 200, saved.text
    assert saved.json()["units"][0]["text"] == after
    assert client.get(url + "/checks/" + check["id"]).json()["reviewed_version"] == 1


def test_completing_review_rejects_foreign_or_unfinished_checks(client):
    from sqlalchemy import select

    from qnu.domains.ocr.review.models import SpellingRun
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client, code="spelling-review-invalid")
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        check = detect(client, data, current).json()

    missing = save(client, url, complete_body(current, [], "spl_missing"), "complete-missing")
    assert missing.status_code == 404, missing.text

    async def mark(mode):
        async with AsyncSessionFactory() as db:
            row = await db.scalar(select(SpellingRun).where(SpellingRun.id == check["id"]))
            if mode == "failed":
                row.status = "failed"
            else:
                row.trace = {**row.trace, "automatic_parent": "spl_parent"}
            await db.commit()

    client.portal.call(mark, "failed")
    not_ready = save(client, url, complete_body(current, [], check["id"]), "complete-not-ready")
    assert not_ready.status_code == 409, not_ready.text
    assert not_ready.json()["code"] == "ocr_spelling_check_not_ready"
    client.portal.call(mark, "child")
    hidden = save(client, url, complete_body(current, [], check["id"]), "complete-child")
    assert hidden.status_code == 409, hidden.text
    assert hidden.json()["code"] == "ocr_spelling_check_not_reviewable"


class TwoUnitSpeller(FakeChat):
    def _respond(self, index):
        incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        suggestions = []
        for unit in incoming["units"]:
            text = unit["text"]
            position = next(i for i, char in enumerate(text) if char.isalpha())
            original = text[position]
            replacement = original.lower() if original.isupper() else original.upper()
            suggestions.append(
                {
                    "evidence_id": unit["evidence_id"],
                    "start": position,
                    "end": position + 1,
                    "original": original,
                    "replacement": replacement,
                    "reason": "Gợi ý kiểm tra chữ",
                    "context_before": text,
                    "context_after": text[:position] + replacement + text[position + 1 :],
                }
            )
        body = {
            "choices": [
                {
                    "message": {"content": json.dumps({"suggestions": suggestions})},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
        }
        return 200, json.dumps(body).encode()


def test_bulk_ignore_persists_all_remaining_suggestions(client):
    data = processed_input(client, code="spelling-review-bulk")
    url = review_url(data)
    current = client.get(url).json()
    units = [unit for unit in current["units"] if any(char.isalpha() for char in unit["text"])][:2]
    assert len(units) == 2
    with TwoUnitSpeller() as model:
        chat_provider(client, data, model.base_url)
        response = client.post(
            url + "/checks",
            headers={"Idempotency-Key": "check-two"},
            json={
                "expected_version": current["version"],
                "expected_sha256": current["canonical_sha256"],
                "evidence_ids": [unit["evidence_id"] for unit in units],
            },
        )
        assert response.status_code == 200, response.text
        check = response.json()
    assert len(check["suggestions"]) == 2
    spans = [
        {"evidence_id": item["evidence_id"], "start": item["start"], "end": item["end"]}
        for item in check["suggestions"]
    ]
    unknown = client.post(
        url + f"/checks/{check['id']}/dispositions/bulk",
        json={"suggestions": [{**spans[0], "end": 99}]},
    )
    assert unknown.status_code == 404, unknown.text
    bulk = client.post(
        url + f"/checks/{check['id']}/dispositions/bulk", json={"suggestions": spans}
    )
    assert bulk.status_code == 200, bulk.text
    assert len(bulk.json()["ignored_suggestions"]) == 2
    done = save(client, url, complete_body(current, [], check["id"]), "complete-bulk")
    assert done.status_code == 200, done.text
    assert done.json()["version"] == 0
    assert client.get(url + "/checks/" + check["id"]).json()["reviewed_version"] == 0
