"""Real HTTP/SQL/artifact boundary: one length stop becomes two durable leaves."""

import asyncio
import json
from concurrent.futures import CancelledError as FutureCancelledError
from datetime import timedelta
from urllib.parse import urljoin

import pytest
from sqlalchemy import update

from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation import execution, refinement
from qnu.domains.knowledge.compilation.lease import claim
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatResponseError
from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import API, EDITOR, OUTSIDER, PLATFORM, as_actor


class RefineChat(FakeChat):
    def _respond(self, index):
        status, body = super()._respond(index)
        if index == 0:
            data = json.loads(body)
            data["choices"][0]["finish_reason"] = "length"
            body = json.dumps(data).encode()
        return status, body


class ReasoningOnlyRefineChat(RefineChat):
    def _respond(self, index):
        status, body = super()._respond(index)
        if index == 0:
            data = json.loads(body)
            data["choices"][0]["message"] = {
                "role": "assistant",
                "content": "",
                "reasoning_content": "Still reasoning when the output limit was reached.",
            }
            body = json.dumps(data).encode()
        return status, body


@pytest.mark.parametrize("chat_type", [RefineChat, ReasoningOnlyRefineChat])
def test_truncated_parent_builds_child_pairs_and_aggregates_usage(client, chat_type):
    data = processed_input(client, code="refine751")
    with chat_type() as chat:
        chat_provider(client, data, chat.base_url)
        created = request_compile(client, data, auto_review=False, max_output_tokens=4096)
        assert created.status_code == 201, created.text
        run_id = created.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        base = data["url"] + "/" + run_id
        progress = client.get(base + "/progress").json()
        assert progress["total"] == progress["completed"] == 1
        assert len(progress["nodes"]) == 3
        assert len(chat.requests) == 3
        assert {call["body"]["max_tokens"] for call in chat.requests} == {4096}
        assert progress["usage_tokens"] == 3 * 173
        root = next(node for node in progress["nodes"] if node["parent_id"] is None)
        child_nodes = [node for node in progress["nodes"] if node["parent_id"] == root["id"]]
        assert len(child_nodes) == 2
        for node in progress["nodes"]:
            url = base + f"/segments/{node['index']}/artifacts/"
            draft = client.get(url + "draft_json")
            markdown = client.get(url + "markdown")
            assert draft.status_code == markdown.status_code == 200
            assert draft.json()["node"]["id"] == node["id"]
            links = draft.json()["node"]["artifacts"]
            assert (
                client.get(urljoin(url + "draft_json", links["document"]["json"])).status_code
                == 200
            )
            if node["parent_id"]:
                parent = client.get(urljoin(url + "draft_json", links["parent"]["json"]))
                assert parent.json()["node"]["id"] == node["parent_id"]
                assert "[Phần cha]" in markdown.text
        before = len(chat.requests)
        assert execute_compile(client, run_id) == "not_claimed"
        assert len(chat.requests) == before
        as_actor(OUTSIDER)
        assert client.get(base + f"/segments/{root['index']}/artifacts/markdown").status_code == 404
        as_actor(EDITOR)


def test_permanently_truncated_single_unit_stops_with_bounded_calls(client):
    data = processed_input(client, code="refine-limit751")
    with FakeChat() as chat:
        chat.mode = "truncated"
        chat_provider(client, data, chat.base_url)
        created = request_compile(client, data, auto_review=False)
        run_id = created.json()["run"]["id"]
        assert execute_compile(client, run_id) == "failed"
        assert len(chat.requests) <= 5
        progress = client.get(data["url"] + f"/{run_id}/progress").json()
        assert progress["completed"] == 0
        assert progress["usage_tokens"] == len(chat.requests) * 173
        assert any(node["error_code"] == "chat_output_truncated" for node in progress["nodes"])


def test_restart_after_raw_commit_refines_without_resending_parent(client, monkeypatch):
    data = processed_input(client, code="refine-restart751")
    with RefineChat() as chat:
        chat_provider(client, data, chat.base_url)
        created = request_compile(client, data, auto_review=False)
        run_id = created.json()["run"]["id"]

        async def interrupted(*args, **kwargs):
            raise asyncio.CancelledError

        with monkeypatch.context() as patch:
            patch.setattr(refinement, "create_children", interrupted)

            async def stop_at_raw_boundary():
                async with AsyncSessionFactory() as db:
                    run = await claim(db, run_id, "test-before-crash", 900)
                    docs = await execution._inputs(db, app.state.container.blob_store, run)
                    root = (await execution._segments(db, run_id))[0]
                    await execution._run_segment(
                        db,
                        app.state.container.blob_store,
                        run,
                        root,
                        docs,
                        app.state.container.chat_model,
                        background_actor(run.requested_by),
                        1,
                    )

            with pytest.raises((asyncio.CancelledError, FutureCancelledError)):
                client.portal.call(stop_at_raw_boundary)
        assert len(chat.requests) == 1

        async def expire_test_lease():
            async with AsyncSessionFactory() as db:
                await db.execute(
                    update(CompilationRun)
                    .where(CompilationRun.id == run_id)
                    .values(
                        lease_expires_at=utcnow() - timedelta(seconds=1),
                    )
                )
                await db.commit()

        client.portal.call(expire_test_lease)
        assert execute_compile(client, run_id) == "completed"
        assert len(chat.requests) == 3


def test_uncertain_child_is_never_resent_or_reported_as_known_usage(client):
    data = processed_input(client, code="refine-uncertain751")
    with RefineChat() as chat:
        chat_provider(client, data, chat.base_url)
        created = request_compile(client, data, auto_review=False)
        run_id = created.json()["run"]["id"]
        managed = app.state.container.chat_model

        class LostChild:
            calls = 0

            async def complete(self, messages, request):
                self.calls += 1
                if self.calls == 2:
                    raise ChatResponseError(
                        AppException(
                            "Lost response", code="chat_provider_uncertain", status_code=504
                        ),
                        b"",
                        None,
                    )
                return await managed.complete(messages, request)

        model = LostChild()
        assert execute_compile(client, run_id, model=model) == "uncertain"
        progress = client.get(data["url"] + f"/{run_id}/progress").json()
        assert progress["usage_tokens"] is None
        assert any(
            node["status"] == "uncertain" and node["parent_id"] for node in progress["nodes"]
        )
        assert execute_compile(client, run_id, model=model) == "not_claimed"
        assert model.calls == 2


def test_default_budget_adapts_to_4k_model_but_explicit_output_is_not_silently_changed(client):
    data = processed_input(client, code="refine-4k751")
    with FakeChat() as chat:
        provider = chat_provider(client, data, chat.base_url)
        as_actor(PLATFORM)
        response = client.patch(
            f"{API}/modelops/providers/{provider['id']}",
            json={
                "token_limits": {"context_window_tokens": 131072, "max_output_tokens": 4096},
            },
        )
        assert response.status_code == 200, response.text
        as_actor(EDITOR)
        requested = request_compile(client, data, auto_review=False)
        assert requested.status_code == 201, requested.text
        assert execute_compile(client, requested.json()["run"]["id"]) == "completed"
        assert {call["body"]["max_tokens"] for call in chat.requests} == {4096}
        explicit = request_compile(client, data, key="explicit-too-large", max_output_tokens=8192)
        assert explicit.status_code == 422
        assert explicit.json()["code"] == "model_output_limit_exceeded"
