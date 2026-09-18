"""Excel and Tabular Data Parser for Structured Knowledge Facts Ingestion."""

from __future__ import annotations

import csv
import io
import logging
import re
from typing import Any

import openpyxl

logger = logging.getLogger(__name__)


def _normalize_attr_key(header: str) -> str:
    """Normalize a Vietnamese or English column header to snake_case attribute name."""
    s = header.strip().casefold()
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
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "attr"


def parse_excel_facts(
    file_bytes: bytes,
    filename: str,
) -> list[dict[str, Any]]:
    """Extract structured facts from Excel (.xlsx) or CSV bytes."""
    facts: list[dict[str, Any]] = []

    if filename.endswith(".csv"):
        return _parse_csv_facts(file_bytes)

    # Read with openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        rows = list(sheet.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            continue

        # Find header row (first row with at least 2 non-empty string cells)
        header_idx = -1
        headers: list[str] = []
        for idx, row in enumerate(rows):
            non_empty = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if len(non_empty) >= 2:
                header_idx = idx
                headers = [str(c).strip() if c is not None else f"col_{i}" for i, c in enumerate(row)]
                break

        if header_idx == -1 or not headers:
            continue

        # Identify entity column (usually "Tên ngành", "Ngành", "Khoản mục", "Nội dung", or column 0/1)
        entity_col_idx = 0
        for i, h in enumerate(headers):
            h_lower = h.casefold()
            if any(k in h_lower for k in ["tên ngành", "ngành đào tạo", "chuyên ngành", "khoản mục", "nội dung"]):
                entity_col_idx = i
                break

        # Process data rows
        for row in rows[header_idx + 1 :]:
            if not row:
                continue
            entity_val = row[entity_col_idx] if entity_col_idx < len(row) else None
            if entity_val is None or not str(entity_val).strip():
                continue

            entity_name = str(entity_val).strip()

            # Infer entity type
            lower_sheet = sheet_name.casefold()
            lower_entity = entity_name.casefold()
            if any(k in lower_sheet for k in ["tuyển sinh", "điểm chuẩn", "chỉ tiêu"]) or any(k in lower_entity for k in ["sư phạm", "công nghệ", "kỹ thuật", "ngôn ngữ", "kinh tế"]):
                entity_type = "major"
            elif any(k in lower_sheet for k in ["học phí", "học bổng", "lệ phí"]):
                entity_type = "tuition"
            else:
                entity_type = "academic_fact"

            row_dict: dict[str, Any] = {}
            for col_idx, h in enumerate(headers):
                if col_idx < len(row) and row[col_idx] is not None:
                    row_dict[h] = str(row[col_idx]).strip()

            # Create individual attribute facts
            for col_idx, h in enumerate(headers):
                if col_idx == entity_col_idx:
                    continue
                val = row[col_idx] if col_idx < len(row) else None
                if val is None or not str(val).strip():
                    continue

                attr_name = _normalize_attr_key(h)
                attr_val = str(val).strip()

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

    return facts


def _parse_csv_facts(file_bytes: bytes) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows or len(rows) < 2:
        return facts

    headers = [h.strip() for h in rows[0]]
    entity_col_idx = 0
    for i, h in enumerate(headers):
        if any(k in h.casefold() for k in ["ngành", "tên", "khoản"]):
            entity_col_idx = i
            break

    for row in rows[1:]:
        if not row or len(row) <= entity_col_idx or not row[entity_col_idx].strip():
            continue
        entity_name = row[entity_col_idx].strip()
        row_dict = {headers[i]: row[i].strip() for i in range(min(len(headers), len(row)))}

        for col_idx, h in enumerate(headers):
            if col_idx == entity_col_idx or col_idx >= len(row) or not row[col_idx].strip():
                continue
            facts.append(
                {
                    "entity_name": entity_name,
                    "entity_type": "academic_fact",
                    "attribute_name": _normalize_attr_key(h),
                    "attribute_value": row[col_idx].strip(),
                    "confidence": 1.0,
                    "raw_data": row_dict,
                }
            )

    return facts
