"""Source-bound table lookup catalog. Model IDs select; backend copies values."""

import re
import unicodedata

from pydantic import ValidationError

from qnu.domains.knowledge.index.presentation import reading_text
from qnu.domains.knowledge.index.table_layout import header_rows, layout
from qnu.domains.rag.answer.coverage import Requirement
from qnu.domains.rag.answer.narrative import complete_citations
from qnu.domains.rag.answer.schemas import EvidenceSource, ModelAnswer, Statement
from qnu.platform.errors import AppException

VERSION = "qnu.answer-cells/v13"
PROJECTION_VERSION = "qnu.answer-projection/v8"

_YEAR = re.compile(r"^(?:19|20)\d{2}$")
_NUMERIC_CODE = re.compile(r"\d[\dA-Z]*(?:[-./]\d[\dA-Z]*)*")
_PARENTHESIZED_LIST = re.compile(r"(?:\([^()\n]+\)\s*)+")
_ORDINAL = re.compile(r"(?m)(?:^|(?<=[;\n]))\s*\d{1,2}[.)](?=\s)")
# "Bảng 7", "Điều 14" name a document object; the digits are not data.
_STRUCTURAL_REF = re.compile(
    r"(?iu)\b(?:bảng(?:\s+số)?|hình(?:\s+số)?|sơ\s+đồ(?:\s+số)?|biểu\s+đồ(?:\s+số)?|"
    r"phụ\s+lục(?:\s+số)?|điều|khoản|mục|chương|phần|công\s+thức)\s*(?:số\s*)?\d+(?:[.,]\d+)*"
)
# "không đồng nghĩa số 0" denies a meaning; it does not claim a value.
_NEGATED_VALUE = re.compile(
    r"(?iu)\b(?:chứ\s+không|không|chẳng)\s+(?:đồng\s+nghĩa|đồng\s+nhất|có\s+nghĩa|"
    r"được\s+hiểu|được\s+coi|phải|bằng)\b(?:\s+(?:với|là|như))?\s*(?:số|giá\s+trị)?\s*"
    r"\d+(?:[.,]\d+)*"
)
# "CS-02", "TT-2", "AM/TN-02", "NV-16" are identifier codes; the digits name
# a row, they are not a claimed value.
_IDENTIFIER = re.compile(r"(?u)\b[A-ZĐ][A-ZĐ0-9]*(?:/[A-ZĐ0-9]+)*(?:\s*-\s*)\d+\b")
_METRIC_LABELS = (
    "quy mô",
    "chỉ tiêu",
    "ghi nhận",
    "số lượng",
    "mức đạt",
    "tỷ lệ",
    "dự kiến",
    "ước tính",
    "ước đạt",
)


def _same_input(left, right):
    return (left.document_id, left.version_id, left.publication_decision_id) == (
        right.document_id,
        right.version_id,
        right.publication_decision_id,
    )


def _ref(source, position):
    evidence = position.cell.get("evidence_id")
    table = source.structure.get("source_table_citation", "")
    ref = table.split(":", 1)[0] + ":" + str(evidence)
    return ref if evidence and ref in source.citations else None


def catalog(
    sources: list[EvidenceSource],
    links: list[dict] | None = None,
    *,
    include_names: bool = False,
) -> dict:
    """No cross-publication joins or header inference from neighboring text."""
    by_chunk = {s.chunk_id: s for s in sources}
    relationships = {link["chunk_id"]: link for link in links or []}
    support_headers = {key: link for link in links or [] for key in link.get("support_ids", [])}
    # A table family's dependency is proven once per source table. Data fragments
    # added as reading siblings may not carry their own link entry; they still
    # share the same sealed header and must stay selectable through it.
    family_links = {
        link["header"]: link
        for link in links or []
        if link.get("header") and any(key in by_chunk for key in link.get("support_ids", []))
    }
    # A retrieved fragment can establish the header for a sibling of the
    # same physical table added later by contextual reading.
    sibling_headers = {}
    for link in links or []:
        anchor = by_chunk.get(link["chunk_id"])
        if anchor is not None:
            ref = (anchor.structure or {}).get("source_table_citation")
            if ref:
                sibling_headers.setdefault(
                    (anchor.document_id, anchor.version_id, anchor.publication_decision_id, ref),
                    link,
                )
    tables, issues = [], []
    list_continuations = []
    for source in sources:
        structure = source.structure or {}
        if source.kind != "table" or "rows" not in structure:
            continue
        positions, errors = layout(structure)
        if errors:
            issues.append({"evidence_id": source.evidence_id, "issues": errors})
            continue
        headers = header_rows(structure)
        header_source, header_positions = source, positions
        link = relationships.get(source.chunk_id)
        header_link = link or support_headers.get(source.chunk_id)
        if not header_link:
            ref = structure.get("source_table_citation")
            header_link = sibling_headers.get(
                (source.document_id, source.version_id, source.publication_decision_id, ref)
            ) or family_links.get(ref)
        # A proven multi-tier header may be only partially marked in the source
        # fragment. Its dependency already proved every tier; never let partial
        # flags collapse two metric tiers into one ambiguous column path.
        proven = (
            [row for row in header_link.get("header_rows") or [] if type(row) is int]
            if header_link and header_link.get("basis") == "native_multitier_header/v1"
            else []
        )
        if proven and all(row in structure.get("row_indices", []) for row in proven):
            headers = sorted(set(proven))
        if not headers and header_link:
            candidates = [
                by_chunk[key]
                for key in header_link.get("support_ids", [])
                if key in by_chunk
                and _same_input(source, by_chunk[key])
                and (by_chunk[key].structure or {}).get("source_table_citation")
                == header_link["header"]
                and 0 in by_chunk[key].structure.get("row_indices", [])
            ]
            if candidates:
                header_source = candidates[0]
                header_positions, errors = layout(header_source.structure)
                # A proven dependency supplies the header rows the source lacks.
                headers = header_rows(header_source.structure)
                if proven and all(
                    row in header_source.structure.get("row_indices", []) for row in proven
                ):
                    headers = sorted(set(proven))
                if not headers:
                    basis = header_link.get("basis")
                    if basis == "native_multitier_header/v1":
                        headers = list(header_link.get("header_rows") or [])
                    elif basis in {
                        "native_numbered_table_boundary/v1",
                        "native_typed_columns/v1",
                    }:
                        headers = [0]
                if (
                    errors
                    or structure["original_column_count"]
                    != (header_source.structure["original_column_count"])
                ):
                    headers = []
        if not headers:
            issues.append({"evidence_id": source.evidence_id, "issues": ["header_unresolved"]})
            continue
        fields, field_refs = {}, {}
        for c in range(structure["original_column_count"]):
            path = [
                p
                for p in header_positions
                if p.row in headers and p.column <= c < p.column + p.cell["col_span"]
            ]
            if path and all(_ref(header_source, p) for p in path):
                fields[str(c)] = [p.cell["text"] for p in path if p.cell["text"].strip()]
                field_refs[str(c)] = [_ref(header_source, p) for p in path]
        previous = None
        if link and link.get("previous"):
            tails = [
                by_chunk[key]
                for key in link.get("support_ids", [])
                if key in by_chunk
                and _same_input(source, by_chunk[key])
                and (by_chunk[key].structure or {}).get("source_table_citation") == link["previous"]
            ]
            if tails:
                previous = tails[-1]
        entries = []
        for row in structure["row_indices"]:
            if source.chunk_id == header_source.chunk_id and row in headers:
                continue
            body = [p for p in positions if p.row <= row < p.row + p.cell["row_span"]]
            identity = [p for p in body if p.cell["text"].strip()]
            origin = source
            if not identity:
                continue
            # Only a verified carried first row may borrow the preceding row's subject.
            if row == 0 and previous and body and not body[0].cell["text"].strip():
                tail, tail_errors = layout(previous.structure)
                if not tail_errors and tail:
                    last = max(previous.structure["row_indices"])
                    identity = [p for p in tail if p.row <= last < p.row + p.cell["row_span"]]
                    origin = previous
            labels = [
                p
                for p in identity
                if p.cell["text"].strip()
                and any(ch.isalpha() for ch in p.cell["text"])
                and _ref(origin, p)
            ]
            # An identifier split by a line wrap can contain letters, e.g.
            # 120045\nAB. Prefer the following named field as the row label.
            if len(labels) > 1 and _NUMERIC_CODE.fullmatch(
                "".join(labels[0].cell["text"].split())
            ):
                labels = labels[1:]
            # A value without a named subject is ambiguous; never label it with row number.
            if not labels:
                # Numeric lookup keys are subjects too (e.g. a conversion grid).
                # Require a nonempty leading source cell and its resolved header;
                # never manufacture an ordinal for an anonymous row.
                first = identity[0]
                if first.column != 0 or not fields.get("0") or not _ref(origin, first):
                    continue
                labels = [first]
            label = labels[0]
            # Keep the leading textual row path (e.g. group + item/phase) rather
            # than collapsing every child of a row-spanned group to one subject.
            subjects = []
            for candidate in identity[identity.index(label) :]:
                if not candidate.cell["text"].strip():
                    break
                if not any(ch.isalpha() for ch in candidate.cell["text"]):
                    # A numeric identity code under the same header as the leading
                    # label is part of the subject path, not a value; skip it so the
                    # following name is kept (e.g. group / code / program name).
                    if (
                        candidate is not label
                        and fields.get("0")
                        and fields.get(str(candidate.column)) == fields["0"]
                    ):
                        continue
                    break
                if not _ref(origin, candidate):
                    break
                subjects.append(candidate)
            if not subjects:
                subjects = [label]
            for p in body:
                row_subjects = [s for s in subjects if s.column < p.column] or [label]
                field = fields.get(str(p.column))
                ref = _ref(source, p)
                row_name = include_names and origin is source and p == label and any(
                    ch.isalpha() for ch in p.cell["text"]
                )
                if (
                    not field or not ref or not p.cell["text"].strip() or (p == label and not row_name)
                ):
                    continue
                # A merged data cell is addressable only if every covered column has
                # exactly the same header path; otherwise its field is ambiguous.
                if any(
                    fields.get(str(c)) != field
                    for c in range(p.column, p.column + p.cell["col_span"])
                ):
                    continue
                ids = list(
                    dict.fromkeys(
                        [source.evidence_id, header_source.evidence_id, origin.evidence_id]
                    )
                )
                entries.append(
                    {
                        # Physical columns remain unique when a preceding row's
                        # spanning cell and a new cell share the same list index.
                        "cell_id": f"{source.evidence_id}:r{row}:k{p.column}",
                        "subject": " / ".join(
                            s.cell["text"]
                            if any(ch.isalpha() for ch in s.cell["text"])
                            else " / ".join(fields[str(s.column)]) + ": " + s.cell["text"]
                            for s in row_subjects
                        ),
                        "subject_labels": [s.cell["text"] for s in row_subjects],
                        "column": p.column,
                        "value": p.cell["text"],
                        **({"row_name": True} if row_name else {}),
                        "evidence_ids": ids,
                        "source_cells": list(
                            dict.fromkeys(
                                [
                                    ref,
                                    *[_ref(origin, s) for s in row_subjects],
                                    *[
                                        ref
                                        for s in row_subjects
                                        for ref in field_refs.get(str(s.column), [])
                                    ],
                                    *field_refs[str(p.column)],
                                ]
                            )
                        ),
                    }
                )
                if row == 0 and previous is not None and origin is previous:
                    previous_row = max(previous.structure["row_indices"])
                    list_continuations.append(
                        (
                            f"{previous.evidence_id}:r{previous_row}:k{p.column}",
                            f"{source.evidence_id}:r{row}:k{p.column}",
                        )
                    )
        tables.append({"evidence_id": source.evidence_id, "fields": fields, "cells": entries})
    return {
        "version": VERSION,
        "tables": tables,
        "issues": issues,
        "list_continuations": list_continuations,
    }


def join_continued_lists(tables: list[dict], continuations: list[tuple[str, str]]) -> None:
    """Keep proven fragments whole only when both survived scope filtering."""
    by_id = {cell["cell_id"]: cell for table in tables for cell in table["cells"]}
    for left_id, right_id in continuations:
        left, right = by_id.get(left_id), by_id.get(right_id)
        if (
            not left or not right
            or left["subject_labels"] != right["subject_labels"]
            or not all(_PARENTHESIZED_LIST.fullmatch(c["value"].strip()) for c in (left, right))
        ):
            continue
        joined = {
            "value": left["value"].rstrip() + "\n" + right["value"].lstrip(),
            "evidence_ids": list(dict.fromkeys(left["evidence_ids"] + right["evidence_ids"])),
            "source_cells": list(dict.fromkeys(left["source_cells"] + right["source_cells"])),
            "joined_list_id": left_id,
        }
        left.update(joined)
        right.update(joined)


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)*", text))


def _visible_text(source: EvidenceSource) -> str:
    """Exactly what the prompt packed for this source; no re-derivation."""
    if source.kind == "table":
        return reading_text(source)
    passages = source.source_passages
    return "\n".join(p["text"] for p in passages) if passages else reading_text(source)


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def _statement_numbers(text: str) -> set[str]:
    """List ordinals, document objects, code names and negated meanings are not facts."""
    said = unicodedata.normalize("NFC", text)
    said = _NEGATED_VALUE.sub(" ", said)
    said = _IDENTIFIER.sub(" ", said)
    return _numbers(_ORDINAL.sub(" ", _STRUCTURAL_REF.sub(" ", said)))


def _fields(structure: dict, positions: list) -> dict[int, list[str]]:
    """Column paths from explicit leading header rows only."""
    headers = set(header_rows(structure))
    fields = {}
    if not headers:
        return fields
    for column in range(structure["original_column_count"]):
        path = [
            p
            for p in positions
            if p.row in headers and p.column <= column < p.column + p.cell["col_span"]
        ]
        if path and all(p.cell["text"].strip() for p in path):
            fields[column] = [p.cell["text"] for p in path]
    return fields


def _row_facts(source: EvidenceSource) -> list[dict]:
    """Canonical rows with explicit labels, numeric cells and column paths."""
    structure = source.structure or {}
    positions, errors = layout(structure)
    if errors:
        return []
    fields = _fields(structure, positions)
    facts = []
    for row in structure.get("row_indices", []):
        body = [p for p in positions if p.row <= row < p.row + p.cell["row_span"]]
        filled = [p for p in body if p.cell["text"].strip()]
        labels = [p for p in filled if any(ch.isalpha() for ch in p.cell["text"])]
        numeric = [p for p in filled if _numbers(p.cell["text"])]
        facts.append(
            {
                "labels": [(p, _normalized(p.cell["text"])) for p in labels],
                "numeric": numeric,
                # Header marks can be partial after OCR review; any mark keeps
                # the row out of numeric proof instead of leaking a header value.
                "header_like": any(p.cell.get("header") for p in filled)
                or not labels
                or not numeric,
                "fields": fields,
            }
        )
    return facts


def _claim_binds(
    year: str | None,
    metric: str | None,
    col_years: set[str],
    col_metrics: set[str],
    said_years: set[str],
    said_metrics: set[str],
) -> bool:
    """Whether one value's own clause label can prove this column.

    A value with a local label must match the column's year/metric. A value
    without one may still bind through the statement's labels (the older
    conservative check), never against them. Unknown columns stay open.
    """
    if year is not None:
        if col_years and year not in col_years:
            return False
    elif col_years and said_years and not col_years & said_years:
        return False
    if metric is not None:
        if col_metrics and metric not in col_metrics:
            return False
    elif col_metrics and said_metrics and not col_metrics & said_metrics:
        return False
    return True


def _column_texts(fact: dict, source: EvidenceSource) -> dict[int, str]:
    """Column → label text from a header-like first row, without marks.

    Used as a fallback when _fields returns empty (no header marks). Only a
    label row (years and metric names, no other numbers) may name its
    columns; a data row's digits are values, not column labels.
    """
    structure = source.structure or {}
    positions, errors = layout(structure)
    if errors:
        return {}
    first_row = min(structure.get("row_indices", [0])) if structure.get("row_indices") else 0
    first = [p for p in positions if p.row == first_row and p.cell["text"].strip()]
    for p in first:
        text = _normalized(p.cell["text"])
        year = any(_YEAR.match(number) for number in _numbers(text))
        metric = any(label in text for label in _METRIC_LABELS)
        if re.search(r"\d", text) and not year and not metric:
            return {}
    texts = {}
    for p in first:
        for c in range(p.column, p.column + p.cell["col_span"]):
            texts[c] = _normalized(p.cell["text"])
    return texts


def _column_year(col_texts: dict[int, str], column: int) -> str | None:
    """Extract a year label from the column's header text, if any."""
    text = col_texts.get(column, "")
    for number in _numbers(text):
        if _YEAR.match(number):
            return number
    return None


def _column_metric(col_texts: dict[int, str], column: int) -> str | None:
    """Extract a metric label from the column's header text, if any."""
    text = col_texts.get(column, "")
    for label in _METRIC_LABELS:
        if label in text:
            return label
    return None


def _table_numbers(source: EvidenceSource) -> set[str]:
    """All numeric values present in the table source's cells."""
    result = set()
    for fact in _row_facts(source):
        for position in fact["numeric"]:
            result |= _numbers(position.cell["text"])
    return result


def _mentions_subject(source: EvidenceSource, statement: str) -> bool:
    """Whether the statement names at least one data row of this table.

    A table binds values only through a named subject row. Without one it
    has no attribution to defend, so its digit set must not suppress a
    cited passage that itself carries the number.
    """
    said = _normalized(statement)
    for fact in _row_facts(source):
        if fact["header_like"]:
            continue
        for _, label in fact["labels"]:
            if len(label) >= 3 and label in said:
                return True
    return False


def _clause_claims(text: str) -> list[tuple[str, str | None, str | None]]:
    """Each numeric token with the year and metric label it belongs to.

    A clause's own label binds its values: "năm 2025 là 22, năm 2026 là 18"
    claims 22 for 2025 and 18 for 2026, even though both years and both
    numbers occur in one statement. A value without a preceding label in its
    clause takes the next label inside the clause; labels in other clauses
    never apply. Decimal commas ("93,3") belong to the number, not a split.
    A year token claims itself so a date cell ("30/11/2026") stays whole.
    """
    claims = []
    for clause in re.split(r"[;:]|,(?!\d)", text):
        said = _normalized(clause)
        years = [
            (match.start(), match.group())
            for match in re.finditer(r"\d+(?:[.,]\d+)*", said)
            if _YEAR.match(match.group())
        ]
        metrics = [
            (start, label) for label in _METRIC_LABELS for start in _occurrences(said, label)
        ]
        for match in re.finditer(r"\d+(?:[.,]\d+)*", said):
            token = match.group()
            year = token if _YEAR.match(token) else _nearest_label(years, match.start())
            metric = _nearest_label(metrics, match.start())
            claims.append((token, year, metric))
    return claims


def _occurrences(text: str, needle: str) -> list[int]:
    starts, start = [], text.find(needle)
    while start != -1:
        starts.append(start)
        start = text.find(needle, start + len(needle))
    return starts


def _nearest_label(labels: list[tuple[int, str]], position: int) -> str | None:
    before = [label for start, label in labels if start < position]
    if before:
        return before[-1]
    after = [label for start, label in labels if start > position]
    return after[0] if after else None


def _subject_segments(
    statement: str, facts: list[dict]
) -> dict[str, list[tuple[str, str | None, str | None]]]:
    """Map each matched subject label to the claimed numbers near it.

    Splits the statement by subject mentions: each segment starts at a
    subject label and ends at the next subject label (or end of text).
    Numbers inside a segment are attributed to that segment's subject and
    keep their own year/metric binding. Years alone are column scope.
    """
    said = _normalized(statement)
    # Collect matched labels sorted by their position in the statement.
    matches = []
    for fact in facts:
        if fact["header_like"]:
            continue
        for position, label in fact["labels"]:
            if len(label) >= 3 and label in said:
                idx = said.index(label)
                matches.append((idx, label, position))
    if not matches:
        return {}
    matches.sort(key=lambda m: m[0])
    segments: dict[str, list[tuple[str, str | None, str | None]]] = {}
    for i, (idx, label, position) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(said)
        claims = _clause_claims(said[idx:end])
        segments[label] = claims
    return segments


def _table_support(source: EvidenceSource, statement: str) -> set[str]:
    """Numbers proven by the claimed row and its resolved column path.

    A co-cited table is not one bag of digits: a value under another subject,
    under another header tier, or inside a partially marked header row is not
    proof. Years are column scope and may come from a cited header cell.

    Each claimed number must appear as a cell value on a row whose subject
    is mentioned in the statement near that number. If multiple subjects are
    mentioned, numbers are attributed to the nearest preceding subject.
    """
    said = _normalized(statement)
    tokens = _statement_numbers(statement)
    facts = _row_facts(source)
    supported = set()
    # Year-only tokens that appear as header cell values are column scope.
    year_tokens = {t for t in tokens if _YEAR.match(t)}
    if year_tokens:
        for fact in facts:
            for position in fact["numeric"]:
                numbers = _numbers(position.cell["text"])
                if numbers and numbers <= year_tokens:
                    supported |= numbers
    # Build subject→claimed-values segments, each value keeping its own
    # year/metric label from the clause it stands in.
    segments = _subject_segments(statement, facts)
    all_claims = [claim for claims in segments.values() for claim in claims]
    said_years = {n for n in _numbers(said) if _YEAR.match(n)}
    said_metrics = {label for label in _METRIC_LABELS if label in said}
    for fact in facts:
        if fact["header_like"]:
            # Header rows may still contribute label numbers (rare), but
            # not value claims.
            for position, label in fact["labels"]:
                if len(label) >= 3 and label in said:
                    supported |= _numbers(position.cell["text"])
            continue
        matched = [
            position for position, label in fact["labels"] if len(label) >= 3 and label in said
        ]
        # Label cells on matched rows: their own numbers are part of the
        # subject identity, not claimed values (e.g. a program code "0012").
        label_numbers = set()
        if matched:
            for position, label in fact["labels"]:
                if position in matched or (len(label) >= 3 and label in said):
                    label_numbers |= _numbers(position.cell["text"])
        if not matched:
            continue
        claims = []
        for position, label in fact["labels"]:
            if len(label) >= 3 and label in said:
                claims.extend(segments.get(label, []))
        # If no segment numbers were found (e.g. single subject, all numbers
        # in one segment), fall back to the statement's own claims.
        if not claims and len(segments) <= 1:
            claims = all_claims or _clause_claims(said)
        claimed_tokens = {token for token, _, _ in claims}
        for position in fact["numeric"]:
            numbers = _numbers(position.cell["text"])
            if not numbers:
                continue
            # Numbers that are part of the subject label itself (e.g. "01" in
            # "NV-01") are supported because the subject is mentioned, but they
            # are not value claims and must not be subject to column checks.
            if numbers <= label_numbers:
                supported |= numbers & tokens
                continue
            # The number must be claimed for this subject's segment.
            if claims and not numbers <= claimed_tokens:
                continue
            # The number must appear in the statement tokens at all.
            if not numbers <= tokens:
                continue
            field = fact["fields"].get(position.column)
            if field:
                path = _normalized(" / ".join(field))
                col_years = {n for n in _numbers(path) if _YEAR.match(n)}
                col_metrics = {label for label in _METRIC_LABELS if label in path}
            else:
                # Without resolved fields, only a header-like first row names
                # its columns; a data row's digits are never column labels.
                col_texts = _column_texts(fact, source)
                col_year = _column_year(col_texts, position.column)
                col_metric = _column_metric(col_texts, position.column)
                col_years = {col_year} if col_year else set()
                col_metrics = {col_metric} if col_metric else set()
            # Each claimed value must match its own clause label against the
            # value's column. A label elsewhere in the statement cannot
            # license the swapped value.
            if claims:
                bound = True
                for token in numbers:
                    options = [
                        (claim_year, claim_metric)
                        for claim_token, claim_year, claim_metric in claims
                        if claim_token == token
                    ]
                    if not any(
                        _claim_binds(
                            year,
                            metric,
                            col_years,
                            col_metrics,
                            said_years,
                            said_metrics,
                        )
                        for year, metric in options
                    ):
                        bound = False
                        break
                if not bound:
                    continue
            supported |= numbers
    return supported


def _unsupported_numbers(
    answer: ModelAnswer, sources: list[EvidenceSource], unselectable: set[str]
) -> list[dict]:
    """Per-statement missing numbers, keeping grounded statements intact.

    When a statement cites both a table and a passage, numbers that appear
    in the table must be verified through the table's per-fact binding.
    A passage mentioning the same number cannot override the table's
    column/subject attribution.
    """
    by_id = {s.evidence_id: s for s in sources}
    dropped = []
    for index, statement in enumerate(answer.statements):
        if not unselectable.intersection(statement.evidence_ids):
            continue
        numbers = _statement_numbers(statement.text)
        if not numbers:
            continue
        table_ids = [
            eid
            for eid in statement.evidence_ids
            if by_id[eid].kind == "table" and eid in unselectable
        ]
        passage_ids = [eid for eid in statement.evidence_ids if by_id[eid].kind != "table"]
        supported = set()
        # Collect all numbers that appear in cited tables. A table the
        # statement attributes no row to cannot verify or suppress anything:
        # its digits prove no subject binding, and blocking passage support
        # there only drops evidence the passage itself carries.
        table_all_numbers: set[str] = set()
        for eid in table_ids:
            if _mentions_subject(by_id[eid], statement.text):
                table_all_numbers |= _table_numbers(by_id[eid])
        # Table-sourced numbers must pass per-fact verification.
        for eid in table_ids:
            supported |= _table_support(by_id[eid], statement.text)
        # Passage numbers only support numbers NOT present in any cited table.
        # If a number appears in a table, the passage cannot override the
        # table's column binding.
        for eid in passage_ids:
            passage_numbers = _numbers(_visible_text(by_id[eid]))
            supported |= passage_numbers - table_all_numbers
        missing = numbers - supported
        if missing:
            dropped.append({"index": index, "numbers": sorted(missing)})
    return dropped


def materialize(
    answer: ModelAnswer,
    sources: list[EvidenceSource],
    cells: dict,
    *,
    report: dict | None = None,
) -> ModelAnswer:
    allowed = {
        cell["cell_id"]: (table, cell) for table in cells["tables"] for cell in table["cells"]
    }
    selected, rejected, seen = [], [], set()
    for index, item in enumerate(answer.lookups):
        key = item.cell_id
        if key in seen:
            rejected.append({"path": ["lookups", index, "cell_id"], "type": "duplicate"})
        elif key not in allowed:
            rejected.append({"path": ["lookups", index, "cell_id"], "type": "not_in_catalog"})
        else:
            selected.append(key)
        seen.add(key)
    if rejected:
        if report is not None:
            report["rejected_lookups"] = rejected
        # One malformed identifier must not discard the valid cells beside it;
        # a lookup set with no valid cell still fails the whole answer.
        if not selected:
            error = AppException(
                "Ô được chọn không thuộc bằng chứng.",
                code="answer_cell_invalid",
                status_code=502,
                title="Ô bảng mô hình chọn không hợp lệ",
            )
            error.validation_issues = rejected[:20]
            raise error
    structured = {s.evidence_id for s in sources if s.kind == "table"}
    selectable = {t["evidence_id"] for t in cells["tables"] if t["cells"]}
    # Selectable tables keep the cell-selection contract. Unselectable tables have
    # no catalog cells, so their values may only be copied verbatim into prose.
    if not selected and any(
        re.search(r"\d", s.text) and selectable.intersection(s.evidence_ids)
        for s in answer.statements
    ):
        error = AppException(
            "Dữ kiện số trong bảng phải chọn bằng định danh ô.",
            code="answer_cell_selection_required",
            status_code=502,
            title="Ô bảng mô hình chọn không hợp lệ",
        )
        error.validation_issues = [{"path": ["lookups"], "type": "table_value_requires_cell"}]
        raise error
    unselectable = structured - selectable
    dropped = _unsupported_numbers(answer, sources, unselectable)
    if dropped and not selected and len(dropped) == len(answer.statements):
        error = AppException(
            "Số trong câu trả lời không có trong nguồn được dẫn.",
            code="answer_table_value_not_extractive",
            status_code=502,
            title="Giá trị bảng không trích từ nguồn",
        )
        error.validation_issues = [
            {"path": ["statements", item["index"], "text"], "type": "number_not_in_cited_source"}
            for item in dropped
        ][:20]
        raise error
    dropped_numbers = list(dict.fromkeys(number for item in dropped for number in item["numbers"]))
    if dropped_numbers:
        if report is not None:
            report["dropped_statements"] = dropped
            report["dropped_numbers"] = dropped_numbers
        assessment = list(answer.assessment)
        if len(assessment) < 20:
            assessment.append(
                Requirement(
                    label=(
                        "Không xác minh được dữ kiện số trong nguồn đã dẫn: "
                        + ", ".join(dropped_numbers)
                    )[:500],
                    status="missing",
                    evidence_ids=[],
                )
            )
        answer = answer.model_copy(update={"assessment": assessment})
    dropped_indexes = {item["index"] for item in dropped}
    statements = [
        s.model_copy(deep=True)
        for index, s in enumerate(answer.statements)
        if index not in dropped_indexes
        and (not selected or not selectable.intersection(s.evidence_ids))
    ]
    complete_citations(statements, sources)
    emitted_names, emitted_lists = set(), set()
    by_evidence = {source.evidence_id: source for source in sources}
    for key in selected:
        table, cell = allowed[key]
        if cell.get("row_name"):
            source = by_evidence[table["evidence_id"]]
            name_key = (
                source.document_id,
                source.version_id,
                source.publication_decision_id,
                _normalized(cell["value"]),
            )
            if name_key in emitted_names:
                continue
            emitted_names.add(name_key)
        if list_id := cell.get("joined_list_id"):
            if list_id in emitted_lists:
                continue
            emitted_lists.add(list_id)
        field = " / ".join(table["fields"][str(cell["column"])])
        year = cell.get("data_year")
        if year is not None and str(year) not in _numbers(field):
            field = f"Năm {year} / {field}"
        text = (
            " ".join(cell["value"].split())
            if cell.get("row_name")
            else f"{cell['subject']} — {field}: {cell['value']}"
        )
        try:
            statements.append(
                Statement(
                    text=text,
                    evidence_ids=cell["evidence_ids"],
                )
            )
        except ValidationError as exc:
            error = AppException(
                "Ô nguồn không thể hiển thị dưới dạng text thuần.",
                code="answer_source_text_invalid",
                status_code=502,
                title="Ô bảng mô hình chọn không hợp lệ",
            )
            error.validation_issues = [{"path": ["lookups"], "type": "source_cell_not_displayable"}]
            raise error from exc
    if len(statements) > 20:
        error = AppException(
            "Quá nhiều ý trong câu trả lời.",
            code="answer_response_invalid",
            status_code=502,
            title="Phản hồi mô hình không hợp lệ",
        )
        error.validation_issues = [{"path": ["statements"], "type": "too_many_statements"}]
        raise error
    return ModelAnswer(
        status=answer.status,
        statements=statements,
        assessment=answer.assessment,
        message=answer.message,
    )


def prompt_catalog(cells: dict) -> dict:
    """Expose exact lookup IDs beside values while keeping provenance server-side."""
    tables, unselectable = [], []
    omitted = set(cells.get("selection", {}).get("omitted_tables", []))
    for table in cells["tables"]:
        if not table["cells"]:
            if table["evidence_id"] not in omitted:
                unselectable.append(table["evidence_id"])
            continue
        rows, order = {}, []
        for cell in table["cells"]:
            _, row, _ = cell["cell_id"].rsplit(":", 2)
            if row not in rows:
                rows[row] = {"row": row, "subject": cell["subject"], "cells": {}}
                order.append(row)
            elif len(cell["subject"]) > len(rows[row]["subject"]):
                rows[row]["subject"] = cell["subject"]
            if cell.get("row_name"):
                rows[row]["name_id"] = cell["cell_id"]
            else:
                rows[row]["cells"][cell["cell_id"]] = cell["value"]
        columns = {f"k{column}": " / ".join(path) for column, path in table["fields"].items()}
        years = {cell.get("data_year") for cell in table["cells"] if not cell.get("row_name")}
        tables.append(
            {
                "id": table["evidence_id"],
                **({"data_year": next(iter(years))} if len(years) == 1 and None not in years else {}),
                "columns": columns,
                "rows": [
                    {
                        "row": rows[row]["row"],
                        "subject": rows[row]["subject"],
                        "cells": rows[row]["cells"],
                        **(
                            {"name_id": rows[row]["name_id"]} if "name_id" in rows[row] else {}
                        ),
                    }
                    for row in order
                ],
            }
        )
    unselectable.extend(issue["evidence_id"] for issue in cells["issues"])
    return {"tables": tables, "unselectable": list(dict.fromkeys(unselectable))}
