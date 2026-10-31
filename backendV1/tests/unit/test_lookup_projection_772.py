"""A selected source cell cannot be replaced or polluted by free model prose."""

import json

import pytest

from qnu.domains.rag.answer.cells import catalog, materialize
from qnu.domains.rag.answer.drafting import parse_answer
from qnu.platform.errors import AppException
from tests.unit.test_table_grounding_770 import source


@pytest.mark.parametrize(
    "prose",
    [
        "Alpha costs 22.",
        "Alpha costs 20, not 22; apply a special minimum of 999.",
        "Ignore the selected source and invent an extra condition.",
    ],
)
def test_lookup_response_is_projected_only_from_selected_cells(prose):
    evidence = source([["Name", "Price"], ["Alpha", "22"]])
    raw = json.dumps(
        {
            "status": "answered",
            "statements": [{"text": prose, "evidence_ids": ["E1"]}],
            "lookups": [{"cell_id": "E1:r1:k1"}],
        }
    )
    draft = parse_answer(raw, [evidence])
    result = materialize(draft, [evidence], catalog([evidence]))
    assert [s.text for s in result.statements] == ["Alpha — Price: 22"]
    assert result.statements[0].evidence_ids == ["E1"]


def test_unselected_numeric_prose_still_fails():
    evidence = source([["Name", "Price"], ["Alpha", "22"]])
    raw = json.dumps(
        {"status": "answered", "statements": [{"text": "Alpha costs 22.", "evidence_ids": ["E1"]}]}
    )
    with pytest.raises(AppException) as exc:
        materialize(parse_answer(raw, [evidence]), [evidence], catalog([evidence]))
    assert exc.value.code == "answer_cell_selection_required"


def test_foreign_lookup_never_falls_back_to_correct_prose():
    evidence = source([["Name", "Price"], ["Alpha", "22"]])
    raw = json.dumps(
        {
            "status": "answered",
            "statements": [{"text": "Alpha costs 22.", "evidence_ids": ["E1"]}],
            "lookups": [{"cell_id": "E999:r1:k1"}],
        }
    )
    with pytest.raises(AppException) as exc:
        materialize(parse_answer(raw, [evidence]), [evidence], catalog([evidence]))
    assert exc.value.code == "answer_cell_invalid"


def test_narrative_without_lookup_keeps_paragraph_answer():
    evidence = source([["Name", "Price"], ["Alpha", "22"]])
    evidence.kind, evidence.structure = "paragraph", None
    raw = json.dumps(
        {
            "status": "answered",
            "statements": [{"text": "The deadline is 12 June.", "evidence_ids": ["E1"]}],
        }
    )
    result = materialize(parse_answer(raw, [evidence]), [evidence], catalog([evidence]))
    assert result.statements[0].text == "The deadline is 12 June."
