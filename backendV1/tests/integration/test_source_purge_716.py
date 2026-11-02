"""Opt-in isolated DB coverage; never executes against the application's data."""

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
