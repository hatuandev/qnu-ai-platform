"""Explicit column-header years; geometry and labels only, never file names or dates."""

import re
import unicodedata

from qnu.domains.knowledge.index.table_dependencies import multitier_header
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
BARE_YEAR = re.compile(r"((?:19|20)\d{2})\s*[*†‡]?")
SEASON_TITLE = re.compile(r"^thông\s+tin\s+tuyển\s+sinh\b.+\bnăm\s+((?:19|20)\d{2})\b")
CONVERSION_INTRO = re.compile(
    r"\b(?:được\s+)?quy\s+đổi(?:\s+theo\s+[^:;.]{1,55})?\s+như\s+sau\s*:$"
)
PAST_DATA = re.compile(r"\b(?:năm\s+trước|trước\s+đây|tham\s+khảo|đã\s+áp\s+dụng)\b")


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


def bare_year(text: str) -> int | None:
    """A header cell that holds nothing but one year (an optional footnote mark allowed)."""
    value = _normalized(text)
    match = BARE_YEAR.fullmatch(value)
    if match is None or ROLE.search(value) or DATE.search(value):
        return None
    return int(match.group(1))


def column_year_proof(
    cells: list[dict], *, allow_bare_year: bool = False
) -> tuple[int | None, list[dict]]:
    """One data year and the header cells that prove it for a physical column.

    A bare year proves nothing by default. It is accepted only when the caller
    verified a multitier header and the cell itself is a merged group governing
    child columns. Any multi-year or conflicting claim leaves the column unknown.
    """
    claimed: set[int] = set()
    labelled: list[dict] = []
    bare: list[dict] = []
    for cell in cells:
        text = cell.get("text", "")
        claimed |= year_mentions(text)
        year = data_year(text)
        if year is not None:
            labelled.append(cell)
        if allow_bare_year and bare_year(text) is not None and cell["col_span"] > 1:
            bare.append(cell)
    if len(claimed) != 1:
        return None, []
    year = next(iter(claimed))
    proven = [cell for cell in labelled if data_year(cell.get("text", "")) == year]
    if proven:
        return year, proven
    if bare and {bare_year(cell.get("text", "")) for cell in bare} == {year}:
        return year, bare
    return None, []


def column_year(cells: list[dict]) -> int | None:
    """One data year proven by an explicit label in the governing header cells."""
    return column_year_proof(cells)[0]


def table_year_headers(table: dict, shape: dict) -> tuple[list[int], bool]:
    marked = header_rows(shape)
    if len(marked) == 1:
        return marked, False
    structural = multitier_header(table) or []
    allow_bare = bool(structural and (not marked or set(structural) <= set(marked)))
    return marked or structural, allow_bare


def _has_data(positions: list, headers: list[int], column: int) -> bool:
    """A non-header cell physically covers this column; spans keep their own start."""
    return any(
        position.row not in headers
        and position.column <= column < position.column + position.cell["col_span"]
        and (position.cell.get("text") or "").strip()
        for position in positions
    )


def header_year_scopes(draft: dict) -> list[dict]:
    """Column scopes proven by native header marks or a proven multitier header."""
    scopes = []
    for entry in draft.get("source_tables", []):
        table = entry.get("table") or {}
        if table.get("status") != "parsed":
            continue
        shape = table_structure(table)
        positions, errors = layout(shape)
        if errors:
            continue
        tiers, allow_bare = table_year_headers(table, shape)
        if not tiers:
            continue
        headers = set(tiers)
        for column in range(shape["original_column_count"]):
            governing = [
                position.cell
                for position in positions
                if position.row in headers
                and position.column <= column < position.column + position.cell["col_span"]
            ]
            year, proof = column_year_proof(governing, allow_bare_year=allow_bare)
            if year is None or not _has_data(positions, headers, column):
                continue
            cell = proof[0]
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


def _season_title(page: dict) -> tuple[int, dict] | None:
    candidates = []
    for block in page["blocks"]:
        text = block["text"].strip()
        normal = _normalized(text)
        match = SEASON_TITLE.match(normal)
        if not match or not (text.isupper() or block.get("type") in {"title", "heading"}):
            continue
        year = int(match[1])
        if year_mentions(normal) == {year} and not block.get("requires_review"):
            candidates.append((year, block))
    return candidates[0] if len(candidates) == 1 else None


def _conversion_table(table: dict) -> bool:
    if table.get("status") != "parsed":
        return False
    positions, errors = layout(table_structure(table))
    return (
        not errors
        and any(
            position.row == 0 and "quy đổi" in _normalized(position.cell["text"])
            for position in positions
        )
        and not any(year_mentions(position.cell["text"]) for position in positions)
    )


def conversion_year_scopes(documents: list[dict]) -> dict[str, tuple[int, list[dict]]]:
    """Bind a current conversion rule to its own explicitly titled intake season."""
    found = {}
    for document in documents:
        if not document["pages"] or not (season := _season_title(document["pages"][0])):
            continue
        year, title = season
        run = document["ocr_run_id"]
        for page in document["pages"]:
            intro = None
            blocks = page["blocks"]
            for i, block in enumerate(blocks):
                text = _normalized(block["text"])
                if block.get("requires_review"):
                    intro = None
                elif (table := block.get("table")) and intro and _conversion_table(table):
                    found[f"{run}:{block['evidence_id']}"] = (
                        year,
                        [
                            {"citation": f"{run}:{b['evidence_id']}", "quote": b["text"].strip()}
                            for b in (title, intro)
                        ],
                    )
                elif CONVERSION_INTRO.search(text):
                    context = " ".join(
                        _normalized(b["text"]) for b in blocks[max(0, i - 2) : i + 1]
                    )
                    mentioned = {int(value) for value in YEAR.findall(DATE.sub(" ", context))}
                    intro = block if not PAST_DATA.search(context) and mentioned <= {year} else None
                else:
                    intro = None
    return found
