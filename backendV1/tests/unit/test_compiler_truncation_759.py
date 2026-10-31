"""A measured length stop is refinable even before a reasoning model writes content."""

import json

import pytest

from qnu.domains.knowledge.compilation.refinement import diagnose


@pytest.mark.parametrize("reasoning_key", ["reasoning_content", "reasoning"])
def test_reasoning_only_length_stop_is_refinable(reasoning_key):
    raw = json.dumps(
        {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": "", reasoning_key: "Still reasoning."},
                }
            ],
            "usage": {"completion_tokens": 8192, "total_tokens": 40228},
        }
    ).encode()
    assert diagnose(raw)


@pytest.mark.parametrize("raw", [b"", b"422 context exceeded", b"{}", b"null"])
def test_no_inferred_truncation_from_missing_or_malformed_response(raw):
    assert not diagnose(raw)
