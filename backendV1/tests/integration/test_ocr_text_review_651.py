"""Text editing crosses the HTTP, authorization, persistence and blob boundaries."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.integration.compiler_support import FakeChat, chat_provider, processed_input
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor


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


@pytest.mark.parametrize("mode", ["foreign", "span", "number", "overlap", "http_error"])
def test_bad_suggestions_and_provider_errors_never_change_files_or_resend(client, mode):
    data = processed_input(client)
    url = review_url(data)
    current = client.get(url).json()
    with FakeSpeller() as model:
        model.mode = mode
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
                pending = accept(
                    client, data["workspace"], proposal, "purge-spelling-" + mode
                )
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
