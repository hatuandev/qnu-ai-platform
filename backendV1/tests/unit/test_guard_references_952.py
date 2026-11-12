"""Structural and negated mentions are not table value claims.

Regression tests for two false positives in _statement_numbers seen live:

1. Q27: "CS-02 tại Bảng 7 ... TT-02 ở Bảng 8" cited an unselectable table that
   contains the digit 7 as an unrelated cell value. The reference "Bảng 7" was
   treated as a data claim, could not bind to any row, and the whole statement
   was dropped.

2. Q18: "... không đồng nghĩa số 0" cited an unselectable table where 0 occurs
   on an unrelated row. The negated definition mention was treated as a value
   claim and the whole statement was dropped.

The guard must keep rejecting real numbers: a value on another row, a value
absent from the table, and any number not in the cited source still fail.
"""

import pytest

from qnu.domains.rag.answer.cells import _statement_numbers, catalog, materialize
from qnu.domains.rag.answer.drafting import parse_answer
from qnu.platform.errors import AppException
from tests.unit.test_fact_attribution_946 import (
    answer_with,
    cell,
    passage_source,
    unselectable_source,
)


def code_table():
    """CS-02 and TT-02 statuses; the stray "7" lives on an unmentioned row."""
    return [
        [cell("Quy trình", "q-0-0"), cell("Ghi chú", "q-0-1")],
        [cell("CS-02", "q-1-0"), cell("Đang thực hiện", "q-1-1")],
        [cell("TT-02", "q-2-0"), cell("Chưa triển khai", "q-2-1")],
        [cell("Mã lưu trữ", "q-3-0"), cell("7", "q-3-1")],
    ]


def definition_table():
    """CT-05 has no value; the stray "0" lives on an unmentioned row."""
    return [
        [cell("Chỉ tiêu", "d-0-0"), cell("Giá trị", "d-0-1")],
        [cell("CT-05", "d-1-0"), cell("–", "d-1-1")],
        [cell("Mã khác", "d-2-0"), cell("0", "d-2-1")],
    ]


def q27_sources():
    table = unselectable_source(code_table(), [0, 1, 2, 3], key="E1")
    sentence = "Không sử dụng trạng thái CS-02 tại Bảng 7 để suy trạng thái TT-02 ở Bảng 8."
    return table, passage_source(sentence, key="E2"), sentence


def q18_sources():
    table = unselectable_source(definition_table(), [0, 1, 2], key="E1")
    sentence = "Dấu “–” tại dòng CT-05 nghĩa là chưa tiến hành đo và không đồng nghĩa số 0."
    return table, passage_source(sentence, key="E2"), sentence


def failed(code, draft, sources):
    with pytest.raises(AppException) as exc:
        materialize(draft, sources, catalog(sources))
    assert exc.value.code == code


# ---------------------------------------------------------------------------
# False positives reproduced from the live G3 answers
# ---------------------------------------------------------------------------


def test_table_reference_is_not_a_value_claim():
    """Q27: "Bảng 7"/"Bảng 8" reference numbers must not drop the statement."""
    table, passage, sentence = q27_sources()
    sources = [table, passage]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1", "E2"]}]),
        sources,
    )
    result = materialize(draft, sources, catalog(sources))
    assert [stmt.text for stmt in result.statements] == [sentence]


def test_negated_number_is_not_a_value_claim():
    """Q18: "không đồng nghĩa số 0" must not drop the statement."""
    table, passage, sentence = q18_sources()
    sources = [table, passage]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1", "E2"]}]),
        sources,
    )
    result = materialize(draft, sources, catalog(sources))
    assert [stmt.text for stmt in result.statements] == [sentence]


def test_reference_and_negation_keep_real_values():
    """A verified value survives next to a reference and a negated mention."""
    rows = [
        [cell("Chỉ tiêu", "n-0-0"), cell("Giá trị", "n-0-1")],
        [cell("CT-05", "n-1-0"), cell("3", "n-1-1")],
        [cell("Mã khác", "n-2-0"), cell("0", "n-2-1")],
    ]
    table = unselectable_source(rows, [0, 1, 2], key="E1")
    sentence = "CT-05 đạt 3 tại Bảng 4, không đồng nghĩa số 0."
    passage = passage_source(sentence, key="E2")
    sources = [table, passage]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1", "E2"]}]),
        sources,
    )
    result = materialize(draft, sources, catalog(sources))
    assert [stmt.text for stmt in result.statements] == [sentence]


# ---------------------------------------------------------------------------
# Negative controls: the guard still rejects real value claims
# ---------------------------------------------------------------------------


def test_reference_does_not_hide_missing_value():
    """Only "Bảng 7" is stripped; the fabricated 9 still fails."""
    table = unselectable_source(code_table(), [0, 1, 2, 3], key="E1")
    sources = [table]
    draft = parse_answer(
        answer_with([{"text": "Bảng 7 ghi 9 dòng.", "evidence_ids": ["E1"]}]),
        sources,
    )
    failed("answer_table_value_not_extractive", draft, sources)


def test_reference_does_not_license_cross_row_value():
    """Naming row CS-02 must not let another row's 7 through.

    The table suppresses passage support for its digits only when the
    statement attributes a row of that table (Q10 false positive keeps an
    unattributed table from blocking a passage number), so this cross-row
    control names the row the value is wrongly attributed to.
    """
    table = unselectable_source(code_table(), [0, 1, 2, 3], key="E1")
    sentence = "CS-02 có giá trị 7 tại Bảng 3."
    passage = passage_source(sentence, key="E2")
    sources = [table, passage]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1", "E2"]}]),
        sources,
    )
    failed("answer_table_value_not_extractive", draft, sources)


def test_plain_value_after_negation_word_still_checked():
    """ "CT-05 bằng 0" asserts a value; it stays a claim and fails."""
    table = unselectable_source(definition_table(), [0, 1, 2], key="E1")
    sentence = "CT-05 bằng 0."
    passage = passage_source(sentence, key="E2")
    sources = [table, passage]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1", "E2"]}]),
        sources,
    )
    failed("answer_table_value_not_extractive", draft, sources)


def test_fabricated_value_with_negation_elsewhere_fails():
    """A negated mention elsewhere must not shield a fabricated value."""
    table = unselectable_source(definition_table(), [0, 1, 2], key="E1")
    sources = [table]
    draft = parse_answer(
        answer_with([{"text": "CT-05 không phải là 0 mà đạt 42.", "evidence_ids": ["E1"]}]),
        sources,
    )
    failed("answer_table_value_not_extractive", draft, sources)


def test_claimed_row_value_still_accepted():
    """Control: a value on the mentioned row still verifies."""
    table = unselectable_source(code_table(), [0, 1, 2, 3], key="E1")
    sentence = "Mã lưu trữ là 7."
    sources = [table]
    draft = parse_answer(
        answer_with([{"text": sentence, "evidence_ids": ["E1"]}]),
        sources,
    )
    result = materialize(draft, sources, catalog(sources))
    assert [stmt.text for stmt in result.statements] == [sentence]


# ---------------------------------------------------------------------------
# Token extraction contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Xem Bảng 7 và Bảng số 5.2.",
        "Theo Điều 14, Khoản 2, Mục 3, Chương 4, Phần 5.",
        "Phụ lục 6, Hình 7, Sơ đồ 8, Biểu đồ 9, Công thức 10.",
        "không đồng nghĩa với số 0",
        "chứ không phải là 0",
        "không bằng 0",
        "không được hiểu là 0",
        "không có nghĩa là 0",
    ],
)
def test_structure_and_negation_leave_no_tokens(text):
    assert _statement_numbers(text) == set()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("giá trị 7", {"7"}),
        ("0 sinh viên", {"0"}),
        ("không đạt 0", {"0"}),
        ("Bảng 7 ghi 9 dòng", {"9"}),
        ("không phải là 0 mà đạt 42", {"42"}),
    ],
)
def test_real_claims_keep_their_tokens(text, expected):
    assert _statement_numbers(text) == expected
