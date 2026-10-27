"""Question answering through real API, ModelOps, publication and Qdrant boundaries."""

import json

import pytest

from tests.integration.index_support import execute_index
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeNemotron
from tests.integration.test_index_api_647 import indexed  # noqa: F401


class FakeAnswerChat(FakeNemotron):
    def _respond(self, index):
        incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        source = next(
            (e for e in incoming["evidence"] if e["kind"] == "table"), incoming["evidence"][0]
        )
        value = {
            "status": "answered",
            "statements": [{"text": "Chỉ tiêu là 150.", "evidence_ids": [source["evidence_id"]]}],
        }
        if self.mode == "abstain":
            value = {"status": "insufficient_evidence", "statements": []}
        if self.mode == "foreign_citation":
            value["statements"][0]["evidence_ids"] = ["E999"]
        if self.mode == "uncited":
            value["statements"][0]["evidence_ids"] = []
        if self.mode == "schema":
            value["unexpected"] = True
        if self.mode == "inline_citation":
            value["statements"][0]["text"] += " [E999]"
        if self.mode == "http_error":
            return 503, b'{"error":"unavailable"}'
        return 200, json.dumps(
            {
                "choices": [
                    {
                        "message": {"content": json.dumps(value)},
                        "finish_reason": "length" if self.mode == "truncated" else "stop",
                    }
                ],
                "usage": {"total_tokens": 190},
            }
        ).encode()


@pytest.fixture
def ready(client, indexed):  # noqa: F811 - shared pytest fixture
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    with FakeAnswerChat() as chat:
        as_actor(PLATFORM)
        created = client.post(
            f"{API}/modelops/providers",
            json={
                "name": "answer-" + indexed["workspace"]["id"],
                "provider_type": "openai_compatible",
                "base_url": chat.base_url,
                "model_name": "test-chat",
                "capabilities": ["chat"],
                "timeout_seconds": 5,
                "token_limits": {"context_window_tokens": 131072, "max_output_tokens": 8192},
            },
        )
        assert created.status_code == 201, created.text
        provider = created.json()
        assert (
            client.post(
                f"{API}/modelops/providers/{provider['id']}/keys",
                json={"name": "test", "secret": "answer-test-secret"},
            ).status_code
            == 201
        )
        assert (
            client.put(
                f"{API}/workspaces/{indexed['workspace']['id']}/allowed-providers",
                json={
                    "provider_ids": [
                        indexed["ocr_provider"]["id"],
                        indexed["embedding_provider"]["id"],
                        provider["id"],
                    ],
                    "defaults": {
                        "embedding": indexed["embedding_provider"]["id"],
                        "chat": provider["id"],
                    },
                },
            ).status_code
            == 200
        )
        as_actor(EDITOR)
        yield {
            **indexed,
            "answer_chat": chat,
            "chat_provider": provider,
            "answer_url": indexed["base"] + "/answers",
        }


def ask(client, data, **options):
    return client.post(
        data["answer_url"],
        json={"question": "Chỉ tiêu tuyển sinh năm 2024 là bao nhiêu?", **options},
    )


def test_answer_returns_only_server_bound_sources(client, ready):
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "answered" and "150" in body["answer"]
    assert body["statements"] and body["sources"]
    assert body["index_run_id"] == ready["index_run"]["id"]
    assert all(
        c["revision_id"] == ready["revision"]["id"]
        for s in body["sources"]
        for c in s["citations"].values()
    )
    assert body["trace"]["provider_id"] == ready["chat_provider"]["id"]
    assert body["trace"]["total_tokens"] == 190
    assert response.headers["cache-control"] == "private, no-store"
    sent = ready["answer_chat"].requests[0]["body"]
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["model"] == "test-chat"
    assert "revision_id" not in sent["messages"][-1]["content"]


@pytest.mark.parametrize(
    "mode,code",
    [
        ("foreign_citation", "answer_citation_invalid"),
        ("uncited", "answer_response_invalid"),
        ("schema", "answer_response_invalid"),
        ("inline_citation", "answer_response_invalid"),
        ("truncated", "chat_output_truncated"),
        ("http_error", "chat_provider_unavailable"),
    ],
)
def test_invalid_answer_is_an_error_not_no_data(client, ready, mode, code):
    ready["answer_chat"].mode = mode
    response = ask(client, ready)
    assert response.status_code >= 400, response.text
    assert response.json()["code"] == code
    assert len(ready["answer_chat"].requests) == 1


def test_model_can_abstain_without_fabricated_answer(client, ready):
    ready["answer_chat"].mode = "abstain"
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["answer"] is None and not response.json()["sources"]


def test_withdrawn_content_does_not_call_chat(client, ready):
    from tests.integration.test_index_api_647 import withdraw

    withdraw(client, ready)
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    assert response.json()["reason"] == "no_eligible_content"
    assert not ready["answer_chat"].requests


def test_answer_requires_membership_and_preserves_document_scope(client, ready):
    from tests.integration.knowledge_support import MEMBER, OUTSIDER

    assert ask(client, ready, document_ids=["foreign"]).status_code == 404
    as_actor(OUTSIDER)
    assert ask(client, ready).status_code == 404
    as_actor(None)
    assert ask(client, ready).status_code == 401
    assert not ready["answer_chat"].requests
    as_actor(MEMBER)
    assert ask(client, ready).status_code == 200


def test_withdrawal_during_generation_discards_answer(client, ready, monkeypatch):
    from qnu.domains.knowledge.publication.decisions import commit_decision, create_preview
    from qnu.domains.knowledge.publication.schemas import CommitRequest, PreviewRequest
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    original = app.state.container.chat_model

    class WithdrawDuringChat:
        async def complete(self, messages, request):
            result = await original.complete(messages, request)
            async with AsyncSessionFactory() as db:
                args = (
                    db,
                    app.state.container.blob_store,
                    PLATFORM,
                    ready["workspace"]["id"],
                    ready["collection"]["id"],
                    ready["compiled"]["document"]["id"],
                    ready["compiled"]["version"]["id"],
                )
                preview = await create_preview(
                    *args, PreviewRequest(action="withdraw", reason="Synthetic race.")
                )
                await commit_decision(
                    *args,
                    CommitRequest(preview_id=preview.id, preview_sha256=preview.preview_sha256),
                    "answer-withdraw",
                )
            return result

    monkeypatch.setattr(app.state.container, "chat_model", WithdrawDuringChat())
    response = ask(client, ready)
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "answer_evidence_changed"


@pytest.mark.parametrize(
    "change,expected",
    [("membership", 404), ("provider_disabled", 409), ("provider_identity", 409), ("index", 409)],
)
def test_runtime_changes_during_chat_do_not_return_answer(
    client, ready, monkeypatch, change, expected
):
    from sqlalchemy import update

    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.domains.modelops.models import Provider
    from qnu.domains.workspaces.access import actor_ref
    from qnu.domains.workspaces.models import WorkspaceMember
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    original = app.state.container.chat_model

    class ChangeDuringChat:
        async def complete(self, messages, request):
            result = await original.complete(messages, request)
            async with AsyncSessionFactory() as db:
                if change == "membership":
                    await db.execute(
                        update(WorkspaceMember)
                        .where(
                            WorkspaceMember.workspace_id == ready["workspace"]["id"],
                            WorkspaceMember.actor_ref == actor_ref(EDITOR),
                        )
                        .values(status="revoked")
                    )
                elif change == "index":
                    await db.execute(
                        update(IndexRun)
                        .where(IndexRun.id == ready["index_run"]["id"])
                        .values(is_active=False)
                    )
                else:
                    row = await db.get(Provider, ready["chat_provider"]["id"])
                    if change == "provider_disabled":
                        row.is_active = False
                    else:
                        row.model_name = "changed-model"
                await db.commit()
            return result

    monkeypatch.setattr(app.state.container, "chat_model", ChangeDuringChat())
    response = ask(client, ready)
    assert response.status_code == expected, response.text
    assert "answer" not in response.json()


def test_invalid_document_list_is_422_before_inference(client, ready):
    assert ask(client, ready, document_ids=["same", "same"]).status_code == 422
    assert not ready["answer_chat"].requests


def test_chat_budget_limit_is_enforced_before_chat(client, ready):
    response = ask(client, ready, max_output_tokens=1000000)
    assert response.status_code == 422, response.text
    assert not ready["answer_chat"].requests


def test_ungiven_chat_provider_is_not_a_fallback(client, ready):
    response = ask(client, ready, provider_id="ungranted-provider")
    assert response.status_code == 404
    assert not ready["answer_chat"].requests


def test_no_search_hits_does_not_call_chat(client, ready, monkeypatch):
    from qnu.main import app

    async def empty(*args, **kwargs):
        return []

    monkeypatch.setattr(app.state.container.vector_store, "search", empty)
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    assert response.json()["reason"] == "no_match" and response.json()["answer"] is None
    assert not ready["answer_chat"].requests


def test_change_after_reservation_before_chat_releases_unused_budget(client, ready, monkeypatch):
    from sqlalchemy import select, update

    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.domains.modelops.models import ModelUsageRecord
    from qnu.domains.modelops.usage.service import usage_service
    from qnu.platform.database import AsyncSessionFactory

    original = usage_service.reserve

    async def change_after_reserve(*args, **kwargs):
        record = await original(*args, **kwargs)
        if record.capability == "chat":
            async with AsyncSessionFactory() as db:
                await db.execute(
                    update(IndexRun)
                    .where(IndexRun.id == ready["index_run"]["id"])
                    .values(is_active=False)
                )
                await db.commit()
        return record

    monkeypatch.setattr(usage_service, "reserve", change_after_reserve)
    response = ask(client, ready)
    assert response.status_code == 409, response.text
    assert not ready["answer_chat"].requests

    async def ledger():
        async with AsyncSessionFactory() as db:
            row = await db.scalar(
                select(ModelUsageRecord).where(ModelUsageRecord.request_id.startswith("ans_"))
            )
            return row.total_tokens, row.status

    assert client.portal.call(ledger) == (0, "failed")
