"""Synthetic reviewer for pre-existing publication fixtures, never quality labels."""

import json

from qnu.ports.chat_model import ChatResult


def acknowledgement(client, version_url):
    from qnu.main import app
    from tests.integration.test_compiler_review_652 import ReviewChat

    status = client.get(version_url + "/review-gate")
    if status.status_code == 409:
        version = client.get(version_url).json()
        base = version_url.split("/compiled-documents/")[0]
        review_url = base + "/compilation-runs/" + version["compilation_run_id"] + "/reviews"
        fixture = ReviewChat()
        fixture.mode = "no_issues"

        class SyntheticReviewer:
            async def complete(self, messages, request):
                fixture.requests.append(
                    {
                        "body": {
                            "messages": [{"role": m.role, "content": m.content} for m in messages]
                        }
                    }
                )
                _, raw = fixture._respond(len(fixture.requests) - 1)
                content = json.loads(raw)["choices"][0]["message"]["content"]
                return ChatResult(content, "test", request.model, 200, 400, "stop", 600, raw)

        original = app.state.container.chat_model
        app.state.container.chat_model = SyntheticReviewer()
        try:
            result = client.post(
                review_url, json={}, headers={"Idempotency-Key": "fixture-review:" + version["id"]}
            )
            assert result.status_code == 200, result.text
        finally:
            app.state.container.chat_model = original
        status = client.get(version_url + "/review-gate")
    assert status.status_code == 200, status.text
    current = status.json()
    return {
        "review_id": current["review_id"],
        "report_sha256": current["report_sha256"],
        "confirmed_reviewed": True,
        "resolutions": [
            {
                "finding_id": item["finding_id"],
                "decision": "not_an_issue",
                "reason": "Synthetic fixture acknowledgement; no accuracy claim.",
            }
            for item in current["findings"]
        ],
    }
