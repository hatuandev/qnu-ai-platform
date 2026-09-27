"""Excel and Tabular Data Parser for Structured Knowledge Facts Ingestion.

Implements Algorithmic-First, Zero-Keyword Morphological Table Processing:
- Unmerge & Hierarchical Forward-Fill (resolves RowSpan & ColSpan cell voids).
- Table Boundary & Multi-Tier Header Detection (filters top banners and stitches 2-tier headers).
- Zero-Keyword Entity Column Profiling (selects primary entity by uniqueness & data structure).
- Footer Noise Filtering (removes totals, footnotes, and signature blocks).
"""

from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
from typing import Any

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)

_FOOTER_PATTERNS: tuple[str, ...] = (
    "tổng cộng",
    "tổng số",
    "cộng:",
    "total",
    "ghi chú",
    "* ghi chú",
    "* lưu ý",
    "lưu ý:",
    "người lập biểu",
    "người lập",
    "trưởng phòng",
    "hiệu trưởng",
    "thủ trưởng",
    "ngày ... tháng",
    "ngày ...",
)


def _normalize_attr_key(header: str) -> str:
    """Normalize a Vietnamese or English column header to snake_case attribute name."""
    s = unicodedata.normalize("NFC", header.strip()).casefold()
    # Replace common Vietnamese diacritics
    replacements = {
        "đ": "d",
        "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a",
        "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
        "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
        "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o",
        "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
        "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u",
        "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    }
    for char, rep in replacements.items():
        s = s.replace(char, rep)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "attr"


def unmerge_and_forward_fill(sheet: Worksheet) -> list[list[Any]]:
    """Convert openpyxl worksheet into a 2D matrix with unmerged & forward-filled values.

    Resolves merged cell voids so every subordinate row inherits its parent
    group/entity data.
    """
    max_r = sheet.max_row or 0
    max_c = sheet.max_column or 0
    if max_r == 0 or max_c == 0:
        return []

    matrix: list[list[Any]] = [
        [sheet.cell(row=r, column=c).value for c in range(1, max_c + 1)]
        for r in range(1, max_r + 1)
    ]

    # Process all merged cell ranges
    for rng in list(sheet.merged_cells.ranges):
        min_col, min_row, max_col, max_row = rng.min_col, rng.min_row, rng.max_col, rng.max_row
        top_left_val = matrix[min_row - 1][min_col - 1]
        if top_left_val is None:
            continue

        # Forward-fill value across entire merged rectangular region
        for r_idx in range(min_row - 1, max_row):
            for c_idx in range(min_col - 1, max_col):
                matrix[r_idx][c_idx] = top_left_val

    return matrix


def detect_table_boundary_and_header(
    matrix: list[list[Any]],
) -> tuple[int, list[str], int]:
    """Detect table header row and data boundary, filtering out banners and stitching 2-tier headers.

    Returns:
        (header_idx, headers, data_start_idx)
    """
    if not matrix or len(matrix) < 2:
        return -1, [], -1

    effective_cols = max(
        sum(1 for c in r if c is not None and str(c).strip()) for r in matrix
    )
    if effective_cols == 0:
        return -1, [], -1

    for idx, row in enumerate(matrix):
        non_empty = [c for c in row if c is not None and str(c).strip()]
        if len(non_empty) < 2:
            continue

        # Filter out sparse banners/metadata at the top (e.g. agency names spanning <= 35% table width)
        if effective_cols >= 3 and (len(non_empty) / effective_cols) <= 0.35:
            continue

        # Check that header contains mostly text (not numeric data)
        non_numeric = sum(
            1 for c in non_empty if not str(c).strip().replace(".", "", 1).isdigit()
        )
        if non_numeric / len(non_empty) < 0.6:
            continue

        # Candidate header row found
        # Check if the immediate next row is a multi-tier sub-header
        is_multi_tier = False
        if idx + 2 < len(matrix):
            next_row = matrix[idx + 1]
            next_non_empty = [c for c in next_row if c is not None and str(c).strip()]
            data_row = matrix[idx + 2]
            data_has_num = any(
                str(c).strip().replace(".", "", 1).isdigit()
                for c in data_row
                if c is not None and str(c).strip()
            )
            next_all_str = all(
                not str(c).strip().replace(".", "", 1).isdigit()
                for c in next_non_empty
            )
            next_short = all(len(str(c).strip()) <= 45 for c in next_non_empty)
            if len(next_non_empty) >= 2 and next_all_str and next_short and data_has_num:
                is_multi_tier = True

        if is_multi_tier:
            next_row = matrix[idx + 1]
            headers: list[str] = []
            for c in range(len(row)):
                h_top = str(row[c]).strip() if row[c] is not None and str(row[c]).strip() else ""
                h_sub = (
                    str(next_row[c]).strip()
                    if c < len(next_row) and next_row[c] is not None and str(next_row[c]).strip()
                    else ""
                )
                if h_top and h_sub and h_top != h_sub:
                    h = f"{h_top} - {h_sub}"
                else:
                    h = h_sub or h_top or f"col_{c}"
                headers.append(unicodedata.normalize("NFC", h))
            return idx, headers, idx + 2

        headers = [
            unicodedata.normalize("NFC", str(c).strip()) if c is not None and str(c).strip() else f"col_{i}"
            for i, c in enumerate(row)
        ]
        return idx, headers, idx + 1

    return -1, [], -1


def detect_entity_column_zero_keyword(
    headers: list[str],
    data_rows: list[list[Any]],
) -> int:
    """Select the primary entity column using structural invariants (zero-keyword).

    Evaluates candidate columns by:
    1. Excluding sequence/index columns (STT, incrementing integers).
    2. Excluding mostly numeric/code columns.
    3. Maximizing uniqueness ratio and text length among descriptive name columns.
    """
    if not headers or not data_rows:
        return 0

    num_cols = len(headers)
    stt_cols: set[int] = set()

    for col_idx in range(num_cols):
        h_clean = headers[col_idx].strip().casefold()
        if h_clean in ("stt", "tt", "no", "no.", "index", "id"):
            stt_cols.add(col_idx)
            continue
        vals = [
            r[col_idx]
            for r in data_rows
            if col_idx < len(r) and r[col_idx] is not None and str(r[col_idx]).strip()
        ]
        if vals and all(str(v).strip().isdigit() for v in vals):
            int_vals = [int(str(v).strip()) for v in vals]
            if len(int_vals) >= 2 and all(int_vals[i] == int_vals[0] + i for i in range(len(int_vals))):
                stt_cols.add(col_idx)

    candidate_cols = [c for c in range(min(5, num_cols)) if c not in stt_cols]
    if not candidate_cols:
        candidate_cols = [c for c in range(num_cols) if c not in stt_cols]
    if not candidate_cols:
        return 0

    best_col: int | None = None
    best_score = -1.0

    for col_idx in candidate_cols:
        vals = [
            str(r[col_idx]).strip()
            for r in data_rows
            if col_idx < len(r) and r[col_idx] is not None and str(r[col_idx]).strip()
        ]
        if not vals:
            continue

        numeric_count = sum(1 for v in vals if re.match(r"^[-+]?\d+(\.\d+)?$", v))
        if numeric_count / len(vals) > 0.5:
            continue

        uniqueness = len(set(vals)) / len(vals)
        avg_len = sum(len(v) for v in vals) / len(vals)
        has_spaces = sum(1 for v in vals if " " in v) / len(vals)

        pos_weight = 1.0 - (col_idx * 0.05)
        score = uniqueness * pos_weight

        if 4 <= avg_len <= 80:
            score += 0.5
        if has_spaces > 0.4:
            score += 0.8

        if score > best_score:
            best_score = score
            best_col = col_idx

    return best_col if best_col is not None else candidate_cols[0]


def filter_footer_noise(rows: list[list[Any]]) -> list[list[Any]]:
    """Remove summary, footnote, and signature blocks from the tail of data rows."""
    clean_rows: list[list[Any]] = []
    for r in rows:
        if not r or not any(c is not None and str(c).strip() for c in r):
            continue
        first_non_empty = next(
            (str(c).strip().casefold() for c in r if c is not None and str(c).strip()),
            "",
        )
        if any(first_non_empty.startswith(pat) for pat in _FOOTER_PATTERNS):
            continue
        if re.search(r"ngày\s+\d+\s+tháng\s+\d+\s+năm", first_non_empty):
            continue
        clean_rows.append(r)
    return clean_rows


def infer_entity_type(sheet_name: str, entity_name: str, headers: list[str]) -> str:
    """Infer semantic entity type dynamically from sheet name, entity name, and headers."""
    combined = f"{sheet_name} {entity_name} {' '.join(headers)}".casefold()
    unaccented = _normalize_attr_key(combined)

    if (
        any(k in combined for k in ["tuyển sinh", "điểm chuẩn", "chỉ tiêu", "ngành"])
        or any(k in unaccented for k in ["tuyen_sinh", "diem_chuan", "chi_tieu", "nganh"])
        or any(k in combined for k in ["sư phạm", "công nghệ", "kỹ thuật", "ngôn ngữ", "kinh tế"])
    ):
        return "major"
    if (
        any(k in combined for k in ["học phí", "học bổng", "lệ phí", "miễn giảm"])
        or any(k in unaccented for k in ["hoc_phi", "hoc_bong", "le_phi"])
    ):
        return "tuition"
    if (
        any(k in combined for k in ["thiết bị", "vật tư", "phòng thí nghiệm", "máy móc"])
        or any(k in unaccented for k in ["thiet_bi", "thietbi", "vat_tu", "may_moc"])
    ):
        return "equipment"
    if (
        any(k in combined for k in ["môn học", "học phần", "tín chỉ"])
        or any(k in unaccented for k in ["mon_hoc", "hoc_phan", "tin_chi"])
    ):
        return "course"

    return "academic_fact"


def parse_excel_facts(
    file_bytes: bytes,
    filename: str,
) -> list[dict[str, Any]]:
    """Extract structured facts from Excel (.xlsx, .xls) or CSV bytes using zero-keyword pipeline."""
    facts: list[dict[str, Any]] = []

    if filename.endswith(".csv"):
        return _parse_csv_facts(file_bytes)

    # Read with openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        # 1. Unmerge and forward fill merged ranges
        matrix = unmerge_and_forward_fill(sheet)
        if not matrix or len(matrix) < 2:
            continue

        # 2. Detect table boundary and multi-tier headers
        _, headers, data_start_idx = detect_table_boundary_and_header(matrix)
        if not headers or data_start_idx == -1:
            continue

        # 3. Filter footer noise
        raw_data_rows = matrix[data_start_idx:]
        data_rows = filter_footer_noise(raw_data_rows)
        if not data_rows:
            continue

        # 4. Detect primary entity column (Zero-Keyword)
        entity_col_idx = detect_entity_column_zero_keyword(headers, data_rows)

        # 5. Extract facts
        for row in data_rows:
            entity_val = row[entity_col_idx] if entity_col_idx < len(row) else None
            if entity_val is None or not str(entity_val).strip():
                continue

            entity_name = unicodedata.normalize("NFC", str(entity_val).strip())
            entity_type = infer_entity_type(sheet_name, entity_name, headers)

            row_dict: dict[str, Any] = {}
            for col_idx, h in enumerate(headers):
                if col_idx < len(row) and row[col_idx] is not None:
                    row_dict[h] = unicodedata.normalize("NFC", str(row[col_idx]).strip())

            for col_idx, h in enumerate(headers):
                if col_idx == entity_col_idx:
                    continue
                val = row[col_idx] if col_idx < len(row) else None
                if val is None or not str(val).strip():
                    continue

                attr_name = _normalize_attr_key(h)
                attr_val = unicodedata.normalize("NFC", str(val).strip())

                facts.append(
                    {
                        "entity_name": entity_name,
                        "entity_type": entity_type,
                        "attribute_name": attr_name,
                        "attribute_value": attr_val,
                        "confidence": 1.0,
                        "raw_data": row_dict,
                    }
                )

    wb.close()
    return facts


def _parse_csv_facts(file_bytes: bytes) -> list[dict[str, Any]]:
    """Parse CSV tabular data applying the same zero-keyword boundary & entity profiling pipeline."""
    facts: list[dict[str, Any]] = []
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    matrix: list[list[Any]] = [
        [c for c in row] for row in reader if any(c.strip() for c in row)
    ]
    if not matrix or len(matrix) < 2:
        return facts

    _, headers, data_start_idx = detect_table_boundary_and_header(matrix)
    if not headers or data_start_idx == -1:
        return facts

    raw_data_rows = matrix[data_start_idx:]
    data_rows = filter_footer_noise(raw_data_rows)
    if not data_rows:
        return facts

    entity_col_idx = detect_entity_column_zero_keyword(headers, data_rows)

    for row in data_rows:
        if not row or len(row) <= entity_col_idx or not str(row[entity_col_idx]).strip():
            continue
        entity_name = unicodedata.normalize("NFC", str(row[entity_col_idx]).strip())
        entity_type = infer_entity_type("csv_data", entity_name, headers)
        row_dict = {
            headers[i]: unicodedata.normalize("NFC", str(row[i]).strip())
            for i in range(min(len(headers), len(row)))
            if row[i] is not None
        }

        for col_idx, h in enumerate(headers):
            if col_idx == entity_col_idx or col_idx >= len(row):
                continue
            val = row[col_idx]
            if val is None or not str(val).strip():
                continue
            facts.append(
                {
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "attribute_name": _normalize_attr_key(h),
                    "attribute_value": unicodedata.normalize("NFC", str(val).strip()),
                    "confidence": 1.0,
                    "raw_data": row_dict,
                }
            )

    return facts
