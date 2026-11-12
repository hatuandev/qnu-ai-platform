"""A model's approximate offsets are never trusted over literal source evidence."""

import json

import pytest

from qnu.domains.ocr.review.context import contextual_suggestions
from qnu.domains.ocr.review.schemas import TextUnit


def unit(text, evidence_id="e1"):
    return TextUnit(
        evidence_id=evidence_id, page=1, kind="text", text=text, original_text=text, bbox={}
    )


def inspect(text, items):
    return contextual_suggestions(
        json.dumps({"suggestions": items}, ensure_ascii=False), {"e1": unit(text)}
    )


def proposal(
    text,
    start,
    end,
    replacement,
    *,
    original=None,
    anchor=None,
    evidence_id="e1",
    before=None,
    after=None,
):
    original = text[start:end] if original is None else original
    anchor = text.index(original) if anchor is None else anchor
    return {
        "evidence_id": evidence_id,
        "start": start,
        "end": end,
        "original": original,
        "replacement": replacement,
        "reason": "Kiểm tra dấu",
        "context_before": text if before is None else before,
        "context_after": (
            text[:anchor] + replacement + text[anchor + len(original) :] if after is None else after
        ),
    }


def test_unique_literal_anchor_repairs_codepoint_offsets_without_rewriting_source():
    text = "Một đoạn: tôi thiểu 04 năm."
    accepted, withheld, rejected = inspect(text, [proposal(text, 0, 1, "tối", original="tôi")])
    assert not withheld and not rejected
    assert accepted[0].start == text.index("tôi")
    assert text[accepted[0].start : accepted[0].end] == "tôi"
    assert accepted[0].replacement == "tối"


def test_repeated_literal_is_resolved_by_its_exact_context_only():
    text = "tôi và tôi"
    first = proposal(text, 1, 2, "tối", original="tôi", anchor=0)
    second = proposal(text, 3, 4, "tối", original="tôi", anchor=7)
    accepted, withheld, rejected = inspect(text, [first, second])
    assert not withheld and not rejected
    assert [(item.start, item.end) for item in accepted] == [(0, 3), (7, 10)]


@pytest.mark.parametrize(
    "before,after",
    [
        ("tôi", "tối"),
        ("tôi và tôi", "tối và tối"),
        ("không có trong đoạn", "tối"),
    ],
)
def test_repeated_literal_without_single_context_candidate_is_rejected(before, after):
    text = "tôi và tôi"
    accepted, withheld, rejected = inspect(
        text,
        [proposal(text, 1, 2, "tối", original="tôi", before=before, after=after)],
    )
    assert not accepted and not withheld
    assert [item.reason for item in rejected] == ["source_anchor_ambiguous"]


@pytest.mark.parametrize(
    "text,item,reason",
    [
        (
            "tôi",
            proposal("tôi", 0, 3, "tối", original="khác", anchor=0, after="tối"),
            "source_text_missing",
        ),
        (
            "tôi",
            proposal("tôi", 0, 3, "tối", original="tôi", evidence_id="foreign"),
            "unknown_evidence",
        ),
        (
            "tôi",
            proposal("tôi", 3, 1, "tối", original="tôi", after="tối"),
            "invalid_span",
        ),
        (
            "tôi",
            proposal("tôi", 0, 3, "tôi", original="tôi", after="tôi"),
            "no_change",
        ),
        (
            "tôi",
            proposal("tôi", 0, 3, " ", original="tôi", after="tôi"),
            "empty_replacement",
        ),
        (
            "tôi",
            proposal("tôi", 0, 3, "tối 2026", original="tôi", after="tối 2026"),
            "numeric_change",
        ),
    ],
)
def test_unknown_absent_invalid_unchanged_and_numeric_proposals_are_quarantined(text, item, reason):
    accepted, withheld, rejected = inspect(text, [item])
    assert not accepted and not withheld
    assert [entry.reason for entry in rejected] == [reason]


def test_overlap_is_checked_after_anchor_resolution():
    text = "tôi thiểu"
    accepted, withheld, rejected = inspect(
        text,
        [
            proposal(text, 0, 3, "tối", original="tôi"),
            proposal(text, 0, 10, "tối thiểu", original="tôi thiểu"),
        ],
    )
    assert [item.original for item in accepted] == ["tôi"]
    assert not withheld
    assert [item.reason for item in rejected] == ["overlap"]


def test_one_bad_proposal_never_discards_a_valid_sibling():
    text = "tôi thiểu 04 năm."
    accepted, withheld, rejected = inspect(
        text,
        [
            proposal(text, 0, 3, "tối", original="tôi"),
            proposal(text, 0, 3, "tôi 2026", original="tôi", after="tôi 2026"),
        ],
    )
    assert [(item.start, item.end, item.replacement) for item in accepted] == [(0, 3, "tối")]
    assert not withheld
    assert [item.reason for item in rejected] == ["numeric_change"]
