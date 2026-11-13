"""Provider-first onboarding and shared credentials, with real admin API/DB."""

import os

import pytest

if not os.environ.get("TEST_DATABASE_URL"):
    pytest.skip("Isolated PostgreSQL required", allow_module_level=True)

from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.main import app

API = "/platform/v1alpha1/modelops"
ADMIN = AuthActor(username="connection-admin", actor_id="connection-admin", roles=["AI.Admin"])


def test_provider_can_exist_before_keys_and_models(client):
    app.dependency_overrides[get_actor] = lambda: ADMIN
    response = client.post(
        f"{API}/connections",
        json={
            "name": "QNU test server",
            "family": "custom",
            "base_url": "http://127.0.0.1:19999/v1",
        },
    )
    assert response.status_code == 201, response.text
    connection = response.json()
    assert connection["model_count"] == 0 and connection["total_keys_count"] == 0
    assert "secret" not in response.text
    models = client.get(f"{API}/connections/{connection['id']}/models")
    assert models.status_code == 200 and models.json() == []


SECRET = "sk-connection-test-only"


def connection(client, name="Test server", url="https://models.example/v1"):
    app.dependency_overrides[get_actor] = lambda: ADMIN
    r = client.post(f"{API}/connections", json={"name": name, "family": "custom", "base_url": url})
    assert r.status_code == 201, r.text
    return r.json()


def key(client, cid, secret=SECRET):
    r = client.post(f"{API}/providers/{cid}/keys", json={"name": "Test key", "secret": secret})
    assert r.status_code == 201, r.text
    return r.json()


def model(client, cid, name="test-chat", caps=None):
    r = client.post(
        f"{API}/connections/{cid}/models",
        json={
            "model_name": name,
            "capabilities": caps or ["chat"],
            "token_limits": {"context_window_tokens": 32768, "max_output_tokens": 2048},
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def workspace(client, providers):
    r = client.post(
        "/platform/v1alpha1/workspaces", json={"code": "connection-test", "name": "Connection test"}
    )
    assert r.status_code == 201, r.text
    wid = r.json()["id"]
    defaults = client.put(
        "/platform/v1alpha1/modelops/defaults", json={"chat_provider_id": providers[0]}
    )
    assert defaults.status_code == 200, defaults.text
    return wid


def test_key_and_discovery_precede_models_and_models_share_secret(client):
    import httpx

    from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient
    from qnu.domains.modelops.diagnostics.router import get_diagnostic_client
    from qnu.domains.modelops.public_api import resolve_chat_runtime
    from qnu.platform.database import AsyncSessionFactory

    provider = connection(client)
    cid = provider["id"]
    assert (
        client.post(
            f"{API}/connections/{cid}/models",
            json={"model_name": "test-chat", "capabilities": ["chat"]},
        ).status_code
        == 409
    )
    created = key(client, cid)
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"data": [{"id": "test-chat"}, {"id": "test-embed"}]})

    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(respond)
    )
    try:
        check = client.post(f"{API}/providers/{cid}/discover")
        assert check.status_code == 200 and check.json()["outcome"] == "ok", check.text
        assert requests[0].headers["authorization"] == "Bearer " + SECRET
        assert client.get(f"{API}/connections/{cid}/models").json() == []
    finally:
        app.dependency_overrides.pop(get_diagnostic_client, None)
    first = model(client, cid)
    second = model(client, cid, "other-chat")
    assert first["parent_id"] == cid and first["id"] != cid
    assert first["base_url"] == provider["base_url"]
    assert (
        client.post(
            f"{API}/connections/{cid}/models",
            json={"model_name": "test-chat", "capabilities": ["chat"]},
        ).status_code
        == 409
    )
    ws = workspace(client, [first["id"], second["id"]])

    async def run():
        async with AsyncSessionFactory() as db:
            one = await resolve_chat_runtime(db, ws, first["id"])
            two = await resolve_chat_runtime(db, ws, second["id"])
            assert one.api_key == two.api_key == SECRET

    client.portal.call(run)
    detail = client.get(f"{API}/connections/{cid}").json()
    assert detail["model_count"] == 2 and detail["active_keys_count"] == 1
    assert SECRET not in str(detail)
    assert created["model_ids"] is None


def test_connection_disabled_blocks_every_child_and_revoke_is_shared(client):
    from qnu.domains.modelops.public_api import resolve_chat_runtime
    from qnu.platform.database import AsyncSessionFactory
    from qnu.platform.errors import AppException

    c = connection(client)
    k = key(client, c["id"])
    m = model(client, c["id"])
    wid = workspace(client, [m["id"]])

    async def blocked(code):
        async with AsyncSessionFactory() as db:
            with pytest.raises(AppException) as error:
                await resolve_chat_runtime(db, wid, m["id"])
            assert error.value.code == code

    r = client.patch(
        f"{API}/connections/{c['id']}",
        json={
            "name": c["name"],
            "family": c["family"],
            "base_url": c["base_url"],
            "is_active": False,
        },
    )
    assert r.status_code == 200, r.text
    client.portal.call(blocked, "provider_inactive")
    client.patch(
        f"{API}/connections/{c['id']}",
        json={
            "name": c["name"],
            "family": c["family"],
            "base_url": c["base_url"],
            "is_active": True,
        },
    )
    r = client.request(
        "POST",
        f"{API}/providers/{c['id']}/keys/{k['id']}/revoke",
        json={"reason": "Synthetic revoke"},
    )
    assert r.status_code == 200, r.text
    client.portal.call(blocked, "chat_credentials_missing")


def test_key_on_one_connection_cannot_authorize_another(client):
    c = connection(client)
    key(client, c["id"])
    other = connection(client, "Other server", "https://other.example/v1")
    r = client.post(
        f"{API}/connections/{other['id']}/models",
        json={"model_name": "test-chat", "capabilities": ["chat"]},
    )
    assert r.status_code == 409 and r.json()["code"] == "connection_key_required"


def test_endpoint_edit_cannot_repoint_existing_model_or_embedding(client):
    c = connection(client)
    key(client, c["id"])
    m = model(client, c["id"])
    r = client.patch(
        f"{API}/connections/{c['id']}",
        json={"name": c["name"], "family": c["family"], "base_url": "https://different.example/v1"},
    )
    assert r.status_code == 409 and r.json()["code"] == "connection_endpoint_bound"
    r = client.patch(
        f"{API}/providers/{m['id']}", json={"base_url": "https://different.example/v1"}
    )
    assert r.status_code == 409 and r.json()["code"] == "model_connection_mismatch"


def test_non_admin_cannot_manage_connection(client):
    app.dependency_overrides[get_actor] = lambda: AuthActor(
        username="member", actor_id="member", roles=["staff"]
    )
    assert client.get(f"{API}/connections").status_code == 403
    assert (
        client.post(
            f"{API}/connections", json={"name": "Denied", "base_url": "https://models.example/v1"}
        ).status_code
        == 403
    )


def test_delete_referenced_model_reports_reference_type_and_keeps_defaults(client):
    c = connection(client)
    key(client, c["id"])
    first = model(client, c["id"], "guarded-first")
    second = model(client, c["id"], "guarded-second")
    workspace(client, [first["id"], second["id"]])

    blocked = client.delete(f"{API}/connections/{c['id']}/models/{first['id']}")
    assert blocked.status_code == 409, blocked.text
    body = blocked.json()
    assert body["code"] == "model_provider_in_use"
    assert "cấu hình mặc định hệ thống" in body["detail"]
    listed = {item["id"] for item in client.get(f"{API}/connections/{c['id']}/models").json()}
    assert listed == {first["id"], second["id"]}
    connection_blocked = client.delete(f"{API}/connections/{c['id']}")
    assert connection_blocked.status_code == 409
    assert connection_blocked.json()["code"] == "model_provider_in_use"

    moved = client.put(
        "/platform/v1alpha1/modelops/defaults", json={"chat_provider_id": second["id"]}
    )
    assert moved.status_code == 200, moved.text
    assert client.delete(f"{API}/connections/{c['id']}/models/{first['id']}").status_code == 204
    defaults = client.get("/platform/v1alpha1/modelops/defaults").json()
    assert defaults["chat_provider_id"] == second["id"]


def test_model_usage_history_blocks_deletion_and_is_retained(client):
    from qnu.domains.modelops.usage.service import usage_service
    from qnu.platform.database import AsyncSessionFactory

    c = connection(client)
    key(client, c["id"])
    m = model(client, c["id"], "guarded-history")
    wid = workspace(client, [m["id"]])

    async def reserve():
        async with AsyncSessionFactory() as db:
            return await usage_service.reserve(
                db, ADMIN, wid, "chat", "history-block", "a" * 64, 1000, m["id"]
            )

    client.portal.call(reserve)
    blocked = client.delete(f"{API}/connections/{c['id']}/models/{m['id']}")
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "model_provider_in_use"
    assert "lịch sử sử dụng model" in blocked.json()["detail"]
    assert client.get(f"{API}/connections/{c['id']}/models").json()


@pytest.mark.parametrize(
    ("api_type", "model_name"),
    [("ollama", "gpt-oss:120b"), ("llamacpp", "qwen3.8-27b-q4")],
)
def test_declared_local_runtimes_keep_their_chat_provider_type(client, api_type, model_name):
    app.dependency_overrides[get_actor] = lambda: ADMIN
    created = client.post(
        f"{API}/connections",
        json={
            "name": f"{api_type} dev",
            "family": "custom",
            "base_url": "http://127.0.0.1:18080/v1",
            "api_type": api_type,
        },
    )
    assert created.status_code == 201, created.text
    cid = created.json()["id"]
    key(client, cid)
    child = model(client, cid, name=model_name)
    assert child["provider_type"] == api_type
    assert child["capabilities"] == ["chat"]


def test_gemini_compatibility_does_not_append_a_second_v1(client):
    import httpx

    from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient
    from qnu.domains.modelops.diagnostics.router import get_diagnostic_client

    c = connection(client, "Gemini", "https://generativelanguage.googleapis.com/v1beta/openai")
    key(client, c["id"])
    seen = []

    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"data": [{"id": "gemini-test"}]})

    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(respond)
    )
    try:
        assert client.post(f"{API}/providers/{c['id']}/discover").json()["outcome"] == "ok"
    finally:
        app.dependency_overrides.pop(get_diagnostic_client, None)
    assert seen == ["https://generativelanguage.googleapis.com/v1beta/openai/models"]
    from qnu.adapters.providers.openai_compatible import completions_url

    assert completions_url(c["base_url"]) == c["base_url"] + "/chat/completions"


def test_conversion_preserves_old_model_ids_and_key_scope(client):
    import importlib.util
    from pathlib import Path

    from sqlalchemy import select

    from qnu.domains.modelops.models import Provider, ProviderKey
    from qnu.domains.modelops.public_api import _active_key
    from qnu.platform.database import AsyncSessionFactory, engine

    app.dependency_overrides[get_actor] = lambda: ADMIN
    children = []
    keys = []
    for number in range(2):
        r = client.post(
            f"{API}/providers",
            json={
                "name": f"Legacy {number}",
                "provider_type": "openai_compatible",
                "base_url": "https://legacy.example/v1",
                "model_name": f"legacy-{number}",
                "capabilities": ["chat"],
            },
        )
        assert r.status_code == 201, r.text
        child = r.json()
        children.append(child)
        keys.append(key(client, child["id"], f"sk-legacy-private-{number}"))
    migration_path = Path("alembic/versions/0005_provider_connections.py")
    spec = importlib.util.spec_from_file_location("connection_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    async def convert():
        async with engine.begin() as conn:
            await conn.run_sync(migration.convert_legacy_providers)
        async with AsyncSessionFactory() as db:
            rows = [await db.get(Provider, c["id"]) for c in children]
            assert rows[0].parent_id == rows[1].parent_id and rows[0].parent_id
            assert [r.model_name for r in rows] == ["legacy-0", "legacy-1"]
            for child, k in zip(rows, keys, strict=True):
                key_row = await db.get(ProviderKey, k["id"])
                assert key_row.provider_id == child.parent_id
                assert key_row.model_ids == [child.id]
                selected = await _active_key(db, child.id)
                assert selected.id == k["id"]
            roots = (
                await db.scalars(select(Provider).where(Provider.is_connection.is_(True)))
            ).all()
            assert len(roots) == 1

    client.portal.call(convert)
    cid = client.get(f"{API}/connections").json()[0]["id"]
    r = client.post(
        f"{API}/connections/{cid}/models",
        json={"model_name": "new-model", "capabilities": ["chat"]},
    )
    assert r.status_code == 409 and r.json()["code"] == "connection_key_required"
    key(client, cid)
    assert model(client, cid, "new-model")["parent_id"] == cid


def test_disabled_connection_prevents_child_diagnostic_egress(client):
    import httpx

    from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient
    from qnu.domains.modelops.diagnostics.router import get_diagnostic_client

    c = connection(client)
    key(client, c["id"])
    m = model(client, c["id"])
    r = client.patch(
        f"{API}/connections/{c['id']}",
        json={
            "name": c["name"],
            "family": c["family"],
            "base_url": c["base_url"],
            "is_active": False,
        },
    )
    assert r.status_code == 200
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [{"id": "test-chat"}]})

    app.dependency_overrides[get_diagnostic_client] = lambda: HttpProviderDiagnosticClient(
        transport=httpx.MockTransport(respond)
    )
    try:
        r = client.post(f"{API}/providers/{m['id']}/discover")
        assert r.status_code == 409 and r.json()["code"] == "provider_inactive"
        assert seen == []
    finally:
        app.dependency_overrides.pop(get_diagnostic_client, None)


def test_shared_key_lease_is_fenced_across_models(client):
    from qnu.domains.modelops.resilience.key_pool import acquire, finish
    from qnu.domains.modelops.resilience.schemas import ResiliencePolicy
    from qnu.platform.database import AsyncSessionFactory
    from qnu.platform.errors import AppException
    from qnu.ports.provider_execution import ProviderExecution

    c = connection(client)
    key(client, c["id"])
    first = model(client, c["id"], "lease-one")
    second = model(client, c["id"], "lease-two")
    wid = workspace(client, [first["id"], second["id"]])
    for child in (first, second):
        r = client.put(
            f"{API}/providers/{child['id']}/resilience",
            json=ResiliencePolicy(key_pool_enabled=True).model_dump(),
        )
        assert r.status_code == 200, r.text

    async def run():
        async with AsyncSessionFactory() as db:
            lease = await acquire(
                db,
                ProviderExecution(wid, first["id"]),
                "chat",
                c["base_url"],
                first["model_name"],
                5,
                set(),
            )
        async with AsyncSessionFactory() as db:
            with pytest.raises(AppException) as error:
                await acquire(
                    db,
                    ProviderExecution(wid, second["id"]),
                    "chat",
                    c["base_url"],
                    second["model_name"],
                    5,
                    set(),
                )
            assert error.value.code == "provider_keys_unavailable"
        async with AsyncSessionFactory() as db:
            await finish(
                db, lease, call_id="shared-lease", capability="chat", code="ok", success=True
            )
        async with AsyncSessionFactory() as db:
            next_lease = await acquire(
                db,
                ProviderExecution(wid, second["id"]),
                "chat",
                c["base_url"],
                second["model_name"],
                5,
                set(),
            )
            assert next_lease.key_id == lease.key_id
            assert next_lease.token != lease.token
        async with AsyncSessionFactory() as db:
            await finish(
                db, lease, call_id="stale-owner", capability="chat", code="ok", success=True
            )
        async with AsyncSessionFactory() as db:
            with pytest.raises(AppException) as error:
                await acquire(
                    db,
                    ProviderExecution(wid, first["id"]),
                    "chat",
                    c["base_url"],
                    first["model_name"],
                    5,
                    set(),
                )
            assert error.value.code == "provider_keys_unavailable"
        async with AsyncSessionFactory() as db:
            await finish(
                db, next_lease, call_id="next-owner", capability="chat", code="ok", success=True
            )

    client.portal.call(run)
