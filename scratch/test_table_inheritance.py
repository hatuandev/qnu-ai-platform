import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import re

from app.modules.ocr.cleaner import (
    _split_table_cells,
    _is_table_separator,
    _is_table_row,
    clean_ocr_table_syntax,
    clean_html_layout_tables,
    merge_ocr_orphan_table_rows,
    stitch_ocr_multipage_tables,
)

# Raw output Trang 1
p1_text = """### I. Mức học phí theo khối ngành
*Đơn vị tính: VND*

| STT | Tên ngành | Khối ngành | Thời gian học (năm) | Hình thức đào tạo | Học phí toàn khóa | Ghi chú |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Kế toán | III | 2 | Tốt nghiệp trình độ cao đẳng cùng nhóm ngành | 23.660.000 | |
| | | | | Học phí đợt 1 | 5.600.000 | Học phí thu theo 4 đợt |
| | | | | Học phí đợt 2 | 5.600.000 | |
| | | | | Học phí đợt 3 | 6.230.000 | |
| | | | | Học phí đợt 4 | 6.230.000 | |
| | | | 2,5 | Văn bằng đại học 2 | 30.550.000 | |
| | | | | Học phí đợt 1 | 5.600.000 | Học phí thu theo 5 đợt |
| | | | | Học phí đợt 2 | 5.600.000 | |
| | | | | Học phí đợt 3 | 6.230.000 | |
| | | | | Học phí đợt 4 | 6.230.000 | |
| | | | | Học phí đợt 5 | 6.890.000 | |"""

# Raw output Trang 2 (như user gặp phải)
p2_text = """| :---: | :--- | :--- | :--- | :--- | :--- |
| :---: | :--- | :--- | :--- | :--- | :--- |
|  | Kế toán | III | 3 | Tốt nghiệp trình độ cao đẳng khác ngành, trung cấp | 37.440.000 |
| | | | | Học phí đợt 1 | 5.600.000 |
| | | | | Học phí đợt 2 | 5.600.000 |
| | | | | Học phí đợt 3 | 6.230.000 |
| | | | | Học phí đợt 4 | 6.230.000 |
| | | | | Học phí đợt 5 | 6.890.000 |
| | | | | Học phí đợt 6 | 6.890.000 | Học phí thu theo 6 đợt |
| 2 | Ngôn Ngữ Anh | VII | 2,5 | Văn bằng đại học thứ 2 | 32.550.000 |
| | | | | Học phí đợt 1 | 5.900.000 |
| | | | | Học phí đợt 2 | 5.900.000 |
| | | | | Học phí đợt 3 | 6.700.000 |
| | | | | Học phí đợt 4 | 6.700.000 |
| | | | | Học phí đợt 5 | 7.350.000 | Học phí thu theo 5 đợt |

## II. Hiệu lực thi hành
Quy định này có hiệu lực kể từ ngày ký và áp dụng đối với hệ đào tạo từ xa tuyển sinh tháng 9 năm 2025 (Đợt 1)."""

def inherit_table_headers_for_continuation_pages(pages: list[dict]) -> list[dict]:
    """Ensure multi-page continuation tables inherit standard headers from preceding pages."""
    last_header: str | None = None
    last_separator: str | None = None
    last_col_count: int = 0

    out_pages = []
    for page in pages:
        p_copy = dict(page)
        p_text = p_copy.get("extracted_text", "")
        lines = p_text.splitlines()
        
        # Scan page for any full table with valid header
        found_header = None
        found_sep = None
        for i in range(len(lines) - 1):
            if _is_table_row(lines[i]) and not _is_table_separator(lines[i]):
                if _is_table_separator(lines[i + 1]):
                    cells = _split_table_cells(lines[i])
                    # Ensure it's not a false header
                    if len(cells) >= 3 and any(len(c) > 1 for c in cells):
                        found_header = lines[i]
                        found_sep = lines[i + 1]
                        break

        # Check if this page starts with a continuation table (missing header)
        first_table_idx = -1
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("<!--"):
                continue
            if _is_table_row(stripped):
                first_table_idx = idx
                break
            else:
                break  # Not starting with a table

        if first_table_idx != -1 and last_header and last_separator:
            # Check if this table has its own valid header
            has_own_header = False
            if first_table_idx + 1 < len(lines):
                if _is_table_separator(lines[first_table_idx + 1]) and not _is_table_separator(lines[first_table_idx]):
                    # Check if first row is actually a header (not data)
                    c0 = _split_table_cells(lines[first_table_idx])[0]
                    if not re.search(r"^\d+$", c0):
                        has_own_header = True

            if not has_own_header:
                # Remove any stray leading separator rows
                while first_table_idx < len(lines) and _is_table_separator(lines[first_table_idx]):
                    lines.pop(first_table_idx)

                # Pad rows to match last_col_count
                for r_idx in range(first_table_idx, len(lines)):
                    if not _is_table_row(lines[r_idx]):
                        break
                    row_cells = _split_table_cells(lines[r_idx])
                    if len(row_cells) < last_col_count:
                        while len(row_cells) < last_col_count:
                            row_cells.append("")
                        lines[r_idx] = "| " + " | ".join(row_cells) + " |"

                # Insert inherited header and separator
                lines.insert(first_table_idx, last_separator)
                lines.insert(first_table_idx, last_header)
                p_copy["extracted_text"] = "\n".join(lines)

        if found_header and found_sep:
            last_header = found_header
            last_separator = found_sep
            last_col_count = len(_split_table_cells(found_header))

        out_pages.append(p_copy)
    return out_pages

pages = [
    {"page_number": 1, "extracted_text": p1_text},
    {"page_number": 2, "extracted_text": p2_text},
]

res = inherit_table_headers_for_continuation_pages(pages)
print("=== PAGE 2 AFTER HEADER INHERITANCE ===")
print(res[1]["extracted_text"])
