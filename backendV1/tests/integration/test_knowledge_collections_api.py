"""Acceptance for collections: scoping, roles, pagination and metadata updates."""

from __future__ import annotations

from fastapi.testclient import TestClient

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
    create_workspace,
    workspace_with_editor,
)


def test_collection_endpoints_require_authentication(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(None)
    assert (
        client.get(f"{API}/workspaces/{workspace['id']}/collections").status_code == 401
    )


def test_editor_creates_collection_with_server_owned_owner(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    response = client.post(
        f"{API}/workspaces/{workspace['id']}/collections",
        json={"name": " Tuyển sinh 2026 ", "description": "Đề án và điểm chuẩn"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Tuyển sinh 2026"
    assert body["workspace_id"] == workspace["id"]
    assert body["created_by"] == EDITOR.actor_id
    assert body["source_count"] == 0
    assert body["id"].startswith("col_")


def test_collection_list_is_paginated_and_scoped(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    for name in ("Tuyển sinh", "Quy chế", "Thư viện"):
        create_collection(client, workspace["id"], name)

    page = client.get(
        f"{API}/workspaces/{workspace['id']}/collections", params={"page": 1, "page_size": 2}
    )
    assert page.status_code == 200, page.text
    body = page.json()
    assert len(body["items"]) == 2
    assert body["meta"] == {"page": 1, "page_size": 2, "total": 3}
    assert {item["name"] for item in body["items"]} <= {"Tuyển sinh", "Quy chế", "Thư viện"}


def test_collection_detail_and_metadata_update(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    created = create_collection(client, workspace["id"], "Quy chế đào tạo")

    detail = client.get(f"{API}/workspaces/{workspace['id']}/collections/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Quy chế đào tạo"

    renamed = client.patch(
        f"{API}/workspaces/{workspace['id']}/collections/{created['id']}",
        json={"name": "Quy chế & quy định", "description": "Bản 2026"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Quy chế & quy định"
    assert renamed.json()["description"] == "Bản 2026"

    cleared = client.patch(
        f"{API}/workspaces/{workspace['id']}/collections/{created['id']}",
        json={"description": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    assert cleared.json()["name"] == "Quy chế & quy định"


def test_duplicate_collection_name_conflicts(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    create_collection(client, workspace["id"], "Trùng tên")
    response = client.post(
        f"{API}/workspaces/{workspace['id']}/collections", json={"name": "Trùng tên"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "collection_name_exists"


def test_reviewer_and_member_read_but_cannot_write(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    created = create_collection(client, workspace["id"], "Chỉ đọc")

    for actor in (REVIEWER, MEMBER):
        as_actor(actor)
        assert (
            client.get(f"{API}/workspaces/{workspace['id']}/collections").status_code == 200
        )
        assert (
            client.get(
                f"{API}/workspaces/{workspace['id']}/collections/{created['id']}"
            ).status_code
            == 200
        )
        blocked = client.post(
            f"{API}/workspaces/{workspace['id']}/collections", json={"name": "Không được tạo"}
        )
        assert blocked.status_code == 403
        assert blocked.json()["code"] == "workspace_forbidden"
        patched = client.patch(
            f"{API}/workspaces/{workspace['id']}/collections/{created['id']}",
            json={"name": "Đổi trộm"},
        )
        assert patched.status_code == 403


def test_non_member_cannot_see_the_workspace(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(OUTSIDER)
    assert (
        client.get(f"{API}/workspaces/{workspace['id']}/collections").status_code == 404
    )
    assert (
        client.post(
            f"{API}/workspaces/{workspace['id']}/collections", json={"name": "Lén"}
        ).status_code
        == 404
    )


def test_collection_id_from_another_workspace_is_not_found(client: TestClient) -> None:
    workspace_a = create_workspace(client, "khoa-a")
    workspace_b = create_workspace(client, "khoa-b")
    for workspace in (workspace_a, workspace_b):
        add_member(client, workspace["id"], EDITOR.actor_id, "editor")

    as_actor(EDITOR)
    foreign = create_collection(client, workspace_a["id"], "Của A")
    response = client.get(
        f"{API}/workspaces/{workspace_b['id']}/collections/{foreign['id']}"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "collection_not_found"
    assert (
        client.patch(
            f"{API}/workspaces/{workspace_b['id']}/collections/{foreign['id']}",
            json={"name": "Chiếm"},
        ).status_code
        == 404
    )


def test_suspended_workspace_blocks_content_access(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    created = create_collection(client, workspace["id"], "Tạm dừng")

    as_actor(PLATFORM)
    suspended = client.patch(
        f"{API}/workspaces/{workspace['id']}", json={"status": "suspended"}
    )
    assert suspended.status_code == 200, suspended.text

    as_actor(EDITOR)
    blocked = client.get(f"{API}/workspaces/{workspace['id']}/collections/{created['id']}")
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "workspace_suspended"


def test_workspace_id_cannot_be_supplied_in_the_body(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    other = create_workspace(client, "khoa-khac")
    as_actor(EDITOR)
    response = client.post(
        f"{API}/workspaces/{workspace['id']}/collections",
        json={"name": "Chèn workspace", "workspace_id": other["id"]},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
