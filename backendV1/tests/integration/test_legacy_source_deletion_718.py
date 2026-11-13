"""Opt-in isolated DB coverage for soft-deleted uploads from older V1 versions."""

from tests.integration.knowledge_support import (
    API,
    EDITOR,
    OUTSIDER,
    PLATFORM,
    add_member,
    as_actor,
    upload_source,
)
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.test_lifecycle_659 import accept, lifecycle, preview, setup_source


def legacy_delete(client, workspace, source):
    from qnu.domains.lifecycle.models import ResourceState
    from qnu.platform.database import AsyncSessionFactory

    async def seed():
        async with AsyncSessionFactory() as db:
            db.add(
                ResourceState(
                    workspace_id=workspace["id"],
                    kind="source",
                    resource_id=source["id"],
                    status="deleted",
                )
            )
            await db.commit()

    client.portal.call(seed)


def legacy_list(client, workspace, collection):
    return client.get(
        lifecycle(workspace) + "/source-deletions/legacy",
        params={"collection_id": collection["id"]},
    )


def test_legacy_source_requires_confirmation_then_purge_releases_content_hash(client):
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    workspace, collection, source = setup_source(client)
    legacy_delete(client, workspace, source)
    as_actor(PLATFORM)
    response = legacy_list(client, workspace, collection)
    assert response.status_code == 200, response.text
    assert response.json()["items"] == [{"source_id": source["id"], "title": source["title"]}]
    duplicate = upload_source(client, workspace["id"], collection["id"])
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_content_deleted"

    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")
    use_queue(FakeJobQueue(failing=True))
    p = preview(client, workspace, "source", source["id"], "delete")
    assert p.status_code == 200, p.text
    # Preview itself does not hide the recovery candidate or release its checksum.
    assert legacy_list(client, workspace, collection).json()["total"] == 1
    accepted = accept(client, workspace, p)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "pending"
    assert legacy_list(client, workspace, collection).json()["total"] == 0
    assert (
        upload_source(client, workspace["id"], collection["id"]).json()["code"]
        == "source_purge_pending"
    )

    async def worker():
        async with AsyncSessionFactory() as db:
            return await execute(
                db,
                app.state.container.blob_store,
                app.state.container.vector_store,
                accepted.json()["id"],
            )

    assert client.portal.call(worker) == "completed"
    assert upload_source(client, workspace["id"], collection["id"]).status_code == 201


def test_legacy_inventory_requires_workspace_admin(client):
    workspace, collection, source = setup_source(client)
    legacy_delete(client, workspace, source)
    as_actor(EDITOR)
    assert legacy_list(client, workspace, collection).status_code == 403
    as_actor(OUTSIDER)
    assert legacy_list(client, workspace, collection).status_code == 404


def test_legacy_deleted_source_with_published_version_withdraws_on_confirmed_purge(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.publication.models import CompiledVersion
    from qnu.domains.lifecycle.purge import execute
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from tests.integration.index_support import published_input

    data = published_input(client)
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    legacy_delete(client, data["workspace"], data["source"])
    as_actor(PLATFORM)
    proposal = preview(client, data["workspace"], "source", data["source"]["id"], "delete")
    assert proposal.status_code == 200, proposal.text
    assert proposal.json()["impact"]["published_versions_to_withdraw"] == 1
    version_id = proposal.json()["impact"]["published_version_ids"][0]

    async def read_version_status():
        async with AsyncSessionFactory() as db:
            return await db.scalar(
                select(CompiledVersion.status).where(CompiledVersion.id == version_id)
            )

    assert client.portal.call(read_version_status) == "published"
    pending = accept(client, data["workspace"], proposal)
    assert pending.status_code == 200, pending.text
    assert pending.json()["status"] == "pending"
    # Confirmation withdraws every published version before background cleanup.
    assert client.portal.call(read_version_status) == "withdrawn"

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
