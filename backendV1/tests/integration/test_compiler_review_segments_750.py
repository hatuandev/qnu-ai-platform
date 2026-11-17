"""A draft that cannot fit one review call is reviewed in parts, still covering every unit.

This exercises the segmented review execution path end to end: planning, per-part
model calls, durable part checkpoints, the merged report and the coverage proof.
It exists because that path used to be unreachable: the first part raised
``NameError`` for a missing ``run`` argument and the whole review stopped as
``uncertain`` without ever sending a request.
"""

import asyncio
import json

import pytest

from qnu.domains.knowledge.compilation.review import execution as review_execution
from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeJobQueue, ocr_blocks, set_quota, use_queue

SECTIONS = 40
BODY = "Điều kiện xét tuyển theo đề án năm 2026 được ghi rõ trong bảng chỉ tiêu. " * 8


class SegmentedReviewChat(FakeChat):
    """A long compiler draft, then part-scoped assessments for whatever a part owns."""

    def _respond(self, index):
        incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        if "allowed_citations" in incoming:
            return self._draft(incoming["allowed_citations"][0])
        sources = incoming["source_units"]
        drafts = incoming["draft_units"]
        allowed_sources = incoming.get("allowed_source_ids") or [unit["id"] for unit in sources]
        allowed_drafts = incoming.get("allowed_draft_ids") or [unit["id"] for unit in drafts]
        source_checks = [
            {
                "source_id": unit["id"],
                "status": "covered" if allowed_drafts else "out_of_scope",
                "draft_ids": allowed_drafts[:1],
                "explanation": "Đã đối chiếu trong phần này.",
                "suggested_action": "",
            }
            for unit in sources
        ]
        draft_checks = [
            {
                "draft_id": unit["id"],
                "status": "supported" if allowed_sources else "uncertain",
                "source_ids": allowed_sources[:1],
                "explanation": "Có nguồn tương ứng trong phần này.",
                "suggested_action": "",
            }
            for unit in drafts
        ]
        return self._reply(
            {
                "source_assessments": source_checks,
                "draft_assessments": draft_checks,
            }
        )

    def _draft(self, citation):
        return self._reply(
            {
                "title": "Chỉ tiêu tuyển sinh",
                "sections": [
                    {
                        "heading": f"Điều kiện {number}",
                        "paragraphs": [{"text": BODY, "citations": [citation]}],
                    }
                    for number in range(1, SECTIONS + 1)
                ],
                "unknowns": [],
            }
        )

    def _reply(self, content):
        body = {
            "model": "test-chat",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(content, ensure_ascii=False),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        self.last_raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return 200, self.last_raw


def small_provider(client, data, base_url, *, context_window, max_output, model="small-chat"):
    """A second provider whose envelope cannot hold the whole review payload."""
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "small-" + data["workspace"]["id"],
            "provider_type": "openai_compatible",
            "base_url": base_url,
            "model_name": model,
            "capabilities": ["chat"],
            "timeout_seconds": 5,
            "token_limits": {
                "context_window_tokens": context_window,
                "max_output_tokens": max_output,
            },
        },
    )
    assert response.status_code == 201, response.text
    provider = response.json()
    response = client.post(
        f"{API}/modelops/providers/{provider['id']}/keys",
        json={"name": "chat-key", "secret": "compiler-test-secret"},
    )
    assert response.status_code == 201, response.text
    as_actor(EDITOR)
    return provider


@pytest.mark.parametrize("limit", [1, 5])
def test_long_review_runs_in_parts_and_still_covers_every_unit(client, monkeypatch, limit):
    active = peak = 0
    run_part = review_execution._part_session

    async def count_in_flight(*args, **kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0)
            return await run_part(*args, **kwargs)
        finally:
            active -= 1

    monkeypatch.setattr(review_execution, "_part_session", count_in_flight)
    data = processed_input(client, code="segmented-review")
    with SegmentedReviewChat() as chat:
        provider = chat_provider(client, data, chat.base_url, model="big-chat")
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        if limit > 1:
            as_actor(PLATFORM)
            configured = client.patch(
                f"{API}/modelops/document-processing",
                json={"provider_id": provider["id"], "concurrency": {provider["id"]: 2}},
            )
            assert configured.is_success, configured.text
            as_actor(EDITOR)
        requested = request_compile(client, data)
        assert requested.status_code == 201, requested.text
        run = requested.json()["run"]
        assert run["provider_id"] == provider["id"]
        run_id = run["id"]
        progress = client.get(f"{data['url']}/{run_id}/progress").json()
        assert progress["concurrency"] == (2 if limit > 1 else 1)
        assert execute_compile(client, run_id) == "completed"
        small = small_provider(
            client,
            {**data, "provider": provider},
            chat.base_url,
            context_window=40960,
            max_output=4096,
        )
        base = data["url"] + "/" + run_id + "/reviews"
        as_actor(PLATFORM)
        saved = client.patch(
            f"{API}/modelops/document-processing",
            json={
                "provider_id": small["id"],
                **({"concurrency": {small["id"]: limit}} if limit > 1 else {}),
            },
        )
        assert saved.is_success, saved.text
        as_actor(EDITOR)
        if limit > 1:
            assert saved.json()["concurrency"] == {provider["id"]: 2, small["id"]: 5}
            assert client.get(f"{data['url']}/{run_id}/progress").json()["concurrency"] == 2
        body = {}
        response = client.post(base, json=body, headers={"Idempotency-Key": "segmented-review"})
        assert response.status_code == 200, response.text
        row = response.json()
        assert row["status"] == "completed", row
        assert row["provider_id"] == small["id"]
        assert row["trace"]["review_concurrency"] == limit
        assert row["trace"]["segmentation"]["segment_count"] >= 2
        assert peak == (0 if limit == 1 else min(limit, row["trace"]["segmentation"]["segment_count"]))
        progress = client.get(f"{base}/{row['id']}/progress").json()
        assert progress["segmented"] is True
        assert progress["total"] >= 2
        assert progress["completed"] == progress["total"]
        assert progress["pending"] == progress["running"] == progress["failed"] == 0
        assert progress["uncertain"] == 0
        report = client.get(f"{base}/{row['id']}/report")
        assert report.status_code == 200, report.text
        content = report.json()
        assert content["summary"]["source_units_checked"] == 14
        assert content["summary"]["draft_units_checked"] >= SECTIONS + 1
        # Exact table parts consume no model request; every other part sends once.
        sent = len(chat.requests)
        assert sent == 1 + sum(part["attempt_count"] for part in progress["segments"])
        assert all(
            part["attempt_count"] == (0 if part["usage_tokens"] == 0 else 1)
            for part in progress["segments"]
        )
        replay = client.post(base, json=body, headers={"Idempotency-Key": "segmented-review"})
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == row["id"]
        assert len(chat.requests) == sent
        seg_index = progress["segments"][0]["index"]
        assert client.get(f"{base}/{row['id']}/segments/{seg_index}/assessment").status_code == 200
        assert client.get(f"{base}/{row['id']}/segments/{seg_index}/markdown").status_code == 200


def test_worker_records_oversized_table_finding_and_exposes_pinned_source(client):
    from qnu.main import app
    from qnu.workers.tasks.compilation import manual_compiler_review_job

    class TableReviewChat(SegmentedReviewChat):
        def _respond(self, index):
            incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
            if "allowed_citations" not in incoming:
                return super()._respond(index)
            citation = next(
                ref for ref in incoming["allowed_citations"] if ref.endswith(":ev_p001_b002")
            )
            return self._reply(
                {
                    "title": "Bảng đối chiếu",
                    "sections": [
                        {
                            "heading": "Tổng hợp",
                            "paragraphs": [
                                {"text": "Tổng hợp từ cả bảng.", "citations": [citation]}
                            ],
                        }
                    ],
                    "unknowns": [],
                }
            )

    rows = [r"\thead{STT} & \thead{Nội dung}"]
    rows.extend(f"{number} & " + ("Điều kiện áp dụng. " * 60) for number in range(1, 23))
    table = r"\begin{tabular}{cc} " + r" \\ ".join(rows) + r" \end{tabular}"
    data = processed_input(
        client,
        code="planner-limited-review",
        response=ocr_blocks("Bảng đối chiếu|Title", table + "|Table"),
    )
    with TableReviewChat() as chat:
        chat_provider(client, data, chat.base_url)
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        requested = request_compile(client, data)
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        small = small_provider(client, data, chat.base_url, context_window=22000, max_output=4096)
        base = data["url"] + "/" + run_id + "/reviews"
        use_queue(FakeJobQueue())
        queued = client.post(
            base + "?background=true",
            json={"provider_id": small["id"]},
            headers={"Idempotency-Key": "planner-limited"},
        )
        assert queued.status_code == 200, queued.text
        review_id = queued.json()["id"]
        assert (
            client.portal.call(
                manual_compiler_review_job, {"container": app.state.container}, review_id
            )
            == "completed"
        )
        response = client.get(f"{base}/{review_id}/report")
        assert response.status_code == 200, response.text
        report = response.json()
        assert report["verdict"] == "needs_attention"
        (finding,) = [item for item in report["findings"] if item.get("source_locations")]
        assert finding["status"] == "uncertain" and finding["sources"] == []
        assert finding["draft_excerpts"][0]["text"] == "Tổng hợp từ cả bảng."
        (location,) = finding["source_locations"]
        assert location["source_id"] == data["source"]["id"]
        assert location["revision_id"] == data["revision"]["id"]
        assert location["page"] == 1
        calls = [json.loads(call["body"]["messages"][-1]["content"]) for call in chat.requests]
        assert any(call.get("source_units") for call in calls)
        assert not any(
            unit["text"] == "Tổng hợp từ cả bảng."
            for call in calls
            for unit in call.get("draft_units", [])
        )


class TruncatingFirstReviewPartChat(SegmentedReviewChat):
    def __init__(self):
        super().__init__()
        self.truncated_once = False

    def _respond(self, index):
        incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        if "allowed_citations" in incoming:
            return self._draft(incoming["allowed_citations"][0])
        if not self.truncated_once and len(incoming.get("draft_units", [])) >= 2:
            self.truncated_once = True
            body = {
                "model": "test-chat",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": '{"source_assessments": ['},
                        "finish_reason": "length",
                    }
                ],
                "usage": {"prompt_tokens": 120, "completion_tokens": 4096, "total_tokens": 4216},
            }
            self.last_raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            return 200, self.last_raw
        return super()._respond(index)


def test_truncated_review_segment_splits_into_children_and_exposes_segment_artifacts(client):
    data = processed_input(client, code="segmented-review-refine")
    with TruncatingFirstReviewPartChat() as chat:
        provider = chat_provider(client, data, chat.base_url, model="big-chat")
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        requested = request_compile(client, data)
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        small = small_provider(
            client,
            {**data, "provider": provider},
            chat.base_url,
            context_window=40960,
            max_output=4096,
        )
        base = data["url"] + "/" + run_id + "/reviews"
        body = {"provider_id": small["id"]}
        response = client.post(
            base, json=body, headers={"Idempotency-Key": "segmented-review-refine"}
        )
        assert response.status_code == 200, response.text
        row = response.json()
        assert row["status"] == "completed", row
        assert row["trace"].get("refinement_events")
        progress = client.get(f"{base}/{row['id']}/progress").json()
        assert progress["completed"] == progress["total"]
        parents = [s for s in progress["segments"] if not s["is_leaf"]]
        children = [s for s in progress["segments"] if s["parent_segment_id"]]
        assert len(parents) == 1 and len(children) >= 2
        for seg in progress["segments"]:
            idx = seg["index"]
            assert client.get(f"{base}/{row['id']}/segments/{idx}/assessment").status_code == 200
            assert client.get(f"{base}/{row['id']}/segments/{idx}/markdown").status_code == 200


def test_worker_preserves_terminal_recovery_code_if_cleanup_fails(client, monkeypatch):
    from dataclasses import replace

    from qnu.domains.knowledge.compilation.review import execution, refinement
    from qnu.main import app
    from qnu.workers.tasks.compilation import manual_compiler_review_job

    class InvalidCoverageChat(SegmentedReviewChat):
        def _respond(self, index):
            incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
            if "allowed_citations" in incoming:
                return self._draft(incoming["allowed_citations"][0])
            return self._reply({"source_assessments": [], "draft_assessments": []})

    async def broken_cleanup(*args):
        raise RuntimeError("Test recovery bookkeeping failure")

    limits_for = refinement.limits_for
    monkeypatch.setattr(
        refinement,
        "limits_for",
        lambda *args, **kwargs: replace(limits_for(*args, **kwargs), max_contract_recoveries=0),
    )
    monkeypatch.setattr(execution, "_mark_uncertain", broken_cleanup)
    data = processed_input(client, code="terminal-review-code")
    with InvalidCoverageChat() as chat:
        chat_provider(client, data, chat.base_url, model="full-chat")
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        requested = request_compile(client, data)
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        small = small_provider(client, data, chat.base_url, context_window=40960, max_output=4096)
        base = data["url"] + "/" + run_id + "/reviews"
        use_queue(FakeJobQueue())
        queued = client.post(
            base + "?background=true",
            json={"provider_id": small["id"]},
            headers={"Idempotency-Key": "terminal-review-code"},
        )
        assert queued.status_code == 200, queued.text
        review_id = queued.json()["id"]
        assert (
            client.portal.call(
                manual_compiler_review_job, {"container": app.state.container}, review_id
            )
            == "failed"
        )
        row = client.get(f"{base}/{review_id}").json()
        assert row["error_code"] == "compilation_review_recovery_exhausted"
        progress = client.get(f"{base}/{review_id}/progress").json()
        assert any(seg["error_code"] == row["error_code"] for seg in progress["segments"])


def test_source_first_review_repairs_only_missing_and_uncited_units(client, monkeypatch):
    from qnu.domains.knowledge.compilation.review import service
    from qnu.main import app
    from qnu.workers.tasks.compilation import manual_compiler_review_job

    # Keep the fixture on the model path to exercise recovery of several findings.
    monkeypatch.setattr(service, "source_prose_pairs", lambda material: {})

    class RepairChat(SegmentedReviewChat):
        def _respond(self, index):
            request = self.requests[index]["body"]
            payload = json.loads(request["messages"][-1]["content"])
            assert request["response_format"]["type"] == "json_schema"
            assert "tối đa 240 ký tự" in request["messages"][0]["content"]
            _, raw = super()._respond(index)
            data = json.loads(json.loads(raw)["choices"][0]["message"]["content"])
            result = {
                field: {
                    item[identity]: {k: v for k, v in item.items() if k != identity}
                    for item in data[field]
                }
                for field, identity in (
                    ("source_assessments", "source_id"),
                    ("draft_assessments", "draft_id"),
                )
            }
            if index == 0:
                candidates = [
                    item["id"] for item in payload["draft_units"] if item["kind"] == "paragraph"
                ]
                self.failed_ids = set(candidates[:2])
                assert len(self.failed_ids) == 2
                del result["draft_assessments"][candidates[0]]
                result["draft_assessments"][candidates[1]]["source_ids"] = ["not-in-pinned-scope"]
            return self._reply(result)

    data = processed_input(
        client,
        code="source-first-review-repair",
        response=ocr_blocks(
            "Chỉ tiêu theo ngành|Title",
            "Ngành A có chỉ tiêu 25.|Text",
            "Ngành B có chỉ tiêu 30.|Text",
        ),
    )
    with RepairChat() as chat:
        chat_provider(client, data, chat.base_url)
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        compiled = request_compile(client, data, source_first=True, auto_review=False)
        assert compiled.status_code == 201, compiled.text
        run_id = compiled.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        assert not chat.requests
        base = data["url"] + "/" + run_id + "/reviews"
        use_queue(FakeJobQueue())
        queued = client.post(
            base + "?background=true", json={}, headers={"Idempotency-Key": "repair"}
        )
        assert queued.status_code == 200, queued.text
        review_id = queued.json()["id"]
        replay = client.post(
            base + "?background=true", json={}, headers={"Idempotency-Key": "repair"}
        )
        assert replay.status_code == 200 and replay.json()["id"] == review_id
        conflicting = client.post(
            base + "?background=true",
            json={"structured_output": False},
            headers={"Idempotency-Key": "repair"},
        )
        assert (
            conflicting.status_code == 409 and conflicting.json()["code"] == "idempotency_conflict"
        )
        assert (
            client.portal.call(
                manual_compiler_review_job, {"container": app.state.container}, review_id
            )
            == "completed"
        )

        assert len(chat.requests) == 2
        first, repair = [json.loads(r["body"]["messages"][-1]["content"]) for r in chat.requests]
        assert "section:1:heading" not in {u["id"] for u in first["draft_units"]}
        assert {u["id"] for u in repair["draft_units"]} == chat.failed_ids
        assert repair["source_units"] == []
        assert len(chat.requests[1]["body"]["messages"][-1]["content"]) < len(
            chat.requests[0]["body"]["messages"][-1]["content"]
        )
        row = client.get(f"{base}/{review_id}").json()
        assert row["usage_tokens"] == 300
        assert row["trace"]["refinement_events"][0]["policy"] == "repair_owned_units/v1"
        report = client.get(f"{base}/{review_id}/report").json()
        assert report["summary"]["draft_units_checked"] == len(first["draft_units"]) + 1
        heading = next(
            check
            for check in report["draft_assessments"]
            if check["draft_id"] == "section:1:heading"
        )
        assert heading["status"] == "supported" and len(heading["source_excerpts"]) == 1
        assert "not-in-pinned-scope" not in json.dumps(report)


@pytest.mark.parametrize("selective", [False, True])
def test_review_verifies_retained_prose_without_model_round_trip(client, selective):
    from qnu.main import app
    from qnu.workers.tasks.compilation import manual_compiler_review_job

    class TitleChat(SegmentedReviewChat):
        def _respond(self, index):
            messages = self.requests[index]["body"]["messages"]
            payload = json.loads(messages[-1]["content"])
            if "part" in payload:
                (unit,) = payload["part"]["owned"]
                citation = f"{unit['ocr_run_id']}:{unit['evidence_id']}"
                return self._reply(
                    {
                        "sections": [],
                        "unknowns": [],
                        "metadata": [
                            {
                                "field": "Số hiệu",
                                "value": "07/AB",
                                "citation": citation,
                                "quote": "Số hiệu: 07/AB",
                            }
                        ],
                    }
                )
            assert "Nội dung và độ phủ nguồn được kiểm riêng" in messages[0]["content"]
            assert payload["source_units"] == []
            assert [unit["id"] for unit in payload["draft_units"]] == ["title"]
            anchor = payload["context_source_units"][0]["id"]
            return self._reply(
                {
                    "source_assessments": {},
                    "draft_assessments": {
                        "title": {
                            "status": "supported",
                            "source_ids": [anchor],
                            "explanation": "Tiêu đề phù hợp.",
                            "suggested_action": "",
                        }
                    },
                }
            )

    data = processed_input(
        client,
        code=f"retained-review-prose-{int(selective)}",
        response=ocr_blocks(
            "Chỉ tiêu tuyển sinh|Title",
            "Năm 2026 có 25 chỉ tiêu.|Text",
            "Năm 2025 có 19 chỉ tiêu.|Text",
            "Số hiệu: 07/AB|Text",
        ),
    )
    with TitleChat() as chat:
        chat_provider(client, data, chat.base_url)
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        compiled = request_compile(
            client,
            data,
            source_first=not selective,
            selective_supplement=selective,
            auto_review=False,
        )
        assert compiled.status_code == 201, compiled.text
        run = compiled.json()["run"]
        assert run["source_first"] is (not selective)
        run_id = run["id"]
        assert execute_compile(client, run_id) == "completed"
        assert len(chat.requests) == int(selective)
        run_path = data["url"] + "/" + run_id
        draft_before = client.get(run_path + "/draft.json").content
        if selective:
            supplement = json.loads(draft_before)["supplement"]
            assert supplement["state"] == "completed"
            assert any(item["origin"] == "model" for item in supplement["metadata"])
        use_queue(FakeJobQueue())
        queued = client.post(
            run_path + "/reviews?background=true", json={}, headers={"Idempotency-Key": "prose"}
        )
        assert queued.status_code == 200, queued.text
        review_id = queued.json()["id"]
        outcome = client.portal.call(
            manual_compiler_review_job, {"container": app.state.container}, review_id
        )
        assert outcome == "completed"
        assert len(chat.requests) == int(selective) + 1
        review_path = run_path + "/reviews?background=true"
        replay = client.post(review_path, json={}, headers={"Idempotency-Key": "prose"})
        assert replay.json()["id"] == review_id
        different = client.post(
            review_path, json={"structured_output": False}, headers={"Idempotency-Key": "prose"}
        )
        assert different.status_code == 409, different.text
        report = client.get(f"{run_path}/reviews/{review_id}/report").json()
        assert report["summary"]["source_units_checked"] == 4
        assert report["summary"]["draft_units_checked"] == 6
        assert report["summary"]["finding_count"] == 0
        assert all(
            a["source"]["text"] == a["draft_excerpts"][0]["text"]
            for a in report["source_assessments"]
        )
        assert client.get(run_path + "/draft.json").content == draft_before


def test_source_first_review_splits_single_over_budget_text_block(client):
    from qnu.domains.modelops.inference.service import request_input_tokens
    from qnu.main import app
    from qnu.ports.chat_model import ChatMessage
    from qnu.workers.tasks.compilation import manual_compiler_review_job

    original = "Ngưỡng22%" * 5000
    context_window = 36096
    max_output = 4096

    class SpanChat(SegmentedReviewChat):
        def _respond(self, index):
            request = self.requests[index]["body"]
            messages = [ChatMessage(item["role"], item["content"]) for item in request["messages"]]
            schema = request["response_format"]["json_schema"]["schema"]
            assert request_input_tokens(messages, schema) + request["max_tokens"] <= context_window
            payload = json.loads(messages[-1].content)
            sources = payload["source_units"]
            drafts = payload["draft_units"]
            visible_sources = {
                unit["id"]: unit for unit in sources + payload.get("context_source_units", [])
            }
            visible_drafts = drafts + payload.get("context_draft_units", [])
            draft_refs = {
                ref: draft["id"] for draft in visible_drafts for ref in draft.get("citations", [])
            }
            assert all(
                visible_sources[ref]["text"] == draft["text"]
                for draft in drafts
                for ref in draft.get("citations", [])
            )
            return self._reply(
                {
                    "source_assessments": {
                        src["id"]: {
                            "status": "covered",
                            "draft_ids": [draft_refs[src["id"]]],
                            "explanation": "Khớp nguyên văn.",
                            "suggested_action": "",
                        }
                        for src in sources
                    },
                    "draft_assessments": {
                        draft["id"]: {
                            "status": "supported",
                            "source_ids": draft.get("citations") or [next(iter(visible_sources))],
                            "explanation": "Khớp nguyên văn.",
                            "suggested_action": "",
                        }
                        for draft in drafts
                    },
                }
            )

    data = processed_input(
        client, code="source-first-review-long-block", response=ocr_blocks(original + "|Text")
    )
    with SpanChat() as chat:
        provider = small_provider(
            client, data, chat.base_url, context_window=context_window, max_output=max_output
        )
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        compiled = request_compile(client, data, source_first=True, auto_review=False)
        assert compiled.status_code == 201, compiled.text
        run_id = compiled.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        base = data["url"] + "/" + run_id + "/reviews"
        use_queue(FakeJobQueue())
        queued = client.post(
            base + "?background=true",
            json={"provider_id": provider["id"]},
            headers={"Idempotency-Key": "text-spans"},
        )
        assert queued.status_code == 200, queued.text
        review_id = queued.json()["id"]
        assert (
            client.portal.call(
                manual_compiler_review_job, {"container": app.state.container}, review_id
            )
            == "completed"
        )
        assert len(chat.requests) > 1
        report = client.get(f"{base}/{review_id}/report").json()
        source = [item["source"] for item in report["source_assessments"]]
        draft = [
            item["draft"]
            for item in report["draft_assessments"]
            if item["draft"]["kind"] == "paragraph"
        ]
        assert len(source) == len(draft) > 3
        assert len({unit["source_block_id"] for unit in source}) == 1
        assert [unit["start_char"] for unit in source] == [
            0,
            *(unit["end_char"] for unit in source[:-1]),
        ]
        assert "".join(unit["text"] for unit in source) == original
        assert "".join(unit["text"] for unit in draft) == original
        assert report["summary"]["finding_count"] == 0
