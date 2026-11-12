import json

import pytest

from qnu.domains.rag.answer.drafting import parse_answer
from qnu.platform.errors import AppException
from tests.unit.test_table_grounding_770 import source


def payload(statements):
    return json.dumps(
        {"status": "answered", "statements": statements, "lookups": [], "assessment": []}
    )


def sources():
    return [
        source([["Name", "Value"], ["A", "10"]], key="E1"),
        source([["Name", "Value"], ["B", "20"]], key="E2"),
    ]


def test_repeated_valid_evidence_ids_are_deduped_keeping_first_position():
    result = parse_answer(
        payload([{"text": "Có căn cứ.", "evidence_ids": ["E2", "E1", "E2"]}]), sources()
    )
    assert result.statements[0].evidence_ids == ["E2", "E1"]


def test_repetition_is_scoped_to_each_statement():
    result = parse_answer(
        payload(
            [
                {"text": "Một.", "evidence_ids": ["E1", "E1"]},
                {"text": "Hai.", "evidence_ids": ["E2", "E1"]},
            ]
        ),
        sources(),
    )
    assert [statement.evidence_ids for statement in result.statements] == [["E1"], ["E2", "E1"]]


def test_foreign_ids_are_still_rejected_after_dedupe():
    with pytest.raises(AppException) as exc:
        parse_answer(
            payload([{"text": "Sai nguồn.", "evidence_ids": ["E1", "E9", "E1"]}]), sources()
        )
    assert exc.value.code == "answer_citation_invalid"
    assert exc.value.validation_issues == [
        {"path": ["statements", 0, "evidence_ids"], "type": "not_allowed"}
    ]
