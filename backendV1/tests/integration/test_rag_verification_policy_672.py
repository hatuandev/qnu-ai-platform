"""Judge failure boundaries and assistant policy reach the real HTTP answer pipeline."""

import json

import pytest

from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.test_answers_api_648 import ask
from tests.integration.test_answers_api_648 import ready as ready_fixture
from tests.integration.test_conversations_649 import create_assistant
from tests.integration.test_hybrid_655 import FakeRerank, setup_rerank
from tests.integration.test_index_api_647 import indexed, withdraw  # noqa: F401

ready = ready_fixture


def judging(data, outcome="supported"):
    fake = data["answer_chat"]
    original = fake._respond

    def respond(index):
        incoming = json.loads(fake.requests[index]["body"]["messages"][-1]["content"])
        if "statements" not in incoming:
            return original(index)
        if outcome == "http_error":
            return 503, b'{"error":"judge unavailable"}'
        if outcome == "withdraw":
            withdraw(data["client"], data)
        source = next(
            s
            for s in incoming["evidence"]
            if "150" in json.dumps(s.get("rows") or s.get("texts"), ensure_ascii=False)
        )
        # The extractive statement includes its field/header (which can contain a
        # year). A supported fake judge must quote those numbers too, not only
        # the value "150"; production correctly rejects such an incomplete proof.
        texts = [cell for row in source.get("rows", []) for cell in row if cell.strip()] or source[
            "texts"
        ]
        assert len(texts) <= 20
        value = {
            "findings": [
                {
                    "statement_index": s["statement_index"],
                    "status": outcome
                    if outcome in {"supported", "unsupported", "uncertain"}
                    else "supported",
                    "reason": "Controlled judge fixture.",
                    "quotes": [{"evidence_id": source["id"], "quote": text} for text in texts],
                }
                for s in incoming["statements"]
            ]
        }
        if outcome == "bad_quote":
            value["findings"][0]["quotes"][0]["quote"] = "invented quote"
        if outcome == "missing":
            value["findings"] = []
        return 200, json.dumps(
            {
                "choices": [{"message": {"content": json.dumps(value)}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 71},
            }
        ).encode()

    fake._respond = respond


@pytest.mark.parametrize(
    "mode,outcome,status,reason",
    [
        ("observe", "supported", "answered", None),
        ("observe", "unsupported", "answered", None),
        ("enforce", "supported", "answered", None),
        ("enforce", "unsupported", "insufficient_evidence", "answer_not_supported"),
        ("enforce", "uncertain", "insufficient_evidence", "answer_verification_uncertain"),
    ],
)
def test_verification_mode_controls_release_without_silently_rewriting(
    client, ready, mode, outcome, status, reason
):
    judging(ready, outcome)
    response = ask(client, ready, verification_mode=mode)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == status and body["reason"] == reason
    assert body["trace"]["verification"]["status"] == outcome
    assert body["trace"]["verification"]["total_tokens"] == 71
    assert len(ready["answer_chat"].requests) == 2
    assert ready["answer_chat"].requests[-1]["body"]["max_tokens"] == 8192
    assert body["trace"]["verification"]["output_budget"]["mode"] == "automatic"
    if status == "answered":
        assert "150" in body["answer"]
    else:
        assert body["answer"] is None and body["statements"] == [] and body["sources"]


@pytest.mark.parametrize("outcome", ["http_error", "bad_quote", "missing", "withdraw"])
def test_judge_and_source_failures_are_errors_even_in_observe_mode(client, ready, outcome):
    judging({**ready, "client": client}, outcome)
    response = ask(client, ready, verification_mode="observe")
    assert response.status_code >= 400, response.text
    if outcome in {"bad_quote", "missing"}:
        assert response.json()["code"] == "answer_verification_invalid"
    if outcome == "withdraw":
        assert response.json()["code"] in {"answer_evidence_changed", "index_outdated"}
    assert "status" not in response.json() or response.json()["status"] != "insufficient_evidence"


def test_assistant_chat_uses_persisted_hybrid_rerank_policy_and_checks_provider_access(
    client, ready
):
    data = ready
    with FakeRerank() as rerank:
        rerank_id = setup_rerank(client, data, rerank.base_url)
        as_actor(PLATFORM)
        allow = client.put(
            f"{API}/workspaces/{data['workspace']['id']}/allowed-providers",
            json={
                "provider_ids": [
                    data["ocr_provider"]["id"],
                    data["embedding_provider"]["id"],
                    data["chat_provider"]["id"],
                    rerank_id,
                ],
                "defaults": {
                    "ocr": data["ocr_provider"]["id"],
                    "embedding": data["embedding_provider"]["id"],
                    "chat": data["chat_provider"]["id"],
                    "rerank": rerank_id,
                },
            },
        )
        assert allow.status_code == 200, allow.text
        payload = {
            "name": "Hybrid",
            "collection_id": data["collection"]["id"],
            "chat_provider_id": data["chat_provider"]["id"],
            "top_k": 1,
            "rag_policy": {
                "retrieval_mode": "hybrid_rerank",
                "candidate_k": 10,
                "rerank_provider_id": rerank_id,
                "context_window": 1,
            },
        }
        url = f"{API}/workspaces/{data['workspace']['id']}/assistants"
        created = client.post(url, json=payload)
        assert created.status_code == 201, created.text
        assert created.json()["rag_policy"]["retrieval_mode"] == "hybrid_rerank"
        denied = client.post(
            url,
            json={
                **payload,
                "rag_policy": {**payload["rag_policy"], "rerank_provider_id": "foreign"},
            },
        )
        assert denied.status_code == 404, denied.text
        as_actor(EDITOR)
        base = f"{API}/workspaces/{data['workspace']['id']}/conversations"
        conversation = client.post(base, json={"assistant_id": created.json()["id"]})
        assert conversation.status_code == 201, conversation.text
        turn = client.post(
            base + "/" + conversation.json()["id"] + "/turns",
            headers={"Idempotency-Key": "turn"},
            json={"question": "Chỉ tiêu là bao nhiêu?", "expected_turn_no": 0},
        )
        assert turn.status_code == 200, turn.text
        trace = turn.json()["result"]["trace"]
        assert trace["retrieval"]["mode"] == "hybrid_rerank" and trace["context"]["window"] == 1
        assert rerank.requests
        as_actor(PLATFORM)
        updated = client.put(
            url + "/" + created.json()["id"],
            json={
                **{k: v for k, v in payload.items() if k != "rag_policy"},
                "name": "Renamed",
                "expected_revision": created.json()["revision"],
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["rag_policy"] == created.json()["rag_policy"]
        assert updated.json()["revision"] == created.json()["revision"] + 1
        incompatible = client.put(
            url + "/" + created.json()["id"],
            json={
                **{k: v for k, v in payload.items() if k != "rag_policy"},
                "top_k": 20,
                "expected_revision": updated.json()["revision"],
            },
        )
        assert (
            incompatible.status_code == 422
            and incompatible.json()["code"] == "assistant_rag_policy_invalid"
        )
        as_actor(EDITOR)
        stale = client.post(
            base + "/" + conversation.json()["id"] + "/turns",
            headers={"Idempotency-Key": "stale"},
            json={"question": "Tiếp tục", "expected_turn_no": 1},
        )
        assert stale.status_code == 409 and stale.json()["code"] == "conversation_assistant_changed"


def test_turn_scope_is_pinned_and_inherited_without_promoting_history_answers_to_evidence(
    client, ready
):

    from qnu.platform.database import AsyncSessionFactory

    assistant = create_assistant(client, ready)
    base = f"{API}/workspaces/{ready['workspace']['id']}/conversations"
    conversation = client.post(base, json={"assistant_id": assistant["id"]}).json()
    turns = base + "/" + conversation["id"] + "/turns"
    response = client.post(
        turns,
        headers={"Idempotency-Key": "one"},
        json={
            "question": "Năm 2024",
            "expected_turn_no": 0,
            "metadata_filter": {"data_year": 2024},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["metadata_filter"]["data_year"] == 2024
    # The routing call runs, but no source-grounded answer may use unannotated content.
    assert response.json()["result"]["status"] == "insufficient_evidence"
    replay = client.post(
        turns,
        headers={"Idempotency-Key": "one"},
        json={
            "question": "Năm 2024",
            "expected_turn_no": 0,
            "metadata_filter": {"data_year": 2025},
        },
    )
    assert replay.status_code == 409
    # Inspect reservation directly to isolate scope inheritance from rewrite quality.
    from qnu.domains.conversations.schemas import TurnRequest
    from qnu.domains.conversations.service import reserve_turn

    async def reserve():
        async with AsyncSessionFactory() as db:
            _, row, _ = await reserve_turn(
                db,
                EDITOR,
                ready["workspace"]["id"],
                conversation["id"],
                TurnRequest(question="Giải thích thêm", expected_turn_no=1),
                "two",
            )
            assert row.metadata_filter == {"data_year": 2024}

    client.portal.call(reserve)
