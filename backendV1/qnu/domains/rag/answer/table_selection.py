"""Project explicitly named rows from a source-bound table family, without guessing."""

import re
import unicodedata

from qnu.domains.rag.answer.selection import question_needs

VERSION = "qnu.rag.table-selection/v1"


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


def select_catalog(cells: dict, sources: list, question: str, links: list[dict]) -> dict:
    """Keep all fields/years/notes for named subjects; uncertain matches keep all rows.

    Families require the same publication and physical table or sealed header
    dependency. A match in another document/table never narrows this family.
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
    omitted = []
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
            if table["cells"] and not kept:
                omitted.append(table["evidence_id"])
    tables = [
        {**table, "cells": selected.get(table["evidence_id"], table["cells"])}
        for table in cells["tables"]
    ]
    return {
        **cells,
        "tables": tables,
        "selection": {
            "version": VERSION,
            "basis": "exact_source_subject_and_sealed_table_family",
            "matched_families": matched_families,
            "available_cells": sum(len(t["cells"]) for t in cells["tables"]),
            "selected_cells": sum(len(t["cells"]) for t in tables),
            "omitted_tables": omitted,
        },
    }
