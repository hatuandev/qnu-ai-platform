"""Unit tests for direct Excel (.xlsx) extraction pipeline."""

import io

import openpyxl
import pytest

from qnu.domains.ocr.direct_xlsx import extract_xlsx


def test_extract_xlsx_empty_payload_raises():
    with pytest.raises(Exception) as exc_info:
        extract_xlsx(b"")
    assert "xlsx_empty" in str(exc_info.value.code)


def test_extract_xlsx_multisheet_with_headers_and_merged_cells():
    wb = openpyxl.Workbook()
    # Sheet 1: Standard Table
    ws1 = wb.active
    ws1.title = "Dữ liệu sách"
    ws1.append(["ItemId", "Nhan đề", "Tác giả", "Năm XB"])
    ws1.append([1, "Practice and Progress", "Alexander, L.G.", 1994])
    ws1.append([2, "American business terms Dictionary", "Donald, L.", 1994])

    # Sheet 2: Table with Title row and merged cells
    ws2 = wb.create_sheet(title="Đề tài khoa học")
    ws2.append(["DANH MỤC ĐỀ TÀI CẤP BỘ", "", "", ""])
    ws2.merge_cells("A1:D1")
    ws2.append(["STT", "Nhan đề", "Chủ nhiệm", "SL"])
    ws2.append([1, "Điều khiển phụ tải thông minh", "Huỳnh Đức Hoàn", 2])
    ws2.append([2, "Xử lý nước thải bằng nano", "Nguyễn Phi Hùng", 1])
    # Add a formula row that should be ignored
    ws2.append(["Tổng cộng", "", "", "=SUM(D3:D4)"])

    buf = io.BytesIO()
    wb.save(buf)
    payload = buf.getvalue()

    rendered, plan = extract_xlsx(payload)

    assert rendered.extension == ".xlsx"
    assert rendered.renderer["name"] == "openpyxl"
    assert len(plan.pages) == 2

    # Check Page 1
    page1 = plan.pages[0]
    assert len(page1.layout.blocks) == 1
    table1_block = page1.layout.blocks[0]
    assert table1_block.kind == "table"
    assert table1_block.table is not None
    assert table1_block.table.column_count == 4
    # Header + 2 data rows
    assert len(table1_block.table.rows) == 3
    assert [c.text for c in table1_block.table.rows[0]] == ["ItemId", "Nhan đề", "Tác giả", "Năm XB"]
    assert all(c.header for c in table1_block.table.rows[0])
    assert table1_block.table.rows[1][1].text == "Practice and Progress"

    # Check Page 2
    page2 = plan.pages[1]
    # Block 1 should be Title, Block 2 should be Table
    assert len(page2.layout.blocks) == 2
    title_block = page2.layout.blocks[0]
    assert title_block.kind == "title"
    assert "DANH MỤC ĐỀ TÀI CẤP BỘ" in title_block.text

    table2_block = page2.layout.blocks[1]
    assert table2_block.kind == "table"
    assert table2_block.table is not None
    assert table2_block.table.column_count == 4
    # Formula row =SUM was filtered out: Header + 2 data rows = 3 rows
    assert len(table2_block.table.rows) == 3
    assert [c.text for c in table2_block.table.rows[0]] == ["STT", "Nhan đề", "Chủ nhiệm", "SL"]
    assert table2_block.table.rows[1][2].text == "Huỳnh Đức Hoàn"


def test_extract_xlsx_under_max_rows_succeeds():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DS Sinh Viên"
    ws.append(["MSSV", "Họ tên", "Lớp"])
    for i in range(1, 501):
        ws.append([f"SV{i:04d}", f"Sinh viên {i}", "K46 CNTT"])

    buf = io.BytesIO()
    wb.save(buf)
    payload = buf.getvalue()

    # 500 rows should succeed with max_rows=500
    _rendered, plan = extract_xlsx(payload, max_rows=500)
    assert len(plan.pages) == 1
    table = plan.pages[0].layout.blocks[0].table
    assert table is not None
    # 1 header + 500 data rows = 501
    assert len(table.rows) == 501


def test_extract_xlsx_over_max_rows_raises_clear_error():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DS Sách Quá Lớn"
    ws.append(["Mã", "Tên sách"])
    for i in range(1, 502):
        ws.append([i, f"Cuốn sách số {i}"])

    buf = io.BytesIO()
    wb.save(buf)
    payload = buf.getvalue()

    from qnu.platform.errors import AppException

    with pytest.raises(AppException) as exc_info:
        extract_xlsx(payload, max_rows=500)

    err = exc_info.value
    assert err.code == "xlsx_row_limit_exceeded"
    assert err.status_code == 422
    assert "DS Sách Quá Lớn" in str(err)
    assert "501" in str(err)
    assert "500" in str(err)
    assert "tách nhỏ" in str(err).lower()
    assert "XLSX_MAX_ROWS" in str(err)


def test_extract_xlsx_ignores_empty_and_summary_rows_when_counting():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Kê khai"
    ws.append(["Mã", "Tên", "Số lượng"])
    ws.append([1, "Bàn phím", 10])
    ws.append([2, "Chuột", 20])
    # Empty rows
    ws.append([])
    ws.append(["", "", ""])
    # Formula / summary row
    ws.append(["Tổng cộng", "", "=SUM(C2:C3)"])

    buf = io.BytesIO()
    wb.save(buf)
    payload = buf.getvalue()

    # Even if max_rows is 2, it should succeed because valid data rows = 2
    _rendered, plan = extract_xlsx(payload, max_rows=2)
    assert len(plan.pages) == 1
    table = plan.pages[0].layout.blocks[0].table
    assert len(table.rows) == 3  # 1 header + 2 data rows


def test_extract_xlsx_preserves_sheet_name_in_source_mapping_and_row_card():
    from qnu.domains.knowledge.compilation.evidence import literal_tables
    from qnu.domains.knowledge.index.row_cards import build_row_card_chunks

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dữ liệu chuẩn hóa"
    ws.append(["Mã sách", "Tên sách", "Năm"])
    ws.append(["BK01", "American business terms Dictionary", 1994])

    buf = io.BytesIO()
    wb.save(buf)
    payload = buf.getvalue()

    _rendered, plan = extract_xlsx(payload)
    block = plan.pages[0].layout.blocks[0]
    assert block.table.source_mapping["sheet"] == "Dữ liệu chuẩn hóa"
    assert block.table.source_mapping["title"] == "Sheet: Dữ liệu chuẩn hóa"

    # Simulate compilation document
    doc = {
        "ocr_run_id": "ocr_test",
        "pages": [
            {
                "page_number": 1,
                "blocks": [
                    {
                        "evidence_id": "ev_tbl_1",
                        "table": {
                            "status": "parsed",
                            "rows": [
                                [
                                    {
                                        "text": c.text,
                                        "header": c.header,
                                        "row_span": c.row_span,
                                        "col_span": c.col_span,
                                    }
                                    for c in row
                                ]
                                for row in block.table.rows
                            ],
                            "column_count": block.table.column_count,
                            "source_mapping": block.table.source_mapping,
                        },
                        "source_locator": block.source_locator,
                    }
                ],
            }
        ],
    }

    lit_tables = literal_tables([doc])
    assert len(lit_tables) == 1
    assert lit_tables[0]["title"] == "Sheet: Dữ liệu chuẩn hóa"

    # Convert to Row Card Chunks
    chunks = build_row_card_chunks(lit_tables, doc_title="TaiLieuThuVien.xlsx")
    assert len(chunks) == 1
    chunk_text = chunks[0].text
    assert "[Nguồn: TaiLieuThuVien.xlsx | Trang: 1 | Bảng: Sheet: Dữ liệu chuẩn hóa]" in chunk_text
    assert "American business terms Dictionary" in chunk_text


