"""Model capacity registration persists real limits without a global token ceiling."""

import pytest

from qnu.domains.modelops.public_api import plan_model_request, resolve_model_capacity
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException
from tests.integration.test_workspace_model_boundaries import setup_policy
from tests.integration.test_workspaces_modelops_api import API, MEMBER_A, OUTSIDER, PLATFORM, _as

URL = f"{API}/modelops/providers"
LIMITS = {"context_window_tokens": 1048576, "max_output_tokens": 65536}


def create_model(client, *, limits=None):
    _as(PLATFORM)
    body = {
        "name": "Large synthetic model",
        "provider_type": "openai_compatible",
        "base_url": "https://capacity.example.test/v1",
        "model_name": "synthetic-large",
        "capabilities": ["chat", "ocr"],
    }
    if limits is not None:
        body["token_limits"] = limits
    response = client.post(URL, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_capacity_above_old_global_defaults_persists_and_roundtrips(client):
    created = create_model(client, limits=LIMITS)
    detail = client.get(f"{URL}/{created['id']}").json()
    assert detail["token_limits"]["context_window_tokens"] == 1048576
    assert detail["token_limits"]["max_output_tokens"] == 65536
    assert detail["capacity_status"] == "configured"
    assert detail["capacity_basis"] == "operator_configured"


def test_unconfigured_capacity_stays_unknown_instead_of_assuming_8192(client):
    created = create_model(client)
    assert created["token_limits"] is None
    assert created["capacity_status"] == "unknown"


def test_endpoint_change_invalidates_capacity_until_explicit_reconfiguration(client):
    created = create_model(client, limits=LIMITS)
    url = f"{URL}/{created['id']}"
    changed = client.patch(url, json={"base_url": "https://new.example.test/v1"})
    assert changed.status_code == 200
    assert changed.json()["token_limits"] is None
    assert changed.json()["capacity_status"] == "stale"
    configured = client.patch(url, json={"token_limits": LIMITS})
    assert configured.status_code == 200
    assert configured.json()["capacity_status"] == "configured"


def test_model_change_cannot_reuse_previous_capacity_even_if_name_changed_back(client):
    created = create_model(client, limits=LIMITS)
    url = f"{URL}/{created['id']}"
    assert (
        client.patch(url, json={"model_name": "other-model"}).json()["capacity_status"] == "stale"
    )
    assert (
        client.patch(url, json={"model_name": "synthetic-large"}).json()["capacity_status"]
        == "stale"
    )


def test_unrelated_patch_preserves_limits_and_explicit_null_clears_them(client):
    created = create_model(client, limits=LIMITS)
    url = f"{URL}/{created['id']}"
    changed = client.patch(
        url, json={"timeout_seconds": 120, "base_url": created["base_url"] + "/"}
    )
    assert changed.json()["token_limits"]["context_window_tokens"] == 1048576
    assert changed.json()["capacity_status"] == "configured"
    cleared = client.patch(url, json={"token_limits": None})
    assert cleared.json()["token_limits"] is None
    assert cleared.json()["capacity_status"] == "unknown"


@pytest.mark.parametrize(
    "limits",
    [
        {"context_window_tokens": -1},
        {"context_window_tokens": 32768, "max_output_tokens": 32769},
        {"context_window_tokens": 32768, "basis": "provider_reported"},
    ],
)
def test_invalid_capacity_patch_leaves_saved_profile_unchanged(client, limits):
    created = create_model(client, limits=LIMITS)
    url = f"{URL}/{created['id']}"
    response = client.patch(url, json={"token_limits": limits})
    assert response.status_code == 422
    assert client.get(url).json()["token_limits"] == created["token_limits"]


def test_public_runtime_budget_resolves_workspace_and_rechecks_provider(client):
    ws, provider = setup_policy(client)
    _as(PLATFORM)
    url = f"{URL}/{provider['id']}"
    assert client.patch(url, json={"token_limits": LIMITS}).status_code == 200

    async def budget(actor=MEMBER_A):
        async with AsyncSessionFactory() as db:
            return await plan_model_request(db, actor, ws["id"], "chat", input_tokens=900000)

    snapshot, planned = client.portal.call(budget)
    assert snapshot.provider_id == provider["id"] and planned.max_output_tokens == 65536
    assert len(snapshot.configuration_hash) == 64
    with pytest.raises(AppException) as outsider:
        client.portal.call(budget, OUTSIDER)
    assert outsider.value.status_code == 404
    assert client.patch(url, json={"is_active": False}).status_code == 200
    with pytest.raises(AppException) as disabled:
        client.portal.call(budget)
    assert disabled.value.code == "provider_inactive"


def test_runtime_capacity_requires_configuration_and_rejects_stale_binding(client):
    ws, provider = setup_policy(client)
    _as(PLATFORM)
    url = f"{URL}/{provider['id']}"

    async def resolve():
        async with AsyncSessionFactory() as db:
            return await resolve_model_capacity(db, MEMBER_A, ws["id"], "chat")

    with pytest.raises(AppException) as unknown:
        client.portal.call(resolve)
    assert unknown.value.code == "model_capacity_required"
    assert client.patch(url, json={"token_limits": LIMITS}).status_code == 200
    first = client.portal.call(resolve)
    assert (
        client.patch(url, json={"token_limits": {"context_window_tokens": 2000000}}).status_code
        == 200
    )
    assert client.portal.call(resolve).configuration_hash != first.configuration_hash
    assert client.patch(url, json={"base_url": "https://other.example.test/v1"}).status_code == 200
    with pytest.raises(AppException) as stale:
        client.portal.call(resolve)
    assert stale.value.code == "model_token_limits_stale"
