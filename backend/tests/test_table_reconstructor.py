"""Unit tests for Canonical Multi-Page Table Reconstruction & Normalization."""

from __future__ import annotations

import pytest

from app.modules.knowledge.normalization.markdown_renderer import (
    render_canonical_table_markdown,
)
from app.modules.knowledge.normalization.models import (
    CanonicalCell,
    CanonicalRow,
    CanonicalTable,
    SourceSpan,
)
from app.modules.knowledge.normalization.table_reconstructor import (
    clean_table_columns,
    is_orphan_continuation_row,
    is_repeated_header,
    merge_continuation,
    reconstruct_multi_page_tables,
    table_schema_key,
)


def _cell(val: str, page: int = 1) -> CanonicalCell:
    return CanonicalCell(
        raw_value=val,
        normalized_value=val if val else None,
        source_span=SourceSpan(page_number=page),
    )


def test_table_schema_key_deterministic():
    headers_a = ["TT", "Nội dung nhiệm vụ", "Đơn vị chủ trì", "Sản phẩm kết quả"]
    headers_b = ["TT ", " Nội dung nhiệm vụ :", "Đơn vị chủ trì.-", "SẢN PHẨM KẾT QUẢ"]
    headers_diff = ["STT", "Mã ngành", "Tên ngành", "Chỉ tiêu"]

    assert table_schema_key(headers_a) == table_schema_key(headers_b)
    assert table_schema_key(headers_a) != table_schema_key(headers_diff)


def test_is_repeated_header():
    expected_headers = ["TT", "Nội dung nhiệm vụ", "Đơn vị chủ trì", "Sản phẩm"]
    header_row_cells = [_cell("TT"), _cell("Nội dung nhiệm vụ"), _cell("Đơn vị chủ trì"), _cell("Sản phẩm")]
    data_row_cells = [_cell("1.1"), _cell("Quy hoạch nhân sự"), _cell("Phòng TC-NS"), _cell("Quyết định")]

    assert is_repeated_header(header_row_cells, expected_headers) is True
    assert is_repeated_header(data_row_cells, expected_headers) is False


def test_is_orphan_continuation_row():
    # Primary key (TT) is empty, but content column has continuation text
    orphan_cells = [_cell(""), _cell("kỳ 2030 - 2035 tiếp nối"), _cell(""), _cell("")]
    normal_cells = [_cell("1.2"), _cell("Kiện toàn tổ chức"), _cell("Phòng TC-NS"), _cell("Đề án")]

    assert is_orphan_continuation_row(CanonicalRow(row_id="r1", cells=orphan_cells)) is True
    assert is_orphan_continuation_row(CanonicalRow(row_id="r2", cells=normal_cells)) is False


def test_merge_continuation():
    prev_row = CanonicalRow(
        row_id="prev",
        cells=[_cell("1.1"), _cell("Quy hoạch Ban Chấp hành"), _cell("Văn phòng"), _cell("Quyết định")],
        source_pages=[3],
    )
    next_row = CanonicalRow(
        row_id="next",
        cells=[_cell(""), _cell("nhiệm kỳ 2030 - 2035"), _cell(""), _cell("")],
        source_pages=[4],
    )

    merged = merge_continuation(prev_row, next_row)
    assert merged.is_continuation is True
    assert merged.source_pages == [3, 4]
    assert merged.cells[0].raw_value == "1.1"
    assert merged.cells[1].raw_value == "Quy hoạch Ban Chấp hành nhiệm kỳ 2030 - 2035"
    assert merged.cells[2].raw_value == "Văn phòng"


def test_clean_table_columns_drops_empty_phantom_columns():
    headers = ["TT", "Cột 2", "Nội dung", "Cột 4", "Đơn vị"]
    # Cột 2 and Cột 4 are >85% empty
    rows = [
        CanonicalRow(row_id="r1", cells=[_cell("1"), _cell(""), _cell("Nhiệm vụ 1"), _cell(""), _cell("Khoa CNTT")]),
        CanonicalRow(row_id="r2", cells=[_cell("2"), _cell(""), _cell("Nhiệm vụ 2"), _cell(""), _cell("Phòng ĐT")]),
    ]

    clean_h, clean_r = clean_table_columns(headers, rows)
    assert clean_h == ["TT", "Nội dung", "Đơn vị"]
    assert len(clean_r[0].cells) == 3
    assert clean_r[0].cells[1].raw_value == "Nhiệm vụ 1"


def test_reconstruct_multi_page_tables_stitches_contiguous_pages():
    headers = ["STT", "Tên ngành", "Tổ hợp môn"]
    key = table_schema_key(headers)

    table_page_2 = CanonicalTable(
        table_id="tbl_p2",
        schema_key=key,
        headers=headers,
        rows=[
            CanonicalRow(row_id="p2_r1", cells=[_cell("1"), _cell("Quản lý giáo dục"), _cell("(Văn, Sử, Địa)")]),
            CanonicalRow(row_id="p2_r2", cells=[_cell("2"), _cell("Giáo dục Mầm non"), _cell("(Văn, Toán, NK)")]),
        ],
        source_pages=[2],
    )

    table_page_3 = CanonicalTable(
        table_id="tbl_p3",
        schema_key=key,
        headers=headers,
        rows=[
            # Repeated header line at top of page 3
            CanonicalRow(row_id="p3_header", cells=[_cell("STT"), _cell("Tên ngành"), _cell("Tổ hợp môn")]),
            # Real data
            CanonicalRow(row_id="p3_r1", cells=[_cell("3"), _cell("Giáo dục Tiểu học"), _cell("(Văn, Anh, Toán)")]),
        ],
        source_pages=[3],
    )

    reconstructed = reconstruct_multi_page_tables([table_page_2, table_page_3])

    assert len(reconstructed) == 1
    master = reconstructed[0]
    assert master.source_pages == [2, 3]
    # Header row should be dropped, leaving 3 data rows
    assert len(master.rows) == 3
    assert master.rows[0].cells[1].raw_value == "Quản lý giáo dục"
    assert master.rows[1].cells[1].raw_value == "Giáo dục Mầm non"
    assert master.rows[2].cells[1].raw_value == "Giáo dục Tiểu học"


def test_reconstructs_continuation_page_without_a_repeated_header():
    headers = ["STT", "Mã ngành", "Tên ngành", "Phương thức", "Chỉ tiêu", "Tổ hợp môn"]
    master = CanonicalTable(
        table_id="admissions_p2",
        schema_key=table_schema_key(headers),
        headers=headers,
        rows=[
            CanonicalRow(
                row_id="p2_r5",
                cells=[
                    _cell("5", 2),
                    _cell("7140206", 2),
                    _cell("Giáo dục Thể chất", 2),
                    _cell("5", 2),
                    _cell("", 2),
                    _cell("(Toán, Sinh, NK TDTT)", 2),
                ],
                source_pages=[2],
            )
        ],
        source_pages=[2],
    )
    continuation = CanonicalTable(
        table_id="admissions_p3",
        schema_key="empty_schema",
        headers=["", "", "", "", "", "(Toán, Văn, NK TDTT)"],
        rows=[
            CanonicalRow(
                row_id="p3_r6",
                cells=[
                    _cell("6", 3),
                    _cell("7140209", 3),
                    _cell("Sư phạm Toán học", 3),
                    _cell("1,4", 3),
                    _cell("", 3),
                    _cell("(Toán, Lý, Hóa)", 3),
                ],
                source_pages=[3],
            )
        ],
        source_pages=[3],
    )

    reconstructed = reconstruct_multi_page_tables([master, continuation])

    assert len(reconstructed) == 1
    assert reconstructed[0].headers == headers
    assert len(reconstructed[0].rows) == 2
    assert "(Toán, Văn, NK TDTT)" in reconstructed[0].rows[0].cells[5].raw_value
    assert reconstructed[0].rows[1].cells[1].raw_value == "7140209"


def test_clean_table_columns_normalizes_visual_spacer_columns_and_mixed_rows():
    headers = [
        "TT",
        "",
        "",
        "Nội dung nhiệm vụ",
        "",
        "Đơn vị chủ trì",
        "Đơn vị phối hợp",
        "Thời gian bắt đầu",
        "Thời gian hoàn thành",
        "Sản phẩm kết quả",
        "",
    ]
    rows = [
        CanonicalRow(
            row_id="category",
            cells=[
                _cell("", 3),
                _cell("I", 3),
                _cell("", 3),
                _cell("", 3),
                _cell("Công tác nhân sự", 3),
                _cell("", 3),
                _cell("", 3),
                _cell("", 3),
                _cell("", 3),
                _cell("", 3),
                _cell("", 3),
            ],
            source_pages=[3],
        ),
        CanonicalRow(
            row_id="wide",
            cells=[
                _cell("1.1", 3),
                _cell("", 3),
                _cell("", 3),
                _cell("Quy hoạch nhân sự", 3),
                _cell("", 3),
                _cell("Phòng TC-NS", 3),
                _cell("Các đơn vị", 3),
                _cell("10/2025", 3),
                _cell("12/2025", 3),
                _cell("Quyết định", 3),
                _cell("", 3),
            ],
            source_pages=[3],
        ),
        CanonicalRow(
            row_id="compact",
            cells=[
                _cell("1.2", 4),
                _cell("Kiện toàn tổ chức", 4),
                _cell("Phòng TC-NS", 4),
                _cell("Các khoa", 4),
                _cell("10/2025", 4),
                _cell("12/2025", 4),
                _cell("Đề án", 4),
            ],
            source_pages=[4],
        ),
    ]

    clean_headers, clean_rows = clean_table_columns(headers, rows)

    assert clean_headers == [
        "TT",
        "Nội dung nhiệm vụ",
        "Đơn vị chủ trì",
        "Đơn vị phối hợp",
        "Thời gian bắt đầu",
        "Thời gian hoàn thành",
        "Sản phẩm kết quả",
    ]
    assert clean_rows[0].cells[0].raw_value == "I"
    assert clean_rows[0].cells[1].raw_value == "Công tác nhân sự"
    assert clean_rows[1].cells[1].raw_value == "Quy hoạch nhân sự"
    assert clean_rows[2].cells[1].raw_value == "Kiện toàn tổ chức"


def test_render_canonical_table_markdown_is_single_line():
    headers = ["STT", "Mã ngành", "Tổ hợp"]
    table = CanonicalTable(
        table_id="t1",
        schema_key="key",
        headers=headers,
        rows=[
            CanonicalRow(
                row_id="r1",
                cells=[
                    _cell("1"),
                    _cell("7140114"),
                    _cell("(Văn, Sử, Địa)\n(Văn, Toán, Anh)\n(Văn, Toán, Sử)"),
                ],
            ),
        ],
        source_pages=[1],
    )

    md = render_canonical_table_markdown(table)
    lines = md.splitlines()

    # Must have exactly 3 lines: header, separator, 1 data row
    assert len(lines) == 3
    assert lines[0].startswith("| STT |")
    assert lines[1].startswith("| :---: |")
    # Multi-line cell must be joined with <br> on a single line!
    assert "<br>" in lines[2]
    assert "\n" not in lines[2]


@pytest.mark.asyncio
async def test_pdf_parser_does_not_duplicate_table_text():
    import pymupdf as fitz

    from app.modules.knowledge.parsers.pdf_parser import PyMuPdfParser

    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    # 1. Đoạn văn phía trên
    page.insert_text((50, 50), "QUYET DINH BAN HANH KE HOACH NAM HOC")
    # 2. Vẽ bảng lưới rõ ràng
    # Đường kẻ ngang
    page.draw_line((50, 100), (550, 100))
    page.draw_line((50, 140), (550, 140))
    page.draw_line((50, 180), (550, 180))
    # Đường kẻ dọc
    page.draw_line((50, 100), (50, 180))
    page.draw_line((200, 100), (200, 180))
    page.draw_line((550, 100), (550, 180))
    # Chữ trong header bảng
    page.insert_text((60, 125), "Ma nhiem vu")
    page.insert_text((210, 125), "Noi dung trien khai")
    # Chữ trong hàng dữ liệu bảng
    page.insert_text((60, 165), "NV-01")
    page.insert_text((210, 165), "Trien khai dao tao tri tue nhan tao")
    # 3. Đoạn văn phía dưới
    page.insert_text((50, 250), "HIEU TRUONG KY TEN VA DONG DAU")

    pdf_bytes = doc.write()
    doc.close()

    parser = PyMuPdfParser()
    parsed = await parser.parse(pdf_bytes, "test_table_no_duplicate.pdf")

    # Kiểm tra:
    # 1. Văn bản ngoài bảng phải có
    assert "QUYET DINH BAN HANH KE HOACH NAM HOC" in parsed.raw_text
    assert "HIEU TRUONG KY TEN VA DONG DAU" in parsed.raw_text
    # 2. Bảng phải được bóc tách
    assert len(parsed.tables) >= 1
    # 3. Tỷ lệ lặp: chuỗi "NV-01" chỉ được xuất hiện đúng 1 lần trong parsed.raw_text (bên trong bảng markdown)!
    count_nv01 = parsed.raw_text.count("NV-01")
    assert count_nv01 == 1, f"Expected 'NV-01' to appear exactly once, but appeared {count_nv01} times!"


def test_suppress_nested_tables():
    from unittest.mock import MagicMock

    from app.modules.knowledge.parsers.blocks import suppress_nested_tables

    # Table 0: Large parent table covering entire width
    t0 = MagicMock()
    t0.bbox = (37.0, 85.0, 808.0, 506.0)

    # Table 1: Nested sub-table inside cell 6.8 of Table 0
    t1 = MagicMock()
    t1.bbox = (636.0, 409.0, 802.0, 473.0)

    # Table 2: Another independent table below
    t2 = MagicMock()
    t2.bbox = (37.0, 520.0, 808.0, 700.0)

    result = suppress_nested_tables([t0, t1, t2])
    # Table 1 should be suppressed because it is completely inside Table 0
    assert len(result) == 2
    assert t0 in result
    assert t2 in result
    assert t1 not in result


@pytest.mark.asyncio
async def test_extract_page_blocks_suppresses_side_by_side_tables_text():
    import pymupdf as fitz

    from app.modules.knowledge.parsers.blocks import extract_page_blocks

    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # Header text
    page.insert_text((50, 50), "Dieu kien xet tuyen")

    # Table 1: IELTS (left: 100 to 280, top: 100 to 200)
    page.draw_rect((100, 100, 280, 200))
    page.draw_line((100, 130), (280, 130))
    page.draw_line((190, 100), (190, 200))
    page.insert_text((110, 120), "IELTS")
    page.insert_text((200, 120), "Quy doi")
    page.insert_text((110, 160), "5.0")
    page.insert_text((200, 160), "8.0")

    # Table 2: VSTEP (left: 300 to 480, top: 100 to 200)
    page.draw_rect((300, 100, 480, 200))
    page.draw_line((300, 130), (480, 130))
    page.draw_line((390, 100), (390, 200))
    page.insert_text((310, 120), "VSTEP")
    page.insert_text((400, 120), "Quy doi")
    page.insert_text((310, 160), "4.0")
    page.insert_text((400, 160), "8.0")

    # Footer text
    page.insert_text((50, 250), "Thi sinh nop chung chi tai phong dao tao")

    blocks = extract_page_blocks(page)
    table_blocks = [b for b in blocks if b["type"] == "table"]
    text_blocks = [b for b in blocks if b["type"] == "text"]

    # Table blocks should be extracted
    assert len(table_blocks) >= 1

    # Text blocks must NOT include the raw cell contents inside the tables
    for tb in text_blocks:
        txt = tb["text"]
        assert "5.0" not in txt or "Thi sinh" in txt
        assert "4.0" not in txt or "Thi sinh" in txt


def test_detect_open_top_lines_and_rescue_table():
    """Verify that an open-top table continuation (missing top horizontal border) is rescued."""
    import pymupdf as fitz

    from app.modules.knowledge.parsers.blocks import detect_open_top_lines, extract_page_blocks

    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # 4 vertical lines from y=50 to y=65 (row 1) and y=65 to y=80 (row 2)
    # NO horizontal line at y=50!
    for x in [50, 250, 470, 580]:
        page.draw_line((x, 50), (x, 80))

    # Horizontal lines only at y=65 (between row 1 and row 2) and y=80 (bottom)
    page.draw_line((50, 65), (580, 65))
    page.draw_line((50, 80), (580, 80))

    # Text in row 1
    page.insert_text((70, 60), "Dong phuong hoc")
    page.insert_text((490, 60), "7310608")

    # Text in row 2
    page.insert_text((70, 75), "Tieng Trung")
    page.insert_text((490, 75), "7220204")

    # detect_open_top_lines should find the missing top line at y=50
    missing_lines = detect_open_top_lines(page)
    assert len(missing_lines) == 1
    assert abs(missing_lines[0][0][1] - 50.0) < 1.0

    # extract_page_blocks should extract the table including Dong phuong hoc
    blocks = extract_page_blocks(page)
    table_blocks = [b for b in blocks if b["type"] == "table"]
    assert len(table_blocks) == 1

    tbl = table_blocks[0]
    # Coordinates top should be around 50/800 * 100 = 6.25%
    assert tbl["coordinates"]["y"] < 7.0
    assert "Dong phuong hoc" in tbl["text"]
    assert "7310608" in tbl["text"]
    assert "Tieng Trung" in tbl["text"]


