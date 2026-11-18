"""Closed-list facts computed from packed table fragments; the model only narrates them."""

import re
import unicodedata

from qnu.domains.knowledge.index.schemas import SearchHit
from qnu.domains.knowledge.index.table_layout import header_rows, layout

VERSION = "qnu.rag.closed-set/v1"

_SEGMENT = re.compile(r"[;\n]+")
_PARENTHESES = re.compile(r"\(([^()]*)\)")
_JOIN = re.compile(r"\s*(?:,|và\b|hoặc\b|với\b)\s*")
_MIN_NAME = 6


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split()).casefold()


def _list_groups(text: str) -> list[frozenset[str]]:
    """Unordered named lists; digit-only runs are codes, not option sets."""
    groups = []
    for segment in _SEGMENT.split(text):
        parts = _PARENTHESES.findall(segment) or [segment]
        for part in parts:
            elements = {
                _normalized(piece).strip(" .")
                for piece in part.split(",")
                if any(ch.isalpha() for ch in piece)
            }
            elements.discard("")
            if len(elements) >= 2:
                groups.append(frozenset(elements))
    return groups


def _fragments(sources: list[SearchHit], exclude: set[str]):
    """Valid table fragments and their cell positions; invalid geometry stays out."""
    result = []
    for source in sources:
        structure = source.structure or {}
        if source.kind != "table" or "rows" not in structure:
            continue
        positions, errors = layout(structure)
        if errors or source.evidence_id in exclude:
            continue
        result.append((source, structure, positions))
    return result


def _rows(source: SearchHit, structure: dict, positions) -> list[dict]:
    """One record per data row: display name, list-cell groups and their columns."""
    rows = []
    headers = set(header_rows(structure))
    for number in structure.get("row_indices") or []:
        if number in headers:
            continue
        name, groups = None, {}
        cells = (p for p in positions if p.row == number and p.cell.get("text", "").strip())
        for position in sorted(cells, key=lambda p: p.column):
            text = position.cell["text"]
            lists = _list_groups(text)
            if lists:
                groups.setdefault(position.column, []).extend(lists)
                continue
            display = " ".join(text.split())
            if (
                any(ch.isalpha() for ch in display)
                and len(display) > 1
                and (name is None or len(display) > len(name))
            ):
                name = display
        rows.append({"name": name, "groups": groups, "evidence_id": source.evidence_id})
    return rows


def _families(fragments) -> dict:
    families = {}
    for source, structure, positions in fragments:
        identity = (
            source.document_id,
            source.version_id,
            source.publication_decision_id,
            structure.get("source_table_citation") or "",
        )
        family = families.setdefault(identity, {"columns": {}, "rows": []})
        for row in _rows(source, structure, positions):
            family["rows"].append(row)
            for column, groups in row["groups"].items():
                family["columns"].setdefault(column, set()).update(
                    element for group in groups for element in group
                )
    return families


def _suffix_of(run: tuple[str, ...], other: tuple[str, ...]) -> bool:
    """A run that starts mid-list is the longer list's tail, not a second option set."""
    return len(run) < len(other) and any(
        other[index : index + len(run)] == run for index in range(len(other) - len(run) + 1)
    )


def _option_runs(question: str, vocabulary: set[str]) -> list[tuple[str, ...]]:
    """Greedy unordered-list run of known elements; a truncated run selects nothing."""
    if len(vocabulary) < 2:
        return []
    options = "|".join(re.escape(key) for key in sorted(vocabulary, key=len, reverse=True))
    occurrence = re.compile(r"(?<!\w)(?:" + options + r")(?!\w|[.,]\d)")
    step_pattern = re.compile(r"\s*(" + options + r")(?!\w|[.,]\d)")
    runs, seen = [], set()
    for match in occurrence.finditer(question):
        found, cursor = [], match.start()
        step = step_pattern.match(question, cursor)
        while step:
            found.append(step[1])
            cursor = step.end()
            separator = _JOIN.match(question, cursor)
            step = step_pattern.match(question, separator.end()) if separator else None
        if len(found) < 2:
            continue
        look = question[cursor:].lstrip()
        if look and (look[0].isalnum() or look[0] in ",;_"):
            continue
        key = tuple(found)
        if key not in seen:
            seen.add(key)
            runs.append(key)
    return [run for run in runs if not any(_suffix_of(run, other) for other in runs)]


def _contains(row: dict, option: frozenset[str]) -> bool:
    return any(option <= group for groups in row["groups"].values() for group in groups)


def _subject(question: str, names: set[str]) -> str | None:
    """Longest source row name stated by the question; shorter prefixes never shadow it."""
    best = None
    for name in names:
        if len(name) < _MIN_NAME:
            continue
        if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", question) and (
            best is None or len(name) > len(best)
        ):
            best = name
    return best


def computed_facts(
    question: str,
    sources: list[SearchHit],
    *,
    enumeration_requested: bool = False,
    exclude_evidence_ids: set[str] | None = None,
) -> tuple[dict | None, dict]:
    """Facts from packed evidence only; absence stays scoped to the cited list."""
    exclude = exclude_evidence_ids or set()
    fragments = _fragments(sources, exclude)
    summary = {
        "version": VERSION,
        "status": "no_tables",
        "tables": len(fragments),
        "skipped_selectable": sum(s.evidence_id in exclude for s in sources if s.kind == "table"),
    }
    if not fragments:
        return None, summary
    families = _families(fragments)
    query = _normalized(question)
    names = {
        _normalized(row["name"])
        for family in families.values()
        for row in family["rows"]
        if row["name"]
    }
    subject = _subject(query, names)
    memberships: dict[tuple, dict] = {}
    enumerations: dict[tuple, dict] = {}
    for family in families.values():
        rows = family["rows"]
        named_lists = {_normalized(row["name"]) for row in rows if row["name"] and row["groups"]}
        unknown = {
            _normalized(row["name"]) for row in rows if row["name"] and not row["groups"]
        } - named_lists
        for vocabulary in family["columns"].values():
            for option in _option_runs(query, vocabulary):
                key = tuple(sorted(option))
                requested = frozenset(option)
                matched = [row for row in rows if _contains(row, requested)]
                if subject:
                    _membership(memberships, subject, (key, subject), rows, requested)
                if not enumeration_requested or not matched:
                    continue
                entry = enumerations.setdefault(
                    key,
                    {
                        "option": list(option),
                        "scope": "packed_table_fragments",
                        "matches": {},
                        "unknown_rows": len(unknown),
                    },
                )
                entry["unknown_rows"] = max(entry["unknown_rows"], len(unknown))
                for row in matched:
                    if row["name"] is None:
                        entry["unknown_rows"] += 1
                        continue
                    item = entry["matches"].setdefault(
                        _normalized(row["name"]), {"name": row["name"], "evidence_ids": []}
                    )
                    if row["evidence_id"] not in item["evidence_ids"]:
                        item["evidence_ids"].append(row["evidence_id"])
    facts = {
        "version": VERSION,
        "list_membership": list(memberships.values()),
        "list_enumeration": [
            {**entry, "matches": list(entry["matches"].values())} for entry in enumerations.values()
        ],
    }
    if not facts["list_membership"] and not facts["list_enumeration"]:
        facts = None
    summary.update(
        {
            "status": "computed",
            "families": len(families),
            "subject": subject,
            "memberships": len(facts["list_membership"]) if facts else 0,
            "enumerations": len(facts["list_enumeration"]) if facts else 0,
            "matches": (
                sum(len(entry["matches"]) for entry in facts["list_enumeration"]) if facts else 0
            ),
        }
    )
    return facts, summary


def _membership(
    memberships: dict[tuple, dict],
    subject: str,
    key: tuple,
    rows: list[dict],
    option: frozenset[str],
) -> None:
    """Only absent options leave the scoped negative conclusion to the model."""
    for row in rows:
        if not row["name"] or _normalized(row["name"]) != subject or not row["groups"]:
            continue
        if _contains(row, option):
            continue
        item = memberships.setdefault(
            key,
            {
                "subject": row["name"],
                "option": sorted(option),
                "present": False,
                "scope": "packed_table_fragments",
                "evidence_ids": [],
            },
        )
        if row["evidence_id"] not in item["evidence_ids"]:
            item["evidence_ids"].append(row["evidence_id"])
