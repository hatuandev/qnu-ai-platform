"""System-wide default model resolution across workspaces."""

import pytest

from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.resilience.routing import choose_target
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import Conflict, EntityNotFound
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


def test_system_defaults_apply_across_all_workspaces_and_override_old(client):
    # 1. Create 2 isolated workspaces
    ws1 = _create_workspace(client, "ws-old-configured")
    ws2 = _create_workspace(client, "ws-never-configured")

    _add_member(client, ws1["id"], MEMBER_A.actor_id, "member")

    # 2. Create providers
    p_old = make_provider(client, name="chat-old", capabilities=["chat"])
    p_system = make_provider(client, name="chat-system", capabilities=["chat"])
    p_ocr = make_provider(client, name="ocr-system", capabilities=["ocr"])

    # ws1 has old workspace-level default for chat
    _as(PLATFORM)
    grant_res = client.put(
        f"{API}/workspaces/{ws1['id']}/allowed-providers",
        json={"provider_ids": [p_old["id"]], "defaults": {"chat": p_old["id"]}},
    )
    assert grant_res.status_code == 200

    # ws2 has NO workspace-level defaults and NO grants at all

    # Before setting system default:
    async def check_before():
        async with AsyncSessionFactory() as session:
            # ws1 uses its workspace default
            selected_ws1, _ = await choose_target(session, ws1["id"], "chat", None)
            assert selected_ws1 == p_old["id"]
            prov_ws1 = await catalog_service.resolve_workspace_provider(session, ws1["id"], "chat")
            assert prov_ws1.id == p_old["id"]

            # ws2 has no defaults configured
            selected_ws2, _ = await choose_target(session, ws2["id"], "chat", None)
            assert selected_ws2 is None
            with pytest.raises(Conflict) as exc_info:
                await catalog_service.resolve_workspace_provider(session, ws2["id"], "chat")
            assert exc_info.value.code == "model_not_configured"

    client.portal.call(check_before)

    # 3. Model Administrator sets system-wide default
    _as(PLATFORM)
    update_res = client.put(
        f"{API}/modelops/defaults",
        json={"chat_provider_id": p_system["id"], "ocr_provider_id": p_ocr["id"]},
    )
    assert update_res.status_code == 200
    assert update_res.json()["chat_provider_id"] == p_system["id"]
    assert update_res.json()["ocr_provider_id"] == p_ocr["id"]

    # 4. Now both workspaces resolve to the system default!
    async def check_after():
        async with AsyncSessionFactory() as session:
            # ws1 (old configured) now uses p_system (system default overrides old workspace default)
            selected_ws1, _ = await choose_target(session, ws1["id"], "chat", None)
            assert selected_ws1 == p_system["id"]
            prov_ws1 = await catalog_service.resolve_workspace_provider(session, ws1["id"], "chat")
            assert prov_ws1.id == p_system["id"]

            # ws2 (never configured) also automatically resolves to p_system!
            selected_ws2, _ = await choose_target(session, ws2["id"], "chat", None)
            assert selected_ws2 == p_system["id"]
            prov_ws2 = await catalog_service.resolve_workspace_provider(session, ws2["id"], "chat")
            assert prov_ws2.id == p_system["id"]

            # ws2 also resolves OCR to p_ocr
            selected_ocr, _ = await choose_target(session, ws2["id"], "ocr", None)
            assert selected_ocr == p_ocr["id"]
            prov_ocr = await catalog_service.resolve_workspace_provider(session, ws2["id"], "ocr")
            assert prov_ocr.id == p_ocr["id"]

            # Capability isolation: p_ocr is only granted for OCR, not chat
            with pytest.raises(EntityNotFound) as exc_info:
                await catalog_service.resolve_workspace_provider(session, ws2["id"], "chat", p_ocr["id"])
            assert exc_info.value.code == "provider_not_found"

    client.portal.call(check_after)

    # 5. Permission checks: Member lacking ai.models.manage cannot update system defaults
    _as(MEMBER_A)
    forbidden_update = client.put(
        f"{API}/modelops/defaults",
        json={"chat_provider_id": p_old["id"]},
    )
    assert forbidden_update.status_code == 403

    # Member of ws1 cannot access ws2
    forbidden_cross_ws = client.get(
        f"{API}/workspaces/{ws2['id']}/allowed-providers",
    )
    assert forbidden_cross_ws.status_code in (403, 404)

    # 6. Disabling the provider immediately causes Conflict(code="provider_inactive")
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
