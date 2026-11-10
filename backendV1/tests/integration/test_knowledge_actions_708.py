"""Knowledge explorer safety regressions; disposable database and synthetic files."""

import pytest
from sqlalchemy import select

from qnu.domains.identity.dev_gate import issue_dev_token
from qnu.domains.workspaces.models import WorkspaceMember
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    as_actor,
    create_collection,
    upload_source,
    workspace_with_editor,
)
from tests.integration.ocr_support import (
    FakeJobQueue,
    FakeNemotron,
    execute_now,
    prepare_source,
    real_pdf,
    request_run,
    setup_ocr_provider,
    use_queue,
)
from tests.integration.test_lifecycle_659 import accept, preview


def test_nonempty_folder_delete_preserves_sources_and_directory(client):
    ws = workspace_with_editor(client, "folder-safety-708")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Folder safety")
    base = f"{API}/workspaces/{ws['id']}/collections/{col['id']}"
    folder = client.post(base + "/folders", json={"name": "Evidence"}).json()
    source = upload_source(client, ws["id"], col["id"]).json()["source"]
    assert client.post(
        base + f"/sources/{source['id']}/move",
        json={"target_folder_id": folder["id"]},
    ).status_code == 200
    response = client.delete(base + f"/folders/{folder['id']}")
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "folder_not_empty"
    assert client.get(base + f"/folders/{folder['id']}").status_code == 200
    assert client.get(base + f"/sources/{source['id']}").status_code == 200


def test_folder_with_children_cannot_be_deleted_but_empty_folder_can(client):
    ws = workspace_with_editor(client, "folder-tree-708")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Folder tree")
    base = f"{API}/workspaces/{ws['id']}/collections/{col['id']}/folders"
    parent = client.post(base, json={"name": "Parent"}).json()
    child = client.post(base, json={"name": "Child", "parent_id": parent["id"]}).json()
    assert client.delete(base + f"/{parent['id']}").status_code == 409
    assert client.delete(base + f"/{child['id']}").status_code == 200
    assert client.post(base + f"/{child['id']}/restore").status_code == 200


def test_folder_restore_requires_visible_parent_and_free_name(client):
    ws = workspace_with_editor(client, "folder-restore-708")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Folder restore")
    base = f"{API}/workspaces/{ws['id']}/collections/{col['id']}/folders"
    parent = client.post(base, json={"name": "Parent"}).json()
    child = client.post(base, json={"name": "Child", "parent_id": parent["id"]}).json()
    assert client.delete(base + f"/{child['id']}").status_code == 200
    assert client.delete(base + f"/{parent['id']}").status_code == 200
    blocked = client.post(base + f"/{child['id']}/restore")
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "folder_parent_unavailable"
    assert client.post(base + f"/{parent['id']}/restore").status_code == 200
    assert client.post(base + f"/{child['id']}/restore").status_code == 200
    restored = client.get(base + f"/{child['id']}")
    assert restored.status_code == 200
    assert restored.json()["parent_id"] == parent["id"]


def test_folder_restore_rejects_case_insensitive_sibling(client):
    ws = workspace_with_editor(client, "folder-name-708")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Folder names")
    base = f"{API}/workspaces/{ws['id']}/collections/{col['id']}/folders"
    first = client.post(base, json={"name": "Evidence"}).json()
    assert client.delete(base + f"/{first['id']}").status_code == 200
    second = client.post(base, json={"name": "evidence"}).json()
    conflict = client.post(base + f"/{first['id']}/restore")
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "folder_name_exists"
    assert client.delete(base + f"/{second['id']}").status_code == 200
    assert client.post(base + f"/{first['id']}/restore").status_code == 200


def test_folder_restore_in_archived_collection_is_not_available(client):
    ws = workspace_with_editor(client, "folder-archived-708")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Archived store")
    base = f"{API}/workspaces/{ws['id']}/collections/{col['id']}/folders"
    folder = client.post(base, json={"name": "Pending"}).json()
    assert client.delete(base + f"/{folder['id']}").status_code == 200
    archived = accept(client, ws, preview(client, ws, "collection", col["id"], "archive"))
    assert archived.status_code == 200, archived.text
    blocked = client.post(base + f"/{folder['id']}/restore")
    assert blocked.status_code == 404, blocked.text
    assert blocked.json()["code"] == "resource_unavailable"


@pytest.mark.parametrize("gate_still_enabled", [True, False])
def test_dev_admin_background_ocr_rechecks_server_gate(client, monkeypatch, gate_still_enabled):
    settings = get_settings()
    monkeypatch.setattr(settings, "DEV_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "SSO_ENABLED", False)
    monkeypatch.setattr(settings, "DEV_ACCESS_PASSWORD", "synthetic-dev-password-708")
    monkeypatch.setattr(settings, "SECRET_KEY", "synthetic-signing-key-708-32-characters")
    _token, admin = issue_dev_token("synthetic-dev-password-708")
    ws = workspace_with_editor(client, "background-admin-708")
    as_actor(admin)
    use_queue(FakeJobQueue())
    col, source, revision = prepare_source(client, ws["id"], "Admin OCR", payload=real_pdf(["Synthetic page"]))
    with FakeNemotron() as fake:
        setup_ocr_provider(client, ws["id"], fake.base_url)
        run = request_run(client, ws["id"], col["id"], source["id"], revision["id"], queue=FakeJobQueue()).json()["run"]
        monkeypatch.setattr(settings, "DEV_AUTH_ENABLED", gate_still_enabled)
        result = execute_now(client, run["id"])
        assert result.status == ("completed" if gate_still_enabled else "failed"), result
        assert len(fake.requests) == (1 if gate_still_enabled else 0)


def test_revoked_member_background_ocr_stops_before_provider(client):
    ws = workspace_with_editor(client, "revoked-worker-708")
    as_actor(EDITOR)
    use_queue(FakeJobQueue())
    col, source, revision = prepare_source(client, ws["id"], "Revoked OCR", payload=real_pdf(["Synthetic page"]))
    with FakeNemotron() as fake:
        setup_ocr_provider(client, ws["id"], fake.base_url)
        run = request_run(client, ws["id"], col["id"], source["id"], revision["id"], queue=FakeJobQueue()).json()["run"]

        async def revoke():
            async with AsyncSessionFactory() as db:
                member = await db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws["id"], WorkspaceMember.actor_ref == EDITOR.actor_id))
                member.status = "revoked"
                await db.commit()

        client.portal.call(revoke)
        result = execute_now(client, run["id"])
        assert result.status == "failed" and result.reason == "workspace_not_found"
        assert not fake.requests
