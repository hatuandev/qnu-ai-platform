"""Structured decoding remains opt-in, source-bound, metered and independently validated."""

import pytest

from tests.integration.compiler_support import execute_compile, request_compile
from tests.integration.test_compiler_review_652 import ReviewChat, prepared, review
from tests.integration.workflow_support import run_review


@pytest.mark.parametrize("mode", ["normal", "missing_draft"])
def test_structured_review_keeps_server_coverage_guard_and_idempotency(client, mode):
    with prepared(client) as (data, chat):
        chat.mode = mode
        response = review(client, data, structured_output=True)
        assert response.status_code == (502 if mode == "missing_draft" else 200), response.text
        sent = chat.requests[-1]["body"]["response_format"]
        assert sent["type"] == "json_schema"
        schema = sent["json_schema"]["schema"]
        assert len(schema["properties"]["source_assessments"]["required"]) == 14
        assert len(schema["properties"]["draft_assessments"]["required"]) == 15
        assert "source_id" not in schema["$defs"]["SourceAssessment"]["properties"]
        import json

        incoming = json.loads(chat.requests[-1]["body"]["messages"][-1]["content"])
        assert set(incoming) == {"topic", "source_units", "draft_units", "documents"}
        assert incoming["documents"] and all(
            "pages" not in document and "evidence" not in document
            for document in incoming["documents"]
        )
        assert len(incoming["source_units"]) == 14 and len(incoming["draft_units"]) == 15
        assert review(client, data, structured_output=True).status_code == 200
        assert review(client, data, structured_output=False).status_code == 409
        assert len(chat.requests) == 2
        if mode == "normal":
            assert response.json()["trace"]["output_schema_sha256"]


def test_automatic_review_inherits_explicit_schema_option(client):
    from tests.integration.compiler_support import chat_provider, processed_input

    data = processed_input(client, code="schema-auto")
    with ReviewChat() as chat:
        chat_provider(client, data, chat.base_url)
        response = request_compile(
            client, data, structured_output=True, review_structured_output=True
        )
        assert response.status_code == 201, response.text
        run_id = response.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        assert run_review(client, run_id) == "completed"
        assert chat.requests[0]["body"]["response_format"]["type"] == "json_schema"
        assert chat.requests[-1]["body"]["response_format"]["type"] == "json_schema"
