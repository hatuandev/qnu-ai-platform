"""Image limitations distinguish missing extraction from linked unverified OCR."""

import copy
import json

import pytest

from qnu.domains.knowledge.compilation.drafting import build_draft
from qnu.domains.knowledge.compilation.limitations import limitation_paragraphs


def material():
    return {
        "ocr_run_id": "ocr_image",
        "canonical_sha256": "1" * 64,
        "manifest_sha256": "2" * 64,
        "identity": {"revision_id": "rev_image"},
        "evidence": {"ev_image": {}, "ev_text": {}},
        "pages": [
            {
                "page_number": 2,
                "blocks": [
                    {
                        "evidence_id": "ev_image",
                        "type": "figure",
                        "image": {"asset_no": 20001},
                        "text": "",
                        "requires_review": True,
                    },
                    {
                        "evidence_id": "ev_text",
                        "type": "text",
                        "source_image_asset_no": 20001,
                        "text": "Văn bản OCR chưa đối chiếu.",
                        "requires_review": True,
                    },
                ],
            }
        ],
    }


def test_linked_text_has_honest_cited_limit_and_preserves_source():
    document = material()
    original = copy.deepcopy(document)
    [note] = limitation_paragraphs([document])
    assert "đã có văn bản OCR" in note["text"]
    assert "Chưa xác minh" in note["text"]
    assert note["citations"] == ["ocr_image:ev_image", "ocr_image:ev_text"]
    raw = {
        "title": "Ảnh",
        "sections": [
            {
                "heading": "Nguồn",
                "paragraphs": [{"text": "Văn bản OCR.", "citations": ["ocr_image:ev_text"]}],
            }
        ],
        "unknowns": [],
    }
    draft = build_draft(json.dumps(raw), "Ảnh", [document], "cmp_image")
    assert note in draft["sections"][-1]["paragraphs"]
    assert document == original


@pytest.mark.parametrize("case", ["asset", "page", "document", "empty", "no_asset", "blank_table"])
def test_only_readable_explicit_same_page_same_document_links_change_warning(case):
    document = material()
    image, text = document["pages"][0]["blocks"]
    documents = [document]
    if case == "asset":
        text["source_image_asset_no"] += 1
    elif case == "page":
        document["pages"][0]["blocks"].remove(text)
        document["pages"].append({"page_number": 3, "blocks": [text]})
    elif case == "document":
        document["pages"][0]["blocks"].remove(text)
        documents.append(
            {"ocr_run_id": "ocr_other", "pages": [{"page_number": 2, "blocks": [text]}]}
        )
    elif case == "empty":
        text["text"] = " "
    elif case == "blank_table":
        text.update(text="", type="table", table={"status": "parsed", "rows": [[{"text": ""}]]})
    else:
        image.pop("image")
    note = limitation_paragraphs(documents)[0]
    assert "chưa có văn bản trích xuất" in note["text"]
    assert note["citations"] == ["ocr_image:ev_image"]


def test_readable_linked_table_is_also_recognised():
    document = material()
    text = document["pages"][0]["blocks"][1]
    text.update(text="", type="table", table={"status": "parsed", "rows": [[{"text": "0012"}]]})
    assert "đã có văn bản OCR" in limitation_paragraphs([document])[0]["text"]


def test_all_linked_citations_survive_more_than_one_draft_paragraph():
    document = material()
    page = document["pages"][0]
    for i in range(120):
        page["blocks"].append({**page["blocks"][1], "evidence_id": f"ev_more_{i}"})
    notes = limitation_paragraphs([document])
    assert len(notes) == 2
    assert all(len(n["citations"]) <= 100 for n in notes)
    assert len({c for n in notes for c in n["citations"]}) == 122
