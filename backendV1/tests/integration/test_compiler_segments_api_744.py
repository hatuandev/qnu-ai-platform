"""New progress/partial routes stay additive for existing single-call runs."""

import json

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)


class CompatibilityChat(FakeChat):
    """Single-call compiler plus one exhaustive review assessment."""

    def _respond(self, index):
        incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        if "allowed_citations" in incoming:
            return super()._respond(index)
        sources = incoming["source_units"]
        drafts = incoming["draft_units"]
        source_checks = [
            {
                "source_id": unit["id"],
                "status": "covered",
                "draft_ids": [
                    next(
                        (draft["id"] for draft in drafts if draft.get("source_id") == unit["id"]),
                        drafts[0]["id"],
                    )
                ],
                "explanation": "Đã đối chiếu trong fixture.",
                "suggested_action": "",
            }
            for unit in sources
        ]
        draft_checks = [
            {
                "draft_id": unit["id"],
                "status": "supported",
                "source_ids": [unit.get("source_id") or sources[0]["id"]],
                "explanation": "Có nguồn tương ứng trong fixture.",
                "suggested_action": "",
            }
            for unit in drafts
        ]
        body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "source_assessments": source_checks,
                                "draft_assessments": draft_checks,
                            },
                            ensure_ascii=False,
                        )
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 200, "completion_tokens": 400, "total_tokens": 600},
        }
        self.last_raw = json.dumps(body, ensure_ascii=False).encode()
        return 200, self.last_raw


def test_new_small_run_uses_one_refinable_node_and_exposes_its_artifacts(client):
    data = processed_input(client, code="compat-progress")
    with CompatibilityChat() as chat:
        chat_provider(client, data, chat.base_url)
        created = request_compile(client, data)
        assert created.status_code == 201, created.text
        run_id = created.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"

        base = data["url"] + "/" + run_id
        progress = client.get(base + "/progress")
        assert progress.status_code == 200, progress.text
        body = progress.json()
        assert body["status"] == "completed" and body["segmented"] is True
        assert body["total"] == 1 and body["completed"] == 1
        assert len(body["segments"]) == 1 and len(body["nodes"]) == 1
        assert body["latest_output_generation"] is not None

        assert client.get(base + "/draft?partial=true").status_code == 200
        assert client.get(base + "/segments/1/raw").status_code == 200
        assert client.get(base + "/segments/1/artifacts/markdown").status_code == 200

        review = client.post(
            base + "/reviews",
            headers={"Idempotency-Key": "compat-review"},
            json={},
        )
        assert review.status_code == 200, review.text
        review_id = review.json()["id"]
        review_progress = client.get(f"{base}/reviews/{review_id}/progress")
        assert review_progress.status_code == 200, review_progress.text
        review_body = review_progress.json()
        assert review_body["status"] == "completed"
        assert review_body["segmented"] is False
        assert review_body["total"] == 1 and review_body["completed"] == 1
        assert review_body["usage_tokens"] == 600
        assert client.get(f"{base}/reviews/{review_id}/segments/1/raw").status_code == 404

        assert client.get(base + "/draft").status_code == 200
        assert client.get(f"{base}/reviews/{review_id}/report").status_code == 200
