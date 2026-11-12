"""An uncited table row cannot license or block a number from a cited passage.

Regression for the Q10 false positive (G3 cohort 952): a statement cited an
unselectable table (header_unresolved) plus a passage carrying the same
number. The statement named no row of that table, so the table could not
attribute the number to any subject, yet its digit set suppressed the
passage's support and the statement was dropped.

The table's per-row binding must only govern numbers attributed to one of
its subjects; without a named row the cited passage remains the proof.
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


def q10_table():
    """G3 Q10 shape: no header marks (header_unresolved), long row labels."""
    return [
        [
            cell("Trường hợp", "q-0-0"),
            cell("Đối tượng", "q-0-1"),
            cell("Giới hạn thời gian", "q-0-2"),
        ],
        [
            cell("Thiết bị nhóm A, kế hoạch 2027", "q-1-0"),
            cell("Phòng Đào tạo", "q-1-1"),
            cell("≤ 15 ngày làm việc", "q-1-2"),
        ],
        [
            cell("Thực tập ngoài trường nhóm B", "q-2-0"),
            cell("Phòng Đào tạo", "q-2-1"),
            cell("≤ 30 ngày kể từ cuối đợt", "q-2-2"),
        ],
    ]


def chunk(rows, indices, *, key, total=None, columns=None, citation="run:t"):
    total = total if total is not None else len(rows)
    columns = columns if columns is not None else len(rows[0])
    refs = {
        citation.split(":", 1)[0] + ":" + c["evidence_id"]: {"page": 4}
        for row in rows
        for c in row
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
        citations={citation: {"page": 4}, **refs},
        structure={
            "source_table_citation": citation,
            "original_row_count": total,
            "original_column_count": columns,
            "rows": rows,
            "row_indices": indices,
        },
    )


def passage_source(text, *, key="E6"):
    return EvidenceSource(
        evidence_id=key,
        chunk_id=key,
        document_id="doc",
        version_id="v",
        publication_decision_id="published",
        kind="passage",
        score=1,
        text=text,
        citations={"run:p": {"page": 7}},
        structure={
            "source_table_citation": "run:p",
            "original_row_count": 1,
            "original_column_count": 1,
            "rows": [[cell("", "p-0-0")]],
            "row_indices": [0],
        },
        source_passages=[{"text": text, "citation": "run:p", "position": "2"}],
    )


def q10_sources():
    table = chunk(q10_table(), [0, 1, 2], key="E1")
    table.text = (
        "row[0]: Trường hợp | Đối tượng | Giới hạn thời gian\n"
        "row[1]: Thiết bị nhóm A, kế hoạch 2027 | Phòng Đào tạo | ≤ 15 ngày làm việc\n"
        "row[2]: Thực tập ngoài trường nhóm B | Phòng Đào tạo | ≤ 30 ngày kể từ cuối đợt"
    )
    passage = passage_source(
        "2. Cho phép gia hạn tối đa 15 ngày làm việc kể từ hạn xác nhận ban đầu "
        "nếu có văn bản đề nghị của đơn vị."
    )
    return table, passage


def answer_with(text, evidence_ids):
    return json.dumps(
        {
            "status": "answered",
            "statements": [{"text": text, "evidence_ids": evidence_ids}],
            "lookups": [],
        }
    )


def materialize_one(text, evidence_ids):
    table, passage = q10_sources()
    draft = parse_answer(answer_with(text, evidence_ids), [table, passage])
    return materialize(draft, [table, passage], catalog([table, passage]), report={})


def test_unattributed_table_does_not_block_passage_number():
    """The statement names no row of E1; E6's own "15 ngày làm việc" proves it."""
    result = materialize_one(
        "Hồ sơ xác nhận thiết bị năm 2027 của nhóm A được gia hạn tối đa 15 ngày làm việc.",
        ["E1", "E6"],
    )
    assert [stmt.text for stmt in result.statements] == [
        "Hồ sơ xác nhận thiết bị năm 2027 của nhóm A được gia hạn tối đa 15 ngày làm việc."
    ]


def test_unattributed_table_general_claim_kept_once_passage_proves_it():
    """Same guard scope without any subject: the passage number still proves."""
    result = materialize_one(
        "Thời gian gia hạn tối đa là 15 ngày làm việc.", ["E1", "E6"]
    )
    assert [stmt.text for stmt in result.statements] == [
        "Thời gian gia hạn tối đa là 15 ngày làm việc."
    ]


def test_row_mention_still_blocks_passage_override():
    """Row B caps at 30; claiming 15 for it must stay rejected even though the
    passage contains 15 — the named row keeps its binding."""
    with pytest.raises(AppException) as exc:
        materialize_one("Thực tập ngoài trường nhóm B được gia hạn 15 ngày.", ["E1", "E6"])
    assert exc.value.code == "answer_table_value_not_extractive"


def test_row_mention_wrong_year_value_stays_rejected():
    """Row A caps at 15; claiming 30 for it finds only row B's value."""
    with pytest.raises(AppException) as exc:
        materialize_one(
            "Thiết bị nhóm A, kế hoạch 2027 được gia hạn 30 ngày.", ["E1", "E6"]
        )
    assert exc.value.code == "answer_table_value_not_extractive"


def test_fabricated_number_stays_rejected():
    """99 is in neither the table nor the passage."""
    with pytest.raises(AppException) as exc:
        materialize_one("Thời gian gia hạn tối đa là 99 ngày làm việc.", ["E1", "E6"])
    assert exc.value.code == "answer_table_value_not_extractive"


def test_verbatim_row_claim_stays_supported():
    """Naming row A with its own value still passes through the table path."""
    result = materialize_one(
        "Thiết bị nhóm A, kế hoạch 2027 được gia hạn ≤ 15 ngày làm việc.", ["E1"]
    )
    assert [stmt.text for stmt in result.statements] == [
        "Thiết bị nhóm A, kế hoạch 2027 được gia hạn ≤ 15 ngày làm việc."
    ]
