"""User edits create immutable children only after scoped preview acceptance."""

import json
from datetime import timedelta

import pytest

from tests.integration.knowledge_support import MEMBER, OUTSIDER, as_actor
from tests.integration.workflow_support import (
    accept_edit,
    base_url,
    mutate,
    prepared,
    preview_edit,
    run_review,
)


def test_new_immutable_version_has_own_review_without_recompiling(client):
    with prepared(client) as (data, chat):
        assert run_review(client, data["run_id"]) == "completed"
        parent_review = client.get(base_url(data) + "/auto-review").json()["review_id"]
        original = client.get(base_url(data) + "/draft").content
        preview, body = preview_edit(client, data, review_id=parent_review)
        assert preview["before"] != preview["after"]
        response = accept_edit(client, data, preview)
        assert response.status_code == 201, response.text
        child = response.json()["run"]
        assert child["origin"] == "user_edit" and child["parent_run_id"] == data["run_id"]
        assert (
            child["status"] == "completed"
            and child["attempt_count"] == 0
            and child["usage_tokens"] is None
        )
        child_url = data["url"] + "/" + child["id"]
        draft = client.get(child_url + "/draft").json()
        assert draft["sections"] == body["content"]["sections"]
        assert draft["source_tables"] == json.loads(original)["source_tables"]
        assert client.get(child_url + "/raw").status_code == 404
        assert client.get(base_url(data) + "/draft").content == original
        replay = accept_edit(client, data, preview)
        assert replay.status_code == 200 and replay.json()["run"]["id"] == child["id"]
        assert len(chat.requests) == 2
        assert run_review(client, child["id"]) == "completed"
        assert len(chat.requests) == 3
        assert client.get(base_url(data) + "/auto-review").json()["review_id"] == parent_review
        child_review = client.get(child_url + "/auto-review").json()["review_id"]
        assert child_review != parent_review
        assert client.get(child_url + "/reviews/" + child_review + "/report").status_code == 200
        assert draft["publication_status"] == "draft" and draft["requires_review"]


@pytest.mark.parametrize("case", ["hash", "expired", "tampered", "stale_sibling", "actor"])
def test_accept_rejects_stale_or_unowned_preview(client, case):
    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.compilation.workflow.models import EditPreview

    with prepared(client) as (data, chat):
        preview, _ = preview_edit(client, data)
        if case == "hash":
            preview["preview_sha256"] = "0" * 64
        elif case == "expired":
            mutate(
                client,
                EditPreview,
                preview["preview_id"],
                expires_at=utcnow() - timedelta(seconds=1),
            )
        elif case == "tampered":
            mutate(client, EditPreview, preview["preview_id"], reason="Changed after preview")
        elif case == "stale_sibling":
            sibling, _ = preview_edit(client, data)
            assert accept_edit(client, data, sibling, "sibling").status_code == 201
        else:
            as_actor(MEMBER)
        response = accept_edit(client, data, preview)
        assert response.status_code in {403, 404, 409}, response.text
        assert len(chat.requests) == 1


def test_rejects_protected_tables_and_foreign_citation(client):
    with prepared(client) as (data, _):
        _, body = preview_edit(client, data)
        body["content"]["source_tables"] = []
        assert client.post(base_url(data) + "/edit-previews", json=body).status_code == 422
        del body["content"]["source_tables"]
        body["content"]["sections"][0]["paragraphs"][0]["citations"] = ["foreign:evidence"]
        response = client.post(base_url(data) + "/edit-previews", json=body)
        assert response.status_code == 422 and response.json()["code"] == "compilation_edit_invalid"


def test_workflow_scope_blocks_outsiders(client):
    with prepared(client) as (data, _):
        as_actor(OUTSIDER)
        for suffix in ("/edit-context", "/auto-review"):
            assert client.get(base_url(data) + suffix).status_code in {403, 404}


def test_storage_failure_exposes_no_partial_child_and_same_preview_can_retry(client, monkeypatch):
    from qnu.main import app

    with prepared(client) as (data, chat):
        preview, _ = preview_edit(client, data)
        blob = app.state.container.blob_store
        original_put = blob.put_bytes

        async def fail_markdown(key, payload, content_type):
            if "/markdown/" in key:
                raise OSError("simulated storage outage")
            return await original_put(key, payload, content_type)

        monkeypatch.setattr(blob, "put_bytes", fail_markdown)
        response = accept_edit(client, data, preview)
        assert response.status_code == 503 and response.json()["code"] == "storage_unavailable"
        assert len(client.get(data["url"]).json()) == 1
        monkeypatch.setattr(blob, "put_bytes", original_put)
        response = accept_edit(client, data, preview)
        assert response.status_code == 201, response.text
        assert len(client.get(data["url"]).json()) == 2 and len(chat.requests) == 1


def test_concurrent_accept_is_idempotent_and_different_preview_conflicts(client):
    from concurrent.futures import ThreadPoolExecutor

    with prepared(client) as (data, chat):
        preview, _ = preview_edit(client, data)
        other, _ = preview_edit(client, data)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: accept_edit(client, data, preview), range(2)))
        assert sorted(r.status_code for r in results) == [200, 201]
        assert results[0].json()["run"]["id"] == results[1].json()["run"]["id"]
        assert accept_edit(client, data, other).json()["code"] == "idempotency_conflict"
        assert len(client.get(data["url"]).json()) == 2 and len(chat.requests) == 1


def test_source_revision_changed_after_preview_blocks_accept(client):
    from tests.integration.knowledge_support import add_revision
    from tests.integration.ocr_support import real_pdf

    with prepared(client) as (data, chat):
        preview, _ = preview_edit(client, data)
        changed = add_revision(
            client,
            data["workspace"]["id"],
            data["collection"]["id"],
            data["source"]["id"],
            payload=real_pdf(["New source revision"]),
            staged=False,
        )
        assert changed.status_code == 201, changed.text
        response = accept_edit(client, data, preview)
        assert response.status_code == 409 and response.json()["code"] == "publication_source_stale"
        assert len(client.get(data["url"]).json()) == 1 and len(chat.requests) == 1
