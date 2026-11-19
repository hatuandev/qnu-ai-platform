"""Source-bound annotations; unknown values never match a filter."""

import re
from datetime import date as Date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from qnu.domains.knowledge.compilation.table_year import (
    column_year_proof,
    conversion_year_scopes,
    labelled_years,
    table_year_headers,
    year_mentions,
)
from qnu.domains.knowledge.index.table_dependencies import multitier_header, typed_header
from qnu.domains.knowledge.index.table_layout import header_rows, layout, table_structure
from qnu.domains.knowledge.source_sections import source_sections
from qnu.platform.errors import AppException

MetadataScalar = (
    Annotated[str, Field(strict=True, min_length=1, max_length=500)]
    | StrictBool
    | StrictInt
    | Annotated[float, Field(strict=True, allow_inf_nan=False)]
)
MetadataAttributes = Annotated[
    dict[Annotated[str, Field(min_length=1, max_length=80)], MetadataScalar],
    Field(min_length=1, max_length=20),
]


def same_attribute(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right


def value_parts(text: str) -> tuple[str, ...] | None:
    parts = tuple(" ".join(part.split()).casefold() for part in text.split(","))
    return parts if len(parts) > 1 and all(parts) else None


def same_listed(left: str, right: str) -> bool:
    left_parts, right_parts = value_parts(left), value_parts(right)
    return (
        left_parts is not None
        and right_parts is not None
        and frozenset(left_parts) == frozenset(right_parts)
    )


def attribute_contains(stored: object, requested: object) -> bool:
    """A stored list value contains a requested element in any order.

    Exact scalars keep type-sensitive equality; a '; '-joined value matches
    each of its elements, and a comma list matches as an unordered set.
    """
    if same_attribute(stored, requested):
        return True
    if not isinstance(stored, str) or not isinstance(requested, str):
        return False
    return any(
        element and (same_attribute(element, requested) or same_listed(element, requested))
        for element in (part.strip() for part in stored.split(";"))
    )


def list_value(text: str) -> str | None:
    """Canonical '; '-joined value when every item is a comma list of short names.

    A shape rule only: it recognizes combination-list structure and never
    consults a subject dictionary. Single names, numeric lists and long
    parenthesized names stay out.
    """
    items = []
    for raw in re.split(r"[\n;]+", text):
        item = raw.strip()
        if len(item) >= 2 and item.startswith("(") and item.endswith(")"):
            item = item[1:-1]
        parts = [" ".join(part.split()) for part in item.split(",")]
        if len(parts) < 2:
            return None
        for part in parts:
            if (
                not 1 <= len(part) <= 30
                or len(part.split()) > 6
                or any(ch.isdigit() for ch in part)
                or not any(ch.isalpha() for ch in part)
            ):
                return None
        items.append(", ".join(parts))
    canonical = "; ".join(items)
    return canonical if canonical and len(canonical) <= 500 else None


def merge_scope(base: dict, extra: dict) -> dict:
    scope = {**base, **extra}
    if "attributes" in scope:
        scope["attributes"] = {**(base.get("attributes") or {}), **(extra.get("attributes") or {})}
    return scope


def scope_conflicts(fixed: dict, requested: dict) -> bool:
    pinned = fixed.get("attributes") or {}
    return any(
        key in fixed and fixed[key] != value
        for key, value in requested.items()
        if key != "attributes"
    ) or any(
        key in pinned and not attribute_contains(pinned[key], requested_value)
        for key, requested_value in requested.get("attributes", {}).items()
    )


EventKind = Literal[
    "registration_deadline", "exam_date", "result_date", "fee_deadline", "enrollment_confirmation"
]


class EventMoment(BaseModel):
    """One normalized moment; partial dates keep the precision of the source."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    date: Date | None = None
    year: int | None = Field(None, strict=True, ge=1990, le=2100)
    month: int | None = Field(None, strict=True, ge=1, le=12)
    day: int | None = Field(None, strict=True, ge=1, le=31)
    time: str | None = Field(None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def shape(self):
        if self.date is not None:
            if self.year is not None or self.month is not None or self.day is not None:
                raise ValueError("Mốc đầy đủ không đi kèm ngày/tháng/năm rời.")
            return self
        if self.month is None:
            raise ValueError("Mốc thiếu năm cần ít nhất tháng.")
        if self.day is not None and self.year is not None:
            raise ValueError("Ngày đủ năm phải dùng trường date.")
        if self.day is not None:
            try:
                Date(2000, self.month, self.day)
            except ValueError:
                raise ValueError("Ngày/tháng không hợp lệ.") from None
        return self


class RelativeDeadline(BaseModel):
    """A duration anchored to a named source event, never converted without a start date."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    value: int = Field(strict=True, ge=1, le=366)
    unit: Literal["day", "working_day", "week", "month"]
    from_event: str = Field(min_length=3, max_length=200)


class EventValue(BaseModel):
    """One source-bound schedule event, keeping its original label and scope."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: EventKind
    label: str = Field(min_length=2, max_length=200)
    moment: EventMoment | None = None
    window_start: EventMoment | None = None
    relative: RelativeDeadline | None = None
    dates: list[Date] | None = Field(
        None, min_length=2, max_length=31, exclude_if=lambda value: value is None
    )
    end_exclusive: Literal[True] | None = Field(None, exclude_if=lambda value: value is None)
    intake: str | None = Field(None, min_length=1, max_length=120)
    audience: str | None = Field(None, min_length=1, max_length=160)
    method: str | None = Field(None, min_length=1, max_length=160)
    clause: str | None = Field(None, min_length=1, max_length=160)
    note: str | None = Field(None, min_length=1, max_length=120)
    supersedes: str | None = Field(None, min_length=3, max_length=200)

    @model_validator(mode="after")
    def shape(self):
        modes = (
            bool(self.moment or self.window_start),
            self.relative is not None,
            self.dates is not None,
        )
        if sum(modes) > 1:
            raise ValueError("Sự kiện chỉ dùng một cách biểu diễn thời gian.")
        if not any(modes):
            raise ValueError("Sự kiện cần mốc thời gian hoặc thời hạn tương đối.")
        if self.dates is not None and len(set(self.dates)) != len(self.dates):
            raise ValueError("Danh sách ngày của sự kiện không được trùng lặp.")
        if self.end_exclusive is not None and self.moment is None:
            raise ValueError("Cần có mốc kết thúc để xác định hạn trước thời điểm đó.")
        if (
            self.window_start is not None
            and self.moment is not None
            and self.window_start.date is not None
            and self.moment.date is not None
            and self.moment.date < self.window_start.date
        ):
            raise ValueError("Khoảng thời gian không hợp lệ.")
        return self


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def _numeric_moment_forms(moment: EventMoment) -> list[str]:
    if moment.date is not None:
        parts = (moment.date.day, moment.date.month, moment.date.year)
        return [
            f"{day}{separator}{month}{separator}{year}"
            for day in {str(parts[0]), f"{parts[0]:02d}"}
            for month in {str(parts[1]), f"{parts[1]:02d}"}
            for separator in ("/", "-", ".")
            for year in {str(parts[2])}
        ]
    if moment.day is not None and moment.month is not None:
        return [
            f"{day}{separator}{month}"
            for day in {str(moment.day), f"{moment.day:02d}"}
            for month in {str(moment.month), f"{moment.month:02d}"}
            for separator in ("/", ".")
        ]
    if moment.year is not None and moment.month is not None:
        return [
            f"{month}{separator}{moment.year}"
            for month in {str(moment.month), f"{moment.month:02d}"}
            for separator in ("/", ".")
        ]
    return []


def moment_in_quote(moment: EventMoment, quote: str) -> bool:
    text = _normalized(quote)
    if moment.date is not None:
        written = (
            f"{prefix}{day} tháng {month} năm {moment.date.year}"
            for prefix in ("ngày ", "")
            for day in {str(moment.date.day), f"{moment.date.day:02d}"}
            for month in {str(moment.date.month), f"{moment.date.month:02d}"}
        )
    elif moment.day is not None and moment.month is not None:
        written = (
            f"{prefix}{day} tháng {month}"
            for prefix in ("ngày ", "")
            for day in {str(moment.day), f"{moment.day:02d}"}
            for month in {str(moment.month), f"{moment.month:02d}"}
        )
    elif moment.year is not None and moment.month is not None:
        written = (
            f"tháng {month} năm {moment.year}"
            for month in {str(moment.month), f"{moment.month:02d}"}
        )
    else:
        written = ()
    matched = any(phrase in text for phrase in written) or any(
        re.search(r"(?<![\d/.\-])" + re.escape(form) + r"(?!\d)(?![/.\-]\s*\d)", text)
        for form in _numeric_moment_forms(moment)
    )
    if not matched:
        return False
    if moment.time is None:
        return True
    hour, minute = moment.time.split(":")
    return any(
        candidate in text
        for candidate in (
            moment.time,
            f"{int(hour)}:{minute}",
            f"{int(hour)}h{minute}",
            f"{int(hour)} giờ {minute}",
            f"{hour} giờ {minute}",
        )
    )


def _scope_literals(event: EventValue) -> list[str]:
    return [
        value
        for value in (
            event.intake,
            event.audience,
            event.method,
            event.clause,
            event.note,
            event.supersedes,
        )
        if value
    ]


def event_proved(event: EventValue, quotes: list[str]) -> bool:
    """Read historical publications under their original literal-proof contract."""
    if (
        event.kind in {"fee_deadline", "enrollment_confirmation"}
        or event.dates is not None
        or event.end_exclusive is not None
    ):
        from qnu.domains.knowledge.event_schedule import event_proved as has_matching_event

        return has_matching_event(event, quotes)
    texts = [_normalized(quote) for quote in quotes]

    def stated(literal: str) -> bool:
        return any(_normalized(literal) in text for text in texts)

    if not stated(event.label):
        return False
    if event.relative is not None:
        unit = {
            "day": "ngày",
            "working_day": "ngày làm việc",
            "week": "tuần",
            "month": "tháng",
        }[event.relative.unit]
        if not stated(f"{event.relative.value} {unit}"):
            return False
        if not stated(event.relative.from_event):
            return False
    moments = [moment for moment in (event.window_start, event.moment) if moment is not None]
    if not moments and event.relative is None:
        return False
    if not all(any(moment_in_quote(moment, quote) for quote in quotes) for moment in moments):
        return False
    return all(stated(value) for value in _scope_literals(event))


LifecycleStatus = Literal["active", "amended", "superseded", "deprecated"]


class LifecycleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: LifecycleStatus = "active"
    effective_from: Date | None = None
    effective_until: Date | None = None
    amends_ref: str | None = Field(None, min_length=1, max_length=200)
    superseded_by_ref: str | None = Field(None, min_length=1, max_length=200)
    amendment_summary: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def interval(self):
        if (
            self.effective_from
            and self.effective_until
            and self.effective_from > self.effective_until
        ):
            raise ValueError("Khoảng hiệu lực lifecycle không hợp lệ.")
        return self


class MetadataValues(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    data_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    issued_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    effective_from: Date | None = None
    effective_until: Date | None = None
    program: str | None = Field(None, min_length=1, max_length=160)
    intake: str | None = Field(None, min_length=1, max_length=160)
    attributes: MetadataAttributes | None = None
    events: list[EventValue] | None = Field(None, min_length=1, max_length=20)
    lifecycle: LifecycleMetadata | None = None
    scope_facets: MetadataAttributes | None = None

    @model_validator(mode="after")
    def interval(self):
        if (
            self.effective_from
            and self.effective_until
            and self.effective_from > self.effective_until
        ):
            raise ValueError("Khoảng hiệu lực không hợp lệ.")
        return self


class MetadataFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    data_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    issued_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    event_year: int | None = Field(
        None, strict=True, ge=1000, le=9999, exclude_if=lambda value: value is None
    )
    event_kind: EventKind | None = Field(None, exclude_if=lambda value: value is None)
    event_method: str | None = Field(
        None, min_length=1, max_length=160, exclude_if=lambda value: value is None
    )
    effective_on: Date | None = None
    program: str | None = Field(None, min_length=1, max_length=160)
    intake: str | None = Field(None, min_length=1, max_length=160)

    attributes: MetadataAttributes | None = Field(None, exclude_if=lambda value: value is None)
    lifecycle_status: LifecycleStatus | None = Field(None, exclude_if=lambda value: value is None)
    scope_facets: MetadataAttributes | None = Field(None, exclude_if=lambda value: value is None)
    include_superseded: bool = False


class MetadataEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    citation: str = Field(min_length=3, max_length=200)
    quote: str = Field(min_length=1, max_length=2000)


class RetrievalAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: str = Field(min_length=1, max_length=260)
    values: MetadataValues
    evidence: list[MetadataEvidence] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.values.model_dump(exclude_none=True):
            raise ValueError("Annotation cần ít nhất một giá trị có căn cứ.")
        if self.target.startswith("section:") and not self.target[8:]:
            raise ValueError("Annotation cần dẫn chứng tiêu đề mục.")
        if self.target == "document" and any(
            (self.values.data_year, self.values.program, self.values.intake)
        ):
            raise ValueError("Năm dữ liệu/ngành/đợt phải gắn đoạn hoặc hàng/ô cụ thể.")
        if self.target == "document" and self.values.events:
            raise ValueError("Lịch và thời hạn phải gắn đoạn hoặc hàng/ô cụ thể.")
        return self


def _invalid(message: str) -> AppException:
    return AppException(message, code="retrieval_metadata_invalid", status_code=422)


def _table_entry(content: dict, citation: str) -> dict | None:
    return next((t for t in content["source_tables"] if t["citation"] == citation), None)


def _grid(entry: dict) -> tuple[dict, list | None]:
    """Physical column grid, or None when the source table geometry is broken."""
    shape = table_structure(entry["table"])
    positions, errors = layout(shape)
    return shape, None if errors else positions


def _refs(entry: dict, cells: list[dict]) -> set[str]:
    run = entry["citation"].split(":", 1)[0]
    return {entry["citation"], *[run + ":" + cell["evidence_id"] for cell in cells]}


def _row_refs(entry: dict, row: int, column: int | None) -> set[str]:
    """Cells covering the physical row, plus row-local list coordinates for old proofs."""
    refs = set()
    shape, positions = _grid(entry)
    if positions is not None and 0 <= row < shape["original_row_count"]:
        covering = [
            position
            for position in positions
            if position.row <= row < position.row + position.cell["row_span"]
            and (
                column is None
                or position.column <= column < position.column + position.cell["col_span"]
            )
        ]
        if covering:
            refs |= _refs(entry, [position.cell for position in covering])
    try:
        cells = entry["table"]["rows"][row]
        if column is not None:
            cells = [cells[column]]
        if not cells:
            raise IndexError
    except IndexError:
        return refs
    return refs | _refs(entry, cells)


def _column_refs(entry: dict, index: int) -> set[str]:
    """Cells covering the physical column, plus row-local coordinates for old proofs."""
    refs = {entry["citation"]}
    _, positions = _grid(entry)
    if positions is not None:
        covering = [
            position
            for position in positions
            if position.column <= index < position.column + position.cell["col_span"]
        ]
        refs |= _refs(entry, [position.cell for position in covering])
    for row in entry["table"]["rows"]:
        start = 0
        for cell in row:
            span = cell.get("col_span") or 1
            if start <= index < start + span:
                refs.add(entry["citation"].split(":", 1)[0] + ":" + cell["evidence_id"])
                break
            start += span
    return refs


def _header_refs(entry: dict, index: int) -> set[str]:
    """Header cells governing the physical column of a cell target."""
    shape, positions = _grid(entry)
    if positions is None:
        return set()
    headers = set(header_rows(shape) or multitier_header(entry["table"]) or [])
    run = entry["citation"].split(":", 1)[0]
    return {
        run + ":" + position.cell["evidence_id"]
        for position in positions
        if position.row in headers
        and position.column <= index < position.column + position.cell["col_span"]
    }


def _carried_first_row(table: dict) -> bool:
    rows = table.get("rows") or []
    return bool(rows and rows[0] and not rows[0][0]["text"].strip())


def _continues_numbering(previous: dict, table: dict) -> bool:
    """Identity column resumes one number after the previous table's last row."""
    before, rows = previous.get("rows") or [], table.get("rows") or []
    if not before or not rows or not before[-1] or not rows[0]:
        return False
    last = before[-1][0]["text"].strip()
    first = rows[0][0]["text"].strip()
    return last.isdigit() and first.isdigit() and int(first) == int(last) + 1


def _local_header_labels(entry: dict) -> dict[int, tuple[str, str]]:
    """Header label text and citation per physical column, local to one table.

    Only single-tier labels are kept: a joined multi-tier label has no single
    source quote to prove, so those columns stay without an attribute path.
    """
    shape, positions = _grid(entry)
    if positions is None:
        return {}
    headers = (
        header_rows(shape)
        or multitier_header(entry["table"])
        or ([0] if typed_header(entry["table"]) else [])
    )
    if not headers:
        return {}
    run = entry["citation"].split(":", 1)[0]
    pieces: dict[int, list[str]] = {}
    refs: dict[int, str] = {}
    for position in positions:
        if position.row not in headers:
            continue
        text = " ".join(position.cell["text"].split())
        if not text:
            continue
        for column in range(position.column, position.column + position.cell["col_span"]):
            pieces.setdefault(column, []).append(text)
            refs.setdefault(column, run + ":" + position.cell["evidence_id"])
    return {
        column: (refs[column], texts[0])
        for column, texts in pieces.items()
        if len(texts) == 1 and len(texts[0]) <= 80
    }


def table_chain_labels(tables: list[dict]) -> dict[str, dict[int, tuple[str, str]]]:
    """Header labels inherited down page-adjacent continuation tables of one run.

    Continuation proof needs the same run and width, the next page, and either
    a carried first row whose identity cells are empty, or an identity column
    that resumes one number after the previous table's last row.
    """
    labels_by_table: dict[str, dict[int, tuple[str, str]]] = {}
    previous: tuple[str, int | None, int, dict[int, tuple[str, str]], dict] | None = None
    for entry in tables:
        citation = entry["citation"]
        run, columns = citation.split(":", 1)[0], entry["table"].get("column_count") or 0
        labels = _local_header_labels(entry)
        if not labels and previous is not None:
            previous_run, previous_page, previous_columns, previous_labels, previous_table = (
                previous
            )
            if (
                previous_run == run
                and previous_page is not None
                and previous_page + 1 == entry.get("page_number")
                and previous_columns == columns
                and previous_labels
                and (
                    _carried_first_row(entry["table"])
                    or _continues_numbering(previous_table, entry["table"])
                )
            ):
                labels = previous_labels
        if labels:
            labels_by_table[citation] = labels
        previous = (run, entry.get("page_number"), columns, labels, entry["table"])
    return labels_by_table


def target_refs(content: dict, target: str, outline: dict | None = None) -> set[str]:
    if target == "document":
        return set(content["citations"])
    if target.startswith("section:"):
        ref = target.removeprefix("section:")
        section = (outline or {}).get(ref)
        if section is None or section.citation != ref:
            raise _invalid("Annotation cần trỏ đến tiêu đề mục trong nguồn đã ghim.")
        return {ref}
    paragraph = re.fullmatch(r"paragraph:(\d+):(\d+)", target)
    if paragraph:
        try:
            section, index = map(int, paragraph.groups())
            return set(content["sections"][section]["paragraphs"][index]["citations"])
        except IndexError:
            raise _invalid("Annotation trỏ đến đoạn không tồn tại.") from None
    table = re.fullmatch(r"table:(.+):row:(\d+)(?::column:(\d+))?", target)
    if table:
        citation, row, column = table.groups()
        entry = _table_entry(content, citation)
        if entry is None:
            raise _invalid("Annotation trỏ đến hàng/ô không tồn tại.")
        refs = _row_refs(entry, int(row), int(column) if column is not None else None)
        if not refs:
            raise _invalid("Annotation trỏ đến hàng/ô không tồn tại.")
        if column is not None:
            refs |= _header_refs(entry, int(column))
        return refs
    column = re.fullmatch(r"table:(.+):column:(\d+)", target)
    if column:
        citation, index = column.group(1), int(column.group(2))
        entry = _table_entry(content, citation)
        if entry is None or index >= (entry["table"].get("column_count") or 0):
            raise _invalid("Annotation trỏ đến cột không tồn tại.")
        return _column_refs(entry, index)
    raise _invalid(
        "Target phải là document, section:citation, paragraph:s:p hoặc "
        "table:citation:row:r[:column:c] / table:citation:column:c."
    )


def attribute_in_quote(label: str, value: str | float | bool, quote: str) -> bool:
    folded = quote.casefold()
    if label.casefold() not in folded:
        return False
    literal = re.escape(str(value).casefold())
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return re.search(r"(?<![\w.,])" + literal + r"(?!\w|[.,]\d)", folded) is not None
    return re.search(r"(?<!\w)" + literal + r"(?!\w)", folded) is not None


def _structural_attribute_proof(
    item: RetrievalAnnotation,
    label: str,
    value: str,
    content: dict,
    labels: dict[str, dict[int, tuple[str, str]]],
) -> bool:
    """A row attribute is proven by the chain header governing a matching list cell.

    Evidence must cite that header cell with exactly the stored label; the
    value itself is proven by the cell's canonical list form.
    """
    target = re.fullmatch(r"table:(.+):row:(\d+)", item.target)
    if target is None or not isinstance(value, str):
        return False
    citation, row = target.group(1), int(target.group(2))
    entry = _table_entry(content, citation)
    if entry is None:
        return False
    columns = labels.get(citation) or {}
    _, positions = _grid(entry)
    if positions is None:
        return False
    for position in positions:
        cell = position.cell
        if (
            position.row != row
            or cell.get("row_span") != 1
            or cell.get("col_span") != 1
            or list_value(cell.get("text", "")) != value
        ):
            continue
        header = columns.get(position.column)
        if header is None or header[1] != label:
            continue
        if any(
            evidence.citation == header[0] and " ".join(evidence.quote.split()) == label
            for evidence in item.evidence
        ):
            return True
    return False


def _mentions_year(text: str, year: int) -> bool:
    return re.search(r"(?<!\d)" + str(year) + r"(?!\d)", text) is not None


def _proved_by_evidence(item: RetrievalAnnotation, refs: set[str], year: int) -> bool:
    return any(
        evidence.citation in refs and _mentions_year(evidence.quote, year)
        for evidence in item.evidence
    )


def _require_row_year_proof(item: RetrievalAnnotation, entry: dict, row: int, year: int) -> None:
    """A row data_year is proven by a labelled year cell inside that same row."""
    _, positions = _grid(entry)
    cells = (
        [
            position.cell
            for position in positions
            if position.row <= row < position.row + position.cell["row_span"]
        ]
        if positions is not None
        else []
    )
    try:
        cells = [*cells, *entry["table"]["rows"][row]]
    except IndexError:
        raise _invalid("Annotation trỏ đến hàng không tồn tại.") from None
    run = entry["citation"].split(":", 1)[0]
    proofs = {
        run + ":" + cell["evidence_id"]
        for cell in cells
        if labelled_years(cell.get("text", "")) == {year}
        and year_mentions(cell.get("text", "")) == {year}
    }
    if not _proved_by_evidence(item, proofs, year):
        raise _invalid("Năm dữ liệu của hàng cần dẫn chứng từ ô nêu năm trong hàng.")


def _require_table_year_proof(item: RetrievalAnnotation, content: dict) -> None:
    """A table data_year is proven by its governing header, read in full."""
    year = item.values.data_year
    if year is None:
        return
    cell = re.fullmatch(r"table:(.+):row:(\d+):column:(\d+)", item.target)
    column = re.fullmatch(r"table:(.+):column:(\d+)", item.target)
    row = None if cell else re.fullmatch(r"table:(.+):row:(\d+)", item.target)
    match = cell or column or row
    if match is None:
        return
    entry = _table_entry(content, match.group(1))
    if entry is None:
        raise _invalid("Annotation trỏ đến bảng không tồn tại.")
    if row is not None:
        _require_row_year_proof(item, entry, int(row.group(2)), year)
        return
    index = int(cell.group(3)) if cell else int(column.group(2))
    shape, positions = _grid(entry)
    if positions is None:
        raise _invalid("Không đọc được cấu trúc bảng để xác định tiêu đề cột.")
    tiers, allow_bare = table_year_headers(entry["table"], shape)
    headers = set(tiers)
    governing = [
        position
        for position in positions
        if position.row in headers
        and position.column <= index < position.column + position.cell["col_span"]
    ]
    # The whole governing header text is inspected: a short quote must not hide
    # a role, and a multi-year child header must not inherit one parent year.
    proven, proof_cells = column_year_proof(
        [position.cell for position in governing], allow_bare_year=allow_bare
    )
    run = entry["citation"].split(":", 1)[0]
    proofs = {run + ":" + position["evidence_id"] for position in proof_cells}
    known = {proven} if proven is not None else set()
    if cell is not None:
        target_cell = next(
            (
                position.cell
                for position in positions
                if position.row == int(cell.group(2)) and position.column == int(cell.group(3))
            ),
            None,
        )
        if target_cell is not None:
            text = target_cell.get("text", "")
            own = labelled_years(text)
            if not own or year_mentions(text) != own:
                own = set()
            known |= own
            if own == {year}:
                proofs.add(run + ":" + target_cell["evidence_id"])
    if known != {year}:
        raise _invalid("Năm dữ liệu của ô/cột không xác định đúng một năm.")
    if not _proved_by_evidence(item, proofs, year):
        raise _invalid("Năm dữ liệu cần dẫn chứng từ ô tiêu đề chi phối hoặc chính ô nêu năm.")


def validate_annotations(
    annotations: list[dict],
    content: dict,
    documents: list[dict],
    *,
    strict_roles: bool = False,
) -> None:
    texts = {}
    for document in documents:
        prefix = document["ocr_run_id"] + ":"
        for page in document["pages"]:
            for block in page["blocks"]:
                texts[prefix + block["evidence_id"]] = block["text"]
                for row in (block.get("table") or {}).get("rows", []):
                    for cell in row:
                        texts[prefix + cell["evidence_id"]] = cell["text"]
    outline = (
        source_sections(documents)
        if any(a["target"].startswith("section:") for a in annotations)
        else {}
    )
    seen = set()
    conversion = None
    fragmented = None
    chain_labels = None
    global_values = next((a["values"] for a in annotations if a["target"] == "document"), {})
    for raw in annotations:
        item = RetrievalAnnotation.model_validate(raw)
        if item.target == "document" and len(documents) != 1:
            raise _invalid("Bản biên soạn nhiều nguồn cần metadata ở từng đoạn/hàng/ô.")
        if item.target in seen:
            raise _invalid("Target metadata bị trùng; gộp các trường vào một annotation.")
        seen.add(item.target)
        refs = target_refs(content, item.target, outline)
        # A proof in the same OCR run is not necessarily a proof for this unit.
        # For parsed table rows/cells the table-wide text is also too broad.
        local_texts = texts
        table = re.fullmatch(
            r"table:(.+):row:(\d+)(?::column:(\d+))?", item.target
        ) or re.fullmatch(r"table:(.+):column:(\d+)", item.target)
        conversion_bound = False
        structural = table is not None and bool(item.values.attributes)
        structural_refs: set[str] = set()
        if table:
            table_ref = table.group(1)
            if structural:
                if chain_labels is None:
                    chain_labels = table_chain_labels(content["source_tables"])
                structural_refs = {
                    header[0] for header in (chain_labels.get(table_ref) or {}).values()
                }
            if item.values.data_year is not None and any(
                e.citation not in refs for e in item.evidence
            ):
                if conversion is None:
                    conversion = conversion_year_scopes(documents)
                conversion_bound = _proved_conversion_year(item, conversion.get(table_ref))
            if conversion_bound:
                refs |= {proof["citation"] for proof in conversion[table_ref][1]}
            local_texts = {
                **texts,
                table_ref: "\n".join(texts.get(r, "") for r in sorted(refs - {table_ref})),
            }
        for evidence in item.evidence:
            if (
                evidence.citation not in content["citations"]
                or (evidence.citation not in refs and evidence.citation not in structural_refs)
                or evidence.quote not in texts.get(evidence.citation, "")
                or evidence.quote not in local_texts.get(evidence.citation, "")
            ):
                raise _invalid("Trích đoạn metadata không thuộc nguồn đã ghim của target.")
        quotes = "\n".join(e.quote for e in item.evidence).casefold()
        for key, value in item.values.model_dump(mode="json", exclude_none=True).items():
            if key == "events":
                continue
            if key != "attributes" and key in global_values and global_values[key] != value:
                raise _invalid("Metadata của target mâu thuẫn với metadata toàn văn bản.")
            if key == "attributes":
                for label, entry in value.items():
                    global_attributes = global_values.get("attributes", {})
                    if label in global_attributes and (
                        type(global_attributes[label]) is not type(entry)
                        or global_attributes[label] != entry
                    ):
                        raise _invalid("Thuộc tính mâu thuẫn với metadata toàn văn bản.")
                    if not any(
                        attribute_in_quote(label, entry, e.quote) for e in item.evidence
                    ) and not (
                        structural
                        and _structural_attribute_proof(
                            item, label, entry, content, chain_labels or {}
                        )
                    ):
                        raise _invalid("Nhãn và giá trị metadata cần có trong trích đoạn nguồn.")
                continue
            alternatives = [str(value)]
            if key.startswith("effective_"):
                day = Date.fromisoformat(value)
                alternatives += [
                    f"{d}{sep}{m}{sep}{day.year}"
                    for d in {str(day.day), f"{day.day:02d}"}
                    for m in {str(day.month), f"{day.month:02d}"}
                    for sep in ("/", "-")
                ] + [
                    f"ngày {d} tháng {m} năm {day.year}"
                    for d in {str(day.day), f"{day.day:02d}"}
                    for m in {str(day.month), f"{day.month:02d}"}
                ]
            found = any(v.casefold() in quotes for v in alternatives)
            if key.endswith("_year"):
                found = _mentions_year(quotes, value)
            if not found:
                raise _invalid("Giá trị metadata cần xuất hiện trong trích đoạn nguồn.")
        for event in item.values.events or []:
            if _event_evidence_valid(event, item.evidence, texts, strict_roles):
                continue
            if fragmented is None:
                from qnu.domains.knowledge.event_schedule import fragmented_proofs

                fragmented = list(fragmented_proofs(documents))
            stated = [evidence.model_dump() for evidence in item.evidence]
            if not any(
                event == candidate and all(part in stated for part in proof)
                for candidate, proof in fragmented
            ):
                raise _invalid(
                    "Sự kiện cần nhãn, mốc thời gian và phạm vi trong cùng trích đoạn nguồn."
                )
        if strict_roles and not conversion_bound:
            _require_table_year_proof(item, content)


def _proved_conversion_year(
    item: RetrievalAnnotation, scope: tuple[int, list[dict]] | None
) -> bool:
    if scope is None or not re.fullmatch(r"table:.+:column:\d+", item.target):
        return False
    year, evidence = scope
    stated = [entry.model_dump() for entry in item.evidence]
    return item.values.model_dump(exclude_none=True) == {"data_year": year} and all(
        proof in stated for proof in evidence
    )


def _event_evidence_valid(
    event: EventValue, evidence: list[MetadataEvidence], texts: dict[str, str], strict_roles: bool
) -> bool:
    if not strict_roles:
        return event_proved(event, [item.quote for item in evidence])
    # The extractor uses these metadata models. Import it at the validation boundary.
    from qnu.domains.knowledge.event_schedule import event_proved as has_matching_event

    return any(
        has_matching_event(event, [item.quote])
        and has_matching_event(event, [texts[item.citation]])
        for item in evidence
    )


def chunk_metadata(annotations: list[dict], targets: set[str]) -> list[dict]:
    global_item = next((a for a in annotations if a["target"] == "document"), {})
    global_values = global_item.get("values", {})
    global_evidence = global_item.get("evidence", [])
    selected = [a for a in annotations if a["target"] in targets]
    result = []
    for item in selected:
        values = {**global_values, **item["values"]}
        if "attributes" in values:
            values["attributes"] = {
                **global_values.get("attributes", {}),
                **item["values"].get("attributes", {}),
            }
        result.append(
            {
                "target": item["target"],
                "values": values,
                "evidence": [*global_evidence, *item["evidence"]],
            }
        )
    return result or (
        [{"target": "document", "values": global_values, "evidence": global_evidence}]
        if global_values
        else []
    )


def matches_metadata(structure: dict | None, scope: MetadataFilter) -> bool:
    wanted = scope.model_dump(mode="json", exclude_none=True)
    event_kind = wanted.pop("event_kind", None)
    event_year = wanted.pop("event_year", None)
    event_method = wanted.pop("event_method", None)
    include_superseded = wanted.pop("include_superseded", False)
    lifecycle_status = wanted.pop("lifecycle_status", None)
    scope_facets = wanted.pop("scope_facets", None)
    event_scope = any(value is not None for value in (event_kind, event_year, event_method))
    event_intake = wanted.pop("intake", None) if event_scope else None

    annotations = (structure or {}).get("retrieval_metadata", [])
    if not annotations:
        struct = structure or {}
        lifecycle = struct.get("lifecycle") or {}
        status = lifecycle.get("status", "active")
        if not include_superseded and lifecycle_status is None and status == "superseded":
            return False
        if lifecycle_status is not None and status != lifecycle_status:
            return False
        if scope_facets:
            facets = struct.get("scope_facets") or struct.get("attributes") or {}
            if not all(attribute_contains(facets.get(k), v) for k, v in scope_facets.items()):
                return False
        if not wanted and not event_scope:
            return True

    for annotation in annotations:
        values = annotation["values"]
        lifecycle = values.get("lifecycle") or {}
        status = lifecycle.get("status", "active")
        if not include_superseded and lifecycle_status is None and status == "superseded":
            continue
        if lifecycle_status is not None and status != lifecycle_status:
            continue
        if scope_facets:
            facets = values.get("scope_facets") or values.get("attributes") or {}
            if not all(attribute_contains(facets.get(k), v) for k, v in scope_facets.items()):
                continue
        if event_scope and not any(
            (event_kind is None or event.get("kind") == event_kind)
            and (event_year is None or event_year in event_years(event))
            and (
                event_method is None
                or (event.get("method") or "").casefold() == event_method.casefold()
            )
            and (
                event_intake is None
                or (event.get("intake") or "").casefold() == event_intake.casefold()
            )
            for event in values.get("events") or []
        ):
            continue
        matches = True
        for key, value in wanted.items():
            if key == "attributes":
                current = values.get("attributes") or {}
                matches &= all(attribute_contains(current.get(k), v) for k, v in value.items())
            elif key == "effective_on":
                # An annotated validity interval is open-ended on a missing side.
                # A unit with neither boundary stays unknown and never matches.
                start = values.get("effective_from")
                end = values.get("effective_until")
                matches &= bool(start or end) and (not start or str(start) <= str(value))
                matches &= not end or str(value) <= str(end)
            elif key == "intake":
                # An intake named by the source unit or by one of its schedule
                # events both scope this unit; events carry their own intake.
                requested = str(value).casefold()
                matches &= str(values.get("intake", "")).casefold() == requested or any(
                    isinstance(event, dict)
                    and str(event.get("intake") or "").casefold() == requested
                    for event in values.get("events") or []
                )
            else:
                matches &= str(values.get(key, "")).casefold() == str(value).casefold()
        if matches:
            return True
    return False


def event_years(event: dict) -> set[int]:
    years = {Date.fromisoformat(day).year for day in event.get("dates") or []}
    for key in ("window_start", "moment"):
        moment = event.get(key) or {}
        if moment.get("date"):
            years.add(Date.fromisoformat(moment["date"]).year)
        elif moment.get("year") is not None:
            years.add(moment["year"])
    return years
