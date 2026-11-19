"""Deterministic Universal Facts projection from canonical sealed tables (Slice 1).

No LLM calls; preserves leading-zero string codes, explicit value_kind,
multi-year row splitting, rowspan/colspan unmerging, headerless raw rows,
long-cell Markdown pointers, scoped notes, row_kind classification,
keep_whole_in_chunk flag, and exact column_keys for Slice 3.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from qnu.domains.knowledge.index.table_layout import (
    CellPosition,
    header_rows,
    layout,
    table_structure,
)

VERSION = "qnu.universal-facts/v1"
DEFAULT_SMALL_TABLE_ROWS = 10
DEFAULT_LONG_CELL_WORDS = 100
DEFAULT_PREVIEW_WORDS = 30

ValueKind = Literal[
    "normal",
    "numeric_zero",
    "empty_cell",
    "not_published",
    "not_applicable",
    "defined_symbol",
    "undefined_symbol",
]
DataStatus = Literal["locked", "interim", "planned", "unknown"]
NoteScope = Literal["table", "group", "row", "column_year"]
RowKind = Literal["data", "summary", "group_header", "inline_note"]
StorageMode = Literal["facts", "raw_rows", "invalid"]

_ZERO_RE = re.compile(r"^[+-]?0(?:[.,]0+)?$")
_NOT_PUBLISHED = frozenset(
    {
        "chưa công bố",
        "chưa có",
        "chưa ban hành",
        "sẽ thông báo sau",
        "thông báo sau",
        "chưa xác định",
    }
)
_NOT_APPLICABLE = frozenset({"không áp dụng", "n/a", "na", "k/a"})
_CODE_HEADER_RE = re.compile(r"^(?:mã|code|id|số hiệu|ký hiệu)\b", re.IGNORECASE)
_GROUP_HEADER_RE = re.compile(r"^(?:nhóm|khối|lĩnh vực|phân nhóm|khoa)\b", re.IGNORECASE)
_NAME_HEADER_RE = re.compile(
    r"^(?:tên|ngành|chương trình|đối tượng|nội dung|môn|hạng mục|"
    r"nhiệm vụ|công việc|chỉ tiêu|trường hợp)\b",
    re.IGNORECASE,
)
_ORDINAL_HEADER_RE = re.compile(r"^(?:stt|tt|no\.?|#)$", re.IGNORECASE)
_SUMMARY_ROW_RE = re.compile(
    r"^(?:tổng\s+cộng|tổng\s+số|tổng\s+chỉ\s+tiêu|tổng|cộng|total|subtotal|grand\s+total)\b",
    re.IGNORECASE,
)
_INLINE_NOTE_RE = re.compile(
    r"^(?:ghi\s+chú|lưu\s+ý|chú\s+thích|chú\s+ý|nguồn|note|\(\*\)|\*|"
    r"áp\s+dụng|riêng\s+(?:đối\s+với|cho|ngành|nhóm|đơn\s+vị)|điều\s+kiện|"
    r"trường\s+hợp|ngoại\s+lệ|ngoại\s+trừ)",
    re.IGNORECASE,
)
_GROUP_PREFIX_RE = re.compile(r"^(?:[ivxlcdm]+|\d+|[a-z])[.)]\s+", re.IGNORECASE)
_MAX_FALLBACK_NAME_CHARS = 120


class ScopedNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str
    scope: NoteScope
    target: str = ""
    text: str
    source_citation: str | None = None


class FactAttributeValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    value_kind: ValueKind
    is_truncated: bool = False
    detail_md_pointer: str | None = None
    source_cell_ref: str | None = None


class UniversalFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str
    row_index: int
    row_kind: RowKind = "data"
    row_pointer: str
    group: str | None = None
    subject_code: str | None = None
    subject_name: str | None = None
    data_year: int | None = None
    data_status: DataStatus = "unknown"
    attributes: dict[str, FactAttributeValue] = Field(default_factory=dict)
    detail_md_pointers: dict[str, str] = Field(default_factory=dict)
    applicable_note_ids: list[str] = Field(default_factory=list)
    source_cell_refs: list[str] = Field(default_factory=list)
    cross_references: list[str] = Field(default_factory=list)


class RawTableRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_index: int
    cells: list[str]
    is_colspan: bool = False
    source_cell_refs: list[str] = Field(default_factory=list)


class TableSchemaSummary(BaseModel):
    """Exact table metadata exposed to Slice 3 query_facts before filtering jsonb."""

    model_config = ConfigDict(extra="forbid")

    table_id: str
    source_table_citation: str
    title: str
    has_header: bool
    storage_mode: StorageMode
    keep_whole_in_chunk: bool
    column_keys: list[str]
    data_years: list[int]
    row_count: int
    data_row_count: int
    scoped_note_ids: list[str] = Field(default_factory=list)


class UniversalTableProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = VERSION
    table_id: str
    source_table_citation: str
    title: str = ""
    has_header: bool
    storage_mode: StorageMode
    keep_whole_in_chunk: bool = False
    lead_in_pointer: str | None = None
    data_years: list[int] = Field(default_factory=list)
    column_keys: list[str] = Field(default_factory=list)
    scoped_notes: list[ScopedNote] = Field(default_factory=list)
    facts: list[UniversalFact] = Field(default_factory=list)
    raw_rows: list[RawTableRow] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)

    def table_schema(self) -> TableSchemaSummary:
        data_rows = len({f.row_index for f in self.facts if f.row_kind == "data"})
        return TableSchemaSummary(
            table_id=self.table_id,
            source_table_citation=self.source_table_citation,
            title=self.title,
            has_header=self.has_header,
            storage_mode=self.storage_mode,
            keep_whole_in_chunk=self.keep_whole_in_chunk,
            column_keys=list(self.column_keys),
            data_years=list(self.data_years),
            row_count=len(self.facts) if self.facts else len(self.raw_rows),
            data_row_count=data_rows,
            scoped_note_ids=[note.note_id for note in self.scoped_notes],
        )


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split()).casefold()


def _clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split())


def classify_value(raw_text: str, *, defined_symbols: set[str] | None = None) -> ValueKind:
    """Classify cell value without ever coercing leading-zero codes into integers."""
    cleaned = _clean(raw_text)
    if not cleaned:
        return "empty_cell"
    lowered = cleaned.casefold()
    if lowered in _NOT_PUBLISHED:
        return "not_published"
    if lowered in _NOT_APPLICABLE:
        return "not_applicable"
    normalized_symbols = {_clean(s) for s in (defined_symbols or set()) if _clean(s)}
    if cleaned in normalized_symbols:
        return "defined_symbol"
    if _ZERO_RE.fullmatch(cleaned):
        return "numeric_zero"
    if not any(ch.isalnum() for ch in cleaned):
        return "undefined_symbol"
    return "normal"


def _cell_ref(source_table_citation: str, cell: dict) -> str | None:
    evidence_id = cell.get("evidence_id")
    if not evidence_id:
        return None
    run_id = source_table_citation.split(":", 1)[0] if ":" in source_table_citation else ""
    return f"{run_id}:{evidence_id}" if run_id else str(evidence_id)


def _grid(positions: list[CellPosition]) -> dict[tuple[int, int], CellPosition]:
    """Unmerge & fill physical grid: every covered (row, col) points to its source cell."""
    mapping: dict[tuple[int, int], CellPosition] = {}
    for pos in positions:
        for r in range(pos.row, pos.row + pos.cell["row_span"]):
            for c in range(pos.column, pos.column + pos.cell["col_span"]):
                mapping[r, c] = pos
    return mapping


def _column_paths(
    grid: dict[tuple[int, int], CellPosition],
    headers: list[int],
    column_count: int,
) -> dict[int, list[str]]:
    paths: dict[int, list[str]] = {}
    for col in range(column_count):
        parts: list[str] = []
        seen_ids: set[int] = set()
        for row in headers:
            pos = grid.get((row, col))
            if pos is None or id(pos) in seen_ids:
                continue
            seen_ids.add(id(pos))
            label = _clean(pos.cell["text"])
            if label:
                parts.append(label)
        paths[col] = parts or [f"Cột {col + 1}"]
    return paths


def _unique_column_names(
    paths: dict[int, list[str]],
    *,
    strip_year: int | None = None,
) -> dict[int, str]:
    """Flatten multi-tier header paths; strip the tier naming strip_year when split by year."""
    names: dict[int, str] = {}
    used: dict[str, int] = {}
    year_token = str(strip_year) if strip_year is not None else None
    for col in sorted(paths):
        parts = list(paths[col])
        if year_token is not None and len(parts) > 1:
            filtered = [p for p in parts if not re.search(rf"(?<!\d){year_token}(?!\d)", p)]
            if filtered:
                parts = filtered
        base = " > ".join(parts)
        count = used.get(base, 0) + 1
        used[base] = count
        names[col] = base if count == 1 else f"{base} ({count})"
    return names


def _to_raw_rows(
    structure: dict,
    positions: list[CellPosition],
    source_table_citation: str,
) -> list[RawTableRow]:
    by_row: dict[int, list[CellPosition]] = {}
    for pos in positions:
        by_row.setdefault(pos.row, []).append(pos)
    result: list[RawTableRow] = []
    for row_idx in structure["row_indices"]:
        row_cells = sorted(by_row.get(row_idx, []), key=lambda p: p.column)
        refs = [
            ref
            for pos in row_cells
            if (ref := _cell_ref(source_table_citation, pos.cell)) is not None
        ]
        result.append(
            RawTableRow(
                row_index=row_idx,
                cells=[_clean(pos.cell["text"]) for pos in row_cells],
                is_colspan=any(pos.cell["col_span"] > 1 for pos in row_cells),
                source_cell_refs=list(dict.fromkeys(refs)),
            )
        )
    return result


def _classify_row_kind(
    row_idx: int,
    col_count: int,
    row_positions: list[CellPosition],
) -> tuple[RowKind, str | None]:
    """Classify body row as data, summary, group_header, or inline_note."""
    own_cells = sorted(
        (pos for pos in row_positions if pos.row == row_idx),
        key=lambda p: p.column,
    )
    non_empty = [pos for pos in own_cells if _clean(pos.cell["text"])]
    if not non_empty:
        return "data", None

    # Full-width (or single-cell wide colspan) row inside table body
    if len(non_empty) == 1 and non_empty[0].cell["col_span"] == col_count and col_count > 1:
        banner_text = _clean(non_empty[0].cell["text"])
        if _INLINE_NOTE_RE.search(banner_text):
            return "inline_note", banner_text
        if _SUMMARY_ROW_RE.search(banner_text):
            return "summary", banner_text
        if len(banner_text) > 80 or banner_text.endswith("."):
            return "inline_note", banner_text
        return "group_header", banner_text

    # Summary row check on leading textual cells (e.g. "Tổng cộng", "Cộng", "Total")
    for pos in non_empty[:2]:
        text = _clean(pos.cell["text"])
        if _SUMMARY_ROW_RE.search(text):
            return "summary", text
        if pos.cell["col_span"] >= max(2, col_count - 1) and _INLINE_NOTE_RE.search(text):
            return "inline_note", text

    return "data", None


def _detect_role_columns(
    paths: dict[int, list[str]],
    data_rows: list[int],
    grid: dict[tuple[int, int], CellPosition],
    year_columns: set[int],
) -> tuple[int | None, int | None, int | None]:
    """Identify (group_col, code_col, name_col) generically from headers and spans."""
    non_year_cols = [c for c in sorted(paths) if c not in year_columns]
    group_col: int | None = None
    code_col: int | None = None
    name_col: int | None = None

    for col in non_year_cols:
        leaf = paths[col][-1]
        if _ORDINAL_HEADER_RE.fullmatch(leaf):
            continue
        if code_col is None and _CODE_HEADER_RE.search(leaf):
            code_col = col
        elif group_col is None and _GROUP_HEADER_RE.search(leaf):
            group_col = col
        elif name_col is None and _NAME_HEADER_RE.search(leaf):
            name_col = col

    if group_col is None:
        for col in non_year_cols:
            if col in {code_col, name_col} or _ORDINAL_HEADER_RE.fullmatch(paths[col][-1]):
                continue
            has_vertical_span = any(
                (pos := grid.get((r, col))) is not None
                and pos.cell["row_span"] > 1
                and any(ch.isalpha() for ch in pos.cell["text"])
                for r in data_rows
            )
            if has_vertical_span:
                group_col = col
                break

    if name_col is None:
        candidates = [
            c
            for c in non_year_cols
            if c not in {code_col, group_col} and not _ORDINAL_HEADER_RE.fullmatch(paths[c][-1])
        ]
        # Never pick a long prose column (e.g. 400-word description) as subject_name;
        # pick the first short textual column with alphabetic labels instead.
        for col in candidates:
            texts = [
                _clean(grid[r, col].cell["text"])
                for r in data_rows
                if (r, col) in grid and _clean(grid[r, col].cell["text"])
            ]
            if not texts:
                continue
            has_alpha = any(any(ch.isalpha() for ch in t) for t in texts)
            if has_alpha and max(len(t) for t in texts) <= _MAX_FALLBACK_NAME_CHARS:
                name_col = col
                break
    return group_col, code_col, name_col


def _build_attribute(
    raw_text: str,
    *,
    source_cell_ref: str | None,
    fallback_pointer: str,
    defined_symbols: set[str] | None,
    long_cell_word_limit: int,
) -> FactAttributeValue:
    cleaned = _clean(raw_text)
    kind = classify_value(cleaned, defined_symbols=defined_symbols)
    words = cleaned.split()
    if len(words) > long_cell_word_limit:
        preview = " ".join(words[:DEFAULT_PREVIEW_WORDS]) + "..."
        return FactAttributeValue(
            raw=preview,
            value_kind=kind,
            is_truncated=True,
            detail_md_pointer=source_cell_ref or fallback_pointer,
            source_cell_ref=source_cell_ref,
        )
    return FactAttributeValue(
        raw=cleaned,
        value_kind=kind,
        is_truncated=False,
        detail_md_pointer=None,
        source_cell_ref=source_cell_ref,
    )


def _group_matches(norm_group: str, target: str) -> bool:
    if not norm_group or not target:
        return False
    stripped = _GROUP_PREFIX_RE.sub("", norm_group, count=1).strip()
    pattern = re.compile(rf"^{re.escape(target)}(?:$|\s*[-–—:(,/])")
    return bool(pattern.match(norm_group) or pattern.match(stripped))


def _match_notes(
    notes: list[ScopedNote],
    *,
    group: str | None,
    subject_code: str | None,
    subject_name: str | None,
    row_index: int,
    data_year: int | None,
) -> list[str]:
    matched: list[str] = []
    norm_group = _norm(group or "")
    norm_code = _norm(subject_code or "")
    norm_name = _norm(subject_name or "")
    row_str = str(row_index)
    year_str = str(data_year) if data_year is not None else ""

    for note in notes:
        target = _norm(note.target)
        applies = False
        if note.scope == "table":
            applies = True
        elif note.scope == "group":
            applies = _group_matches(norm_group, target)
        elif note.scope == "row":
            applies = bool(target and target in {norm_code, norm_name, row_str})
        elif note.scope == "column_year":
            applies = bool(target and year_str and target == year_str)
        if applies and note.note_id not in matched:
            matched.append(note.note_id)
    return matched


def project_table(
    table: dict,
    *,
    table_id: str,
    source_table_citation: str,
    title: str = "",
    lead_in_pointer: str | None = None,
    column_years: dict[int, int] | None = None,
    year_statuses: dict[int, DataStatus] | None = None,
    scoped_notes: list[ScopedNote] | None = None,
    defined_symbols: set[str] | None = None,
    long_cell_word_limit: int = DEFAULT_LONG_CELL_WORDS,
    small_table_row_limit: int = DEFAULT_SMALL_TABLE_ROWS,
    cross_references: list[str] | None = None,
    inherited_header_rows: list[list[dict]] | None = None,
) -> UniversalTableProjection:
    """Project one canonical table into Universal Facts (all headed tables) or raw_rows."""
    structure = table if "row_indices" in table else table_structure(table)
    notes = list(scoped_notes or [])
    positions, errors = layout(structure)
    if errors:
        return UniversalTableProjection(
            table_id=table_id,
            source_table_citation=source_table_citation,
            title=title,
            has_header=False,
            storage_mode="invalid",
            keep_whole_in_chunk=False,
            lead_in_pointer=lead_in_pointer,
            scoped_notes=notes,
            issues=errors,
        )

    headers = header_rows(structure)
    candidate_tbl = table
    if "column_count" not in candidate_tbl and "original_column_count" in candidate_tbl:
        candidate_tbl = {**candidate_tbl, "column_count": candidate_tbl["original_column_count"]}

    if not headers and "rows" in candidate_tbl and "column_count" in candidate_tbl:
        from qnu.domains.knowledge.index.table_dependencies import (
            header_row,
            multitier_header,
            typed_header,
        )

        multi = multitier_header(candidate_tbl)
        if multi is not None:
            headers = multi
        elif typed_header(candidate_tbl):
            headers = [0]
        elif header_row(candidate_tbl):
            headers = [0]

    if not headers and inherited_header_rows:
        col_count = candidate_tbl.get("column_count") or structure.get("original_column_count", 0)
        if col_count and len(inherited_header_rows[0]) == col_count:
            import copy

            prepended_rows = [copy.deepcopy(r) for r in inherited_header_rows]
            for r in prepended_rows:
                for c in r:
                    c["header"] = True
            synth_tbl = {
                "rows": prepended_rows + copy.deepcopy(candidate_tbl["rows"]),
                "column_count": col_count,
            }
            return project_table(
                synth_tbl,
                table_id=table_id,
                source_table_citation=source_table_citation,
                title=title,
                lead_in_pointer=lead_in_pointer,
                column_years=column_years,
                year_statuses=year_statuses,
                scoped_notes=scoped_notes,
                defined_symbols=defined_symbols,
                long_cell_word_limit=long_cell_word_limit,
                small_table_row_limit=small_table_row_limit,
                cross_references=cross_references,
                inherited_header_rows=None,
            )

    if not headers:
        return UniversalTableProjection(
            table_id=table_id,
            source_table_citation=source_table_citation,
            title=title,
            has_header=False,
            storage_mode="raw_rows",
            keep_whole_in_chunk=True,
            lead_in_pointer=lead_in_pointer,
            scoped_notes=notes,
            raw_rows=_to_raw_rows(structure, positions, source_table_citation),
        )

    grid = _grid(positions)
    col_count = structure["original_column_count"]
    paths = _column_paths(grid, headers, col_count)
    body_rows = [r for r in structure["row_indices"] if r not in headers]
    col_year_map = {
        col: year for col, year in (column_years or {}).items() if 0 <= col < col_count
    }
    distinct_years = sorted(set(col_year_map.values()))
    statuses = year_statuses or {}

    positions_by_row: dict[int, list[CellPosition]] = {}
    for pos in positions:
        positions_by_row.setdefault(pos.row, []).append(pos)

    row_classifications: dict[int, tuple[RowKind, str | None]] = {
        row_idx: _classify_row_kind(row_idx, col_count, positions_by_row.get(row_idx, []))
        for row_idx in body_rows
    }
    pure_data_rows = [r for r in body_rows if row_classifications[r][0] == "data"]
    keep_whole = len(pure_data_rows) < small_table_row_limit

    year_cols = set(col_year_map)
    shared_cols = [c for c in range(col_count) if c not in year_cols]
    group_col, code_col, name_col = _detect_role_columns(
        paths, pure_data_rows or body_rows, grid, year_cols
    )
    shared_names = _unique_column_names({c: paths[c] for c in shared_cols})

    year_groups: list[tuple[int | None, list[int], dict[int, str]]] = []
    if distinct_years:
        for year in distinct_years:
            cols_for_year = [c for c in range(col_count) if col_year_map.get(c) == year]
            year_names = _unique_column_names(
                {c: paths[c] for c in cols_for_year}, strip_year=year
            )
            year_groups.append((year, cols_for_year, year_names))
    else:
        year_groups.append((None, [], {}))

    all_column_keys: list[str] = []
    facts: list[UniversalFact] = []
    xrefs = list(cross_references or [])
    active_banner_group: str | None = None

    for row_idx in body_rows:
        row_kind, banner_text = row_classifications[row_idx]
        if row_kind == "group_header":
            active_banner_group = banner_text
            own_refs = [
                ref
                for pos in positions_by_row.get(row_idx, [])
                if (ref := _cell_ref(source_table_citation, pos.cell)) is not None
            ]
            facts.append(
                UniversalFact(
                    fact_id=f"{table_id}:r{row_idx}",
                    row_index=row_idx,
                    row_kind="group_header",
                    row_pointer=f"{source_table_citation}:r{row_idx}",
                    group=banner_text,
                    subject_name=banner_text,
                    source_cell_refs=list(dict.fromkeys(own_refs)),
                    cross_references=list(xrefs),
                )
            )
            continue

        if row_kind == "inline_note":
            own_refs = [
                ref
                for pos in positions_by_row.get(row_idx, [])
                if (ref := _cell_ref(source_table_citation, pos.cell)) is not None
            ]
            facts.append(
                UniversalFact(
                    fact_id=f"{table_id}:r{row_idx}",
                    row_index=row_idx,
                    row_kind="inline_note",
                    row_pointer=f"{source_table_citation}:r{row_idx}",
                    group=active_banner_group,
                    subject_name=banner_text,
                    source_cell_refs=list(dict.fromkeys(own_refs)),
                    cross_references=list(xrefs),
                )
            )
            continue

        group_val = (
            _clean(grid[row_idx, group_col].cell["text"])
            if group_col is not None and (row_idx, group_col) in grid
            else None
        ) or active_banner_group
        code_val = (
            _clean(grid[row_idx, code_col].cell["text"])
            if code_col is not None and (row_idx, code_col) in grid
            else None
        ) or None
        name_val = (
            _clean(grid[row_idx, name_col].cell["text"])
            if name_col is not None and (row_idx, name_col) in grid
            else None
        ) or (banner_text if row_kind == "summary" else None)

        for year, cols_for_year, year_names in year_groups:
            attributes: dict[str, FactAttributeValue] = {}
            detail_pointers: dict[str, str] = {}
            cell_refs: list[str] = []

            selected_cols = [
                *((col_idx, shared_names[col_idx]) for col_idx in shared_cols),
                *((col_idx, year_names[col_idx]) for col_idx in cols_for_year),
            ]
            for col_idx, col_name in selected_cols:
                pos = grid.get((row_idx, col_idx))
                raw_text = pos.cell["text"] if pos is not None else ""
                ref = _cell_ref(source_table_citation, pos.cell) if pos is not None else None
                if ref and ref not in cell_refs:
                    cell_refs.append(ref)
                attr = _build_attribute(
                    raw_text,
                    source_cell_ref=ref,
                    fallback_pointer=f"{source_table_citation}:r{row_idx}:c{col_idx}",
                    defined_symbols=defined_symbols,
                    long_cell_word_limit=long_cell_word_limit,
                )
                attributes[col_name] = attr
                if attr.detail_md_pointer:
                    detail_pointers[col_name] = attr.detail_md_pointer
                if col_name not in all_column_keys:
                    all_column_keys.append(col_name)

            year_suffix = f":y{year}" if year is not None else ""
            fact_id = f"{table_id}:r{row_idx}{year_suffix}"
            status: DataStatus = statuses.get(year, "unknown") if year is not None else "unknown"
            applicable = _match_notes(
                notes,
                group=group_val,
                subject_code=code_val,
                subject_name=name_val,
                row_index=row_idx,
                data_year=year,
            )
            facts.append(
                UniversalFact(
                    fact_id=fact_id,
                    row_index=row_idx,
                    row_kind=row_kind,
                    row_pointer=f"{source_table_citation}:r{row_idx}",
                    group=group_val,
                    subject_code=code_val,
                    subject_name=name_val,
                    data_year=year,
                    data_status=status,
                    attributes=attributes,
                    detail_md_pointers=detail_pointers,
                    applicable_note_ids=applicable,
                    source_cell_refs=cell_refs,
                    cross_references=list(xrefs),
                )
            )

    return UniversalTableProjection(
        table_id=table_id,
        source_table_citation=source_table_citation,
        title=title,
        has_header=True,
        storage_mode="facts",
        keep_whole_in_chunk=keep_whole,
        lead_in_pointer=lead_in_pointer,
        data_years=distinct_years,
        column_keys=all_column_keys,
        scoped_notes=notes,
        facts=facts,
    )
