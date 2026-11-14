"""Question answering through real API, ModelOps, publication and Qdrant boundaries."""

import json
import re

import pytest

from tests.integration.index_support import execute_index
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeNemotron
from tests.integration.test_index_api_647 import indexed  # noqa: F401


class FakeAnswerChat(FakeNemotron):
    def _respond(self, index):
        incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        if "current_question" in incoming:
            history = incoming["previous_user_questions"]
            value = {
                "route": "knowledge",
                "answer": None,
                "standalone_question": (history[-1] + " " if history else "")
                + incoming["current_question"],
                "needs_clarification": False,
            }
            return 200, json.dumps(
                {
                    "choices": [
                        {"message": {"content": json.dumps(value)}, "finish_reason": "stop"}
                    ],
                    "usage": {"total_tokens": 80},
                }
            ).encode()
        source = next(
            (e for e in incoming["evidence"] if e["kind"] == "table"), incoming["evidence"][0]
        )
        value = {
            "status": "answered",
            "statements": [{"text": "Chỉ tiêu là 150.", "evidence_ids": [source["id"]]}],
        }
        # The fake follows the production table contract; negative modes below
        # deliberately keep malformed prose/citations to exercise rejection.
        if self.mode in {"ok", "mixed_lookup", "mixed_narrative", "repair_cell"}:
            choices = [
                {"cell_id": key, "value": value}
                for t in incoming.get("tables", [])
                for row in t["rows"]
                for key, value in row["cells"].items()
            ]
            if choices:
                chosen = next((c for c in choices if c["value"] == "150"), choices[0])
                value = {
                    "status": "answered",
                    "statements": [],
                    "lookups": [{"cell_id": chosen["cell_id"]}],
                }
                if self.mode == "mixed_lookup":
                    value["statements"] = [
                        {
                            "text": "Chỉ tiêu là 999, phải nộp thêm phí.",
                            "evidence_ids": [source["id"]],
                        }
                    ]
                if self.mode == "mixed_narrative":
                    paragraph = next(e for e in incoming["evidence"] if e["kind"] != "table")
                    value["statements"] = [
                        {"text": paragraph["text"], "evidence_ids": [paragraph["id"]]}
                    ]
        if self.mode == "foreign_cell" or (self.mode == "repair_cell" and index == 0):
            value = {"status": "answered", "statements": [], "lookups": [{"cell_id": "E999:r1:k2"}]}
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
                f"{API}/modelops/defaults",
                json={
                    "embedding_provider_id": indexed["embedding_provider"]["id"],
                    "chat_provider_id": provider["id"],
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
        json={
            "question": "Chỉ tiêu trúng tuyển năm 2024 là bao nhiêu?",
            "retrieval_mode": "dense",
            **options,
        },
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
    stage_ms = body["trace"]["stage_ms"]
    assert {
        "retrieval",
        "context",
        "packing",
        "proof",
        "model_prepare",
        "generation",
        "validation",
        "total",
    } <= set(stage_ms)
    assert all(value >= 0 for value in stage_ms.values())
    assert stage_ms["total"] >= stage_ms["generation"]
    assert response.headers["cache-control"] == "private, no-store"
    sent = ready["answer_chat"].requests[0]["body"]
    assert sent["response_format"]["type"] == "json_schema"
    contract = sent["response_format"]["json_schema"]
    assert contract["strict"] is True
    assert set(contract["schema"]["required"]) == {
        "status", "statements", "lookups", "assessment", "message"
    }
    assert sent["model"] == "test-chat"
    assert "revision_id" not in sent["messages"][-1]["content"]


def test_answer_projection_preserves_published_table_and_prompt_contract(client, ready):
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["trace"]["prompt_version"] == "qnu.rag.answer/v35"
    assert body["trace"]["grounding"]["selected_cells"]
    selection = body["trace"]["context"]["selection"]
    packing = body["trace"]["context"]["packing"]
    assert selection["version"] == "qnu.rag.selection/v2"
    assert selection["selected_count"] >= 1
    assert packing["payload_version"] == "qnu.answer-payload/v4"
    assert packing["system_prompt_bytes"] and packing["component_bytes"]["evidence"] > 0
    assert packing["request_bytes_estimate"] > packing["system_prompt_bytes"]
    assert body["trace"]["grounding"]["payload_version"] == "qnu.answer-payload/v4"
    sent = json.loads(ready["answer_chat"].requests[0]["body"]["messages"][-1]["content"])
    schema = ready["answer_chat"].requests[0]["body"]["response_format"]["json_schema"]["schema"]
    assert schema["$defs"]["Statement"]["properties"]["evidence_ids"]["items"]["enum"] == [
        s["id"] for s in sent["evidence"] if s["kind"] != "table"
    ]
    from qnu.domains.knowledge.publication.evidence import digest

    assert body["trace"]["contract"]["schema_sha256"] == digest(schema)
    source = next(s for s in body["sources"] if s["kind"] == "table")
    projected = next(e for e in sent["evidence"] if e["id"] == source["evidence_id"])
    assert "structure" not in projected
    table = next(t for t in sent["tables"] if t["id"] == source["evidence_id"])
    assert table["columns"] and table["rows"]
    assert all(
        re.fullmatch(r"E[1-9]\d*:r\d+:k\d+", key)
        for row in table["rows"]
        for key in row["cells"]
    )
    assert "source_cells" not in json.dumps(table)
    assert set(schema["$defs"]["CellSelection"]["properties"]["cell_id"]["enum"]) == {
        cell_id for entry in sent["tables"] for row in entry["rows"] for cell_id in row["cells"]
    }
    # Full source geometry remains available to the backend contract.
    assert source["structure"]["source_table_citation"] in source["citations"]


@pytest.mark.parametrize(
    "mode,code",
    [
        ("foreign_citation", "answer_citation_invalid"),
        ("uncited", "answer_response_invalid"),
        ("schema", "answer_response_invalid"),
        ("inline_citation", "answer_response_invalid"),
        ("truncated", "chat_output_truncated"),
        ("http_error", "chat_provider_unavailable"),
        ("foreign_cell", "answer_cell_invalid"),
        ("numeric_prose", "answer_cell_selection_required"),
    ],
)
def test_invalid_answer_is_an_error_not_no_data(client, ready, mode, code):
    ready["answer_chat"].mode = mode
    response = ask(client, ready)
    assert response.status_code >= 400, response.text
    assert response.json()["code"] == code
    expected_calls = 2 if mode in {"foreign_cell", "numeric_prose"} else 1
    assert len(ready["answer_chat"].requests) == expected_calls


def test_repairs_bad_selection_once_using_same_evidence(client, ready):
    chat = ready["answer_chat"]
    chat.mode = "repair_cell"
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "answered" and "150" in body["answer"]
    assert body["trace"]["appeal"]["trigger"] == "answer_cell_invalid"
    assert body["trace"]["appeal"]["outcome"] == "answered"
    first, retry = [call["body"] for call in chat.requests]
    assert first["messages"][-1] == retry["messages"][-1]
    assert first["response_format"] == retry["response_format"]
    assert "lookups[].cell_id" in retry["messages"][0]["content"]


def test_model_can_abstain_without_fabricated_answer(client, ready):
    ready["answer_chat"].mode = "abstain"
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["answer"] is None and not response.json()["sources"]


def test_invalid_contract_has_safe_audit_without_retry(client, ready):
    ready["answer_chat"].mode = "schema"
    response = ask(client, ready)
    assert response.status_code == 502
    assert response.json()["title"] == "Phản hồi mô hình không hợp lệ"
    as_actor(PLATFORM)
    events = client.get(f"{API}/workspaces/{ready['workspace']['id']}/events").json()
    rows = events["items"] if isinstance(events, dict) else events
    event = next(row for row in rows if row["action"] == "answer.validation_failed")
    detail = event["detail"]
    assert detail["code"] == "answer_response_invalid"
    assert detail["issues"] and detail["output_sha256"]
    assert "answer-test-secret" not in json.dumps(detail)
    assert all("input" not in issue for issue in detail["issues"])
    assert len(ready["answer_chat"].requests) == 1


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
    [
        ("membership", 404),
        ("provider_disabled", 409),
        ("provider_identity", 409),
        ("reasoning", 409),
        ("index", 409),
    ],
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
                    elif change == "reasoning":
                        row.extra_config = {
                            **(row.extra_config or {}),
                            "reasoning_policy_v1": {
                                "mode": "chat_template_kwarg",
                                "parameter": "enable_thinking",
                                "off_value": False,
                                "tasks": {"off": ["answer"]},
                                "verified": True,
                            },
                        }
                    else:
                        row.model_name = "changed-model"
                await db.commit()
            return result

    monkeypatch.setattr(app.state.container, "chat_model", ChangeDuringChat())
    response = ask(client, ready)
    assert response.status_code == expected, response.text
    assert "answer" not in response.json()
    assert len(ready["answer_chat"].requests) == 1


def test_answer_budget_window_zero_is_checked_before_chat(client, ready):
    response = ask(client, ready, context_window=0, context_max_bytes=256)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "answer_context_budget_exceeded"
    assert not ready["answer_chat"].requests


def test_mixed_lookup_returns_only_original_cells_with_projection_trace(client, ready):
    ready["answer_chat"].mode = "mixed_lookup"
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "answered" and "150" in body["answer"]
    assert "999" not in body["answer"] and "phí" not in body["answer"]
    assert len(body["statements"]) == 1
    assert body["trace"]["grounding"]["projection"] == {
        "version": "qnu.answer-projection/v7",
        "mode": "selected_cells",
        "omitted_model_statements": 1,
    }
    assert len(ready["answer_chat"].requests) == 1


def test_mixed_paragraph_and_selected_cell_survive_one_provider_call(client, ready):
    ready["answer_chat"].mode = "mixed_narrative"
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "answered" and len(body["statements"]) == 2
    incoming = json.loads(ready["answer_chat"].requests[0]["body"]["messages"][-1]["content"])
    paragraph = next(e for e in incoming["evidence"] if e["kind"] != "table")
    assert body["statements"][0] == {
        "text": paragraph["text"],
        "evidence_ids": [paragraph["id"]],
    }
    assert "150" in body["statements"][1]["text"]
    assert body["trace"]["grounding"]["projection"] == {
        "version": "qnu.answer-projection/v7",
        "mode": "mixed",
        "omitted_model_statements": 0,
    }
    assert len(ready["answer_chat"].requests) == 1


def test_answer_trace_records_the_exact_reasoning_contract(client, ready):
    as_actor(PLATFORM)
    configured = client.put(
        f"{API}/modelops/providers/{ready['chat_provider']['id']}/reasoning",
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
    response = ask(client, ready)
    assert response.status_code == 200, response.text
    trace = response.json()["trace"]
    assert trace["reasoning"]["applied"] is True
    assert trace["reasoning"]["value"] is False
    assert len(trace["reasoning"]["policy_sha256"]) == 64
    assert trace["inference_configuration_hash"] != trace["configuration_hash"]
    assert ready["answer_chat"].requests[0]["body"]["chat_template_kwargs"] == {
        "enable_thinking": False,
    }
    assert len(ready["answer_chat"].requests) == 1


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


@pytest.mark.parametrize("change", ["index", "reasoning"])
def test_change_after_reservation_before_chat_releases_unused_budget(
    client, ready, monkeypatch, change
):
    from sqlalchemy import select, update

    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.domains.modelops.models import ModelUsageRecord, Provider
    from qnu.domains.modelops.usage.service import usage_service
    from qnu.platform.database import AsyncSessionFactory

    original = usage_service.reserve

    async def change_after_reserve(*args, **kwargs):
        record = await original(*args, **kwargs)
        if record.capability == "chat":
            async with AsyncSessionFactory() as db:
                if change == "index":
                    await db.execute(
                        update(IndexRun)
                        .where(IndexRun.id == ready["index_run"]["id"])
                        .values(is_active=False)
                    )
                else:
                    provider = await db.get(Provider, ready["chat_provider"]["id"])
                    provider.extra_config = {
                        **(provider.extra_config or {}),
                        "reasoning_policy_v1": {
                            "mode": "chat_template_kwarg",
                            "parameter": "enable_thinking",
                            "off_value": False,
                            "tasks": {"off": ["answer"]},
                            "verified": True,
                        },
                    }
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


def test_bare_requests_default_to_hybrid_rerank_with_workspace_default_provider(client, ready):
    from tests.integration.test_hybrid_655 import FakeRerank

    with FakeRerank() as rerank:
        as_actor(PLATFORM)
        created = client.post(
            f"{API}/modelops/providers",
            json={
                "name": "default-rerank-" + ready["workspace"]["id"],
                "provider_type": "openai_compatible",
                "base_url": rerank.base_url,
                "model_name": "test-rerank",
                "capabilities": ["rerank"],
                "timeout_seconds": 5,
                "token_limits": {"max_input_tokens": 32768},
            },
        )
        assert created.status_code == 201, created.text
        provider_id = created.json()["id"]
        assert (
            client.post(
                f"{API}/modelops/providers/{provider_id}/keys",
                json={"name": "test", "secret": "rerank-default-secret"},
            ).status_code
            == 201
        )
        assert (
            client.put(
                f"{API}/modelops/defaults",
                json={"rerank_provider_id": provider_id},
            ).status_code
            == 200
        )
        as_actor(EDITOR)
        answer = client.post(
            ready["answer_url"],
            json={"question": "Chỉ tiêu trúng tuyển năm 2024 là bao nhiêu?"},
        )
        assert answer.status_code == 200, answer.text
        assert answer.json()["status"] == "answered"
        retrieval = answer.json()["trace"]["retrieval"]
        assert retrieval["mode"] == "hybrid_rerank"
        assert retrieval["rerank_provider"]["provider_id"] == provider_id
        assert retrieval["rerank_tokens"] == 57
        search = client.post(ready["base"] + "/search", json={"query": "Chỉ tiêu trúng tuyển"})
        assert search.status_code == 200, search.text
        assert search.json()["trace"]["mode"] == "hybrid_rerank"
        assert search.json()["trace"]["rerank_provider"]["provider_id"] == provider_id
        assert len(rerank.requests) == 2
