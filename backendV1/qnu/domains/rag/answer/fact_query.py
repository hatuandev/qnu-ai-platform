"""Scoped read-only table schema discovery and deterministic query_facts (Slice 3).

Security & fidelity invariants:
- Every DB call enforces resolve_workspace_access(db, actor, workspace_id) and pins
  queries strictly to active completed IndexRuns of the allowed collection_ids.
- Every filter/target column must exist in the table's real column_keys (or standard
  fact fields); guessed column names fail with 422 fact_query_invalid_column.
- COUNT/SUM/MIN/MAX/LIST operate exclusively on row_kind == 'data' by default.
- Numeric filters and aggregations NEVER coerce empty_cell, not_published,
  not_applicable, defined_symbol, or undefined_symbol to 0; excluded counts are
  reported in excluded_by_value_kind alongside exact source_cell_refs.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.facts import (
    FactAttributeValue,
    ScopedNote,
    UniversalFact,
    UniversalTableProjection,
)
from qnu.domains.knowledge.index.models import IndexRun, IndexTableFact
from qnu.domains.rag.answer.cells import materialize as materialize_cells
from qnu.domains.rag.answer.coverage import Requirement
from qnu.domains.rag.answer.schemas import CellSelection, EvidenceSource, ModelAnswer, Statement
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import AppException, EntityNotFound

VERSION = "qnu.fact-query/v1"

FilterOp = Literal["eq", "contains", "in", "set_contains", "gt", "gte", "lt", "lte"]
AggregationOp = Literal["list", "count", "sum", "min", "max"]

STANDARD_FIELDS = frozenset({"group", "subject_code", "subject_name", "data_year", "data_status"})
NUMERIC_ALLOWED_KINDS = frozenset({"normal", "numeric_zero"})
_SEGMENT_RE = re.compile(r"[;\n]+")
_PAREN_RE = re.compile(r"\(([^()]*)\)")


class FactFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column: str
    op: FilterOp = "eq"
    value: str | int | float | list[str]


class FactQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_id: str
    data_year: int | None = None
    filters: list[FactFilter] = Field(default_factory=list)
    aggregation: AggregationOp = "list"
    target_column: str | None = None
    include_non_data: bool = False
    limit: int = Field(default=200, ge=1, le=2000)


class ScopedTableSchema(BaseModel):
    """Real table schema pinned to an active IndexRun for Step 1 of query_facts."""

    model_config = ConfigDict(extra="forbid")

    table_id: str
    source_table_citation: str
    table_title: str = ""
    index_run_id: str
    collection_id: str
    document_id: str
    version_id: str
    publication_decision_id: str
    has_header: bool
    keep_whole_in_chunk: bool
    column_keys: list[str] = Field(default_factory=list)
    data_years: list[int] = Field(default_factory=list)
    data_row_count: int = 0
    scoped_notes: list[ScopedNote] = Field(default_factory=list)


class MatchedFactRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str
    row_index: int
    row_kind: str
    group: str | None = None
    subject_code: str | None = None
    subject_name: str | None = None
    data_year: int | None = None
    data_status: str = "unknown"
    attributes: dict[str, FactAttributeValue] = Field(default_factory=dict)
    applicable_note_ids: list[str] = Field(default_factory=list)
    source_cell_refs: list[str] = Field(default_factory=list)


class FactQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = VERSION
    table_id: str
    source_table_citation: str
    index_run_id: str
    aggregation: AggregationOp
    target_column: str | None = None
    row_kind_scope: str = "data"
    total_matched_rows: int = 0
    included_numeric_count: int = 0
    excluded_by_value_kind: dict[str, int] = Field(default_factory=dict)
    numeric_result: str | None = None
    matched_rows: list[MatchedFactRow] = Field(default_factory=list)
    source_cell_refs: list[str] = Field(default_factory=list)


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split()).casefold()


def parse_numeric_value(raw: str) -> Decimal | None:
    """Parse Vietnamese and international numeric strings strictly without guessing."""
    cleaned = " ".join(unicodedata.normalize("NFC", raw or "").split()).strip()
    if not cleaned:
        return None
    # Reject strings containing alphabetic letters (e.g. "AM-0007", "25 điểm")
    if any(ch.isalpha() for ch in cleaned):
        return None
    token = cleaned.replace(" ", "").rstrip("%")
    if not token:
        return None
    if "," in token and "." in token:
        # 1.250,5 -> 1250.5; 1,250.5 -> 1250.5
        if token.rfind(",") > token.rfind("."):
            token = token.replace(".", "").replace(",", ".")
        else:
            token = token.replace(",", "")
    elif "," in token:
        parts = token.split(",")
        if len(parts) == 2 and len(parts[1]) != 3:
            token = token.replace(",", ".")
        elif all(len(p) == 3 for p in parts[1:]):
            token = "".join(parts)
        else:
            token = token.replace(",", ".")
    elif "." in token:
        parts = token.split(".")
        if len(parts) >= 2 and all(len(p) == 3 for p in parts[1:]) and len(parts[0].lstrip("+-")) <= 3:
            # Vietnamese thousands separator: 5.173 -> 5173
            token = "".join(parts)
    try:
        return Decimal(token)
    except InvalidOperation:
        return None


def _unordered_sets(raw: str) -> list[frozenset[str]]:
    groups: list[frozenset[str]] = []
    for seg in _SEGMENT_RE.split(raw or ""):
        parts = _PAREN_RE.findall(seg) or [seg]
        for part in parts:
            items = {_norm(piece).strip(" .") for piece in part.split(",") if _norm(piece).strip(" .")}
            if items:
                groups.append(frozenset(items))
    return groups


def _extract_field(
    fact: UniversalFact, column: str
) -> tuple[str | None, str, str | None]:
    """Return (raw_text, value_kind, cell_ref) for either a standard field or JSONB attribute."""
    if column == "group":
        val = fact.group or ""
        return val, "normal" if val else "empty_cell", None
    if column == "subject_code":
        val = fact.subject_code or ""
        return val, "normal" if val else "empty_cell", None
    if column == "subject_name":
        val = fact.subject_name or ""
        return val, "normal" if val else "empty_cell", None
    if column == "data_year":
        val = str(fact.data_year) if fact.data_year is not None else ""
        return val, "normal" if val else "empty_cell", None
    if column == "data_status":
        return fact.data_status, "normal", None

    attr = fact.attributes.get(column)
    if attr is None:
        return None, "empty_cell", None
    return attr.raw, attr.value_kind, attr.source_cell_ref


def _matches_filter(fact: UniversalFact, flt: FactFilter) -> bool:
    raw, kind, _ = _extract_field(fact, flt.column)
    if flt.op in {"gt", "gte", "lt", "lte"}:
        if kind not in NUMERIC_ALLOWED_KINDS or raw is None:
            return False
        left = parse_numeric_value(raw)
        right = parse_numeric_value(str(flt.value))
        if left is None or right is None:
            return False
        if flt.op == "gt":
            return left > right
        if flt.op == "gte":
            return left >= right
        if flt.op == "lt":
            return left < right
        return left <= right

    if raw is None:
        return False
    norm_raw = _norm(raw)

    if flt.op == "eq":
        return norm_raw == _norm(str(flt.value))
    if flt.op == "contains":
        return _norm(str(flt.value)) in norm_raw
    if flt.op == "in":
        targets = (
            {_norm(str(v)) for v in flt.value}
            if isinstance(flt.value, list)
            else {_norm(str(flt.value))}
        )
        return norm_raw in targets
    if flt.op == "set_contains":
        wanted = (
            frozenset(_norm(str(v)).strip(" .") for v in flt.value if _norm(str(v)).strip(" ."))
            if isinstance(flt.value, list)
            else frozenset(
                _norm(p).strip(" .") for p in str(flt.value).split(",") if _norm(p).strip(" .")
            )
        )
        if not wanted:
            return False
        return any(wanted <= grp for grp in _unordered_sets(raw))
    return False


def _validate_columns(schema: ScopedTableSchema, request: FactQueryRequest) -> None:
    allowed = set(schema.column_keys) | STANDARD_FIELDS
    invalid: list[str] = []
    for flt in request.filters:
        if flt.column not in allowed:
            invalid.append(flt.column)
    if request.target_column is not None and request.target_column not in allowed:
        invalid.append(request.target_column)
    if invalid:
        raise AppException(
            f"Tên cột không tồn tại trong bảng '{schema.table_id}': {', '.join(invalid)}. "
            f"Các cột hợp lệ: {', '.join(schema.column_keys)}",
            code="fact_query_invalid_column",
            status_code=422,
        )
    if request.aggregation in {"sum", "min", "max"} and not request.target_column:
        raise AppException(
            f"Phép tổng hợp '{request.aggregation}' bắt buộc chỉ định target_column.",
            code="fact_query_target_column_required",
            status_code=422,
        )


def _format_decimal(value: Decimal) -> str:
    if value == value.to_integral():
        return format(value.to_integral(), "f")
    return format(value.normalize(), "f")


def execute_fact_query(
    facts: list[UniversalFact],
    schema: ScopedTableSchema,
    request: FactQueryRequest,
) -> FactQueryResult:
    """Pure deterministic query engine over scoped UniversalFacts."""
    _validate_columns(schema, request)

    candidates: list[UniversalFact] = []
    for fact in facts:
        if not request.include_non_data and fact.row_kind != "data":
            continue
        if request.data_year is not None and fact.data_year != request.data_year:
            continue
        if all(_matches_filter(fact, flt) for flt in request.filters):
            candidates.append(fact)

    excluded_counts: dict[str, int] = {}
    all_refs: list[str] = []
    matched_models: list[MatchedFactRow] = []

    def _add_refs(refs: list[str]) -> None:
        for ref in refs:
            if ref and ref not in all_refs:
                all_refs.append(ref)

    if request.aggregation in {"list", "count"}:
        for fact in candidates:
            _add_refs(fact.source_cell_refs)
        if request.aggregation == "list":
            for fact in candidates[: request.limit]:
                matched_models.append(
                    MatchedFactRow(
                        fact_id=fact.fact_id,
                        row_index=fact.row_index,
                        row_kind=fact.row_kind,
                        group=fact.group,
                        subject_code=fact.subject_code,
                        subject_name=fact.subject_name,
                        data_year=fact.data_year,
                        data_status=fact.data_status,
                        attributes=fact.attributes,
                        applicable_note_ids=fact.applicable_note_ids,
                        source_cell_refs=fact.source_cell_refs,
                    )
                )
        return FactQueryResult(
            table_id=schema.table_id,
            source_table_citation=schema.source_table_citation,
            index_run_id=schema.index_run_id,
            aggregation=request.aggregation,
            target_column=request.target_column,
            row_kind_scope="all" if request.include_non_data else "data",
            total_matched_rows=len(candidates),
            included_numeric_count=0,
            excluded_by_value_kind={},
            numeric_result=str(len(candidates)) if request.aggregation == "count" else None,
            matched_rows=matched_models,
            source_cell_refs=all_refs,
        )

    # Numeric aggregation: sum / min / max (strictly normal + numeric_zero only)
    assert request.target_column is not None
    numeric_pairs: list[tuple[Decimal, UniversalFact, str | None]] = []
    for fact in candidates:
        raw, kind, cell_ref = _extract_field(fact, request.target_column)
        if kind not in NUMERIC_ALLOWED_KINDS or raw is None:
            excluded_counts[kind] = excluded_counts.get(kind, 0) + 1
            continue
        parsed = parse_numeric_value(raw)
        if parsed is None:
            excluded_counts["non_numeric_text"] = excluded_counts.get("non_numeric_text", 0) + 1
            continue
        numeric_pairs.append((parsed, fact, cell_ref))
        if cell_ref:
            _add_refs([cell_ref])
        _add_refs(fact.source_cell_refs)

    numeric_result: str | None = None
    winning_facts: list[UniversalFact] = []
    if numeric_pairs:
        if request.aggregation == "sum":
            total = sum((val for val, _, _ in numeric_pairs), Decimal(0))
            numeric_result = _format_decimal(total)
            winning_facts = [fact for _, fact, _ in numeric_pairs[: request.limit]]
        elif request.aggregation == "min":
            min_val = min(val for val, _, _ in numeric_pairs)
            numeric_result = _format_decimal(min_val)
            winning_facts = [fact for val, fact, _ in numeric_pairs if val == min_val]
        elif request.aggregation == "max":
            max_val = max(val for val, _, _ in numeric_pairs)
            numeric_result = _format_decimal(max_val)
            winning_facts = [fact for val, fact, _ in numeric_pairs if val == max_val]

    for fact in winning_facts[: request.limit]:
        matched_models.append(
            MatchedFactRow(
                fact_id=fact.fact_id,
                row_index=fact.row_index,
                row_kind=fact.row_kind,
                group=fact.group,
                subject_code=fact.subject_code,
                subject_name=fact.subject_name,
                data_year=fact.data_year,
                data_status=fact.data_status,
                attributes=fact.attributes,
                applicable_note_ids=fact.applicable_note_ids,
                source_cell_refs=fact.source_cell_refs,
            )
        )

    return FactQueryResult(
        table_id=schema.table_id,
        source_table_citation=schema.source_table_citation,
        index_run_id=schema.index_run_id,
        aggregation=request.aggregation,
        target_column=request.target_column,
        row_kind_scope="all" if request.include_non_data else "data",
        total_matched_rows=len(candidates),
        included_numeric_count=len(numeric_pairs),
        excluded_by_value_kind=excluded_counts,
        numeric_result=numeric_result,
        matched_rows=matched_models,
        source_cell_refs=all_refs,
    )


def _row_to_fact(row: IndexTableFact) -> UniversalFact:
    return UniversalFact(
        fact_id=row.fact_id,
        row_index=row.row_index,
        row_kind=row.row_kind,  # type: ignore[arg-type]
        row_pointer=row.row_pointer,
        group=row.group_name,
        subject_code=row.subject_code,
        subject_name=row.subject_name,
        data_year=row.data_year,
        data_status=row.data_status,  # type: ignore[arg-type]
        attributes={
            k: FactAttributeValue.model_validate(v) for k, v in (row.attributes or {}).items()
        },
        detail_md_pointers=dict(row.detail_md_pointers or {}),
        applicable_note_ids=list(row.applicable_note_ids or []),
        source_cell_refs=list(row.source_cell_refs or []),
        cross_references=list(row.cross_references or []),
    )


def rows_for_projection(
    projection: UniversalTableProjection,
    *,
    input_id: str,
    index_run_id: str,
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    publication_decision_id: str,
    id_factory,
) -> list[IndexTableFact]:
    """Convert one UniversalTableProjection into ORM rows ready for kb_index_table_facts."""
    serialized_notes = [note.model_dump(mode="json") for note in projection.scoped_notes]
    orm_rows: list[IndexTableFact] = []
    for fact in projection.facts:
        orm_rows.append(
            IndexTableFact(
                id=id_factory(),
                input_id=input_id,
                index_run_id=index_run_id,
                workspace_id=workspace_id,
                collection_id=collection_id,
                document_id=document_id,
                version_id=version_id,
                publication_decision_id=publication_decision_id,
                table_id=projection.table_id,
                source_table_citation=projection.source_table_citation,
                table_title=projection.title,
                has_header=projection.has_header,
                keep_whole_in_chunk=projection.keep_whole_in_chunk,
                column_keys=list(projection.column_keys),
                scoped_notes=serialized_notes,
                fact_id=fact.fact_id,
                row_index=fact.row_index,
                row_kind=fact.row_kind,
                row_pointer=fact.row_pointer,
                group_name=fact.group,
                subject_code=fact.subject_code,
                subject_name=fact.subject_name,
                data_year=fact.data_year,
                data_status=fact.data_status,
                attributes={k: v.model_dump(mode="json") for k, v in fact.attributes.items()},
                detail_md_pointers=dict(fact.detail_md_pointers),
                applicable_note_ids=list(fact.applicable_note_ids),
                source_cell_refs=list(fact.source_cell_refs),
                cross_references=list(fact.cross_references),
            )
        )
    return orm_rows


async def _active_run_ids(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_ids: list[str],
) -> list[str]:
    await resolve_workspace_access(db, actor, workspace_id)
    ids = list(dict.fromkeys(collection_ids))
    if not ids:
        return []
    result = await db.execute(
        select(IndexRun.id).where(
            IndexRun.workspace_id == workspace_id,
            IndexRun.collection_id.in_(ids),
            IndexRun.is_active.is_(True),
            IndexRun.status == "completed",
        )
    )
    return [row[0] for row in result.all()]


async def get_table_schemas(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_ids: list[str],
    *,
    table_id: str | None = None,
) -> list[ScopedTableSchema]:
    """Step 1: discover real table_ids and column_keys strictly inside active IndexRuns."""
    run_ids = await _active_run_ids(db, actor, workspace_id, collection_ids)
    if not run_ids:
        return []
    stmt = select(IndexTableFact).where(
        IndexTableFact.workspace_id == workspace_id,
        IndexTableFact.index_run_id.in_(run_ids),
    )
    if table_id is not None:
        stmt = stmt.where(IndexTableFact.table_id == table_id)
    rows = (await db.execute(stmt)).scalars().all()

    grouped: dict[tuple[str, str], list[IndexTableFact]] = {}
    for row in rows:
        grouped.setdefault((row.index_run_id, row.table_id), []).append(row)

    schemas: list[ScopedTableSchema] = []
    for (_, _), group_rows in sorted(grouped.items()):
        first = group_rows[0]
        years = sorted({r.data_year for r in group_rows if r.data_year is not None})
        data_count = len({r.row_index for r in group_rows if r.row_kind == "data"})
        notes = [ScopedNote.model_validate(n) for n in (first.scoped_notes or [])]
        schemas.append(
            ScopedTableSchema(
                table_id=first.table_id,
                source_table_citation=first.source_table_citation,
                table_title=first.table_title,
                index_run_id=first.index_run_id,
                collection_id=first.collection_id,
                document_id=first.document_id,
                version_id=first.version_id,
                publication_decision_id=first.publication_decision_id,
                has_header=first.has_header,
                keep_whole_in_chunk=first.keep_whole_in_chunk,
                column_keys=list(first.column_keys or []),
                data_years=years,
                data_row_count=data_count,
                scoped_notes=notes,
            )
        )
    return schemas


async def query_facts(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_ids: list[str],
    request: FactQueryRequest,
) -> FactQueryResult:
    """Step 2: execute validated deterministic query strictly within active IndexRuns."""
    schemas = await get_table_schemas(
        db, actor, workspace_id, collection_ids, table_id=request.table_id
    )
    if not schemas:
        raise EntityNotFound(
            f"Không tìm thấy bảng '{request.table_id}' trong phạm vi chỉ mục đang hoạt động.",
            code="fact_table_not_found",
        )
    schema = schemas[0]
    stmt = (
        select(IndexTableFact)
        .where(
            IndexTableFact.workspace_id == workspace_id,
            IndexTableFact.index_run_id == schema.index_run_id,
            IndexTableFact.table_id == schema.table_id,
        )
        .order_by(IndexTableFact.row_index.asc())
    )
    if not request.include_non_data:
        stmt = stmt.where(IndexTableFact.row_kind == "data")
    if request.data_year is not None:
        stmt = stmt.where(
            or_(
                IndexTableFact.data_year == request.data_year,
                IndexTableFact.data_year.is_(None),
            )
        )
    rows = list((await db.execute(stmt)).scalars().all())
    if request.data_year is not None:
        filtered_rows = []
        for r in rows:
            if r.data_year == request.data_year:
                filtered_rows.append(r)
            elif r.data_year is None:
                attrs = r.attributes or {}
                meta_years = (attrs.get("_data_years") or {}).get("years", [])
                has_year_col = any(k.startswith(f"{request.data_year} > ") for k in attrs)
                if request.data_year in meta_years or has_year_col:
                    filtered_rows.append(r)
        rows = filtered_rows
    facts = [_row_to_fact(r) for r in rows]
    return execute_fact_query(facts, schema, request)


def materialize_fact_query_answer(
    result: FactQueryResult,
    sources: list[EvidenceSource],
    cells: dict,
    *,
    report: dict | None = None,
) -> ModelAnswer:
    """Route deterministic query_facts output through cells.py::materialize()."""
    if result.total_matched_rows == 0 or (
        result.aggregation in {"sum", "min", "max"} and result.numeric_result is None
    ):
        return ModelAnswer(
            status="insufficient_evidence",
            statements=[],
            lookups=[],
            assessment=[
                Requirement(
                    label=f"Truy vấn bảng {result.table_id} ({result.aggregation})",
                    status="missing",
                    evidence_ids=[],
                )
            ],
            message="Không tìm thấy dữ liệu phù hợp trong bảng đã xuất bản để trả lời yêu cầu.",
        )

    # Map source_cell_ref -> cell_id from the sealed cells catalog
    ref_to_cell_ids: dict[str, list[tuple[str, bool]]] = {}
    evidence_ids_used: list[str] = []
    for table in cells.get("tables") or []:
        ev_id = table["evidence_id"]
        for cell in table.get("cells") or []:
            is_name = bool(cell.get("row_name"))
            for ref in cell.get("source_cells") or []:
                ref_to_cell_ids.setdefault(ref, []).append((cell["cell_id"], is_name))
            if ev_id not in evidence_ids_used and any(
                ref in result.source_cell_refs for ref in cell.get("source_cells") or []
            ):
                evidence_ids_used.append(ev_id)

    lookups: list[CellSelection] = []
    seen_cell_ids: set[str] = set()
    for row in result.matched_rows:
        target_refs: list[str] = []
        if result.target_column and result.target_column in row.attributes:
            ref = row.attributes[result.target_column].source_cell_ref
            if ref:
                target_refs.append(ref)
        if not target_refs:
            target_refs = list(row.source_cell_refs)

        chosen_for_row: str | None = None
        all_candidates = [
            item for ref in target_refs for item in (ref_to_cell_ids.get(ref) or [])
        ]
        if all_candidates:
            if result.aggregation == "list" and not result.target_column:
                name_match = next((cid for cid, is_name in all_candidates if is_name), None)
                chosen_for_row = name_match or all_candidates[0][0]
            else:
                non_name = next((cid for cid, is_name in all_candidates if not is_name), None)
                chosen_for_row = non_name or all_candidates[0][0]
        if chosen_for_row and chosen_for_row not in seen_cell_ids:
            seen_cell_ids.add(chosen_for_row)
            lookups.append(CellSelection(cell_id=chosen_for_row))

    statements: list[Statement] = []
    if not lookups:
        # Unselectable table fallback: emit verbatim row names / values citing the table evidence_id
        table_ev_ids = [
            s.evidence_id
            for s in sources
            if s.kind == "table"
            and (s.structure or {}).get("source_table_citation") == result.source_table_citation
        ]
        ev_ids = table_ev_ids or [s.evidence_id for s in sources[:1]]
        evidence_ids_used = list(dict.fromkeys([*evidence_ids_used, *ev_ids]))
        if result.aggregation == "list":
            names = [r.subject_name or r.subject_code or r.fact_id for r in result.matched_rows]
            statements.append(Statement(text=", ".join(names), evidence_ids=ev_ids))
        elif result.numeric_result is not None:
            statements.append(
                Statement(
                    text=f"{result.target_column or result.table_id}: {result.numeric_result}",
                    evidence_ids=ev_ids,
                )
            )

    if not evidence_ids_used and sources:
        evidence_ids_used = [sources[0].evidence_id]

    proposed = ModelAnswer(
        status="answered",
        statements=statements,
        lookups=lookups[:20],
        assessment=[
            Requirement(
                label=f"Truy vấn bảng {result.table_id} ({result.aggregation})",
                status="covered",
                evidence_ids=evidence_ids_used,
            )
        ],
        message=None,
    )
    return materialize_cells(proposed, sources, cells, report=report)
