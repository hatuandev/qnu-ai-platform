"""Test suite for Universal Report & Artifact Exporter Service."""

import io

import openpyxl
import pytest
from docx import Document

from app.modules.tools.universal_report import (
    ReportTable,
    UniversalReportPayload,
    export_universal_report,
    generate_docx_report,
    generate_excel_report,
)


@pytest.fixture
def sample_payload() -> UniversalReportPayload:
    return UniversalReportPayload(
        title="Phiếu Tư Vấn Tuyển Sinh & Kế Hoạch Nguyện Vọng QNU 2026",
        subtitle="Hệ Thống Trợ Lý Ảo Tuyển Sinh Thông Minh — Trường Đại học Quy Nhơn",
        issuing_unit="TRƯỜNG ĐẠI HỌC QUY NHƠN",
        metadata={
            "Họ và tên thí sinh": "Trần Văn An",
            "Tổ hợp xét tuyển": "A00 (Toán, Vật lý, Hóa học)",
            "Điểm 3 môn": "23.50",
            "Khu vực ưu tiên": "KV1 (+0.75 điểm)",
            "Tổng điểm xét tuyển": "24.25",
            "Ngày tư vấn": "29/09/2026",
        },
        summary_paragraphs=[
            "Thí sinh có tổng điểm xét tuyển đạt 24.25 điểm, có cơ hội trúng tuyển rất cao vào các ngành thuộc khối Công nghệ và Kỹ thuật của Trường Đại học Quy Nhơn.",
            "Khuyến nghị đặt nguyện vọng ngành Kỹ thuật phần mềm (điểm chuẩn 23.0) ở NV1 hoặc NV2 trong vùng an toàn, và ngành Công nghệ thông tin (điểm chuẩn 24.5) ở NV1 để thử vận may.",
        ],
        tables=[
            ReportTable(
                sheet_name="Kế hoạch nguyện vọng",
                table_title="BẢNG ĐỀ XUẤT THỨ TỰ NGUYỆN VỌNG XÉT TUYỂN 2026",
                headers=["STT", "Nguyện vọng", "Mã ngành", "Tên ngành đào tạo", "Tổ hợp", "Điểm chuẩn 2025", "Chênh lệch", "Đánh giá cơ hội"],
                rows=[
                    [1, "NV 1", "7480201", "Công nghệ thông tin", "A00, A01", 24.50, "-0.25", "Thử thách (Reach)"],
                    [2, "NV 2", "7480103", "Kỹ thuật phần mềm", "A00, A01, D01", 23.00, "+1.25", "Mục tiêu (Target)"],
                    [3, "NV 3", "7480101", "Khoa học máy tính", "A00, A01", 22.00, "+2.25", "An toàn (Safe)"],
                    [4, "NV 4", "7140217", "Sư phạm Tin học", "A00, A01", 21.50, "+2.75", "An toàn (Safe)"],
                ],
                notes="Điểm chuẩn 2025 mang tính chất tham khảo. Thứ tự nguyện vọng trên cổng Bộ GD&ĐT cần xác nhận trước ngày 30/07/2026.",
            ),
            ReportTable(
                sheet_name="Đối chiếu 3 năm",
                table_title="ĐỐI CHIẾU ĐIỂM CHUẨN 3 NĂM GẦN NHẤT (2023 - 2025)",
                headers=["Mã ngành", "Tên ngành", "Chỉ tiêu 2026", "Điểm 2023", "Điểm 2024", "Điểm 2025"],
                rows=[
                    ["7480201", "Công nghệ thông tin", 220, 24.0, 24.5, 24.5],
                    ["7480103", "Kỹ thuật phần mềm", 100, 22.5, 23.0, 23.0],
                    ["7480101", "Khoa học máy tính", 80, 21.5, 22.0, 22.0],
                ],
                notes="Chỉ tiêu 2026 dự kiến theo Đề án Tuyển sinh chính thức.",
            ),
        ],
        formats=["xlsx", "docx", "pdf"],
        base_name="phieu_tu_van_tuyen_sinh_tran_van_an",
    )


def test_generate_excel_report(sample_payload: UniversalReportPayload):
    """Verify that Excel generator creates multi-sheet workbook with valid data and styling."""
    excel_bytes = generate_excel_report(sample_payload)
    assert len(excel_bytes) > 0

    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    assert len(sheet_names) == 2
    assert "Kế hoạch nguyện vọng" in sheet_names
    assert "Đối chiếu 3 năm" in sheet_names

    ws1 = wb["Kế hoạch nguyện vọng"]
    assert "TRƯỜNG ĐẠI HỌC QUY NHƠN" in str(ws1["A1"].value)
    # Check that rows were written
    found_cntt = False
    for row in ws1.iter_rows(values_only=True):
        if any("Công nghệ thông tin" in str(cell) for cell in row if cell):
            found_cntt = True
            break
    assert found_cntt, "Major name should be present in Excel worksheet"


def test_generate_docx_report(sample_payload: UniversalReportPayload):
    """Verify that Word generator creates document with header, metadata and tables."""
    docx_bytes = generate_docx_report(sample_payload)
    assert len(docx_bytes) > 0

    doc = Document(io.BytesIO(docx_bytes))
    all_texts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            all_texts.extend(cell.text for cell in row.cells)
    full_text = "\n".join(all_texts)
    assert "TRƯỜNG ĐẠI HỌC QUY NHƠN" in full_text
    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in full_text
    assert "PHIẾU TƯ VẤN TUYỂN SINH" in full_text.upper()

    # Verify tables
    table_texts = []
    for table in doc.tables:
        for row in table.rows:
            table_texts.append(" | ".join(cell.text for cell in row.cells))
    full_table_text = "\n".join(table_texts)
    assert "Trần Văn An" in full_table_text
    assert "Công nghệ thông tin" in full_table_text
    assert "Kỹ thuật phần mềm" in full_table_text


@pytest.mark.asyncio
async def test_export_universal_report(sample_payload: UniversalReportPayload):
    """Verify end-to-end export saving to storage and returning artifacts."""
    artifacts = await export_universal_report(sample_payload)
    assert len(artifacts) >= 2  # XLSX and DOCX guaranteed, PDF depends on Gotenberg availability

    types = [a["type"] for a in artifacts]
    assert "xlsx" in types
    assert "docx" in types

    for art in artifacts:
        assert art["size"] > 0
        assert art["url"].startswith("/platform/v1alpha1/tools/artifacts/")
        assert art["name"].startswith("phieu_tu_van_tuyen_sinh")
