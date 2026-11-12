"""Numeric facts bind to a source row and column path, never to co-cited text nearby.

A value may appear in a cited table fragment and still belong to another program,
year or metric. The guard must not accept it as proof for the claimed subject.
Multi-tier headers that are only partially marked still resolve their full column
path through the proven dependency. When part of a multi-claim answer verifies,
the grounded part is kept and the missing numbers are reported as missing.
"""

import json

import pytest

from qnu.domains.knowledge.index.table_dependencies import MULTITIER_BASIS
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


def grid():
    """Compact Bảng 1: 3-tier merged header, 12 programs split A/B and a total row."""
    rows = [
        [
            cell("Nhóm Mã CT Tên chương trình", "t-0-0", rs=3, cs=3),
            cell("2025", "t-0-1", cs=3),
            cell("2026", "t-0-2", cs=3),
            cell("2027", "t-0-3", cs=3),
        ],
        [
            cell("Quy mô", "t-1-0"),
            cell("Ghi nhận", "t-1-1"),
            cell("Mức đạt", "t-1-2"),
            cell("Quy mô", "t-1-3"),
            cell("Ghi nhận", "t-1-4"),
            cell("Mức đạt", "t-1-5"),
            cell("Quy mô", "t-1-6"),
            cell("Dự kiến", "t-1-7"),
            cell("Ước đạt", "t-1-8"),
        ],
        [
            cell("Chỉ tiêu (SV)", "t-2-0"),
            cell("Số lượng (SV)", "t-2-1"),
            cell("Tỷ lệ (%)", "t-2-2"),
            cell("Chỉ tiêu (SV)", "t-2-3"),
            cell("Số lượng (SV)", "t-2-4"),
            cell("Tỷ lệ (%)", "t-2-5"),
            cell("Chỉ tiêu (SV)", "t-2-6"),
            cell("Ước tính (SV)", "t-2-7"),
            cell("Tỷ lệ (%)", "t-2-8"),
        ],
        [
            cell("A\nCông nghệ,\nsố hóa", "t-3-0", rs=6),
            cell("0012", "t-3-1"),
            cell("Kỹ thuật phần mềm", "t-3-2"),
            cell("120", "t-3-3"),
            cell("112", "t-3-4"),
            cell("93,3", "t-3-5"),
            cell("130", "t-3-6"),
            cell("119", "t-3-7"),
            cell("91,5", "t-3-8"),
            cell("140", "t-3-9"),
            cell("132", "t-3-10"),
            cell("94,3", "t-3-11"),
        ],
        [
            cell("00027", "t-4-0"),
            cell("Công nghệ thông tin ứng dụng", "t-4-1"),
            cell("110", "t-4-2"),
            cell("104", "t-4-3"),
            cell("94,5", "t-4-4"),
            cell("125", "t-4-5"),
            cell("116", "t-4-6"),
            cell("92,8", "t-4-7"),
            cell("130", "t-4-8"),
            cell("123", "t-4-9"),
            cell("94,6", "t-4-10"),
        ],
        [
            cell("AM-0007", "t-5-0"),
            cell("Khoa học dữ liệu", "t-5-1"),
            cell("85", "t-5-2"),
            cell("77", "t-5-3"),
            cell("90,6", "t-5-4"),
            cell("100", "t-5-5"),
            cell("92", "t-5-6"),
            cell("92,0", "t-5-7"),
            cell("110", "t-5-8"),
            cell("101", "t-5-9"),
            cell("91,8", "t-5-10"),
        ],
        [
            cell("AM-0070", "t-6-0"),
            cell("Quản trị dữ liệu số", "t-6-1"),
            cell("70", "t-6-2"),
            cell("63", "t-6-3"),
            cell("90,0", "t-6-4"),
            cell("78", "t-6-5"),
            cell("72", "t-6-6"),
            cell("92,3", "t-6-7"),
            cell("90", "t-6-8"),
            cell("82", "t-6-9"),
            cell("91,1", "t-6-10"),
        ],
        [
            cell("0120", "t-7-0"),
            cell("An toàn thông tin", "t-7-1"),
            cell("95", "t-7-2"),
            cell("91", "t-7-3"),
            cell("95,8", "t-7-4"),
            cell("105", "t-7-5"),
            cell("98", "t-7-6"),
            cell("93,3", "t-7-7"),
            cell("115", "t-7-8"),
            cell("108", "t-7-9"),
            cell("93,9", "t-7-10"),
        ],
        [
            cell("AM-0201", "t-8-0"),
            cell("Thiết kế truyền thông số", "t-8-1"),
            cell("75", "t-8-2"),
            cell("68", "t-8-3"),
            cell("90,7", "t-8-4"),
            cell("80", "t-8-5"),
            cell("75", "t-8-6"),
            cell("93,8", "t-8-7"),
            cell("95", "t-8-8"),
            cell("89", "t-8-9"),
            cell("93,7", "t-8-10"),
        ],
        [
            cell("B\nQuản trị,\nxã hội", "t-9-0", rs=6),
            cell("0073", "t-9-1"),
            cell("Quản trị kinh doanh", "t-9-2"),
            cell("125", "t-9-3"),
            cell("119", "t-9-4"),
            cell("95,2", "t-9-5"),
            cell("135", "t-9-6"),
            cell("129", "t-9-7"),
            cell("95,6", "t-9-8"),
            cell("140", "t-9-9"),
            cell("134", "t-9-10"),
            cell("95,7", "t-9-11"),
        ],
        [
            cell("AM-0310", "t-10-0"),
            cell("Logistics và chuỗi cung ứng", "t-10-1"),
            cell("105", "t-10-2"),
            cell("97", "t-10-3"),
            cell("92,4", "t-10-4"),
            cell("115", "t-10-5"),
            cell("108", "t-10-6"),
            cell("93,9", "t-10-7"),
            cell("125", "t-10-8"),
            cell("117", "t-10-9"),
            cell("93,6", "t-10-10"),
        ],
        [
            cell("AM-0450", "t-11-0"),
            cell("Công nghệ giáo dục", "t-11-1"),
            cell("80", "t-11-2"),
            cell("72", "t-11-3"),
            cell("90,0", "t-11-4"),
            cell("90", "t-11-5"),
            cell("84", "t-11-6"),
            cell("93,3", "t-11-7"),
            cell("100", "t-11-8"),
            cell("93", "t-11-9"),
            cell("93,0", "t-11-10"),
        ],
        [
            cell("00081", "t-12-0"),
            cell("Quản trị nhân lực", "t-12-1"),
            cell("90", "t-12-2"),
            cell("83", "t-12-3"),
            cell("92,2", "t-12-4"),
            cell("100", "t-12-5"),
            cell("95", "t-12-6"),
            cell("95,0", "t-12-7"),
            cell("110", "t-12-8"),
            cell("104", "t-12-9"),
            cell("94,5", "t-12-10"),
        ],
        [
            cell("AM-0029", "t-13-0"),
            cell("Kế toán số", "t-13-1"),
            cell("110", "t-13-2"),
            cell("101", "t-13-3"),
            cell("91,8", "t-13-4"),
            cell("120", "t-13-5"),
            cell("113", "t-13-6"),
            cell("94,2", "t-13-7"),
            cell("135", "t-13-8"),
            cell("127", "t-13-9"),
            cell("94,1", "t-13-10"),
        ],
        [
            cell("AM-0512", "t-14-0"),
            cell("Tài chính số", "t-14-1"),
            cell("100", "t-14-2"),
            cell("92", "t-14-3"),
            cell("92,0", "t-14-4"),
            cell("110", "t-14-5"),
            cell("105", "t-14-6"),
            cell("95,5", "t-14-7"),
            cell("120", "t-14-8"),
            cell("114", "t-14-9"),
            cell("95,0", "t-14-10"),
        ],
        [
            cell("TỔNG CỘNG (12 chương trình)", "t-15-0", rs=1, cs=3),
            cell("1115", "t-15-1"),
            cell("1036", "t-15-2"),
            cell("92,9", "t-15-3"),
            cell("1233", "t-15-4"),
            cell("1149", "t-15-5"),
            cell("93,2", "t-15-6"),
            cell("1340", "t-15-7"),
            cell("1255", "t-15-8"),
            cell("93,7", "t-15-9"),
        ],
    ]
    return rows


def table(rows=None, *, columns=12, total=16):
    return {
        "rows": grid() if rows is None else rows,
        "column_count": columns,
        "original_row_count": total,
    }


def chunk(rows, indices, *, key, total=16, columns=12, citation="run:t"):
    refs = {
        citation.split(":", 1)[0] + ":" + c["evidence_id"]: {"page": 1}
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
        citations={citation: {"page": 1}, **refs},
        structure={
            "source_table_citation": citation,
            "original_row_count": total,
            "original_column_count": columns,
            "rows": rows,
            "row_indices": indices,
        },
    )


def link_for(data_key, header_key, *, header_rows=(0, 1, 2)):
    return {
        "chunk_id": data_key,
        "header": "run:t",
        "previous": None,
        "support_ids": [header_key],
        "basis": MULTITIER_BASIS,
        "header_rows": list(header_rows),
    }


def answer_with(statements, lookups=()):
    return json.dumps(
        {
            "status": "answered",
            "statements": statements,
            "lookups": [{"cell_id": key} for key in lookups],
        }
    )


def simple_unselectable(text, *, key="E1", table="ocr:t"):
    s = chunk(
        [
            [cell("Name", "u-0-0"), cell("Price", "u-0-1")],
            [cell("Alpha", "u-1-0"), cell("18", "u-1-1")],
            [cell("Beta", "u-2-0"), cell("22", "u-2-1")],
        ],
        [0, 1, 2],
        key=key,
        total=3,
        columns=2,
        citation=table,
    )
    s.text = text
    return s


def test_number_from_another_row_is_not_proof():
    s = simple_unselectable("row[0]: Name | Price\nrow[1]: Alpha | 18\nrow[2]: Beta | 22")
    draft = parse_answer(answer_with([{"text": "Alpha: 22", "evidence_ids": ["E1"]}]), [s])
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_number_from_partially_marked_header_is_not_proof():
    header = [cell("Alpha", "u-0-0", header=True), cell("99", "u-0-1")]
    data = [cell("Alpha", "u-1-0"), cell("18", "u-1-1")]
    s = chunk([header, data], [0, 1], key="E1", total=2, columns=2, citation="ocr:t")
    s.text = "row[0]: Alpha | 99\nrow[1]: Alpha | 18"
    draft = parse_answer(answer_with([{"text": "Alpha đạt 99", "evidence_ids": ["E1"]}]), [s])
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_number_from_same_row_is_proof():
    s = simple_unselectable("row[0]: Name | Price\nrow[1]: Alpha | 18\nrow[2]: Beta | 22")
    draft = parse_answer(answer_with([{"text": "Alpha: 18", "evidence_ids": ["E1"]}]), [s])
    result = materialize(draft, [s], catalog([s]))
    assert [statement.text for statement in result.statements] == ["Alpha: 18"]


def test_group_b_number_is_not_proof_for_group_a_subject():
    sources = [
        chunk(grid()[0:3], [0, 1, 2], key="E1"),
        chunk(grid()[3:9], [3, 4, 5, 6, 7, 8], key="E2"),
        chunk(grid()[9:15], [9, 10, 11, 12, 13, 14], key="E3"),
    ]
    draft = parse_answer(
        answer_with(
            [
                {
                    "text": "Quản trị kinh doanh năm 2027 có 127 sinh viên.",
                    "evidence_ids": ["E1", "E3"],
                }
            ]
        ),
        sources,
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, sources, catalog(sources))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_row_subject_and_year_make_the_value_source_bound():
    sources = [
        chunk(grid()[0:3], [0, 1, 2], key="E1"),
        chunk(grid()[9:15], [9, 10, 11, 12, 13, 14], key="E3"),
    ]
    draft = parse_answer(
        answer_with(
            [
                {
                    "text": "Kế toán số năm 2027 có 127 sinh viên.",
                    "evidence_ids": ["E1", "E3"],
                }
            ]
        ),
        sources,
    )
    result = materialize(draft, sources, catalog(sources))
    assert result.statements[0].text == "Kế toán số năm 2027 có 127 sinh viên."


def test_partial_verification_keeps_grounded_statement_and_reports_missing():
    sources = [
        chunk(grid()[0:3], [0, 1, 2], key="E1"),
        chunk(grid()[9:15], [9, 10, 11, 12, 13, 14], key="E3"),
    ]
    draft = parse_answer(
        answer_with(
            [
                {
                    "text": "Quản trị kinh doanh năm 2027 có 127 sinh viên.",
                    "evidence_ids": ["E1", "E3"],
                },
                {
                    "text": "Kế toán số năm 2027 có 127 sinh viên.",
                    "evidence_ids": ["E1", "E3"],
                },
            ]
        ),
        sources,
    )
    report = {}
    result = materialize(draft, sources, catalog(sources), report=report)
    assert [statement.text for statement in result.statements] == [
        "Kế toán số năm 2027 có 127 sinh viên."
    ]
    assert report["dropped_numbers"] == ["127"]
    assert result.assessment[-1].status == "missing"
    assert "127" in result.assessment[-1].label


def test_no_verified_statement_still_fails():
    s = simple_unselectable("row[0]: Name | Price\nrow[1]: Alpha | 18")
    draft = parse_answer(
        answer_with([{"text": "Alpha: 99", "evidence_ids": ["E1"]}]), [s]
    )
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"
    assert exc.value.validation_issues == [
        {"path": ["statements", 0, "text"], "type": "number_not_in_cited_source"}
    ]


def test_partially_marked_multitier_header_resolves_full_column_path():
    rows = grid()
    # Row 0 alone carries header marks; rows 1-2 are the remaining tiers.
    for c in rows[0]:
        c["header"] = True
    header = chunk(rows[0:3], [0, 1, 2], key="E1")
    data = chunk(rows[3:9], [3, 4, 5, 6, 7, 8], key="E2")
    cells = catalog([data, header], [link_for("E2", "E1")])
    by_id = {t["evidence_id"]: t for t in cells["tables"]}
    assert by_id["E1"]["cells"] == []
    assert by_id["E2"]["fields"]["8"] == ["2026", "Mức đạt", "Tỷ lệ (%)"]
    assert by_id["E2"]["fields"]["7"] == ["2026", "Ghi nhận", "Số lượng (SV)"]
    selected = {c["cell_id"]: c for c in by_id["E2"]["cells"]}
    assert selected["E2:r7:k8"]["value"] == "93,3"
    assert selected["E2:r7:k8"]["subject"] == "A\nCông nghệ,\nsố hóa / An toàn thông tin"
    draft = parse_answer(
        answer_with([], ["E2:r7:k8"]), [data, header]
    )
    answer = materialize(draft, [data, header], cells)
    assert answer.statements[0].text == (
        "A\nCông nghệ,\nsố hóa / An toàn thông tin — "
        "2026 / Mức đạt / Tỷ lệ (%): 93,3"
    )


def test_sibling_data_fragment_borrows_the_table_family_header():
    # Q08: the data fragment is packed without its own dependency entry. The
    # header link belongs to the header sibling, but both share one sealed table.
    rows = grid()
    header = chunk(rows[0:3], [0, 1, 2], key="E1")
    shifted = []
    for row in rows[12:15]:
        shifted.append([cell("", f"t-{len(shifted) + 12}-blank"), *row])
    data = chunk(shifted, [12, 13, 14], key="E2")
    link = {
        "chunk_id": "E1",
        "header": "run:t",
        "previous": None,
        "support_ids": ["E1"],
        "basis": MULTITIER_BASIS,
        "header_rows": [0, 1, 2],
    }
    cells = catalog([header, data], [link])
    table = next(
        item for item in cells["tables"] if item["evidence_id"] == "E2" and item["cells"]
    )
    assert table["fields"]["10"] == ["2027", "Dự kiến", "Ước tính (SV)"]
    selected = {cell["cell_id"]: cell for cell in table["cells"]}
    proof = selected["E2:r13:k10"]
    assert proof["value"] == "127"
    assert proof["subject"] == "AM-0029 / Kế toán số"
    assert "run:t-0-3" in proof["source_cells"]
    assert "run:t-1-7" in proof["source_cells"]
    assert "run:t-2-7" in proof["source_cells"]
    assert proof["source_cells"][0] == "run:t-13-9"


def test_q05_cell_binds_933_to_an_toan_thong_tin_2026_rate():
    rows = grid()
    header = chunk(rows[0:3], [0, 1, 2], key="E1")
    data = chunk(rows[3:9], [3, 4, 5, 6, 7, 8], key="E2")
    cells = catalog([data, header], [link_for("E2", "E1")])
    selected = {c["cell_id"]: c for table in cells["tables"] for c in table["cells"]}
    proof = selected["E2:r7:k8"]
    assert proof["value"] == "93,3"
    assert proof["subject"] == "A\nCông nghệ,\nsố hóa / An toàn thông tin"
    # Source-cell id uses the canonical cell index (c07_07 in production).
    assert proof["source_cells"][0] == "run:t-7-7"
    assert selected["E2:r3:k5"]["value"] == "93,3"
    assert selected["E2:r3:k5"]["subject"] == "A\nCông nghệ,\nsố hóa / Kỹ thuật phần mềm"


def test_q07_totals_both_bind_to_the_total_row_and_2026_columns():
    rows = grid()
    header = chunk(rows[0:3], [0, 1, 2], key="E1")
    data = chunk(rows[15:16], [15], key="E2")
    cells = catalog([data, header], [link_for("E2", "E1")])
    selected = {c["cell_id"]: c for table in cells["tables"] for c in table["cells"]}
    assert selected["E2:r15:k6"]["value"] == "1233"
    assert selected["E2:r15:k6"]["subject"] == "TỔNG CỘNG (12 chương trình)"
    assert selected["E2:r15:k7"]["value"] == "1149"
    assert selected["E2:r15:k7"]["subject"] == "TỔNG CỘNG (12 chương trình)"
    assert "2026" in cells["tables"][0]["fields"]["6"]
    assert "Chỉ tiêu (SV)" in cells["tables"][0]["fields"]["6"]


def test_q09_group_a_list_contains_six_programs_and_no_group_b_name():
    rows = grid()
    header = chunk(rows[0:3], [0, 1, 2], key="E1")
    data = chunk(rows[3:9], [3, 4, 5, 6, 7, 8], key="E2")
    cells = catalog([data, header], [link_for("E2", "E1")])
    table = next(t for t in cells["tables"] if t["evidence_id"] == "E2")
    subjects = {
        c["subject"].split(" / ")[-1]
        for c in table["cells"]
        if c["column"] == 3
    }
    assert subjects == {
        "Kỹ thuật phần mềm",
        "Công nghệ thông tin ứng dụng",
        "Khoa học dữ liệu",
        "Quản trị dữ liệu số",
        "An toàn thông tin",
        "Thiết kế truyền thông số",
    }
    assert "Quản trị kinh doanh" not in subjects
    assert "Kế toán số" not in subjects
