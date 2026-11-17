"""Document model group and reasoning contract at the API level.

Runs through HTTP against a real test database; the scheduler itself is covered by
``tests/unit/test_document_model_group.py``. Skipped (NOT RUN) without
``TEST_DATABASE_URL``.
"""

from __future__ import annotations

import os

import pytest

if not os.environ.get("TEST_DATABASE_URL", "").strip():
    pytest.skip(
        "NOT RUN: TEST_DATABASE_URL chưa cấu hình (Postgres test riêng).",
        allow_module_level=True,
    )

from qnu.domains.modelops.document_processing import (
    document_provider,
    resolve_document_group,
)
from qnu.domains.modelops.resilience.routing import choose_target
from qnu.platform.database import AsyncSessionFactory
from tests.integration.test_system_model_defaults_global import make_provider
from tests.integration.test_workspaces_modelops_api import API, MEMBER_A, PLATFORM, _as

PATH = f"{API}/modelops/document-processing"


def settings(client) -> dict:
    response = client.get(PATH)
    assert response.status_code == 200, response.text
    return response.json()


def save_group(client, models, **extra) -> dict:
    _as(PLATFORM)
    response = client.patch(PATH, json={"models": models, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_group_order_concurrency_and_mode_survive_save_and_reload(client):
    first = make_provider(client, name="group-first")["id"]
    second = make_provider(client, name="group-second")["id"]
    third = make_provider(client, name="group-third")["id"]
    empty = settings(client)
    assert empty["models"] == []
    assert empty["provider_id"] is None
    assert empty["mode"] == "priority"

    body = save_group(
        client,
        [
            {"provider_id": second, "concurrency": 5},
            {"provider_id": first, "concurrency": 2},
            {"provider_id": third, "concurrency": 1},
        ],
        mode="parallel",
    )
    assert body["mode"] == "parallel"
    assert [model["provider_id"] for model in body["models"]] == [second, first, third]
    assert [model["concurrency"] for model in body["models"]] == [5, 2, 1]
    assert [model["effective_concurrency"] for model in body["models"]] == [5, 2, 1]
    assert [model["available"] for model in body["models"]] == [True, True, True]
    assert body["shared_concurrency"] == 5
    assert body["max_concurrency"] == 64
    # Legacy mirror: first entry plus non-default limits only.
    assert body["provider_id"] == second
    assert body["concurrency"] == {second: 5, first: 2}

    reloaded = settings(client)
    assert reloaded["mode"] == "parallel"
    assert [model["provider_id"] for model in reloaded["models"]] == [second, first, third]

    reordered = save_group(
        client,
        [
            {"provider_id": first, "concurrency": 2},
            {"provider_id": second, "concurrency": 5},
        ],
    )
    assert [model["provider_id"] for model in reordered["models"]] == [first, second]
    assert reordered["provider_id"] == first
    assert reordered["mode"] == "parallel"

    priority = save_group(client, [], mode="priority")
    assert priority["mode"] == "priority"
    assert priority["models"] == []
    assert priority["provider_id"] is None


def test_group_rejects_duplicate_bad_limits_and_unusable_models(client):
    first = make_provider(client, name="reject-first")["id"]
    ocr = make_provider(client, name="reject-ocr", capabilities=["ocr"])["id"]
    _as(PLATFORM)
    saved = client.patch(PATH, json={"models": [{"provider_id": first, "concurrency": 2}]})
    assert saved.status_code == 200, saved.text

    duplicate = client.patch(
        PATH,
        json={
            "models": [
                {"provider_id": first, "concurrency": 1},
                {"provider_id": first, "concurrency": 2},
            ]
        },
    )
    assert duplicate.status_code == 422
    assert duplicate.json()["code"] == "document_models_invalid"

    too_many = client.patch(
        PATH,
        json={
            "models": [
                {"provider_id": f"prv_missing_{index}", "concurrency": 1}
                for index in range(9)
            ]
        },
    )
    assert too_many.status_code == 422
    assert too_many.json()["code"] == "document_models_invalid"

    for invalid in (0, 65):
        response = client.patch(
            PATH, json={"models": [{"provider_id": first, "concurrency": invalid}]}
        )
        assert response.status_code == 422, invalid

    # The interface value governs: above the environment default is still saved as is.
    above_default = client.patch(
        PATH, json={"models": [{"provider_id": first, "concurrency": 7}]}
    )
    assert above_default.status_code == 200, above_default.text
    assert above_default.json()["models"][0]["concurrency"] == 7
    assert above_default.json()["models"][0]["effective_concurrency"] == 7

    not_chat = client.patch(
        PATH, json={"models": [{"provider_id": ocr, "concurrency": 1}]}
    )
    assert not_chat.status_code == 409
    assert not_chat.json()["code"] == "provider_capability_mismatch"

    missing = client.patch(
        PATH, json={"models": [{"provider_id": "prv_nope", "concurrency": 1}]}
    )
    assert missing.status_code == 404

    bad_mode = client.patch(PATH, json={"mode": "sequential"})
    assert bad_mode.status_code == 422

    client.patch(f"{API}/modelops/providers/{first}", json={"is_active": False})
    inactive = client.patch(
        PATH, json={"models": [{"provider_id": first, "concurrency": 1}]}
    )
    assert inactive.status_code == 409
    assert inactive.json()["code"] == "provider_inactive"

    # A rejected write never overwrites the stored group.
    kept = settings(client)
    assert [model["provider_id"] for model in kept["models"]] == [first]
    assert kept["models"][0]["concurrency"] == 7


def test_legacy_fields_keep_working_and_group_writes_own_the_contract(client):
    first = make_provider(client, name="legacy-first")["id"]
    second = make_provider(client, name="legacy-second")["id"]
    _as(PLATFORM)
    legacy = client.patch(
        PATH, json={"provider_id": second, "concurrency": {first: 2, second: 5}}
    )
    assert legacy.status_code == 200, legacy.text
    body = legacy.json()
    assert body["provider_id"] == second
    assert body["concurrency"] == {first: 2, second: 5}
    assert [model["provider_id"] for model in body["models"]] == [second]
    assert body["models"][0]["concurrency"] == 5
    assert body["mode"] == "priority"

    group = save_group(
        client,
        [
            {"provider_id": first, "concurrency": 2},
            {"provider_id": second, "concurrency": 5},
        ],
        mode="parallel",
    )
    assert group["provider_id"] == first
    assert group["concurrency"] == {first: 2, second: 5}
    assert [model["provider_id"] for model in group["models"]] == [first, second]

    back_to_legacy = client.patch(PATH, json={"provider_id": second})
    assert back_to_legacy.status_code == 200, back_to_legacy.text
    assert [model["provider_id"] for model in back_to_legacy.json()["models"]] == [second]
    assert back_to_legacy.json()["provider_id"] == second


def test_resolution_pins_order_skips_disabled_and_falls_back_when_empty(client):
    first = make_provider(client, name="resolve-first")["id"]
    second = make_provider(client, name="resolve-second")["id"]
    third = make_provider(client, name="resolve-third")["id"]
    save_group(
        client,
        [
            {"provider_id": second, "concurrency": 5},
            {"provider_id": first, "concurrency": 2},
        ],
        mode="parallel",
    )

    async def check_parallel():
        async with AsyncSessionFactory() as session:
            group = await resolve_document_group(session)
            assert group.mode == "parallel"
            assert [(model.provider_id, model.concurrency) for model in group.models] == [
                (second, 5),
                (first, 2),
            ]
            pinned = await resolve_document_group(session, first)
            assert pinned.mode == "priority"
            assert [(model.provider_id, model.concurrency) for model in pinned.models] == [
                (first, 2)
            ]
            assert await document_provider(session) == second

    client.portal.call(check_parallel)

    save_group(
        client,
        [
            {"provider_id": second, "concurrency": 5},
            {"provider_id": first, "concurrency": 2},
        ],
        mode="priority",
    )

    async def check_priority():
        async with AsyncSessionFactory() as session:
            group = await resolve_document_group(session)
            assert group.mode == "priority"
            assert [model.provider_id for model in group.models] == [second]

    client.portal.call(check_priority)

    save_group(
        client,
        [
            {"provider_id": second, "concurrency": 5},
            {"provider_id": first, "concurrency": 2},
        ],
        mode="parallel",
    )
    _as(PLATFORM)
    client.patch(f"{API}/modelops/providers/{second}", json={"is_active": False})
    disabled = settings(client)
    by_id = {model["provider_id"]: model for model in disabled["models"]}
    assert by_id[second]["available"] is False
    assert by_id[first]["available"] is True

    async def check_disabled():
        async with AsyncSessionFactory() as session:
            group = await resolve_document_group(session)
            assert [model.provider_id for model in group.models] == [first]

    client.portal.call(check_disabled)

    save_group(client, [], mode="parallel")
    _as(PLATFORM)
    assert client.put(
        f"{API}/modelops/defaults", json={"chat_provider_id": third}
    ).is_success

    async def check_empty():
        async with AsyncSessionFactory() as session:
            group = await resolve_document_group(session)
            assert group.models == ()
            assert group.provider_id is None
            target, _ = await choose_target(session, "ws_any", "compiler", None)
            assert target == third

    client.portal.call(check_empty)


def test_reasoning_contract_is_only_applied_after_verification(client):
    provider = make_provider(client, name="reasoning-target")
    path = f"{API}/modelops/providers/{provider['id']}/reasoning"
    _as(PLATFORM)

    initial = client.get(path)
    assert initial.status_code == 200, initial.text
    assert initial.json()["status"] == "not_configured"
    assert initial.json()["policy"] is None
    assert initial.json()["effective"]["compiler"]["reason"] == (
        "provider_keeps_server_default"
    )

    unverified = client.put(
        path,
        json={
            "policy": {
                "mode": "toggle",
                "parameter": "enable_thinking",
                "low_value": True,
                "off_value": False,
                "tasks": {"off": ["compiler"]},
                "verified": False,
            }
        },
    )
    assert unverified.status_code == 200, unverified.text
    body = unverified.json()
    assert body["status"] == "unverified"
    assert body["effective"]["compiler"]["applied"] is False
    assert body["effective"]["compiler"]["reason"] == "capability_not_verified"

    save_group(client, [{"provider_id": provider["id"], "concurrency": 1}])
    thinking = settings(client)["models"][0]["thinking"]
    assert thinking == {
        "configured": "off",
        "effective": "server",
        "verified": False,
        "status": "unverified",
        "reason": "capability_not_verified",
    }

    verified = client.put(
        path,
        json={
            "policy": {
                "mode": "toggle",
                "parameter": "enable_thinking",
                "low_value": True,
                "off_value": False,
                "tasks": {"off": ["compiler"], "low": ["compiler_review"]},
                "verified": True,
            }
        },
    )
    assert verified.status_code == 200, verified.text
    body = verified.json()
    assert body["status"] == "active"
    assert body["policy"]["tasks"] == {
        "off": ["compiler"],
        "low": ["compiler_review"],
    }
    assert body["effective"]["compiler"]["applied"] is True
    assert body["effective"]["compiler"]["mode"] == "toggle"
    assert body["effective"]["compiler"]["parameter"] == "enable_thinking"
    assert body["effective"]["compiler"]["level"] == "off"
    assert body["effective"]["compiler"]["value"] is False
    assert body["effective"]["compiler_review"]["level"] == "low"
    assert body["effective"]["compiler_review"]["value"] is True
    thinking = settings(client)["models"][0]["thinking"]
    assert thinking["configured"] == "off"
    assert thinking["effective"] == "off"
    assert thinking["verified"] is True

    reset = client.put(path, json={"policy": {"mode": "server_default"}})
    assert reset.status_code == 200, reset.text
    assert reset.json()["status"] == "not_configured"
    assert reset.json()["policy"] is None
    assert settings(client)["models"][0]["thinking"]["effective"] == "server"

    _as(MEMBER_A)
    assert client.get(path).status_code == 403
    assert client.put(path, json={"policy": {"mode": "server_default"}}).status_code == 403
