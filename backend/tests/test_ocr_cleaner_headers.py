
from app.modules.ocr.cleaner import (
    inherit_table_headers_for_continuation_pages,
    merge_ocr_orphan_table_rows,
)


def test_inherit_table_headers_for_continuation_pages():
    """Verify that multi-page tables inherit column headers cleanly on subsequent pages."""
    p1 = {
        "page_number": 1,
        "extracted_text": (
            "| STT | Tên ngành | Học phí |\n"
            "| :---: | :--- | :--- |\n"
            "| 1 | Kế toán | 23.660.000 |"
        ),
    }
    p2 = {
        "page_number": 2,
        "extracted_text": (
            "| :---: | :--- | :--- |\n"
            "|  | Kế toán tiếp | 37.440.000 |\n"
            "| 2 | Ngôn Ngữ Anh | 32.550.000 |"
        ),
    }

    result = inherit_table_headers_for_continuation_pages([p1, p2])
    p2_text = result[1]["extracted_text"]
    assert "| STT | Tên ngành | Học phí |" in p2_text
    assert "| :---: | :--- | :--- |" in p2_text
    assert "Kế toán tiếp" in p2_text
    assert "| :---: | :--- | :--- |\n| :---: | :--- | :--- |" not in p2_text


def test_merge_ocr_orphan_table_rows_preserves_installments():
    """Independent fee installment records must remain independent data rows and not squashed with <br>."""
    sample = (
        "| STT | Tên ngành | Khối ngành | Thời gian | Hình thức đào tạo | Học phí | Ghi chú |\n"
        "| :---: | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| 1 | Kế toán | III | 2 | Tốt nghiệp cùng ngành | 23.660.000 | |\n"
        "| | | | | Học phí đợt 1 | 5.600.000 | Học phí thu theo 4 đợt |\n"
        "| | | | | Học phí đợt 2 | 5.600.000 | |"
    )
    cleaned = merge_ocr_orphan_table_rows(sample)
    assert "<br>" not in cleaned
    assert "Học phí đợt 1" in cleaned
    assert "Học phí đợt 2" in cleaned
