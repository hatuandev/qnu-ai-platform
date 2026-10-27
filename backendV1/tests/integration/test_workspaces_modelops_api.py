"""API-level acceptance for workspaces, membership and ModelOps allowlists.

Every case runs through HTTP with a real test database; nothing is faked.
Skipped (NOT RUN) when TEST_DATABASE_URL is absent.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

if not os.environ.get("TEST_DATABASE_URL", "").strip():
    pytest.skip(
        "NOT RUN: TEST_DATABASE_URL chưa cấu hình (Postgres test riêng).",
        allow_module_level=True,
    )

from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.main import app
from qnu.platform.errors import AppException

PLATFORM = AuthActor(
    username="root", actor_id="root", roles=["AI.Admin"], permissions=["ai.access.admin"]
)
ADMIN_A = AuthActor(
    username="admin-a",
    actor_id="cb_a",
    roles=["staff"],
    permissions=["ai.workspaces.view", "ai.knowledge.view", "ai.models.view"],
)
MEMBER_A = AuthActor(
    username="member-a",
    actor_id="cb_m",
    roles=["staff"],
    permissions=["ai.workspaces.view", "ai.models.view"],
)
OUTSIDER = AuthActor(
    username="outsider",
    actor_id="cb_x",
    roles=["staff"],
    permissions=["ai.workspaces.view", "ai.models.view"],
)

API = "/platform/v1alpha1"


def _as(actor: AuthActor | None) -> None:
    def _dependency() -> AuthActor:
        if actor is None:
            raise AppException("Chưa đăng nhập.", code="unauthorized", status_code=401)
        return actor

    app.dependency_overrides[get_actor] = _dependency


def _create_workspace(client: TestClient, code: str) -> dict:
    _as(PLATFORM)
    response = client.post(f"{API}/workspaces", json={"code": code, "name": f"Đơn vị {code}"})
    assert response.status_code == 201, response.text
    return response.json()


def _add_member(client: TestClient, workspace_id: str, actor_ref: str, role: str) -> dict:
    _as(PLATFORM)
    response = client.post(
        f"{API}/workspaces/{workspace_id}/members",
        json={"actor_ref": actor_ref, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_unauthenticated_request_is_rejected(client: TestClient) -> None:
    _as(None)
    assert client.get(f"{API}/workspaces").status_code == 401


def test_workspace_admin_cannot_create_workspace(client: TestClient) -> None:
    _as(ADMIN_A)
    response = client.post(f"{API}/workspaces", json={"code": "blocked", "name": "Bị chặn"})
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_duplicate_workspace_code_conflicts(client: TestClient) -> None:
    _create_workspace(client, "khoa-a")
    _as(PLATFORM)
    response = client.post(f"{API}/workspaces", json={"code": "khoa-a", "name": "Trùng"})
    assert response.status_code == 409
    assert response.json()["code"] == "workspace_code_exists"


def test_member_of_a_cannot_manage_b(client: TestClient) -> None:
    workspace_a = _create_workspace(client, "khoa-a")
    workspace_b = _create_workspace(client, "khoa-b")
    _add_member(client, workspace_a["id"], "cb_a", "admin")

    _as(ADMIN_A)
    assert client.get(f"{API}/workspaces/{workspace_b['id']}").status_code == 404
    assert (
        client.patch(f"{API}/workspaces/{workspace_b['id']}", json={"name": "X"}).status_code == 403
    )
    assert (
        client.post(
            f"{API}/workspaces/{workspace_b['id']}/members",
            json={"actor_ref": "cb_a", "role": "admin"},
        ).status_code
        == 404
    )


def test_swapping_workspace_id_in_body_does_not_escalate(client: TestClient) -> None:
    workspace_a = _create_workspace(client, "khoa-a")
    workspace_b = _create_workspace(client, "khoa-b")
    _add_member(client, workspace_a["id"], "cb_a", "admin")

    _as(ADMIN_A)
    response = client.post(
        f"{API}/workspaces/{workspace_a['id']}/members",
        json={"actor_ref": "cb_new", "role": "admin", "workspace_id": workspace_b["id"]},
    )
    assert response.status_code == 422


def test_duplicate_membership_then_revoke_and_restore(client: TestClient) -> None:
    workspace = _create_workspace(client, "khoa-a")
    member = _add_member(client, workspace["id"], "cb_a", "admin")
    _as(PLATFORM)
    duplicate = client.post(
        f"{API}/workspaces/{workspace['id']}/members",
        json={"actor_ref": "cb_a", "role": "member"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "membership_exists"

    revoked = client.delete(f"{API}/workspaces/{workspace['id']}/members/{member['id']}")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    restored = client.post(
        f"{API}/workspaces/{workspace['id']}/members",
        json={"actor_ref": "cb_a", "role": "admin"},
    )
    assert restored.status_code == 201
    assert restored.json()["id"] == member["id"]


def test_suspended_workspace_blocks_members_but_not_platform(client: TestClient) -> None:
    workspace = _create_workspace(client, "khoa-a")
    _add_member(client, workspace["id"], "cb_a", "admin")

    _as(PLATFORM)
    assert (
        client.patch(
            f"{API}/workspaces/{workspace['id']}", json={"status": "suspended"}
        ).status_code
        == 200
    )

    _as(ADMIN_A)
    blocked = client.get(f"{API}/workspaces/{workspace['id']}")
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "workspace_suspended"

    _as(PLATFORM)
    assert client.get(f"{API}/workspaces/{workspace['id']}").status_code == 200


def test_last_admin_cannot_be_revoked(client: TestClient) -> None:
    workspace = _create_workspace(client, "khoa-a")
    member = _add_member(client, workspace["id"], "cb_a", "admin")

    _as(ADMIN_A)
    response = client.delete(f"{API}/workspaces/{workspace['id']}/members/{member['id']}")
    assert response.status_code == 409
    assert response.json()["code"] == "last_admin_required"


def test_workspace_audit_records_actions(client: TestClient) -> None:
    workspace = _create_workspace(client, "khoa-a")
    _add_member(client, workspace["id"], "cb_a", "admin")

    _as(PLATFORM)
    response = client.get(f"{API}/workspaces/{workspace['id']}/events")
    assert response.status_code == 200
    actions = [item["action"] for item in response.json()["items"]]
    assert "workspace.created" in actions
    assert "member.added" in actions


def test_provider_and_key_lifecycle_never_returns_plaintext(client: TestClient) -> None:
    _as(PLATFORM)
    created = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "local-chat",
            "provider_type": "openai_compatible",
            "base_url": "http://localhost:11434/v1",
            "model_name": "qwen2.5",
            "capabilities": ["chat"],
        },
    )
    assert created.status_code == 201, created.text
    provider = created.json()

    member_attempt = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "blocked",
            "provider_type": "local",
            "base_url": "http://localhost:11434/v1",
            "model_name": "m",
            "capabilities": ["chat"],
        },
    )
    assert member_attempt.status_code == 201

    _as(MEMBER_A)
    forbidden = client.post(
        f"{API}/modelops/providers/{provider['id']}/keys",
        json={"name": "k", "secret": "sk-should-not-be-allowed"},
    )
    assert forbidden.status_code == 403

    _as(PLATFORM)
    key_response = client.post(
        f"{API}/modelops/providers/{provider['id']}/keys",
        json={"name": "primary", "secret": "sk-super-secret-value"},
    )
    assert key_response.status_code == 201, key_response.text
    body = key_response.json()
    assert "sk-super-secret-value" not in key_response.text
    assert body["masked_hint"].startswith("****")

    revoked = client.post(
        f"{API}/modelops/providers/{provider['id']}/keys/{body['id']}/revoke", json={}
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    again = client.post(
        f"{API}/modelops/providers/{provider['id']}/keys/{body['id']}/revoke", json={}
    )
    assert again.status_code == 200


def test_allowlist_controls_catalog_and_stays_workspace_scoped(client: TestClient) -> None:
    workspace_a = _create_workspace(client, "khoa-a")
    workspace_b = _create_workspace(client, "khoa-b")
    _add_member(client, workspace_a["id"], "cb_a", "admin")
    _add_member(client, workspace_a["id"], "cb_m", "member")

    _as(PLATFORM)
    provider = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "cloud-chat",
            "provider_type": "openai_compatible",
            "base_url": "https://api.example.test/v1",
            "model_name": "gpt-x",
            "capabilities": ["chat"],
        },
    ).json()

    _as(PLATFORM)
    granted = client.put(
        f"{API}/workspaces/{workspace_a['id']}/allowed-providers",
        json={"provider_ids": [provider["id"]], "default_provider_id": provider["id"]},
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["providers"][0]["is_default"] is True

    _as(MEMBER_A)
    catalog = client.get(
        f"{API}/modelops/catalog", params={"workspace_id": workspace_a["id"]}
    ).json()
    assert [item["id"] for item in catalog] == [provider["id"]]

    _as(OUTSIDER)
    assert (
        client.get(
            f"{API}/modelops/catalog", params={"workspace_id": workspace_a["id"]}
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"{API}/workspaces/{workspace_a['id']}/allowed-providers",
            json={"provider_ids": [provider["id"]]},
        ).status_code
        == 403
    )

    _as(ADMIN_A)
    assert (
        client.put(
            f"{API}/workspaces/{workspace_b['id']}/allowed-providers",
            json={"provider_ids": [provider["id"]]},
        ).status_code
        == 403
    )


def test_defaults_reject_provider_without_capability(client: TestClient) -> None:
    _as(PLATFORM)
    provider = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "chat-only",
            "provider_type": "openai_compatible",
            "base_url": "https://api.example.test/v1",
            "model_name": "gpt-x",
            "capabilities": ["chat"],
        },
    ).json()

    response = client.put(
        f"{API}/modelops/defaults",
        json={"embedding_provider_id": provider["id"], "embedding_model": "text-embedding"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "provider_capability_mismatch"
