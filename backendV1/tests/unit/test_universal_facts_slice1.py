"""Unit tests for Slice 1: Universal Facts projection & strict data fidelity."""

from __future__ import annotations

from qnu.domains.knowledge.index.facts import (
    ScopedNote,
    classify_value,
    project_table,
)


def _cell(
    text: str,
    *,
    header: bool = False,
    row_span: int = 1,
    col_span: int = 1,
    evidence_id: str | None = None,
) -> dict:
    payload = {
        "text": text,
        "header": header,
        "row_span": row_span,
        "col_span": col_span,
    }
    if evidence_id is not None:
        payload["evidence_id"] = evidence_id
    return payload


def test_classify_value_preserves_leading_zeros_and_distinguishes_special_kinds():
    assert classify_value("0012") == "normal"
    assert classify_value("00027") == "normal"
    assert classify_value("AM-0007") == "normal"
    assert classify_value("0") == "numeric_zero"
    assert classify_value("0,0") == "numeric_zero"
    assert classify_value("0.00") == "numeric_zero"
    assert classify_value("") == "empty_cell"
    assert classify_value("   \t ") == "empty_cell"
    assert classify_value("Chưa công bố") == "not_published"
    assert classify_value("Không áp dụng") == "not_applicable"
    assert classify_value("–", defined_symbols={"–"}) == "defined_symbol"
    assert classify_value("/", defined_symbols={"–"}) == "undefined_symbol"
    assert classify_value("–") == "undefined_symbol"


def test_small_headed_table_still_emits_full_facts_with_keep_whole_flag():
    table = {
        "row_count": 4,
        "column_count": 2,
        "rows": [
            [
                _cell("IELTS", header=True, evidence_id="c0_0"),
                _cell("Điểm quy đổi", header=True, evidence_id="c0_1"),
            ],
            [_cell("5.5", evidence_id="c1_0"), _cell("8,5", evidence_id="c1_1")],
            [_cell("6.0", evidence_id="c2_0"), _cell("9,0", evidence_id="c2_1")],
            [_cell("6.5", evidence_id="c3_0"), _cell("/", evidence_id="c3_1")],
        ],
    }
    notes = [
        ScopedNote(note_id="N_IELTS", scope="table", target="", text="Chứng chỉ còn hạn 2 năm"),
    ]

    projected = project_table(
        table,
        table_id="tbl_ielts",
        source_table_citation="ocr_1:ev_p003_b001",
        title="Bảng quy đổi điểm IELTS",
        scoped_notes=notes,
    )

    assert projected.has_header is True
    assert projected.storage_mode == "facts"
    assert projected.keep_whole_in_chunk is True
    assert len(projected.facts) == 3
    assert projected.facts[0].attributes["Điểm quy đổi"].raw == "8,5"
    assert projected.facts[0].attributes["Điểm quy đổi"].value_kind == "normal"
    assert projected.facts[2].attributes["Điểm quy đổi"].value_kind == "undefined_symbol"
    assert all(f.applicable_note_ids == ["N_IELTS"] for f in projected.facts)
    schema = projected.table_schema()
    assert schema.keep_whole_in_chunk is True
    assert schema.data_row_count == 3


def test_headerless_table_stores_raw_rows_with_colspan_flag_and_never_uses_row1_as_keys():
    table = {
        "row_count": 3,
        "column_count": 3,
        "rows": [
            [_cell("Ghi chú chung toàn bảng", col_span=3, evidence_id="c0_0")],
            [
                _cell("0012", evidence_id="c1_0"),
                _cell("Mục A", evidence_id="c1_1"),
                _cell("100", evidence_id="c1_2"),
            ],
            [
                _cell("0027", evidence_id="c2_0"),
                _cell("Mục B", evidence_id="c2_1"),
                _cell("/", evidence_id="c2_2"),
            ],
        ],
    }

    projected = project_table(
        table,
        table_id="tbl_no_header",
        source_table_citation="ocr_2:ev_p005_b002",
        title="Bảng không tiêu đề",
    )

    assert projected.has_header is False
    assert projected.storage_mode == "raw_rows"
    assert projected.keep_whole_in_chunk is True
    assert projected.facts == []
    assert projected.column_keys == []
    assert len(projected.raw_rows) == 3
    assert projected.raw_rows[0].is_colspan is True
    assert projected.raw_rows[0].cells == ["Ghi chú chung toàn bảng"]
    assert projected.raw_rows[1].is_colspan is False
    assert projected.raw_rows[1].cells[0] == "0012"
    assert projected.raw_rows[1].source_cell_refs == [
        "ocr_2:c1_0",
        "ocr_2:c1_1",
        "ocr_2:c1_2",
    ]


def test_large_multitier_year_table_unmerges_splits_years_and_applies_scoped_notes():
    rows = [
        [
            _cell("Nhóm ngành", header=True, row_span=2, evidence_id="h0_0"),
            _cell("Mã ngành", header=True, row_span=2, evidence_id="h0_1"),
            _cell("Tên ngành", header=True, row_span=2, evidence_id="h0_2"),
            _cell("Năm 2024", header=True, col_span=2, evidence_id="h0_3"),
            _cell("Năm 2025", header=True, col_span=2, evidence_id="h0_5"),
        ],
        [
            _cell("Chỉ tiêu", header=True, evidence_id="h1_3"),
            _cell("Điểm chuẩn", header=True, evidence_id="h1_4"),
            _cell("Chỉ tiêu", header=True, evidence_id="h1_5"),
            _cell("Điểm chuẩn", header=True, evidence_id="h1_6"),
        ],
    ]
    for idx in range(10):
        row = []
        if idx == 0:
            row.append(_cell("Khối Sư phạm", row_span=5, evidence_id="g_sp"))
        elif idx == 5:
            row.append(_cell("Khối Kỹ thuật", row_span=5, evidence_id="g_kt"))
        code = f"000{idx + 1}" if idx < 9 else "AM-0010"
        name = f"Ngành thử nghiệm {idx + 1}"
        if idx == 0:
            vals = ("0", "", "–", "/")
        elif idx == 1:
            vals = ("120", "25,85", "150", "Chưa công bố")
        else:
            vals = (str(50 + idx), "21,0", str(60 + idx), "Không áp dụng")
        row.extend(
            [
                _cell(code, evidence_id=f"r{idx}_c1"),
                _cell(name, evidence_id=f"r{idx}_c2"),
                _cell(vals[0], evidence_id=f"r{idx}_c3"),
                _cell(vals[1], evidence_id=f"r{idx}_c4"),
                _cell(vals[2], evidence_id=f"r{idx}_c5"),
                _cell(vals[3], evidence_id=f"r{idx}_c6"),
            ]
        )
        rows.append(row)

    table = {"row_count": len(rows), "column_count": 7, "rows": rows}
    notes = [
        ScopedNote(note_id="N_TBL", scope="table", target="", text="Áp dụng toàn bảng"),
        ScopedNote(note_id="N_GRP", scope="group", target="Khối Sư phạm", text="Miễn học phí NĐ 116"),
        ScopedNote(note_id="N_ROW", scope="row", target="0001", text="Ghi chú riêng cho mã 0001"),
        ScopedNote(note_id="N_Y25", scope="column_year", target="2025", text="Số liệu dự kiến 2025"),
    ]

    projected = project_table(
        table,
        table_id="tbl_ts",
        source_table_citation="ocr_9:ev_p006_b001",
        title="Bảng chỉ tiêu và điểm chuẩn 2024-2025",
        column_years={3: 2024, 4: 2024, 5: 2025, 6: 2025},
        year_statuses={2024: "locked", 2025: "interim"},
        scoped_notes=notes,
        defined_symbols={"–"},
    )

    assert projected.has_header is True
    assert projected.storage_mode == "facts"
    assert projected.keep_whole_in_chunk is False
    assert projected.data_years == [2024, 2025]
    assert len(projected.facts) == 20

    schema = projected.table_schema()
    assert schema.column_keys == ["Nhóm ngành", "Mã ngành", "Tên ngành", "Chỉ tiêu", "Điểm chuẩn"]
    assert schema.data_years == [2024, 2025]
    assert schema.data_row_count == 10

    fact_r0_2024 = next(f for f in projected.facts if f.row_index == 2 and f.data_year == 2024)
    fact_r0_2025 = next(f for f in projected.facts if f.row_index == 2 and f.data_year == 2025)
    fact_r5_2024 = next(f for f in projected.facts if f.row_index == 7 and f.data_year == 2024)
    fact_r9_2025 = next(f for f in projected.facts if f.row_index == 11 and f.data_year == 2025)

    assert fact_r0_2024.subject_code == "0001"
    assert fact_r9_2025.subject_code == "AM-0010"
    assert fact_r0_2024.group == "Khối Sư phạm"
    assert fact_r5_2024.group == "Khối Kỹ thuật"
    assert "ocr_9:g_sp" in fact_r0_2024.source_cell_refs
    assert "ocr_9:g_kt" in fact_r5_2024.source_cell_refs

    assert fact_r0_2024.data_status == "locked"
    assert fact_r0_2024.attributes["Chỉ tiêu"].raw == "0"
    assert fact_r0_2024.attributes["Chỉ tiêu"].value_kind == "numeric_zero"
    assert fact_r0_2024.attributes["Điểm chuẩn"].raw == ""
    assert fact_r0_2024.attributes["Điểm chuẩn"].value_kind == "empty_cell"

    assert fact_r0_2025.data_status == "interim"
    assert fact_r0_2025.attributes["Chỉ tiêu"].raw == "–"
    assert fact_r0_2025.attributes["Chỉ tiêu"].value_kind == "defined_symbol"
    assert fact_r0_2025.attributes["Điểm chuẩn"].raw == "/"
    assert fact_r0_2025.attributes["Điểm chuẩn"].value_kind == "undefined_symbol"

    assert fact_r0_2024.applicable_note_ids == ["N_TBL", "N_GRP", "N_ROW"]
    assert fact_r0_2025.applicable_note_ids == ["N_TBL", "N_GRP", "N_ROW", "N_Y25"]
    assert fact_r5_2024.applicable_note_ids == ["N_TBL"]
    assert fact_r9_2025.applicable_note_ids == ["N_TBL", "N_Y25"]


def test_row_kind_classifies_summary_group_header_inline_note_and_preserves_duplicate_names():
    table = {
        "row_count": 7,
        "column_count": 4,
        "rows": [
            [
                _cell("Đơn vị", header=True, evidence_id="h0"),
                _cell("Mã", header=True, evidence_id="h1"),
                _cell("Tên chương trình", header=True, evidence_id="h2"),
                _cell("Chỉ tiêu", header=True, evidence_id="h3"),
            ],
            [_cell("I. HỆ CHÍNH QUY", col_span=4, evidence_id="b_grp1")],
            [
                _cell("Khoa Toán", evidence_id="r2_0"),
                _cell("0011", evidence_id="r2_1"),
                _cell("Quản trị chất lượng", evidence_id="r2_2"),
                _cell("80", evidence_id="r2_3"),
            ],
            [_cell("II. HỆ VỪA LÀM VỪA HỌC", col_span=4, evidence_id="b_grp2")],
            [
                _cell("Khoa Kinh tế", evidence_id="r4_0"),
                _cell("0012", evidence_id="r4_1"),
                _cell("Quản trị chất lượng", evidence_id="r4_2"),
                _cell("40", evidence_id="r4_3"),
            ],
            [
                _cell("Tổng cộng", col_span=3, evidence_id="r5_0"),
                _cell("120", evidence_id="r5_3"),
            ],
            [
                _cell("Ghi chú: Chỉ tiêu có thể điều chỉnh theo quy định Bộ GD&ĐT.", col_span=4, evidence_id="r6_0")
            ],
        ],
    }

    projected = project_table(
        table,
        table_id="tbl_dup",
        source_table_citation="ocr_8:ev_p004_b001",
        title="Bảng chỉ tiêu các hệ",
    )

    by_row = {f.row_index: f for f in projected.facts}
    assert by_row[1].row_kind == "group_header"
    assert by_row[2].row_kind == "data"
    assert by_row[2].group == "I. HỆ CHÍNH QUY"
    assert by_row[3].row_kind == "group_header"
    assert by_row[4].row_kind == "data"
    assert by_row[4].group == "II. HỆ VỪA LÀM VỪA HỌC"
    assert by_row[5].row_kind == "summary"
    assert by_row[6].row_kind == "inline_note"

    # Two data rows share the exact same subject_name but differ by unit/group:
    # fact_ids must stay distinct and never overwrite each other.
    data_facts = [f for f in projected.facts if f.row_kind == "data"]
    assert len(data_facts) == 2
    assert len({f.fact_id for f in data_facts}) == 2
    assert data_facts[0].subject_name == data_facts[1].subject_name == "Quản trị chất lượng"
    assert data_facts[0].attributes["Đơn vị"].raw == "Khoa Toán"
    assert data_facts[1].attributes["Đơn vị"].raw == "Khoa Kinh tế"
    assert projected.table_schema().data_row_count == 2


def test_long_cell_over_100_words_uses_markdown_pointer_instead_of_full_text_in_jsonb():
    long_text = " ".join(f"tu_{i}" for i in range(130))
    table = {
        "row_count": 2,
        "column_count": 3,
        "rows": [
            [
                _cell("Mã ngành", header=True, evidence_id="h0"),
                _cell("Tên ngành", header=True, evidence_id="h1"),
                _cell("Ghi chú chi tiết", header=True, evidence_id="h2"),
            ],
            [
                _cell("00027", evidence_id="c1_0"),
                _cell("Khoa học dữ liệu", evidence_id="c1_1"),
                _cell(long_text, evidence_id="c1_2"),
            ],
        ],
    }

    projected = project_table(
        table,
        table_id="tbl_long",
        source_table_citation="ocr_7:ev_p009_b001",
        title="Bảng có ô mô tả dài",
    )

    assert projected.storage_mode == "facts"
    assert projected.keep_whole_in_chunk is True
    assert len(projected.facts) == 1
    fact = projected.facts[0]
    detail_attr = fact.attributes["Ghi chú chi tiết"]
    assert detail_attr.is_truncated is True
    assert detail_attr.detail_md_pointer == "ocr_7:c1_2"
    assert len(detail_attr.raw.split()) <= 31
    assert fact.detail_md_pointers == {"Ghi chú chi tiết": "ocr_7:c1_2"}


def test_role_columns_handles_nhiem_vu_and_never_picks_400_word_column_as_subject_name():
    long_prose = " ".join(f"mo_ta_{i}" for i in range(400))
    table = {
        "row_count": 3,
        "column_count": 3,
        "rows": [
            [
                _cell("Mã", header=True, evidence_id="h0"),
                _cell("Nhiệm vụ", header=True, evidence_id="h1"),
                _cell("Mô tả thực hiện", header=True, evidence_id="h2"),
            ],
            [
                _cell("NV-30", evidence_id="r1_0"),
                _cell("Số hóa học liệu", evidence_id="r1_1"),
                _cell(long_prose, evidence_id="r1_2"),
            ],
            [
                _cell("NV-31", evidence_id="r2_0"),
                _cell("Cập nhật quy chế", evidence_id="r2_1"),
                _cell("Mô tả ngắn", evidence_id="r2_2"),
            ],
        ],
    }

    projected = project_table(
        table,
        table_id="tbl_nv",
        source_table_citation="ocr_10:ev_p001_b001",
        title="Bảng nhiệm vụ",
    )
    assert projected.facts[0].subject_code == "NV-30"
    assert projected.facts[0].subject_name == "Số hóa học liệu"

    # Even without explicit name header, a 400-word prose column must never be selected as subject_name
    table_no_name_header = {
        "row_count": 2,
        "column_count": 2,
        "rows": [
            [_cell("Mã", header=True, evidence_id="h0"), _cell("Diễn giải", header=True, evidence_id="h1")],
            [_cell("NV-30", evidence_id="r1_0"), _cell(long_prose, evidence_id="r1_1")],
        ],
    }
    projected2 = project_table(
        table_no_name_header,
        table_id="tbl_nv2",
        source_table_citation="ocr_10:ev_p002_b001",
    )
    assert projected2.facts[0].subject_name is None


def test_inline_condition_colspan_and_group_boundary_aware_prefix_match():
    table = {
        "row_count": 5,
        "column_count": 3,
        "rows": [
            [
                _cell("Mã", header=True, evidence_id="h0"),
                _cell("Tên ngành", header=True, evidence_id="h1"),
                _cell("Chỉ tiêu", header=True, evidence_id="h2"),
            ],
            [_cell("I. Khối Sư phạm - Hệ chính quy", col_span=3, evidence_id="b_grp1")],
            [_cell("0001", evidence_id="r2_0"), _cell("Sư phạm Toán", evidence_id="r2_1"), _cell("80", evidence_id="r2_2")],
            [_cell("Riêng đối với thí sinh khu vực 1 được cộng điểm ưu tiên theo quy chế hiện hành", col_span=3, evidence_id="b_cond")],
            [_cell("0002", evidence_id="r4_0"), _cell("Sư phạm Lý", evidence_id="r4_1"), _cell("50", evidence_id="r4_2")],
        ],
    }
    notes = [
        ScopedNote(note_id="N_MATCH", scope="group", target="Khối Sư phạm", text="Khớp boundary prefix"),
        ScopedNote(note_id="N_NO_MATCH", scope="group", target="Khối Sư", text="Không được khớp cắt ngang từ"),
    ]

    projected = project_table(
        table,
        table_id="tbl_cond",
        source_table_citation="ocr_11:ev_p001_b001",
        scoped_notes=notes,
    )
    by_row = {f.row_index: f for f in projected.facts}
    assert by_row[1].row_kind == "group_header"
    assert by_row[3].row_kind == "inline_note"
    assert by_row[2].applicable_note_ids == ["N_MATCH"]
    assert by_row[4].applicable_note_ids == ["N_MATCH"]
