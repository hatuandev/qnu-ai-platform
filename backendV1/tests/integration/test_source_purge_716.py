"""Opt-in isolated DB coverage; never executes against the application's data."""

import hashlib

import pytest

from tests.integration.index_support import published_input
from tests.integration.knowledge_support import API, PLATFORM, add_member, as_actor, upload_source
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.test_lifecycle_659 import accept, lifecycle, preview, setup_source


def test_published_input_cannot_be_purged_even_when_document_is_archived(client):
    data = published_input(client)
    as_actor(PLATFORM)
    archive = preview(
        client, data["workspace"], "document", data["compiled"]["document"]["id"], "archive"
    )
    assert accept(client, data["workspace"], archive).status_code == 200
    blocked = preview(client, data["workspace"], "source", data["source"]["id"], "delete")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "source_publication_in_use"


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
