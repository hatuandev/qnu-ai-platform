"""Source-bound table lookup catalog. Model IDs select; backend copies values."""

import re

from pydantic import ValidationError

from qnu.domains.knowledge.index.table_layout import header_rows, layout
from qnu.domains.rag.answer.narrative import complete_citations
from qnu.domains.rag.answer.schemas import EvidenceSource, ModelAnswer, Statement
from qnu.platform.errors import AppException

VERSION = "qnu.answer-cells/v3"
PROJECTION_VERSION = "qnu.answer-projection/v3"


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


def catalog(sources: list[EvidenceSource], links: list[dict] | None = None) -> dict:
    """No cross-publication joins or header inference from neighboring text."""
    by_chunk = {s.chunk_id: s for s in sources}
    relationships = {link["chunk_id"]: link for link in links or []}
    support_headers = {key: link for link in links or [] for key in link.get("support_ids", [])}
    tables, issues = [], []
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
                # Legacy native dependency proof verifies a single unmarked header row.
                headers = header_rows(header_source.structure) or (
                    [0]
                    if header_link.get("basis")
                    in {"native_numbered_table_boundary/v1", "native_typed_columns/v1"}
                    else []
                )
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
                if not candidate.cell["text"].strip() or not any(
                    ch.isalpha() for ch in candidate.cell["text"]
                ):
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
                if not field or not ref or not p.cell["text"].strip() or p == label:
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
                        "column": p.column,
                        "value": p.cell["text"],
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
        tables.append({"evidence_id": source.evidence_id, "fields": fields, "cells": entries})
    return {"version": VERSION, "tables": tables, "issues": issues}


def materialize(answer: ModelAnswer, sources: list[EvidenceSource], cells: dict) -> ModelAnswer:
    allowed = {
        cell["cell_id"]: (table, cell) for table in cells["tables"] for cell in table["cells"]
    }
    selected = [item.cell_id for item in answer.lookups]
    if len(set(selected)) != len(selected) or any(key not in allowed for key in selected):
        raise AppException(
            "Ô được chọn không thuộc bằng chứng.", code="answer_cell_invalid", status_code=502
        )
    structured = {s.evidence_id for s in sources if s.kind == "table"}
    # Table values remain extractive. Paragraph prose retains the same citation
    # contract as narrative-only answers; table prose is never another authority.
    if not selected and any(
        re.search(r"\d", s.text) and structured.intersection(s.evidence_ids)
        for s in answer.statements
    ):
        raise AppException(
            "Dữ kiện số trong bảng phải chọn bằng định danh ô.",
            code="answer_cell_selection_required",
            status_code=502,
        )
    statements = [
        s.model_copy(deep=True)
        for s in answer.statements
        if not selected or not structured.intersection(s.evidence_ids)
    ]
    complete_citations(statements, sources)
    for key in selected:
        table, cell = allowed[key]
        field = " / ".join(table["fields"][str(cell["column"])])
        try:
            statements.append(
                Statement(
                    text=f"{cell['subject']} — {field}: {cell['value']}",
                    evidence_ids=cell["evidence_ids"],
                )
            )
        except ValidationError as exc:
            raise AppException(
                "Ô nguồn không thể hiển thị dưới dạng text thuần.",
                code="answer_source_text_invalid",
                status_code=502,
            ) from exc
    if len(statements) > 20:
        raise AppException(
            "Quá nhiều ý trong câu trả lời.", code="answer_response_invalid", status_code=502
        )
    return ModelAnswer(status=answer.status, statements=statements, assessment=answer.assessment)


def prompt_catalog(cells: dict) -> dict:
    """Share row subjects/headers; keep full cell provenance in the server catalog."""
    tables = []
    for table in cells["tables"]:
        rows = {}
        for cell in table["cells"]:
            _, row, key = cell["cell_id"].split(":")
            if row in rows and len(cell["subject"]) > len(rows[row]["subject"]):
                rows[row]["subject"] = cell["subject"]
            rows.setdefault(row, {"subject": cell["subject"], "values": {}})["values"][key] = [
                cell["column"],
                cell["value"],
            ]
        tables.append(
            {"evidence_id": table["evidence_id"], "fields": table["fields"], "rows": rows}
        )
    return {"version": VERSION, "tables": tables, "issues": cells["issues"]}
