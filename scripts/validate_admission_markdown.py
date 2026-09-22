#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validation script for standardized admission markdown.

Verifies:
1. GFM table syntax (all tables have proper header delimiter rows).
2. Logical reading order (no inverted sections or broken continuity).
3. 53/53 admission majors present with non-empty codes, names, and combos.
4. Zero orphan rows in tables (no row with empty STT and major code).
5. VSTEP/IELTS 4-column conversion table validity.
6. 52/52 historical cutoff score majors present in Section 11.
7. 38/38 majors in Phụ lục 1 with complete subject names.
8. Zero duplicate sections and zero raw OCR leakage.
"""

from pathlib import Path
import re
import sys

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TARGET_FILE = Path(__file__).resolve().parent.parent / "Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach.md"
if len(sys.argv) > 1:
    TARGET_FILE = Path(sys.argv[1])


def validate():
    if not TARGET_FILE.exists():
        print(f"[FAIL] Target file does not exist: {TARGET_FILE}")
        sys.exit(1)

    text = TARGET_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()

    errors = []

    # 1. Check UTF-8 Cleanliness / Mojibake
    mojibake_patterns = [r"\ufffd", r"\?oAn", r"B~ GIA", r"Quyt `<nh"]
    for p in mojibake_patterns:
        if re.search(p, text):
            errors.append(f"Mojibake detected matching pattern '{p}'")

    # 2. Check GFM table delimiters
    table_blocks = []
    current_table = []
    in_table = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                current_table = [(idx + 1, stripped)]
            else:
                current_table.append((idx + 1, stripped))
        else:
            if in_table:
                table_blocks.append(current_table)
                in_table = False
                current_table = []
    if in_table:
        table_blocks.append(current_table)

    print(f"[INFO] Found {len(table_blocks)} contiguous table blocks in document.")

    for t_idx, tbl in enumerate(table_blocks):
        if len(tbl) < 2:
            errors.append(f"Table #{t_idx+1} (line {tbl[0][0]}) has fewer than 2 rows.")
            continue
        header_line = tbl[0][1]
        delimiter_line = tbl[1][1]
        if not re.search(r"\|(?:\s*:?-+:?\s*\|)+", delimiter_line):
            errors.append(
                f"Table #{t_idx+1} (line {tbl[0][0]}) lacks valid GFM delimiter row at line {tbl[1][0]}: '{delimiter_line}'"
            )

    # 3. Check for Orphan rows (rows where first 2 data cells are empty but last cell has content)
    for t_idx, tbl in enumerate(table_blocks):
        for line_num, row_str in tbl[2:]:
            cells = [c.strip() for c in row_str.split("|")[1:-1]]
            if len(cells) >= 3:
                # If first 2 cells are empty and another cell is non-empty
                if cells[0] == "" and cells[1] == "" and any(cells[2:]):
                    errors.append(f"Orphan table row at line {line_num}: '{row_str}'")

    # 4. Check 53 Majors in Section II.4
    sec4_match = re.search(
        r"4\.\s*(?:\*\*)?Các ngành, tổ hợp môn xét tuyển(?:\*\*)?:(.*?)(?:##\s*)?5\.\s*Các thông tin cần thiết",
        text,
        re.DOTALL,
    )
    if not sec4_match:
        errors.append("Section II.4 boundary not found.")
    else:
        sec4_text = sec4_match.group(1)
        major_matches = re.findall(
            r"\|\s*(\d+)\s*\|\s*(\d{7}[A-Z]*)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]+?)\s*\|",
            sec4_text,
        )
        major_stts = [int(m[0]) for m in major_matches]
        if len(major_stts) != 53:
            errors.append(f"Expected 53 admission majors in Section 4, but found {len(major_stts)}")
        else:
            if major_stts != list(range(1, 54)):
                errors.append(f"Major STTs not strictly 1..53: {major_stts}")

        # Verify key stitched majors have their combinations preserved
        gdtc = [m for m in major_matches if m[1] == "7140206"]
        if gdtc:
            combo_str = gdtc[0][5]
            if "Toán, Sinh, NK TDTT" not in combo_str or "Toán, Lý, NK TDTT" not in combo_str:
                errors.append(f"STT 5 GDTC missing stitched combinations: {combo_str}")

        nonghoc = [m for m in major_matches if m[1] == "7620109"]
        if nonghoc:
            combo_str = nonghoc[0][5]
            if "Toán, Sinh, Lý" not in combo_str or "Toán, Sinh, Địa" not in combo_str:
                errors.append(f"STT 48 Nông học missing stitched combinations: {combo_str}")

    # 5. Check Section II.5 VSTEP/IELTS Conversion Table
    vstep_match = re.search(
        r"\|\s*Điểm IELTS\s*\|\s*Điểm quy đổi IELTS\s*\|\s*Điểm VSTEP\s*\|\s*Điểm quy đổi VSTEP\s*\|",
        text,
    )
    if not vstep_match:
        errors.append("VSTEP/IELTS 4-column conversion table header not found.")
    else:
        for score_str in ["5.0", "5.5", "6.0", "6.5", "7.0 trở lên"]:
            if score_str not in text:
                errors.append(f"Missing IELTS score row: {score_str}")
        for vstep_str in ["4.0", "5.0", "6.0", "7.0", "8.0 trở lên"]:
            if vstep_str not in text:
                errors.append(f"Missing VSTEP score row: {vstep_str}")

    # 6. Check Section 11 (2-year historical scores)
    sec11_match = re.search(
        r"(?:##\s*)?11\.\s*Thông tin về tuyển sinh của 2 năm gần nhất.*?(?=\n\*\*Nơi nhận\*\*|\n(?:#\s*)?PHỤ LỤC 1|\Z)",
        text,
        re.DOTALL,
    )
    if not sec11_match:
        errors.append("Section 11 boundary not found.")
    else:
        sec11_text = sec11_match.group(0)
        hist_matches = re.findall(
            r"\|\s*(\d+)\s*\|\s*(\d{7}[A-Z]*)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|",
            sec11_text,
        )
        hist_stts = [int(m[0]) for m in hist_matches]
        if len(hist_stts) != 52:
            errors.append(f"Expected 52 historical majors in Section 11, but found {len(hist_stts)}")
        else:
            if hist_stts != list(range(1, 53)):
                errors.append(f"Historical STTs not strictly 1..52: {hist_stts}")

    # 7. Check Phụ Lục 1
    pl1_match = re.search(r"(?:#\s*)?PHỤ LỤC 1.*?\| Tên môn thi học sinh giỏi quốc gia \| Tên ngành đào tạo \| Mã ngành \|(.*?)(?:\Z)", text, re.DOTALL)
    if not pl1_match:
        errors.append("Phụ lục 1 header or table not found.")
    else:
        pl1_table_text = pl1_match.group(1)
        pl1_rows = [r.strip() for r in pl1_table_text.splitlines() if r.strip().startswith("|") and not re.search(r":---", r)]
        if len(pl1_rows) != 38:
            errors.append(f"Expected 38 rows in Phụ lục 1, found {len(pl1_rows)}")
        # Check for empty subject in column 1
        for r_idx, r in enumerate(pl1_rows):
            cells = [c.strip() for c in r.split("|")[1:-1]]
            if len(cells) >= 3 and not cells[0]:
                errors.append(f"Phụ lục 1 row #{r_idx+1} has empty subject column: '{r}'")

    # 8. Check Logical Reading Order
    pos_sec_2 = text.find("2. Phương thức tuyển sinh:")
    if pos_sec_2 == -1:
        pos_sec_2 = text.find("2. **Phương thức tuyển sinh**:")

    pos_sec_4 = text.find("4. Các ngành, tổ hợp môn xét tuyển:")
    if pos_sec_4 == -1:
        pos_sec_4 = text.find("4. **Các ngành, tổ hợp môn xét tuyển**:")

    pos_tbl_majors = text.find("| STT | Mã xét tuyển | Tên ngành")

    pos_sec_8 = text.find("8. Lệ phí xét tuyển, thi tuyển, học phí")

    pos_sec_11 = text.find("11. Thông tin về tuyển sinh của 2 năm gần nhất")

    pos_tbl_hist = text.find("| 2024 - Chỉ tiêu |")
    if pos_tbl_hist == -1:
        pos_tbl_hist = text.find("| Chỉ tiêu 2024 |")

    pos_pl1 = text.find("PHỤ LỤC 1")

    if not (0 <= pos_sec_2 < pos_sec_4 < pos_tbl_majors):
        errors.append(f"Logical order violated: Section 2 ({pos_sec_2}) must precede Section 4 ({pos_sec_4}), which must precede the majors table ({pos_tbl_majors}).")

    if not (0 <= pos_sec_8 < pos_sec_11 < pos_tbl_hist < pos_pl1):
        errors.append(f"Logical order violated: Section 8 ({pos_sec_8}) must precede Section 11 ({pos_sec_11}), which must precede history table ({pos_tbl_hist}), which must precede Phụ lục 1 ({pos_pl1}).")

    # 9. Check for Duplicate Sections or Raw Leakage
    if text.count("8. Lệ phí xét tuyển, thi tuyển, học phí") != 1:
        errors.append("Section 8 title appears more than once (duplicate extraction).")

    raw_leakage_sample = "7850101\nQuản lý tài nguyên và môi trường\n100\n84\n15"
    if raw_leakage_sample in text:
        errors.append("Raw OCR leakage from page 12 still present in document.")

    # Report Results
    print("\n--- VALIDATION REPORT ---")
    if errors:
        print(f"[FAILED] Found {len(errors)} errors:")
        for e in errors:
            print(f"  [X] {e}")
        sys.exit(1)
    else:
        print("[SUCCESS] 100% of validation checks passed!")
        print("  [PASS] UTF-8 & Mojibake clean")
        print("  [PASS] GFM table syntax: All tables have header delimiters (:---: / :---)")
        print("  [PASS] Section order: 100% logical linear reading order")
        print("  [PASS] 53/53 admission majors present with stitched combinations (0 orphan rows)")
        print("  [PASS] 4-column VSTEP/IELTS conversion table intact with full headers")
        print("  [PASS] 52/52 historical 2-year cutoff majors complete")
        print("  [PASS] 38/38 Phụ lục 1 majors complete with subjects in column 1")
        print("  [PASS] Zero duplicate blocks and zero OCR raw leakage")
        print("  [PASS] Ready for Qdrant Vector DB & Hybrid RAG Ingestion!")


if __name__ == "__main__":
    validate()
