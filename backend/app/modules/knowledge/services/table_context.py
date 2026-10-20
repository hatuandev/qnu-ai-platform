"""Header trees recovered only from evidenced structural repetitions."""

import re
from itertools import pairwise
from typing import Any

from app.modules.knowledge.entity_codes import code_cell
from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.source_pages import canonical_pages
from app.modules.knowledge.services.temporal_metadata import YEAR

SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


def clean_cell(value: str) -> str:
    text = value.strip()
    for marker in ('**', '__', '`', '*', '_'):
        if text.startswith(marker) and text.endswith(marker) and len(text) > 2 * len(marker):
            text = text[len(marker):-len(marker)].strip()
    return text


def _boundary_noise(lines: list[str]) -> bool:
    return all(not line.strip() or re.fullmatch(r"\s*\d{1,3}\s*", line) for line in lines)


def _year_subheader(row: list[str]) -> bool:
    cells = [clean_cell(cell) for cell in row]
    years = [cell for cell in cells if YEAR.fullmatch(cell)]
    return len(set(years)) >= 2 and not cells[0].isdigit() and all(
        not cell or YEAR.fullmatch(cell) or (len(cell) <= 45 and not re.search(r"\d", cell))
        for cell in cells
    )


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
    row = [clean_cell(cell) for cell in row]
    previous = [clean_cell(cell) for cell in previous] if previous else None
    return bool(previous and len(row) == len(previous) and row[0].strip().isdigit()
                and previous[0].strip().isdigit() and int(row[0]) == int(previous[0]) + 1
                and any(any(char.isalpha() for char in cell) for cell in row[1:])
                and any(code_cell(cell.strip()) and any(c.isdigit() for c in cell) for cell in row[1:]))


def _coded_data_row(row: list[str]) -> bool:
    return bool(row and re.fullmatch(r"\d+[.)]?", clean_cell(row[0]))
                and any(re.fullmatch(r"\d{3,}[A-Za-z]*", clean_cell(cell)) for cell in row[1:]))


def _body_rows(lines: list[str], start: int, previous: list[str] | None = None, declared: bool = False) -> tuple[list[list[str]], int]:
    rows, i = [], start
    while i < len(lines) and "|" in lines[i] and not SEPARATOR.fullmatch(lines[i]):
        row = _split_gfm_row(lines[i])
        if i + 1 < len(lines) and SEPARATOR.fullmatch(lines[i + 1]):
            if not _successor(rows[-1] if rows else previous, row) and not (declared and not rows and _coded_data_row(row)):
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
            adjacent = preceding and preceding.get("ends_page") and preceding["page_number"] == page["page_number"] - 1 and _boundary_noise(lines[:i])
            same_page = preceding and preceding["page_number"] == page["page_number"] and _boundary_noise(lines[preceding.get("end_line_number", 0):i])
            if (preceding and (adjacent or same_page) and "|" in lines[i]
                    and (preceding["rows"] and _successor(preceding["rows"][-1], _split_gfm_row(lines[i]))
                         or same_page and not preceding["rows"] and len(preceding["headers"]) == len(_split_gfm_row(lines[i]))
                         and not _coded_data_row(preceding["headers"]) and _coded_data_row(_split_gfm_row(lines[i])))):
                rows, i = _body_rows(lines, i, preceding["rows"][-1] if preceding["rows"] else None, declared=True)
                tables.append({**preceding, "id": f"table_{len(tables) + 1}", "page_number": page["page_number"],
                               "rows": rows, "continuation_of": preceding["id"],
                               "header_page_number": preceding.get("header_page_number", preceding["page_number"]),
                               "end_line_number": i,
                               "ends_page": _boundary_noise(lines[i:])})
                continue
            if i + 1 >= len(lines) or "|" not in lines[i] or not SEPARATOR.fullmatch(lines[i + 1]):
                i += 1
                continue
            start = i
            headers = [_split_gfm_row(lines[i])]
            i += 2
            rows, i = _body_rows(lines, i, declared=not _coded_data_row(headers[0]))
            while rows and len(rows[0]) == len(headers[0]) and (_year_subheader(rows[0]) or (
                (not rows[0][0].strip() or (
                    clean_cell(rows[0][0]) == clean_cell(headers[0][0])
                    and (any(YEAR.fullmatch(clean_cell(value)) for value in headers[0])
                         or sum(bool(clean_cell(value)) and clean_cell(value) == clean_cell(rows[0][col])
                                for col, value in enumerate(headers[0])) >= len(headers[0]) / 2)
                )) and any(rows[0])
                and all(not cell.strip() or any(c.isalpha() for c in cell) or YEAR.fullmatch(clean_cell(cell)) for cell in rows[0])
            )):
                child = rows.pop(0)
                if _year_subheader(child):
                    child = [clean_cell(cell) if YEAR.fullmatch(clean_cell(cell)) else "" for cell in child]
                headers.append(child)
            paths = header_paths(headers)
            tables.append({"id": f"table_{len(tables) + 1}", "page_number": page["page_number"],
                           "line_number": start + 1, "headers": [" / ".join(path) for path in paths],
                           "end_line_number": i,
                           "header_paths": paths, "header_rows": headers, "rows": rows,
                           "header_page_number": page["page_number"],
                           "ends_page": _boundary_noise(lines[i:]),
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
        roles = {col: detect_column_role(" / ".join(paths[col]))[0] for col in range(first, end)}
        code_cols = [col for col in range(first, end) if roles[col] == "code" and code_cell(clean_cell(row[col]))]
        named_cols = [col for col in range(first, end) if roles[col] == "name" and clean_cell(row[col])]
        text_cols = [col for col in range(first, end) if col not in code_cols and roles[col] is None
                     and any(char.isalpha() for char in row[col])]
        descriptive = [col for col in text_cols if sum(char.isalpha() for char in row[col]) / max(len(row[col]), 1) > 0.5]
        def diversity(column: int) -> float:
            values = [clean_cell(value[column]).casefold() for value in table["rows"] if len(value) > column and any(char.isalpha() for char in value[column])]
            return len(set(values)) / max(len(table["rows"]), 1)

        identity = (named_cols[0] if len(named_cols) == 1 else code_cols[0] if len(code_cols) == 1
                    else max(descriptive or text_cols or [first], key=diversity))
        code = clean_cell(row[code_cols[0]]) if len(code_cols) == 1 else None
        name = (clean_cell(row[identity]) if named_cols or code_cols or text_cols
                else " ".join([*paths[identity], clean_cell(row[identity])]))
        identities.append((identity, end, name, code))
    return identities
