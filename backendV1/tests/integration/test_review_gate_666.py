# ruff: noqa: F811
"""Publication requires an explicit human acknowledgement of a source-pinned review."""

import copy
import hashlib

import pytest

from tests.integration.knowledge_support import PLATFORM, as_actor
from tests.integration.test_compiler_review_652 import prepared, review
from tests.integration.test_publication_646 import compiled, register  # noqa: F401


def target(client, data):
    data = {
        **data,
        "base": data["review_url"].split("/compilation-runs/")[0] + "/compiled-documents",
    }
    registered = register(client, data).json()
    return (
        data["base"]
        + "/"
        + registered["document"]["id"]
        + "/versions/"
        + registered["version"]["id"]
    )


def ack(client, url):
    result = client.get(url + "/review-gate")
    assert result.status_code == 200, result.text
    report = result.json()
    return {
        "review_id": report["review_id"],
        "report_sha256": report["report_sha256"],
        "confirmed_reviewed": True,
        "resolutions": [
            {
                "finding_id": item["finding_id"],
                "decision": "accepted_risk",
                "reason": "Reviewed synthetic fixture; explicit human decision.",
            }
            for item in report["findings"]
        ],
    }


def commit(client, url, preview, key="gate-approve"):
    body = preview.json()
    return client.post(
        url + "/decisions",
        json={"preview_id": body["id"], "preview_sha256": body["preview_sha256"]},
        headers={"Idempotency-Key": key},
    )


def test_approval_requires_review_acknowledgement(client, compiled):
    data = compiled
    registered = register(client, data).json()
    url = data["base"] + "/" + registered["document"]["id"]
    url += "/versions/" + registered["version"]["id"]
    as_actor(PLATFORM)
    result = client.post(url + "/decision-preview", json={"action": "approve", "reason": "Review"})
    assert result.status_code == 409, result.text
    assert result.json()["code"] == "publication_review_required"


def test_findings_require_explicit_human_resolutions_pinned_in_approval(client):
    with prepared(client) as (data, _chat):
        response = review(client, data)
        assert response.status_code == 200, response.text
        url = target(client, data)
        as_actor(PLATFORM)
        acknowledgement = ack(client, url)
        assert len(acknowledgement["resolutions"]) == 2
        body = {"action": "approve", "reason": "Human review", "review_ack": acknowledgement}
        preview = client.post(url + "/decision-preview", json=body)
        assert preview.status_code == 200, preview.text
        result = commit(client, url, preview)
        assert result.status_code == 200, result.text
        assert (
            result.json()["after"]["review_ack"]["report_sha256"]
            == acknowledgement["report_sha256"]
        )
        assert commit(client, url, preview).json()["id"] == result.json()["id"]
        publish = client.post(
            url + "/decision-preview", json={"action": "publish", "reason": "Publish approved"}
        )
        assert publish.status_code == 200, publish.text
        assert commit(client, url, publish, "gate-publish").status_code == 200


@pytest.mark.parametrize(
    "change,expected",
    [
        ("missing", 409),
        ("duplicate", 409),
        ("foreign", 409),
        ("hash", 409),
        ("unconfirmed", 422),
        ("claims_fixed", 422),
    ],
)
def test_review_ack_cannot_omit_forge_or_self_claim_a_fix(client, change, expected):
    with prepared(client) as (data, _chat):
        assert review(client, data).status_code == 200
        url = target(client, data)
        as_actor(PLATFORM)
        value = copy.deepcopy(ack(client, url))
        if change == "missing":
            value["resolutions"].pop()
        elif change == "duplicate":
            value["resolutions"].append(value["resolutions"][0])
        elif change == "foreign":
            value["review_id"] = "rvw_foreign"
        elif change == "hash":
            value["report_sha256"] = "0" * 64
        elif change == "unconfirmed":
            value["confirmed_reviewed"] = False
        else:
            value["resolutions"][0]["decision"] = "fixed"
        response = client.post(
            url + "/decision-preview",
            json={"action": "approve", "reason": "Human review", "review_ack": value},
        )
        assert response.status_code == expected, response.text
        assert client.get(url).json()["status"] == "draft"


def test_new_review_between_preview_and_commit_requires_new_ack(client):
    with prepared(client) as (data, _chat):
        assert review(client, data).status_code == 200
        url = target(client, data)
        as_actor(PLATFORM)
        preview = client.post(
            url + "/decision-preview",
            json={"action": "approve", "reason": "Human review", "review_ack": ack(client, url)},
        )
        assert preview.status_code == 200
        assert review(client, data, key="second-review").status_code == 200
        response = commit(client, url, preview)
        assert response.status_code == 409 and response.json()["code"] == "publication_review_stale"


def test_no_findings_still_requires_confirmation_and_uses_exact_report_hash(client):
    with prepared(client) as (data, chat):
        chat.mode = "no_issues"
        result = review(client, data)
        assert result.status_code == 200
        url = target(client, data)
        as_actor(PLATFORM)
        value = ack(client, url)
        assert value["resolutions"] == []
        raw = client.get(data["review_url"] + "/" + value["review_id"] + "/report").content
        assert value["report_sha256"] == hashlib.sha256(raw).hexdigest()
        missing = client.post(
            url + "/decision-preview", json={"action": "approve", "reason": "Human review"}
        )
        assert missing.status_code == 409
        response = client.post(
            url + "/decision-preview",
            json={"action": "approve", "reason": "Human review", "review_ack": value},
        )
        assert response.status_code == 200, response.text
