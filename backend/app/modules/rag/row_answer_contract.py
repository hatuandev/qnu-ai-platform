"""Server-owned cell coordinates and exact citations for published source rows."""

import html
import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import Field

from app.core.exceptions import AppException
from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.normalization.retrieval_models import SourceUnit
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.table_context import extract_context_tables, row_identities
from app.modules.rag.evidence_dependencies import dependency_groups, sentence_continuations
from app.modules.rag.evidence_schemas import EvidenceBlock, QuoteReference, StrictContract
from app.modules.rag.evidence_validation import bind_quote
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import RetrievalSnapshot


class RowSelection(StrictContract):
    status: Literal["selected", "missing", "conflict", "not_applicable"]
    cell_ids: list[str] = Field(default_factory=list, max_length=60)
    scope_ids: list[str] = Field(default_factory=list, max_length=20)
    note_ids: list[str] = Field(default_factory=list, max_length=40)
    missing_constraints: list[str] = Field(default_factory=list, max_length=8)


class MetricScope(StrictContract):
    context_ids: list[str] = Field(default_factory=list, max_length=12)


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
        fact_context={"source_kind": unit.kind})


def _reference(block: EvidenceBlock) -> dict:
    return bind_quote(QuoteReference(block_id=block.id, quote=block.text), {block.id: block})


def _display(text: str) -> str:
    return html.escape(re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)).replace("|", "\\|").replace("\n", " ")


def _add_row(catalog: RowCatalog, row: FusionCandidate, index: int) -> None:
    unit = SourceUnit.model_validate(row.metadata["source_unit"])
    tables = extract_context_tables(unit.header_context + "\n" + unit.text, 1)
    if len(tables) != 1 or len(tables[0]["rows"]) != 1:
        return  # Unresolved matrix is not a cell-answer candidate.
    table = tables[0]
    values = _split_gfm_row(unit.text)
    identities = row_identities(values, table)
    if len(identities) != 1 or len(values) != len(table["headers"]):
        return
    identity, _, entity, _ = identities[0]
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
    cells = []
    for column, (label, value) in enumerate(zip(table["headers"], values, strict=True)):
        if column == identity or detect_column_role(label)[0] == "code" or column < identity:
            continue
        key = f"{row_id}c{column}"
        catalog.cells[key] = SourceCell(row_id, entity, label, value, refs)
        cells.append({"id": key, "header": label, "value": value})
    if cells:
        catalog.rows[row_id] = {"id": row_id, "entity": entity, "title": body.title,
            "source_revision_id": body.source_revision_id, "cells": cells, "context_ids": context_ids,
            "scope_candidates": [key for key in context_ids if catalog.contexts[key].start < unit.start],
            "note_candidates": [key for key in context_ids if catalog.contexts[key].start > unit.start]}


def build_catalog(rows: list[FusionCandidate], snapshot: RetrievalSnapshot) -> RowCatalog:
    catalog = RowCatalog()
    for index, row in enumerate(rows):
        meta = row.metadata or {}
        if (not row.binding_id or snapshot.binding_revisions.get(row.binding_id) != row.index_revision_id
                or not meta.get("source_revision_id") or not meta.get("canonical_hash")):
            raise AppException("Hàng trả lời không khớp snapshot nguồn.", code="ROW_ANSWER_SOURCE_INVALID", status_code=503)
        try:
            _add_row(catalog, row, index)
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
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", question))
    for key in selection.cell_ids:
        cell = catalog.cells[key]
        column_years = set(re.findall(r"\b(?:19|20)\d{2}\b", cell.header))
        if years and column_years and not column_years.issubset(years):
            raise ValueError("Requested year does not match this column")
        row_context = set(catalog.rows[cell.row_id]["context_ids"]).intersection(selection.scope_ids)
        scope_text = cell.header + "\n" + "\n".join(catalog.contexts[ref].text for ref in row_context)
        if years and not years.issubset(set(re.findall(r"\b(?:19|20)\d{2}\b", scope_text))):
            raise ValueError("No same-source scope for requested year")


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
            if not any(char.isalnum() for char in cell["value"]) and cell["header"].split()[:len(prefix)] == prefix:
                selected.add(cell["id"])
    return selection.model_copy(update={"cell_ids": [key for key in catalog.cells if key in selected]})


def render_cells(selection: RowSelection, catalog: RowCatalog) -> tuple[str, list[dict], list[dict]]:
    """No model-authored values or interpretations enter the public answer."""
    lines = ["| Ngành/đối tượng | Chỉ số/phương thức trong nguồn | Giá trị |", "| --- | --- | --- |"]
    cells, refs = [], []
    for key in selection.cell_ids:
        cell = catalog.cells[key]
        lines.append("| " + " | ".join(_display(text) for text in (cell.entity, cell.header, cell.value)) + " |")
        cells.append({"id": key, "entity": cell.entity, "header": cell.header, "value": cell.value,
                      "references": cell.references})
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
