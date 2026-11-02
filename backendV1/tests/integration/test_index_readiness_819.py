# ruff: noqa: F811
"""Real handler/SQL/manifest checks; model fixtures are synthetic, not live acceptance."""

from tests.integration.index_support import execute_index
from tests.integration.knowledge_support import API, MEMBER, as_actor
from tests.integration.test_index_api_647 import indexed, withdraw  # noqa: F401


def test_readiness_tracks_binding_and_withdrawal_without_embedding(client, indexed):
    data = indexed
    url = data["document_url"] + "/index-readiness"
    assert client.get(url).json()["status"] == "not_indexed"
    assert execute_index(client, data["index_run"]["id"]) == "completed"
    before = len(data["embedding"].requests)
    response = client.get(url)
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["status"] == "ready"
    assert value["version_id"] == data["compiled"]["version"]["id"]
    assert value["bundle_sha256"] == data["compiled"]["version"]["bundle_sha256"]
    assert response.headers["cache-control"] == "private, no-store"
    withdraw(client, data)
    assert client.get(url).json()["status"] == "unavailable"
    assert len(data["embedding"].requests) == before


def test_readiness_rejects_other_workspace_or_missing_document(client, indexed):
    data = indexed
    missing = data["base"] + "/compiled-documents/missing/index-readiness"
    assert client.get(missing).status_code == 404
    as_actor(MEMBER)
    other = f"{API}/workspaces/not-granted/collections/{data['collection']['id']}/compiled-documents/{data['compiled']['document']['id']}/index-readiness"
    assert client.get(other).status_code in (403, 404)
