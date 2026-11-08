# ruff: noqa: F811
"""Review handoff receipts and the state-derived inbox, through the real API."""

from datetime import timedelta

from sqlalchemy import func, select

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexSync
from qnu.domains.knowledge.preparation.models import PreparationIntent
from qnu.platform.database import AsyncSessionFactory
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    OUTSIDER,
    PLATFORM,
    REVIEWER,
    as_actor,
)
from tests.integration.test_publication_646 import (  # noqa: F401
    another_version,
    compiled,
    decision,
)


def review_url(data: dict) -> str:
    return (
        f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
        "/review-submissions"
    )


def inbox_url(data: dict) -> str:
    return f"{API}/workspaces/{data['workspace']['id']}/inbox"


def registered_doc(client, data: dict, *, key: str = "register-review"):
    response = client.post(
        data["base"],
        headers={"Idempotency-Key": key},
        json={
            "document_key": "chi-tieu",
            "title": "Chỉ tiêu",
            "compilation_run_id": data["run_id"],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    document, version = body["document"], body["version"]
    doc_url = data["base"] + "/" + document["id"]
    return document, version, doc_url, doc_url + "/versions/" + version["id"]


def preview(
    client,
    data: dict,
    document_id: str,
    version_id: str,
    *,
    action: str = "submit",
    submission_id: str | None = None,
    reason: str = "",
):
    body = {
        "document_id": document_id,
        "version_id": version_id,
        "action": action,
        "reason": reason,
    }
    if submission_id is not None:
        body["submission_id"] = submission_id
    return client.post(review_url(data) + "/previews", json=body)


def commit(client, data: dict, preview_body: dict, key: str):
    return client.post(
        review_url(data),
        headers={"Idempotency-Key": key},
        json={
            "preview_id": preview_body["id"],
            "preview_sha256": preview_body["preview_sha256"],
        },
    )


def inbox(client, data: dict, **params):
    return client.get(inbox_url(data), params=params)


def submit(client, data: dict, document_id: str, version_id: str, key: str = "submit-one"):
    created = preview(client, data, document_id, version_id)
    assert created.status_code == 200, created.text
    saved = commit(client, data, created.json(), key)
    assert saved.status_code == 200, saved.text
    return saved.json()["submission"]


def count_rows(client, model) -> int:
    async def _run():
        async with AsyncSessionFactory() as db:
            return await db.scalar(select(func.count()).select_from(model))

    return client.portal.call(_run)


def mutate(client, model, row_id, **values) -> None:
    async def _run():
        async with AsyncSessionFactory() as db:
            row = await db.get(model, row_id, populate_existing=True)
            for key, value in values.items():
                setattr(row, key, value)
            await db.commit()

    client.portal.call(_run)


def test_unsent_draft_is_not_queued_and_editor_submits_then_cancels(client, compiled):
    as_actor(EDITOR)
    document, version, _, _ = registered_doc(client, compiled)
    assert inbox(client, compiled).json()["items"] == []

    as_actor(REVIEWER)
    denied = preview(client, compiled, document["id"], version["id"])
    assert denied.status_code == 403, denied.text

    as_actor(EDITOR)
    submission = submit(client, compiled, document["id"], version["id"])
    assert submission["status"] == "pending" and submission["is_open"] is True
    assert submission["document_title"] == "Chỉ tiêu" and submission["version_no"] == 1

    duplicate = preview(client, compiled, document["id"], version["id"])
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "review_submission_duplicate"

    as_actor(REVIEWER)
    page = inbox(client, compiled).json()
    assert [item["kind"] for item in page["items"]] == ["review_pending"]
    item = page["items"][0]
    assert item["problem"] == "Chờ người duyệt"
    assert item["allowed_roles"] == ["admin", "reviewer"]
    assert item["submission_id"] == submission["id"]
    assert item["deep_path"].endswith(f"/documents/{document['id']}/versions/{version['id']}")
    detail = client.get(review_url(compiled) + "/" + submission["id"]).json()
    assert [action["action"] for action in detail["actions"]] == ["submit"]

    denied_cancel = preview(
        client,
        compiled,
        document["id"],
        version["id"],
        action="cancel",
        submission_id=submission["id"],
        reason="Thu hồi yêu cầu",
    )
    assert denied_cancel.status_code == 403, denied_cancel.text

    as_actor(EDITOR)
    cancel = preview(
        client,
        compiled,
        document["id"],
        version["id"],
        action="cancel",
        submission_id=submission["id"],
        reason="Rút để bổ sung số liệu",
    )
    assert cancel.status_code == 200, cancel.text
    cancelled = commit(client, compiled, cancel.json(), "cancel-one")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["submission"]["status"] == "cancelled"
    assert inbox(client, compiled).json()["items"] == []


def test_changes_request_needs_reason_and_new_version_supersedes_it(client, compiled):
    as_actor(EDITOR)
    document, version, doc_url, _ = registered_doc(client, compiled)
    submission = submit(client, compiled, document["id"], version["id"])

    as_actor(REVIEWER)
    short = preview(
        client,
        compiled,
        document["id"],
        version["id"],
        action="request_changes",
        submission_id=submission["id"],
        reason="sửa",
    )
    assert short.status_code == 422, short.text

    as_actor(EDITOR)
    wrong_role = preview(
        client,
        compiled,
        document["id"],
        version["id"],
        action="request_changes",
        submission_id=submission["id"],
        reason="Cần sửa số liệu",
    )
    assert wrong_role.status_code == 403, wrong_role.text

    as_actor(REVIEWER)
    changes = preview(
        client,
        compiled,
        document["id"],
        version["id"],
        action="request_changes",
        submission_id=submission["id"],
        reason="Cần sửa số liệu",
    )
    assert changes.status_code == 200, changes.text
    closed = commit(client, compiled, changes.json(), "request-changes")
    assert closed.status_code == 200, closed.text
    assert closed.json()["submission"]["status"] == "changes_requested"

    page = inbox(client, compiled).json()
    assert [item["kind"] for item in page["items"]] == ["changes_requested"]
    assert page["items"][0]["problem"] == "Đã yêu cầu sửa"
    assert page["items"][0]["detail"] == "Cần sửa số liệu"

    as_actor(EDITOR)
    retry = preview(client, compiled, document["id"], version["id"])
    assert retry.status_code == 409
    assert retry.json()["code"] == "review_submission_changes_required"

    _, second = another_version(client, compiled, doc_url, key="second")
    as_actor(EDITOR)
    submit(client, compiled, document["id"], second["id"], key="submit-second")

    old = client.get(review_url(compiled) + "/" + submission["id"]).json()
    assert old["status"] == "resolved"
    assert old["close_reason"] == "Đã có phiên bản mới gửi duyệt."
    assert [action["action"] for action in old["actions"]] == [
        "submit",
        "request_changes",
        "superseded",
    ]
    page = inbox(client, compiled).json()
    assert [item["kind"] for item in page["items"]] == ["review_pending"]
    assert page["items"][0]["version_id"] == second["id"]


def test_approval_closes_handoff_without_publishing(client, compiled):
    as_actor(EDITOR)
    document, version, doc_url, version_url = registered_doc(client, compiled)
    submission = submit(client, compiled, document["id"], version["id"])

    as_actor(REVIEWER)
    stale = preview(
        client,
        compiled,
        document["id"],
        version["id"],
        action="request_changes",
        submission_id=submission["id"],
        reason="Cần sửa trước khi duyệt",
    )
    assert stale.status_code == 200, stale.text
    approved = decision(client, version_url, "approve", key="approve-review")
    assert approved.status_code == 200, approved.text

    assert client.get(version_url).json()["status"] == "approved"
    assert client.get(doc_url + "/published").status_code == 404
    assert count_rows(client, IndexSync) == 0

    detail = client.get(review_url(compiled) + "/" + submission["id"]).json()
    assert detail["status"] == "resolved"
    assert detail["actions"][-1]["action"] == "approved"
    assert detail["actions"][-1]["publication_decision_id"] == approved.json()["id"]

    page = inbox(client, compiled).json()
    assert [item["kind"] for item in page["items"]] == ["awaiting_publish"]
    assert page["items"][0]["problem"] == "Chờ xuất bản"

    as_actor(PLATFORM)
    published = decision(client, version_url, "publish", key="publish-review")
    assert published.status_code == 200, published.text
    assert client.get(doc_url + "/published").status_code == 200
    assert inbox(client, compiled).json()["items"] == []

    as_actor(REVIEWER)
    late = commit(client, compiled, stale.json(), "late-changes")
    assert late.status_code == 409
    assert late.json()["code"] == "review_preview_stale"


def test_replay_preview_consumption_and_permission_revocation(client, compiled):
    as_actor(EDITOR)
    document, version, _, _ = registered_doc(client, compiled)
    created = preview(client, compiled, document["id"], version["id"])
    assert created.status_code == 200, created.text
    first = commit(client, compiled, created.json(), "same-key")
    assert first.status_code == 200, first.text
    replay = commit(client, compiled, created.json(), "same-key")
    assert replay.status_code == 200, replay.text
    assert replay.json()["created"] is False
    assert replay.json()["submission"]["id"] == first.json()["submission"]["id"]
    reused = commit(client, compiled, created.json(), "another-key")
    assert reused.status_code == 409
    assert reused.json()["code"] == "review_preview_consumed"

    as_actor(MEMBER)
    denied = preview(client, compiled, document["id"], version["id"])
    assert denied.status_code == 403, denied.text

    as_actor(REVIEWER)
    changes = preview(
        client,
        compiled,
        document["id"],
        version["id"],
        action="request_changes",
        submission_id=first.json()["submission"]["id"],
        reason="Cần sửa số liệu",
    )
    assert changes.status_code == 200, changes.text
    as_actor(EDITOR)
    stolen = commit(client, compiled, changes.json(), "stolen-preview")
    assert stolen.status_code == 404, stolen.text

    as_actor(PLATFORM)
    workspace = compiled["workspace"]["id"]
    members = client.get(f"{API}/workspaces/{workspace}/members").json()["items"]
    member_id = next(m["id"] for m in members if m["actor_ref"] == REVIEWER.actor_id)
    assert client.delete(f"{API}/workspaces/{workspace}/members/{member_id}").status_code == 200
    as_actor(REVIEWER)
    revoked = commit(client, compiled, changes.json(), "revoked-preview")
    assert revoked.status_code == 404, revoked.text


def test_inbox_is_scoped_filtered_and_paginated(client, compiled):
    as_actor(EDITOR)
    document, version, doc_url, _ = registered_doc(client, compiled)
    submit(client, compiled, document["id"], version["id"], key="submit-v1")
    _, second = another_version(client, compiled, doc_url, key="second")
    as_actor(EDITOR)
    submit(client, compiled, document["id"], second["id"], key="submit-v2")

    as_actor(MEMBER)
    first_page = inbox(client, compiled, page_size=1).json()
    assert first_page["meta"] == {"page": 1, "page_size": 1, "total": 2}
    assert first_page["counts"] == {"review_pending": 2}
    second_page = inbox(client, compiled, page_size=1, page=2).json()
    assert len(second_page["items"]) == 1
    assert first_page["items"][0]["id"] != second_page["items"][0]["id"]

    filtered = inbox(client, compiled, kind="changes_requested").json()
    assert filtered["items"] == [] and filtered["meta"]["total"] == 0
    scoped = inbox(client, compiled, collection_id=compiled["collection"]["id"]).json()
    assert scoped["meta"]["total"] == 2
    assert inbox(client, compiled, collection_id="missing").status_code == 404

    as_actor(OUTSIDER)
    assert inbox(client, compiled).status_code == 404


def test_inbox_sync_category_follows_current_state(client, compiled):
    as_actor(EDITOR)
    _, _, _, version_url = registered_doc(client, compiled)
    as_actor(PLATFORM)
    assert decision(client, version_url, "approve", key="approve-sync").status_code == 200
    assert decision(client, version_url, "publish", key="publish-sync").status_code == 200

    mutate(
        client,
        IndexSync,
        compiled["collection"]["id"],
        status="failed",
        error_code="embedding_timeout",
        updated_at=utcnow(),
    )
    page = inbox(client, compiled).json()
    assert [item["kind"] for item in page["items"]] == ["sync_incomplete"]
    item = page["items"][0]
    assert item["title"] == compiled["collection"]["name"]
    assert item["detail"] == "embedding_timeout"
    assert item["deep_path"].endswith("?tab=index")

    mutate(
        client,
        IndexSync,
        compiled["collection"]["id"],
        status="ready",
        error_code=None,
        updated_at=utcnow(),
    )
    assert inbox(client, compiled).json()["items"] == []


def test_preparation_failure_reports_only_the_latest_attempt(client):
    from tests.integration.ocr_support import FakeJobQueue, FakeNemotron
    from tests.integration.test_preparation_intents import (
        create_intent,
        prepared_workspace,
    )

    with FakeNemotron() as ocr_api:
        data = prepared_workspace(client, "inbox-preparation", ocr_api)
        queue = FakeJobQueue()
        first = create_intent(client, data, key="inbox-prep-1", queue=queue)
        assert first.status_code == 201, first.text
        second = create_intent(client, data, key="inbox-prep-2", queue=queue)
        assert second.status_code == 201, second.text
        now = utcnow()
        mutate(
            client,
            PreparationIntent,
            first.json()["intent"]["id"],
            status="failed",
            error_code="ocr_failed",
            finished_at=now,
            created_at=now - timedelta(minutes=1),
        )
        mutate(
            client,
            PreparationIntent,
            second.json()["intent"]["id"],
            status="ready",
            finished_at=now,
            created_at=now,
        )
        as_actor(EDITOR)
        assert inbox(client, data).json()["items"] == []

        mutate(
            client,
            PreparationIntent,
            second.json()["intent"]["id"],
            status="failed",
            error_code="model_timeout",
            finished_at=now + timedelta(seconds=1),
        )
        page = inbox(client, data).json()
        assert [item["kind"] for item in page["items"]] == ["preparation_failed"]
        item = page["items"][0]
        assert item["detail"] == "model_timeout"
        assert item["title"] == data["source"]["title"]
        assert item["source_id"] == data["source"]["id"]
