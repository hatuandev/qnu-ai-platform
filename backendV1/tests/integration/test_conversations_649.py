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
            "rag_policy": {"retrieval_mode": "dense"},
        },
    )
    assert response.status_code == 201, response.text
    as_actor(EDITOR)
    return response.json()


def test_assistant_binding_and_owned_conversation_are_persistent(client, ready):  # noqa: F811
    assistant = create_assistant(client, ready)
    assert assistant["max_output_tokens"] is None
    assert assistant["rag_policy"]["context_window"] == 1
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
        "rag_policy": {"context_window": 0},
    }
    created = client.post(assistant_url(ready), json=body)
    assert created.status_code == 201, created.text
    assistant = created.json()
    path = assistant_url(ready) + "/" + assistant["id"]
    body.pop("max_output_tokens")
    body.pop("rag_policy")
    updated = client.put(path, json={**body, "expected_revision": assistant["revision"]})
    assert updated.status_code == 200, updated.text
    assert updated.json()["max_output_tokens"] == 777
    assert updated.json()["rag_policy"]["context_window"] == 0
    automatic = client.put(
        path,
        json={
            **body,
            "max_output_tokens": None,
            "expected_revision": updated.json()["revision"],
        },
    )
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
            if fake.mode == "http_error":
                return 503, b'{"error":"unavailable"}'
            route = getattr(fake, "intent_route", "knowledge")
            previous = incoming["previous_user_questions"]
            value = {
                "route": route,
                "answer": getattr(fake, "direct_answer", "Phản hồi từ model thử nghiệm.")
                if route != "knowledge"
                else None,
                "standalone_question": getattr(
                    fake,
                    "standalone_override",
                    (previous[-1] + " " if previous else "") + incoming["current_question"],
                ),
                "needs_clarification": fake.mode == "clarify" or getattr(
                    fake, "require_clarification", False
                ),
            }
            if fake.mode == "rewrite_bad":
                value = {"unexpected": True}
            return 200, json.dumps(
                {
                    "choices": [
                        {
                            "message": {"content": json.dumps(value)},
                            "finish_reason": "length" if fake.mode == "route_truncated" else "stop",
                        }
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
    earlier_answer = first.json()["result"]["answer"].strip()
    assert incoming["previous_assistant_answers"] == [earlier_answer[:600]]
    assert "revision_id" not in json.dumps(incoming)
    listing = client.get(data["conversation_url"] + "/turns")
    assert listing.status_code == 200, listing.text
    assert [t["turn_no"] for t in listing.json()] == [1, 2]
    assert all(t["source_status"] == "current" and t["result"] for t in listing.json())
    assert listing.headers["cache-control"] == "private, no-store"


def test_first_knowledge_turn_preserves_original_query_when_model_rewrites_it(client, chat_session):
    chat_session["answer_chat"].standalone_override = "Chỉ tiêu là gì?"
    question = "Cho tôi biết chỉ tiêu năm 2024"
    response = send(client, chat_session, question)
    assert response.status_code == 200, response.text
    assert response.json()["resolved_question"] == question


@pytest.mark.parametrize("route", ["greeting", "courtesy", "identity", "protected_request"])
def test_social_reply_comes_from_model_once_and_stays_out_of_retrieval_evidence(
    client, chat_session, route
):
    data = chat_session
    fake = data["answer_chat"]
    fake.intent_route = route
    fake.direct_answer = "Đây là lời đáp riêng do model sinh, không lấy từ câu mẫu."
    before = len(data["answer_chat"].requests)
    embeddings_before = len(data["embedding"].requests)
    first = send(client, data, "Dạ, xin chào trợ lý ạ!")
    assert first.status_code == 200, first.text
    reply = first.json()
    assert reply["result"]["status"] == "direct_reply"
    assert reply["result"]["route"] == route
    assert reply["result"]["answer"] == fake.direct_answer
    trace = reply["rewrite_trace"]
    assert trace["route"] == route and trace["total_tokens"] == 80
    assert trace["provider_id"] == data["chat_provider"]["id"]
    body = fake.requests[-1]["body"]
    assert data["assistant"]["persona"] in body["messages"][0]["content"]
    assert data["assistant"]["name"] in body["messages"][0]["content"]
    assert body["response_format"]["type"] == "json_schema"
    assert send(client, data, "Dạ, xin chào trợ lý ạ!").json() == reply
    assert len(fake.requests) == before + 1
    assert len(data["embedding"].requests) == embeddings_before
    fake.intent_route = "knowledge"
    question = send(client, data, "Xin chào, chỉ tiêu trúng tuyển năm 2024?", seq=1, key="turn-two")
    assert question.status_code == 200, question.text
    assert question.json()["result"]["sources"]
    assert question.json()["history_turn_ids"] == [reply["id"]]
    assert len(fake.requests) == before + 3
    route_payload = json.loads(fake.requests[-2]["body"]["messages"][-1]["content"])
    assert route_payload["previous_user_questions"] == ["Dạ, xin chào trợ lý ạ!"]
    assert route_payload["previous_assistant_answers"] == [fake.direct_answer]
    answer_payload = fake.requests[-1]["body"]["messages"]
    assert all(fake.direct_answer not in message["content"] for message in answer_payload)


@pytest.mark.parametrize(
    "mode,code",
    [
        ("http_error", "chat_provider_unavailable"),
        ("rewrite_bad", "conversation_route_invalid"),
        ("route_truncated", "chat_output_truncated"),
    ],
)
def test_social_model_failure_is_reported_without_canned_reply_or_retry(
    client, chat_session, mode, code
):
    fake = chat_session["answer_chat"]
    fake.intent_route, fake.mode = "greeting", mode
    response = send(client, chat_session, "Xin chào")
    assert response.status_code >= 400, response.text
    assert response.json()["code"] == code
    assert len(fake.requests) == 1
    turns = client.get(chat_session["conversation_url"] + "/turns").json()
    assert turns[0]["status"] == "failed" and turns[0]["result"] is None
    assert send(client, chat_session, "Xin chào").json()["code"] == "conversation_turn_failed"
    assert len(fake.requests) == 1


def test_social_call_uses_declared_reasoning_policy_and_records_paid_usage(client, chat_session):
    from sqlalchemy import select

    from qnu.domains.modelops.models import ModelUsageRecord
    from qnu.platform.database import AsyncSessionFactory

    data = chat_session
    as_actor(PLATFORM)
    configured = client.put(
        f"{API}/modelops/providers/{data['chat_provider']['id']}/reasoning",
        json={
            "policy": {
                "mode": "chat_template_kwarg",
                "parameter": "enable_thinking",
                "off_value": False,
                "tasks": {"off": ["answer"]},
                "verified": True,
            }
        },
    )
    assert configured.status_code == 200, configured.text
    as_actor(EDITOR)
    data["answer_chat"].intent_route = "greeting"
    response = send(client, data, "Xin chào")
    assert response.status_code == 200, response.text
    turn = response.json()
    assert turn["rewrite_trace"]["reasoning"]["value"] is False
    assert data["answer_chat"].requests[0]["body"]["chat_template_kwargs"] == {
        "enable_thinking": False,
    }

    async def ledger():
        async with AsyncSessionFactory() as db:
            row = await db.scalar(
                select(ModelUsageRecord).where(ModelUsageRecord.request_id == "route:" + turn["id"])
            )
            return row.total_tokens, row.status

    assert client.portal.call(ledger) == (80, "completed")


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
    assert "thay đổi" in response.json()[0]["source_status_reason"]
    assert send(client, chat_session).json()["code"] == "answer_evidence_changed"


@pytest.mark.parametrize(
    "mode,code",
    [
        ("clarify", "conversation_clarification_required"),
        ("rewrite_bad", "conversation_route_invalid"),
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


def test_first_turn_can_resolve_document_reference_from_single_source(client, chat_session):
    chat_session["answer_chat"].require_clarification = True
    response = send(client, chat_session, "Tài liệu này quy định gì?")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"]["status"] == "answered"
    assert body["rewrite_trace"]["needs_clarification"] is True
    assert body["resolved_question"] == "Tài liệu này quy định gì?"


def test_first_turn_requests_clarification_for_multiple_matching_documents(
    client, chat_session, monkeypatch
):
    from qnu.domains.rag.answer import service

    search = service.search

    async def two_documents(*args, **kwargs):
        found = await search(*args, **kwargs)
        first = found.hits[0]
        other = first.model_copy(update={"document_id": "second-document"})
        return found.model_copy(update={"hits": [first, other]})

    monkeypatch.setattr(service, "search", two_documents)
    chat_session["answer_chat"].require_clarification = True
    response = send(client, chat_session, "Tài liệu này quy định gì?")
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "conversation_clarification_required"
    assert len(chat_session["answer_chat"].requests) == 1


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
        ("provider", "chat_provider_changed"),
    ],
)
@pytest.mark.parametrize("intent", ["knowledge", "greeting"])
def test_changes_during_generation_discard_persisted_answer(
    client, chat_session, monkeypatch, change, code, intent
):
    from sqlalchemy import update

    from qnu.domains.assistants.models import Assistant
    from qnu.domains.conversations.models import Conversation
    from qnu.domains.modelops.models import Provider
    from qnu.domains.workspaces.models import WorkspaceMember
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    original = app.state.container.chat_model
    chat_session["answer_chat"].intent_route = intent

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
                elif change == "provider":
                    await db.execute(
                        update(Provider)
                        .where(Provider.id == chat_session["chat_provider"]["id"])
                        .values(model_name="changed-model")
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
