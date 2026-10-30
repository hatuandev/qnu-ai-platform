"""Review receives empty evidence without inventing text or removing uncertainty."""

import copy
import json

import pytest

from qnu.domains.knowledge.compilation.review.material import source_units
from qnu.domains.knowledge.compilation.review.report import (
    build_report,
    messages_for,
    output_schema,
    validate_content,
)
from qnu.platform.errors import AppException


def material(kind="figure", text=""):
    blocks = [
        {
            "evidence_id": "ev_empty",
            "bbox": {"x0": 0, "y0": 0, "x1": 1, "y1": 1},
            "type": kind,
            "text": text,
            "origin": "native",
            "requires_review": True,
        },
        {"evidence_id": "ev_text", "bbox": {}, "type": "text", "text": "Nội dung OCR"},
    ]
    return [
        {
            "ocr_run_id": "ocr_one",
            "identity": {"revision_id": "rev_one"},
            "pages": [{"page_number": 1, "blocks": blocks}],
        }
    ]


@pytest.mark.parametrize("kind", ["figure", "formula", "unknown", "text", "table"])
@pytest.mark.parametrize("text", ["", "  "])
def test_empty_block_remains_available_to_reviewer(kind, text):
    documents = material(kind, text)
    original = copy.deepcopy(documents)
    units = source_units(documents)
    assert [u["id"] for u in units] == ["ocr_one:ev_empty", "ocr_one:ev_text"]
    assert units[0]["text"] == text and units[0]["kind"] == kind
    assert units[0]["evidence_id"] == "ev_empty"
    assert units[0]["origin"] == "native" and units[0]["requires_review"] is True
    assert units[0]["bbox"] == documents[0]["pages"][0]["blocks"][0]["bbox"]
    assert units[0]["identity"] == {"revision_id": "rev_one"}
    assert documents == original


def test_empty_unit_reaches_model_and_schema_and_cannot_be_silently_skipped():
    documents = material()
    payload = {
        "topic": "Tóm tắt",
        "documents": documents,
        "source_units": source_units(documents),
        "draft_units": [{"id": "unknown:1", "kind": "unknown", "text": "Chưa rõ hình ảnh"}],
    }
    sent = json.loads(messages_for(payload, structured=True)[-1].content)
    assert sent["source_units"][0]["id"] == "ocr_one:ev_empty"
    assert sent["source_units"][0]["text"] == ""
    required = output_schema(payload)["properties"]["source_assessments"]["required"]
    assert "ocr_one:ev_empty" in required
    checks = {
        "source_assessments": [
            {
                "source_id": u["id"],
                "status": "uncertain",
                "draft_ids": [],
                "explanation": "Không đủ căn cứ về nội dung hình.",
                "suggested_action": "Đối chiếu ảnh.",
            }
            for u in payload["source_units"]
        ],
        "draft_assessments": [
            {
                "draft_id": "unknown:1",
                "status": "uncertain",
                "source_ids": ["ocr_one:ev_empty"],
                "explanation": "Cần đối chiếu ảnh.",
                "suggested_action": "Kiểm tra nguồn.",
            }
        ],
    }
    report = build_report(json.dumps(checks), payload, "review_one", "bundle_hash")
    assert report["verdict"] == "needs_attention"
    assert report["findings"][0]["sources"][0]["text"] == ""
    checks["source_assessments"].pop(0)
    with pytest.raises(AppException, match="Review"):
        validate_content(json.dumps(checks), payload)


def test_empty_blocks_in_different_documents_keep_distinct_references():
    documents = material()
    other = copy.deepcopy(documents[0])
    other["ocr_run_id"] = "ocr_two"
    other["identity"] = {"revision_id": "rev_two"}
    units = source_units([documents[0], other])
    assert len({u["id"] for u in units}) == 4
    assert units[2]["id"] == "ocr_two:ev_empty"
    assert units[2]["identity"] == {"revision_id": "rev_two"}


def test_table_cells_keep_their_own_ids_and_literal_empty_values():
    documents = material("table")
    block = documents[0]["pages"][0]["blocks"][0]
    block["table"] = {
        "status": "parsed",
        "rows": [
            [{"evidence_id": "ev_cell", "text": "", "row_span": 1, "col_span": 1, "header": False}]
        ],
    }
    cell = source_units(documents)[0]
    assert cell["id"] == "ocr_one:ev_cell" and cell["evidence_id"] == "ev_cell"
    assert cell["table_id"] == "ocr_one:ev_empty"
    assert cell["kind"] == "table_cell" and cell["text"] == ""
