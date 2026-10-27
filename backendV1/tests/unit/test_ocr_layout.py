"""Parsing of Nemotron located output: blocks, tables, spans and refusals.

The parser must never invent a table it cannot reconstruct, and must never drop a
value because it looks empty, zero or like a dash.
"""

from __future__ import annotations

import pytest

from qnu.domains.ocr.layout import parse_page, parse_table
from qnu.platform.errors import AppException


def _block(text: str, label: str, top: float = 0.1) -> str:
    return (
        f"<x_0.10><y_{top:.2f}>{text}<x_0.90><y_{top + 0.05:.2f}><class_{label}>"
    )


def _table(body: str, columns: str = "cccc") -> str:
    return f"\\begin{{tabular}}{{{columns}}} {body} \\end{{tabular}}"


def test_blocks_keep_document_order_and_bbox() -> None:
    layout = parse_page(
        _block("PHỤ LỤC 01", "Title", 0.05)
        + _block("Nội dung", "Text", 0.20)
        + _block("Ghi chú", "Footnote", 0.80)
    )
    assert [block.kind for block in layout.blocks] == ["title", "text", "footnote"]
    assert [block.order for block in layout.blocks] == [1, 2, 3]
    first = layout.blocks[0]
    assert first.bbox == pytest.approx((0.10, 0.05, 0.90, 0.10))
    assert first.text == "PHỤ LỤC 01"
    assert layout.has_tables is False


def test_table_header_marks_every_thead_cell() -> None:
    table = parse_table(
        _table(
            "\\hline \\thead{STT} & \\thead{Chỉ tiêu} & \\thead{Năm 2023} & \\thead{Năm 2024} \\\\ "
            "1 & Chỉ tiêu tuyển sinh & 0 & - \\\\ \\hline"
        )
    )
    assert table.status == "parsed"
    assert table.column_count == 4
    assert all(cell.header for cell in table.rows[0])
    assert not any(cell.header for cell in table.rows[1])


def test_empty_zero_dash_and_units_survive_verbatim() -> None:
    table = parse_table(
        _table(
            "\\thead{Chỉ tiêu} & \\thead{2023} & \\thead{2024} \\\\ "
            "Chỉ tiêu tuyển sinh & 0 & - \\\\ "
            "Chỉ tiêu trúng tuyển & & 150 \\\\ "
            "Điểm chuẩn (thang 30) & 27,5 & -- \\\\",
            columns="ccc",
        )
    )
    assert table.status == "parsed"
    rows = [[cell.text for cell in row] for row in table.rows]
    assert rows[1] == ["Chỉ tiêu tuyển sinh", "0", "-"]
    assert rows[2] == ["Chỉ tiêu trúng tuyển", "", "150"]
    assert rows[3] == ["Điểm chuẩn (thang 30)", "27,5", "--"]


def test_multicolumn_and_multirow_spans_are_recorded() -> None:
    table = parse_table(
        _table(
            "\\multicolumn{2}{c}{\\thead{Nhóm}} & \\thead{Năm} \\\\ "
            "\\multicolumn{1}{c}{} & \\multicolumn{1}{c}{} & \\thead{2023} \\\\ "
            "\\multirow{2}{*}{A} & X & 1 \\\\ "
            " & Y & 2 \\\\",
            columns="ccc",
        )
    )
    assert table.status == "parsed"
    assert table.rows[0][0].col_span == 2
    assert table.rows[0][0].header is True
    assert table.rows[2][0].row_span == 2
    assert table.rows[2][0].text == "A"


def test_unreconstructable_table_is_unsupported_and_keeps_raw_text() -> None:
    table = parse_table(_table("a & b & c \\\\ d \\\\", columns="cc"))
    assert table.status == "unsupported"
    assert table.reason in {"grid_mismatch", "column_count_mismatch", "too_many_columns"}
    assert table.rows == ()


def test_table_without_tabular_wrapper_is_unsupported() -> None:
    table = parse_table("STT & Chỉ tiêu \\\\ 1 & 150 \\\\")
    assert table.status == "unsupported"
    assert table.reason == "unsupported_layout"


def test_inline_latex_is_unescaped_without_rewriting_words() -> None:
    table = parse_table(
        _table(
            "\\thead{\\textbf{Chỉ tiêu}} & \\thead{Đơn vị} \\\\ Tuyển sinh & người \\\\",
            columns="cc",
        )
    )
    assert table.status == "parsed"
    assert table.rows[0][0].text == "Chỉ tiêu"
    assert table.rows[1][1].text == "người"


def test_stray_text_outside_a_block_is_invalid() -> None:
    with pytest.raises(AppException) as caught:
        parse_page("văn bản rơi vãi" + _block("Nội dung", "Text"))
    assert caught.value.code == "ocr_response_invalid"


def test_bbox_outside_unit_range_is_invalid() -> None:
    with pytest.raises(AppException) as caught:
        parse_page("<x_0.10><y_0.10>Nội dung<x_1.40><y_0.20><class_Text>")
    assert caught.value.code == "ocr_response_invalid"


def test_empty_response_yields_an_empty_layout_not_an_error() -> None:
    # An empty body is not a parse error: the adapter rejects it as `ocr_response_empty`
    # and validation decides whether an empty page is legitimately blank or suspicious.
    layout = parse_page("   ")
    assert layout.blocks == ()
    assert layout.text == ""
