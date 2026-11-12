"""Project explicitly named rows and verified year columns; never guess."""

import re
import unicodedata

from qnu.domains.rag.answer.selection import question_needs

VERSION = "qnu.rag.table-selection/v2"

_ROW_CELL = re.compile(r"^table:(.+):row:(\d+):column:(\d+)$")
_ROW = re.compile(r"^table:(.+):row:(\d+)$")
_COLUMN = re.compile(r"^table:(.+):column:(\d+)$")
_CELL_KEY = re.compile(r":r(\d+):k(\d+)$")


def _words(text: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold()))


def _matches(question: str, labels: set[str]) -> set[str]:
    spans = [
        (match.start(), match.end(), label)
        for label in labels
        if label and any(c.isalpha() for c in label)
        for match in re.finditer(r"(?<!\w)" + re.escape(label) + r"(?!\w)", question)
    ]
    # A prefix name inside a longer named subject is not a second subject.
    return {
        label
        for start, end, label in spans
        if not any(a <= start and end <= b and (a, b) != (start, end) for a, b, _ in spans)
    }


def requested_data_years(metadata_filter: dict | None) -> set[int]:
    """Exact data years already resolved for this turn; empty means no year scope."""
    if not metadata_filter:
        return set()
    scopes = metadata_filter.get("any_of") or [metadata_filter]
    return {scope["data_year"] for scope in scopes if type(scope.get("data_year")) is int}


def _year_scopes(
    source,
) -> tuple[dict[int, set[int]], dict[int, set[int]], dict[tuple[int, int], set[int]]]:
    """Column, row and cell year proof published on this source's own annotations."""
    structure = source.structure or {}
    citation = structure.get("source_table_citation")
    columns: dict[int, set[int]] = {}
    rows: dict[int, set[int]] = {}
    cells: dict[tuple[int, int], set[int]] = {}
    if not citation:
        return columns, rows, cells
    for annotation in structure.get("retrieval_metadata", []):
        year = (annotation.get("values") or {}).get("data_year")
        if type(year) is not int:
            continue
        target = annotation.get("target", "")
        cell = _ROW_CELL.fullmatch(target)
        column = _COLUMN.fullmatch(target)
        row = _ROW.fullmatch(target)
        if cell and cell.group(1) == citation:
            cells.setdefault((int(cell.group(2)), int(cell.group(3))), set()).add(year)
        elif column and column.group(1) == citation:
            columns.setdefault(int(column.group(2)), set()).add(year)
        elif row and row.group(1) == citation:
            rows.setdefault(int(row.group(2)), set()).add(year)
    return columns, rows, cells


def _cell_years(cell: dict, scopes) -> set[int]:
    columns, rows, cells = scopes
    match = _CELL_KEY.search(cell.get("cell_id", ""))
    if not match:
        return set()
    row, column = int(match.group(1)), int(match.group(2))
    return columns.get(column, set()) | rows.get(row, set()) | cells.get((row, column), set())


def _year_kept(cell: dict, scopes, years: set[int]) -> bool:
    """A cell with a proven year must match the request; unknown stays selectable."""
    proven = _cell_years(cell, scopes)
    return not proven or bool(proven & years)


def select_catalog(
    cells: dict,
    sources: list,
    question: str,
    links: list[dict],
    *,
    data_years: set[int] | None = None,
) -> dict:
    """Keep all fields/notes for named subjects and requested years; uncertain keeps all.

    Families require the same publication and physical table or sealed header
    dependency. A match in another document/table never narrows this family.
    Years come from published column/row/cell annotations only.
    """
    by_id = {s.evidence_id: s for s in sources}
    needs = question_needs(question)
    can_narrow = not needs["enumeration"] and (needs["single_value"] or needs["comparison"])
    headers = {link["chunk_id"]: link["header"] for link in links}
    families = {}
    for table in cells["tables"]:
        source = by_id[table["evidence_id"]]
        citation = (source.structure or {}).get("source_table_citation")
        if not citation:
            continue
        key = (
            source.document_id,
            source.version_id,
            source.publication_decision_id,
            headers.get(source.chunk_id, citation),
        )
        families.setdefault(key, []).append(table)
    selected = {}
    matched_families = 0
    for tables in families.values():
        labels = {
            _words(cell["subject_labels"][0])
            for table in tables
            for cell in table["cells"]
            if cell.get("subject_labels")
        }
        matches = _matches(_words(question), labels) if can_narrow else set()
        if needs["comparison"] and len(matches) < 2:
            # A single named subject may be compared with the rest of the table.
            matches = set()
        if not matches:
            continue
        matched_families += 1
        for table in tables:
            kept = [
                cell
                for cell in table["cells"]
                if not cell.get("subject_labels") or _words(cell["subject_labels"][0]) in matches
            ]
            selected[table["evidence_id"]] = kept
    years = data_years or set()
    scopes = {source.evidence_id: _year_scopes(source) for source in sources}
    tables, omitted = [], []
    year_omitted = 0
    for table in cells["tables"]:
        kept = selected.get(table["evidence_id"], table["cells"])
        narrowed = (
            [cell for cell in kept if _year_kept(cell, scopes[table["evidence_id"]], years)]
            if years
            else kept
        )
        year_omitted += len(kept) - len(narrowed)
        if table["cells"] and not narrowed:
            omitted.append(table["evidence_id"])
        tables.append({**table, "cells": narrowed})
    return {
        **cells,
        "tables": tables,
        "selection": {
            "version": VERSION,
            "basis": "exact_source_subject_and_sealed_table_family",
            "matched_families": matched_families,
            "requested_years": sorted(years),
            "year_omitted_cells": year_omitted,
            "available_cells": sum(len(t["cells"]) for t in cells["tables"]),
            "selected_cells": sum(len(t["cells"]) for t in tables),
            "omitted_tables": omitted,
        },
    }
