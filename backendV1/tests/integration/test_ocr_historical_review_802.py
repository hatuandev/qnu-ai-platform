"""Explicit historical checks are read-only; the default optimistic lock remains."""

import pytest

from tests.integration.compiler_support import chat_provider, processed_input
from tests.integration.test_ocr_text_review_651 import FakeSpeller, edit_body, review_url, save


def test_explicit_original_check_keeps_latest_version_and_replays_without_resending(client):
    data = processed_input(client, code="history802")
    url = review_url(data)
    original = client.get(url).json()
    latest = save(client, url, edit_body(original, original["units"][0], "Bản đã sửa")).json()
    payload = {
        "source_version": 0,
        "expected_version": 0,
        "expected_sha256": original["canonical_sha256"],
        "evidence_ids": [original["units"][0]["evidence_id"]],
    }
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        response = client.post(
            url + "/checks", json=payload, headers={"Idempotency-Key": "history802"}
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["version"] == 0
        assert result["canonical_sha256"] == original["canonical_sha256"]
        replay = client.post(
            url + "/checks", json=payload, headers={"Idempotency-Key": "history802"}
        )
        assert replay.json()["id"] == result["id"]
        assert len(model.requests) == 1
    assert client.get(url).json()["version_id"] == latest["version_id"]
    assert client.get(url).json()["canonical_sha256"] == latest["canonical_sha256"]


@pytest.mark.parametrize(
    "source_version,expected_version,code",
    [
        (None, 0, "ocr_text_version_conflict"),
        (0, 1, "ocr_text_version_conflict"),
        (999, 0, "ocr_text_not_found"),
    ],
)
def test_source_selection_never_weakens_version_hash_or_missing_snapshot_checks(
    client,
    source_version,
    expected_version,
    code,
):
    data = processed_input(client, code="history802-conflict")
    url = review_url(data)
    original = client.get(url).json()
    save(client, url, edit_body(original, original["units"][0], "Bản đã sửa"))
    response = client.post(
        url + "/checks",
        json={
            "source_version": source_version,
            "expected_version": expected_version,
            "expected_sha256": original["canonical_sha256"],
            "evidence_ids": [original["units"][0]["evidence_id"]],
        },
        headers={"Idempotency-Key": "history802-conflict"},
    )
    assert response.status_code in {404, 409}, response.text
    assert response.json()["code"] == code
