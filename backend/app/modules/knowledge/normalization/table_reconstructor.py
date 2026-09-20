"""Multi-Page Table Reconstructor — Schema Fingerprinting, Header Deduplication & Continuation Stitching.

Implements the P0.2 requirements of the QNU AI Platform Knowledge Normalization Plan:
- Fingerprints table headers via SHA-256 schema keys.
- Merges fragmented table pages with identical schemas into unified logical tables.
- Drops repeated headers and stray page-break markers.
- Rescues orphan continuation rows split across page boundaries.
- Replaces phantom placeholder columns with clean schema layouts.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata

from app.modules.knowledge.normalization.models import (
    CanonicalCell,
    CanonicalRow,
    CanonicalTable,
    SourceSpan,
)

logger = logging.getLogger(__name__)

_PHANTOM_HEADER_RE = re.compile(r"^Cột\s+\d+$", re.IGNORECASE)
_PROGRAM_CODE_RE = re.compile(r"^\d{7}$")
_TASK_CODE_RE = re.compile(r"^\d+\.\d+$")
_ROMAN_NUMERAL_RE = re.compile(r"^[IVXLCDM]+$")
_LEAD_UNIT_RE = re.compile(
    r"^(?:ban|cđ|đtn|hsv|khoa|phòng|trung tâm|trường|viện|văn phòng)\b",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"^\d{1,2}/\d{4}$")


def normalize_header(value: str) -> str:
    """Normalize a header title for robust schema fingerprinting."""
    if not value:
        return ""
    nfc = unicodedata.normalize("NFC", str(value))
    collapsed = re.sub(r"\s+", " ", nfc).strip(" :.-")
    return collapsed.casefold()


def _is_phantom_header(value: str) -> bool:
    """Return whether a header is empty or a parser-generated placeholder."""
    return not normalize_header(value) or bool(_PHANTOM_HEADER_RE.match(value.strip()))


def _has_semantic_headers(headers: list[str]) -> bool:
    """Determine whether a table has a genuine header row instead of data at its top."""
    meaningful_headers = [header for header in headers if not _is_phantom_header(header)]
    if len(meaningful_headers) < 2:
        return False

    semantic_terms = (
        "stt",
        "tt",
        "mã",
        "tên",
        "ngành",
        "nhiệm vụ",
        "đơn vị",
        "thời gian",
        "sản phẩm",
        "điểm",
        "chỉ tiêu",
        "tổ hợp",
    )
    return any(term in normalize_header(header) for header in meaningful_headers for term in semantic_terms)


def _header_looks_like_data(headers: list[str]) -> bool:
    """Identify page-continuation tables whose first extracted row was misread as headers."""
    values = [header.strip() for header in headers]
    non_empty_values = [value for value in values if value]
    if not non_empty_values:
        return True
    if not _has_semantic_headers(headers):
        return True
    return any(
        _PROGRAM_CODE_RE.fullmatch(value) or _TASK_CODE_RE.fullmatch(value)
        for value in values
    )


def _header_as_row(table: CanonicalTable) -> CanonicalRow:
    """Preserve a data-like extracted header as the first row of a continuation table."""
    page_number = min(table.source_pages) if table.source_pages else 1
    source_span = SourceSpan(page_number=page_number, bbox=table.bbox)
    return CanonicalRow(
        row_id=f"{table.table_id}_header_data",
        cells=[
            CanonicalCell(
                raw_value=value.strip(),
                normalized_value=value.strip() or None,
                source_span=source_span,
            )
            for value in table.headers
        ],
        source_pages=[page_number],
    )


def _as_text(cell: CanonicalCell | None) -> str:
    """Return a stripped cell value while tolerating missing padded cells."""
    return cell.raw_value.strip() if cell is not None else ""


def _cell_at(row: CanonicalRow, index: int) -> CanonicalCell | None:
    """Safely retrieve one cell from a possibly ragged extracted row."""
    return row.cells[index] if index < len(row.cells) else None


def _merge_second_header_row(
    headers: list[str], rows: list[CanonicalRow]
) -> tuple[list[str], list[CanonicalRow]]:
    """Merge a split two-level table header such as 2024 / Chỉ tiêu / Điểm."""
    if not headers or not rows or len(rows[0].cells) != len(headers):
        return headers, rows

    first_row = rows[0]
    first_values = [_as_text(cell) for cell in first_row.cells]
    first_three_are_empty = not any(first_values[: min(3, len(first_values))])
    has_subheaders = sum(1 for value in first_values if value) >= 2
    if not first_three_are_empty or not has_subheaders:
        return headers, rows

    merged_headers: list[str] = []
    active_group = ""
    for parent, child in zip(headers, first_values):
        parent_clean = re.sub(r"\s+", " ", parent).strip()
        child_clean = re.sub(r"\s+", " ", child).strip()
        if re.fullmatch(r"20\d{2}", parent_clean):
            active_group = parent_clean
        if child_clean:
            prefix = parent_clean or active_group
            merged_headers.append(f"{prefix} - {child_clean}" if prefix else child_clean)
        else:
            merged_headers.append(parent_clean)
    return merged_headers, rows[1:]


def _looks_like_implementation_table(headers: list[str]) -> bool:
    """Recognize the task-plan table layout that contains visual spacer columns."""
    normalized = " ".join(normalize_header(header) for header in headers)
    return "nhiệm vụ" in normalized and "đơn vị chủ trì" in normalized


def _clone_cell_with_value(source: CanonicalCell | None, value: str, page_number: int) -> CanonicalCell:
    """Keep provenance while producing a normalized cell value."""
    clean_value = re.sub(r"\s+", " ", value).strip()
    if source is not None:
        return source.model_copy(
            update={
                "raw_value": clean_value,
                "normalized_value": clean_value or None,
            }
        )
    return CanonicalCell(
        raw_value=clean_value,
        normalized_value=clean_value or None,
        source_span=SourceSpan(page_number=page_number),
    )


def _split_coordination_spillover(value: str) -> tuple[str, str]:
    """Separate a task-content continuation accidentally appended to a coordinating unit."""
    match = re.match(
        r"^(Các đơn vị liên quan)\s+([a-zà-ỹ].*)$",
        re.sub(r"\s+", " ", value).strip(),
        re.IGNORECASE,
    )
    if not match:
        return value, ""
    return match.group(1), match.group(2)


def _compact_task_row(row: CanonicalRow, target_count: int) -> CanonicalRow:
    """Repair mixed 7/9/11-column task rows into one seven-column semantic layout."""
    values = [_as_text(cell) for cell in row.cells]
    page_number = row.source_pages[0] if row.source_pages else 1
    code = values[0] if values else ""

    if not _TASK_CODE_RE.fullmatch(code):
        roman_index = next(
            (index for index, value in enumerate(values) if _ROMAN_NUMERAL_RE.fullmatch(value)),
            None,
        )
        if roman_index is None:
            return row
        category = next(
            (
                value
                for index, value in enumerate(values)
                if index != roman_index and value and not _ROMAN_NUMERAL_RE.fullmatch(value)
            ),
            "",
        )
        category_cells = [
            _clone_cell_with_value(_cell_at(row, roman_index), values[roman_index], page_number),
            _clone_cell_with_value(None, category, page_number),
        ]
        category_cells.extend(
            _clone_cell_with_value(None, "", page_number)
            for _ in range(max(0, target_count - len(category_cells)))
        )
        return row.model_copy(update={"cells": category_cells})

    lead_index = next(
        (index for index, value in enumerate(values[1:], start=1) if _LEAD_UNIT_RE.match(value)),
        None,
    )
    if lead_index is None:
        return row

    content_values = [value for value in values[1:lead_index] if value]
    content = " ".join(content_values)
    lead = values[lead_index]
    trailing_values = values[lead_index + 1 :]

    coordination = trailing_values[0] if trailing_values else ""
    coordination, content_spillover = _split_coordination_spillover(coordination)
    if content_spillover:
        content = f"{content} {content_spillover}".strip()

    start_date = next((value for value in trailing_values if _DATE_RE.fullmatch(value)), "")
    end_date = next(
        (
            value
            for value in trailing_values
            if _DATE_RE.fullmatch(value) and value != start_date
        ),
        "",
    )
    ignored_values = {coordination, start_date, end_date, ""}
    deliverables = " ".join(value for value in trailing_values if value not in ignored_values)

    semantic_values = [code, content, lead, coordination, start_date, end_date, deliverables]
    cells = [
        _clone_cell_with_value(_cell_at(row, index), value, page_number)
        for index, value in enumerate(semantic_values[:target_count])
    ]
    return row.model_copy(update={"cells": cells})


def _normalize_spacer_columns(
    headers: list[str], rows: list[CanonicalRow]
) -> tuple[list[str], list[CanonicalRow]]:
    """Remove visual spacer columns while preserving already compact rows."""
    semantic_indices = [
        index for index, header in enumerate(headers) if not _is_phantom_header(header)
    ]
    has_interspersed_spacers = (
        len(semantic_indices) >= 5 and len(semantic_indices) < len(headers)
    )
    if not has_interspersed_spacers:
        return headers, rows

    semantic_headers = [headers[index] for index in semantic_indices]
    normalized_rows: list[CanonicalRow] = []
    for row in rows:
        if len(row.cells) == len(semantic_headers):
            normalized_rows.append(row)
            continue
        if len(row.cells) >= len(headers):
            if _looks_like_implementation_table(headers) and not _as_text(_cell_at(row, 0)):
                normalized_rows.append(_compact_task_row(row, len(semantic_headers)))
                continue
            selected_cells = [_cell_at(row, index) for index in semantic_indices]
            if _looks_like_implementation_table(headers):
                unmapped_values = [
                    _as_text(_cell_at(row, index))
                    for index, header in enumerate(headers)
                    if _is_phantom_header(header) and _as_text(_cell_at(row, index))
                ]
                selected_cells = [cell for cell in selected_cells if cell is not None]
                normalized_row = row.model_copy(update={"cells": selected_cells})
                if unmapped_values and len(normalized_row.cells) > 1:
                    extra_text = " ".join(unmapped_values)
                    current_content = normalized_row.cells[1].raw_value
                    normalized_row.cells[1] = _clone_cell_with_value(
                        normalized_row.cells[1],
                        f"{current_content} {extra_text}",
                        row.source_pages[0] if row.source_pages else 1,
                    )
                normalized_rows.append(normalized_row)
            else:
                normalized_rows.append(
                    row.model_copy(update={"cells": [cell for cell in selected_cells if cell is not None]})
                )
            continue
        if _looks_like_implementation_table(headers):
            normalized_rows.append(_compact_task_row(row, len(semantic_headers)))
            continue
        normalized_rows.append(row)
    return semantic_headers, normalized_rows


def table_schema_key(headers: list[str]) -> str:
    """Compute a deterministic SHA-256 fingerprint for a list of table headers."""
    canonical = "|".join(normalize_header(h) for h in headers if normalize_header(h))
    if not canonical:
        return "empty_schema"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def is_repeated_header(row_cells: list[CanonicalCell], expected_headers: list[str]) -> bool:
    """Check if a table row is simply a repeated column header on a new page."""
    if not row_cells or not expected_headers:
        return False
    row_texts = [normalize_header(c.raw_value) for c in row_cells]
    exp_texts = [normalize_header(h) for h in expected_headers]

    # If length significantly mismatches, not a repeated header
    if abs(len(row_texts) - len(exp_texts)) > 1:
        return False

    matches = sum(
        1 for r, e in zip(row_texts, exp_texts)
        if r and e and (r in e or e in r or r == e)
    )
    # If 70% or more non-empty columns match, it is a repeated header
    non_empty_expected = max(1, sum(1 for e in exp_texts if e))
    return (matches / non_empty_expected) >= 0.70


def is_orphan_continuation_row(row: CanonicalRow, key_col_idx: int = 0) -> bool:
    """Detect if a row on top of a new page is an orphan continuation of the previous row.

    Typically lacks a primary business key (e.g. empty STT or code) but contains trailing text
    in the descriptive/content columns.
    """
    if not row.cells:
        return False
    if key_col_idx < len(row.cells):
        key_val = row.cells[key_col_idx].raw_value.strip()
        # If key column is empty and at least one other cell has meaningful text
        has_other_text = any(
            c.raw_value.strip() for i, c in enumerate(row.cells) if i != key_col_idx
        )
        return (not key_val) and has_other_text
    return False


def merge_continuation(previous: CanonicalRow, current: CanonicalRow) -> CanonicalRow:
    """Merge an orphan continuation row into the previous logical row."""
    merged_cells: list[CanonicalCell] = []
    max_len = max(len(previous.cells), len(current.cells))

    for i in range(max_len):
        old_cell = previous.cells[i] if i < len(previous.cells) else None
        new_cell = current.cells[i] if i < len(current.cells) else None

        if old_cell is None and new_cell is not None:
            merged_cells.append(new_cell)
        elif old_cell is not None and new_cell is None:
            merged_cells.append(old_cell)
        elif old_cell is not None and new_cell is not None:
            old_raw = old_cell.raw_value.strip()
            new_raw = new_cell.raw_value.strip()
            if not new_raw:
                merged_cells.append(old_cell)
            elif not old_raw:
                merged_cells.append(new_cell)
            else:
                combined_raw = f"{old_raw} {new_raw}"
                combined_norm = f"{old_cell.normalized_value or old_raw} {new_cell.normalized_value or new_raw}".strip()
                merged_cells.append(
                    old_cell.model_copy(
                        update={
                            "raw_value": combined_raw,
                            "normalized_value": combined_norm,
                            "confidence": min(old_cell.confidence, new_cell.confidence),
                        }
                    )
                )

    all_pages = sorted(set(previous.source_pages + current.source_pages))
    return previous.model_copy(
        update={
            "cells": merged_cells,
            "source_pages": all_pages,
            "is_continuation": True,
        }
    )


def clean_table_columns(headers: list[str], rows: list[CanonicalRow]) -> tuple[list[str], list[CanonicalRow]]:
    """Remove phantom placeholder columns (e.g. 'Cột 2' with >85% empty cells) and trim padding."""
    if not headers or not rows:
        return headers, rows

    headers, rows = _merge_second_header_row(headers, rows)
    headers, rows = _normalize_spacer_columns(headers, rows)

    col_count = len(headers)
    # Check emptiness of each column across all rows
    empty_ratios: list[float] = []
    for c_idx in range(col_count):
        empty_cells = sum(
            1 for r in rows
            if c_idx >= len(r.cells) or not r.cells[c_idx].raw_value.strip()
        )
        empty_ratios.append(empty_cells / max(1, len(rows)))

    # Determine which columns to keep:
    # Keep column if:
    # 1. Header is meaningful (not blank or matching /^Cột \d+$/i) OR
    # 2. Emptiness ratio is < 0.85 (contains substantial data)
    keep_indices: list[int] = []
    for c_idx, h in enumerate(headers):
        if _is_phantom_header(h) and empty_ratios[c_idx] >= 0.85:
            continue  # Drop phantom column
        keep_indices.append(c_idx)

    if not keep_indices or len(keep_indices) == col_count:
        return headers, rows

    clean_headers = [headers[i] for i in keep_indices]
    clean_rows: list[CanonicalRow] = []
    for r in rows:
        filtered_cells = [r.cells[i] for i in keep_indices if i < len(r.cells)]
        clean_rows.append(r.model_copy(update={"cells": filtered_cells}))

    return clean_headers, clean_rows


def _row_business_key(row: CanonicalRow) -> str | None:
    """Return a stable business key for rows that can safely be de-duplicated."""
    values = [_as_text(cell) for cell in row.cells]
    if not values:
        return None
    if _TASK_CODE_RE.fullmatch(values[0]):
        return f"task:{values[0]}"
    if len(values) > 1 and _PROGRAM_CODE_RE.fullmatch(values[1]):
        return f"program:{values[1]}"
    return None


def _deduplicate_exact_business_rows(rows: list[CanonicalRow]) -> list[CanonicalRow]:
    """Drop exact repeated business rows without hiding conflicting values."""
    seen: dict[str, str] = {}
    unique_rows: list[CanonicalRow] = []
    for row in rows:
        business_key = _row_business_key(row)
        row_signature = "\u241f".join(normalize_header(_as_text(cell)) for cell in row.cells)
        if business_key and seen.get(business_key) == row_signature:
            continue
        if business_key:
            seen[business_key] = row_signature
        unique_rows.append(row)
    return unique_rows


def _finalize_table(table: CanonicalTable) -> CanonicalTable:
    """Apply structural cleanup once a logical table has been fully reconstructed."""
    clean_headers, clean_rows = clean_table_columns(table.headers, table.rows)
    clean_rows = _deduplicate_exact_business_rows(clean_rows)
    return table.model_copy(
        update={
            "headers": clean_headers,
            "rows": clean_rows,
            "schema_key": table_schema_key(clean_headers),
        }
    )


def reconstruct_multi_page_tables(raw_tables: list[CanonicalTable]) -> list[CanonicalTable]:
    """Stitch contiguous tables, including pages whose data row is misread as a header."""
    if not raw_tables:
        return []

    reconstructed: list[CanonicalTable] = []
    current_master: CanonicalTable | None = None

    for tbl in raw_tables:
        if current_master is None:
            current_master = tbl.model_copy(deep=True)
            continue

        prev_max_page = max(current_master.source_pages) if current_master.source_pages else 1
        curr_min_page = min(tbl.source_pages) if tbl.source_pages else prev_max_page + 1

        # A PDF continuation page frequently has no repeated header. PyMuPDF then
        # promotes its first data row (or an orphan cell continuation) into headers.
        schema_matches = (tbl.schema_key == current_master.schema_key)
        page_adjacent = (curr_min_page - prev_max_page <= 1)
        data_header_continuation = (
            page_adjacent
            and len(tbl.headers) == len(current_master.headers)
            and _has_semantic_headers(current_master.headers)
            and _header_looks_like_data(tbl.headers)
        )

        if page_adjacent and (schema_matches or data_header_continuation):
            # Table is a continuation!
            candidate_rows = tbl.rows
            if data_header_continuation:
                candidate_rows = [_header_as_row(tbl), *tbl.rows]

            new_rows: list[CanonicalRow] = []
            for row in candidate_rows:
                # 1. Drop repeated column headers at the start of new page
                if is_repeated_header(row.cells, current_master.headers):
                    continue

                # 2. Check if the first row of new page is an orphan continuation
                if not new_rows and current_master.rows and is_orphan_continuation_row(row):
                    # Merge with the last row of the master table
                    last_row = current_master.rows[-1]
                    current_master.rows[-1] = merge_continuation(last_row, row)
                    continue

                new_rows.append(row)

            current_master.rows.extend(new_rows)
            current_master.source_pages = sorted(set(current_master.source_pages + tbl.source_pages))
        else:
            # Different table: clean up current master and push to list
            reconstructed.append(_finalize_table(current_master))
            current_master = tbl.model_copy(deep=True)

    if current_master is not None:
        reconstructed.append(_finalize_table(current_master))

    return reconstructed
