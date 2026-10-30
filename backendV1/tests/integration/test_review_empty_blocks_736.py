"""Real review API retains empty image evidence and enforces exhaustive coverage."""

import json

import pytest

from qnu.domains.knowledge.compilation.review.report import PROMPT_VERSION
from tests.integration import compiler_support
from tests.integration.test_compiler_review_652 import prepared, review


@pytest.mark.parametrize("mode", ["no_issues", "missing_source"])
def test_review_api_sends_empty_block_and_requires_its_assessment(client, monkeypatch, mode):
    monkeypatch.setattr(
        compiler_support,
        "TABLE_RESPONSE",
        compiler_support.TABLE_RESPONSE + "<x_0.1><y_0.7><x_0.9><y_0.9><class_Picture>",
    )
    with prepared(client) as (data, chat):
        draft_url = data["url"] + "/" + data["run_id"] + "/draft"
        original = client.get(draft_url).content
        chat.mode = mode
        result = review(client, data, structured_output=True)
        assert result.status_code == (200 if mode == "no_issues" else 502), result.text
        request = chat.requests[-1]["body"]
        payload = json.loads(request["messages"][-1]["content"])
        images = [u for u in payload["source_units"] if u["kind"] == "figure"]
        assert len(images) == 1 and images[0]["text"] == ""
        image = images[0]
        assert image["id"] == data["ocr_run_id"] + ":" + image["evidence_id"]
        assert image["identity"]["revision_id"] == data["revision"]["id"]
        assert image["page"] == 1 and image["bbox"]["x0"] == 0.1
        required = request["response_format"]["json_schema"]["schema"]["properties"][
            "source_assessments"
        ]["required"]
        assert image["id"] in required
        if mode == "no_issues":
            row = result.json()
            assert row["trace"]["prompt_version"] == PROMPT_VERSION
            report = client.get(data["review_url"] + "/" + row["id"] + "/report").json()
            assert any(c["source"] == image for c in report["source_assessments"])
        else:
            assert result.json()["code"] == "compilation_review_invalid"
        assert client.get(draft_url).content == original
