"""Shared helpers for knowledge acceptance tests.

Every helper drives the real HTTP stack; nothing is stubbed except the actor, which
is the documented test seam (``app.dependency_overrides[get_actor]``).
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

API = "/platform/v1alpha1"

PLATFORM = AuthActor(
    username="root", actor_id="root", roles=["AI.Admin"], permissions=["ai.access.admin"]
)
EDITOR = AuthActor(username="editor", actor_id="cb_editor", permissions=["ai.knowledge.view"])
REVIEWER = AuthActor(username="reviewer", actor_id="cb_reviewer", permissions=["ai.knowledge.view"])
MEMBER = AuthActor(username="member", actor_id="cb_member", permissions=["ai.knowledge.view"])
OUTSIDER = AuthActor(username="outsider", actor_id="cb_outside", permissions=["ai.knowledge.view"])


def pdf_bytes(marker: str) -> bytes:
    return b"%PDF-1.7\n% " + marker.encode("utf-8") + b"\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


_ACTIVE_ACTOR: AuthActor | None = None


def as_actor(actor: AuthActor | None) -> None:
    global _ACTIVE_ACTOR
    _ACTIVE_ACTOR = actor

    def _dependency() -> AuthActor:
        if actor is None:
            raise AppException("Chưa đăng nhập.", code="unauthorized", status_code=401)
        return actor

    app.dependency_overrides[get_actor] = _dependency


def active_actor() -> AuthActor | None:
    """Who the next request will authenticate as (helpers restore it after use)."""
    return _ACTIVE_ACTOR


def create_workspace(client: TestClient, code: str) -> dict:
    as_actor(PLATFORM)
    response = client.post(f"{API}/workspaces", json={"code": code, "name": f"Đơn vị {code}"})
    assert response.status_code == 201, response.text
    return response.json()


def add_member(client: TestClient, workspace_id: str, actor_ref: str, role: str) -> dict:
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/workspaces/{workspace_id}/members", json={"actor_ref": actor_ref, "role": role}
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_collection(client: TestClient, workspace_id: str, name: str) -> dict:
    response = client.post(f"{API}/workspaces/{workspace_id}/collections", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def upload_source(
    client: TestClient,
    workspace_id: str,
    collection_id: str,
    *,
    payload: bytes | None = None,
    filename: str = "de-an.pdf",
    title: str | None = None,
    idempotency_key: str | None = None,
    content_type: str = "application/pdf",
    extra_data: dict | None = None,
    extra_headers: dict | None = None,
    auto_extract: bool = False,
):
    data = dict(extra_data or {})
    # Existing fixtures intentionally stage stored sources before explicit OCR/index
    # requests. New automatic-upload acceptance tests opt in to the new API default.
    data.setdefault("auto_extract", str(auto_extract).lower())
    if title is not None:
        data["title"] = title
    headers = dict(extra_headers or {})
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return client.post(
        f"{API}/workspaces/{workspace_id}/collections/{collection_id}/sources",
        files={
            "file": (filename, payload if payload is not None else pdf_bytes("v1"), content_type)
        },
        data=data,
        headers=headers,
    )


def add_revision(
    client: TestClient,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    *,
    payload: bytes,
    filename: str = "de-an.pdf",
    idempotency_key: str | None = None,
):
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
    return client.post(
        f"{API}/workspaces/{workspace_id}/collections/{collection_id}/sources/{source_id}/revisions",
        files={"file": (filename, payload, "application/pdf")},
        data={"auto_extract": "false"},
        headers=headers,
    )


def workspace_with_editor(client: TestClient, code: str = "khoa-cntt") -> dict:
    workspace = create_workspace(client, code)
    add_member(client, workspace["id"], EDITOR.actor_id, "editor")
    add_member(client, workspace["id"], REVIEWER.actor_id, "reviewer")
    add_member(client, workspace["id"], MEMBER.actor_id, "member")
    return workspace
