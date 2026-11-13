"""A draft that cannot fit one review call is reviewed in parts, still covering every unit.

This exercises the segmented review execution path end to end: planning, per-part
model calls, durable part checkpoints, the merged report and the coverage proof.
It exists because that path used to be unreachable: the first part raised
``NameError`` for a missing ``run`` argument and the whole review stopped as
``uncertain`` without ever sending a request.
"""

import json

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import set_quota

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


def test_long_review_runs_in_parts_and_still_covers_every_unit(client):
    data = processed_input(client, code="segmented-review")
    with SegmentedReviewChat() as chat:
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
        response = client.post(base, json=body, headers={"Idempotency-Key": "segmented-review"})
        assert response.status_code == 200, response.text
        row = response.json()
        assert row["status"] == "completed", row
        assert row["trace"]["segmentation"]["segment_count"] >= 2
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
