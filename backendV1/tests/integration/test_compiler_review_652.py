"""Semantic review is an independent, source-pinned report, never approval."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    OUTSIDER,
    PLATFORM,
    REVIEWER,
    as_actor,
    create_collection,
)
from tests.integration.ocr_support import set_quota


def completed_compilation(client):
    data = processed_input(client, code="semantic-review")
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        requested = request_compile(client, data)
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
    return {**data, "run_id": run_id, "review_url": data["url"] + "/" + run_id + "/reviews"}


def test_completed_compiler_exposes_independent_reviews(client):
    data = completed_compilation(client)
    result = client.get(data["review_url"])
    assert result.status_code == 200, result.text
    assert result.json() == []


class ReviewChat(FakeChat):
    """Only a protocol fixture; its assessments are not semantic quality labels."""

    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()
        self.slow = False

    def _respond(self, index):
        incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        if "allowed_citations" in incoming:
            return super()._respond(index)
        if self.slow:
            self.started.set()
            assert self.release.wait(5)
        sources, drafts = incoming["source_units"], incoming["draft_units"]
        source_checks = [
            {
                "source_id": s["id"],
                "status": "covered",
                "draft_ids": [
                    next(
                        (d["id"] for d in drafts if d.get("source_id") == s["id"]), drafts[0]["id"]
                    )
                ],
                "explanation": "Đã đối chiếu trong phạm vi fixture.",
                "suggested_action": "",
            }
            for s in sources
        ]
        draft_checks = [
            {
                "draft_id": d["id"],
                "status": "supported",
                "source_ids": [d.get("source_id", sources[0]["id"])],
                "explanation": "Có nguồn tương ứng trong fixture.",
                "suggested_action": "",
            }
            for d in drafts
        ]
        if self.mode != "no_issues":
            source_checks[-1].update(
                status="omitted",
                draft_ids=[],
                explanation="Có thể thiếu ghi chú giới hạn năm.",
                suggested_action="Bổ sung ghi chú vào đoạn liên quan.",
            )
            draft_checks[2].update(
                status="contradicted",
                source_ids=[sources[-1]["id"]],
                explanation="Cần kiểm tra phạm vi của diễn giải.",
                suggested_action="Đối chiếu lại ghi chú nguồn.",
            )
        if self.mode == "missing_source":
            source_checks.pop()
        elif self.mode == "missing_draft":
            draft_checks.pop()
        elif self.mode == "duplicate_source":
            source_checks.append(source_checks[0])
        elif self.mode == "duplicate_draft":
            draft_checks.append(draft_checks[0])
        elif self.mode == "foreign_source":
            draft_checks[0]["source_ids"] = ["unrelated:source"]
        elif self.mode == "foreign_draft":
            source_checks[0]["draft_ids"] = ["unrelated:paragraph"]
        elif self.mode == "unsupported_reference":
            draft_checks[0]["source_ids"] = []
        elif self.mode == "covered_without_reference":
            source_checks[0]["draft_ids"] = []
        value = {"source_assessments": source_checks, "draft_assessments": draft_checks}
        if self.mode == "schema":
            value["approved"] = True
        if self.requests[index]["body"].get("response_format", {}).get("type") == "json_schema":
            value = {
                "source_assessments": {
                    a["source_id"]: {k: v for k, v in a.items() if k != "source_id"}
                    for a in source_checks
                },
                "draft_assessments": {
                    a["draft_id"]: {k: v for k, v in a.items() if k != "draft_id"}
                    for a in draft_checks
                },
            }
        body = {
            "choices": [
                {
                    "message": {"content": json.dumps(value, ensure_ascii=False)},
                    "finish_reason": "length" if self.mode == "truncated" else "stop",
                }
            ],
            "usage": {"prompt_tokens": 200, "completion_tokens": 400, "total_tokens": 600},
        }
        self.last_raw = json.dumps(body, ensure_ascii=False).encode()
        if self.mode == "http_error":
            self.last_raw = b'{"error":"unavailable"}'
            return 503, self.last_raw
        return 200, self.last_raw


@contextmanager
def prepared(client):
    data = processed_input(client, code="review-ready")
    with ReviewChat() as chat:
        provider = chat_provider(client, data, chat.base_url)
        response = request_compile(client, data)
        assert response.status_code == 201, response.text
        run_id = response.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        yield (
            {
                **data,
                "run_id": run_id,
                "review_url": data["url"] + "/" + run_id + "/reviews",
                "provider": provider,
            },
            chat,
        )


def review(client, data, key="review-one", **body):
    return client.post(data["review_url"], json=body, headers={"Idempotency-Key": key})


def test_review_has_readable_exact_sources_and_draft_without_changing_compiler(client):
    with prepared(client) as (data, chat):
        draft_url = data["url"] + "/" + data["run_id"] + "/draft"
        original = client.get(draft_url).content
        response = review(client, data)
        assert response.status_code == 200, response.text
        row = response.json()
        assert row["status"] == "completed" and row["verdict"] == "needs_attention"
        assert row["usage_tokens"] == 600 and row["usage_id"]
        base = data["review_url"] + "/" + row["id"]
        report = client.get(base + "/report")
        assert report.status_code == 200, report.text
        content = report.json()
        assert content["summary"]["finding_count"] == 2
        assert content["summary"]["source_units_checked"] == 14
        assert content["summary"]["draft_units_checked"] == 15
        assert content["findings"][0]["sources"][0]["text"] == "Ghi chú: số liệu năm 2023."
        assert (
            content["findings"][0]["sources"][0]["identity"]["revision_id"]
            == data["revision"]["id"]
        )
        assert "Nguồn — trang 1:" in client.get(base + "/markdown").text
        assert client.get(base + "/raw").content == chat.last_raw
        assert client.get(draft_url).content == original
        assert (
            client.get(draft_url).json()["validation"]["semantic_faithfulness"] == "not_evaluated"
        )
        assert len(chat.requests) == 2
        replay = review(client, data)
        assert replay.json()["id"] == row["id"] and len(chat.requests) == 2
        assert client.get(data["review_url"]).json()[0]["id"] == row["id"]
        assert client.get(base).json()["trace"]["source_unit_count"] == 14


def test_no_findings_is_not_approval_and_includes_every_unit(client):
    with prepared(client) as (data, chat):
        chat.mode = "no_issues"
        result = review(client, data)
        assert result.status_code == 200, result.text
        assert result.json()["verdict"] == "no_issues_detected"
        report = client.get(data["review_url"] + "/" + result.json()["id"] + "/report").json()
        assert report["findings"] == [] and report["limits"]
        source_texts = [c["source"]["text"] for c in report["source_assessments"]]
        assert all(value in source_texts for value in ["0", "-", "", "150", "Năm 2023", "Năm 2024"])
        draft = client.get(data["url"] + "/" + data["run_id"] + "/draft").json()
        assert draft["requires_review"] and draft["publication_status"] == "draft"


@pytest.mark.parametrize(
    "mode",
    [
        "missing_source",
        "missing_draft",
        "duplicate_source",
        "duplicate_draft",
        "foreign_source",
        "foreign_draft",
        "unsupported_reference",
        "covered_without_reference",
        "schema",
        "truncated",
        "http_error",
    ],
)
def test_incomplete_or_invalid_reviews_fail_with_raw_and_never_resend(client, mode):
    with prepared(client) as (data, chat):
        chat.mode = mode
        response = review(client, data)
        expected = 422 if mode == "truncated" else (503 if mode == "http_error" else 502)
        assert response.status_code == expected, response.text
        listing = client.get(data["review_url"]).json()
        assert len(listing) == 1 and listing[0]["status"] == "failed"
        base = data["review_url"] + "/" + listing[0]["id"]
        assert client.get(base + "/raw").content == chat.last_raw
        assert client.get(base + "/report").status_code == 409
        replay = review(client, data)
        assert replay.status_code == 200 and replay.json()["id"] == listing[0]["id"]
        assert len(chat.requests) == 2


def test_idempotency_body_scope_and_permissions_are_server_checked(client):
    with prepared(client) as (data, chat):
        as_actor(MEMBER)
        assert review(client, data).status_code == 403
        as_actor(OUTSIDER)
        assert client.get(data["review_url"]).status_code == 404
        as_actor(None)
        assert review(client, data).status_code == 401
        as_actor(REVIEWER)
        response = review(client, data)
        assert response.status_code == 200, response.text
        as_actor(MEMBER)
        assert (
            client.get(data["review_url"] + "/" + response.json()["id"] + "/report").status_code
            == 200
        )
        as_actor(REVIEWER)
        assert review(client, data, max_output_tokens=4096).status_code == 409
        as_actor(EDITOR)
        other = create_collection(client, data["workspace"]["id"], "Other review collection")
        assert (
            client.get(
                data["review_url"].replace(data["collection"]["id"], other["id"])
            ).status_code
            == 404
        )
        assert len(chat.requests) == 2


def test_review_requires_completed_current_sources_and_real_model_quota(client):
    from tests.integration.compiler_support import FakeJobQueue
    from tests.integration.ocr_support import use_queue

    data = processed_input(client)
    with ReviewChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        run_id = request_compile(client, data).json()["run"]["id"]
        data = {**data, "run_id": run_id, "review_url": data["url"] + "/" + run_id + "/reviews"}
        assert review(client, data).status_code == 409
        assert not chat.requests
        assert execute_compile(client, run_id) == "completed"
        set_quota(client, data["workspace"]["id"], 1)
        response = review(client, data)
        assert response.status_code == 429, response.text
        replay = review(client, data)
        assert replay.status_code == 200 and replay.json()["status"] == "failed"
        assert not replay.json()["usage_id"] and len(chat.requests) == 1


def test_report_storage_failure_keeps_raw_but_exposes_no_partial_report(client, monkeypatch):
    from qnu.main import app

    with prepared(client) as (data, chat):
        blob = app.state.container.blob_store
        original_put = blob.put_bytes

        async def failing(key, payload, content_type=None):
            if "/compilation-review/" in key and "/markdown/" in key:
                raise OSError("simulated storage outage")
            return await original_put(key, payload, content_type)

        monkeypatch.setattr(blob, "put_bytes", failing)
        response = review(client, data)
        assert response.status_code == 503, response.text
        row = client.get(data["review_url"]).json()[0]
        assert row["status"] == "failed" and not row["verdict"]
        base = data["review_url"] + "/" + row["id"]
        assert client.get(base + "/report").status_code == 409
        assert client.get(base + "/markdown").status_code == 409
        assert client.get(base + "/raw").content == chat.last_raw


def test_same_key_during_quota_commit_uses_one_review_model_call(client, monkeypatch):
    from qnu.domains.modelops.usage.service import usage_service

    with prepared(client) as (data, chat):
        reserved, release = threading.Event(), threading.Event()
        original_reserve = usage_service.reserve
        calls = 0

        async def pause(*args, **kwargs):
            nonlocal calls
            usage = await original_reserve(*args, **kwargs)
            calls += 1
            if calls == 1:
                reserved.set()
                assert await asyncio.to_thread(release.wait, 5)
            return usage

        monkeypatch.setattr(usage_service, "reserve", pause)
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(review, client, data)
            try:
                assert reserved.wait(5)
                second = review(client, data)
                assert second.status_code == 200 and second.json()["status"] == "running", (
                    second.text
                )
            finally:
                release.set()
            first_result = first.result(timeout=10)
        assert first_result.status_code == 200, first_result.text
        assert first_result.json()["id"] == second.json()["id"]
        assert calls == 1 and len(chat.requests) == 2


@pytest.mark.parametrize("change", ["membership", "provider", "source", "expiry"])
def test_changes_during_review_reject_results_and_keep_durable_failure(client, change):
    from sqlalchemy import select

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.compilation.review.models import CompilationReview
    from qnu.domains.knowledge.models import KBSource
    from qnu.domains.modelops.models import Provider
    from qnu.domains.workspaces.models import WorkspaceMember
    from qnu.platform.database import AsyncSessionFactory

    with prepared(client) as (data, chat):
        chat.slow = True

        async def mutate():
            async with AsyncSessionFactory() as db:
                if change == "membership":
                    member = await db.scalar(
                        select(WorkspaceMember).where(
                            WorkspaceMember.workspace_id == data["workspace"]["id"],
                            WorkspaceMember.actor_ref == EDITOR.actor_id,
                        )
                    )
                    member.status = "revoked"
                elif change == "provider":
                    provider = await db.get(Provider, data["provider"]["id"])
                    provider.is_active = False
                elif change == "source":
                    source = await db.get(KBSource, data["source"]["id"])
                    source.latest_revision_no += 1
                else:
                    row = await db.scalar(select(CompilationReview))
                    row.expires_at = utcnow() - timedelta(seconds=1)
                await db.commit()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(review, client, data)
            try:
                assert chat.started.wait(5)
                client.portal.call(mutate)
            finally:
                chat.release.set()
            response = future.result(timeout=10)
        assert response.status_code in {403, 404, 409, 503}, response.text
        as_actor(PLATFORM)
        row = client.get(data["review_url"]).json()[0]
        assert row["status"] in {"failed", "uncertain"}
        assert client.get(data["review_url"] + "/" + row["id"] + "/report").status_code == 409
        assert len(chat.requests) == 2


def test_explicit_review_provider_is_used_without_changing_compiler_model(client):
    with prepared(client) as (data, compiler_chat), ReviewChat() as reviewer:
        as_actor(PLATFORM)
        provider = client.post(
            f"{API}/modelops/providers",
            json={
                "name": "independent-reviewer",
                "provider_type": "openai_compatible",
                "base_url": reviewer.base_url,
                "model_name": "review-model",
                "capabilities": ["chat"],
                "timeout_seconds": 5,
                "token_limits": {"context_window_tokens": 131072, "max_output_tokens": 8192},
            },
        )
        assert provider.status_code == 201, provider.text
        provider_id = provider.json()["id"]
        assert (
            client.post(
                f"{API}/modelops/providers/{provider_id}/keys",
                json={
                    "name": "review-key",
                    "secret": "test-review-credential",
                },
            ).status_code
            == 201
        )
        assert (
            client.put(
                f"{API}/workspaces/{data['workspace']['id']}/allowed-providers",
                json={
                    "provider_ids": [
                        data["ocr_provider"]["id"],
                        data["provider"]["id"],
                        provider_id,
                    ],
                    "defaults": {"chat": data["provider"]["id"], "ocr": data["ocr_provider"]["id"]},
                },
            ).status_code
            == 200
        )
        as_actor(EDITOR)
        response = review(client, data, provider_id=provider_id)
        assert response.status_code == 200, response.text
        assert response.json()["provider_id"] == provider_id
        assert response.json()["trace"]["model_name"] == "review-model"
        assert reviewer.requests[0]["body"]["model"] == "review-model"
        assert reviewer.requests[0]["authorization"] == "Bearer test-review-credential"
        assert len(compiler_chat.requests) == 1
        run = client.get(data["url"] + "/" + data["run_id"]).json()
        assert run["provider_id"] == data["provider"]["id"]


def test_uncertain_request_preserves_unknown_usage_and_never_retries(client):
    from qnu.domains.modelops.models import ModelUsageRecord
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory
    from qnu.platform.errors import AppException

    class UncertainChat:
        def __init__(self):
            self.calls = 0

        async def complete(self, messages, request):
            self.calls += 1
            raise AppException(
                "Không biết kết quả gọi model.", code="chat_provider_uncertain", status_code=504
            )

    with prepared(client) as (data, _):
        original = app.state.container.chat_model
        model = UncertainChat()
        app.state.container.chat_model = model
        try:
            response = review(client, data)
            assert response.status_code == 504, response.text
            replay = review(client, data)
            assert replay.status_code == 200 and replay.json()["status"] == "uncertain"
            assert replay.json()["usage_tokens"] is None and model.calls == 1

            async def usage():
                async with AsyncSessionFactory() as db:
                    row = await db.get(ModelUsageRecord, replay.json()["usage_id"])
                    return row.status, row.total_tokens, row.reserved_tokens

            status, tokens, reserved = client.portal.call(usage)
            assert status == "unknown" and tokens is None and reserved > 0
        finally:
            app.state.container.chat_model = original


def test_corrupted_report_is_an_error_and_old_review_does_not_match_new_source(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.compilation.review.models import ReviewArtifact
    from qnu.domains.knowledge.models import KBSource
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    with prepared(client) as (data, chat):
        response = review(client, data)
        assert response.status_code == 200, response.text
        base = data["review_url"] + "/" + response.json()["id"]

        async def corrupt():
            async with AsyncSessionFactory() as db:
                artifact = await db.scalar(
                    select(ReviewArtifact).where(
                        ReviewArtifact.review_id == response.json()["id"],
                        ReviewArtifact.kind == "report_json",
                    )
                )
                await app.state.container.blob_store.put_bytes(artifact.blob_key, b"corrupted")

        client.portal.call(corrupt)
        assert (
            client.get(base + "/report").json()["code"] == "compilation_review_artifact_integrity"
        )

        async def change_source():
            async with AsyncSessionFactory() as db:
                source = await db.get(KBSource, data["source"]["id"])
                source.latest_revision_no += 1
                await db.commit()

        client.portal.call(change_source)
        assert client.get(base + "/markdown").status_code == 409
        assert review(client, data).status_code == 409
        assert len(chat.requests) == 2
