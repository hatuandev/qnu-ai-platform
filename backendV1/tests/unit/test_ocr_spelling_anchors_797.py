"""A model's approximate offsets are never trusted over literal source evidence."""

import json

import pytest

from qnu.domains.ocr.review.detection import validate_suggestions
from qnu.domains.ocr.review.schemas import TextUnit
from qnu.platform.errors import AppException


def inspect(text, suggestions):
    units = {
        "e1": TextUnit(
            evidence_id="e1", page=1, kind="text", text=text, original_text=text, bbox={}
        )
    }
    return validate_suggestions(
        json.dumps(
            {
                "suggestions": [
                    {"evidence_id": "e1", "reason": "Kiểm tra dấu", **s} for s in suggestions
                ]
            },
            ensure_ascii=False,
        ),
        units,
    )


def proposal(start=0, end=1, original="tôi", replacement="tối", **fields):
    return dict(start=start, end=end, original=original, replacement=replacement, **fields)


def test_unique_literal_anchor_repairs_codepoint_offsets_without_rewriting_source():
    text = "Một đoạn: tôi thiểu 04 năm."
    result = inspect(text, [proposal()])
    assert result[0].start == text.index("tôi")
    assert text[result[0].start : result[0].end] == "tôi"
    assert result[0].replacement == "tối"


def test_repeated_anchors_require_all_occurrences_and_identical_replacement():
    result = inspect("tôi và tôi", [proposal(1, 2), proposal(3, 4)])
    assert [(r.start, r.end) for r in result] == [(0, 3), (7, 10)]


@pytest.mark.parametrize(
    "text,items",
    [
        ("tôi và tôi", [proposal()]),  # An unspecified occurrence cannot be guessed.
        ("tôi và tôi", [proposal(1, 2), proposal(3, 4, replacement="tội")]),
        ("tôi và tôi", [proposal(1, 2), proposal(1, 2)]),
        ("tôi", [proposal(original="unknown")]),
        ("tôi", [proposal(evidence_id="foreign")]),
        ("tôi", [proposal(replacement="tối 2026")]),
        ("tôi", [proposal(start=3, end=1)]),
        ("tôi", [proposal(replacement="tôi")]),
    ],
)
def test_ambiguous_foreign_numeric_and_invalid_edits_are_rejected(text, items):
    with pytest.raises(AppException) as error:
        inspect(text, items)
    assert error.value.code == "ocr_spelling_invalid"


def test_overlap_is_checked_after_anchor_resolution():
    with pytest.raises(AppException):
        inspect("tôi thiểu", [proposal(), proposal(original="tôi thiểu", replacement="tối thiểu")])
