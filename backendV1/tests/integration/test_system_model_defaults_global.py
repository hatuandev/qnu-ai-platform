"""System-wide default model resolution across workspaces."""

import pytest

from qnu.domains.modelops.catalog.service import catalog_service
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
