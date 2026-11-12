"""Identifier codes are names, not numeric value claims.

Regression for Q27: the statement naming "CS-2"/"CS-02" at Bảng 7 was dropped
because the code digit was treated as a table value claim, losing the status
fact. Codes stay whole; real values next to a code are still claims.
"""

import pytest

from qnu.domains.rag.answer.cells import _statement_numbers, catalog, materialize
from qnu.domains.rag.answer.drafting import parse_answer
from qnu.platform.errors import AppException
from tests.unit.test_fact_attribution_946 import (
    answer_with,
    cell,
    unselectable_source,
)


def status_table():
    """CS-02 carries the status; the stray 7 lives on an unmentioned row."""
    return [
        [cell("Quy trình", "s-0-0"), cell("Trạng thái", "s-0-1")],
        [cell("CS-02", "s-1-0"), cell("Cần làm rõ", "s-1-1")],
        [cell("Mã khác", "s-2-0"), cell("7", "s-2-1")],
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        "Trạng thái của CS-2 tại Bảng 7 là “Cần làm rõ”.",
        "Trạng thái của CS-02 tại Bảng 7 là “Cần làm rõ”.",
        "TT-02 ở Bảng 8 và AM/TN-02, NV-16.",
    ],
)
def test_identifier_digits_are_not_value_claims(sentence):
    assert _statement_numbers(sentence) == set()


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("CS-2 đạt 7 tại Bảng 4.", {"7"}),
        ("CT-05 có 0 sinh viên.", {"0"}),
        ("Mã lưu trữ là 7.", {"7"}),
    ],
)
def test_real_value_next_to_an_identifier_stays_a_claim(sentence, expected):
    assert _statement_numbers(sentence) == expected


def test_identifier_status_statement_survives_materialize():
    """Q27: the status statement must not be dropped for naming CS-2."""
    table = unselectable_source(status_table(), [0, 1, 2], key="E1")
    sentence = "Trạng thái của CS-2 tại Bảng 7 là “Cần làm rõ”."
    sources = [table]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1"]}]),
        sources,
    )
    result = materialize(draft, sources, catalog(sources))
    assert [stmt.text for stmt in result.statements] == [sentence]


def test_identifier_does_not_hide_a_fabricated_value():
    """A code mention must not license a value absent from the table."""
    table = unselectable_source(status_table(), [0, 1, 2], key="E1")
    sentence = "CS-2 có 9 sinh viên."
    sources = [table]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1"]}]),
        sources,
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, sources, catalog(sources))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_identifier_does_not_license_another_rows_value():
    """Only the code is stripped; the stray 7 on another row still fails."""
    table = unselectable_source(status_table(), [0, 1, 2], key="E1")
    sentence = "CS-2 có giá trị 7 tại Bảng 3."
    sources = [table]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1"]}]),
        sources,
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, sources, catalog(sources))
    assert exc.value.code == "answer_table_value_not_extractive"
