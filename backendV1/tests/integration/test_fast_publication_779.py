# ruff: noqa: F811
"""Fast approval is explicit, source-pinned and authorized; review stays the default."""

import pytest

from tests.integration.knowledge_support import EDITOR, OUTSIDER, PLATFORM, as_actor
from tests.integration.test_publication_646 import compiled, register  # noqa: F401


def setup_target(client, data):
    row = register(client, data).json()
    url = data["base"] + "/" + row["document"]["id"] + "/versions/" + row["version"]["id"]
    as_actor(PLATFORM)
    target = client.get(url).json()
    body = {
        "action": "approve",
        "reason": "Operator explicitly skips AI review for this version.",
        "review_skip": {
            "confirmed_skip": True,
            "version_id": target["id"],
            "bundle_sha256": target["bundle_sha256"],
        },
    }
    return url, body


def commit(client, url, preview, key):
    return client.post(
        url + "/decisions",
        headers={"Idempotency-Key": key},
        json={"preview_id": preview["id"], "preview_sha256": preview["preview_sha256"]},
    )


def test_skip_is_audited_and_can_publish_without_creating_a_review(client, compiled):
    url, body = setup_target(client, compiled)
    assert (
        client.post(
            url + "/decision-preview", json={"action": "approve", "reason": "Default"}
        ).status_code
        == 409
    )
    preview = client.post(url + "/decision-preview", json=body)
    assert preview.status_code == 200, preview.text
    saved = preview.json()["review_ack"]
    assert saved["mode"] == "skipped" and "review_id" not in saved
    assert saved["bundle_sha256"] == body["review_skip"]["bundle_sha256"]
    approved = commit(client, url, preview.json(), "fast-approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["after"]["review_ack"] == saved
    assert commit(client, url, preview.json(), "fast-approve").json()["id"] == approved.json()["id"]
    publish = client.post(
        url + "/decision-preview",
        json={"action": "publish", "reason": "Publish explicitly approved version"},
    )
    assert publish.status_code == 200, publish.text
    assert commit(client, url, publish.json(), "fast-publish").status_code == 200
    assert client.get(url).json()["status"] == "published"
    review_url = (
        compiled["base"].replace("compiled-documents", "compilation-runs")
        + "/"
        + compiled["run_id"]
        + "/reviews"
    )
    assert client.get(review_url).json() == []


@pytest.mark.parametrize(
    "change,status",
    [("hash", 409), ("version", 409), ("unconfirmed", 422), ("short", 422), ("publish", 422)],
)
def test_skip_cannot_forge_binding_or_skip_confirmation(client, compiled, change, status):
    url, body = setup_target(client, compiled)
    if change == "hash":
        body["review_skip"]["bundle_sha256"] = "0" * 64
    elif change == "version":
        body["review_skip"]["version_id"] = "another"
    elif change == "unconfirmed":
        body["review_skip"]["confirmed_skip"] = False
    elif change == "short":
        body["reason"] = "short"
    else:
        body["action"] = "publish"
    result = client.post(url + "/decision-preview", json=body)
    assert result.status_code == status, result.text
    assert client.get(url).json()["status"] == "draft"


@pytest.mark.parametrize("actor", [EDITOR, OUTSIDER])
def test_skip_does_not_grant_approval_permissions(client, compiled, actor):
    url, body = setup_target(client, compiled)
    as_actor(actor)
    assert client.post(url + "/decision-preview", json=body).status_code in (403, 404)


def test_skip_preview_is_bound_to_its_original_bytes(client, compiled):
    url, body = setup_target(client, compiled)
    preview = client.post(url + "/decision-preview", json=body).json()
    preview["preview_sha256"] = "0" * 64
    result = commit(client, url, preview, "tampered-fast")
    assert result.status_code == 409, result.text
    assert client.get(url).json()["status"] == "draft"
