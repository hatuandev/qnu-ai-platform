"""Real handler/storage/citation path; one controlled provider call per request."""

import json

import pytest

from tests.integration.test_answers_api_648 import ready as ready_fixture
from tests.integration.test_index_api_647 import indexed  # noqa: F401

ready = ready_fixture


@pytest.mark.parametrize("foreign", [False, True])
def test_partial_answer_contract_and_foreign_coverage_rejection(
    client, ready, monkeypatch, foreign
):
    chat = ready["answer_chat"]

    def respond(index):
        payload = json.loads(chat.requests[index]["body"]["messages"][-1]["content"])
        paragraph = next(e for e in payload["evidence"] if e["kind"] != "table")
        eid = paragraph["evidence_id"]
        value = {
            "status": "answered",
            "lookups": [],
            "statements": [{"text": paragraph["text"], "evidence_ids": [eid]}],
            "assessment": [
                {"label": "Quy định chung", "status": "covered", "evidence_ids": [eid]},
                {
                    "label": "Danh sách chi tiết",
                    "status": "missing",
                    "evidence_ids": ["E999"] if foreign else [eid],
                },
            ],
        }
        return 200, json.dumps(
            {
                "choices": [{"message": {"content": json.dumps(value)}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 190},
            }
        ).encode()

    monkeypatch.setattr(chat, "_respond", respond)
    result = client.post(
        ready["answer_url"], json={"question": "Nguồn nói gì?", "context_max_bytes": 32000}
    )
    assert len(chat.requests) == 1
    if foreign:
        assert result.status_code == 502 and result.json()["code"] == "answer_coverage_invalid"
        return
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "answered" and body["statements"]
    assert body["coverage"]["status"] == "partial"
    assert body["coverage"]["requirements"][1]["label"] == "Danh sách chi tiết"
    assert body["trace"]["coverage"]["version"] == "qnu.rag.coverage/v1"
    assert body["sources"] and all(s["publication_decision_id"] for s in body["sources"])


@pytest.mark.parametrize("abstain", [False, True])
def test_unused_coverage_witness_stays_in_the_revalidated_response(
    client, ready, monkeypatch, abstain
):
    chat = ready["answer_chat"]
    witnesses = []

    def respond(index):
        payload = json.loads(chat.requests[index]["body"]["messages"][-1]["content"])
        source = next(e for e in payload["evidence"] if e["kind"] != "table")
        witness = next(e for e in payload["evidence"] if e != source)
        witnesses.append(witness["evidence_id"])
        content = {
            "status": "insufficient_evidence" if abstain else "answered",
            "lookups": [],
            "statements": []
            if abstain
            else [{"text": source["text"], "evidence_ids": [source["evidence_id"]]}],
            "assessment": [
                {"label": "Missing detail", "status": "missing", "evidence_ids": witnesses}
            ],
        }
        return 200, json.dumps(
            {
                "choices": [{"message": {"content": json.dumps(content)}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 190},
            }
        ).encode()

    monkeypatch.setattr(chat, "_respond", respond)
    result = client.post(
        ready["answer_url"], json={"question": "Nguồn nói gì?", "context_max_bytes": 32000}
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert len(chat.requests) == 1
    assert set(witnesses) <= {s["evidence_id"] for s in body["sources"]}
    assert bool(body["statements"]) is not abstain
