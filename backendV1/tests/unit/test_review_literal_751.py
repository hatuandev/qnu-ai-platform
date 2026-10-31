from copy import deepcopy

import pytest

from qnu.domains.knowledge.compilation.review.literal import assess


def fixture():
    source = {
        "id": "ocr:cell",
        "kind": "table_cell",
        "table_id": "ocr:table",
        "text": "15.0",
        "row": 2,
        "column": 1,
        "header": False,
        "row_span": 1,
        "col_span": 1,
    }
    draft = {**source, "id": "table:1:row:2:cell:1", "source_id": source["id"]}
    return {
        "source_units": [source],
        "draft_units": [draft],
        "draft": {
            "source_tables": [{"citation": "ocr:table"}],
        },
    }


def test_exact_retention_is_checked_without_claiming_ocr_accuracy():
    data = fixture()
    result = assess(data, data)
    assert result["source_assessments"][0]["status"] == "covered"
    assert result["draft_assessments"][0]["source_ids"] == ["ocr:cell"]
    assert "không xác minh OCR" in result["draft_assessments"][0]["explanation"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("text", "150"),
        ("row", 3),
        ("column", 2),
        ("header", True),
        ("row_span", 2),
        ("col_span", 2),
        ("source_id", "other"),
    ],
)
def test_any_disagreement_falls_back_to_semantic_review(field, value):
    data = fixture()
    data["draft_units"][0][field] = value
    assert assess(data, data) is None


def test_wrong_table_duplicate_or_narrative_cannot_bypass_review():
    data = fixture()
    bad = deepcopy(data)
    bad["draft"]["source_tables"][0]["citation"] = "ocr:other"
    assert assess(bad, bad) is None
    duplicate = deepcopy(data)
    duplicate["draft_units"].append(deepcopy(duplicate["draft_units"][0]))
    assert assess(duplicate, duplicate) is None
    bad = deepcopy(data)
    bad["draft_units"][0]["id"] = "table:0:row:2:cell:1"
    assert assess(bad, bad) is None
    data["draft_units"].append({"id": "paragraph", "kind": "paragraph", "text": "Condition"})
    assert assess(data, data) is None
