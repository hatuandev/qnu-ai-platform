"""Explicit column-header years; geometry and labels only, never file names or dates."""

import re
import unicodedata

from qnu.domains.knowledge.index.table_layout import header_rows, layout, table_structure

DATA_YEAR = re.compile(r"(?:năm(?:\s+dữ\s+liệu)?|niên\s+độ)\s*[:–-]?\s*((?:19|20)\d{2})(?!\d)")
LABELLED_YEAR = re.compile(
    r"(?:năm(?:\s+(?:dữ\s+liệu|tuyển\s+sinh))?|niên\s+độ(?:\s+báo\s+cáo)?|"
    r"mùa\s+tuyển\s+sinh|tuyển\s+sinh(?:\s+năm)?)\s*[:–-]?\s*((?:19|20)\d{2})(?!\d)"
)
ROLE = re.compile(r"\b(?:ban\s+hành|hiệu\s+lực|ký|ngày|phát\s+hành)\b")
DATE = re.compile(r"\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4}")
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
RANGE = re.compile(
    r"(?<!\d)((?:19|20)\d{2})\s*(?:[-–—/]|\s+đến\s+)\s*((?:19|20)\d{2}|\d{2})(?!\d|[-/]\d)"
)


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").casefold().split())


def year_mentions(text: str) -> set[int]:
    """Years a header cell explicitly claims for its columns; dates and roles excluded."""
    value = DATE.sub(" ", _normalized(text))
    if ROLE.search(value):
        return set()
    years = {int(year) for year in YEAR.findall(value)}
    for start, end in RANGE.findall(value):
        years.add(int(start))
        years.add(int(end) if len(end) == 4 else int(start[:2] + end))
    return years


def data_year(text: str) -> int | None:
    """One explicitly labelled data year; dates, roles, ranges and year sets stay unknown."""
    value = _normalized(text)
    if ROLE.search(value) or DATE.search(value):
        return None
    labelled = {int(year) for year in DATA_YEAR.findall(value)}
    if len(labelled) == 1 and year_mentions(value) == labelled:
        return next(iter(labelled))
    return None


def labelled_years(text: str) -> set[int]:
    """Explicit data-year labels of one cell, including enrollment-season labels."""
    value = _normalized(text)
    if ROLE.search(value) or DATE.search(value):
        return set()
    return {int(year) for year in LABELLED_YEAR.findall(value)}


def column_year(cells: list[dict]) -> int | None:
    """One data year proven by the header cells governing a physical column.

    Any multi-year or conflicting claim leaves the column unknown, and a bare
    year never proves a scope without an explicit data-year label.
    """
    claimed: set[int] = set()
    labelled: set[int] = set()
    for cell in cells:
        text = cell.get("text", "")
        claimed |= year_mentions(text)
        year = data_year(text)
        if year is not None:
            labelled.add(year)
    if len(claimed) == 1 and claimed == labelled:
        return next(iter(claimed))
    return None


def _has_data(positions: list, headers: list[int], column: int) -> bool:
    """A non-header cell physically covers this column; spans keep their own start."""
    return any(
        position.row not in headers
        and position.column <= column < position.column + position.cell["col_span"]
        and (position.cell.get("text") or "").strip()
        for position in positions
    )


def header_year_scopes(draft: dict) -> list[dict]:
    """Column scopes proven by a marked header cell that names exactly one data year."""
    scopes = []
    for entry in draft.get("source_tables", []):
        table = entry.get("table") or {}
        if table.get("status") != "parsed":
            continue
        shape = table_structure(table)
        positions, errors = layout(shape)
        if errors:
            continue
        headers = header_rows(shape)
        if not headers:
            continue
        for column in range(shape["original_column_count"]):
            governing = [
                position.cell
                for position in positions
                if position.row in headers
                and position.column <= column < position.column + position.cell["col_span"]
            ]
            year = column_year(governing)
            if year is None or not _has_data(positions, headers, column):
                continue
            cell = next(cell for cell in governing if data_year(cell.get("text", "")) == year)
            scopes.append(
                {
                    "table": entry["citation"],
                    "column": column,
                    "year": year,
                    "evidence_citation": entry["citation"].split(":", 1)[0]
                    + ":"
                    + cell["evidence_id"],
                    "evidence_quote": cell["text"],
                }
            )
    return scopes
