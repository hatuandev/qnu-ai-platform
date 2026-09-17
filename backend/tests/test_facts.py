"""Unit Tests for Vietnamese Structured Fact Extraction (Admissions Tables)."""

from __future__ import annotations

from app.modules.knowledge.facts import (
    FactExtractor,
    detect_column_role,
    parse_vietnamese_float,
    parse_vietnamese_int,
)
from app.modules.knowledge.parsers.base import ExtractedTable


def _table(headers: list[str], rows: list[list[str]], page: int = 3) -> ExtractedTable:
    return ExtractedTable(page_number=page, headers=headers, rows=rows, markdown_repr="")


def test_parse_vietnamese_numbers():
    assert parse_vietnamese_int("180") == 180
    assert parse_vietnamese_int("1.200") == 1200
    assert parse_vietnamese_int("") is None
    assert parse_vietnamese_int("1,4") is None  # method list, not an integer
    assert parse_vietnamese_int(None) is None
    assert parse_vietnamese_float("24,5") == 24.5
    assert parse_vietnamese_float("16.500.000") == 16500000.0
    assert parse_vietnamese_float("26.75") == 26.75
    assert parse_vietnamese_float("") is None


def test_detect_column_role_vietnamese_headers():
    assert detect_column_role("Mã xét tuyển") == ("code", None)
    assert detect_column_role("Tên ngành, chương trình xét tuyển") == ("name", None)
    assert detect_column_role("Số lượng tuyển sinh dự kiến") == ("quota", None)
    assert detect_column_role("Điểm chuẩn 2024") == ("benchmark", "2024")
    assert detect_column_role("Tổ hợp môn xét tuyển") == ("combos", None)
    assert detect_column_role("Phương thức tuyển sinh") == ("method", None)
    assert detect_column_role("Học phí/năm 2025") == ("tuition", "2025")
    assert detect_column_role("STT")[0] is None
    assert detect_column_role("Ghi chú")[0] is None


def test_extract_admissions_table_row_facts():
    extractor = FactExtractor()
    table = _table(
        ["STT", "Mã xét tuyển", "Tên ngành", "Phương thức", "Số lượng", "Tổ hợp môn"],
        [
            ["1", "7480201", "Công nghệ thông tin", "1,4", "180", "(Toán, Lý, Hóa)"],
            ["2", "7140209", "Sư phạm Toán học", "1", "", "(Toán, Lý, Anh)"],
        ],
    )
    facts = extractor.extract([table], collection_id="col_1", document_id="d1")
    by_attr = {(f["entity_name"], f["attribute_name"]): f["attribute_value"] for f in facts}

    assert by_attr[("Công nghệ thông tin (7480201)", "Mã ngành")] == "7480201"
    assert by_attr[("Công nghệ thông tin (7480201)", "Chỉ tiêu")] == "180"
    # Method lists stay raw text, never parsed as decimals
    assert by_attr[("Công nghệ thông tin (7480201)", "Phương thức tuyển sinh")] == "1,4"
    assert (
        by_attr[("Công nghệ thông tin (7480201)", "Tổ hợp xét tuyển")]
        == "(Toán, Lý, Hóa)"
    )
    # Empty quota cell produces no fact (honest skip)
    assert ("Sư phạm Toán học (7140209)", "Chỉ tiêu") not in by_attr
    # Every table keeps exactly one summary fact
    assert sum(1 for f in facts if f["entity_type"] == "table") == 1


def test_extract_benchmark_with_year_suffix():
    extractor = FactExtractor()
    table = _table(
        ["Mã ngành", "Tên ngành", "Điểm chuẩn 2024", "Điểm chuẩn 2025"],
        [["7480201", "Công nghệ thông tin", "24,5", "25"]],
    )
    facts = extractor.extract([table], collection_id="col_1", document_id="d1")
    by_attr = {(f["entity_name"], f["attribute_name"]): f["attribute_value"] for f in facts}
    entity = "Công nghệ thông tin (7480201)"
    assert by_attr[(entity, "Điểm chuẩn 2024")] == "24.5"
    assert by_attr[(entity, "Điểm chuẩn 2025")] == "25"


def test_unknown_table_yields_summary_only():
    extractor = FactExtractor()
    table = _table(["STT", "Nội dung", "Ghi chú"], [["1", "Họp giao ban", "Sáng thứ 2"]])
    facts = extractor.extract([table], collection_id="col_1", document_id="d1")
    assert len(facts) == 1
    assert facts[0]["entity_type"] == "table"
    assert facts[0]["confidence"] == 1.0
