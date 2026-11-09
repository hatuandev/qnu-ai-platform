"""Workspace grants, capability resolution, concurrency and truthful usage accounting."""

import asyncio
from decimal import Decimal

import pytest

from qnu.domains.modelops.public_api import assert_provider_allowed
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.workspaces.service import workspace_service
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException
from tests.integration.test_workspaces_modelops_api import (
    ADMIN_A,
    API,
    MEMBER_A,
    OUTSIDER,
    PLATFORM,
    _add_member,
    _as,
    _create_workspace,
)


def provider(client, name="chat-one", capabilities=None):
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
    return result.json()


def setup_policy(client, limit=100):
    ws = _create_workspace(client, "workspace-a")
    _add_member(client, ws["id"], ADMIN_A.actor_id, "admin")
    _add_member(client, ws["id"], MEMBER_A.actor_id, "member")
    p = provider(client)
    assert (
        client.put(
            f"{API}/workspaces/{ws['id']}/allowed-providers",
            json={"provider_ids": [p["id"]], "defaults": {"chat": p["id"]}},
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"{API}/workspaces/{ws['id']}/quota", json={"monthly_token_limit": limit}
        ).status_code
        == 200
    )
    return ws, p


def test_unit_admin_selects_defaults_but_cannot_grant_provider(client):
    ws, p = setup_policy(client)
    forbidden = provider(client, "not-granted")
    _as(ADMIN_A)
    assert (
        client.put(
            f"{API}/workspaces/{ws['id']}/allowed-providers",
            json={"provider_ids": [forbidden["id"]]},
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"{API}/workspaces/{ws['id']}/model-defaults",
            json={"defaults": {"chat": forbidden["id"]}},
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"{API}/workspaces/{ws['id']}/model-defaults", json={"defaults": {"chat": p["id"]}}
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"{API}/workspaces/{ws['id']}/quota", json={"monthly_token_limit": 999999}
        ).status_code
        == 403
    )


def test_catalog_and_runtime_do_not_union_memberships(client):
    ws, p = setup_policy(client)
    other = _create_workspace(client, "workspace-b")
    _add_member(client, other["id"], MEMBER_A.actor_id, "member")
    _as(MEMBER_A)
    assert client.get(f"{API}/modelops/catalog").status_code == 400
    result = client.get(f"{API}/modelops/catalog", params={"workspace_id": ws["id"]})
    assert result.status_code == 200
    assert result.json()[0]["id"] == p["id"]
    assert "base_url" not in result.json()[0]
    assert client.get(f"{API}/modelops/catalog", params={"workspace_id": other["id"]}).json() == []

    async def resolve():
        async with AsyncSessionFactory() as db:
            with pytest.raises(AppException) as error:
                await assert_provider_allowed(db, MEMBER_A, other["id"], "chat", p["id"])
            assert error.value.status_code == 404

    client.portal.call(resolve)


def test_grants_defaults_and_disabled_workspace_are_rechecked(client):
    ws, p = setup_policy(client)
    ocr = provider(client, "ocr-only", ["ocr"])
    result = client.put(
        f"{API}/workspaces/{ws['id']}/allowed-providers",
        json={
            "provider_ids": [p["id"], ocr["id"]],
            "defaults": {"chat": p["id"], "ocr": ocr["id"]},
        },
    )
    assert result.status_code == 200
    assert {cap for item in result.json()["providers"] for cap in item["default_capabilities"]} == {
        "chat",
        "ocr",
    }
    invalid = client.put(
        f"{API}/workspaces/{ws['id']}/allowed-providers",
        json={"provider_ids": [ocr["id"]], "defaults": {"chat": ocr["id"]}},
    )
    assert invalid.status_code == 409
    assert (
        len(client.get(f"{API}/workspaces/{ws['id']}/allowed-providers").json()["providers"]) == 2
    )
    assert (
        client.patch(f"{API}/modelops/providers/{p['id']}", json={"is_active": False}).status_code
        == 200
    )
    assert any(not item["is_active"] for item in client.get(f"{API}/modelops/providers").json())
    _as(MEMBER_A)
    assert [
        row["id"]
        for row in client.get(f"{API}/modelops/catalog", params={"workspace_id": ws["id"]}).json()
    ] == [ocr["id"]]
    _as(PLATFORM)
    client.patch(f"{API}/workspaces/{ws['id']}", json={"status": "suspended"})
    _as(MEMBER_A)
    assert (
        client.get(f"{API}/modelops/catalog", params={"workspace_id": ws["id"]}).status_code == 403
    )


def test_system_defaults_partial_update_preserves_other_capabilities(client):
    chat = provider(client)
    ocr = provider(client, "ocr-one", ["ocr"])
    assert (
        client.put(f"{API}/modelops/defaults", json={"chat_provider_id": chat["id"]}).status_code
        == 200
    )
    result = client.put(f"{API}/modelops/defaults", json={"ocr_provider_id": ocr["id"]})
    assert result.status_code == 200
    assert result.json()["chat_provider_id"] == chat["id"]
    assert result.json()["ocr_model"] == ocr["model_name"]
    assert (
        client.put(
            f"{API}/modelops/defaults",
            json={"ocr_provider_id": ocr["id"], "ocr_model": "unregistered"},
        ).status_code
        == 409
    )
    events = client.get(f"{API}/modelops/events")
    assert events.status_code == 200
    assert {row["action"] for row in events.json()} == {"provider.created", "defaults.updated"}
    assert all("base_url" not in row["detail"] for row in events.json())


def test_key_rotation_keeps_secrets_encrypted_and_audited(client):
    p = provider(client)
    old = client.post(
        f"{API}/modelops/providers/{p['id']}/keys",
        json={"name": "primary", "secret": "sk-old-test-secret-1234"},
    ).json()
    response = client.post(
        f"{API}/modelops/providers/{p['id']}/keys/{old['id']}/rotate",
        json={"name": "replacement", "secret": "sk-new-test-secret-5678", "reason": "scheduled"},
    )
    assert response.status_code == 200
    assert "sk-new-test-secret" not in response.text
    states = {
        row["id"]: row["status"]
        for row in client.get(f"{API}/modelops/providers/{p['id']}/keys").json()
    }
    assert states[old["id"]] == "revoked"
    assert states[response.json()["id"]] == "active"
    assert "rotated" in {
        row["action"] for row in client.get(f"{API}/modelops/providers/{p['id']}/key-events").json()
    }

    async def ciphertext():
        from qnu.domains.modelops.models import ProviderKey

        async with AsyncSessionFactory() as db:
            row = await db.get(ProviderKey, response.json()["id"])
            assert row.secret_encrypted.startswith("enc:v1:")
            assert "sk-new-test-secret" not in row.secret_encrypted

    client.portal.call(ciphertext)


def test_quota_read_before_usage_starts_at_zero_without_limits(client):
    ws = _create_workspace(client, "workspace-a")
    _add_member(client, ws["id"], MEMBER_A.actor_id, "member")
    _as(MEMBER_A)
    response = client.get(f"{API}/workspaces/{ws['id']}/quota")
    assert response.status_code == 200, response.text
    quota = response.json()
    assert quota["configured"] is False
    assert quota["tokens_used"] == 0
    assert quota["tokens_reserved"] == 0
    assert quota["monthly_token_limit"] is None
    assert quota["is_blocked"] is False


def test_concurrent_reservations_record_usage_without_monthly_limit(client):
    ws, _ = setup_policy(client, limit=100)

    async def reserve(request_id):
        async with AsyncSessionFactory() as db:
            row = await usage_service.reserve(
                db, MEMBER_A, ws["id"], "chat", request_id, "a" * 64, 60
            )
            return row.id

    async def run():
        rows = await asyncio.gather(reserve("first"), reserve("second"))
        assert len(set(rows)) == 2
        async with AsyncSessionFactory() as db:
            row = await usage_service.settle(
                db, rows[0], total_tokens=35, cost_usd=Decimal("0.001")
            )
            await usage_service.settle(db, row.id, total_tokens=35, cost_usd=Decimal("0.001"))

    client.portal.call(run)
    _as(ADMIN_A)
    quota = client.get(f"{API}/workspaces/{ws['id']}/quota").json()
    assert quota["tokens_used"] == 35
    assert quota["tokens_reserved"] == 60
    usage = client.get(f"{API}/workspaces/{ws['id']}/usage").json()["items"]
    assert len(usage) == 2
    assert sorted(row["status"] for row in usage) == ["completed", "reserved"]


def test_unknown_usage_retains_reservation_and_retry_is_idempotent(client):
    ws, _ = setup_policy(client)

    async def run():
        async with AsyncSessionFactory() as db:
            first = await usage_service.reserve(
                db, MEMBER_A, ws["id"], "chat", "same", "a" * 64, 60
            )
            again = await usage_service.reserve(
                db, MEMBER_A, ws["id"], "chat", "same", "a" * 64, 60
            )
            assert first.id == again.id
            unknown = await usage_service.settle(db, first.id, total_tokens=None)
            assert unknown.total_tokens is None and unknown.cost_usd is None
            with pytest.raises(AppException) as error:
                await usage_service.reserve(db, MEMBER_A, ws["id"], "chat", "same", "b" * 64, 60)
            assert error.value.status_code == 409

    client.portal.call(run)
    _as(ADMIN_A)
    quota = client.get(f"{API}/workspaces/{ws['id']}/quota").json()
    assert quota["tokens_reserved"] == 60 and quota["tokens_used"] == 0
    _as(OUTSIDER)
    assert client.get(f"{API}/workspaces/{ws['id']}/usage").status_code == 404


def test_concurrent_admin_departures_preserve_at_least_one_admin(client):
    ws, _ = setup_policy(client)
    second = _add_member(client, ws["id"], "admin-other", "admin")
    from qnu.domains.identity.actor import AuthActor

    other = AuthActor(username="other", actor_id="admin-other")
    _as(PLATFORM)
    members = client.get(f"{API}/workspaces/{ws['id']}/members").json()["items"]
    first = next(row for row in members if row["actor_ref"] == ADMIN_A.actor_id)

    async def revoke(actor, member_id):
        async with AsyncSessionFactory() as db:
            try:
                await workspace_service.revoke_member(db, ws["id"], member_id, actor)
                return 200
            except AppException as error:
                return error.status_code

    async def run():
        return await asyncio.gather(revoke(ADMIN_A, first["id"]), revoke(other, second["id"]))

    assert sorted(client.portal.call(run)) == [200, 409]


def test_new_month_automatically_creates_usage_period(client):
    from datetime import date

    from qnu.domains.modelops.usage import service

    ws, _ = setup_policy(client)
    original = service.month_start

    async def run():
        service.month_start = lambda period=None: date(2099, 1, 1)
        try:
            async with AsyncSessionFactory() as db:
                record = await usage_service.reserve(
                    db, MEMBER_A, ws["id"], "chat", "next-month", "a" * 64, 10
                )
                assert record.month_period == date(2099, 1, 1)
                assert record.status == "reserved"
        finally:
            service.month_start = original

    client.portal.call(run)


def test_revoked_membership_immediately_removes_workspace_and_model_access(client):
    ws, _ = setup_policy(client)
    _as(PLATFORM)
    members = client.get(f"{API}/workspaces/{ws['id']}/members").json()["items"]
    member_id = next(row["id"] for row in members if row["actor_ref"] == MEMBER_A.actor_id)
    assert client.delete(f"{API}/workspaces/{ws['id']}/members/{member_id}").status_code == 200
    _as(MEMBER_A)
    assert client.get(f"{API}/workspaces").json()["items"] == []
    assert (
        client.get(f"{API}/modelops/catalog", params={"workspace_id": ws["id"]}).status_code == 404
    )


def test_subjects_differing_by_case_do_not_share_membership(client):
    from qnu.domains.identity.actor import AuthActor

    ws = _create_workspace(client, "case-sensitive")
    _add_member(client, ws["id"], "Subject-A", "member")
    _as(AuthActor(username="a", actor_id="subject-a"))
    assert client.get(f"{API}/workspaces/{ws['id']}").status_code == 404
    _as(AuthActor(username="a", actor_id="Subject-A"))
    assert client.get(f"{API}/workspaces/{ws['id']}").status_code == 200
