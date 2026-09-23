"""Dedicated Post-Processing & Normalization Pipeline for Document OCR Extraction.

Specialized in:
1. Multi-page Table Stitching across page dividers (--- / <!-- Trang X -->).
2. Merging orphan continuation rows into single semantic parent records (<br>).
3. Repairing Vietnamese compound words split across page boundaries.
4. Correcting common OCR typo artifacts without touching DOCX or PDF Text pipelines.
"""

from __future__ import annotations

import re
from typing import Any

_RE_SEPARATOR_ROW = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
_RE_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_RE_PAGE_MARKER = re.compile(r"<!--\s*Trang\s*(\d+)\s*-->", re.IGNORECASE)
_RE_DIVIDER = re.compile(r"^\s*---+\s*$")


def _split_table_cells(row: str) -> list[str]:
    """Split a markdown table row into trimmed cell contents."""
    trimmed = row.strip().removeprefix("|").removesuffix("|")
    return [c.strip() for c in trimmed.split("|")]


def _is_table_separator(row: str) -> bool:
    """Check if row is a markdown table separator like |:---|:---|."""
    return bool(_RE_SEPARATOR_ROW.match(row.strip()))


def _is_table_row(row: str) -> bool:
    """Check if row is a valid markdown table line."""
    return bool(_RE_TABLE_ROW.match(row.strip()))


def repair_ocr_split_words_across_pages(markdown: str) -> str:
    """Repair words or continuous clauses split across page boundaries using morphological heuristics.

    Zero-Keyword & Algorithmic-First Approach:
    Identifies continuation based on syntactic boundary invariants:
    1. Hyphenated word break (e.g., 'tiến-' + 'hành' -> 'tiến hành').
    2. Boundary continuation:
       - Scans across page boundary delimiters ('---' or '<!-- Trang X -->').
       - Analyzes row structure:
         * In markdown tables: When an orphan row begins with an empty identifier column and
           its first content cell starts with a lowercase letter, the first token is bridged
           back into the preceding parent cell.
         * In plain text: When a line before boundary does not end with terminal punctuation
           and the next line starts with a lowercase letter, the continuation is merged.
    """
    if not markdown or not markdown.strip():
        return markdown

    # Step 1: Repair hyphenated word breaks across page breaks
    re_hyphen = re.compile(
        r"(\b[\w]+)-\s*\n+(?:---\s*\n+)?(?:<!--\s*Trang\s*\d+\s*-->\s*\n+)?\s*([\w]+\b)",
        re.IGNORECASE,
    )
    text = re_hyphen.sub(r"\1 \2", markdown)

    # Step 2: Algorithmic line & table row boundary stitcher
    lines = text.splitlines()
    n = len(lines)
    i = 0

    while i < n:
        line_i = lines[i]
        stripped_i = line_i.strip()

        # Only evaluate lines that have meaningful content
        if not stripped_i or _RE_DIVIDER.match(stripped_i) or _RE_PAGE_MARKER.match(stripped_i):
            i += 1
            continue

        # Look ahead across page delimiters
        j = i + 1
        has_page_boundary = False
        while j < n:
            stripped_j = lines[j].strip()
            if not stripped_j:
                j += 1
                continue
            if _RE_DIVIDER.match(stripped_j) or _RE_PAGE_MARKER.match(stripped_j):
                has_page_boundary = True
                j += 1
                continue
            break

        if has_page_boundary and j < n:
            prev_line = lines[i]
            next_line = lines[j]

            # Case A: Table rows across page break
            if _is_table_row(prev_line) and _is_table_row(next_line):
                prev_cells = _split_table_cells(prev_line)
                next_cells = _split_table_cells(next_line)

                # Find the first column with content in next_cells
                target_col = -1
                for col_idx, cell in enumerate(next_cells):
                    if cell.strip():
                        target_col = col_idx
                        break

                # If Column 0 (e.g. STT/ID) is empty and target_col starts with a lowercase letter
                if target_col > 0 and target_col < len(prev_cells):
                    next_val = next_cells[target_col].strip()
                    prev_val = prev_cells[target_col].strip()

                    if next_val and next_val[0].islower() and (not prev_val or prev_val[-1] not in ".!?:"):
                        parts = next_val.split(maxsplit=1)
                        first_token = parts[0]
                        rest_next = parts[1] if len(parts) > 1 else ""

                        prev_cells[target_col] = f"{prev_val} {first_token}".strip()
                        next_cells[target_col] = rest_next

                        lines[i] = "| " + " | ".join(prev_cells) + " |"
                        if any(bool(c.strip()) for c in next_cells):
                            lines[j] = "| " + " | ".join(next_cells) + " |"
                        else:
                            lines[j] = ""

            # Case B: Plain text lines across page break
            elif not _is_table_row(prev_line) and not _is_table_row(next_line):
                prev_val = prev_line.strip()
                next_val = next_line.strip()

                if next_val and next_val[0].islower() and (prev_val and prev_val[-1] not in ".!?:"):
                    parts = next_val.split(maxsplit=1)
                    first_token = parts[0]
                    rest_next = parts[1] if len(parts) > 1 else ""

                    lines[i] = f"{prev_line} {first_token}".strip()
                    lines[j] = rest_next

        i += 1

    return "\n".join(lines)


def stitch_ocr_multipage_tables(markdown: str) -> str:
    """Merge markdown tables split across page breaks (--- or <!-- Trang X -->).

    Removes intermediate `---` dividers and repeated headers between table segments,
    producing a unified Master Table while preserving page commentary.
    """
    lines = markdown.splitlines()
    out_lines: list[str] = []
    i = 0
    n = len(lines)

    in_table = False
    last_table_col_count = 0
    last_header_cells: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if _is_table_row(stripped):
            cells = _split_table_cells(stripped)
            col_count = len(cells)

            if not in_table:
                # Potential start of a new table
                # Lookahead to see if next line is separator
                if i + 1 < n and _is_table_separator(lines[i + 1]):
                    in_table = True
                    last_table_col_count = col_count
                    last_header_cells = [c.lower() for c in cells]
                    out_lines.append(line)
                    out_lines.append(lines[i + 1])
                    i += 2
                    continue
                out_lines.append(line)
                i += 1
                continue

            # Currently in_table: check if this is a duplicated header
            norm_cells = [c.lower() for c in cells]
            is_dup_header = (
                last_header_cells
                and norm_cells == last_header_cells
                and i + 1 < n
                and _is_table_separator(lines[i + 1])
            )
            if is_dup_header:
                # Skip duplicate header and separator row
                i += 2
                continue

            # Normal data row
            out_lines.append(line)
            i += 1
            continue

        # Not a table row: check if it's a page boundary inside an open table
        if in_table:
            # Look ahead to see if the table continues after this boundary
            j = i
            page_comments: list[str] = []

            while j < n and not lines[j].strip():
                j += 1

            while j < n and (_RE_DIVIDER.match(lines[j].strip()) or _RE_PAGE_MARKER.match(lines[j].strip())):
                line_j = lines[j].strip()
                if _RE_PAGE_MARKER.match(line_j):
                    page_comments.append(line_j)
                j += 1
                while j < n and not lines[j].strip():
                    j += 1

            # Check if next meaningful line is a table continuation
            if j < n and _is_table_row(lines[j].strip()):
                next_cells = _split_table_cells(lines[j].strip())
                next_is_dup_header = (
                    last_header_cells
                    and [c.lower() for c in next_cells] == last_header_cells
                    and j + 1 < n
                    and _is_table_separator(lines[j + 1])
                )
                same_cols = (len(next_cells) == last_table_col_count) or (
                    abs(len(next_cells) - last_table_col_count) <= 1
                )

                if same_cols or next_is_dup_header:
                    # Bridge the table!
                    # Do not emit `---` which breaks markdown table syntax.
                    # Emit page comments as HTML comments if any
                    for pc in page_comments:
                        out_lines.append(f"<!-- {pc} -->" if not pc.startswith("<!--") else pc)
                    i = j
                    continue

            # Not a continuation: close the table
            in_table = False
            last_header_cells = []
            last_table_col_count = 0

        out_lines.append(line)
        i += 1

    return "\n".join(out_lines)


def merge_ocr_orphan_table_rows(markdown: str) -> str:
    """Merge orphan continuation rows (where Column 0 is empty) into the parent row.

    Transforms multi-line cell breaks into a single unified row using `<br>`.
    Example:
      | 1.1 | Kế thừa chức năng... | | | | |
      |     | Bảo đảm hệ thống... | | | | |
    Becomes:
      | 1.1 | Kế thừa chức năng...<br>Bảo đảm hệ thống... | | | | |
    """
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

        # A row is an orphan continuation row if Column 0 is empty but at least one other column has text
        is_orphan = (not col0) and any(bool(c.strip()) for c in cells[1:]) and (last_parent_idx != -1)

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
                        # If child is a lowercase sentence continuation, join with space
                        if child_val and child_val[0].islower():
                            parent_cells[k] = f"{parent_val} {child_val}"
                        else:
                            parent_cells[k] = f"{parent_val}<br>{child_val}"

            out_lines[last_parent_idx] = "| " + " | ".join(parent_cells) + " |"
            i += 1
            continue

        # Normal row
        out_lines.append(line)
        last_parent_idx = len(out_lines) - 1
        i += 1

    return "\n".join(out_lines)


def clean_ocr_table_syntax(markdown: str) -> str:
    """Clean duplicate separators, standardize column alignments and fix OCR typos."""
    text = markdown

    # 1. Remove duplicate adjacent table separator rows
    dup_sep = re.compile(
        r"(^\s*\|(?:\s*:?-+:?\s*\|)+\s*\n)(?:\s*\|(?:\s*:?-+:?\s*\|)+\s*\n)+",
        re.MULTILINE,
    )
    text = dup_sep.sub(r"\1", text)

    # 2. Fix Vietnamese administrative & tech OCR typos
    # 'số chỉ' -> 'chỉ số' when describing metrics/indicators
    text = re.sub(
        r"\b(số\s+chỉ)\s+(hiệu\s+năng|đo\s+lường|kỹ\s+thuật|đánh\s+giá|phát\s+triển|then\s+chốt)\b",
        r"chỉ số \2",
        text,
        flags=re.IGNORECASE,
    )

    # Standardize 'kí kết' -> 'ký kết'
    text = re.sub(r"\bkí\s+kết\b", "ký kết", text, flags=re.IGNORECASE)
    text = re.sub(r"\bkí\s+hợp\s+đồng\b", "ký hợp đồng", text, flags=re.IGNORECASE)

    # 3. Clean trailing empty spaces inside table pipes
    text = re.sub(r"\|\s*\|\s*\|\s*\|\s*\|\s*\|$", "||||||", text, flags=re.MULTILINE)

    # 4. Clean orphan header page numbers immediately following page markers
    # Administrative format (Decree 30/2020/ND-CP Article 9.4) places isolated page numbers at top
    text = re.sub(
        r"(<!--\s*Trang\s*\d+\s*-->\s*\n+)[0-9]{1,3}\s*\n+",
        r"\1",
        text,
    )

    # 5. Remove stray separator rows placed between data rows (only 1 separator right after header is valid)
    lines = text.splitlines()
    clean_lines: list[str] = []
    in_tbl = False
    seen_sep = False
    for line in lines:
        stripped = line.strip()
        if _is_table_separator(stripped):
            if not in_tbl or seen_sep:
                continue
            seen_sep = True
            clean_lines.append(line)
        elif _is_table_row(stripped):
            in_tbl = True
            clean_lines.append(line)
        else:
            in_tbl = False
            seen_sep = False
            clean_lines.append(line)

    return "\n".join(clean_lines)


def post_process_ocr_output(
    raw_text: str, pages: list[dict[str, Any]] | None = None
) -> tuple[str, list[dict[str, Any]]]:
    """Execute full post-processing pipeline on OCR markdown text and page outputs.

    This function is strictly isolated to the OCR module and does not impact DOCX or PDF Text.
    """
    if not raw_text or not raw_text.strip():
        return raw_text, pages or []

    # Step 1: Repair words split across page/table boundaries
    cleaned = repair_ocr_split_words_across_pages(raw_text)

    # Step 2: Stitch multi-page tables across --- / page boundaries
    cleaned = stitch_ocr_multipage_tables(cleaned)

    # Step 3: Merge orphan continuation rows into parent rows
    cleaned = merge_ocr_orphan_table_rows(cleaned)

    # Step 4: Clean syntax & typos
    cleaned = clean_ocr_table_syntax(cleaned)

    # Step 5: Update page chunks if pages were provided
    out_pages: list[dict[str, Any]] = []
    if pages:
        for p in pages:
            p_copy = dict(p)
            p_text = str(p_copy.get("extracted_text") or "")
            if p_text:
                p_cleaned = repair_ocr_split_words_across_pages(p_text)
                p_cleaned = merge_ocr_orphan_table_rows(p_cleaned)
                p_cleaned = clean_ocr_table_syntax(p_cleaned)
                p_copy["extracted_text"] = p_cleaned
                p_copy["word_count"] = len(p_cleaned.split())
                p_copy["line_count"] = len(p_cleaned.splitlines())
            out_pages.append(p_copy)
    else:
        out_pages = []

    return cleaned, out_pages
