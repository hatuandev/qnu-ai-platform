"""System-wide default model resolution across workspaces."""

import pytest

from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.document_processing import configured_concurrency
from qnu.domains.modelops.resilience.routing import choose_target
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import Conflict
from tests.integration.test_workspaces_modelops_api import (
    API,
    MEMBER_A,
    PLATFORM,
    _add_member,
    _as,
    _create_workspace,
)


def make_provider(client, name="chat-one", capabilities=None):
    _as(PLATFORM)
    result = client.post(
        f"{API}/modelops/providers",
        json={
            "name": name,
            "provider_type": "openai_compatible",
            "base_url": "https://provider.example.test/v1",
            "model_name": name,
            "capabilities": capabilities or ["chat"],
        },
    )
    assert result.status_code == 201, result.text
    p = result.json()
    # Add an active key
    key_res = client.post(
        f"{API}/modelops/providers/{p['id']}/keys",
        json={"name": "key-1", "secret": "sk-test-secret-12345"},
    )
    assert key_res.status_code == 201, key_res.text
    return p


def test_system_defaults_apply_across_all_workspaces(client):
    ws1 = _create_workspace(client, "ws-member")
    ws2 = _create_workspace(client, "ws-other")

    _add_member(client, ws1["id"], MEMBER_A.actor_id, "member")

    p_system = make_provider(client, name="chat-system", capabilities=["chat"])
    p_ocr = make_provider(client, name="ocr-system", capabilities=["ocr"])

    # Before a system default exists, no workspace resolves a model implicitly.
    async def check_before():
        async with AsyncSessionFactory() as session:
            selected_ws1, _ = await choose_target(session, ws1["id"], "chat", None)
            assert selected_ws1 is None
            with pytest.raises(Conflict) as exc_info:
                await catalog_service.resolve_workspace_provider(session, ws1["id"], "chat")
            assert exc_info.value.code == "model_not_configured"

    client.portal.call(check_before)

    # Model Administrator sets system-wide defaults.
    _as(PLATFORM)
    update_res = client.put(
        f"{API}/modelops/defaults",
        json={"chat_provider_id": p_system["id"], "ocr_provider_id": p_ocr["id"]},
    )
    assert update_res.status_code == 200
    assert update_res.json()["chat_provider_id"] == p_system["id"]
    assert update_res.json()["ocr_provider_id"] == p_ocr["id"]

    # Both workspaces resolve the same defaults without any per-unit configuration.
    async def check_after():
        async with AsyncSessionFactory() as session:
            for workspace_id in (ws1["id"], ws2["id"]):
                selected_chat, _ = await choose_target(session, workspace_id, "chat", None)
                assert selected_chat == p_system["id"]
                chat = await catalog_service.resolve_workspace_provider(
                    session, workspace_id, "chat"
                )
                assert chat.id == p_system["id"]

                selected_ocr, _ = await choose_target(session, workspace_id, "ocr", None)
                assert selected_ocr == p_ocr["id"]
                ocr = await catalog_service.resolve_workspace_provider(
                    session, workspace_id, "ocr"
                )
                assert ocr.id == p_ocr["id"]

            # Capability isolation: p_ocr serves OCR only, never chat.
            with pytest.raises(Conflict) as exc_info:
                await catalog_service.resolve_workspace_provider(
                    session, ws2["id"], "chat", p_ocr["id"]
                )
            assert exc_info.value.code == "provider_capability_mismatch"

    client.portal.call(check_after)

    # Permission checks: a member lacking ai.models.manage cannot update defaults.
    _as(MEMBER_A)
    forbidden_update = client.put(
        f"{API}/modelops/defaults",
        json={"chat_provider_id": p_system["id"]},
    )
    assert forbidden_update.status_code == 403

    # Member of ws1 cannot see ws2's catalog.
    forbidden_cross_ws = client.get(
        f"{API}/modelops/catalog", params={"workspace_id": ws2["id"]}
    )
    assert forbidden_cross_ws.status_code == 404

    # Disabling the default provider immediately makes resolution fail.
    _as(PLATFORM)
    client.patch(
        f"{API}/modelops/providers/{p_system['id']}",
        json={"is_active": False},
    )

    async def check_inactive():
        async with AsyncSessionFactory() as session:
            with pytest.raises(Conflict) as exc_info:
                await catalog_service.resolve_workspace_provider(session, ws1["id"], "chat")
            assert exc_info.value.code == "provider_inactive"

    client.portal.call(check_inactive)


def test_document_settings_are_system_wide_and_keep_a_limit_per_model(client):
    workspace = _create_workspace(client, "ws-document")
    _add_member(client, workspace["id"], MEMBER_A.actor_id, "member")
    first = make_provider(client, name="document-first")["id"]
    second = make_provider(client, name="document-second")["id"]
    ocr = make_provider(client, name="ocr-only", capabilities=["ocr"])["id"]
    path = f"{API}/modelops/document-processing"
    assert client.get(path).json()["concurrency"] == {}
    assert client.put(f"{API}/modelops/defaults", json={"chat_provider_id": first}).is_success

    response = client.patch(path, json={"provider_id": second, "concurrency": {first: 2, second: 5}})
    assert response.is_success, response.text
    assert response.json()["concurrency"] == {first: 2, second: 5}
    assert client.patch(path, json={"concurrency": {first: 0}}).status_code == 422
    assert client.patch(path, json={"concurrency": {first: 65}}).status_code == 422
    assert client.patch(path, json={"provider_id": ocr}).status_code == 409

    async def resolve():
        async with AsyncSessionFactory() as session:
            for task in ("compiler", "compiler_review"):
                target, _ = await choose_target(session, workspace["id"], task, None)
                assert target == second
                explicit, _ = await choose_target(session, workspace["id"], task, first)
                assert explicit == first
            target, _ = await choose_target(session, workspace["id"], "chat", None)
            assert target == first
            assert await configured_concurrency(session, second) == 5

    client.portal.call(resolve)
    cleared = client.patch(path, json={"provider_id": None, "concurrency": {second: 1}})
    assert cleared.is_success, cleared.text
    assert cleared.json()["provider_id"] is None
    assert cleared.json()["concurrency"] == {first: 2}
    _as(MEMBER_A)
    assert client.get(path).status_code == 403
    assert client.patch(path, json={"provider_id": first}).status_code == 403
