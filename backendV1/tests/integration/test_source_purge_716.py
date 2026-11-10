"""Opt-in isolated DB coverage; never executes against the application's data."""

import hashlib
import json
from datetime import timedelta

import pytest

from tests.integration.index_support import published_input
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    OUTSIDER,
    PLATFORM,
    REVIEWER,
    add_member,
    as_actor,
    create_workspace,
    upload_source,
)
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.test_lifecycle_659 import accept, lifecycle, preview, setup_source


def test_published_source_delete_withdraws_before_background_cleanup(client):
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = published_input(client)
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    published_url = data["document_url"] + "/published"
    assert client.get(published_url).status_code == 200
    proposal = preview(client, data["workspace"], "source", data["source"]["id"], "delete")
    assert proposal.status_code == 200, proposal.text
    assert proposal.json()["impact"]["published_versions_to_withdraw"] == 1
    assert proposal.json()["impact"]["published_version_ids"]
    pending = accept(client, data["workspace"], proposal)
    assert pending.status_code == 200, pending.text
    assert pending.json()["status"] == "pending"
    assert client.get(published_url).status_code == 404

    async def worker():
        async with AsyncSessionFactory() as db:
            return await execute(
                db,
                app.state.container.blob_store,
                app.state.container.vector_store,
                pending.json()["id"],
            )

    assert client.portal.call(worker) == "completed"
    assert accept(client, data["workspace"], proposal).json()["status"] == "completed"
    source_url = (
        f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
        f"/sources/{data['source']['id']}"
    )
    assert client.get(source_url).status_code == 404


def test_archived_document_source_can_be_purged(client):
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = published_input(client)
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    archive = preview(
        client, data["workspace"], "document", data["compiled"]["document"]["id"], "archive"
    )
    assert accept(client, data["workspace"], archive, "archive").status_code == 200
    proposal = preview(client, data["workspace"], "source", data["source"]["id"], "delete")
    assert proposal.status_code == 200, proposal.text
    assert proposal.json()["impact"]["published_versions_to_withdraw"] == 1
    pending = accept(client, data["workspace"], proposal, "purge")
    assert pending.status_code == 200, pending.text

    async def worker():
        async with AsyncSessionFactory() as db:
            return await execute(
                db,
                app.state.container.blob_store,
                app.state.container.vector_store,
                pending.json()["id"],
            )

    assert client.portal.call(worker) == "completed"
    assert accept(client, data["workspace"], proposal, "purge").json()["status"] == "completed"


def test_unpublished_purge_is_durable_irreversible_and_keeps_other_uploads(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.models import KBSourceRevision
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    workspace, collection, source = setup_source(client)

    async def original_keys():
        async with AsyncSessionFactory() as db:
            return list(
                (
                    await db.scalars(
                        select(KBSourceRevision.storage_key).where(
                            KBSourceRevision.source_id == source["id"]
                        )
                    )
                ).all()
            )

    keys = client.portal.call(original_keys)
    assert keys and all(
        client.portal.call(app.state.container.blob_store.exists, key) for key in keys
    )
    other = upload_source(
        client,
        workspace["id"],
        collection["id"],
        payload=b"%PDF-1.7\n% different synthetic input\n%%EOF\n",
    ).json()["source"]
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    use_queue(FakeJobQueue(failing=True))
    p = preview(client, workspace, "source", source["id"], "delete")
    assert p.status_code == 200, p.text
    assert p.json()["impact"]["restore_available"] is False
    pending = accept(client, workspace, p)
    assert pending.status_code == 200, pending.text
    assert pending.json()["status"] == "pending"
    assert "_purge_plan" not in pending.json()["result"]

    async def worker():
        async with AsyncSessionFactory() as db:
            return await execute(
                db,
                app.state.container.blob_store,
                app.state.container.vector_store,
                pending.json()["id"],
            )

    assert client.portal.call(worker) == "completed"
    assert all(not client.portal.call(app.state.container.blob_store.exists, key) for key in keys)
    prefix = f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources/"
    assert client.get(prefix + source["id"]).status_code == 404
    assert client.get(prefix + other["id"]).status_code == 200
    assert accept(client, workspace, p).json()["status"] == "completed"
    assert preview(client, workspace, "source", source["id"], "restore").status_code == 404
    pending = client.get(
        lifecycle(workspace) + "/source-deletions", params={"collection_id": collection["id"]}
    )
    assert pending.status_code == 200, pending.text
    assert pending.json() == []


@pytest.mark.parametrize("source_first", [False, True])
def test_compiled_source_purge_removes_output_and_segment_trees(client, source_first):
    from sqlalchemy import select

    from qnu.domains.knowledge.compilation.models import (
        CompilationRun,
        CompilationSegment,
        CompilationSegmentArtifact,
    )
    from qnu.domains.knowledge.compilation.outputs import store_output
    from qnu.domains.knowledge.compilation.review.models import (
        CompilationReview,
        CompilationReviewSegment,
        CompilationReviewSegmentArtifact,
    )
    from qnu.domains.lifecycle.purge import execute
    from qnu.domains.lifecycle.purge_graph import graph_for_source, graph_plan, selected, table
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from tests.integration.compiler_support import (
        chat_provider,
        execute_compile,
        processed_input,
        request_compile,
    )
    from tests.integration.test_compiler_segments_api_744 import CompatibilityChat

    data = processed_input(client, code="purge-compiled")
    workspace = data["workspace"]
    blob = app.state.container.blob_store
    with CompatibilityChat() as chat:
        chat_provider(client, data, chat.base_url)
        requested = request_compile(client, data, source_first=source_first)
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        review = client.post(
            data["url"] + f"/{run_id}/reviews",
            json={},
            headers={"Idempotency-Key": "purge-review"},
        )
        assert review.status_code == 200, review.text
        assert review.json()["status"] == "completed"
    draft = client.get(data["url"] + f"/{run_id}/draft")
    markdown = client.get(data["url"] + f"/{run_id}/markdown")
    assert draft.status_code == markdown.status_code == 200

    async def checkpoints():
        async with AsyncSessionFactory() as db:
            run = await db.get(CompilationRun, run_id)
            # Older partial output pairs are only referenced by the output table.
            partial = await store_output(
                db,
                blob,
                run,
                draft_payload=draft.content,
                markdown_payload=markdown.content,
                coverage={},
                partial=True,
            )
            expected_keys = {partial.draft_blob_key, partial.markdown_blob_key}
            review_row = await db.get(CompilationReview, review.json()["id"])
            for model, artifact, owner_field, owner in (
                (CompilationSegment, CompilationSegmentArtifact, "run_id", run),
                (
                    CompilationReviewSegment,
                    CompilationReviewSegmentArtifact,
                    "review_id",
                    review_row,
                ),
            ):
                # Two refinement levels exercise self-FKs independently of table order.
                parent = None
                for number in range(3):
                    part_id = f"purge-{owner_field}-{number}"
                    db.add(
                        model(
                            id=part_id,
                            **{owner_field: owner.id},
                            parent_segment_id=parent,
                            segment_index=100 + number,
                            status="failed" if number < 2 else "completed",
                            scope={},
                            input_sha256=owner.input_sha256,
                            prompt_version="synthetic-purge",
                            config={},
                            request_hash=owner.input_sha256,
                        )
                    )
                    await db.flush()
                    key = f"v1/workspaces/{workspace['id']}/purge-check/{part_id}"
                    expected_keys.add(key)
                    payload = part_id.encode()
                    await blob.put_bytes(key, payload, "application/octet-stream")
                    db.add(
                        artifact(
                            id=part_id + "-raw",
                            segment_id=part_id,
                            kind="raw_response",
                            blob_key=key,
                            sha256=hashlib.sha256(payload).hexdigest(),
                            size_bytes=len(payload),
                            content_type="application/octet-stream",
                        )
                    )
                    parent = part_id
            await db.commit()
            return expected_keys

    async def scope_plan():
        async with AsyncSessionFactory() as db:
            graph = await graph_for_source(db, workspace["id"], data["source"]["id"])
            return graph_plan(graph)

    expected_keys = client.portal.call(checkpoints)
    other = upload_source(
        client,
        workspace["id"],
        data["collection"]["id"],
        payload=b"%PDF-1.7\n% keep this unrelated source\n%%EOF\n",
    ).json()["source"]
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    use_queue(FakeJobQueue())
    proposal = preview(client, workspace, "source", data["source"]["id"], "delete")
    assert proposal.status_code == 200, proposal.text
    plan = client.portal.call(scope_plan)
    keys = plan["objects"]
    assert expected_keys <= keys.keys()
    assert all(client.portal.call(blob.exists, key) for key in keys)
    pending = accept(client, workspace, proposal)
    assert pending.status_code == 200, pending.text

    async def worker():
        async with AsyncSessionFactory() as db:
            assert (
                await execute(db, blob, app.state.container.vector_store, pending.json()["id"])
                == "completed"
            )
            for name, rows in plan["rows"].items():
                if rows:
                    target = table(name)
                    assert await db.scalar(select(1).where(selected(target, rows))) is None

    client.portal.call(worker)
    assert all(not client.portal.call(blob.exists, key) for key in keys)
    base = f"{API}/workspaces/{workspace['id']}/collections/{data['collection']['id']}"
    assert client.get(base + "/sources/" + data["source"]["id"]).status_code == 404
    assert client.get(base + "/sources/" + other["id"]).status_code == 200
    assert accept(client, workspace, proposal).json()["status"] == "completed"


def test_purge_resumes_on_the_same_receipt_after_lease_and_storage_failure(client, monkeypatch):
    from sqlalchemy import select

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.models import KBSourceRevision
    from qnu.domains.lifecycle.models import LifecycleAction
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from qnu.platform.errors import DependencyUnavailable

    workspace, _collection, source = setup_source(client)
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    use_queue(FakeJobQueue())
    blob = app.state.container.blob_store
    vectors = app.state.container.vector_store

    async def revision_keys():
        async with AsyncSessionFactory() as db:
            return list(
                (
                    await db.scalars(
                        select(KBSourceRevision.storage_key).where(
                            KBSourceRevision.source_id == source["id"]
                        )
                    )
                ).all()
            )

    keys = client.portal.call(revision_keys)
    assert keys and all(client.portal.call(blob.exists, key) for key in keys)

    proposal = preview(client, workspace, "source", source["id"], "delete")
    pending = accept(client, workspace, proposal, "purge-resume")
    assert pending.status_code == 200, pending.text
    action_id = pending.json()["id"]

    async def set_lease(value):
        async with AsyncSessionFactory() as db:
            row = await db.get(LifecycleAction, action_id)
            row.lease_expires_at = value
            await db.commit()

    async def worker():
        async with AsyncSessionFactory() as db:
            return await execute(db, blob, vectors, action_id)

    client.portal.call(set_lease, utcnow() + timedelta(seconds=60))
    assert client.portal.call(worker) == "not_claimed"
    assert all(client.portal.call(blob.exists, key) for key in keys)

    client.portal.call(set_lease, None)
    original_purge = blob.purge
    calls = {"count": 0}

    async def fail_once(key):
        calls["count"] += 1
        raise DependencyUnavailable("Synthetic storage outage.", code="storage_unavailable")

    monkeypatch.setattr(blob, "purge", fail_once)
    assert client.portal.call(worker) == "pending"
    assert calls["count"] == 1
    receipt = client.get(lifecycle(workspace) + "/actions/" + action_id).json()
    assert receipt["status"] == "pending"
    assert receipt["phase"] == "deleting_objects"
    assert receipt["progress"]["step"].startswith("Tạm dừng")
    assert receipt["progress"]["percent"] == 55
    assert receipt["error_code"] == "storage_unavailable"
    assert receipt["last_error_at"] is not None
    # A lease-fenced call is not an attempt; only claimed executions are counted.
    assert receipt["attempt_count"] == 1
    assert all(client.portal.call(blob.exists, key) for key in keys)

    monkeypatch.setattr(blob, "purge", original_purge)
    assert client.portal.call(worker) == "completed"
    assert all(not client.portal.call(blob.exists, key) for key in keys)
    finished = client.get(lifecycle(workspace) + "/actions/" + action_id).json()
    assert finished["status"] == "completed"
    assert finished["phase"] == "completed"
    assert finished["progress"]["percent"] == 100
    assert finished["attempt_count"] == 2


def test_revoked_confirmer_takeover_is_admin_only_and_audited(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.lifecycle.models import LifecycleAction
    from qnu.domains.lifecycle.purge import execute
    from qnu.domains.workspaces.models import WorkspaceEvent
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    workspace, collection, source = setup_source(client)
    members_url = f"{API}/workspaces/{workspace['id']}/members"

    def promote(actor_ref, role):
        as_actor(PLATFORM)
        rows = client.get(members_url).json()["items"]
        row = next(item for item in rows if item["actor_ref"] == actor_ref)
        response = client.patch(members_url + "/" + row["id"], json={"role": role})
        assert response.status_code == 200, response.text
        return response.json()

    # The confirmer is a workspace admin, not a platform admin, so revoking the
    # membership really removes their authority. A second admin keeps the team usable.
    confirmer = promote(MEMBER.actor_id, "admin")
    promote(REVIEWER.actor_id, "admin")

    as_actor(MEMBER)
    use_queue(FakeJobQueue())
    proposal = preview(client, workspace, "source", source["id"], "delete")
    pending = accept(client, workspace, proposal, "takeover-purge")
    assert pending.status_code == 200, pending.text
    action_id = pending.json()["id"]

    # One accepted preview can never become a second destructive intent.
    assert accept(client, workspace, proposal, "takeover-purge").json()["id"] == action_id
    duplicate = accept(client, workspace, proposal, "takeover-other")
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["code"] == "lifecycle_preview_stale"

    as_actor(EDITOR)
    assert client.get(lifecycle(workspace) + "/source-deletions/active").status_code == 403

    as_actor(PLATFORM)
    revoked = client.delete(members_url + "/" + confirmer["id"])
    assert revoked.status_code in (200, 204), revoked.text

    async def worker():
        async with AsyncSessionFactory() as db:
            return await execute(
                db, app.state.container.blob_store, app.state.container.vector_store, action_id
            )

    # The persisted confirmer lost authority; nothing is deleted and the receipt stays.
    assert client.portal.call(worker) == "pending"
    as_actor(REVIEWER)
    receipt = client.get(lifecycle(workspace) + "/actions/" + action_id).json()
    assert receipt["status"] == "pending"
    assert receipt["error_code"] == "workspace_not_found"
    assert receipt["confirmed_by"] == MEMBER.actor_id
    assert (
        client.get(
            f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
            f"/sources/{source['id']}"
        ).status_code
        == 404
    )

    active = client.get(lifecycle(workspace) + "/source-deletions/active")
    assert active.status_code == 200, active.text
    assert [row["id"] for row in active.json()] == [action_id]
    assert active.json()[0]["phase"] and active.json()[0]["progress"]["step"]

    async def set_lease(value):
        async with AsyncSessionFactory() as db:
            row = await db.get(LifecycleAction, action_id)
            row.lease_expires_at = value
            await db.commit()

    client.portal.call(set_lease, utcnow() + timedelta(seconds=60))
    busy = client.post(lifecycle(workspace) + f"/actions/{action_id}/takeover")
    assert busy.status_code == 409, busy.text
    assert busy.json()["code"] == "purge_lease_active"

    client.portal.call(set_lease, None)
    takeover = client.post(lifecycle(workspace) + f"/actions/{action_id}/takeover")
    assert takeover.status_code == 200, takeover.text
    assert takeover.json()["confirmed_by"] == MEMBER.actor_id
    assert takeover.json()["takeover_by"] == REVIEWER.actor_id
    assert takeover.json()["takeover_at"] is not None

    # An admin of another workspace still cannot see or resume this receipt.
    other_workspace = create_workspace(client, "purge-other")
    add_member(client, other_workspace["id"], OUTSIDER.actor_id, "admin")
    as_actor(OUTSIDER)
    assert client.get(lifecycle(workspace) + "/source-deletions/active").status_code == 404
    assert client.post(lifecycle(workspace) + f"/actions/{action_id}/takeover").status_code == 404
    assert client.get(lifecycle(workspace) + "/actions/" + action_id).status_code == 404

    as_actor(REVIEWER)
    assert client.portal.call(worker) == "completed"
    final = client.get(lifecycle(workspace) + "/actions/" + action_id).json()
    assert final["status"] == "completed"
    assert final["confirmed_by"] == MEMBER.actor_id
    assert final["takeover_by"] == REVIEWER.actor_id

    async def audit():
        async with AsyncSessionFactory() as db:
            rows = list(
                (
                    await db.scalars(
                        select(WorkspaceEvent).where(
                            WorkspaceEvent.workspace_id == workspace["id"],
                            WorkspaceEvent.action.in_(("source.purge_takeover", "source.purged")),
                        )
                    )
                ).all()
            )
            return [
                (row.action, row.detail.get("confirmed_by"), row.detail.get("takeover_by"))
                for row in rows
            ]

    events = client.portal.call(audit)
    expected = ("source.purged", MEMBER.actor_id, REVIEWER.actor_id)
    assert expected in events
    assert ("source.purge_takeover", MEMBER.actor_id, REVIEWER.actor_id) in events


def test_purge_waits_for_recorded_running_workers_and_releases_its_lease(client):
    from sqlalchemy import select, update

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.models import KBSourceRevision
    from qnu.domains.lifecycle.purge import execute
    from qnu.domains.ocr.models import OcrProcessingRun
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    workspace, collection, source = setup_source(client)
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    use_queue(FakeJobQueue())

    async def add_running_ocr():
        async with AsyncSessionFactory() as db:
            revision = await db.scalar(
                select(KBSourceRevision).where(KBSourceRevision.source_id == source["id"])
            )
            db.add(
                OcrProcessingRun(
                    id="ocr-purge-running",
                    workspace_id=workspace["id"],
                    collection_id=collection["id"],
                    source_id=source["id"],
                    revision_id=revision.id,
                    revision_no=revision.revision_no,
                    source_sha256=revision.sha256,
                    generation=1,
                    status="running",
                    config={},
                    config_fingerprint="0" * 64,
                    requested_by=EDITOR.actor_id,
                    worker_id="ocr-running-worker",
                    lease_expires_at=utcnow() + timedelta(seconds=90),
                )
            )
            await db.commit()

    client.portal.call(add_running_ocr)
    proposal = preview(client, workspace, "source", source["id"], "delete")
    assert proposal.status_code == 200, proposal.text
    pending = accept(client, workspace, proposal, "purge-running")
    assert pending.status_code == 200, pending.text
    body = pending.json()
    assert body["phase"] == "waiting_for_workers"
    checkpoint = body["result"]["checkpoint"]["jobs"]
    assert [(entry["table"], entry["id"]) for entry in checkpoint] == [
        ("ocr_processing_runs", "ocr-purge-running")
    ]
    assert checkpoint[0]["lease_expires_at"]

    async def worker():
        async with AsyncSessionFactory() as db:
            return await execute(
                db, app.state.container.blob_store, app.state.container.vector_store, body["id"]
            )

    # A deferral must release the purge lease so resumption/takeover stays possible.
    assert client.portal.call(worker) == "waiting_for_cancelled_work"
    waiting = client.get(lifecycle(workspace) + "/actions/" + body["id"]).json()
    assert waiting["status"] == "pending"
    assert waiting["lease_expires_at"] is None

    async def expire_worker_lease():
        async with AsyncSessionFactory() as db:
            await db.execute(
                update(OcrProcessingRun)
                .where(OcrProcessingRun.id == "ocr-purge-running")
                .values(lease_expires_at=utcnow() - timedelta(seconds=1))
            )
            await db.commit()

    client.portal.call(expire_worker_lease)
    assert client.portal.call(worker) == "completed"
    assert (
        client.get(lifecycle(workspace) + "/actions/" + body["id"]).json()["status"] == "completed"
    )


@pytest.mark.parametrize("failure", [False, True])
def test_takeover_fences_old_purge_worker_from_committing_or_clearing_lease(
    client, monkeypatch, failure
):
    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.lifecycle import purge
    from qnu.domains.lifecycle.models import LifecycleAction
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from qnu.platform.errors import DependencyUnavailable

    workspace, _collection, source = setup_source(client)
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    use_queue(FakeJobQueue())
    proposal = preview(client, workspace, "source", source["id"], "delete")
    pending = accept(client, workspace, proposal, "purge-takeover")
    assert pending.status_code == 200, pending.text
    action_id = pending.json()["id"]
    blob, vectors = app.state.container.blob_store, app.state.container.vector_store
    original_delete = purge._delete_objects

    async def replacement_claims_then_work(path_blob, plan, workspace_id):
        async with AsyncSessionFactory() as other:
            row = await other.get(
                LifecycleAction, action_id, populate_existing=True, with_for_update=True
            )
            row.takeover_by, row.takeover_at = PLATFORM.actor_id, utcnow()
            row.worker_id = "purge:replacement"
            row.lease_expires_at = utcnow() + timedelta(seconds=60)
            await other.commit()
        if failure:
            raise DependencyUnavailable("Synthetic worker lost.", code="storage_unavailable")
        await original_delete(path_blob, plan, workspace_id)

    monkeypatch.setattr(purge, "_delete_objects", replacement_claims_then_work)

    async def worker():
        async with AsyncSessionFactory() as db:
            return await purge.execute(db, blob, vectors, action_id)

    assert client.portal.call(worker) == ("pending" if failure else "not_claimed")

    async def lease_state():
        async with AsyncSessionFactory() as db:
            row = await db.get(LifecycleAction, action_id, populate_existing=True)
            return row.status, row.worker_id, row.error_code, row.lease_expires_at

    status, worker_id, error_code, lease = client.portal.call(lease_state)
    assert status == "pending"
    assert worker_id == "purge:replacement"
    assert error_code is None
    assert lease is not None and lease > utcnow()

    monkeypatch.setattr(purge, "_delete_objects", original_delete)

    async def release_replacement():
        async with AsyncSessionFactory() as db:
            row = await db.get(LifecycleAction, action_id, populate_existing=True)
            row.worker_id, row.lease_expires_at = None, None
            await db.commit()

    client.portal.call(release_replacement)
    assert client.portal.call(worker) == "completed"


@pytest.mark.parametrize("interruption", ["storage-outage", "claim-lost", "uncommitted-batch"])
def test_single_source_index_batch_files_are_removed_and_reseal_is_resumable(
    client, monkeypatch, interruption
):
    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.domains.lifecycle import purge
    from qnu.domains.lifecycle.models import LifecycleAction
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from qnu.platform.errors import DependencyUnavailable
    from tests.integration.index_support import FakeEmbedding, execute_index
    from tests.integration.test_index_api_647 import embedding_provider

    data = published_input(client)
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    blob = app.state.container.blob_store
    with FakeEmbedding() as fake:
        embedding_provider(client, data, fake.base_url)
        as_actor(EDITOR)
        created = client.post(
            data["base"] + "/indexing-runs",
            json={},
            headers={"Idempotency-Key": "purge-batch-single"},
        )
        assert created.status_code == 201, created.text
        run_id = created.json()["run"]["id"]
        orphaned = []
        if interruption == "uncommitted-batch":
            original_put = blob.put_bytes

            async def interrupt_after_put(key, payload, content_type=None):
                result = await original_put(key, payload, content_type)
                if "/index/" in key and "/batches/" in key:
                    orphaned.append(key)
                    raise OSError("Interrupted after storing raw embedding")
                return result

            with monkeypatch.context() as patch:
                patch.setattr(blob, "put_bytes", interrupt_after_put)
                assert execute_index(client, run_id) == "uncertain"
        else:
            assert execute_index(client, run_id) == "completed"

        async def batch_state():
            async with AsyncSessionFactory() as db:
                run = await db.get(IndexRun, run_id, populate_existing=True)
                return run.manifest_key, list(run.batch_receipts)

        manifest_key, receipts = client.portal.call(batch_state)
        if interruption == "uncommitted-batch":
            assert len(orphaned) == 1 and not receipts and manifest_key is None
        else:
            assert receipts and manifest_key
        raw_keys = orphaned or [receipt["raw_key"] for receipt in receipts]
        assert all(client.portal.call(blob.exists, key) for key in raw_keys)

        as_actor(PLATFORM)
        use_queue(FakeJobQueue())
        proposal = preview(client, data["workspace"], "source", data["source"]["id"], "delete")
        pending = accept(client, data["workspace"], proposal, "purge-batch-single")
        assert pending.status_code == 200, pending.text
        action_id = pending.json()["id"]

        async def worker():
            async with AsyncSessionFactory() as db:
                return await purge.execute(db, blob, app.state.container.vector_store, action_id)

        original_purge = blob.purge

        async def fail_batch_cleanup(key):
            if "/index/" in key and "/batches/" in key:
                raise DependencyUnavailable(
                    "Synthetic batch cleanup outage.", code="storage_unavailable"
                )
            return await original_purge(key)

        if interruption == "storage-outage":
            with monkeypatch.context() as patch:
                patch.setattr(blob, "purge", fail_batch_cleanup)
                assert client.portal.call(worker) == "pending"
            receipt = client.get(lifecycle(data["workspace"]) + "/actions/" + action_id).json()
            assert receipt["status"] == "pending"
            assert receipt["phase"] == "resealing"
            assert receipt["error_code"] == "storage_unavailable"
        elif interruption == "claim-lost":
            original_filter = purge._filtered_batch_receipts

            async def take_over(*args):
                async with AsyncSessionFactory() as other:
                    action = await other.get(LifecycleAction, action_id, with_for_update=True)
                    action.worker_id = "purge:replacement"
                    action.lease_expires_at = utcnow() + timedelta(minutes=1)
                    await other.commit()
                return await original_filter(*args)

            with monkeypatch.context() as patch:
                patch.setattr(purge, "_filtered_batch_receipts", take_over)
                assert client.portal.call(worker) == "not_claimed"
            assert client.portal.call(batch_state) == (manifest_key, receipts)
            assert all(client.portal.call(blob.exists, key) for key in raw_keys)

            async def release_replacement():
                async with AsyncSessionFactory() as other:
                    action = await other.get(LifecycleAction, action_id, with_for_update=True)
                    assert action.worker_id == "purge:replacement"
                    assert "_purge_cleanup" not in action.result
                    action.worker_id, action.lease_expires_at = None, None
                    await other.commit()

            client.portal.call(release_replacement)

        assert client.portal.call(worker) == "completed"

        async def final_state():
            async with AsyncSessionFactory() as db:
                run = await db.get(IndexRun, run_id, populate_existing=True)
                return list(run.batch_receipts)

        assert client.portal.call(final_state) == []
        assert all(not client.portal.call(blob.exists, key) for key in raw_keys)
        manifest = client.get(data["base"] + "/indexing-runs/" + run_id + "/manifest")
        if interruption == "uncommitted-batch":
            assert manifest.status_code == 409, manifest.text
            assert manifest.json()["code"] == "index_manifest_not_ready"
        else:
            assert manifest.status_code == 200, manifest.text
            sealed = manifest.json()
            assert sealed["inputs"] == [] and sealed["chunks"] == []
            assert sealed["batch_receipts"] == []
            assert sealed["purge"]["action_id"] == action_id
        assert (
            client.get(lifecycle(data["workspace"]) + "/actions/" + action_id).json()["status"]
            == "completed"
        )


def _shared_published_pair(client, ocr_api, chat_api, fake):
    """Serve two published documents from one collection-level index generation."""
    from tests.integration.compiler_support import execute_compile, request_compile
    from tests.integration.ocr_support import execute_now, real_pdf, request_run
    from tests.integration.test_index_api_647 import embedding_provider
    from tests.integration.test_publication_646 import decision
    from tests.integration.test_publication_index_sync_878 import sync_now

    data = published_input(client)
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    collection_base = data["base"]
    documents_base = collection_base + "/compiled-documents"

    as_actor(PLATFORM)
    providers = client.get(f"{API}/modelops/providers").json()
    ocr = next(
        row
        for row in providers
        if "ocr" in row["capabilities"]
        and row["name"].startswith("nemotron-")
        and row["id"] == data["ocr_provider"]["id"]
    )
    # Re-pointing an endpoint invalidates observed capacity; redeclare the same
    # operator limits in the same edit so the new synthetic endpoint is usable.
    patched = client.patch(
        f"{API}/modelops/providers/{ocr['id']}",
        json={"base_url": ocr_api.base_url, "token_limits": ocr["token_limits"]},
    )
    assert patched.status_code == 200, patched.text
    chat = next(
        row
        for row in providers
        if "chat" in row["capabilities"] and row["name"] == "chat-" + data["workspace"]["id"]
    )
    chat_patch = {"base_url": chat_api.base_url}
    if chat["token_limits"] is not None:
        chat_patch["token_limits"] = chat["token_limits"]
    patched = client.patch(f"{API}/modelops/providers/{chat['id']}", json=chat_patch)
    assert patched.status_code == 200, patched.text

    as_actor(EDITOR)
    second = upload_source(
        client,
        data["workspace"]["id"],
        data["collection"]["id"],
        payload=real_pdf(["PHỤ LỤC 02"]),
        filename="phu-luc-02.pdf",
    )
    assert second.status_code == 201, second.text
    second_body = second.json()
    ocr_request = request_run(
        client,
        data["workspace"]["id"],
        data["collection"]["id"],
        second_body["source"]["id"],
        second_body["revision"]["id"],
        queue=FakeJobQueue(),
    )
    assert ocr_request.status_code == 201, ocr_request.text
    ocr_run_id = ocr_request.json()["run"]["id"]
    assert execute_now(client, ocr_run_id).status == "completed"
    compiled = request_compile(
        client, {**data, "ocr_run_id": ocr_run_id}, key="shared-compile", source_first=True
    )
    assert compiled.status_code == 201, compiled.text
    compilation_id = compiled.json()["run"]["id"]
    assert execute_compile(client, compilation_id) == "completed"
    registered = client.post(
        documents_base,
        headers={"Idempotency-Key": "shared-register"},
        json={
            "document_key": "phu-luc-02",
            "title": "Phụ lục 02",
            "compilation_run_id": compilation_id,
        },
    )
    assert registered.status_code == 201, registered.text
    second_document = registered.json()["document"]
    second_version = registered.json()["version"]
    second_version_url = (
        documents_base + "/" + second_document["id"] + "/versions/" + second_version["id"]
    )
    as_actor(PLATFORM)
    assert decision(client, second_version_url, "approve", key="shared-approve").status_code == 200
    assert decision(client, second_version_url, "publish", key="shared-publish").status_code == 200

    as_actor(EDITOR)
    embedding_provider(client, data, fake.base_url)
    assert sync_now(client, data) == "building"
    runs = client.get(collection_base + "/indexing-runs").json()
    assert len(runs) == 1, runs
    return {
        "data": data,
        "second": second_body,
        "second_document": second_document,
        "second_version": second_version,
        "index_run_id": runs[0]["id"],
    }


def test_shared_index_generation_survives_purge_of_one_document(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.index.models import IndexChunk, IndexInput, IndexRun
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from tests.integration.compiler_support import FakeChat
    from tests.integration.index_support import FakeEmbedding, execute_index
    from tests.integration.ocr_support import FakeNemotron

    with FakeNemotron() as ocr_api, FakeChat() as chat_api, FakeEmbedding() as fake:
        fixture = _shared_published_pair(client, ocr_api, chat_api, fake)
        data = fixture["data"]
        body = fixture["second"]
        second_document = fixture["second_document"]
        second_version = fixture["second_version"]
        index_run_id = fixture["index_run_id"]
        collection_base = data["base"]
        documents_base = collection_base + "/compiled-documents"
        assert execute_index(client, index_run_id) == "completed"

        before_hits = client.post(
            collection_base + "/search", json={"query": "PHỤ LỤC", "top_k": 50}
        ).json()["hits"]
        assert {hit["version_id"] for hit in before_hits} == {
            data["compiled"]["version"]["id"],
            second_version["id"],
        }

        as_actor(PLATFORM)
        use_queue(FakeJobQueue())
        proposal = preview(client, data["workspace"], "source", data["source"]["id"], "delete")
        assert proposal.status_code == 200, proposal.text
        pending = accept(client, data["workspace"], proposal, "purge-shared")
        assert pending.status_code == 200, pending.text

        # Withdrawal reaches the read path before the background cleanup starts.
        as_actor(EDITOR)
        immediate = client.post(
            collection_base + "/search", json={"query": "PHỤ LỤC", "top_k": 50}
        ).json()["hits"]
        assert immediate and {hit["version_id"] for hit in immediate} == {second_version["id"]}

        async def worker():
            async with AsyncSessionFactory() as db:
                return await execute(
                    db,
                    app.state.container.blob_store,
                    app.state.container.vector_store,
                    pending.json()["id"],
                )

        as_actor(PLATFORM)
        assert client.portal.call(worker) == "completed"

        async def index_state():
            async with AsyncSessionFactory() as db:
                run = await db.get(IndexRun, index_run_id, populate_existing=True)
                inputs = list(
                    (await db.scalars(select(IndexInput).where(IndexInput.run_id == run.id))).all()
                )
                chunks = list(
                    (await db.scalars(select(IndexChunk).where(IndexChunk.run_id == run.id))).all()
                )
                return run, inputs, chunks

        run, inputs, chunks = client.portal.call(index_state)
        assert run.status == "completed" and run.is_active
        assert run.vectors_retired_at is None
        assert {row.version_id for row in inputs} == {second_version["id"]}
        assert chunks and run.chunks_total == len(chunks)
        assert all(chunk.vector is not None for chunk in chunks)

        async def vector_count():
            return await app.state.container.vector_store.count(run.vector_collection)

        assert client.portal.call(vector_count) == len(chunks)

        manifest = client.get(collection_base + "/indexing-runs/" + index_run_id + "/manifest")
        assert manifest.status_code == 200, manifest.text
        sealed = manifest.json()
        assert {row["version_id"] for row in sealed["inputs"]} == {second_version["id"]}
        assert {row["id"] for row in sealed["chunks"]} == {chunk.id for chunk in chunks}
        assert sealed["purge"]["action_id"] == pending.json()["id"]

        # The unrelated document keeps serving from the same active generation.
        after_hits = client.post(
            collection_base + "/search", json={"query": "PHỤ LỤC", "top_k": 50}
        ).json()["hits"]
        assert after_hits and {hit["version_id"] for hit in after_hits} == {second_version["id"]}
        assert client.get(collection_base + "/sources/" + body["source"]["id"]).status_code == 200
        assert (
            client.get(documents_base + "/" + second_document["id"] + "/published").status_code
            == 200
        )
        assert client.get(collection_base + "/sources/" + data["source"]["id"]).status_code == 404


@pytest.mark.parametrize("unsealed", [False, True], ids=["sealed", "unsealed-legacy"])
def test_shared_index_batch_files_keep_only_surviving_chunks(client, monkeypatch, unsealed):
    from sqlalchemy import select

    from qnu.domains.knowledge.index import execution
    from qnu.domains.knowledge.index.models import IndexChunk, IndexInput, IndexRun
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from qnu.platform.errors import DependencyUnavailable
    from tests.integration.compiler_support import FakeChat
    from tests.integration.index_support import FakeEmbedding, execute_index
    from tests.integration.ocr_support import FakeNemotron

    with FakeNemotron() as ocr_api, FakeChat() as chat_api, FakeEmbedding() as fake:
        fixture = _shared_published_pair(client, ocr_api, chat_api, fake)
        data = fixture["data"]
        second_version = fixture["second_version"]
        run_id = fixture["index_run_id"]
        collection_base = data["base"]
        blob = app.state.container.blob_store
        purged_version = data["compiled"]["version"]["id"]

        async def chunk_layout():
            async with AsyncSessionFactory() as db:
                rows = list(
                    (
                        await db.scalars(
                            select(IndexChunk)
                            .where(IndexChunk.run_id == run_id)
                            .order_by(IndexChunk.ordinal)
                        )
                    ).all()
                )
                bindings = dict(
                    (
                        await db.execute(
                            select(IndexInput.id, IndexInput.version_id).where(
                                IndexInput.run_id == run_id
                            )
                        )
                    ).all()
                )
                return [(chunk.id, bindings[chunk.input_id]) for chunk in rows]

        chunk_versions = client.portal.call(chunk_layout)
        assert {version for _, version in chunk_versions} == {
            purged_version,
            second_version["id"],
        }
        purged_ids = {chunk_id for chunk_id, version in chunk_versions if version == purged_version}
        assert 0 < len(purged_ids) < len(chunk_versions)
        # One batch must span both publications, so cleanup has to split it.
        size = len(purged_ids) + 1
        starts = list(range(0, len(chunk_versions), size))
        batches = [chunk_versions[start : start + size] for start in starts]

        async def resize_batch():
            async with AsyncSessionFactory() as db:
                run = await db.get(IndexRun, run_id)
                run.config = {**run.config, "embedding_batch_size": size}
                await db.commit()

        client.portal.call(resize_batch)
        if unsealed:

            async def fail_after_embedding(*args):
                raise DependencyUnavailable("Vector store unavailable", code="vector_unavailable")

            monkeypatch.setattr(execution, "_write_vectors", fail_after_embedding)
        assert execute_index(client, run_id) == ("queued" if unsealed else "completed")

        if unsealed:

            async def use_legacy_receipts():
                async with AsyncSessionFactory() as db:
                    run = await db.get(IndexRun, run_id)
                    assert run.manifest_key is None
                    run.batch_receipts = [
                        {key: value for key, value in receipt.items() if key != "chunk_ids"}
                        for receipt in run.batch_receipts
                    ]
                    await db.commit()

            client.portal.call(use_legacy_receipts)

        async def run_state():
            async with AsyncSessionFactory() as db:
                run = await db.get(IndexRun, run_id, populate_existing=True)
                chunks = {
                    chunk.id: chunk.vector
                    for chunk in (
                        await db.scalars(select(IndexChunk).where(IndexChunk.run_id == run_id))
                    ).all()
                }
                return list(run.batch_receipts), chunks

        receipts, vectors_before = client.portal.call(run_state)
        by_start = {receipt["start"]: receipt for receipt in receipts}
        assert sorted(by_start) == starts
        originals = {}
        for start, batch in zip(starts, batches, strict=True):
            originals[start] = by_start[start]["raw_key"]
            raw = json.loads(client.portal.call(blob.get_bytes, by_start[start]["raw_key"]))
            assert [entry["embedding"] for entry in raw["data"]] == [
                vectors_before[chunk_id] for chunk_id, _ in batch
            ]

        as_actor(PLATFORM)
        use_queue(FakeJobQueue())
        proposal = preview(client, data["workspace"], "source", data["source"]["id"], "delete")
        assert proposal.status_code == 200, proposal.text
        pending = accept(client, data["workspace"], proposal, "purge-shared-batches")
        assert pending.status_code == 200, pending.text
        action_id = pending.json()["id"]

        async def worker():
            async with AsyncSessionFactory() as db:
                return await execute(db, blob, app.state.container.vector_store, action_id)

        assert client.portal.call(worker) == "completed"

        receipts, vectors_after = client.portal.call(run_state)
        surviving = {chunk_id for chunk_id, _ in chunk_versions if chunk_id not in purged_ids}
        assert set(vectors_after) == surviving
        assert all(vectors_after[chunk_id] == vectors_before[chunk_id] for chunk_id in surviving)
        by_start = {receipt["start"]: receipt for receipt in receipts}
        seen = set()
        for start, batch in zip(starts, batches, strict=True):
            kept = [chunk_id for chunk_id, _ in batch if chunk_id not in purged_ids]
            if not kept:
                assert start not in by_start
                assert not client.portal.call(blob.exists, originals[start])
                continue
            receipt = by_start[start]
            assert receipt["chunk_ids"] == kept
            payload = client.portal.call(blob.get_bytes, receipt["raw_key"])
            assert hashlib.sha256(payload).hexdigest() == receipt["raw_sha256"]
            raw = json.loads(payload)
            assert [entry["index"] for entry in raw["data"]] == list(range(len(kept)))
            assert [entry["embedding"] for entry in raw["data"]] == [
                vectors_before[chunk_id] for chunk_id in kept
            ]
            if len(kept) == len(batch):
                assert receipt["raw_key"] == originals[start]
            else:
                # A split batch keeps surviving evidence under a new receipt.
                assert receipt["raw_key"] != originals[start]
                assert not client.portal.call(blob.exists, originals[start])
            seen.update(kept)
        assert seen == surviving
        assert sorted(by_start) == [
            start
            for start, batch in zip(starts, batches, strict=True)
            if any(chunk_id not in purged_ids for chunk_id, _ in batch)
        ]

        manifest = client.get(collection_base + "/indexing-runs/" + run_id + "/manifest")
        if unsealed:
            assert manifest.status_code == 409, manifest.text
            assert manifest.json()["code"] == "index_manifest_not_ready"
            return
        assert manifest.status_code == 200, manifest.text
        sealed = manifest.json()
        assert sealed["batch_receipts"] == receipts
        assert {chunk["id"] for chunk in sealed["chunks"]} == surviving
        assert {row["version_id"] for row in sealed["inputs"]} == {second_version["id"]}
        assert sealed["purge"]["action_id"] == action_id
        hits = client.post(
            collection_base + "/search", json={"query": "PHỤ LỤC", "top_k": 50}
        ).json()["hits"]
        assert hits and {hit["version_id"] for hit in hits} == {second_version["id"]}
