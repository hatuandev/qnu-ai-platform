"""Unread blocks remain explicit limitations, without changing source evidence."""

import copy
import json

import pytest

from qnu.domains.knowledge.compilation.drafting import build_draft
from qnu.domains.knowledge.compilation.limitations import limitation_paragraphs


def material():
    return [
        {
            "ocr_run_id": "ocr_one",
            "canonical_sha256": "1" * 64,
            "manifest_sha256": "2" * 64,
            "identity": {"revision_id": "rev_one"},
            "evidence": {"ev_unread": {}, "ev_text": {}},
            "pages": [
                {
                    "page_number": 1,
                    "blocks": [
                        {
                            "evidence_id": "ev_unread",
                            "type": "figure",
                            "text": "",
                            "requires_review": True,
                        },
                        {"evidence_id": "ev_text", "type": "text", "text": "Dữ liệu nguồn."},
                    ],
                }
            ],
        }
    ]


def raw_draft():
    return {
        "title": "Tóm tắt",
        "sections": [
            {
                "heading": "Nội dung",
                "paragraphs": [{"text": "Dữ liệu nguồn.", "citations": ["ocr_one:ev_text"]}],
            }
        ],
        "unknowns": ["Chưa xác định ngày hiệu lực."],
    }


@pytest.mark.parametrize("kind", ["figure", "formula", "text", "table", "unknown"])
def test_missing_text_has_visible_cited_limit_and_source_stays_immutable(kind):
    documents = material()
    documents[0]["pages"][0]["blocks"][0]["type"] = kind
    original = copy.deepcopy(documents)
    draft = build_draft(json.dumps(raw_draft()), "Tóm tắt", documents, "cmp_one")
    note = draft["sections"][-1]["paragraphs"][0]
    assert note["citations"] == ["ocr_one:ev_unread"]
    assert note["text"] == limitation_paragraphs(documents)[0]["text"]
    assert draft["unknowns"] == raw_draft()["unknowns"]
    assert draft["validation"]["unread_source_blocks"] == "retained"
    assert documents == original


def test_round_trip_edit_does_not_duplicate_limit():
    documents = material()
    first = build_draft(json.dumps(raw_draft()), "Tóm tắt", documents, "cmp_one")
    editable = {key: first[key] for key in ("title", "sections", "unknowns")}
    second = build_draft(json.dumps(editable), "Tóm tắt", documents, "cmp_two")
    assert second["sections"] == first["sections"]


def test_readable_text_does_not_get_an_unread_warning():
    documents = material()
    documents[0]["pages"][0]["blocks"][0]["text"] = "Nội dung đã trích."
    assert limitation_paragraphs(documents) == []


def test_parsed_table_with_rows_is_not_treated_as_missing_text():
    documents = material()
    block = documents[0]["pages"][0]["blocks"][0]
    block["type"] = "table"
    block["table"] = {"status": "parsed", "rows": [[{"text": "Ô nguồn"}]]}
    assert limitation_paragraphs(documents) == []
    block["table"]["status"] = "unparsed"
    assert limitation_paragraphs(documents)[0]["citations"] == ["ocr_one:ev_unread"]
