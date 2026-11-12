"""Context is read-only; spelling proposals cannot silently become lexical rewrites."""

import json

import pytest

from qnu.domains.ocr.review.context import build_context, contextual_suggestions
from qnu.domains.ocr.review.schemas import TextUnit
from qnu.platform.errors import AppException


def unit(text="Xác nhận của bệnh viện cấp cơ bán trở lên.", evidence_id="target", **kw):
    return TextUnit(
        evidence_id=evidence_id, page=1, kind="text", text=text, original_text=text, bbox={}, **kw
    )


def response(text, replacement="bản", **updates):
    before = "bệnh viện cấp cơ bán trở lên"
    item = {
        "evidence_id": "target",
        "start": text.index("bán"),
        "end": text.index("bán") + 3,
        "original": "bán",
        "replacement": replacement,
        "reason": "Đối chiếu cụm trong câu.",
        "context_before": before,
        "context_after": before.replace("bán", replacement),
        **updates,
    }
    return json.dumps({"suggestions": [item]}, ensure_ascii=False)


def test_accent_correction_carries_exact_phrase_and_changes_nothing_else():
    target = unit()
    accepted, withheld, rejected = contextual_suggestions(response(target.text), {"target": target})
    assert not withheld and not rejected
    assert accepted[0].replacement == "bản"
    assert accepted[0].context_after == "bệnh viện cấp cơ bản trở lên"
    assert target.text.endswith("cơ bán trở lên.")


def test_lexical_guess_is_withheld_even_when_model_gives_matching_offsets_and_reason():
    target = unit()
    accepted, withheld, rejected = contextual_suggestions(
        response(target.text, "huyên"), {"target": target}
    )
    assert not accepted and not rejected
    assert withheld[0].replacement == "huyên"
    assert withheld[0].review_reason == "source_image_required"


@pytest.mark.parametrize(
    "replacement,reason",
    [
        ("huyện", None),
        ("xã", None),
        ("bản 2026", "numeric_change"),
        ("bản!", None),
        ("b ản", None),
    ],
)
def test_other_letters_numbers_punctuation_or_word_boundaries_cannot_be_auto_offered(
    replacement, reason
):
    target = unit()
    accepted, withheld, rejected = contextual_suggestions(
        response(target.text, replacement), {"target": target}
    )
    assert not accepted
    if reason:
        assert not withheld
        assert [item.reason for item in rejected] == [reason]
    else:
        assert len(withheld) == 1 and not rejected


@pytest.mark.parametrize(
    "fields",
    [
        {"context_before": "bệnh viện cấp huyện", "context_after": "bệnh viện cấp bản"},
        {"context_after": "bệnh viện huyện trở lên"},
        {"context_before": "bán", "context_after": "bản"},
    ],
)
def test_unproven_context_on_a_unique_anchor_is_withheld_for_manual_review(fields):
    target = unit()
    accepted, withheld, rejected = contextual_suggestions(
        response(target.text, **fields), {"target": target}
    )
    assert not accepted and not rejected
    assert withheld[0].review_reason == "context_unverified"


def test_read_only_target_is_rejected_not_withheld():
    target = unit()
    accepted, withheld, rejected = contextual_suggestions(
        response(target.text, evidence_id="read-only-neighbor"), {"target": target}
    )
    assert not accepted and not withheld
    assert [item.reason for item in rejected] == ["unknown_evidence"]


def test_contradictory_context_on_a_repeated_literal_is_rejected():
    target = unit("tôi và tôi")
    item = {
        "evidence_id": "target",
        "start": 7,
        "end": 10,
        "original": "tôi",
        "replacement": "tối",
        "reason": "Đối chiếu cụm trong câu.",
        "context_before": "tôi và tôi",
        "context_after": "tối và tôi",
    }
    accepted, withheld, rejected = contextual_suggestions(
        json.dumps({"suggestions": [item]}, ensure_ascii=False), {"target": target}
    )
    assert not accepted and not withheld
    assert [entry.reason for entry in rejected] == ["context_unverified"]


def test_empty_quoted_context_fails_the_response_contract():
    target = unit()
    with pytest.raises(AppException):
        contextual_suggestions(response(target.text, context_before=""), {"target": target})


def test_missing_context_contract_fails_instead_of_silently_using_legacy_response():
    target = unit()
    payload = json.loads(response(target.text))
    del payload["suggestions"][0]["context_after"]
    with pytest.raises(AppException):
        contextual_suggestions(json.dumps(payload), {"target": target})


def block(evidence_id, text, kind="text", **fields):
    return {"evidence_id": evidence_id, "text": text, "type": kind, **fields}


def test_heading_and_neighbors_keep_source_order_and_only_targets_are_editable():
    doc = {
        "pages": [
            {
                "page_number": 1,
                "blocks": [
                    block("h", "Điều kiện áp dụng", "title"),
                    block("before", "Đoạn trước."),
                    block("target", unit().text),
                    block("after", "Đoạn sau."),
                ],
            },
            {"page_number": 2, "blocks": [block("foreign", "Không liên quan")]},
        ]
    }
    result = build_context(doc, {"target": unit()})
    assert {u["evidence_id"] for u in result["units"]} == {"target"}
    assert [u["evidence_id"] for u in result["context"]] == ["h", "before", "after"]
    assert all(u["read_only"] for u in result["context"])
    assert result["source_image_verified"] is False


def test_table_row_and_header_are_from_same_table_only():
    cell = lambda key, text, header=False: {"evidence_id": key, "text": text, "header": header}
    doc = {
        "pages": [
            {
                "page_number": 1,
                "blocks": [
                    block(
                        "other",
                        "",
                        "table",
                        table={"status": "parsed", "rows": [[cell("wrong", "khác", True)]]},
                    ),
                    block(
                        "table",
                        "",
                        "table",
                        table={
                            "status": "parsed",
                            "rows": [
                                [cell("head", "Tên", True), cell("head2", "Điều kiện", True)],
                                [cell("rowname", "Ngành A"), cell("target", "cơ bán")],
                            ],
                        },
                    ),
                ],
            }
        ]
    }
    target = unit("cơ bán").model_copy(update={"kind": "table_cell", "row": 2, "column": 2})
    result = build_context(doc, {"target": target})
    assert {u["evidence_id"] for u in result["context"]} == {"head", "head2", "rowname"}
    assert all(u["parent_evidence_id"] == "table" for u in result["context"])


def test_context_is_bounded_without_truncating_editable_text():
    target = unit("A" * 3000)
    doc = {
        "pages": [
            {
                "page_number": 1,
                "blocks": [
                    block("before", "B" * 10000),
                    block("target", target.text),
                    block("after", "C" * 10000),
                ],
            }
        ]
    }
    result = build_context(doc, {"target": target}, max_chars=80)
    assert result["units"][0]["text"] == target.text
    assert sum(len(c["text"]) for c in result["context"]) <= 80
    assert result["context_truncated"]


def test_page_boundary_context_is_only_a_candidate_never_an_editable_continuation():
    target = unit()
    doc = {
        "pages": [
            {"page_number": 1, "blocks": [block("target", target.text)]},
            {"page_number": 2, "blocks": [block("next", "Câu đầu trang sau.")]},
        ]
    }
    result = build_context(doc, {"target": target})
    assert result["context"][0]["relationship"] == "page_boundary_candidate"
    assert result["context"][0]["read_only"]
    assert len(result["units"]) == 1
