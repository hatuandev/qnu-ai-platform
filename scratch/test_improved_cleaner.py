import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import re

from app.modules.ocr.cleaner import _split_table_cells, _is_table_separator, _is_table_row, _RE_PAGE_MARKER

sample_table = """| STT | Tên ngành | Khối ngành | Thời gian học (năm) | Hình thức đào tạo | Học phí toàn khóa | Ghi chú |
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

def improved_merge_ocr_orphan_table_rows(markdown: str) -> str:
    lines = markdown.splitlines()
    out_lines: list[str] = []
    i = 0
    n = len(lines)

    in_table = False
    last_parent_idx = -1

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if _is_table_separator(stripped):
            in_table = True
            out_lines.append(line)
            i += 1
            last_parent_idx = -1
            continue

        if in_table and _RE_PAGE_MARKER.match(stripped):
            out_lines.append(line)
            i += 1
            continue

        if not _is_table_row(stripped):
            in_table = False
            last_parent_idx = -1
            out_lines.append(line)
            i += 1
            continue

        if not in_table:
            out_lines.append(line)
            i += 1
            continue

        cells = _split_table_cells(stripped)
        col0 = cells[0].strip() if len(cells) > 0 else ""

        # Check if the row contains numerical data, monetary amounts, or distinct entities
        has_currency_or_number = any(re.search(r"\b\d{1,3}(?:\.\d{3})+\b", c) for c in cells[1:])
        has_installment = any(re.search(r"\b(?:đợt\s+\d+|văn\s+bằng|tốt\s+nghiệp|khóa|năm)\b", c, re.IGNORECASE) for c in cells[1:])
        
        # An orphan continuation row is ONLY a text wrapping artifact where no independent numerical/data record exists
        is_orphan = (not col0) and any(bool(c.strip()) for c in cells[1:]) and (last_parent_idx != -1) and not (has_currency_or_number or has_installment)

        if is_orphan:
            parent_line = out_lines[last_parent_idx]
            parent_cells = _split_table_cells(parent_line)
            max_c = max(len(parent_cells), len(cells))
            while len(parent_cells) < max_c:
                parent_cells.append("")
            while len(cells) < max_c:
                cells.append("")

            for k in range(1, max_c):
                child_val = cells[k].strip()
                if child_val:
                    parent_val = parent_cells[k].strip()
                    if not parent_val:
                        parent_cells[k] = child_val
                    else:
                        if child_val and child_val[0].islower():
                            parent_cells[k] = f"{parent_val} {child_val}"
                        else:
                            parent_cells[k] = f"{parent_val} {child_val}"  # Keep clean text without <br>

            out_lines[last_parent_idx] = "| " + " | ".join(parent_cells) + " |"
            i += 1
            continue

        # Normal row (keep all distinct data rows intact)
        out_lines.append(line)
        last_parent_idx = len(out_lines) - 1
        i += 1

    return "\n".join(out_lines)

print("=== IMPROVED merge_ocr_orphan_table_rows ===")
print(improved_merge_ocr_orphan_table_rows(sample_table))
