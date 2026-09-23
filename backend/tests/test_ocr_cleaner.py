"""Unit Tests for OCR Cleaner & Multi-page Table Stitcher."""

from __future__ import annotations

from app.modules.ocr.cleaner import (
    clean_ocr_table_syntax,
    merge_ocr_orphan_table_rows,
    post_process_ocr_output,
    repair_ocr_split_words_across_pages,
    stitch_ocr_multipage_tables,
)


def test_repair_ocr_split_words_across_pages():
    raw = (
        "|  | Hệ thống hỗ trợ cấu hình các khối nội dung cho landing page như: banner, giới |\n"
        "\n---\n\n"
        "<!-- Trang 4 -->\n"
        "|  | thiệu, hình ảnh, video, nút liên kết |\n"
    )
    repaired = repair_ocr_split_words_across_pages(raw)
    assert "giới thiệu," in repaired

    # Test arbitrary domain words not in any dictionary
    raw_arbitrary = (
        "| 1 | Tổ chức triển khai các đề tài nghiên |\n"
        "\n---\n\n"
        "<!-- Trang 2 -->\n"
        "|  | cứu khoa học cấp Trường |\n"
    )
    repaired_arb = repair_ocr_split_words_across_pages(raw_arbitrary)
    assert "nghiên cứu" in repaired_arb

    # Test hyphenated word break
    raw_hyphen = (
        "Văn bản quy định việc tiến-\n"
        "---\n"
        "<!-- Trang 3 -->\n"
        "hành kiểm định chất lượng giáo dục."
    )
    repaired_hyphen = repair_ocr_split_words_across_pages(raw_hyphen)
    assert "tiến hành" in repaired_hyphen


def test_stitch_multipage_tables_removes_divider_and_merges():
    raw = (
        "| STT | Danh mục | Số lượng |\n"
        "| :---: | :--- | :---: |\n"
        "| 1 | Phần mềm cổng thông tin | 1 |\n"
        "\n---\n\n"
        "<!-- Trang 3 -->\n"
        "| 2 | Quản lý Website Trường | 1 |\n"
    )
    stitched = stitch_ocr_multipage_tables(raw)
    assert "\n---\n" not in stitched
    assert not any(line.strip() == "---" for line in stitched.splitlines())
    assert "| 1 | Phần mềm cổng thông tin | 1 |" in stitched
    assert "| 2 | Quản lý Website Trường | 1 |" in stitched
    # Ensure it is a single valid table
    table_rows = [line for line in stitched.splitlines() if line.startswith("|")]
    assert len(table_rows) == 4  # Header + separator + 2 data rows


def test_stitch_multipage_tables_removes_repeated_header():
    raw = (
        "| STT | Danh mục | Số lượng |\n"
        "| :---: | :--- | :---: |\n"
        "| 1 | Hạng mục A | 1 |\n"
        "\n---\n\n"
        "| STT | Danh mục | Số lượng |\n"
        "| :---: | :--- | :---: |\n"
        "| 2 | Hạng mục B | 1 |\n"
    )
    stitched = stitch_ocr_multipage_tables(raw)
    # The duplicate header should be removed
    assert stitched.count("| STT | Danh mục | Số lượng |") == 1
    assert stitched.count("| :---: | :--- | :---: |") == 1
    assert "| 1 | Hạng mục A | 1 |" in stitched
    assert "| 2 | Hạng mục B | 1 |" in stitched


def test_merge_ocr_orphan_table_rows_with_br():
    raw = (
        "| STT | Danh mục phần mềm | Số lượng | Đơn vị tính |\n"
        "| :---: | :--- | :---: | :---: |\n"
        "| 1.1 | Kế thừa chức năng, dữ liệu cũ |  |  |\n"
        "|  | Bảo đảm hệ thống sau nâng cấp kế thừa các chức năng đang sử dụng. |  |  |\n"
        "|  | Không làm mất dữ liệu, chuyên mục, bài viết. |  |  |\n"
        "| 1.2 | Nâng cấp lõi cổng thông tin |  |  |\n"
    )
    merged = merge_ocr_orphan_table_rows(raw)
    lines = [ln for ln in merged.splitlines() if ln.startswith("|")]
    # Header + separator + Row 1.1 + Row 1.2 = 4 rows
    assert len(lines) == 4
    assert "Kế thừa chức năng, dữ liệu cũ<br>Bảo đảm hệ thống sau nâng cấp" in merged
    assert "chức năng đang sử dụng.<br>Không làm mất dữ liệu" in merged


def test_clean_ocr_table_syntax_and_typos():
    raw = (
        "| A | B |\n"
        "| :--- | :--- |\n"
        "| :--- | :--- |\n"
        "| 1 | Cần đo lường số chỉ hiệu năng của hệ thống |\n"
        "| 2 | Hai bên tiến hành kí hợp đồng kinh tế |\n"
    )
    cleaned = clean_ocr_table_syntax(raw)
    # Duplicate separator removed
    assert cleaned.count("| :--- | :--- |") == 1
    # Typos corrected
    assert "chỉ số hiệu năng" in cleaned
    assert "ký hợp đồng" in cleaned


def test_post_process_ocr_output_end_to_end():
    raw = (
        "## Điều 1. Đối tượng hợp đồng\n\n"
        "| STT | Danh mục phần mềm | Số lượng |\n"
        "| :---: | :--- | :---: |\n"
        "| 1 | Nâng cấp phần mềm | 1 |\n"
        "| 1.1 | Cấu hình landing page: banner, giới |  |\n"
        "\n---\n\n"
        "<!-- Trang 3 -->\n"
        "|  | thiệu, hình ảnh, video |  |\n"
        "| 2 | Quản lý tên miền con | 1 |\n"
    )
    pages = [
        {"page_number": 1, "extracted_text": "Trang 1 text", "word_count": 3, "line_count": 1},
        {"page_number": 2, "extracted_text": "Trang 2 text", "word_count": 3, "line_count": 1},
    ]

    cleaned_text, cleaned_pages = post_process_ocr_output(raw, pages)
    assert "giới thiệu," in cleaned_text
    assert "banner, giới thiệu, hình ảnh, video" in cleaned_text
    assert "\n---\n" not in cleaned_text
    assert not any(line.strip() == "---" for line in cleaned_text.splitlines())
    assert len(cleaned_pages) == 2
