"""Project explicitly named rows and verified year columns; never guess."""

import re
import unicodedata

from qnu.domains.rag.answer.cells import join_continued_lists
from qnu.domains.rag.answer.selection import question_needs

VERSION = "qnu.rag.table-selection/v4"

_ROW_CELL = re.compile(r"^table:(.+):row:(\d+):column:(\d+)$")
_ROW = re.compile(r"^table:(.+):row:(\d+)$")
_COLUMN = re.compile(r"^table:(.+):column:(\d+)$")
_CELL_KEY = re.compile(r":r(\d+):k(\d+)$")
_PAREN_QUALIFIER = re.compile(r"\([^)]*\)")


def _words(text: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold()))


def _subject_keys(label: str) -> set[str]:
    full = _words(label)
    keys = {full} if full else set()
    base = _words(_PAREN_QUALIFIER.sub(" ", label))
    if base and base != full and len(base.split()) >= 2:
        keys.add(base)
    return keys


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


def requested_intakes(metadata_filter: dict | None) -> set[str]:
    """Exact intakes already resolved for this turn; empty means no intake scope."""
    if not metadata_filter:
        return set()
    scopes = metadata_filter.get("any_of") or [metadata_filter]
    return {
        scope["intake"]
        for scope in scopes
        if isinstance(scope.get("intake"), str) and scope["intake"]
    }


def _norm(value) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value)).casefold().split())


def _scoped_targets(structure: dict) -> list[tuple[str, object, dict]]:
    """Row, column and cell targets proven on this source's own annotations."""
    citation = structure.get("source_table_citation")
    if not citation:
        return []
    found = []
    for annotation in structure.get("retrieval_metadata", []):
        target = annotation.get("target", "")
        values = annotation.get("values") or {}
        cell = _ROW_CELL.fullmatch(target)
        column = _COLUMN.fullmatch(target)
        row = _ROW.fullmatch(target)
        if cell and cell.group(1) == citation:
            found.append(("cell", (int(cell.group(2)), int(cell.group(3))), values))
        elif column and column.group(1) == citation:
            found.append(("column", int(column.group(2)), values))
        elif row and row.group(1) == citation:
            found.append(("row", int(row.group(2)), values))
    return found


def _year_scopes(
    source,
) -> tuple[dict[int, set[int]], dict[int, set[int]], dict[tuple[int, int], set[int]]]:
    """Column, row and cell year proof published on this source's own annotations."""
    columns: dict[int, set[int]] = {}
    rows: dict[int, set[int]] = {}
    cells: dict[tuple[int, int], set[int]] = {}
    for kind, key, values in _scoped_targets(source.structure or {}):
        year = values.get("data_year")
        if type(year) is not int:
            continue
        if kind == "cell":
            cells.setdefault(key, set()).add(year)
        elif kind == "column":
            columns.setdefault(key, set()).add(year)
        else:
            rows.setdefault(key, set()).add(year)
    return columns, rows, cells


def _intake_scopes(
    source,
) -> tuple[dict[int, set[str]], dict[int, set[str]], dict[tuple[int, int], set[str]]]:
    """Column, row and cell intake proof, including intakes named by events."""
    columns: dict[int, set[str]] = {}
    rows: dict[int, set[str]] = {}
    cells: dict[tuple[int, int], set[str]] = {}
    for kind, key, values in _scoped_targets(source.structure or {}):
        proven = {_norm(values["intake"])} if values.get("intake") else set()
        proven |= {
            _norm(event["intake"])
            for event in values.get("events") or []
            if isinstance(event, dict) and event.get("intake")
        }
        if not proven:
            continue
        bucket = cells if kind == "cell" else columns if kind == "column" else rows
        bucket.setdefault(key, set()).update(proven)
    return columns, rows, cells


def _cell_years(cell: dict, scopes) -> set[int]:
    columns, rows, cells = scopes
    match = _CELL_KEY.search(cell.get("cell_id", ""))
    if not match:
        return set()
    row, column = int(match.group(1)), int(match.group(2))
    return columns.get(column, set()) | rows.get(row, set()) | cells.get((row, column), set())


def _cell_intakes(cell: dict, scopes) -> set[str]:
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


def _intake_kept(cell: dict, scopes, intakes: set[str]) -> bool:
    proven = _cell_intakes(cell, scopes)
    return not proven or bool(proven & intakes)


def select_catalog(
    cells: dict,
    sources: list,
    question: str,
    links: list[dict],
    *,
    data_years: set[int] | None = None,
    intakes: set[str] | None = None,
) -> dict:
    """Keep all fields/notes for named subjects and requested scope; uncertain keeps all.

    Families require the same publication and physical table or sealed header
    dependency. A match in another document/table never narrows this family.
    Years and intakes come from published row/column/cell annotations only.
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
            key
            for table in tables
            for cell in table["cells"]
            if cell.get("subject_labels")
            for key in _subject_keys(cell["subject_labels"][0])
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
                if not cell.get("subject_labels")
                or bool(_subject_keys(cell["subject_labels"][0]) & matches)
            ]
            selected[table["evidence_id"]] = kept
    years = data_years or set()
    wanted_intakes = {_norm(value) for value in intakes or set()}
    year_scopes = {source.evidence_id: _year_scopes(source) for source in sources}
    intake_scopes = (
        {source.evidence_id: _intake_scopes(source) for source in sources} if wanted_intakes else {}
    )
    tables, omitted = [], []
    year_omitted = 0
    intake_omitted = 0
    for table in cells["tables"]:
        kept = selected.get(table["evidence_id"], table["cells"])
        by_year = (
            [cell for cell in kept if _year_kept(cell, year_scopes[table["evidence_id"]], years)]
            if years
            else kept
        )
        narrowed = (
            [
                cell
                for cell in by_year
                if _intake_kept(cell, intake_scopes[table["evidence_id"]], wanted_intakes)
            ]
            if wanted_intakes
            else by_year
        )
        year_omitted += len(kept) - len(by_year)
        intake_omitted += len(by_year) - len(narrowed)
        if table["cells"] and not narrowed:
            omitted.append(table["evidence_id"])
        projected = [dict(cell) for cell in narrowed]
        if len(years) > 1:
            for cell in projected:
                proven = _cell_years(cell, year_scopes[table["evidence_id"]])
                if len(proven) == 1 and proven <= years:
                    cell["data_year"] = next(iter(proven))
        tables.append({**table, "cells": projected})
    continuations = cells.get("list_continuations", [])
    if not years and not wanted_intakes:
        join_continued_lists(tables, continuations)
    else:
        # Under an explicit scope, both fragments must carry their own matching
        # proof. Unknown survives selection but cannot inherit a scope through
        # a synthesized list.
        allowed = {
            cell["cell_id"]
            for table in tables
            for cell in table["cells"]
            if (not years or _cell_years(cell, year_scopes[table["evidence_id"]]) & years)
            and (
                not wanted_intakes
                or _cell_intakes(cell, intake_scopes[table["evidence_id"]]) & wanted_intakes
            )
        }
        join_continued_lists(
            tables, [(left, right) for left, right in continuations if {left, right} <= allowed]
        )
    return {
        **cells,
        "tables": tables,
        "selection": {
            "version": VERSION,
            "basis": "exact_source_subject_and_sealed_table_family",
            "matched_families": matched_families,
            "requested_years": sorted(years),
            "requested_intakes": sorted(intakes or set()),
            "year_omitted_cells": year_omitted,
            "intake_omitted_cells": intake_omitted,
            "available_cells": sum(len(t["cells"]) for t in cells["tables"]),
            "selected_cells": sum(len(t["cells"]) for t in tables),
            "omitted_tables": omitted,
        },
    }
