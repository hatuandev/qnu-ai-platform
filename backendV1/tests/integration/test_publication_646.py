"""Publication lifecycle through real API, PostgreSQL and immutable Compiler artifacts."""

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeJobQueue, use_queue


@pytest.fixture
def compiled(client):
    data = processed_input(client, code="publication-input")
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        response = request_compile(client, data)
        assert response.status_code == 201, response.text
        data["run_id"] = response.json()["run"]["id"]
        assert execute_compile(client, data["run_id"]) == "completed"
        data["base"] = (
            f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
            "/compiled-documents"
        )
        yield data


def register(client, data, *, key="register-one", run_id=None):
    return client.post(
        data["base"],
        headers={"Idempotency-Key": key},
        json={
            "document_key": "chi-tieu",
            "title": "Chỉ tiêu",
            "compilation_run_id": run_id or data["run_id"],
        },
    )


def decision(client, url, action, *, key=None):
    from tests.integration.publication_review_support import acknowledgement

    body = {"action": action, "reason": "Đã xem bản và đối chiếu nguồn."}
    if action == "approve":
        body["review_ack"] = acknowledgement(client, url)
    preview = client.post(
        url + "/decision-preview",
        json=body,
    )
    assert preview.status_code == 200, preview.text
    p = preview.json()
    return client.post(
        url + "/decisions",
        headers={"Idempotency-Key": key or action},
        json={
            "preview_id": p["id"],
            "preview_sha256": p["preview_sha256"],
        },
    )


def test_register_approve_publish_withdraw_keeps_original_draft(client, compiled):
    data = compiled
    created = register(client, data)
    assert created.status_code == 201, created.text
    body = created.json()
    doc_url = data["base"] + "/" + body["document"]["id"]
    version = body["version"]
    assert version["provenance"]["provider"]["model_name"] == "test-chat"
    assert version["provenance"]["sources"][0]["identity"]["revision_id"] == data["revision"]["id"]
    version_url = doc_url + "/versions/" + version["id"]
    assert version["status"] == "draft"
    assert client.get(doc_url + "/published").status_code == 404
    as_actor(PLATFORM)
    assert (
        client.post(
            version_url + "/decision-preview", json={"action": "publish", "reason": "x"}
        ).status_code
        == 409
    )
    assert decision(client, version_url, "approve").status_code == 200
    assert decision(client, version_url, "publish").status_code == 200
    published = client.get(doc_url + "/published")
    assert published.status_code == 200, published.text
    assert published.json()["version"]["status"] == "published"
    assert published.json()["content"]["publication_status"] == "draft"
    assert published.json()["content"]["source_tables"]
    assert decision(client, version_url, "withdraw").status_code == 200
    assert client.get(doc_url + "/published").status_code == 404
    assert client.get(version_url + "/draft").status_code == 200
    history = client.get(doc_url + "/history").json()
    assert [d["action"] for d in history] == ["approve", "publish", "withdraw"]
    assert all(d["actor_ref"] == PLATFORM.actor_id for d in history)
    as_actor(EDITOR)
    replay = register(client, data)
    assert replay.status_code == 200
    assert replay.json()["version"]["id"] == version["id"]


def registered(client, data):
    response = register(client, data)
    assert response.status_code == 201, response.text
    body = response.json()
    doc_url = data["base"] + "/" + body["document"]["id"]
    return doc_url, doc_url + "/versions/" + body["version"]["id"], body


def preview(client, url, action):
    from tests.integration.publication_review_support import acknowledgement

    payload = {"action": action, "reason": "Xác nhận bản đã xem."}
    if action == "approve":
        payload["review_ack"] = acknowledgement(client, url)
    response = client.post(url + "/decision-preview", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    return {"preview_id": body["id"], "preview_sha256": body["preview_sha256"]}


def commit(client, url, body, key="decision-one"):
    return client.post(url + "/decisions", json=body, headers={"Idempotency-Key": key})


def another_version(client, data, doc_url, *, key="second"):
    as_actor(EDITOR)
    response = request_compile(client, data, key=key)
    assert response.status_code == 201, response.text
    run_id = response.json()["run"]["id"]
    assert execute_compile(client, run_id) == "completed"
    response = client.post(
        doc_url + "/versions",
        headers={"Idempotency-Key": "register-" + key},
        json={"compilation_run_id": run_id},
    )
    assert response.status_code == 201, response.text
    version = response.json()["version"]
    return doc_url + "/versions/" + version["id"], version


def test_replacement_is_atomic_and_keeps_both_versions(client, compiled):
    data = compiled
    doc, first_url, first = registered(client, data)
    as_actor(PLATFORM)
    assert decision(client, first_url, "approve").status_code == 200
    assert decision(client, first_url, "publish").status_code == 200
    second_url, second = another_version(client, data, doc)
    as_actor(PLATFORM)
    assert decision(client, second_url, "approve", key="approve-second").status_code == 200
    assert decision(client, second_url, "publish", key="publish-second").status_code == 200
    rows = client.get(doc + "/versions").json()
    assert [(v["version_no"], v["status"]) for v in rows] == [(2, "published"), (1, "superseded")]
    assert client.get(doc + "/published").json()["version"]["id"] == second["id"]
    assert client.get(first_url + "/draft").status_code == 200
    history = client.get(doc + "/history").json()
    assert history[-1]["after"]["superseded_version_id"] == first["version"]["id"]


def test_publication_roles_scope_and_preview_actor_are_enforced(client, compiled):
    from tests.integration.knowledge_support import MEMBER, OUTSIDER, REVIEWER

    doc, url, _ = registered(client, compiled)
    assert (
        client.post(
            url + "/decision-preview", json={"action": "approve", "reason": "x"}
        ).status_code
        == 403
    )
    as_actor(REVIEWER)
    approved_preview = preview(client, url, "approve")
    as_actor(EDITOR)
    assert commit(client, url, approved_preview).status_code == 404
    as_actor(REVIEWER)
    assert commit(client, url, approved_preview).status_code == 200
    assert (
        client.post(
            url + "/decision-preview", json={"action": "publish", "reason": "x"}
        ).status_code
        == 403
    )
    as_actor(PLATFORM)
    assert decision(client, url, "publish").status_code == 200
    as_actor(MEMBER)
    assert client.get(doc + "/published").status_code == 200
    assert (
        client.post(
            url + "/decision-preview", json={"action": "withdraw", "reason": "x"}
        ).status_code
        == 403
    )
    as_actor(OUTSIDER)
    assert client.get(doc + "/published").status_code == 404
    as_actor(None)
    assert client.get(doc + "/published").status_code == 401


def test_revoked_reviewer_cannot_commit_preview(client, compiled):
    from tests.integration.knowledge_support import REVIEWER

    _, url, _ = registered(client, compiled)
    as_actor(REVIEWER)
    body = preview(client, url, "approve")
    as_actor(PLATFORM)
    workspace = compiled["workspace"]["id"]
    members = client.get(f"{API}/workspaces/{workspace}/members").json()["items"]
    member_id = next(m["id"] for m in members if m["actor_ref"] == REVIEWER.actor_id)
    assert client.delete(f"{API}/workspaces/{workspace}/members/{member_id}").status_code == 200
    as_actor(REVIEWER)
    assert commit(client, url, body).status_code == 404


def test_preview_hash_expiry_and_idempotent_decision(client, compiled):
    from datetime import timedelta

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.publication.models import PublicationPreview
    from qnu.platform.database import AsyncSessionFactory

    doc, url, _ = registered(client, compiled)
    as_actor(PLATFORM)
    body = preview(client, url, "approve")
    assert commit(client, url, {**body, "preview_sha256": "0" * 64}).status_code == 409

    async def expire():
        async with AsyncSessionFactory() as db:
            row = await db.get(PublicationPreview, body["preview_id"])
            row.expires_at = utcnow() - timedelta(seconds=1)
            await db.commit()

    client.portal.call(expire)
    assert commit(client, url, body).json()["code"] == "publication_preview_expired"
    body = preview(client, url, "approve")
    first = commit(client, url, body)
    assert first.status_code == 200, first.text
    assert commit(client, url, body).json()["id"] == first.json()["id"]
    assert commit(client, url, body, key="new-key").status_code == 409
    assert len(client.get(doc + "/history").json()) == 1


def test_preview_stale_after_registering_new_version(client, compiled):
    doc, url, _ = registered(client, compiled)
    as_actor(PLATFORM)
    body = preview(client, url, "approve")
    another_version(client, compiled, doc)
    as_actor(PLATFORM)
    assert commit(client, url, body).json()["code"] == "publication_preview_stale"


def test_concurrent_publish_uses_one_preview_snapshot_once(client, compiled):
    from concurrent.futures import ThreadPoolExecutor

    doc, first_url, _ = registered(client, compiled)
    as_actor(PLATFORM)
    assert decision(client, first_url, "approve").status_code == 200
    second_url, _ = another_version(client, compiled, doc)
    as_actor(PLATFORM)
    assert decision(client, second_url, "approve", key="approve-second").status_code == 200
    bodies = [
        (first_url, preview(client, first_url, "publish"), "publish-first"),
        (second_url, preview(client, second_url, "publish"), "publish-second"),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda args: commit(client, *args), bodies))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert sum(v["status"] == "published" for v in client.get(doc + "/versions").json()) == 1


def test_changed_source_stops_serving_but_can_still_be_withdrawn(client, compiled):
    from tests.integration.knowledge_support import add_revision
    from tests.integration.ocr_support import real_pdf

    doc, url, _ = registered(client, compiled)
    as_actor(PLATFORM)
    assert decision(client, url, "approve").status_code == 200
    assert decision(client, url, "publish").status_code == 200
    as_actor(EDITOR)
    changed = add_revision(
        client,
        compiled["workspace"]["id"],
        compiled["collection"]["id"],
        compiled["source"]["id"],
        payload=real_pdf(["New source revision"]),
    )
    assert changed.status_code == 201, changed.text
    response = client.get(doc + "/published")
    assert response.status_code == 409
    assert response.json()["code"] == "publication_source_stale"
    assert client.get(url + "/draft").status_code == 200
    as_actor(PLATFORM)
    assert decision(client, url, "withdraw").status_code == 200
    assert client.get(doc + "/published").status_code == 404


def test_tampered_artifact_blocks_commit_without_state_change(client, compiled):
    from qnu.domains.knowledge.compilation.artifacts import artifact
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    doc, url, _ = registered(client, compiled)
    as_actor(PLATFORM)
    assert decision(client, url, "approve").status_code == 200
    body = preview(client, url, "publish")

    async def corrupt():
        async with AsyncSessionFactory() as db:
            row = await artifact(db, compiled["run_id"], "draft_json")
            await app.state.container.blob_store.put_bytes(row.blob_key, b"tampered")

    client.portal.call(corrupt)
    assert commit(client, url, body, key="publish").status_code == 503
    assert client.get(url).json()["status"] == "approved"
    assert len(client.get(doc + "/history").json()) == 1


def test_registration_checks_scope_and_does_not_accept_status_overrides(client, compiled):
    from tests.integration.knowledge_support import create_collection

    data = compiled
    bad = client.post(
        data["base"],
        headers={"Idempotency-Key": "override"},
        json={
            "document_key": "bad",
            "title": "Bad",
            "compilation_run_id": data["run_id"],
            "status": "published",
        },
    )
    assert bad.status_code == 422
    collection = create_collection(client, data["workspace"]["id"], "Other")
    wrong = {**data, "base": data["base"].replace(data["collection"]["id"], collection["id"])}
    assert register(client, wrong).status_code == 404
    assert client.get(wrong["base"]).json() == []
    created = register(client, data)
    assert created.status_code == 201
    assert register(client, data, key="different-key").status_code == 409


def test_new_source_between_preview_and_publish_requires_fresh_compile(client, compiled):
    from tests.integration.knowledge_support import add_revision
    from tests.integration.ocr_support import real_pdf

    _, url, _ = registered(client, compiled)
    as_actor(PLATFORM)
    assert decision(client, url, "approve").status_code == 200
    body = preview(client, url, "publish")
    as_actor(EDITOR)
    assert (
        add_revision(
            client,
            compiled["workspace"]["id"],
            compiled["collection"]["id"],
            compiled["source"]["id"],
            payload=real_pdf(["Version two"]),
        ).status_code
        == 201
    )
    as_actor(PLATFORM)
    response = commit(client, url, body, key="publish")
    assert response.status_code == 409
    assert response.json()["code"] == "publication_source_stale"


def test_status_flag_alone_is_not_approval(client, compiled):
    from qnu.domains.knowledge.publication.models import CompiledVersion
    from qnu.platform.database import AsyncSessionFactory

    _, url, body = registered(client, compiled)

    async def forge_flag():
        async with AsyncSessionFactory() as db:
            row = await db.get(CompiledVersion, body["version"]["id"])
            row.status = "approved"
            await db.commit()

    client.portal.call(forge_flag)
    as_actor(PLATFORM)
    response = client.post(url + "/decision-preview", json={"action": "publish", "reason": "x"})
    assert response.status_code == 409
    assert response.json()["code"] == "publication_approval_required"


def test_missing_source_blocks_publication_but_withdrawal_still_works(client, compiled):
    from qnu.domains.knowledge.models import KBSourceRevision
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    doc, url, _ = registered(client, compiled)
    as_actor(PLATFORM)
    assert decision(client, url, "approve").status_code == 200
    assert decision(client, url, "publish").status_code == 200

    async def remove_test_blob():
        async with AsyncSessionFactory() as db:
            row = await db.get(KBSourceRevision, compiled["revision"]["id"])
            await app.state.container.blob_store.delete(row.storage_key)

    client.portal.call(remove_test_blob)
    response = client.get(doc + "/published")
    assert response.status_code == 502
    assert response.json()["code"] == "blob_missing"
    assert decision(client, url, "withdraw").status_code == 200


def test_restore_previous_version_requires_new_approval_and_publication(client, compiled):
    doc, first, body = registered(client, compiled)
    as_actor(PLATFORM)
    assert decision(client, first, "approve").status_code == 200
    assert decision(client, first, "publish").status_code == 200
    second, _ = another_version(client, compiled, doc)
    as_actor(PLATFORM)
    assert decision(client, second, "approve", key="approve-second").status_code == 200
    assert decision(client, second, "publish", key="publish-second").status_code == 200
    assert (
        client.post(
            first + "/decision-preview", json={"action": "publish", "reason": "x"}
        ).status_code
        == 409
    )
    assert decision(client, first, "approve", key="restore-approve").status_code == 200
    assert decision(client, first, "publish", key="restore-publish").status_code == 200
    assert client.get(doc + "/published").json()["version"]["id"] == body["version"]["id"]
