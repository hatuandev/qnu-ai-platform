"""Source selection, durable auto review and approved immutable draft amendments."""

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)


@pytest.mark.parametrize("feature", ["text_version", "auto_review", "edit_context"])
def test_three_workflow_boundaries(client, feature):
    data = processed_input(client, code="workflow-baseline")
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        options = {"text_versions": {data["ocr_run_id"]: 0}} if feature == "text_version" else {}
        result = request_compile(client, data, **options)
        assert result.status_code == 201, result.text
        run_id = result.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        if feature != "text_version":
            suffix = "auto-review" if feature == "auto_review" else "edit-context"
            result = client.get(data["url"] + "/" + run_id + "/" + suffix)
            assert result.status_code == 200, result.text
