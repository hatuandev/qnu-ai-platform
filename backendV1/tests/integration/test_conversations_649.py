"""Assistant binding, owned conversations and persisted multi-turn answering."""

import json

import pytest

from tests.integration.knowledge_support import API, EDITOR, MEMBER, PLATFORM, as_actor
from tests.integration.test_answers_api_648 import ready  # noqa: F401
from tests.integration.test_index_api_647 import indexed  # noqa: F401


def assistant_url(data):
    return f"{API}/workspaces/{data['workspace']['id']}/assistants"


def create_assistant(client, data):
    as_actor(PLATFORM)
    response = client.post(
        assistant_url(data),
        json={
            "name": "Trợ lý tuyển sinh",
            "description": "Trả lời có nguồn",
            "persona": "Giải thích ngắn gọn bằng tiếng Việt.",
            "collection_id": data["collection"]["id"],
            "chat_provider_id": data["chat_provider"]["id"],
        },
    )
    assert response.status_code == 201, response.text
    as_actor(EDITOR)
    return response.json()


def test_assistant_binding_and_owned_conversation_are_persistent(client, ready):  # noqa: F811
    assistant = create_assistant(client, ready)
    assert assistant["max_output_tokens"] is None
    base = f"{API}/workspaces/{ready['workspace']['id']}/conversations"
    response = client.post(base, json={"assistant_id": assistant["id"], "title": "Chỉ tiêu"})
    assert response.status_code == 201, response.text
    conversation = response.json()
    assert conversation["owner_ref"] == EDITOR.actor_id
    assert (
        client.get(base + "/" + conversation["id"]).json()["assistant_revision"]
        == assistant["revision"]
    )
    as_actor(MEMBER)
    assert client.get(base + "/" + conversation["id"]).status_code == 404


def test_assistant_explicit_budget_is_preserved_until_cleared(client, ready):  # noqa: F811
    as_actor(PLATFORM)
    body = {
        "name": "Budget fixture",
        "collection_id": ready["collection"]["id"],
        "chat_provider_id": ready["chat_provider"]["id"],
        "max_output_tokens": 777,
    }
    created = client.post(assistant_url(ready), json=body)
    assert created.status_code == 201, created.text
    assistant = created.json()
    path = assistant_url(ready) + "/" + assistant["id"]
    body.pop("max_output_tokens")
    updated = client.put(path, json={**body, "expected_revision": assistant["revision"]})
    assert updated.status_code == 200, updated.text
    assert updated.json()["max_output_tokens"] == 777
    automatic = client.put(path, json={
        **body, "max_output_tokens": None, "expected_revision": updated.json()["revision"],
    })
    assert automatic.status_code == 200, automatic.text
    assert automatic.json()["max_output_tokens"] is None


@pytest.fixture
def chat_session(client, ready):  # noqa: F811
    assistant = create_assistant(client, ready)
    base = f"{API}/workspaces/{ready['workspace']['id']}/conversations"
    response = client.post(base, json={"assistant_id": assistant["id"]})
    assert response.status_code == 201, response.text
    conversation = response.json()
    fake = ready["answer_chat"]
    original = fake._respond

    def respond(index):
        incoming = json.loads(fake.requests[index]["body"]["messages"][-1]["content"])
        if "previous_user_questions" in incoming:
            value = {
                "standalone_question": incoming["previous_user_questions"][-1]
                + " "
                + incoming["current_question"],
                "needs_clarification": fake.mode == "clarify",
            }
            if fake.mode == "rewrite_bad":
                value = {"unexpected": True}
            return 200, json.dumps(
                {
                    "choices": [
                        {"message": {"content": json.dumps(value)}, "finish_reason": "stop"}
                    ],
                    "usage": {"total_tokens": 80},
                }
            ).encode()
        return original(index)

    fake._respond = respond
    yield {
        **ready,
        "assistant": assistant,
        "conversation": conversation,
        "conversation_url": base + "/" + conversation["id"],
    }


def send(client, data, question="Chỉ tiêu trúng tuyển năm 2024?", *, seq=0, key="turn-one"):
    return client.post(
        data["conversation_url"] + "/turns",
        headers={"Idempotency-Key": key},
        json={"question": question, "expected_turn_no": seq},
    )


def test_saved_answer_replay_and_followup_use_new_evidence(client, chat_session):
    data = chat_session
    first = send(client, data)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "completed" and first.json()["result"]["sources"]
    assert first.json()["history_turn_ids"] == []
    assert data["answer_chat"].requests[0]["body"]["max_tokens"] > 0
    before = len(data["answer_chat"].requests)
    assert send(client, data).json()["id"] == first.json()["id"]
    assert len(data["answer_chat"].requests) == before
    second = send(client, data, "Còn năm 2023?", seq=1, key="turn-two")
    assert second.status_code == 200, second.text
    assert second.json()["history_turn_ids"] == [first.json()["id"]]
    assert second.json()["rewrite_trace"]["total_tokens"] == 80
    assert data["answer_chat"].requests[-2]["body"]["max_tokens"] == 8192
    assert second.json()["rewrite_trace"]["output_budget"]["mode"] == "automatic"
    assert len(data["answer_chat"].requests) == before + 2
    incoming = json.loads(data["answer_chat"].requests[-2]["body"]["messages"][-1]["content"])
    assert incoming["previous_user_questions"] == [first.json()["question"]]
    assert "150" not in json.dumps(incoming)
    listing = client.get(data["conversation_url"] + "/turns")
    assert listing.status_code == 200, listing.text
    assert [t["turn_no"] for t in listing.json()] == [1, 2]
    assert all(t["source_status"] == "current" and t["result"] for t in listing.json())
    assert listing.headers["cache-control"] == "private, no-store"


def test_key_conflict_and_sequence_conflict_never_call_model(client, chat_session):
    assert send(client, chat_session).status_code == 200
    count = len(chat_session["answer_chat"].requests)
    assert send(client, chat_session, "Different").json()["code"] == "idempotency_conflict"
    assert (
        send(client, chat_session, key="new-key").json()["code"] == "conversation_sequence_conflict"
    )
    assert len(chat_session["answer_chat"].requests) == count


@pytest.mark.parametrize(
    "mode,code,status",
    [
        ("http_error", "chat_provider_unavailable", 503),
        ("foreign_citation", "answer_citation_invalid", 502),
    ],
)
def test_failed_turn_is_persisted_and_not_resent(client, chat_session, mode, code, status):
    data = chat_session
    data["answer_chat"].mode = mode
    response = send(client, data)
    assert response.status_code == status, response.text
    assert response.json()["code"] == code
    before = len(data["answer_chat"].requests)
    assert send(client, data).json()["code"] == "conversation_turn_failed"
    assert len(data["answer_chat"].requests) == before
    result = client.get(data["conversation_url"] + "/turns").json()[0]
    assert (
        result["status"] == "failed" and result["error_code"] == code and result["result"] is None
    )


def test_old_source_content_is_hidden_after_withdrawal(client, chat_session):
    from tests.integration.test_index_api_647 import withdraw

    assert send(client, chat_session).status_code == 200
    withdraw(client, chat_session)
    response = client.get(chat_session["conversation_url"] + "/turns")
    assert response.status_code == 200, response.text
    assert (
        response.json()[0]["source_status"] == "unavailable"
        and response.json()[0]["result"] is None
    )
    assert send(client, chat_session).json()["code"] == "answer_evidence_changed"


@pytest.mark.parametrize(
    "mode,code",
    [
        ("clarify", "conversation_clarification_required"),
        ("rewrite_bad", "conversation_rewrite_invalid"),
    ],
)
def test_unclear_or_bad_rewrite_never_reaches_answer(client, chat_session, mode, code):
    assert send(client, chat_session).status_code == 200
    chat_session["answer_chat"].mode = mode
    before = len(chat_session["answer_chat"].requests)
    response = send(client, chat_session, "Còn bên kia?", seq=1, key="second")
    assert response.status_code >= 400, response.text
    assert response.json()["code"] == code
    assert len(chat_session["answer_chat"].requests) == before + 1


def test_conversation_owner_is_not_bypassed_by_platform_admin(client, chat_session):
    as_actor(PLATFORM)
    assert client.get(chat_session["conversation_url"]).status_code == 404
    assert send(client, chat_session).status_code == 404
    assert client.get(chat_session["conversation_url"] + "/turns").status_code == 404


def test_assistant_revision_change_blocks_existing_conversation(client, chat_session):
    data = chat_session
    as_actor(PLATFORM)
    body = {
        k: data["assistant"][k]
        for k in (
            "name",
            "description",
            "persona",
            "collection_id",
            "chat_provider_id",
            "top_k",
            "history_turns",
            "max_output_tokens",
            "is_active",
        )
    }
    body.update(expected_revision=1, persona="Trả lời lịch sự.")
    response = client.put(assistant_url(data) + "/" + data["assistant"]["id"], json=body)
    assert response.status_code == 200, response.text
    assert (
        client.put(assistant_url(data) + "/" + data["assistant"]["id"], json=body).status_code
        == 409
    )
    as_actor(EDITOR)
    assert send(client, data).json()["code"] == "conversation_assistant_changed"
    assert not data["answer_chat"].requests


def test_concurrent_turn_is_rejected_while_first_is_running(client, chat_session, monkeypatch):
    import asyncio
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from qnu.main import app

    started = threading.Event()
    original = app.state.container.chat_model

    class SlowChat:
        async def complete(self, messages, request):
            started.set()
            await asyncio.sleep(0.5)
            return await original.complete(messages, request)

    monkeypatch.setattr(app.state.container, "chat_model", SlowChat())
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(send, client, chat_session)
        assert started.wait(10)
        second = send(client, chat_session, key="parallel")
        assert second.status_code == 409 and second.json()["code"] == "conversation_busy"
        result = first.result(timeout=20)
        assert result.status_code == 200, result.text


def test_expired_turn_becomes_uncertain_without_resend(client, chat_session):
    from datetime import timedelta

    from qnu.domains.conversations.schemas import TurnRequest
    from qnu.domains.conversations.service import reserve_turn
    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.platform.database import AsyncSessionFactory

    async def reserve():
        async with AsyncSessionFactory() as db:
            _, turn, _ = await reserve_turn(
                db,
                EDITOR,
                chat_session["workspace"]["id"],
                chat_session["conversation"]["id"],
                TurnRequest(question="Q", expected_turn_no=0),
                "dead",
            )
            turn.lease_expires_at = utcnow() - timedelta(seconds=10)
            await db.commit()
            return turn.id

    turn_id = client.portal.call(reserve)
    response = client.get(chat_session["conversation_url"] + "/turns/" + turn_id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "uncertain"
    assert (
        send(client, chat_session, "Q", key="dead").json()["code"] == "conversation_turn_uncertain"
    )
    assert not chat_session["answer_chat"].requests


@pytest.mark.parametrize(
    "change,code",
    [
        ("assistant", "conversation_assistant_changed"),
        ("archive", "conversation_archived"),
        ("membership", "workspace_not_found"),
    ],
)
def test_changes_during_generation_discard_persisted_answer(
    client, chat_session, monkeypatch, change, code
):
    from sqlalchemy import update

    from qnu.domains.assistants.models import Assistant
    from qnu.domains.conversations.models import Conversation
    from qnu.domains.workspaces.models import WorkspaceMember
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    original = app.state.container.chat_model

    class ChangeDuringChat:
        async def complete(self, messages, request):
            result = await original.complete(messages, request)
            async with AsyncSessionFactory() as db:
                if change == "assistant":
                    await db.execute(
                        update(Assistant)
                        .where(Assistant.id == chat_session["assistant"]["id"])
                        .values(revision=2)
                    )
                elif change == "archive":
                    await db.execute(
                        update(Conversation)
                        .where(Conversation.id == chat_session["conversation"]["id"])
                        .values(status="archived")
                    )
                else:
                    await db.execute(
                        update(WorkspaceMember)
                        .where(
                            WorkspaceMember.workspace_id == chat_session["workspace"]["id"],
                            WorkspaceMember.actor_ref == EDITOR.actor_id,
                        )
                        .values(status="revoked")
                    )
                await db.commit()
            return result

    monkeypatch.setattr(app.state.container, "chat_model", ChangeDuringChat())
    response = send(client, chat_session)
    assert response.status_code >= 400, response.text
    assert response.json()["code"] == code


def test_history_limit_blocks_rewrite_without_extra_model_call(client, chat_session, monkeypatch):
    from qnu.platform.config import get_settings

    assert send(client, chat_session, "Q" * 1500).status_code == 200
    monkeypatch.setattr(get_settings(), "CONVERSATION_HISTORY_MAX_BYTES", 1024)
    count = len(chat_session["answer_chat"].requests)
    response = send(client, chat_session, "Follow up?", seq=1, key="second")
    assert response.status_code == 422 and response.json()["code"] == "conversation_history_limit"
    assert len(chat_session["answer_chat"].requests) == count


def test_assistant_admin_and_collection_scope_enforced(client, chat_session):
    data = chat_session
    payload = {k: data["assistant"][k] for k in ("name", "collection_id", "chat_provider_id")}
    as_actor(EDITOR)
    assert client.post(assistant_url(data), json=payload).status_code == 403
    as_actor(PLATFORM)
    assert (
        client.post(assistant_url(data), json={**payload, "collection_id": "foreign"}).status_code
        == 404
    )
    as_actor(EDITOR)
    base = f"{API}/workspaces/{data['workspace']['id']}/conversations"
    assert (
        client.post(
            base,
            json={"assistant_id": data["assistant"]["id"], "document_ids": ["foreign-document"]},
        ).status_code
        == 404
    )
