"""Reverse lifecycle uses the real HTTP/database boundary and synthetic evidence only."""

import pytest

from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    OUTSIDER,
    PLATFORM,
    REVIEWER,
    add_member,
    as_actor,
    create_collection,
    upload_source,
    workspace_with_editor,
)


def setup_source(client):
    workspace = workspace_with_editor(client, "lifecycle")
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Lifecycle")
    source = upload_source(client, workspace["id"], collection["id"]).json()["source"]
    return workspace, collection, source


def lifecycle(workspace):
    return f"{API}/workspaces/{workspace['id']}/lifecycle"


def promote_member(client, workspace_id, actor_ref, role="admin"):
    as_actor(PLATFORM)
    url = f"{API}/workspaces/{workspace_id}/members"
    rows = client.get(url).json()["items"]
    member = next(item for item in rows if item["actor_ref"] == actor_ref)
    response = client.patch(url + "/" + member["id"], json={"role": role})
    assert response.status_code == 200, response.text
    return response.json()


def preview(client, workspace, kind, resource_id, action, **extra):
    return client.post(
        lifecycle(workspace) + "/previews",
        json={
            "kind": kind,
            "resource_id": resource_id,
            "action": action,
            "reason": "Synthetic lifecycle acceptance.",
            **extra,
        },
    )


def accept(client, workspace, response, key="accept"):
    assert response.status_code == 200, response.text
    body = response.json()
    return client.post(
        lifecycle(workspace) + "/actions",
        json={"preview_id": body["id"], "preview_sha256": body["preview_sha256"]},
        headers={"Idempotency-Key": key},
    )


def test_archive_source_is_reversible_and_original_bytes_are_unchanged(client):
    workspace, collection, source = setup_source(client)
    url = f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources"
    content = client.get(url + f"/{source['id']}/revisions").json()[0]
    original_url = url + f"/{source['id']}/revisions/{content['id']}/content"
    original = client.get(original_url).content
    as_actor(PLATFORM)
    p = preview(client, workspace, "source", source["id"], "archive")
    result = accept(client, workspace, p)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "completed"
    assert client.get(url + "/" + source["id"]).status_code == 404
    assert not client.get(url).json()["items"]
    assert client.get(original_url).status_code == 404
    replay = accept(client, workspace, p)
    assert replay.json()["id"] == result.json()["id"]
    restored = accept(
        client, workspace, preview(client, workspace, "source", source["id"], "restore"), "restore"
    )
    assert restored.status_code == 200, restored.text
    assert client.get(original_url).content == original


def test_preview_is_bound_to_actor_and_state(client):
    workspace, _, source = setup_source(client)
    p = preview(client, workspace, "source", source["id"], "archive")
    assert p.status_code == 200, p.text
    as_actor(OUTSIDER)
    assert accept(client, workspace, p).status_code == 404
    as_actor(PLATFORM)
    assert accept(client, workspace, p).status_code == 404
    changed = preview(client, workspace, "source", source["id"], "delete")
    # Platform access cannot substitute for the persisted worker's workspace grant.
    denied = accept(client, workspace, changed, "delete")
    assert denied.status_code == 404, denied.text
    assert denied.json()["code"] == "workspace_not_found"
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")
    assert accept(client, workspace, changed, "delete").status_code == 200
    as_actor(EDITOR)
    stale = accept(client, workspace, p, "stale")
    assert stale.status_code == 409, stale.text


def test_member_cannot_mutate_lifecycle_and_trash_does_not_leak_other_owners(client):
    workspace, _, source = setup_source(client)
    as_actor(MEMBER)
    assert preview(client, workspace, "source", source["id"], "delete").status_code == 403
    as_actor(OUTSIDER)
    assert client.get(lifecycle(workspace) + "/resources").status_code == 404


def test_collection_archive_blocks_children_and_can_restore(client):
    workspace, collection, source = setup_source(client)
    as_actor(PLATFORM)
    result = accept(
        client, workspace, preview(client, workspace, "collection", collection["id"], "archive")
    )
    assert result.status_code == 200, result.text
    url = f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
    assert client.get(url + "/sources/" + source["id"]).status_code == 404
    assert (
        accept(
            client,
            workspace,
            preview(client, workspace, "collection", collection["id"], "restore"),
            "restore",
        ).status_code
        == 200
    )
    assert client.get(url + "/sources/" + source["id"]).status_code == 200


def test_collection_delete_requires_empty_store(client):
    workspace, collection, _ = setup_source(client)
    as_actor(PLATFORM)
    blocked = preview(client, workspace, "collection", collection["id"], "delete")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "collection_not_empty"

    empty = create_collection(client, workspace["id"], "Kho trống")
    removed = accept(
        client, workspace, preview(client, workspace, "collection", empty["id"], "delete")
    )
    assert removed.status_code == 200, removed.text
    restored = accept(
        client,
        workspace,
        preview(client, workspace, "collection", empty["id"], "restore"),
        "restore",
    )
    assert restored.status_code == 200, restored.text


def test_source_delete_receipt_is_owner_or_workspace_admin_only(client):
    from tests.integration.index_support import published_input

    data = published_input(client)
    workspace = data["workspace"]
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")
    promote_member(client, workspace["id"], REVIEWER.actor_id)
    as_actor(PLATFORM)
    proposal = preview(client, workspace, "source", data["source"]["id"], "delete")
    assert proposal.status_code == 200, proposal.text
    url = lifecycle(workspace) + "/actions/" + proposal.json()["id"]

    # A preview receipt stays bound to its owner even for a workspace admin.
    as_actor(REVIEWER)
    assert client.get(url).status_code == 404
    as_actor(PLATFORM)
    assert client.get(url).status_code == 200

    accepted = accept(client, workspace, proposal, "receipt-delete")
    assert accepted.status_code == 200, accepted.text
    as_actor(REVIEWER)
    assert client.get(url).status_code == 200
    as_actor(EDITOR)
    assert client.get(url).status_code == 404
    as_actor(MEMBER)
    assert client.get(url).status_code == 404
    as_actor(OUTSIDER)
    assert client.get(url).status_code == 404


def test_non_purge_receipts_never_expand_to_workspace_admins(client):
    from tests.integration.index_support import published_input

    data = published_input(client)
    workspace = data["workspace"]
    promote_member(client, workspace["id"], REVIEWER.actor_id)
    as_actor(PLATFORM)
    proposal = preview(
        client, workspace, "source", data["source"]["id"], "archive"
    )
    assert proposal.status_code == 200, proposal.text
    completed = accept(client, workspace, proposal, "receipt-archive")
    assert completed.status_code == 200, completed.text
    url = lifecycle(workspace) + "/actions/" + proposal.json()["id"]
    as_actor(REVIEWER)
    assert client.get(url).status_code == 404


def test_conversation_and_turn_receipts_stay_owner_scoped(client):
    from datetime import timedelta

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.lifecycle.models import LifecycleAction
    from qnu.platform.database import AsyncSessionFactory

    workspace = workspace_with_editor(client, "receipt-owner")
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")

    async def add_receipts():
        async with AsyncSessionFactory() as db:
            for suffix, kind, action, parameters in (
                ("conv", "conversation", "archive", {}),
                ("turn", "job", "cancel", {"job_kind": "turn"}),
            ):
                db.add(
                    LifecycleAction(
                        id="lca-owner-" + suffix,
                        workspace_id=workspace["id"],
                        actor_ref=EDITOR.actor_id,
                        kind=kind,
                        resource_id="synthetic-" + suffix,
                        action=action,
                        reason="Synthetic receipt scope.",
                        parameters=parameters,
                        impact={},
                        state_sha256="0" * 64,
                        preview_sha256="0" * 64,
                        status="completed",
                        expires_at=utcnow() + timedelta(minutes=5),
                        accepted_at=utcnow(),
                        finished_at=utcnow(),
                    )
                )
            await db.commit()

    client.portal.call(add_receipts)
    base = lifecycle(workspace) + "/actions/lca-owner-"
    as_actor(EDITOR)
    assert client.get(base + "conv").status_code == 200
    assert client.get(base + "turn").status_code == 200
    for actor in (REVIEWER, PLATFORM, MEMBER):
        as_actor(actor)
        assert client.get(base + "conv").status_code == 404
        assert client.get(base + "turn").status_code == 404
    as_actor(OUTSIDER)
    assert client.get(base + "conv").status_code == 404
    assert client.get(base + "turn").status_code == 404


def test_collection_withdraw_retires_serving_scope_and_keeps_originals(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.index.models import IndexSync
    from qnu.platform.database import AsyncSessionFactory
    from tests.integration.index_support import published_input

    data = published_input(client)
    workspace, collection, source = data["workspace"], data["collection"], data["source"]
    add_member(client, workspace["id"], PLATFORM.actor_id, "admin")

    async def sync_revision():
        async with AsyncSessionFactory() as db:
            row = await db.scalar(
                select(IndexSync).where(IndexSync.collection_id == collection["id"])
            )
            return (row.revision, row.status) if row is not None else (0, None)

    before = client.portal.call(sync_revision)
    as_actor(PLATFORM)
    result = accept(
        client,
        workspace,
        preview(client, workspace, "collection", collection["id"], "withdraw"),
        "withdraw-collection",
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "completed"
    assert client.get(data["version_url"]).json()["status"] == "withdrawn"
    assert client.get(data["document_url"] + "/published").status_code == 404
    after = client.portal.call(sync_revision)
    assert after[1] == "pending" and after[0] > before[0]

    revisions = (
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
        f"/sources/{source['id']}/revisions"
    )
    content = client.get(revisions).json()[0]
    original = client.get(revisions + f"/{content['id']}/content")
    assert original.status_code == 200 and original.content


def test_collection_delete_allows_only_soft_deleted_folder_residue(client):
    workspace = workspace_with_editor(client, "collection-residue")
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Kho còn thư mục xóa")
    folders = (
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/folders"
    )
    active = client.post(folders, json={"name": "Còn hoạt động"}).json()
    removed = client.post(folders, json={"name": "Đã xóa"}).json()
    assert client.delete(folders + "/" + removed["id"]).status_code == 200

    as_actor(PLATFORM)
    blocked = preview(client, workspace, "collection", collection["id"], "delete")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "collection_not_empty"

    as_actor(EDITOR)
    assert client.delete(folders + "/" + active["id"]).status_code == 200
    as_actor(PLATFORM)
    allowed = accept(
        client,
        workspace,
        preview(client, workspace, "collection", collection["id"], "delete"),
        "residue-delete",
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "completed"


@pytest.mark.parametrize("change", ["hash", "expired"])
def test_modified_or_expired_preview_cannot_delete_anything(client, change):
    from datetime import timedelta

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.lifecycle.models import LifecycleAction
    from qnu.platform.database import AsyncSessionFactory

    workspace, collection, source = setup_source(client)
    as_actor(PLATFORM)
    p = preview(client, workspace, "source", source["id"], "delete")
    assert p.status_code == 200, p.text
    body = {"preview_id": p.json()["id"], "preview_sha256": p.json()["preview_sha256"]}
    if change == "hash":
        body["preview_sha256"] = "0" * 64
    else:

        async def expire():
            async with AsyncSessionFactory() as db:
                row = await db.get(LifecycleAction, body["preview_id"])
                row.expires_at = utcnow() - timedelta(seconds=1)
                await db.commit()

        client.portal.call(expire)
    result = client.post(
        lifecycle(workspace) + "/actions", json=body, headers={"Idempotency-Key": "invalid"}
    )
    assert result.status_code == 409, result.text
    url = (
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources/{source['id']}"
    )
    assert client.get(url).status_code == 200


def test_concurrent_acceptance_has_one_effect_and_one_receipt(client):
    from concurrent.futures import ThreadPoolExecutor

    workspace, _, source = setup_source(client)
    as_actor(PLATFORM)
    p = preview(client, workspace, "source", source["id"], "archive")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(accept, client, workspace, p) for _ in range(2)]
        responses = [future.result(timeout=20) for future in futures]
    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert len(client.get(lifecycle(workspace) + "/resources").json()["items"]) == 1


def test_deleted_restore_requires_admin(client):
    workspace = workspace_with_editor(client, "lifecycle-restore")
    as_actor(PLATFORM)
    collection = create_collection(client, workspace["id"], "Kho trống")
    p = preview(client, workspace, "collection", collection["id"], "delete")
    assert accept(client, workspace, p).status_code == 200
    as_actor(EDITOR)
    assert preview(client, workspace, "collection", collection["id"], "restore").status_code == 403
