"""Required review identities cannot be lost through duplicate JSON fields or extra output."""

import pytest

from qnu.domains.knowledge.compilation.review.report import decode_keyed
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
