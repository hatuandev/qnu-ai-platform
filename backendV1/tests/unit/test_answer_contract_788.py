import copy

import pytest

from qnu.domains.knowledge.index.table_dependencies import dependencies
from qnu.domains.rag.answer.cells import catalog, materialize
from qnu.domains.rag.answer.drafting import parse_answer
from tests.unit.test_table_context_769 import document
from tests.unit.test_table_grounding_770 import selected, source


@pytest.mark.parametrize(
    "rows",
    [
        [["Level", "Equivalent"], ["4.5", "7.5"], ["5.5", "9.5"]],
        [["Category", "Count", "Percent"], ["Alpha", "1.200", "40%"], ["Beta", "1.800", "60%"]],
    ],
)
def test_pinned_native_typed_header_is_derived_without_editing_raw(rows):
    doc = document()
    doc["pages"] = doc["pages"][:1]
    table = doc["pages"][0]["blocks"][0]["table"]
    table["rows"] = source(rows).structure["rows"]
    table["column_count"] = len(rows[0])
    for row in table["rows"]:
        for cell in row:
            cell["header"] = False
    original = copy.deepcopy(doc)
    proof = dependencies(doc)["run:t1"]
    assert proof["basis"] == "native_typed_columns/v1"
    s = source(rows, headers=0, table="run:t1")
    link = {**proof, "chunk_id": s.chunk_id, "support_ids": [s.chunk_id]}
    cells = catalog([s], [link])
    assert cells["tables"][0]["cells"]
    result = materialize(parse_answer(selected("E1:r1:k1"), [s]), [s], cells)
    assert rows[1][0] in result.statements[0].text
    assert rows[1][1] in result.statements[0].text
    assert doc == original


def test_unproved_header_does_not_become_selectable():
    s = source([["Level", "Equivalent"], ["4.5", "7.5"], ["5.5", "9.5"]], headers=0)
    assert not catalog([s])["tables"]


def test_explicit_header_allows_numeric_row_key_with_source_refs():
    s = source([["Threshold", "Rate"], ["3.5", "0.2"], ["4.5", "0.4"]])
    cells = catalog([s])
    target = next(c for c in cells["tables"][0]["cells"] if c["cell_id"] == "E1:r2:k1")
    assert target["subject"] == "Threshold: 4.5"
    assert len(target["source_cells"]) == 4


@pytest.mark.parametrize("defect", ["review", "ocr", "no_contrast"])
def test_native_type_contrast_never_overrides_ambiguous_source(defect):
    doc = document()
    block = doc["pages"][0]["blocks"][0]
    if defect == "review":
        block["requires_review"] = True
    elif defect == "ocr":
        doc["pages"][0]["extraction_method"] = "ocr"
    else:
        block["table"]["rows"][1][0]["text"] = "alpha"
        block["table"]["rows"][2][0]["text"] = "beta"
        block["table"]["rows"][1][-1]["text"] = "red"
        block["table"]["rows"][2][-1]["text"] = "blue"
    assert "run:t1" not in dependencies(doc)


def test_schema_is_closed_and_required_fields_match_validator():
    from qnu.domains.rag.answer.drafting import output_schema

    schema = output_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"status", "statements", "lookups"}
    assert schema["$defs"]["Statement"]["additionalProperties"] is False
    assert "default" not in schema["properties"]["lookups"]


def test_invalid_output_diagnostics_do_not_copy_input_or_untrusted_keys():
    from qnu.platform.errors import AppException

    with pytest.raises(AppException) as exc:
        parse_answer('{"private-source-key":"private-source-value"}', [])
    detail = str(exc.value.validation_issues)
    assert "private-source" not in detail
    assert "<extra>" in detail and "missing" in detail


def test_original_cited_passage_restores_conditions_without_rewriting_chunk():
    from qnu.domains.rag.answer.projection import evidence_item
    from qnu.domains.rag.answer.source_text import passages

    s = source([["Name", "Value"], ["A", "10"]])
    s.kind = "paragraph"
    s.citations = {"run:block": {"page": 1}}
    original = s.text
    docs = [
        {
            "ocr_run_id": "run",
            "pages": [
                {
                    "blocks": [
                        {
                            "evidence_id": "block",
                            "text": "Only participants who registered in 2031 may join.",
                        },
                        {"evidence_id": "unrelated", "text": "Unpublished unrelated facts."},
                    ]
                }
            ],
        }
    ]
    s.source_passages = passages(s, docs)
    view = evidence_item(s, "E1")
    assert "registered in 2031" in view["text"]
    assert "Unpublished" not in view["text"]
    assert s.text == original and view["source_passage_refs"] == ["run:block"]


def test_reasoning_observation_preserves_unknown_without_storing_thoughts():
    import json
    from types import SimpleNamespace

    from qnu.domains.rag.answer.drafting import response_observation

    result = SimpleNamespace(
        raw_body=json.dumps(
            {"choices": [{"message": {"reasoning_content": "private thought"}}]}
        ).encode()
    )
    assert response_observation(result) == {"reasoning_chars": 15, "reasoning_tokens": None}
    result.raw_body = b'{"choices":[{"message":{}}]}'
    assert response_observation(result) == {"reasoning_chars": None, "reasoning_tokens": None}
