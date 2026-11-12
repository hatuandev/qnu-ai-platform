"""Per-fact verification: each number in a statement binds to its row and column.

Regression tests for three misattribution bugs in _table_support:

1. Cross-row swap: "Alpha = 22 và Beta = 18" accepted when Alpha=18, Beta=22.
   The flat set union collapses subject-value binding; each row's numbers
   leak into the global supported set.

2. Cross-column year: "Alpha năm 2025 là 22" accepted when 2025 column = 18
   and 2026 column = 22, but the header is not resolved so _field_conflicts
   cannot fire.

3. Cross-metric: numbers are individually correct for the row but attributed
   to the wrong metric. The same number appearing in cited passage text
   must not serve as proof for a different metric.
"""

import json

import pytest

from qnu.domains.rag.answer.cells import catalog, materialize
from qnu.domains.rag.answer.drafting import parse_answer
from qnu.domains.rag.answer.schemas import EvidenceSource
from qnu.platform.errors import AppException


def cell(text, ref, *, rs=1, cs=1, header=False):
    return {
        "text": text,
        "row_span": rs,
        "col_span": cs,
        "header": header,
        "evidence_id": ref,
    }


def two_row_table():
    """Alpha = 18, Beta = 22. Two rows, one value column. No header marks
    so the table is unselectable and goes through _unsupported_numbers."""
    return [
        [cell("Name", "h-0-0"), cell("Value", "h-0-1")],
        [cell("Alpha", "h-1-0"), cell("18", "h-1-1")],
        [cell("Beta", "h-2-0"), cell("22", "h-2-1")],
    ]


def two_column_table():
    """Alpha | 18 | 22 — two value columns for 2025 and 2026. No header marks."""
    return [
        [cell("Name", "c-0-0"), cell("2025", "c-0-1"), cell("2026", "c-0-2")],
        [cell("Alpha", "c-1-0"), cell("18", "c-1-1"), cell("22", "c-1-2")],
    ]


def two_metric_table():
    """Alpha row has Quy mô=100 and Ghi nhận=50. No header marks."""
    return [
        [cell("Name", "m-0-0"), cell("Quy mô", "m-0-1"), cell("Ghi nhận", "m-0-2")],
        [cell("Alpha", "m-1-0"), cell("100", "m-1-1"), cell("50", "m-1-2")],
    ]


def two_column_table_with_header():
    """Alpha | 18 | 22 with header marks on row 0. Fields resolve to
    [Name], [2025], [2026]."""
    return [
        [
            cell("Name", "c-0-0", header=True),
            cell("2025", "c-0-1", header=True),
            cell("2026", "c-0-2", header=True),
        ],
        [cell("Alpha", "c-1-0"), cell("18", "c-1-1"), cell("22", "c-1-2")],
    ]


def two_metric_table_with_header():
    """Alpha row has Quy mô=100 and Ghi nhận=50. Header marks on row 0."""
    return [
        [
            cell("Name", "m-0-0", header=True),
            cell("Quy mô", "m-0-1", header=True),
            cell("Ghi nhận", "m-0-2", header=True),
        ],
        [cell("Alpha", "m-1-0"), cell("100", "m-1-1"), cell("50", "m-1-2")],
    ]


def chunk(rows, indices, *, key, total=None, columns=None, citation="run:t"):
    total = total if total is not None else len(rows)
    columns = columns if columns is not None else len(rows[0])
    refs = {
        citation.split(":", 1)[0] + ":" + c["evidence_id"]: {"page": 1} for row in rows for c in row
    }
    return EvidenceSource(
        evidence_id=key,
        chunk_id=key,
        document_id="doc",
        version_id="v",
        publication_decision_id="published",
        kind="table",
        score=1,
        text="raw table",
        citations={citation: {"page": 1}, **refs},
        structure={
            "source_table_citation": citation,
            "original_row_count": total,
            "original_column_count": columns,
            "rows": rows,
            "row_indices": indices,
        },
    )


def answer_with(statements, lookups=()):
    return json.dumps(
        {
            "status": "answered",
            "statements": statements,
            "lookups": [{"cell_id": key} for key in lookups],
        }
    )


def unselectable_source(rows, indices, *, key="E1", text="", citation="run:t"):
    """Table source without header marks → unselectable, goes through
    _unsupported_numbers path."""
    s = chunk(rows, indices, key=key, citation=citation)
    s.text = text or "\n".join(
        f"row[{i}]: " + " | ".join(c["text"] for c in row) for i, row in zip(indices, rows)
    )
    return s


def passage_source(text, *, key="E2"):
    """Non-table source: its visible text numbers are all 'supported'."""
    return EvidenceSource(
        evidence_id=key,
        chunk_id=key,
        document_id="doc",
        version_id="v",
        publication_decision_id="published",
        kind="passage",
        score=1,
        text=text,
        citations={"run:t": {"page": 1}},
        structure={
            "source_table_citation": "run:t",
            "original_row_count": 1,
            "original_column_count": 1,
            "rows": [[cell("", "p-0-0")]],
            "row_indices": [0],
        },
        source_passages=[{"text": text, "citation": "run:t", "position": "1"}],
    )


# ---------------------------------------------------------------------------
# Bug 1: Cross-row swap in a single statement
# ---------------------------------------------------------------------------


def test_cross_row_swap_both_numbers_rejected():
    """Alpha=18, Beta=22. Statement "Alpha = 22 và Beta = 18" swaps values.

    Current code bags numbers: Alpha row contributes {18}, Beta row contributes
    {22}. Union = {18, 22}. Statement tokens = {22, 18}. Missing = empty.
    The swap passes because the set loses subject-value binding.
    """
    s = unselectable_source(two_row_table(), [0, 1, 2])
    draft = parse_answer(
        answer_with([{"text": "Alpha = 22 và Beta = 18", "evidence_ids": ["E1"]}]),
        [s],
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_cross_row_swap_correct_values_accepted():
    """Control: "Alpha = 18 và Beta = 22" must still pass."""
    s = unselectable_source(two_row_table(), [0, 1, 2])
    draft = parse_answer(
        answer_with([{"text": "Alpha = 18 và Beta = 22", "evidence_ids": ["E1"]}]),
        [s],
    )
    result = materialize(draft, [s], catalog([s]))
    assert [stmt.text for stmt in result.statements] == ["Alpha = 18 và Beta = 22"]


# ---------------------------------------------------------------------------
# Bug 2: Cross-column year misattribution
# ---------------------------------------------------------------------------


def test_cross_column_year_swap_without_header_marks_rejected():
    """Alpha | 18 | 22 for 2025 | 2026 but header cells have NO header marks.
    _fields returns empty, so _field_conflicts cannot fire. The statement
    "Alpha năm 2025 là 22" must still be rejected because the number 22 is
    on a different column than the one labeled 2025.
    """
    s = unselectable_source(two_column_table(), [0, 1])
    draft = parse_answer(
        answer_with([{"text": "Alpha năm 2025 là 22", "evidence_ids": ["E1"]}]),
        [s],
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_cross_column_year_correct_without_header_marks_accepted():
    """Control: "Alpha năm 2025 là 18" must pass even without header marks."""
    s = unselectable_source(two_column_table(), [0, 1])
    draft = parse_answer(
        answer_with([{"text": "Alpha năm 2025 là 18", "evidence_ids": ["E1"]}]),
        [s],
    )
    result = materialize(draft, [s], catalog([s]))
    assert [stmt.text for stmt in result.statements] == ["Alpha năm 2025 là 18"]


def test_cross_column_year_swap_with_header_marks_rejected():
    """Alpha | 18 | 22 with header marks on row 0. Fields resolve to
    [Name], [2025], [2026]. Statement says "Alpha năm 2025 là 22" — taking
    2026's value for 2025. _field_conflicts should catch this because the
    column path for 22 says 2026 but the statement says 2025.

    Note: with header marks the table is selectable and would normally require
    cell selection. But if the model provides no lookups and the statement
    cites the table, the _unsupported_numbers path still runs because
    selectable.intersection(evidence_ids) is non-empty — wait, no. With
    selectable tables, materialize raises answer_cell_selection_required
    before reaching _unsupported_numbers. So this test must use a table
    where the header row is excluded from catalog (e.g. header marks present
    but no _ref available for the cell → catalog produces no cells →
    unselectable). We simulate by removing the evidence_id refs from the
    citation map so _ref returns None.
    """
    # To make the table unselectable while still having header marks, we
    # remove the citation refs that _ref needs. _ref checks if the composed
    # ref string is in source.citations. If not, it returns None and the
    # catalog produces no cells for that position.
    rows = two_column_table_with_header()
    s = chunk(rows, [0, 1], key="E1", total=2, columns=3)
    # Override citations to only have the table citation, no per-cell refs.
    s.citations = {"run:t": {"page": 1}}
    s.text = "row[0]: Name | 2025 | 2026\nrow[1]: Alpha | 18 | 22"
    draft = parse_answer(
        answer_with([{"text": "Alpha năm 2025 là 22", "evidence_ids": ["E1"]}]),
        [s],
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_cross_column_year_correct_with_header_marks_accepted():
    """Control: "Alpha năm 2025 là 18" with header marks must pass."""
    rows = two_column_table_with_header()
    s = chunk(rows, [0, 1], key="E1", total=2, columns=3)
    s.citations = {"run:t": {"page": 1}}
    s.text = "row[0]: Name | 2025 | 2026\nrow[1]: Alpha | 18 | 22"
    draft = parse_answer(
        answer_with([{"text": "Alpha năm 2025 là 18", "evidence_ids": ["E1"]}]),
        [s],
    )
    result = materialize(draft, [s], catalog([s]))
    assert [stmt.text for stmt in result.statements] == ["Alpha năm 2025 là 18"]


# ---------------------------------------------------------------------------
# Bug 3: Cross-metric misattribution
# ---------------------------------------------------------------------------


def test_cross_metric_wrong_value_without_header_marks_rejected():
    """Alpha row has Quy mô=100, Ghi nhận=50. No header marks. Statement says
    "Alpha quy mô 50" — taking Ghi nhận's value for Quy mô.
    """
    s = unselectable_source(two_metric_table(), [0, 1])
    draft = parse_answer(
        answer_with([{"text": "Alpha quy mô 50", "evidence_ids": ["E1"]}]),
        [s],
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_cross_metric_correct_value_without_header_marks_accepted():
    """Control: "Alpha quy mô 100" must pass."""
    s = unselectable_source(two_metric_table(), [0, 1])
    draft = parse_answer(
        answer_with([{"text": "Alpha quy mô 100", "evidence_ids": ["E1"]}]),
        [s],
    )
    result = materialize(draft, [s], catalog([s]))
    assert [stmt.text for stmt in result.statements] == ["Alpha quy mô 100"]


def test_cross_metric_wrong_value_with_header_marks_rejected():
    """Alpha row has Quy mô=100, Ghi nhận=50. Header marks present but table
    is unselectable (no per-cell refs). Statement "Alpha ghi nhận 100" takes
    Quy mô's value for Ghi nhận.
    """
    rows = two_metric_table_with_header()
    s = chunk(rows, [0, 1], key="E1", total=2, columns=3)
    s.citations = {"run:t": {"page": 1}}
    s.text = "row[0]: Name | Quy mô | Ghi nhận\nrow[1]: Alpha | 100 | 50"
    draft = parse_answer(
        answer_with([{"text": "Alpha ghi nhận 100", "evidence_ids": ["E1"]}]),
        [s],
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_cross_metric_number_in_passage_not_proof():
    """Alpha has Quy mô=100 (table, unselectable). A passage source cites the
    number 100 in context of "ghi nhận". The statement claims "Alpha ghi nhận
    100" — the wrong metric. The passage text containing 100 must not override
    the table's column binding.

    Current behaviour: the passage source contributes all its numbers to the
    supported set via _numbers(_visible_text(source)). So 100 is globally
    supported, masking the table's column misattribution. This test asserts
    that the statement should be rejected because the TABLE source does not
    confirm the metric binding — the passage alone cannot prove a table cell's
    value for a different metric.
    """
    table_source = unselectable_source(two_metric_table(), [0, 1], key="E1")
    passage = passage_source("Kết quả ghi nhận của Alpha là 100 sinh viên.", key="E2")
    draft = parse_answer(
        answer_with([{"text": "Alpha ghi nhận 100", "evidence_ids": ["E1", "E2"]}]),
        [table_source, passage],
    )
    with pytest.raises(AppException) as exc:
        materialize(
            draft,
            [table_source, passage],
            catalog([table_source, passage]),
        )
    assert exc.value.code == "answer_table_value_not_extractive"


# ---------------------------------------------------------------------------
# Multi-row / multi-year positive cases
# ---------------------------------------------------------------------------


def test_multi_row_correct_values_accepted():
    """Alpha=18 và Beta=22 in separate statements — each correct."""
    s = unselectable_source(two_row_table(), [0, 1, 2])
    draft = parse_answer(
        answer_with(
            [
                {"text": "Alpha: 18", "evidence_ids": ["E1"]},
                {"text": "Beta: 22", "evidence_ids": ["E1"]},
            ]
        ),
        [s],
    )
    result = materialize(draft, [s], catalog([s]))
    assert [stmt.text for stmt in result.statements] == ["Alpha: 18", "Beta: 22"]


def test_multi_year_correct_values_accepted():
    """Alpha 2025=18 và 2026=22 in one statement — both correct."""
    s = unselectable_source(two_column_table(), [0, 1])
    draft = parse_answer(
        answer_with([{"text": "Alpha năm 2025 là 18 và năm 2026 là 22", "evidence_ids": ["E1"]}]),
        [s],
    )
    result = materialize(draft, [s], catalog([s]))
    assert "Alpha năm 2025 là 18 và năm 2026 là 22" in [stmt.text for stmt in result.statements]


# ---------------------------------------------------------------------------
# Swap inside one statement: both labels and both values in the same sentence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("marked", [False, True])
def test_swap_within_one_multi_year_statement_rejected(marked):
    """Alpha 2025=18, 2026=22. The sentence "2025 là 22, năm 2026 là 18"
    swaps both values; naming both years must not license the swap."""
    rows = two_column_table_with_header() if marked else two_column_table()
    s = chunk(rows, [0, 1], key="E1", total=2, columns=3)
    if marked:
        s.citations = {"run:t": {"page": 1}}
    s.text = "row[0]: Name | 2025 | 2026\nrow[1]: Alpha | 18 | 22"
    draft = parse_answer(
        answer_with(
            [
                {
                    "text": "Alpha năm 2025 là 22, năm 2026 là 18",
                    "evidence_ids": ["E1"],
                }
            ]
        ),
        [s],
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


@pytest.mark.parametrize("marked", [False, True])
def test_swap_within_one_multi_year_statement_correct_values_accepted(marked):
    """Control: "2025 là 18, năm 2026 là 22" keeps the source binding."""
    rows = two_column_table_with_header() if marked else two_column_table()
    s = chunk(rows, [0, 1], key="E1", total=2, columns=3)
    if marked:
        s.citations = {"run:t": {"page": 1}}
    s.text = "row[0]: Name | 2025 | 2026\nrow[1]: Alpha | 18 | 22"
    draft = parse_answer(
        answer_with(
            [
                {
                    "text": "Alpha năm 2025 là 18, năm 2026 là 22",
                    "evidence_ids": ["E1"],
                }
            ]
        ),
        [s],
    )
    result = materialize(draft, [s], catalog([s]))
    assert [stmt.text for stmt in result.statements] == ["Alpha năm 2025 là 18, năm 2026 là 22"]


@pytest.mark.parametrize("marked", [False, True])
def test_swap_within_one_multi_metric_statement_rejected(marked):
    """Alpha Quy mô=100, Ghi nhận=50. "Quy mô 50 và Ghi nhận 100" swaps
    the two values while both metric labels stay in the sentence."""
    rows = two_metric_table_with_header() if marked else two_metric_table()
    s = chunk(rows, [0, 1], key="E1", total=2, columns=3)
    if marked:
        s.citations = {"run:t": {"page": 1}}
    s.text = "row[0]: Name | Quy mô | Ghi nhận\nrow[1]: Alpha | 100 | 50"
    draft = parse_answer(
        answer_with(
            [
                {
                    "text": "Alpha có Quy mô 50 và Ghi nhận 100",
                    "evidence_ids": ["E1"],
                }
            ]
        ),
        [s],
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


@pytest.mark.parametrize("marked", [False, True])
def test_swap_within_one_multi_metric_statement_correct_values_accepted(marked):
    """Control: "Quy mô 100 và Ghi nhận 50" keeps the source binding."""
    rows = two_metric_table_with_header() if marked else two_metric_table()
    s = chunk(rows, [0, 1], key="E1", total=2, columns=3)
    if marked:
        s.citations = {"run:t": {"page": 1}}
    s.text = "row[0]: Name | Quy mô | Ghi nhận\nrow[1]: Alpha | 100 | 50"
    draft = parse_answer(
        answer_with(
            [
                {
                    "text": "Alpha có Quy mô 100 và Ghi nhận 50",
                    "evidence_ids": ["E1"],
                }
            ]
        ),
        [s],
    )
    result = materialize(draft, [s], catalog([s]))
    assert [stmt.text for stmt in result.statements] == ["Alpha có Quy mô 100 và Ghi nhận 50"]


# ---------------------------------------------------------------------------
# Partial verification: one correct, one wrong in same statement
# ---------------------------------------------------------------------------


def test_partial_swap_keeps_verified_and_reports_missing():
    """Two statements: "Alpha = 18" (correct) and "Beta = 99" (wrong).
    Alpha=18 should survive; 99 should be reported missing.
    """
    s = unselectable_source(two_row_table(), [0, 1, 2])
    draft = parse_answer(
        answer_with(
            [
                {"text": "Alpha = 18", "evidence_ids": ["E1"]},
                {"text": "Beta = 99", "evidence_ids": ["E1"]},
            ]
        ),
        [s],
    )
    report = {}
    result = materialize(draft, [s], catalog([s]), report=report)
    # Alpha=18 survives, Beta=99 is dropped.
    assert [stmt.text for stmt in result.statements] == ["Alpha = 18"]
    assert report.get("dropped_numbers") == ["99"]
    assert result.assessment[-1].status == "missing"
    assert "99" in result.assessment[-1].label
