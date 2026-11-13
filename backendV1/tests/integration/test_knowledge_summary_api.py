"""Summaries must expose exact lineage, bounded lists and truthful serving state."""

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    compiler_url,
    execute_compile,
)
from tests.integration.index_support import FakeEmbedding, execute_index
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    PLATFORM,
    add_member,
    as_actor,
    create_collection,
    create_workspace,
    upload_source,
    workspace_with_editor,
)
from tests.integration.ocr_support import (
    TABLE_RESPONSE,
    FakeJobQueue,
    FakeNemotron,
    execute_now,
    real_pdf,
    request_run,
    setup_ocr_provider,
)
from tests.integration.publication_review_support import acknowledgement


def collection_base(workspace_id: str, collection_id: str) -> str:
    return f"{API}/workspaces/{workspace_id}/collections/{collection_id}"


def source_summary_url(data, *, source=None, revision_id=None, **params):
    source = source or data["source_a"]
    url = collection_base(data["workspace"]["id"], data["collection"]["id"])
    url += f"/sources/{source['id']}/summary"
    query = {**({"revision_id": revision_id} if revision_id else {}), **params}
    return url, query


def document_summary_url(data, *, document_id=None, **params):
    document_id = document_id or data["compiled"]["document"]["id"]
    url = collection_base(data["workspace"]["id"], data["collection"]["id"])
    return url + f"/compiled-documents/{document_id}/summary", params


def upload_and_run(client, data, marker, *, queue):
    workspace_id = data["workspace"]["id"]
    collection_id = data["collection"]["id"]
    response = upload_source(
        client,
        workspace_id,
        collection_id,
        payload=real_pdf([marker]),
        filename=f"{marker}.pdf",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    requested = request_run(
        client,
        workspace_id,
        collection_id,
        body["source"]["id"],
        body["revision"]["id"],
        queue=queue,
    )
    assert requested.status_code == 201, requested.text
    run_id = requested.json()["run"]["id"]
    assert execute_now(client, run_id).status == "completed"
    return body["source"], body["revision"], run_id


def compile_runs(client, data, run_ids, *, key):
    return client.post(
        data["url"],
        headers={"Idempotency-Key": key},
        json={"topic": "Chỉ tiêu tuyển sinh", "ocr_run_ids": run_ids},
    )


def archive_source(client, workspace, source_id):
    as_actor(PLATFORM)
    preview = client.post(
        f"{API}/workspaces/{workspace['id']}/lifecycle/previews",
        json={
            "kind": "source",
            "resource_id": source_id,
            "action": "archive",
            "reason": "Synthetic summary lifecycle acceptance.",
        },
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    result = client.post(
        f"{API}/workspaces/{workspace['id']}/lifecycle/actions",
        json={"preview_id": body["id"], "preview_sha256": body["preview_sha256"]},
        headers={"Idempotency-Key": "summary-archive"},
    )
    assert result.status_code == 200, result.text


def embedding_provider(client, data, base_url, *, dimension=4):
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "summary-embedding",
            "provider_type": "openai_compatible",
            "base_url": base_url,
            "model_name": "test-embedding",
            "capabilities": ["embedding"],
            "embedding_dimension": dimension,
            "token_limits": {"max_input_tokens": 32768},
            "timeout_seconds": 5,
        },
    )
    assert response.status_code == 201, response.text
    provider = response.json()
    assert (
        client.post(
            f"{API}/modelops/providers/{provider['id']}/keys",
            json={"name": "test", "secret": "summary-embedding-secret"},
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"{API}/modelops/defaults",
            json={"embedding_provider_id": provider["id"]},
        ).status_code
        == 200
    )
    as_actor(EDITOR)
    return provider


def cleanup_vectors(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    async def run():
        async with AsyncSessionFactory() as db:
            names = list((await db.scalars(select(IndexRun.vector_collection))).all())
        for name in names:
            await app.state.container.vector_store.delete_collection(name)

    client.portal.call(run)


def publish(client, data):
    as_actor(PLATFORM)
    for action in ("approve", "publish"):
        payload = {"action": action, "reason": "Synthetic summary fixture review."}
        if action == "approve":
            payload["review_ack"] = acknowledgement(client, data["version_url"])
        preview = client.post(data["version_url"] + "/decision-preview", json=payload)
        assert preview.status_code == 200, preview.text
        body = preview.json()
        result = client.post(
            data["version_url"] + "/decisions",
            headers={"Idempotency-Key": "summary-" + action},
            json={"preview_id": body["id"], "preview_sha256": body["preview_sha256"]},
        )
        assert result.status_code == 200, result.text


@pytest.fixture
def composite(client):
    """Two sources, two compile runs, two versions, an extra later OCR run and a live index."""
    workspace = workspace_with_editor(client, "summary")
    as_actor(EDITOR)
    queue = FakeJobQueue()
    with FakeNemotron() as ocr:
        ocr.responses = [TABLE_RESPONSE]
        ocr_provider = setup_ocr_provider(client, workspace["id"], ocr.base_url)
        collection = create_collection(client, workspace["id"], "Summary")
        data = {
            "workspace": workspace,
            "collection": collection,
            "ocr_provider": ocr_provider,
            "queue": queue,
        }
        data["source_a"], data["revision_a"], run_a1 = upload_and_run(
            client, data, "source-a", queue=queue
        )
        data["source_b"], data["revision_b"], run_b1 = upload_and_run(
            client, data, "source-b", queue=queue
        )
        data["url"] = compiler_url(workspace["id"], collection["id"])
        with FakeChat() as chat:
            chat_provider(client, data, chat.base_url)
            as_actor(EDITOR)
            first = compile_runs(client, data, [run_a1, run_b1], key="summary-one")
            assert first.status_code == 201, first.text
            run1 = first.json()["run"]["id"]
            assert execute_compile(client, run1) == "completed"
            as_actor(EDITOR)
            second = compile_runs(client, data, [run_a1, run_b1], key="summary-two")
            assert second.status_code == 201, second.text
            run2 = second.json()["run"]["id"]
            assert execute_compile(client, run2) == "completed"
        base = collection_base(workspace["id"], collection["id"])
        registration = client.post(
            base + "/compiled-documents",
            headers={"Idempotency-Key": "summary-register"},
            json={
                "document_key": "summary-doc",
                "title": "Tổng hợp nguồn",
                "compilation_run_id": run1,
            },
        )
        assert registration.status_code == 201, registration.text
        data["compiled"] = registration.json()
        data["document_url"] = base + "/compiled-documents/" + data["compiled"]["document"]["id"]
        data["version_url"] = (
            data["document_url"] + "/versions/" + data["compiled"]["version"]["id"]
        )
        publish(client, data)
        as_actor(EDITOR)
        second_version = client.post(
            data["document_url"] + "/versions",
            headers={"Idempotency-Key": "summary-register-two"},
            json={"compilation_run_id": run2},
        )
        assert second_version.status_code == 201, second_version.text
        data["second_version"] = second_version.json()["version"]
        rerun = request_run(
            client,
            workspace["id"],
            collection["id"],
            data["source_a"]["id"],
            data["revision_a"]["id"],
            body={"force": True},
            queue=queue,
        )
        assert rerun.status_code == 201, rerun.text
        run_a2 = rerun.json()["run"]["id"]
        assert execute_now(client, run_a2).status == "completed"
        data.update(run1=run1, run2=run2, run_a1=run_a1, run_b1=run_b1, run_a2=run_a2)
        as_actor(PLATFORM)
        with FakeEmbedding() as embedding:
            embedding_provider(client, data, embedding.base_url)
            as_actor(EDITOR)
            created = client.post(
                base + "/indexing-runs",
                json={},
                headers={"Idempotency-Key": "summary-index"},
            )
            assert created.status_code == 201, created.text
            data["index_run"] = created.json()["run"]["id"]
            assert execute_index(client, data["index_run"]) == "completed"
    try:
        yield data
    finally:
        cleanup_vectors(client)


def test_source_summary_pins_exact_runs_and_serving_version(client, composite):
    as_actor(EDITOR)
    url, query = source_summary_url(composite)
    response = client.get(url, params=query)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_id"] == composite["source_a"]["id"]
    assert body["revision"]["id"] == composite["revision_a"]["id"]
    assert body["observed_at"]
    assert body["processing_runs"][0]["id"] == composite["run_a2"]
    assert body["processing_runs"][1]["id"] == composite["run_a1"]
    assert body["active_run_id"] is None
    assert not body["runs_truncated"] and not body["derivations_truncated"]
    assert body["capabilities"] == {
        "can_prepare": True,
        "can_register": True,
        "can_approve": False,
        "can_publish": False,
    }
    # The later OCR run ran after compilation; ordering alone must not make it the
    # run that feeds a compiled version.
    assert {item["ocr_run_id"] for item in body["derivations"]} == {composite["run_a1"]}
    assert {item["compilation_run_id"] for item in body["derivations"]} == {
        composite["run1"],
        composite["run2"],
    }
    serving = [item for item in body["derivations"] if item["is_serving"]]
    assert len(serving) == 1
    assert serving[0]["compilation_run_id"] == composite["run1"]
    assert serving[0]["version"]["version_id"] == composite["compiled"]["version"]["id"]
    assert serving[0]["readiness"]["status"] == "ready"
    assert serving[0]["version"]["status"] == "published"
    # Three distinct revisions, and the served ids come from the published one.
    assert body["serving"] == {
        "served_revision_no": 1,
        "preparing_revision_no": None,
        "published_revision_no": 1,
        "served_version_id": composite["compiled"]["version"]["id"],
        "served_document_id": composite["compiled"]["document"]["id"],
    }
    assert body["actions"] == {
        "can_stop": False,
        "can_withdraw": False,
        "can_update": True,
        "can_delete": False,
    }
    assert body["preparation"] is None

    # Platform admins get the withdraw/delete affordances without a membership row.
    as_actor(PLATFORM)
    privileged = client.get(url, params=query).json()
    assert privileged["actions"] == {
        "can_stop": False,
        "can_withdraw": True,
        "can_update": True,
        "can_delete": True,
    }
    as_actor(EDITOR)

    bounded = client.get(url, params={"runs_limit": 1, "derivations_limit": 1}).json()
    assert bounded["runs_truncated"] and len(bounded["processing_runs"]) == 1
    assert bounded["derivations_truncated"] and len(bounded["derivations"]) == 1


def test_default_revision_upload_stages_candidate_without_switching_serving(client, composite):
    as_actor(EDITOR)
    source_url = (
        collection_base(composite["workspace"]["id"], composite["collection"]["id"])
        + "/sources/"
        + composite["source_a"]["id"]
    )
    response = client.post(
        source_url + "/revisions",
        files={"file": ("candidate.pdf", real_pdf(["Candidate revision"]), "application/pdf")},
        # ``staged`` is omitted on purpose: the default must keep revision 1 serving.
        data={"auto_extract": "false"},
    )
    assert response.status_code == 201, response.text
    uploaded = response.json()
    assert uploaded["revision"]["revision_no"] == 2
    assert uploaded["source"]["revision_count"] == 2
    assert uploaded["source"]["current_revision_no"] == 2
    assert uploaded["source"]["serving_revision_no"] == 1

    url, query = source_summary_url(composite)
    body = client.get(url, params=query).json()
    assert body["latest_revision_no"] == 2
    assert body["serving_revision_no"] == 1
    assert body["revision"]["revision_no"] == 2
    assert body["serving"]["served_revision_no"] == 1
    assert body["serving"]["preparing_revision_no"] == 2
    assert body["serving"]["published_revision_no"] == 1
    assert body["serving"]["served_version_id"] == composite["compiled"]["version"]["id"]
    assert body["serving"]["served_document_id"] == composite["compiled"]["document"]["id"]
    assert body["actions"]["can_update"] is True
    published = client.get(composite["document_url"] + "/published").json()
    assert published["version"]["id"] == composite["compiled"]["version"]["id"]


def test_source_actions_lock_only_for_confirmed_pending_delete(client, composite):
    from datetime import timedelta

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.lifecycle.models import LifecycleAction
    from qnu.platform.database import AsyncSessionFactory

    as_actor(PLATFORM)
    preview = client.post(
        f"{API}/workspaces/{composite['workspace']['id']}/lifecycle/previews",
        json={
            "kind": "source",
            "resource_id": composite["source_a"]["id"],
            "action": "delete",
            "reason": "Synthetic deletion preview.",
        },
    )
    assert preview.status_code == 200, preview.text
    url, query = source_summary_url(composite)
    unconfirmed = client.get(url, params=query).json()
    # An unconfirmed preview never blocks editorial actions.
    assert unconfirmed["actions"] == {
        "can_stop": False,
        "can_withdraw": True,
        "can_update": True,
        "can_delete": True,
    }

    async def set_receipt(status):
        async with AsyncSessionFactory() as db:
            row = await db.get(
                LifecycleAction, "lca-summary-confirmed", populate_existing=True
            )
            if row is None:
                db.add(
                    LifecycleAction(
                        id="lca-summary-confirmed",
                        workspace_id=composite["workspace"]["id"],
                        actor_ref=PLATFORM.actor_id,
                        kind="source",
                        resource_id=composite["source_a"]["id"],
                        action="delete",
                        reason="Synthetic confirmed deletion.",
                        parameters={},
                        impact={},
                        state_sha256="0" * 64,
                        preview_sha256="0" * 64,
                        status=status,
                        expires_at=utcnow() + timedelta(minutes=5),
                        accepted_at=utcnow(),
                    )
                )
            else:
                row.status = status
            await db.commit()

    client.portal.call(set_receipt, "pending")
    locked = client.get(url, params=query).json()
    assert locked["actions"]["can_update"] is False
    assert locked["actions"]["can_delete"] is False
    assert locked["actions"]["can_withdraw"] is True
    assert locked["actions"]["can_stop"] is False

    client.portal.call(set_receipt, "completed")
    unlocked = client.get(url, params=query).json()
    assert unlocked["actions"]["can_update"] is True
    assert unlocked["actions"]["can_delete"] is True


def test_document_summary_lists_each_compiler_input_and_reused_readiness(client, composite):
    as_actor(EDITOR)
    url, query = document_summary_url(composite)
    response = client.get(url, params=query)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["document"]["id"] == composite["compiled"]["document"]["id"]
    assert body["published_version"]["id"] == composite["compiled"]["version"]["id"]
    assert body["published_decision_id"]
    assert body["prepared_version"]["id"] == composite["second_version"]["id"]
    assert body["served_version"]["id"] == composite["compiled"]["version"]["id"]
    assert body["readiness"]["status"] == "ready"
    assert body["readiness"]["index_run_id"] == composite["index_run"]
    assert body["serving_matches_published"] is True
    assert body["versions"]["meta"]["total"] == 2
    assert not body["capabilities"]["can_publish"]
    version = body["versions"]["items"][1]
    assert version["id"] == composite["compiled"]["version"]["id"]
    assert {item["source_id"] for item in version["origins"]} == {
        composite["source_a"]["id"],
        composite["source_b"]["id"],
    }
    assert {item["ocr_run_id"] for item in version["origins"]} == {
        composite["run_a1"],
        composite["run_b1"],
    }
    assert all(item["revision_id"] for item in version["origins"])
    assert all(item["sha256"] for item in version["origins"])


def test_document_summary_paginates_versions_on_the_server(client, composite):
    as_actor(EDITOR)
    url, _ = document_summary_url(composite)
    first = client.get(url, params={"page": 1, "page_size": 1})
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["versions"]["meta"]["total"] == 2
    assert [item["version_no"] for item in first_body["versions"]["items"]] == [2]
    second = client.get(url, params={"page": 2, "page_size": 1}).json()
    assert [item["version_no"] for item in second["versions"]["items"]] == [1]
    empty = client.get(url, params={"page": 3, "page_size": 1}).json()
    assert empty["versions"]["items"] == []


def test_summary_never_mutates_state(client, composite):
    as_actor(EDITOR)
    queue = composite["queue"]
    jobs_before = len(queue.jobs)
    runs_url = (
        collection_base(composite["workspace"]["id"], composite["collection"]["id"])
        + f"/sources/{composite['source_a']['id']}/revisions/{composite['revision_a']['id']}"
        "/processing-runs"
    )
    total_before = client.get(runs_url).json()["meta"]["total"]
    source_url, source_query = source_summary_url(composite)
    document_url, document_query = document_summary_url(composite)
    assert client.get(source_url, params=source_query).status_code == 200
    assert client.get(document_url, params=document_query).status_code == 200
    assert len(queue.jobs) == jobs_before
    assert client.get(runs_url).json()["meta"]["total"] == total_before


def test_published_document_without_index_is_not_reported_ready(client):
    from tests.integration.index_support import published_input

    data = published_input(client)
    as_actor(EDITOR)
    url, query = document_summary_url(data)
    response = client.get(url, params=query)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["published_version"]["id"] == data["compiled"]["version"]["id"]
    assert body["served_version"] is None
    assert body["prepared_version"] is None
    assert body["readiness"]["status"] == "not_indexed"
    assert body["serving_matches_published"] is False
    source_url, source_query = source_summary_url(data, source=data["source"])
    summary_body = client.get(source_url, params=source_query).json()
    # A publication pointer alone never claims that an active index is serving it.
    assert summary_body["serving"]["served_revision_no"] is None
    assert summary_body["serving"]["served_version_id"] is None
    assert summary_body["serving"]["served_document_id"] is None
    assert summary_body["serving"]["published_revision_no"] == 1
    assert summary_body["serving"]["preparing_revision_no"] == 1
    derivations = summary_body["derivations"]
    assert derivations and all(item["is_serving"] is False for item in derivations)


def test_failed_index_sync_never_reports_serving(client):
    from tests.integration.index_support import published_input

    data = published_input(client)
    with FakeEmbedding() as embedding:
        embedding_provider(client, data, embedding.base_url)
        as_actor(EDITOR)
        created = client.post(
            data["base"] + "/indexing-runs",
            json={},
            headers={"Idempotency-Key": "summary-failed-index"},
        )
        assert created.status_code == 201, created.text
        embedding.mode = "wrong_dimension"
        assert execute_index(client, created.json()["run"]["id"]) == "failed"
        as_actor(EDITOR)
        url, query = document_summary_url(data)
        body = client.get(url, params=query)
        assert body.status_code == 200, body.text
        payload = body.json()
        assert payload["published_version"]["id"] == data["compiled"]["version"]["id"]
        assert payload["readiness"]["status"] == "not_indexed"
        assert payload["serving_matches_published"] is False


def test_archived_source_disappears_from_origins_and_serving_is_not_claimed(client, composite):
    archive_source(client, composite["workspace"], composite["source_b"]["id"])
    as_actor(EDITOR)
    source_url, source_query = source_summary_url(composite, source=composite["source_b"])
    assert client.get(source_url, params=source_query).status_code == 404
    url, query = document_summary_url(composite)
    response = client.get(url, params=query)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["published_version"]["id"] == composite["compiled"]["version"]["id"]
    assert body["readiness"]["status"] == "unavailable"
    assert body["serving_matches_published"] is False
    origin_sources = {
        item["source_id"] for version in body["versions"]["items"] for item in version["origins"]
    }
    assert origin_sources == {composite["source_a"]["id"]}


def test_summary_requires_membership_on_every_read(client):
    workspace = create_workspace(client, "summary-revoke")
    membership = add_member(client, workspace["id"], MEMBER.actor_id, "member")
    add_member(client, workspace["id"], EDITOR.actor_id, "editor")
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Revoke")
    uploaded = upload_source(client, workspace["id"], collection["id"]).json()
    url = (
        collection_base(workspace["id"], collection["id"])
        + f"/sources/{uploaded['source']['id']}/summary"
    )
    as_actor(MEMBER)
    assert client.get(url).status_code == 200
    as_actor(PLATFORM)
    revoked = client.delete(f"{API}/workspaces/{workspace['id']}/members/{membership['id']}")
    assert revoked.status_code == 200, revoked.text
    as_actor(MEMBER)
    denied = client.get(url)
    assert denied.status_code == 404
    assert denied.json()["code"] == "workspace_not_found"


def test_summary_never_crosses_workspace_or_collection(client, composite):
    other = create_workspace(client, "summary-other")
    add_member(client, other["id"], EDITOR.actor_id, "editor")
    collection = create_collection(client, other["id"], "Other")
    as_actor(EDITOR)
    foreign_source = (
        collection_base(other["id"], collection["id"])
        + f"/sources/{composite['source_a']['id']}/summary"
    )
    assert client.get(foreign_source).status_code == 404
    foreign_document = (
        collection_base(other["id"], collection["id"])
        + f"/compiled-documents/{composite['compiled']['document']['id']}/summary"
    )
    assert client.get(foreign_document).status_code == 404
    mismatched = (
        collection_base(other["id"], composite["collection"]["id"])
        + f"/sources/{composite['source_a']['id']}/summary"
    )
    assert client.get(mismatched).status_code == 404
