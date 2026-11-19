"""Self-Contained Row-Card projection & pointer/cross-reference expansion (Slice 2).

Zero LLM tokens; renders UniversalFacts into retrieval-ready Row-Cards for
Hybrid Search + Cross-Encoder Reranker, honors keep_whole_in_chunk for small
tables, and expands detail_md_pointers / cross_references within byte budgets.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from qnu.domains.knowledge.index.chunking import Chunk

from qnu.domains.knowledge.index.facts import (
    FactAttributeValue,
    RowKind,
    ScopedNote,
    UniversalFact,
    UniversalTableProjection,
)

VERSION = "qnu.row-cards/v1"


class DocumentCardMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_number: str = ""
    doc_year: int | None = None
    title: str = ""


class RowCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = VERSION
    card_id: str
    table_id: str
    source_table_citation: str
    fact_ids: list[str] = Field(default_factory=list)
    row_kind: RowKind | str = "data"
    keep_whole_in_chunk: bool = False
    data_years: list[int] = Field(default_factory=list)
    text: str
    detail_md_pointers: dict[str, str] = Field(default_factory=dict)
    cross_references: list[str] = Field(default_factory=list)
    source_cell_refs: list[str] = Field(default_factory=list)


class ExpandedRowCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card: RowCard
    expanded_details: dict[str, str] = Field(default_factory=dict)
    expanded_references: dict[str, str] = Field(default_factory=dict)
    unresolved_pointers: list[str] = Field(default_factory=list)
    omitted_pointers: list[str] = Field(default_factory=list)
    combined_text: str


def render_attribute_value(attr: FactAttributeValue) -> str:
    """Render value_kind explicitly so neither reranker nor LLM coerces symbols to 0."""
    if attr.value_kind == "empty_cell":
        return "[Ô TRỐNG - chưa nhập]"
    if attr.value_kind == "numeric_zero":
        return attr.raw
    if attr.value_kind == "not_published":
        return f"[CHƯA CÔNG BỐ: {attr.raw}]"
    if attr.value_kind == "not_applicable":
        return f"[KHÔNG ÁP DỤNG: {attr.raw}]"
    if attr.value_kind == "defined_symbol":
        return f"{attr.raw} (ký hiệu có chú thích)"
    if attr.value_kind == "undefined_symbol":
        return f'[KÝ HIỆU "{attr.raw}" - chưa có định nghĩa]'
    if attr.is_truncated and attr.detail_md_pointer:
        return f"{attr.raw} [Xem chi tiết: {attr.detail_md_pointer}]"
    return attr.raw


def _header_line(
    projection: UniversalTableProjection,
    *,
    document_meta: DocumentCardMeta | None = None,
    data_year: int | None = None,
    data_status: str | None = None,
) -> str:
    parts: list[str] = []
    if document_meta and (document_meta.doc_number or document_meta.title):
        label = document_meta.doc_number or document_meta.title
        if document_meta.doc_year is not None:
            parts.append(f"Nguồn: {label} (Ban hành {document_meta.doc_year})")
        else:
            parts.append(f"Nguồn: {label}")
    if data_year is not None:
        status_part = f" ({data_status})" if data_status and data_status != "unknown" else ""
        parts.append(f"Dữ liệu năm: {data_year}{status_part}")
    elif projection.data_years:
        years_str = ", ".join(str(y) for y in projection.data_years)
        parts.append(f"Dữ liệu năm: {years_str}")
    table_label = projection.title or projection.table_id
    parts.append(f"Bảng: {table_label}")
    return "[" + " | ".join(parts) + "]"


def _format_fact_body(fact: UniversalFact, note_index: dict[str, ScopedNote]) -> str:
    lines: list[str] = []
    if fact.row_kind == "inline_note":
        if fact.group and fact.subject_name:
            lines.append(f"Nhóm: {fact.group} | Ghi chú trong bảng: {fact.subject_name}")
        elif fact.subject_name:
            lines.append(f"Ghi chú trong bảng: {fact.subject_name}")
        return "\n".join(lines)

    subject_parts: list[str] = []
    if fact.row_kind == "summary":
        subject_parts.append("[DÒNG TỔNG HỢP]")
    if fact.subject_name:
        if fact.subject_code:
            subject_parts.append(f"Đối tượng: {fact.subject_name} (Mã: {fact.subject_code})")
        else:
            subject_parts.append(f"Đối tượng: {fact.subject_name}")
    elif fact.subject_code:
        subject_parts.append(f"Mã đối tượng: {fact.subject_code}")
    if fact.group:
        subject_parts.append(f"Nhóm: {fact.group}")
    if subject_parts:
        lines.append(" | ".join(subject_parts))

    if fact.attributes:
        attr_pairs = [
            f"{key}: {render_attribute_value(val)}" for key, val in fact.attributes.items()
        ]
        lines.append("Thuộc tính: " + "; ".join(attr_pairs))

    applicable_texts = [
        f"{note_id}: {note_index[note_id].text}"
        for note_id in fact.applicable_note_ids
        if note_id in note_index
    ]
    if applicable_texts:
        lines.append("Lưu ý phạm vi áp dụng: " + " | ".join(applicable_texts))

    return "\n".join(lines)


def render_fact_to_row_card(
    fact: UniversalFact,
    projection: UniversalTableProjection,
    *,
    document_meta: DocumentCardMeta | None = None,
) -> RowCard:
    """Render one UniversalFact into a Self-Contained Row-Card."""
    note_index = {note.note_id: note for note in projection.scoped_notes}
    header = _header_line(
        projection,
        document_meta=document_meta,
        data_year=fact.data_year,
        data_status=fact.data_status,
    )
    body = _format_fact_body(fact, note_index)
    text = f"{header}\n{body}" if body else header
    return RowCard(
        card_id=f"card:{fact.fact_id}",
        table_id=projection.table_id,
        source_table_citation=projection.source_table_citation,
        fact_ids=[fact.fact_id],
        row_kind=fact.row_kind,
        keep_whole_in_chunk=False,
        data_years=[fact.data_year] if fact.data_year is not None else [],
        text=text,
        detail_md_pointers=dict(fact.detail_md_pointers),
        cross_references=list(fact.cross_references),
        source_cell_refs=list(fact.source_cell_refs),
    )


def render_projection_to_cards(
    projection: UniversalTableProjection,
    *,
    document_meta: DocumentCardMeta | None = None,
) -> list[RowCard]:
    """Project a table into either 1 whole-table card (small/raw) or per-row Row-Cards."""
    if projection.storage_mode == "invalid":
        return []

    if not projection.has_header or projection.storage_mode == "raw_rows":
        header = _header_line(projection, document_meta=document_meta)
        row_lines = [" | ".join(row.cells) for row in projection.raw_rows]
        refs = list(
            dict.fromkeys(ref for row in projection.raw_rows for ref in row.source_cell_refs)
        )
        note_lines = [f"{n.note_id}: {n.text}" for n in projection.scoped_notes]
        sections = [header, *row_lines]
        if note_lines:
            sections.append("Lưu ý phạm vi áp dụng: " + " | ".join(note_lines))
        return [
            RowCard(
                card_id=f"card:{projection.table_id}:whole",
                table_id=projection.table_id,
                source_table_citation=projection.source_table_citation,
                fact_ids=[],
                row_kind="raw_rows",
                keep_whole_in_chunk=True,
                data_years=list(projection.data_years),
                text="\n".join(sections),
                source_cell_refs=refs,
            )
        ]

    if projection.keep_whole_in_chunk:
        note_index = {note.note_id: note for note in projection.scoped_notes}
        header = _header_line(projection, document_meta=document_meta)
        body_blocks: list[str] = []
        fact_ids: list[str] = []
        detail_pointers: dict[str, str] = {}
        xrefs: list[str] = []
        cell_refs: list[str] = []

        for fact in projection.facts:
            if fact.row_kind == "group_header":
                continue
            rendered = _format_fact_body(fact, note_index)
            if rendered:
                body_blocks.append(rendered)
            fact_ids.append(fact.fact_id)
            for col, ptr in fact.detail_md_pointers.items():
                detail_pointers[f"{fact.fact_id}:{col}"] = ptr
            for ref in fact.cross_references:
                if ref not in xrefs:
                    xrefs.append(ref)
            for cref in fact.source_cell_refs:
                if cref not in cell_refs:
                    cell_refs.append(cref)

        text = "\n".join([header, *body_blocks])
        return [
            RowCard(
                card_id=f"card:{projection.table_id}:whole",
                table_id=projection.table_id,
                source_table_citation=projection.source_table_citation,
                fact_ids=fact_ids,
                row_kind="whole_table",
                keep_whole_in_chunk=True,
                data_years=list(projection.data_years),
                text=text,
                detail_md_pointers=detail_pointers,
                cross_references=xrefs,
                source_cell_refs=cell_refs,
            )
        ]

    cards: list[RowCard] = []
    for fact in projection.facts:
        if fact.row_kind in {"data", "summary", "inline_note"}:
            cards.append(render_fact_to_row_card(fact, projection, document_meta=document_meta))
    return cards


def expand_cards_context(
    cards: list[RowCard],
    *,
    md_blocks: dict[str, str],
    max_bytes: int | None = None,
) -> list[ExpandedRowCard]:
    """Expand detail_md_pointers and cross_references from pinned Markdown blocks.

    Two-pass priority across all cards: every card's detail_md_pointers are
    expanded before any card's cross_references under max_bytes. Missing blocks
    stay unresolved; over-budget blocks are explicitly recorded in omitted_pointers.
    """
    used_bytes = sum(len(card.text.encode("utf-8")) for card in cards)
    states = [
        {
            "card": card,
            "details": {},
            "references": {},
            "unresolved": [],
            "omitted": [],
            "extra_sections": [],
            "seen": set(),
        }
        for card in cards
    ]

    # Pass 1: detail_md_pointers across all cards first
    for state in states:
        card: RowCard = state["card"]
        for col_label, pointer in card.detail_md_pointers.items():
            if pointer in state["seen"]:
                continue
            state["seen"].add(pointer)
            content = md_blocks.get(pointer)
            if content is None:
                state["unresolved"].append(pointer)
                continue
            section = f"[Chi tiết {col_label} ({pointer})]: {content}"
            section_bytes = len(section.encode("utf-8"))
            if max_bytes is not None and used_bytes + section_bytes > max_bytes:
                state["omitted"].append(pointer)
                continue
            used_bytes += section_bytes
            state["details"][pointer] = content
            state["extra_sections"].append(section)

    # Pass 2: cross_references with remaining budget
    for state in states:
        card = state["card"]
        for ref_pointer in card.cross_references:
            if ref_pointer in state["seen"]:
                continue
            state["seen"].add(ref_pointer)
            content = md_blocks.get(ref_pointer)
            if content is None:
                state["unresolved"].append(ref_pointer)
                continue
            section = f"[Tham chiếu {ref_pointer}]: {content}"
            section_bytes = len(section.encode("utf-8"))
            if max_bytes is not None and used_bytes + section_bytes > max_bytes:
                state["omitted"].append(ref_pointer)
                continue
            used_bytes += section_bytes
            state["references"][ref_pointer] = content
            state["extra_sections"].append(section)

    return [
        ExpandedRowCard(
            card=state["card"],
            expanded_details=state["details"],
            expanded_references=state["references"],
            unresolved_pointers=state["unresolved"],
            omitted_pointers=state["omitted"],
            combined_text="\n".join([state["card"].text, *state["extra_sections"]]),
        )
        for state in states
    ]


_COL_YEAR_RE = re.compile(r"^table:(.+):column:(\d+)$")


def column_years_for_table(citation: str, annotations: list[dict]) -> dict[int, int]:
    years: dict[int, int] = {}
    for ann in annotations:
        match = _COL_YEAR_RE.fullmatch(ann.get("target") or "")
        if not match or match.group(1) != citation:
            continue
        year = (ann.get("values") or {}).get("data_year")
        if type(year) is int:
            years[int(match.group(2))] = year
    return years


def row_card_to_chunk(card: RowCard, index: dict | None = None) -> Chunk:
    from qnu.domains.knowledge.index.chunking import Chunk

    if index:
        citations = {
            ref: (index[ref] if isinstance(index.get(ref), dict) else ref)
            for ref in card.source_cell_refs
        }
    else:
        citations = {ref: ref for ref in card.source_cell_refs}
    structure = {
        "card_id": card.card_id,
        "table_id": card.table_id,
        "source_table_citation": card.source_table_citation,
        "fact_ids": card.fact_ids,
        "row_kind": card.row_kind,
        "data_years": card.data_years,
        "detail_md_pointers": card.detail_md_pointers,
        "cross_references": card.cross_references,
        "source_cell_refs": card.source_cell_refs,
        "table": True,
    }
    return Chunk(
        kind="row_card",
        text=card.text,
        citations=citations,
        structure=structure,
    )


def build_row_card_chunks(
    tables: list[dict],
    doc_title: str,
    annotations: list[dict] | None = None,
    index: dict | None = None,
) -> list[Chunk]:
    from qnu.domains.knowledge.index.facts import project_table

    chunks = []
    doc_meta = DocumentCardMeta(title=doc_title)
    annotations = annotations or []
    last_opening_headers: dict[int, list[list[dict]]] = {}
    for entry in tables:
        table = entry.get("table") or {}
        citation = entry.get("citation") or ""
        if table.get("status") != "parsed" or not table.get("rows") or not citation:
            continue
        cols = table.get("column_count", 0)
        inherited = last_opening_headers.get(cols)
        column_years = column_years_for_table(citation, annotations)
        projected = project_table(
            table,
            table_id=citation,
            source_table_citation=citation,
            title=entry.get("title") or doc_title,
            column_years=column_years,
            inherited_header_rows=inherited,
        )
        if not projected.facts:
            continue
        if projected.has_header and projected.storage_mode == "facts" and not inherited:
            from qnu.domains.knowledge.index.table_layout import header_rows, table_structure

            st = table_structure(table)
            hr = header_rows(st)
            if not hr:
                from qnu.domains.knowledge.index.table_dependencies import (
                    header_row,
                    multitier_header,
                    typed_header,
                )

                multi = multitier_header(table)
                if multi is not None:
                    hr = multi
                elif typed_header(table):
                    hr = [0]
                elif header_row(table):
                    hr = [0]
            if hr:
                last_opening_headers[cols] = [table["rows"][r] for r in hr]

        cards = render_projection_to_cards(projected, document_meta=doc_meta)
        for card in cards:
            chunks.append(row_card_to_chunk(card, index=index))
    return chunks
