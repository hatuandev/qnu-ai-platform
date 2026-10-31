"""Readable cell text must not lose source geometry or turn unrelated data into a table."""

import copy
import json

from qnu.domains.knowledge.index.presentation import reading_text, rerank_text
from qnu.domains.rag.answer.projection import evidence_item
from tests.unit.test_answer_projection_764 import source


def test_wrapped_subject_reaches_reranker_as_words_without_json_noise():
    structure = {
        "source_table_citation": "run:table",
        "original_row_count": 3,
        "original_column_count": 2,
        "row_indices": [1],
        "rows": [
            [
                {"text": "Particle\nPhysics", "row_span": 2, "col_span": 1, "header": False},
                {"text": "42", "row_span": 1, "col_span": 1, "header": False},
            ]
        ],
        "page_notes": [{"text": "Metric is preliminary", "citation": "run:note"}],
    }
    item = source("Title\n" + json.dumps(structure, ensure_ascii=False, sort_keys=True), structure)
    original = copy.deepcopy(item)
    assert rerank_text(item) == "Title row[1]: Particle Physics | 42"
    sent = evidence_item(item, "E3")
    assert sent["structure"] == structure
    assert sent["text"] == reading_text(item)
    assert item == original
    assert sent["structure"]["rows"][0][0]["row_span"] == 2


def test_unrecognized_or_incomplete_serialization_is_not_reinterpreted():
    item = source('{"text":"keep\\nthis"}', {"rows": [[{"text": "raw"}]]})
    assert reading_text(item) == item.text
    assert evidence_item(item, "E2")["structure"] == item.structure


def test_paragraph_normalization_does_not_rewrite_fact_or_select_an_exception():
    item = source("General: a\nSpecific: b", {"context": {"parent": "section"}})
    item.kind = "paragraph"
    assert reading_text(item) == item.text
    assert rerank_text(item) == "General: a Specific: b"
