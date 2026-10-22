"""Server-owned cell coordinates and exact citations for published source rows."""

import html
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from pydantic import Field

from app.core.exceptions import AppException
from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.normalization.qnu_markdown import QNU_CELL_STATES
from app.modules.knowledge.normalization.retrieval_models import SourceUnit
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.source_artifact import cell_context
from app.modules.knowledge.services.table_context import extract_context_tables, row_identities
from app.modules.rag.evidence_dependencies import dependency_groups, sentence_continuations
from app.modules.rag.evidence_schemas import EvidenceBlock, QuoteReference, StrictContract
from app.modules.rag.evidence_validation import bind_quote
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import RetrievalSnapshot
from app.modules.rag.source_labels import row_identity


class RowSelection(StrictContract):
    status: Literal["selected", "missing", "conflict", "not_applicable"]
    cell_ids: list[str] = Field(default_factory=list, max_length=60)
    scope_ids: list[str] = Field(default_factory=list, max_length=20)
    note_ids: list[str] = Field(default_factory=list, max_length=40)
    missing_constraints: list[str] = Field(default_factory=list, max_length=8)


class MetricScope(StrictContract):
    context_ids: list[str] = Field(default_factory=list, max_length=12)
    answer_mode: Literal['cells', 'rules'] = 'cells'


class RowAudit(StrictContract):
    compatible: bool
    scope_supported: bool
    complete: bool
    conflict: bool = False
    required_cell_ids: list[str] = Field(default_factory=list, max_length=60)
    required_context_ids: list[str] = Field(default_factory=list, max_length=40)
    missing_constraints: list[str] = Field(default_factory=list, max_length=8)


@dataclass
class SourceCell:
    row_id: str
    entity: str
    header: str
    value: str
    references: list[dict]
    state: str = "legacy"
    normalized: object | None = None
    field_source: dict | None = None
    field_origin: dict | None = None
    column_id: str | None = None
    header_path: list[str] | None = None
    temporal: dict | None = None
    standard: bool = False
    state_source: str = "legacy"
    description_only: bool = False


@dataclass
class RowCatalog:
    cells: dict[str, SourceCell] = field(default_factory=dict)
    contexts: dict[str, EvidenceBlock] = field(default_factory=dict)
    rows: dict[str, dict] = field(default_factory=dict)

    def payload(self) -> dict:
        def passage(key: str) -> dict:
            block = self.contexts[key]
            return {"id": key, "text": block.text, "page": block.page_number}
        return {"tables": [{"id": row["id"], "entity": row["entity"], "title": row["title"],
            "source_revision_id": row["source_revision_id"], "cells": row["cells"],
            "scope_context": [passage(key) for key in row["scope_candidates"]],
            "notes": [passage(key) for key in row["note_candidates"]]}
            for row in self.rows.values()]}


def _block(row: FusionCandidate, unit: SourceUnit, key: str) -> EvidenceBlock:
    meta = row.metadata
    return EvidenceBlock(id=key, binding_id=row.binding_id, index_revision_id=row.index_revision_id,
        source_revision_id=meta["source_revision_id"], canonical_hash=meta["canonical_hash"],
        title=meta["document_title"], text=unit.text, start=unit.start, end=unit.end,
        page_number=unit.page_number, temporal_scope=unit.temporal, unit_id=unit.id,
        fact_context={"source_kind": unit.kind, "source_locations": unit.source_locations})


def _reference(block: EvidenceBlock) -> dict:
    return bind_quote(QuoteReference(block_id=block.id, quote=block.text), {block.id: block})


def _display(text: str) -> str:
    return html.escape(re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _same_cell(raw: str, parsed: str) -> bool:
    canonical = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE).replace("\r\n", "\n")
    return canonical.strip() == parsed.strip()


def _standard_fields(row: FusionCandidate, headers: list[str], values: list[str], *,
                     allow_descriptive: bool = False) -> list[dict] | None:
    """Exact declared cell metadata, or None for artifacts published without it."""
    fields, columns = row.metadata.get("row_fields"), row.metadata.get("row_columns")
    if not isinstance(fields, list) or not isinstance(columns, list):
        return None
    if len(fields) != len(values) or len(columns) != len(values):
        raise ValueError("Standard row fields do not match its emitted cells")
    state_source = row.metadata.get("cell_state_source") or "legacy"
    usage = SourceUnit.model_validate(row.metadata["source_unit"]).field_usage
    for column, (cell_field, label, value) in enumerate(zip(fields, headers, values, strict=True)):
        if not isinstance(cell_field, dict) or not isinstance(cell_field.get("raw"), str) or not _same_cell(cell_field["raw"], value):
            raise ValueError("Standard row field disagrees with its canonical cell")
        if cell_field.get("column_index") is not None and cell_field["column_index"] != column:
            raise ValueError("Standard row field coordinates disagree")
        path = columns[column].get("header_path") if isinstance(columns[column], dict) else None
        if path and " / ".join(path) != label:
            raise ValueError("Standard row header disagrees with its column path")
        if cell_field.get("state") not in QNU_CELL_STATES:
            raise ValueError("Standard row cell state is unavailable")
        if not allow_descriptive:
            if cell_field.get("usage") == "description_only" or usage.get(cell_field.get("column_id")) == "description_only":
                raise ValueError("Source limitation is not answer-bearing quantitative evidence")
            if (cell_field.get("state_source", state_source) == "declared"
                    and cell_field.get("state") in {"ambiguous", "unreadable"}):
                raise ValueError("Unresolved standard cell cannot answer")
    return fields


def _cell_payload(key: str, cell: SourceCell) -> dict:
    payload = {"id": key, "header": cell.header, "value": cell.value,
               "state": cell.state, "standard": cell.standard, "state_source": cell.state_source,
               "description_only": cell.description_only}
    if cell.standard:
        payload.update(column_id=cell.column_id, header_path=cell.header_path, normalized=cell.normalized,
                       field_source=cell.field_source, field_origin=cell.field_origin, temporal=cell.temporal)
    return payload


def _add_row(catalog: RowCatalog, row: FusionCandidate, index: int, question: str = '', *,
             allow_descriptive: bool = False) -> None:
    unit = SourceUnit.model_validate(row.metadata["source_unit"])
    tables = extract_context_tables(unit.header_context + "\n" + unit.text, 1)
    if len(tables) != 1 or len(tables[0]["rows"]) != 1:
        return  # Unresolved matrix is not a cell-answer candidate.
    table = tables[0]
    values = _split_gfm_row(unit.text)
    identities = row_identities(values, table)
    if question:
        matched = row_identity(values, table, question)
        identities = [matched] if matched else []
    if len(identities) != 1 or len(values) != len(table["headers"]):
        return
    identity, _, entity, entity_code = identities[0]
    headers = [SourceUnit.model_validate(header) for header in row.metadata.get("row_headers", [])]
    if not headers or any(header.text != unit.header_context for header in headers):
        return  # No invented offsets or header citations when provenance is absent.
    row_id = f"r{index}"
    body = _block(row, unit, row_id)
    contexts = [*headers, *[SourceUnit.model_validate(item["source_unit"]) for item in row.metadata["row_context"]]]
    context_ids = []
    for position, context in enumerate(contexts):
        key = f"{row_id}p{position}"
        catalog.contexts[key] = _block(row, context, key)
        context_ids.append(key)
    refs = [_reference(body), _reference(catalog.contexts[context_ids[0]])]
    standard_fields = _standard_fields(row, table["headers"], values, allow_descriptive=allow_descriptive)
    state_source = row.metadata.get("cell_state_source") or "legacy"
    cells = []
    for column, (label, value) in enumerate(zip(table["headers"], values, strict=True)):
        if column == identity or detect_column_role(label)[0] == "code" or column < identity:
            continue
        key = f"{row_id}c{column}"
        field = standard_fields[column] if standard_fields else None
        temporal = (field.get("temporal") or field.get("header_temporal")) if field else None
        cell = SourceCell(row_id, entity,
            " / ".join(field.get("header_path") or [label]) if field else label,
            field["raw"] if field else value, refs,
            state=field["state"] if field else "legacy", normalized=field.get("normalized") if field else None,
            field_source=field.get("field_source") if field else None,
            field_origin=field.get("field_origin") if field else None,
            column_id=field.get("column_id") if field else None,
            header_path=field.get("header_path") if field else None,
            temporal=temporal, standard=bool(field),
            state_source=field.get("state_source", state_source) if field else state_source,
            description_only=bool(field and (field.get("usage") == "description_only"
                or unit.field_usage.get(field.get("column_id")) == "description_only")))
        catalog.cells[key] = cell
        cells.append(_cell_payload(key, cell))
    if cells:
        catalog.rows[row_id] = {"id": row_id, "entity": entity, "entity_code": entity_code, "title": body.title,
            "source_revision_id": body.source_revision_id, "cells": cells, "context_ids": context_ids,
            "scope_candidates": [key for key in context_ids if catalog.contexts[key].start < unit.start],
            "note_candidates": [key for key in context_ids if catalog.contexts[key].start > unit.start]}


def build_catalog(rows: list[FusionCandidate], snapshot: RetrievalSnapshot, question: str = '', *,
                  allow_descriptive: bool = False) -> RowCatalog:
    catalog = RowCatalog()
    for index, row in enumerate(rows):
        meta = row.metadata or {}
        if (not row.binding_id or snapshot.binding_revisions.get(row.binding_id) != row.index_revision_id
                or not meta.get("source_revision_id") or not meta.get("canonical_hash")):
            raise AppException("Hàng trả lời không khớp snapshot nguồn.", code="ROW_ANSWER_SOURCE_INVALID", status_code=503)
        try:
            _add_row(catalog, row, index, question, allow_descriptive=allow_descriptive)
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise AppException("Tọa độ ô nguồn không hợp lệ.", code="ROW_ANSWER_SOURCE_INVALID", status_code=503) from exc
    return catalog


def validate_selection(selection: RowSelection, catalog: RowCatalog, question: str) -> None:
    if not selection.cell_ids or len(set(selection.cell_ids)) != len(selection.cell_ids):
        raise ValueError("Missing or duplicate cells")
    if any(key not in catalog.cells for key in selection.cell_ids):
        raise ValueError("Unknown cell")
    context_ids = [*selection.scope_ids, *selection.note_ids]
    if any(key not in catalog.contexts for key in context_ids):
        raise ValueError("Unknown context")
    selected_rows = {catalog.cells[key].row_id for key in selection.cell_ids}
    allowed = {key for row_id in selected_rows for key in catalog.rows[row_id]["context_ids"]}
    if not set(context_ids).issubset(allowed):
        raise ValueError("Context belongs to another source row")
    years = {int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", question)}
    for key in selection.cell_ids:
        cell = catalog.cells[key]
        if cell.description_only or (cell.standard and cell.state_source == "declared"
                                    and cell.state in {"ambiguous", "unreadable"}):
            raise ValueError("Unresolved standard cell is not answer-bearing")
        temporal = cell.temporal or {}
        if temporal.get("review_basis") == "human_review" and temporal.get("status") == "verified":
            corrected_years = set(temporal.get("data_years") or [])
            if years and not years.issubset(corrected_years):
                raise ValueError("Requested year does not match the reviewed cell correction")
            continue  # A source-bound human correction overrides the extracted header year.
        column_years = {int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", cell.header)}
        if years and column_years and not column_years.issubset(years):
            raise ValueError("Requested year does not match this column")
        verified_years = {year for year in temporal.get("data_years") or []
                          if isinstance(year, int) and not isinstance(year, bool)} if (
            temporal.get("status") == "verified" and temporal.get("role", "data") == "data") else set()
        if years and verified_years and not years.intersection(verified_years):
            raise ValueError("Requested year does not match this cell's verified scope")
        row_context = set(catalog.rows[cell.row_id]["context_ids"]).intersection(selection.scope_ids)
        scope_text = cell.header + "\n" + "\n".join(catalog.contexts[ref].text for ref in row_context)
        if years and not years.issubset({int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", scope_text)}):
            raise ValueError("No same-source scope for requested year")


def retain_scoped_cells(selection: RowSelection, catalog: RowCatalog, question: str) -> RowSelection:
    """Prune unsupported years before independent audit, never invent a scope.

    The auditor still receives the full question/candidate set and must verify
    complete coverage, so dropping a requested entity cannot become success.
    Unknown IDs, duplicate IDs and foreign context remain hard validation errors.
    """
    if (any(key not in catalog.cells for key in selection.cell_ids)
            or len(set(selection.cell_ids)) != len(selection.cell_ids)
            or any(key not in catalog.contexts for key in [*selection.scope_ids, *selection.note_ids])):
        return selection  # Let the ordinary strict validator reject malformed IDs.
    selected_rows = {catalog.cells[key].row_id for key in selection.cell_ids}
    allowed = {key for row in selected_rows for key in catalog.rows[row]["context_ids"]}
    if not set(selection.scope_ids + selection.note_ids).issubset(allowed):
        return selection
    kept = []
    for key in selection.cell_ids:
        row_contexts = set(catalog.rows[catalog.cells[key].row_id]["context_ids"])
        single = selection.model_copy(update={"cell_ids": [key],
            "scope_ids": [ref for ref in selection.scope_ids if ref in row_contexts],
            "note_ids": [ref for ref in selection.note_ids if ref in row_contexts]})
        try:
            validate_selection(single, catalog, question)
        except ValueError:
            continue
        kept.append(key)
    remaining = {ref for key in kept for ref in catalog.rows[catalog.cells[key].row_id]["context_ids"]}
    return selection.model_copy(update={"cell_ids": kept,
        "scope_ids": [ref for ref in selection.scope_ids if ref in remaining],
        "note_ids": [ref for ref in selection.note_ids if ref in remaining]})


def source_value_variants(selection: RowSelection, catalog: RowCatalog, question: str) -> bool:
    """A same-year tuple cannot silently hide divergent source values/OCR.

    NFC is only representation normalization. Different accents remain different;
    this flags textual disagreement, not an automatic OCR correction.
    """
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", question))
    if len(years) != 1:
        return False  # Do not mistake historical comparisons for conflicts.

    def normalized(text: str) -> str:
        return " ".join(unicodedata.normalize("NFC", text).casefold().split())

    groups: dict[tuple, list[tuple[str, tuple | str]]] = {}
    for key in selection.cell_ids:
        cell = catalog.cells[key]
        value: tuple | str = normalized(cell.value)
        metric = normalized(cell.header)
        if detect_column_role(cell.header)[0] == "combos":
            tuples = re.findall(r"\(([^)]+)\)", cell.value)
            if tuples:
                value = tuple(sorted(tuple(sorted(normalized(part) for part in item.split(","))) for item in tuples))
            context = cell_context(cell.header)
            # Reuse the existing metric/method classifier; retain structural
            # identifiers such as channel codes so methods are not conflated.
            metric = (context["attribute_code"], normalized((context.get("qualifiers") or {}).get("method") or ""),
                      tuple(re.findall(r"\b[a-z]+\d+\b", normalized(cell.header))))
        if cell.standard:
            value = (cell.state, value)  # Same raw marker with a different declared state is not one datum.
        identity = (normalized(cell.entity), metric)
        code = catalog.rows[cell.row_id].get("entity_code", "") or ""
        groups.setdefault(identity, []).append((code, value))
    return any(left_value != right_value and (not left_code or not right_code or left_code == right_code)
        for values in groups.values() for left_code, left_value in values for right_code, right_value in values)


def complete_audit_context(selection: RowSelection, audit: RowAudit, catalog: RowCatalog) -> RowSelection:
    """Add independently requested context only within the already selected rows.

    Cell agreement and semantic audit flags remain mandatory at the call site.
    Unknown/foreign references are not repaired: the subset validation rejects them.
    """
    selected_rows = {catalog.cells[key].row_id for key in selection.cell_ids}
    scopes = {key for row_id in selected_rows for key in catalog.rows[row_id]["scope_candidates"]}
    notes = {key for row_id in selected_rows for key in catalog.rows[row_id]["note_candidates"]}
    required = set(audit.required_context_ids)
    return selection.model_copy(update={
        "scope_ids": list(dict.fromkeys([*selection.scope_ids, *sorted(required.intersection(scopes))])),
        "note_ids": list(dict.fromkeys([*selection.note_ids, *sorted(required.intersection(notes))])),
    })


def close_context(selection: RowSelection, catalog: RowCatalog) -> RowSelection:
    """Keep whole conditional branches/continued sentences; never infer applicability."""
    required = set(selection.scope_ids + selection.note_ids)
    for row_id in {catalog.cells[key].row_id for key in selection.cell_ids}:
        blocks = [catalog.contexts[key] for key in catalog.rows[row_id]["context_ids"]]
        # Numbered rule branches are lists. A completed rule does not own the
        # following unmarked legend merely because it is the nearest paragraph.
        groups = dependency_groups([block for block in blocks if block.fact_context.get("source_kind") == "list"])
        for block in blocks:
            members = groups.get(block.id, [block])
            continuations = sentence_continuations(blocks, block)
            if required.intersection(member.id for member in [block, *continuations]):
                required.update(member.id for member in [*members, *continuations])
        # Dependencies can introduce a parent whose continuation was not selected.
        for block in blocks:
            if block.id in required:
                required.update(member.id for member in sentence_continuations(blocks, block))
    return selection.model_copy(update={"note_ids": sorted(required - set(selection.scope_ids),
        key=lambda key: (catalog.contexts[key].source_revision_id, catalog.contexts[key].start))})


def close_empty_cells(selection: RowSelection, catalog: RowCatalog) -> RowSelection:
    """Retain empty/dash siblings between selected columns in a shared header family."""
    selected = set(selection.cell_ids)
    for row_id in {catalog.cells[key].row_id for key in selected}:
        siblings = catalog.rows[row_id]["cells"]
        positions = [index for index, cell in enumerate(siblings) if cell["id"] in selected]
        if len(positions) < 2:
            continue
        family = siblings[min(positions):max(positions) + 1]
        prefix = family[0]["header"].split()
        for sibling in family[1:]:
            words = sibling["header"].split()
            common = 0
            for first, last in zip(prefix, words):
                if first != last:
                    break
                common += 1
            prefix = prefix[:common]
        if len(prefix) < 2:
            continue
        for cell in siblings[min(positions):max(positions) + 1]:
            declared = cell.get("standard") and cell.get("state_source") == "declared"
            empty = (cell["state"] in {"blank", "not_stated", "not_applicable"} if declared
                     else not any(char.isalnum() for char in cell["value"]))
            if empty and cell["header"].split()[:len(prefix)] == prefix:
                selected.add(cell["id"])
    return selection.model_copy(update={"cell_ids": [key for key in catalog.cells if key in selected]})


_STATE_LABELS = {"blank": "ô trống trong nguồn", "not_stated": "nguồn không nêu",
                 "not_applicable": "nguồn ghi không áp dụng"}


def _value_display(cell: SourceCell) -> str:
    value = cell.value
    label = _STATE_LABELS.get(cell.state) if cell.standard and cell.state_source == "declared" else None
    if not label:
        return value
    return f"{value} ({label})" if value else f"({label})"


def render_cells(selection: RowSelection, catalog: RowCatalog) -> tuple[str, list[dict], list[dict]]:
    """No model-authored values or interpretations enter the public answer."""
    lines = ["| Ngành/đối tượng | Chỉ số/phương thức trong nguồn | Giá trị |", "| --- | --- | --- |"]
    cells, refs = [], []
    for key in selection.cell_ids:
        cell = catalog.cells[key]
        lines.append("| " + " | ".join(_display(text) for text in (cell.entity, cell.header, _value_display(cell))) + " |")
        entry = {"id": key, "entity": cell.entity, "header": cell.header, "value": cell.value,
                 "state": cell.state, "standard": cell.standard, "references": cell.references}
        if cell.standard:
            entry.update(normalized=cell.normalized, column_id=cell.column_id,
                         header_path=cell.header_path, temporal=cell.temporal)
        cells.append(entry)
        refs.extend(cell.references)
    context_ids = list(dict.fromkeys([*selection.scope_ids, *selection.note_ids]))
    if context_ids:
        lines.append("\nPhạm vi và ghi chú chung trích nguyên văn từ cùng bảng. "
                     "Mỗi mục chỉ áp dụng cho đối tượng/phương thức được nêu trong chính mục đó:")
        for key in context_ids:
            block = catalog.contexts[key]
            if block.text.lstrip().startswith("|"):
                refs.append(_reference(block))  # Header already labels the rendered cells.
                continue
            lines.append("\n> " + block.text.replace("\n", "\n> "))
            refs.append(_reference(block))
    unique = {(ref["binding_id"], ref["index_revision_id"], ref["start"], ref["end"]): ref for ref in refs}
    return "\n".join(lines), cells, list(unique.values())
