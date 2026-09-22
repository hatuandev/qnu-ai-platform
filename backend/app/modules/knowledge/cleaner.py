"""Markdown Document Cleaner & Vietnamese Text Normalization."""

from __future__ import annotations

import re
import unicodedata

# Regex patterns for cleaning document text
_RE_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_RE_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
_RE_PAGE_NUMBERS = re.compile(
    r"^\s*(?:Trang\s+\d+(?:\s*/\s*\d+)?|[-—~–]\s*\d+\s*[-—~–]|\d+\s*/\s*\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_RE_HEADING_NORMALIZE = re.compile(
    r"^(điều|khoản|chương|mục|phần)\s+(\d+|[IVXLCDM]+)[\.:]?\s*", re.IGNORECASE | re.MULTILINE
)


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and (s.endswith("|") or "|" in s[1:])


def _is_table_sep(line: str) -> bool:
    s = line.strip()
    if not s.startswith("|"):
        return False
    inner = s[1:-1] if s.endswith("|") else s.lstrip("|")
    cells = [c.strip() for c in inner.split("|")]
    return len(cells) > 0 and all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cells if c)


def _count_cols(line: str) -> int:
    clean_s = line.strip().replace(r"\|", "___ESCAPED_PIPE___")
    inner = clean_s[1:-1] if clean_s.endswith("|") else clean_s.lstrip("|")
    return len(inner.split("|"))


def _normalize_markdown_table_block(table_lines: list[str]) -> list[str]:
    """Chuẩn hóa một khối bảng Markdown: căn chỉnh số cột, định dạng header và separator."""
    if not table_lines:
        return []

    cleaned_rows = [ln.strip() for ln in table_lines if ln.strip()]
    if not cleaned_rows:
        return []

    first_data = next((ln for ln in cleaned_rows if not _is_table_sep(ln)), None)
    if not first_data:
        return []

    expected_cols = _count_cols(first_data)
    if expected_cols < 2:
        return cleaned_rows

    result: list[str] = []

    for idx, row in enumerate(cleaned_rows):
        if _is_table_sep(row):
            sep_cells = [":---:" if c_i == 0 and expected_cols > 3 else ":---" for c_i in range(expected_cols)]
            result.append("| " + " | ".join(sep_cells) + " |")
            continue

        clean_s = row.replace(r"\|", "___ESCAPED_PIPE___")
        inner = clean_s[1:-1] if clean_s.endswith("|") else clean_s.lstrip("|")
        raw_cells = [c.replace("___ESCAPED_PIPE___", r"\|").strip() for c in inner.split("|")]

        if len(raw_cells) < expected_cols:
            raw_cells += [""] * (expected_cols - len(raw_cells))
        elif len(raw_cells) > expected_cols:
            raw_cells = raw_cells[:expected_cols]

        result.append("| " + " | ".join(raw_cells) + " |")

        # Tự động chèn dòng phân cách header sau dòng đầu tiên nếu thiếu
        if idx == 0 and (len(cleaned_rows) == 1 or not _is_table_sep(cleaned_rows[1])):
            sep_cells = [":---:" if c_i == 0 and expected_cols > 3 else ":---" for c_i in range(expected_cols)]
            result.append("| " + " | ".join(sep_cells) + " |")

    return result


def _is_orphan_markdown_row(line: str) -> bool:
    """Check if a markdown table row lacks primary keys (empty STT/Code) but has trailing text."""
    if not _is_table_row(line) or _is_table_sep(line):
        return False
    clean_s = line.replace(r"\|", "___PIPE___")
    inner = clean_s[1:-1] if clean_s.endswith("|") else clean_s.lstrip("|")
    cells = [c.replace("___PIPE___", r"\|").strip() for c in inner.split("|")]
    if len(cells) < 3:
        return False
    first_empty = not any(cells[:min(3, len(cells) - 1)])
    has_trailing = any(len(c) > 0 for c in cells[min(3, len(cells) - 1):])
    return first_empty and has_trailing


def _merge_orphan_into_row(target_row: str, orphan_row: str) -> str:
    """Merge trailing text of an orphan continuation row into the target table row."""
    clean_t = target_row.replace(r"\|", "___PIPE___")
    inner_t = clean_t[1:-1] if clean_t.endswith("|") else clean_t.lstrip("|")
    t_cells = [c.replace("___PIPE___", r"\|").strip() for c in inner_t.split("|")]

    clean_o = orphan_row.replace(r"\|", "___PIPE___")
    inner_o = clean_o[1:-1] if clean_o.endswith("|") else clean_o.lstrip("|")
    o_cells = [c.replace("___PIPE___", r"\|").strip() for c in inner_o.split("|")]

    max_c = max(len(t_cells), len(o_cells))
    t_cells += [""] * (max_c - len(t_cells))
    o_cells += [""] * (max_c - len(o_cells))

    merged = []
    for tc, oc in zip(t_cells, o_cells):
        if tc and oc:
            merged.append(f"{tc} {oc}".strip())
        else:
            merged.append(tc or oc)
    return "| " + " | ".join(merged) + " |"


def _stitch_table_continuations(text: str) -> str:
    """Nối các bảng bị ngắt qua ranh giới trang (<!-- Trang N --> hoặc ---) mà không làm mất hàng."""
    lines = text.splitlines()
    result: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if _is_table_row(line) and not _is_table_sep(line):
            result.append(line)
            cols = _count_cols(line)

            j = i + 1
            interstitial = []
            while j < n and (
                not lines[j].strip()
                or lines[j].strip() == "---"
                or bool(re.match(r"^<!--\s*(?:Trang|Page)\s+\d+\s*-->$", lines[j].strip(), re.IGNORECASE))
            ):
                interstitial.append(lines[j])
                j += 1

            has_page_boundary = any(
                bool(re.match(r"^<!--\s*(?:Trang|Page)\s+\d+\s*-->$", x.strip(), re.IGNORECASE))
                or x.strip() == "---"
                for x in interstitial
            )

            if has_page_boundary and j < n and _is_table_row(lines[j]):
                next_cols = _count_cols(lines[j])
                if next_cols == cols:
                    k = j
                    # Check if lines[k] is an orphan continuation row
                    if _is_orphan_markdown_row(lines[k]) and result:
                        # Merge into previous table's last row!
                        result[-1] = _merge_orphan_into_row(result[-1], lines[k])
                        k += 1
                        # If a separator was inserted under the orphan row, skip it
                        if k < n and _is_table_sep(lines[k]):
                            k += 1
                    else:
                        # Skip repeated header if present
                        if _is_table_sep(lines[k]):
                            k += 1
                        elif k + 1 < n and _is_table_sep(lines[k + 1]):
                            k += 2

                    i = k - 1
            i += 1
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


def clean_markdown_text(raw_text: str) -> str:
    """Clean and normalize raw extracted markdown/text from documents."""
    if not raw_text:
        return ""

    # 1. Unicode NFC normalization (Zero Mojibake)
    text = unicodedata.normalize("NFC", raw_text)

    # 2. Strip null bytes, form feeds, and BOM
    text = text.replace("\x00", "").replace("\x0c", "\n\n").replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Strip dead/local image artifacts (e.g. ![img-0.jpeg](...))
    text = re.sub(
        r"!\[.*?\]\((?:img-\d+\.(?:jpeg|jpg|png|webp)|image\d*\.(?:png|jpg|jpeg)|local:.*?|data:image/[^)]+)\)",
        "",
        text,
    )

    # 4. Remove standalone page number lines
    text = _RE_PAGE_NUMBERS.sub("", text)

    # 5. Normalize multiple spaces (preserving newlines)
    text = _RE_MULTIPLE_SPACES.sub(" ", text)

    # 6. Normalize tables
    lines = text.split("\n")
    cleaned_lines: list[str] = []
    current_table: list[str] = []

    for line in lines:
        stripped = line.strip()
        if _is_table_row(stripped):
            current_table.append(stripped)
        else:
            if current_table:
                cleaned_lines.extend(_normalize_markdown_table_block(current_table))
                current_table = []
            cleaned_lines.append(stripped)

    if current_table:
        cleaned_lines.extend(_normalize_markdown_table_block(current_table))

    text = "\n".join(cleaned_lines)

    # 7. Stitch table continuations across page markers
    text = _stitch_table_continuations(text)

    # 8. Limit consecutive blank lines to at most 2
    text = _RE_MULTIPLE_NEWLINES.sub("\n\n", text)

    return text.strip()


def extract_sections_metadata(text: str) -> list[dict[str, str]]:
    """Identify key legal document sections (Điều, Khoản, Chương) for metadata indexing."""
    sections = []
    for match in _RE_HEADING_NORMALIZE.finditer(text):
        sections.append(
            {
                "type": match.group(1).capitalize(),
                "number": match.group(2),
                "match": match.group(0).strip(),
            }
        )
    return sections
