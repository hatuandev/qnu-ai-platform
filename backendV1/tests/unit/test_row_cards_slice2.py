"""Unit tests for Slice 2: Self-Contained Row-Card projection & pointer expansion."""

from __future__ import annotations

from qnu.domains.knowledge.index.facts import ScopedNote, project_table
from qnu.domains.knowledge.index.row_cards import (
    DocumentCardMeta,
    expand_cards_context,
    render_fact_to_row_card,
    render_projection_to_cards,
)
from tests.unit.test_universal_facts_slice1 import _cell


def test_render_fact_to_row_card_renders_special_value_kinds_and_scoped_notes():
    rows = [
        [
            _cell("Mã ngành", header=True, evidence_id="h0"),
            _cell("Tên ngành", header=True, evidence_id="h1"),
            _cell("Năm 2025", header=True, col_span=4, evidence_id="h2"),
        ],
        [
            _cell("Mã ngành", header=True, evidence_id="h0"),
            _cell("Tên ngành", header=True, evidence_id="h1"),
            _cell("Chỉ tiêu", header=True, evidence_id="h2_0"),
            _cell("Điểm sàn", header=True, evidence_id="h2_1"),
            _cell("Học phí", header=True, evidence_id="h2_2"),
            _cell("Ký hiệu", header=True, evidence_id="h2_3"),
        ],
    ]
    # Use a 2-tier table with rowspan on shared columns
    rows = [
        [
            _cell("Mã ngành", header=True, row_span=2, evidence_id="h0"),
            _cell("Tên ngành", header=True, row_span=2, evidence_id="h1"),
            _cell("Năm 2025", header=True, col_span=4, evidence_id="h2"),
        ],
        [
            _cell("Chỉ tiêu", header=True, evidence_id="h2_0"),
            _cell("Điểm sàn", header=True, evidence_id="h2_1"),
            _cell("Học phí", header=True, evidence_id="h2_2"),
            _cell("Ký hiệu", header=True, evidence_id="h2_3"),
        ],
        [
            _cell("0001", evidence_id="r0_0"),
            _cell("Sư phạm Toán", evidence_id="r0_1"),
            _cell("0", evidence_id="r0_2"),
            _cell("", evidence_id="r0_3"),
            _cell("–", evidence_id="r0_4"),
            _cell("/", evidence_id="r0_5"),
        ],
    ]
    notes = [
        ScopedNote(note_id="N1", scope="row", target="0001", text="Miễn học phí theo NĐ 116"),
        ScopedNote(note_id="N2", scope="row", target="0002", text="Ghi chú ngành khác"),
    ]
    projected = project_table(
        {"row_count": len(rows), "column_count": 6, "rows": rows},
        table_id="tbl_demo",
        source_table_citation="ocr_1:ev_p001_b001",
        title="Bảng chỉ tiêu 2025",
        column_years={2: 2025, 3: 2025, 4: 2025, 5: 2025},
        year_statuses={2025: "interim"},
        scoped_notes=notes,
        defined_symbols={"–"},
    )
    meta = DocumentCardMeta(doc_number="27/QĐ-ĐHQN", doc_year=2026)

    card = render_fact_to_row_card(projected.facts[0], projected, document_meta=meta)

    assert "[Nguồn: 27/QĐ-ĐHQN (Ban hành 2026) | Dữ liệu năm: 2025 (interim) | Bảng: Bảng chỉ tiêu 2025]" in card.text
    assert "Đối tượng: Sư phạm Toán (Mã: 0001)" in card.text
    assert "Chỉ tiêu: 0;" in card.text
    assert "Điểm sàn: [Ô TRỐNG - chưa nhập]" in card.text
    assert "Học phí: – (ký hiệu có chú thích)" in card.text
    assert 'Ký hiệu: [KÝ HIỆU "/" - chưa có định nghĩa]' in card.text
    assert "N1: Miễn học phí theo NĐ 116" in card.text
    assert "N2:" not in card.text


def test_small_headed_table_keeps_whole_in_single_row_card():
    table = {
        "row_count": 4,
        "column_count": 2,
        "rows": [
            [_cell("IELTS", header=True, evidence_id="h0"), _cell("Điểm quy đổi", header=True, evidence_id="h1")],
            [_cell("5.5", evidence_id="r1_0"), _cell("8,5", evidence_id="r1_1")],
            [_cell("6.0", evidence_id="r2_0"), _cell("9,0", evidence_id="r2_1")],
            [_cell("6.5", evidence_id="r3_0"), _cell("Chưa công bố", evidence_id="r3_1")],
        ],
    }
    projected = project_table(
        table,
        table_id="tbl_ielts",
        source_table_citation="ocr_2:ev_p003_b001",
        title="Bảng quy đổi IELTS",
    )

    cards = render_projection_to_cards(projected)

    assert len(cards) == 1
    assert cards[0].keep_whole_in_chunk is True
    assert len(cards[0].fact_ids) == 3
    assert "8,5" in cards[0].text
    assert "9,0" in cards[0].text
    assert "[CHƯA CÔNG BỐ: Chưa công bố]" in cards[0].text


def test_large_table_renders_individual_cards_for_data_and_summary_skipping_group_banners():
    rows = [
        [
            _cell("Mã", header=True, evidence_id="h0"),
            _cell("Tên ngành", header=True, evidence_id="h1"),
            _cell("Chỉ tiêu", header=True, evidence_id="h2"),
        ],
        [_cell("I. NHÓM NGÀNH KỸ THUẬT", col_span=3, evidence_id="grp_1")],
    ]
    for i in range(10):
        rows.append(
            [
                _cell(f"00{i + 1:02d}", evidence_id=f"r{i}_0"),
                _cell(f"Ngành {i + 1}", evidence_id=f"r{i}_1"),
                _cell(str(50 + i), evidence_id=f"r{i}_2"),
            ]
        )
    rows.append([_cell("Tổng cộng", col_span=2, evidence_id="sum_0"), _cell("545", evidence_id="sum_2")])

    projected = project_table(
        {"row_count": len(rows), "column_count": 3, "rows": rows},
        table_id="tbl_big",
        source_table_citation="ocr_3:ev_p007_b001",
        title="Bảng chỉ tiêu lớn",
    )

    cards = render_projection_to_cards(projected)

    assert projected.keep_whole_in_chunk is False
    # 10 data rows + 1 summary row = 11 cards (group_header banner is inherited, not a standalone card)
    assert len(cards) == 11
    assert all(c.row_kind in {"data", "summary"} for c in cards)
    assert "Nhóm: I. NHÓM NGÀNH KỸ THUẬT" in cards[0].text
    assert cards[-1].row_kind == "summary"
    assert "[DÒNG TỔNG HỢP]" in cards[-1].text


def test_expand_cards_context_pulls_detail_pointers_cross_references_and_respects_budget():
    long_text = " ".join(f"tu_{i}" for i in range(120))
    table = {
        "row_count": 2,
        "column_count": 3,
        "rows": [
            [
                _cell("Mã ngành", header=True, evidence_id="h0"),
                _cell("Tên ngành", header=True, evidence_id="h1"),
                _cell("Điều kiện phụ", header=True, evidence_id="h2"),
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
        table_id="tbl_ext",
        source_table_citation="ocr_7:ev_p009_b001",
        title="Bảng điều kiện phụ",
        cross_references=["phu_luc_II_2", "missing_ref"],
    )
    cards = render_projection_to_cards(projected)
    md_blocks = {
        "ocr_7:c1_2": "Nội dung đầy đủ điều kiện phụ từ Markdown gốc.",
        "phu_luc_II_2": "Phụ lục II.2: Ngoại lệ miễn thi môn ngoại ngữ cho thí sinh có chứng chỉ quốc tế.",
    }

    expanded_full = expand_cards_context(cards, md_blocks=md_blocks)
    assert len(expanded_full) == 1
    item = expanded_full[0]
    assert item.expanded_details == {"ocr_7:c1_2": md_blocks["ocr_7:c1_2"]}
    assert item.expanded_references == {"phu_luc_II_2": md_blocks["phu_luc_II_2"]}
    assert item.unresolved_pointers == ["missing_ref"]
    assert item.omitted_pointers == []
    assert "Nội dung đầy đủ điều kiện phụ" in item.combined_text
    assert "Phụ lục II.2" in item.combined_text

    # Tight budget: enough for base card + detail pointer, but not cross_reference
    base_bytes = len(cards[0].text.encode("utf-8"))
    detail_label = next(iter(cards[0].detail_md_pointers))
    detail_section = f"[Chi tiết {detail_label} (ocr_7:c1_2)]: {md_blocks['ocr_7:c1_2']}"
    tight_budget = base_bytes + len(detail_section.encode("utf-8")) + 10
    expanded_tight = expand_cards_context(cards, md_blocks=md_blocks, max_bytes=tight_budget)
    assert expanded_tight[0].expanded_details == {"ocr_7:c1_2": md_blocks["ocr_7:c1_2"]}
    assert expanded_tight[0].expanded_references == {}
    assert expanded_tight[0].omitted_pointers == ["phu_luc_II_2"]


def test_large_table_preserves_inline_note_cards_with_group():
    rows = [
        [
            _cell("Mã", header=True, evidence_id="h0"),
            _cell("Tên ngành", header=True, evidence_id="h1"),
            _cell("Chỉ tiêu", header=True, evidence_id="h2"),
        ],
        [_cell("I. NHÓM SƯ PHẠM", col_span=3, evidence_id="grp_1")],
    ]
    for i in range(10):
        rows.append(
            [
                _cell(f"00{i + 1:02d}", evidence_id=f"r{i}_0"),
                _cell(f"Ngành {i + 1}", evidence_id=f"r{i}_1"),
                _cell(str(50 + i), evidence_id=f"r{i}_2"),
            ]
        )
    rows.append(
        [
            _cell("Áp dụng riêng cho thí sinh đạt giải học sinh giỏi cấp tỉnh trở lên", col_span=3, evidence_id="note_1")
        ]
    )

    projected = project_table(
        {"row_count": len(rows), "column_count": 3, "rows": rows},
        table_id="tbl_big_note",
        source_table_citation="ocr_3:ev_p008_b001",
        title="Bảng lớn có inline note",
    )
    cards = render_projection_to_cards(projected)

    note_cards = [c for c in cards if c.row_kind == "inline_note"]
    assert len(note_cards) == 1
    assert "Nhóm: I. NHÓM SƯ PHẠM" in note_cards[0].text
    assert "Áp dụng riêng cho thí sinh" in note_cards[0].text


def test_expand_cards_context_prioritizes_all_detail_pointers_before_any_cross_reference():
    long_a = " ".join(f"a_{i}" for i in range(120))
    long_b = " ".join(f"b_{i}" for i in range(120))
    rows = [
        [
            _cell("Mã", header=True, evidence_id="h0"),
            _cell("Tên", header=True, evidence_id="h1"),
            _cell("Chi tiết", header=True, evidence_id="h2"),
        ],
    ]
    for i in range(10):
        detail = long_a if i == 0 else long_b if i == 1 else "Ngắn"
        rows.append(
            [
                _cell(f"00{i + 1:02d}", evidence_id=f"r{i}_0"),
                _cell(f"Mục {i + 1}", evidence_id=f"r{i}_1"),
                _cell(detail, evidence_id=f"r{i}_2"),
            ]
        )
    projected = project_table(
        {"row_count": len(rows), "column_count": 3, "rows": rows},
        table_id="tbl_prio",
        source_table_citation="ocr_9:ev_p001_b001",
        cross_references=["xref_heavy"],
    )
    top_cards = render_projection_to_cards(projected)[:2]
    md_blocks = {
        "ocr_9:r0_2": "Chi tiết đầy đủ A.",
        "ocr_9:r1_2": "Chi tiết đầy đủ B.",
        "xref_heavy": "Phụ lục tham chiếu rất dài " + ("x" * 200),
    }

    base_bytes = sum(len(c.text.encode("utf-8")) for c in top_cards)
    d1 = "[Chi tiết Chi tiết (ocr_9:r0_2)]: Chi tiết đầy đủ A."
    d2 = "[Chi tiết Chi tiết (ocr_9:r1_2)]: Chi tiết đầy đủ B."
    budget = base_bytes + len(d1.encode("utf-8")) + len(d2.encode("utf-8")) + 10

    expanded = expand_cards_context(top_cards, md_blocks=md_blocks, max_bytes=budget)
    assert expanded[0].expanded_details == {"ocr_9:r0_2": "Chi tiết đầy đủ A."}
    assert expanded[1].expanded_details == {"ocr_9:r1_2": "Chi tiết đầy đủ B."}
    assert expanded[0].expanded_references == {}
    assert expanded[0].omitted_pointers == ["xref_heavy"]
