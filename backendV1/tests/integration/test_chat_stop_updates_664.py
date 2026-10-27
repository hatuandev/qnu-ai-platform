# ruff: noqa: F811
"""Existing update APIs must revoke running turns durably in the same transaction."""

import asyncio

import pytest
from sqlalchemy import select

from qnu.domains.assistants.schemas import AssistantConfig
from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.conversations.schemas import TurnRequest
from qnu.domains.conversations.service import reserve_turn
from qnu.domains.modelops.models import ModelUsageRecord
from qnu.domains.workspaces.models import WorkspaceEvent
from qnu.platform.database import AsyncSessionFactory
from tests.integration.knowledge_support import API, EDITOR, MEMBER, PLATFORM, as_actor
from tests.integration.test_answers_api_648 import ready  # noqa: F401
from tests.integration.test_conversations_649 import chat_session, send  # noqa: F401
from tests.integration.test_index_api_647 import indexed  # noqa: F401


def update_state(client, data, route, stopped, *, actor=None):
    if route == "assistant":
        as_actor(actor or PLATFORM)
        config = {key: data["assistant"][key] for key in AssistantConfig.model_fields}
        return client.put(
            f"{API}/workspaces/{data['workspace']['id']}/assistants/{data['assistant']['id']}",
            json={
                **config,
                "is_active": not stopped,
                "expected_revision": data["assistant"]["revision"],
            },
        )
    as_actor(actor or EDITOR)
    return client.put(
        data["conversation_url"],
        json={"title": "Synthetic review", "status": "archived" if stopped else "active"},
    )


def reserve(client, data, conversation_id=None, *, actor=EDITOR, seq=0):
    async def run():
        async with AsyncSessionFactory() as db:
            _, turn, _ = await reserve_turn(
                db,
                actor,
                data["workspace"]["id"],
                conversation_id or data["conversation"]["id"],
                TurnRequest(question="Synthetic question", expected_turn_no=seq),
                "pending",
            )
            return turn.id

    return client.portal.call(run)


def saved_turn(client, turn_id):
    async def load():
        async with AsyncSessionFactory() as db:
            row = await db.get(ConversationTurn, turn_id)
            return {
                "status": row.status,
                "result": row.result,
                "error_code": row.error_code,
                "finished_at": row.finished_at,
            }

    return client.portal.call(load)


@pytest.mark.parametrize("route", ["assistant", "conversation"])
def test_stop_and_resume_discards_late_answer_and_allows_new_turn(
    client, chat_session, monkeypatch, route
):
    from qnu.main import app

    data = chat_session
    original = app.state.container.chat_model

    class StopAndResumeDuringChat:
        async def complete(self, messages, request):
            result = await original.complete(messages, request)

            def stop_and_resume():
                for stopped in (True, False):
                    response = update_state(client, data, route, stopped)
                    assert response.status_code == 200, response.text
                as_actor(EDITOR)

            await asyncio.to_thread(stop_and_resume)
            return result

    monkeypatch.setattr(app.state.container, "chat_model", StopAndResumeDuringChat())
    response = send(client, data)
    as_actor(EDITOR)
    turn = client.get(data["conversation_url"] + "/turns").json()[0]
    assert {
        "http_status": response.status_code,
        "turn_status": turn["status"],
        "has_result": turn["result"] is not None,
    } == {"http_status": 409, "turn_status": "cancelled", "has_result": False}
    assert turn["error_code"] == "operation_cancelled" and turn["finished_at"]
    count = len(data["answer_chat"].requests)
    replay = send(client, data)
    assert replay.status_code == 409 and replay.json()["code"] == "conversation_turn_cancelled"
    assert len(data["answer_chat"].requests) == count

    async def usage():
        async with AsyncSessionFactory() as db:
            records = list(
                (
                    await db.scalars(
                        select(ModelUsageRecord).where(
                            ModelUsageRecord.request_id.startswith("ans_")
                        )
                    )
                ).all()
            )
            return [row.total_tokens for row in records]

    measured = client.portal.call(usage)
    assert len(measured) == 1 and measured[0] is not None and measured[0] > 0
    monkeypatch.setattr(app.state.container, "chat_model", original)
    next_turn = send(client, data, seq=1, key="after-resume")
    assert next_turn.status_code == 200, next_turn.text
    assert next_turn.json()["status"] == "completed"
    assert next_turn.json()["history_turn_ids"] == []
    assert saved_turn(client, turn["id"])["status"] == "cancelled"


@pytest.mark.parametrize("route", ["assistant", "conversation"])
def test_stop_update_only_cancels_related_running_turns(client, chat_session, route):
    data = chat_session
    assert send(client, data).status_code == 200
    first = client.get(data["conversation_url"] + "/turns").json()[0]
    target = reserve(client, data, seq=1)
    base = f"{API}/workspaces/{data['workspace']['id']}"
    as_actor(MEMBER)
    sibling = client.post(
        base + "/conversations", json={"assistant_id": data["assistant"]["id"]}
    ).json()
    sibling_turn = reserve(client, data, sibling["id"], actor=MEMBER)
    as_actor(PLATFORM)
    config = {key: data["assistant"][key] for key in AssistantConfig.model_fields}
    other_assistant = client.post(base + "/assistants", json={**config, "name": "Other"}).json()
    as_actor(EDITOR)
    other = client.post(
        base + "/conversations", json={"assistant_id": other_assistant["id"]}
    ).json()
    unrelated_turn = reserve(client, data, other["id"])
    response = update_state(client, data, route, True)
    assert response.status_code == 200, response.text
    cancelled = saved_turn(client, target)
    assert cancelled["status"] == "cancelled" and cancelled["result"] is None
    assert cancelled["error_code"] == "operation_cancelled" and cancelled["finished_at"]
    assert saved_turn(client, sibling_turn)["status"] == (
        "cancelled" if route == "assistant" else "running"
    )
    assert saved_turn(client, unrelated_turn)["status"] == "running"
    assert saved_turn(client, first["id"])["result"] == first["result"]

    async def audit():
        async with AsyncSessionFactory() as db:
            event = await db.scalar(
                select(WorkspaceEvent)
                .where(
                    WorkspaceEvent.workspace_id == data["workspace"]["id"],
                    WorkspaceEvent.action == route + ".updated",
                )
                .order_by(WorkspaceEvent.created_at.desc())
                .limit(1)
            )
            return event.detail["cancelled_turns"]

    assert client.portal.call(audit) == (2 if route == "assistant" else 1)
    if route == "assistant":
        assert response.json()["revision"] == data["assistant"]["revision"]
    assert update_state(client, data, route, True).status_code == 200
    assert update_state(client, data, route, False).status_code == 200
    assert saved_turn(client, target) == cancelled


@pytest.mark.parametrize("route", ["assistant", "conversation"])
def test_forbidden_stop_cannot_cancel_running_turn(client, chat_session, route):
    turn_id = reserve(client, chat_session)
    actor = EDITOR if route == "assistant" else MEMBER
    response = update_state(client, chat_session, route, True, actor=actor)
    assert response.status_code == (403 if route == "assistant" else 404)
    assert saved_turn(client, turn_id)["status"] == "running"


@pytest.mark.parametrize("route", ["assistant", "conversation"])
def test_active_update_keeps_running_turn(client, chat_session, route):
    turn_id = reserve(client, chat_session)
    response = update_state(client, chat_session, route, False)
    assert response.status_code == 200, response.text
    assert saved_turn(client, turn_id)["status"] == "running"


@pytest.mark.parametrize("route", ["assistant", "conversation"])
def test_failed_update_rolls_back_turn_cancellation(client, chat_session, monkeypatch, route):
    from qnu.domains.assistants import service as assistants
    from qnu.domains.conversations import service as conversations

    turn_id = reserve(client, chat_session)

    async def fail_event(*args, **kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr(
        assistants if route == "assistant" else conversations,
        "record_workspace_event",
        fail_event,
    )
    with pytest.raises(RuntimeError, match="Synthetic audit failure"):
        update_state(client, chat_session, route, True)
    assert saved_turn(client, turn_id)["status"] == "running"
    url = (
        f"{API}/workspaces/{chat_session['workspace']['id']}/assistants/"
        + chat_session["assistant"]["id"]
        if route == "assistant"
        else chat_session["conversation_url"]
    )
    response = client.get(url)
    assert response.status_code == 200, response.text
    assert response.json()["is_active" if route == "assistant" else "status"] == (
        True if route == "assistant" else "active"
    )
