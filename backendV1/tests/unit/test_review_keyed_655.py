"""Required review identities cannot be lost through duplicate JSON fields or extra output."""

import json

import pytest

from qnu.domains.knowledge.compilation.review.report import (
    decode_keyed,
    output_schema,
    validate_content,
)
from qnu.platform.errors import AppException


@pytest.mark.parametrize(
    "content",
    [
        '{"source_assessments":{"s":{},"s":{}},"draft_assessments":{"d":{}}}',
        '{"source_assessments":{},"draft_assessments":{"d":{}}}',
        '{"source_assessments":{"s":{"source_id":"other"}},"draft_assessments":{"d":{}}}',
        '{"source_assessments":{"s":{}},"draft_assessments":{"d":{}},"approved":true}',
    ],
)
def test_keyed_review_rejects_missing_duplicate_or_model_owned_identity(content):
    with pytest.raises(AppException) as caught:
        decode_keyed(content, {"source_units": [{"id": "s"}], "draft_units": [{"id": "d"}]})
    assert caught.value.code == "compilation_review_invalid"


@pytest.mark.parametrize("status", ["supported", "contradicted"])
def test_supported_status_requires_an_explicit_source_in_schema_and_validator(status):
    payload = {"source_units": [], "draft_units": [{"id": "d"}], "allowed_source_ids": ["s"]}
    value = {
        "source_assessments": [],
        "draft_assessments": [
            {
                "draft_id": "d",
                "status": status,
                "source_ids": [],
                "explanation": "Đối chiếu.",
                "suggested_action": "",
            }
        ],
    }
    with pytest.raises(AppException):
        validate_content(json.dumps(value), payload)
    schema = output_schema(payload, require_references=2)
    branches = schema["$defs"]["DraftAssessment"]["anyOf"]
    eligible = [
        branch["properties"]
        for branch in branches
        if status in branch["properties"]["status"]["enum"]
    ]
    assert eligible and all(branch["source_ids"]["minItems"] == 1 for branch in eligible)
    assert all(
        set(branch["required"]) == {"status", "source_ids", "explanation", "suggested_action"}
        for branch in branches
    )
    value["draft_assessments"][0]["source_ids"] = ["s"]
    assert validate_content(json.dumps(value), payload)
    assert "anyOf" not in output_schema(payload)["$defs"]["DraftAssessment"]


def test_no_source_cannot_be_claimed_as_supported_in_strict_schema():
    schema = output_schema({"source_units": [], "draft_units": [{"id": "d"}]}, require_references=2)
    check = schema["$defs"]["DraftAssessment"]
    assert check["properties"]["source_ids"]["maxItems"] == 0
    assert set(check["properties"]["status"]["enum"]) == {"unsupported", "uncertain"}
