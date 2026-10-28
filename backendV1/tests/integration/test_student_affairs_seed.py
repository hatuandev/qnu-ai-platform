"""Real persisted seed, repeated execution, HTTP login and workspace isolation."""

import hashlib
import json

from qnu.domains.identity import dev_accounts
from scripts import seed_student_affairs as seed

PREFIX = "/platform/v1alpha1"


def test_seed_repeat_and_permissions(client, monkeypatch, tmp_path):
    registry = tmp_path / "accounts.json"
    registry.write_text(
        json.dumps(
            {
                name: hashlib.sha256((name + "-key").encode()).hexdigest()
                for name in dev_accounts.SEED_PROFILES
            }
        )
    )
    monkeypatch.setattr(dev_accounts, "ACCOUNTS_PATH", registry)
    first = client.portal.call(seed.seed_workspace)
    second = client.portal.call(seed.seed_workspace)
    assert first["workspace_id"] == second["workspace_id"]
    assert len(first["created"]) == 5
    assert second["created"] == []
    headers = {}
    for name in dev_accounts.SEED_PROFILES:
        response = client.post(PREFIX + "/auth/login", json={"access_key": name + "-key"})
        assert response.status_code == 200
        headers[name] = {"Authorization": "Bearer " + response.json()["access_token"]}
        workspaces = client.get(PREFIX + "/workspaces", headers=headers[name]).json()["items"]
        assert [item["id"] for item in workspaces] == [first["workspace_id"]]
    path = PREFIX + "/workspaces/" + first["workspace_id"]
    user = headers["ctsv.user"]
    admin = headers["ctsv.admin"]
    assert client.get(path + "/collections", headers=user).status_code == 200
    assert (
        client.post(path + "/collections", headers=user, json={"name": "Forbidden"}).status_code
        == 403
    )
    assert (
        client.post(
            path + "/collections",
            headers=headers["ctsv.editor"],
            json={"name": "Editor collection"},
        ).status_code
        == 201
    )
    assert client.get(path + "/events", headers=admin).status_code == 200
    assert client.get(path + "/events", headers=user).status_code == 403
    assert (
        client.post(path + "/members", headers=user, json={"actor_ref": "another-user"}).status_code
        == 403
    )
    assert (
        client.post(
            path + "/members", headers=admin, json={"actor_ref": "another-user"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            PREFIX + "/workspaces", headers=admin, json={"code": "forbidden", "name": "Forbidden"}
        ).status_code
        == 403
    )
    assert client.get(PREFIX + "/modelops/providers", headers=admin).status_code == 403
