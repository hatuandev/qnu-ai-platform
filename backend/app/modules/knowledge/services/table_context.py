"""Header trees recovered only from evidenced structural repetitions."""

import re
from itertools import pairwise
from typing import Any

from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.source_pages import canonical_pages
from app.modules.knowledge.services.temporal_metadata import YEAR

SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


def clean_cell(value: str) -> str:
    return re.sub(r"[*_`]", "", value).strip()


def header_paths(rows: list[list[str]]) -> list[list[str]]:
    width = len(rows[0])
    grid = [[clean_cell(cell) for cell in row] for row in rows]
    for level, row in enumerate(grid[:-1]):
        anchors = [i for i, value in enumerate(row) if value]
        for pos, start in enumerate(anchors):
            end = anchors[pos + 1] if pos + 1 < len(anchors) else width
            if end - start <= 1:
                continue
            # Repeatable child columns establish the bounds of each merged year.
            child = grid[level + 1][start:end]
            peers = [grid[level + 1][a:(anchors[p + 1] if p + 1 < len(anchors) else width)]
                     for p, a in enumerate(anchors) if YEAR.fullmatch(row[a]) and a != start]
            if all(child) and ((YEAR.fullmatch(row[start]) and child in peers)
                              or all(YEAR.fullmatch(value) for value in child)):
                for col in range(start + 1, end):
                    row[col] = row[start]
    return [list(dict.fromkeys(row[col] for row in grid if col < len(row) and row[col])) for col in range(width)]


def _successor(previous: list[str] | None, row: list[str]) -> bool:
    return bool(previous and len(row) == len(previous) and row[0].strip().isdigit()
                and previous[0].strip().isdigit() and int(row[0]) == int(previous[0]) + 1
                and any(any(char.isalpha() for char in cell) for cell in row[1:])
                and any(re.fullmatch(r"\d{3,}", cell.strip()) for cell in row[1:]))


def _body_rows(lines: list[str], start: int, previous: list[str] | None = None) -> tuple[list[list[str]], int]:
    rows, i = [], start
    while i < len(lines) and "|" in lines[i] and not SEPARATOR.fullmatch(lines[i]):
        row = _split_gfm_row(lines[i])
        if i + 1 < len(lines) and SEPARATOR.fullmatch(lines[i + 1]):
            if not _successor(rows[-1] if rows else previous, row):
                break
            rows.append(row)
            i += 2
            continue
        rows.append(row)
        i += 1
    return rows, i


def extract_context_tables(markdown: str, page_count: int) -> list[dict[str, Any]]:
    tables = []
    for page in canonical_pages(markdown, page_count):
        lines = page["markdown_content"].splitlines()
        i = 0
        while i < len(lines):
            preceding = tables[-1] if tables else None
            if (preceding and preceding.get("ends_page") and preceding["page_number"] == page["page_number"] - 1
                    and not any(line.strip() for line in lines[:i]) and "|" in lines[i]
                    and preceding["rows"] and _successor(preceding["rows"][-1], _split_gfm_row(lines[i]))):
                rows, i = _body_rows(lines, i, preceding["rows"][-1])
                tables.append({**preceding, "id": f"table_{len(tables) + 1}", "page_number": page["page_number"],
                               "rows": rows, "continuation_of": preceding["id"],
                               "header_page_number": preceding.get("header_page_number", preceding["page_number"]),
                               "ends_page": not any(line.strip() for line in lines[i:])})
                continue
            if i + 1 >= len(lines) or "|" not in lines[i] or not SEPARATOR.fullmatch(lines[i + 1]):
                i += 1
                continue
            start = i
            headers = [_split_gfm_row(lines[i])]
            i += 2
            rows, i = _body_rows(lines, i)
            while rows and len(rows[0]) == len(headers[0]) and (
                not rows[0][0].strip() and any(rows[0])
                and all(not cell.strip() or any(c.isalpha() for c in cell) or YEAR.fullmatch(clean_cell(cell)) for cell in rows[0])
            ):
                headers.append(rows.pop(0))
            paths = header_paths(headers)
            tables.append({"id": f"table_{len(tables) + 1}", "page_number": page["page_number"],
                           "line_number": start + 1, "headers": [" / ".join(path) for path in paths],
                           "header_paths": paths, "header_rows": headers, "rows": rows,
                           "header_page_number": page["page_number"],
                           "ends_page": not any(line.strip() for line in lines[i:]),
                           "evidence": "canonical_markdown"})
    return tables


def row_identities(row: list[str], table: dict[str, Any]) -> list[tuple[int, int, str, str | None]]:
    """Split side-by-side conversion tables on empty separator columns."""
    paths = table["header_paths"]
    breaks = [i for i, path in enumerate(paths) if not path and not row[i].strip()]
    boundaries = [-1, *breaks, len(row)]
    identities = []
    for start, end in pairwise(boundaries):
        first = start + 1
        if end - first < 2:
            continue
        code_cols = [col for col in range(first, end) if detect_column_role(" / ".join(paths[col]))[0] == "code"
                     and re.fullmatch(r"\d{3,}[A-Za-z]*", clean_cell(row[col]))]
        text_cols = [col for col in range(first, end) if any(char.isalpha() for char in row[col])]
        identity = min(text_cols, key=lambda col: min(abs(col - c) for c in code_cols)) if text_cols and code_cols else text_cols[0] if text_cols else first
        code = clean_cell(row[code_cols[0]]) if len(code_cols) == 1 else None
        name = clean_cell(row[identity]) if text_cols else " ".join([*paths[identity], clean_cell(row[identity])])
        identities.append((identity, end, name, code))
    return identities
