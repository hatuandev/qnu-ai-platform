"""Plan, project and merge structural compilation parts within a model budget.

The immutable input snapshot keeps every block, table cell and citation. A model
request only receives the projected blocks/rows owned by one part plus structural
context that the part actually needs: the header rows of its own tables, the
caption/heading that introduces them and document notes that qualify them.

Legacy v2/v3 request shapes remain reproducible for already-planned runs. The v4
planner retains possible conditions with unresolved scope and never infers table
identity from equal headers. It measures estimated written output instead of the
source size. Nothing is cropped: a unit that cannot fit is rejected.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from itertools import pairwise

from pydantic import ValidationError

from qnu.domains.knowledge.compilation import segments_v2
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.drafting import SYSTEM_PROMPT
from qnu.domains.knowledge.compilation.evidence import citation_index, literal_tables
from qnu.domains.knowledge.compilation.limitations import retain_limitations
from qnu.domains.knowledge.compilation.projection import (
    citations_in,
    project_block,
    project_documents,
    project_table_block,
)
from qnu.domains.knowledge.compilation.quality import (
    NO_ERROR_FOUND,
    NOT_CHECKED,
    PARTIALLY_CHECKED,
    quality_validation,
)
from qnu.domains.knowledge.compilation.schemas import SegmentDraftContent
from qnu.domains.knowledge.compilation.supplement import (
    SELECTIVE_PROMPT,
    SUPPLEMENT_PROMPT,
    SupplementPart,
)
from qnu.domains.knowledge.compilation.units import (
    Unit,
    _ref_key,
    build_units,
    header_row_indexes,
    owned_refs,
)
from qnu.domains.modelops.inference.service import (
    available_input_tokens,
    request_input_tokens,
)
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage

PROJECTION_V2 = "qnu.compiler.projection/v2"
PROJECTION_V3 = "qnu.compiler.projection/v3"
PROJECTION_V4 = "qnu.compiler.projection/v4"
PROJECTION_SUPPLEMENT = "qnu.compiler.projection/supplement-v1"
PROJECTION_SELECTIVE = "qnu.compiler.projection/selective-supplement-v1"
SUPPLEMENT_PROJECTIONS = {PROJECTION_SUPPLEMENT, PROJECTION_SELECTIVE}
PROMPT_VERSION = "qnu.compiler.segment.prompt/v4"
PLANNER_VERSION = "qnu.compiler.plan/v5"
MANIFEST_VERSION = "qnu.compiler.segment-manifest/v2"

PROMPT_VERSIONS = {
    PROJECTION_V2: segments_v2.PROMPT_VERSION,
    PROJECTION_V3: "qnu.compiler.segment.prompt/v3",
    PROJECTION_V4: PROMPT_VERSION,
    PROJECTION_SUPPLEMENT: "qnu.compiler.supplement.prompt/v3",
    PROJECTION_SELECTIVE: "qnu.compiler.selective-supplement.prompt/v3",
}

TARGET_RATIO = 0.7
# Planning heuristic, not a tokenizer. Half of the declared output allowance is
# reserved for the written content; the rest stays for reasoning, JSON keys and
# citation lists. Vietnamese UTF-8 JSON needs roughly three bytes per token.
OUTPUT_CONTENT_SHARE = 0.5
OUTPUT_BYTES_PER_TOKEN = 3
# One owned table row only needs a note/condition, never a re-written row.
ROW_INTERPRETATION_BYTES = 96
SECTION_FRAMING_BYTES = 160
# Retained only to reproduce the frozen v3 request. New plans never discard
# possible conditions just because they exceed an arbitrary length/count.
NOTE_TAIL_MAX_BLOCKS = 6
NOTE_TAIL_MAX_BYTES = 4000
HEADING_TYPES = {"title", "header"}
NOTE_TYPES = {"caption", "footnote"}


@dataclass(frozen=True, slots=True)
class TableLayout:
    page_index: int
    block_index: int
    page_number: int
    evidence_id: str
    header_rows: tuple[int, ...]
    signature: tuple
    row_count: int


@dataclass(frozen=True, slots=True)
class Layout:
    """Structural index of one document, computed once per planning run."""

    reading: tuple[tuple[int, int], ...]
    headings: tuple[tuple[int, int, int, str, str], ...]
    tables: dict[tuple[int, int], TableLayout]
    captions: dict[tuple[int, int], tuple[dict, ...]]
    trailing_notes: tuple[dict, ...]
    note_tail_blocks: int
    note_tail_bytes: int
    table_links: tuple[dict, ...]


@dataclass(frozen=True, slots=True)
class SegmentPlan:
    index: int
    owned: tuple[dict, ...]
    context: tuple[dict, ...]
    scope: str
    input_sha256: str
    input_tokens: int
    schema_sha256: str | None
    units: tuple[Unit, ...] = field(default=(), compare=False)
    output_size_estimate: int = 0
    projection: str = PROJECTION_V4

    def scope_dict(self) -> dict:
        return {
            "index": self.index,
            "scope": self.scope,
            "owned": list(self.owned),
            "context": list(self.context),
            "input_sha256": self.input_sha256,
            "input_tokens": self.input_tokens,
            "schema_sha256": self.schema_sha256,
            "output_size_estimate": self.output_size_estimate,
            "projection_version": self.projection,
        }


def _invalid(detail: str, code: str) -> AppException:
    return AppException(detail, code=code, status_code=422)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def input_capacity(limits, output_tokens: int) -> int | None:
    """Backward-compatible name; the shared ModelOps helper owns the math."""
    return available_input_tokens(limits, output_tokens)


def output_content_bytes(output_tokens: int | None) -> int | None:
    """Estimated bytes the model may spend on written content for one part."""
    if not output_tokens:
        return None
    return int(output_tokens * OUTPUT_CONTENT_SHARE * OUTPUT_BYTES_PER_TOKEN)


def prompt_version_for(projection: str) -> str:
    version = PROMPT_VERSIONS.get(projection)
    if version is None:
        raise AppException(
            "Phần biên soạn dùng phiên bản projection không hỗ trợ.",
            code="compilation_segment_version_unsupported",
            status_code=409,
        )
    return version


# --------------------------------------------------------------------------- layout


def _table_signature(rows: list[list[dict]], headers: tuple[int, ...], columns: int) -> tuple:
    if headers:
        return tuple(
            " ".join((cell.get("text") or "").strip() for cell in rows[index]) for index in headers
        )
    return ("columns", columns)


def build_layout(document: dict, *, legacy_v3: bool = False) -> Layout:
    """One pass over the document: headings, tables, captions, notes and links."""
    reading: list[tuple[int, int]] = []
    headings: list[tuple[int, int, int, str, str]] = []
    tables: dict[tuple[int, int], TableLayout] = {}
    captions: dict[tuple[int, int], tuple[dict, ...]] = {}
    blocks_at: dict[tuple[int, int], dict] = {}
    pages = document["pages"]
    last_table: tuple[int, int] | None = None
    for page_index, page in enumerate(pages):
        for block_index, block in enumerate(page["blocks"]):
            position = (page_index, block_index)
            reading.append(position)
            blocks_at[position] = block
            if block.get("type") in HEADING_TYPES and (block.get("text") or "").strip():
                headings.append(
                    (
                        page_index,
                        block_index,
                        page["page_number"],
                        block["evidence_id"],
                        block["text"],
                    )
                )
            table = block.get("table")
            if table and table.get("status") == "parsed":
                rows = table.get("rows") or []
                headers = header_row_indexes(rows)
                tables[position] = TableLayout(
                    page_index=page_index,
                    block_index=block_index,
                    page_number=page["page_number"],
                    evidence_id=block["evidence_id"],
                    header_rows=headers,
                    signature=_table_signature(rows, headers, table["column_count"]),
                    row_count=table["row_count"],
                )
                last_table = position
    order = {position: index for index, position in enumerate(reading)}
    for position in tables:
        found: list[dict] = []
        start = order[position] - 1
        while start >= 0 and len(found) < 2:
            previous = reading[start]
            block = blocks_at[previous]
            if (
                block.get("table") is not None
                or block.get("type") not in HEADING_TYPES | NOTE_TYPES
            ):
                break
            found.append(
                {
                    "kind": "block",
                    "ocr_run_id": document["ocr_run_id"],
                    "page": pages[previous[0]]["page_number"],
                    "evidence_id": block["evidence_id"],
                    "role": "caption",
                }
            )
            start -= 1
        captions[position] = tuple(reversed(found))
    notes: list[dict] = []
    tail_bytes = 0
    tail_blocks = 0
    if last_table is not None:
        for position in reading[order[last_table] + 1 :]:
            block = blocks_at[position]
            if block.get("table") is not None:
                continue
            tail_blocks += 1
            tail_bytes += len((block.get("text") or "").encode("utf-8"))
            notes.append(
                {
                    "kind": "block",
                    "ocr_run_id": document["ocr_run_id"],
                    "page": pages[position[0]]["page_number"],
                    "evidence_id": block["evidence_id"],
                    "role": "document_note",
                }
            )
    shared_notes = tuple(notes)
    if legacy_v3 and (tail_blocks > NOTE_TAIL_MAX_BLOCKS or tail_bytes > NOTE_TAIL_MAX_BYTES):
        shared_notes = ()
    if not legacy_v3:
        shared_notes = tuple({**ref, "scope": "unresolved"} for ref in shared_notes)
    links: list[dict] = []
    ordered = [tables[position] for position in reading if position in tables]
    for first, second in pairwise(ordered):
        # Header equality/page adjacency never prove source table identity.
        # Keep this heuristic solely for replay of already-pinned v3 bytes.
        if (
            legacy_v3
            and second.page_index == first.page_index + 1
            and second.signature == first.signature
        ):
            links.append(
                {
                    "from": first.evidence_id,
                    "to": second.evidence_id,
                    "from_page": first.page_number,
                    "to_page": second.page_number,
                }
            )
    return Layout(
        reading=tuple(reading),
        headings=tuple(headings),
        tables=tables,
        captions=captions,
        trailing_notes=shared_notes,
        note_tail_blocks=tail_blocks,
        note_tail_bytes=tail_bytes,
        table_links=tuple(links),
    )


def build_layouts(documents: list[dict], *, legacy_v3: bool = False) -> list[Layout]:
    return [build_layout(document, legacy_v3=legacy_v3) for document in documents]


def _heading_for(unit: Unit, layout: Layout) -> dict | None:
    chosen = None
    for page_index, block_index, page_number, evidence_id, _ in layout.headings:
        if (page_index, block_index) > (unit.page_index, unit.block_index):
            break
        chosen = (page_number, evidence_id)
    if chosen is None:
        return None
    return {
        "kind": "block",
        "ocr_run_id": unit.ocr_run_id,
        "page": chosen[0],
        "evidence_id": chosen[1],
        "role": "section_heading",
    }


def context_for(unit: Unit, document: dict, layout: Layout) -> list[dict]:
    """Context this unit actually needs, with an explicit role for each ref."""
    position = (unit.page_index, unit.block_index)
    refs: list[dict] = []
    table = layout.tables.get(position)
    if table is not None:
        if table.header_rows:
            refs.append(
                {
                    "kind": "table_header_rows",
                    "ocr_run_id": unit.ocr_run_id,
                    "page": table.page_number,
                    "evidence_id": table.evidence_id,
                    "rows": list(table.header_rows),
                    "role": "table_header",
                }
            )
        refs.extend(layout.captions.get(position, ()))
        refs.extend(_following_notes(document, unit, layout))
        heading = _heading_for(unit, layout)
        if heading is not None and heading["evidence_id"] != unit.evidence_id:
            refs.append(heading)
        refs.extend(layout.trailing_notes)
        return refs
    heading = _heading_for(unit, layout)
    if heading is not None and heading["evidence_id"] != unit.evidence_id:
        refs.append(heading)
    refs.extend(_adjacent_notes(document, unit))
    refs.extend(layout.trailing_notes)
    return refs


def _following_notes(document: dict, unit: Unit, layout: Layout) -> list[dict]:
    """Keep possible table qualifications until a new heading/table begins.

    These are candidates with unresolved scope, not proof that each note applies
    to every row. Text may contain conditions even when the parser labels it text.
    """
    position = (unit.page_index, unit.block_index)
    refs = []
    for page_index, block_index in layout.reading[layout.reading.index(position) + 1 :]:
        page = document["pages"][page_index]
        block = page["blocks"][block_index]
        if block.get("table") is not None or block.get("type") in HEADING_TYPES:
            break
        refs.append(
            {
                "kind": "block",
                "ocr_run_id": unit.ocr_run_id,
                "page": page["page_number"],
                "evidence_id": block["evidence_id"],
                "role": "neighbour_note",
                "scope": "unresolved",
            }
        )
    return refs


def _adjacent_notes(document: dict, unit: Unit) -> list[dict]:
    page = document["pages"][unit.page_index]
    refs: list[dict] = []
    for offset in (-2, -1, 1, 2):
        index = unit.block_index + offset
        if not 0 <= index < len(page["blocks"]):
            continue
        block = page["blocks"][index]
        if block.get("table") is not None or block.get("type") not in NOTE_TYPES:
            continue
        refs.append(
            {
                "kind": "block",
                "ocr_run_id": unit.ocr_run_id,
                "page": unit.page_number,
                "evidence_id": block["evidence_id"],
                "role": "neighbour_note",
            }
        )
    return refs


def _merge_context(
    documents: list[dict], units: list[Unit], layouts: list[Layout]
) -> tuple[dict, ...]:
    owned = {_ref_key(ref) for ref in owned_refs(units)}
    refs: list[dict] = []
    seen: set[tuple] = set()
    for unit in units:
        for ref in context_for(unit, documents[unit.document_index], layouts[unit.document_index]):
            key = _ref_key(ref)
            if key in owned or key in seen:
                continue
            seen.add(key)
            refs.append(ref)
    return tuple(refs)


def context_refs(documents: list[dict], units: list[Unit]) -> tuple[dict, ...]:
    """Union of structural context over the units, excluding anything owned here."""
    return _merge_context(documents, units, build_layouts(documents))


def structural_context(documents: list[dict], unit: Unit) -> list[dict]:
    """Kept for callers/tests: context of one unit inside its own document."""
    return context_for(
        unit, documents[unit.document_index], build_layout(documents[unit.document_index])
    )


# ------------------------------------------------------------------------- payload


def document_outline(documents: list[dict], layouts: list[Layout]) -> dict:
    """Compact structure: page count, table shapes and headings; no per-page blocks."""
    payload = []
    for document, layout in zip(documents, layouts, strict=True):
        tables = [
            {
                "evidence_id": layout.tables[position].evidence_id,
                "page": layout.tables[position].page_number,
                "row_count": layout.tables[position].row_count,
                "header_rows": len(layout.tables[position].header_rows),
            }
            for position in layout.reading
            if position in layout.tables
        ]
        payload.append(
            {
                "ocr_run_id": document["ocr_run_id"],
                "identity": document["identity"],
                "page_count": len(document["pages"]),
                "tables": tables[:60],
                "headings": [
                    {"page": page_number, "text": text[:200]}
                    for _, _, page_number, _, text in layout.headings[:40]
                ],
                "note_tail": {
                    "blocks": layout.note_tail_blocks,
                    "bytes": layout.note_tail_bytes,
                    "shared_as_context": bool(layout.trailing_notes),
                },
            }
        )
    return {"documents": payload}


def document_structure(documents: list[dict]) -> dict:
    """Backward-compatible name used by older callers and diagnostics."""
    return document_outline(documents, build_layouts(documents))


def _part_note(index: int, total: int) -> str:
    return (
        f"Phần {index}/{total}. Chỉ biên soạn khối/hàng trong owned; context_only chỉ "
        "để đối chiếu header, điều kiện và chú thích, không biên soạn lại. "
        "rows của refs bắt đầu từ 0; row_numbers trong bảng bắt đầu từ 1. "
        "Bảng literal do hệ thống ghép nguyên gốc: không chép lại ô, chỉ nêu điều kiện, "
        "ngoại lệ hoặc ghi chú cần thiết. Không suy nội dung phần khác."
    )


def build_projection(
    topic: str,
    documents: list[dict],
    owned: tuple[dict, ...] | list[dict],
    context: tuple[dict, ...] | list[dict],
    index: int,
    *,
    total: int | None = None,
    projection: str = PROJECTION_V4,
) -> tuple[dict, list[str]]:
    if projection == PROJECTION_V2:
        return segments_v2.build_projection(topic, documents, owned, context, index)
    if projection not in {PROJECTION_V3, PROJECTION_V4, *SUPPLEMENT_PROJECTIONS}:
        raise AppException(
            "Phần biên soạn dùng phiên bản projection không hỗ trợ.",
            code="compilation_segment_version_unsupported",
            status_code=409,
        )
    projected = project_documents(documents, owned, context)
    citations = citations_in(projected)
    layouts = (
        []
        if projection == PROJECTION_SELECTIVE
        else build_layouts(documents, legacy_v3=projection == PROJECTION_V3)
    )
    payload = {
        "topic": topic,
        "part": {
            "index": index,
            "total": total or index,
            "owned": list(owned),
            "context_only": list(context),
            "note": _part_note(index, total or index),
        },
        "outline": document_outline(documents, layouts) if layouts else {},
        "table_links": [link for layout in layouts for link in layout.table_links],
        "documents": projected,
        "allowed_citations": citations,
    }
    return payload, citations


def segment_system(index: int, total: int, *, projection: str = PROJECTION_V4) -> str:
    if projection == PROJECTION_V2:
        return segments_v2.segment_system(index, total)
    if projection == PROJECTION_SUPPLEMENT:
        return SUPPLEMENT_PROMPT
    if projection == PROJECTION_SELECTIVE:
        return SELECTIVE_PROMPT
    prompt = SYSTEM_PROMPT + (
        f"\nĐây là phần {index}/{total} của một tài liệu dài. Chỉ trả nội dung của phần "
        "này, viết gọn và không lặp lại nội dung phần khác. Không tạo lại bảng: hệ thống "
        "đã ghép đủ hàng/ô nguyên gốc. Chỉ nêu điều kiện, phạm vi, ngoại lệ hoặc ghi chú "
        "cần thiết cho owned; dùng context_only khi cần đối chiếu các ghi chú đó. "
        "Nếu owned rỗng hoặc không đủ căn cứ cho một nhận định, trả sections rỗng (hoặc "
        "bỏ nhận định đó) và ghi unknowns; không suy đoán. Không trích dẫn ID ngoài "
        "allowed_citations và không kiểm kê toàn bộ citation trong phản hồi."
    )

    if projection == PROJECTION_V3:
        return prompt  # Frozen request text for runs pinned before v4.
    return prompt + (
        "\nContext có scope=unresolved chỉ là căn cứ tiềm năng, không chứng minh ghi chú "
        "áp dụng cho mọi hàng. Chỉ gắn điều kiện khi nội dung nguồn xác định rõ phạm vi; "
        "nếu chưa rõ thì ghi unknowns. Không tự nối bảng chỉ vì cùng header hoặc số cột."
    )


def segment_schema(citations: list[str], projection: str = PROJECTION_V4) -> dict:
    contract = SupplementPart if projection in SUPPLEMENT_PROJECTIONS else SegmentDraftContent
    schema = contract.model_json_schema()
    if projection in SUPPLEMENT_PROJECTIONS:
        # Preserve the request fingerprints of already-planned structured jobs.
        # The wider schedule vocabulary is extracted from source by the server.
        properties = schema["$defs"]["EventValue"]["properties"]
        properties["kind"]["enum"] = ["registration_deadline", "exam_date", "result_date"]
        for field in ("dates", "end_exclusive"):
            del properties[field]
    schema["$defs"]["DraftParagraph"]["properties"]["citations"]["items"]["enum"] = citations
    return schema


def segment_messages(
    payload: dict, index: int, total: int, *, projection: str = PROJECTION_V4
) -> list[ChatMessage]:
    if projection == PROJECTION_V2:
        return segments_v2.segment_messages(payload, index, total)
    return [
        ChatMessage("system", segment_system(index, total, projection=projection)),
        ChatMessage("user", json.dumps(payload, ensure_ascii=False, sort_keys=True)),
    ]


# --------------------------------------------------------------------------- budget


class Budget:
    """Estimated cost of one request; exact bytes are recomputed before persisting.

    The estimate only drives packing. ``build_plan`` produces the real
    ``input_sha256``/``input_tokens`` that are persisted and verified.
    """

    def __init__(self, documents: list[dict], *, projection: str = PROJECTION_V4):
        self.documents = documents
        self.projection = projection
        self.layouts = build_layouts(documents)
        self.outline = (
            {} if projection == PROJECTION_SELECTIVE else document_outline(documents, self.layouts)
        )
        self.outline_bytes = len(
            json.dumps(self.outline, ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
        # The system prompt is sent with every part; ignoring it made small
        # capacities produce parts that could never fit.
        self.prompt_bytes = len(segment_system(1, 99, projection=projection).encode("utf-8")) + 384
        self._blocks = {
            (document["ocr_run_id"], block["evidence_id"]): block
            for document in documents
            for page in document["pages"]
            for block in page["blocks"]
        }
        self._unit: dict[tuple, int] = {}
        self._ref: dict[tuple, int] = {}

    def unit_bytes(self, unit: Unit) -> int:
        key = (unit.ocr_run_id, unit.evidence_id, unit.row_index)
        cached = self._unit.get(key)
        if cached is not None:
            return cached
        block = self.documents[unit.document_index]["pages"][unit.page_index]["blocks"][
            unit.block_index
        ]
        if unit.kind == "table_row":
            row = block["table"]["rows"][unit.row_index]
            citation = sum(
                len(f"{unit.ocr_run_id}:{cell['evidence_id']}".encode()) + 4 for cell in row
            )
            size = ROW_INTERPRETATION_BYTES + citation
        else:
            citation = len(f"{unit.ocr_run_id}:{block['evidence_id']}".encode()) + 4
            size = SECTION_FRAMING_BYTES + len((block.get("text") or "").encode("utf-8")) + citation
        self._unit[key] = size
        return size

    def ref_bytes(self, ref: dict) -> int:
        key = _ref_key(ref)
        cached = self._ref.get(key)
        if cached is not None:
            return cached
        block = self._blocks[(ref["ocr_run_id"], ref["evidence_id"])]
        projected = (
            project_block(block)
            if ref["kind"] == "block"
            else project_table_block(block, list(ref.get("rows", [])))
        )
        size = len(json.dumps(projected, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        self._ref[key] = size
        return size

    def output(self, units: list[Unit]) -> int:
        return 512 + sum(self.unit_bytes(unit) for unit in units)

    def input(self, units: list[Unit], context: tuple[dict, ...] | list[dict]) -> int:
        owned = sum(self.unit_bytes(unit) for unit in units)
        context_bytes = sum(self.ref_bytes(ref) for ref in context)
        # 128 B of JSON framing per ref plus ~34 B for its citation in the enum.
        fixed = 768 + self.prompt_bytes + self.outline_bytes + 162 * (len(units) + len(context))
        return int((fixed + owned + context_bytes) * 1.1)


def estimate_output_size(documents: list[dict], units: list[Unit]) -> int:
    """Estimated written bytes for the owned units of one part."""
    return Budget(documents).output(units)


def build_plan(
    *,
    index: int,
    units: list[Unit],
    documents: list[dict],
    topic: str,
    structured: bool,
    total_estimate: int,
    projection: str = PROJECTION_V4,
    budget: Budget | None = None,
) -> SegmentPlan:
    meter = budget or Budget(documents, projection=projection)
    owned = owned_refs(units)
    context = _merge_context(documents, units, meter.layouts)
    payload, citations = build_projection(
        topic, documents, owned, context, index, total=total_estimate, projection=projection
    )
    user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    schema = segment_schema(citations, projection) if structured else None
    messages = [
        ChatMessage("system", segment_system(index, total_estimate, projection=projection)),
        ChatMessage("user", user),
    ]
    return SegmentPlan(
        index=index,
        owned=owned,
        context=context,
        scope=_scope_text(units, documents),
        input_sha256=_sha(user.encode("utf-8")),
        input_tokens=request_input_tokens(messages, schema),
        schema_sha256=_sha(json_bytes(schema)) if schema is not None else None,
        units=tuple(units),
        output_size_estimate=meter.output(units),
        projection=projection,
    )


def _scope_text(units: list[Unit], documents: list[dict]) -> str:
    pages = sorted({unit.page_number for unit in units})
    blocks = sum(1 for unit in units if unit.kind == "block")
    rows = sum(1 for unit in units if unit.kind == "table_row")
    tables = len(
        {(unit.ocr_run_id, unit.evidence_id) for unit in units if unit.kind == "table_row"}
    )
    parts = [f"Trang {pages[0]}" if len(pages) == 1 else f"Trang {pages[0]}–{pages[-1]}"]
    if blocks:
        parts.append(f"{blocks} khối văn bản")
    if rows:
        parts.append(f"{rows} hàng của {tables} bảng")
    return "; ".join(parts)


def plan_segments(
    documents: list[dict],
    topic: str,
    *,
    capacity: int,
    structured: bool,
    target_ratio: float = TARGET_RATIO,
    output_tokens: int | None = None,
    projection: str = PROJECTION_V4,
    selected_units: list[Unit] | None = None,
) -> list[SegmentPlan]:
    """Pack units in reading order; split only at block boundaries or whole rows."""
    units = build_units(documents) if selected_units is None else selected_units
    if not units:
        raise _invalid("Nguồn không có khối để biên soạn.", "compilation_source_empty")
    target = max(1, min(capacity, max(1024, int(capacity * target_ratio))))
    output_target = output_content_bytes(output_tokens)
    meter = Budget(documents, projection=projection)
    plans: list[SegmentPlan] = []
    current: list[Unit] = []
    seen: set[tuple] = set()
    owned_blocks: set[tuple[str, int, str]] = set()
    owned_bytes = 0
    context_bytes = 0
    for unit in units:
        refs = context_for(unit, documents[unit.document_index], meter.layouts[unit.document_index])
        new_refs = [
            ref
            for ref in refs
            if _ref_key(ref) not in seen
            and not (
                ref["kind"] == "block"
                and (ref["ocr_run_id"], ref["page"], ref["evidence_id"]) in owned_blocks
            )
        ]
        unit_cost = meter.unit_bytes(unit)
        added_context = sum(meter.ref_bytes(ref) for ref in new_refs)
        estimate = int(
            (
                768
                + meter.prompt_bytes
                + meter.outline_bytes
                + 162 * (len(current) + 1 + len(seen) + len(new_refs))
                + owned_bytes
                + unit_cost
                + context_bytes
                + added_context
            )
            * 1.1
        )
        output_estimate = 512 + owned_bytes + unit_cost
        if current and (
            estimate > target or (output_target is not None and output_estimate > output_target)
        ):
            plans.append(
                build_plan(
                    index=len(plans) + 1,
                    units=current,
                    documents=documents,
                    topic=topic,
                    structured=structured,
                    total_estimate=max(2, len(plans) + 1),
                    projection=projection,
                    budget=meter,
                )
            )
            current, seen, owned_blocks = [], set(), set()
            owned_bytes = context_bytes = 0
            added_context = sum(meter.ref_bytes(ref) for ref in new_refs)
        if not current:
            _check_unit_fits(meter, unit, capacity, output_target, output_tokens)
        current.append(unit)
        owned_bytes += unit_cost
        if unit.kind == "block":
            owned_blocks.add((unit.ocr_run_id, unit.page_number, unit.evidence_id))
        seen.update(_ref_key(ref) for ref in new_refs)
        context_bytes += added_context
    if current:
        plans.append(
            build_plan(
                index=len(plans) + 1,
                units=current,
                documents=documents,
                topic=topic,
                structured=structured,
                total_estimate=max(2, len(plans) + 1),
                projection=projection,
                budget=meter,
            )
        )
    return plans


def _check_unit_fits(
    meter: Budget,
    unit: Unit,
    capacity: int,
    output_target: int | None,
    output_tokens: int | None,
) -> None:
    """A single row/block that cannot fit fails loudly instead of being cropped."""
    single = meter.output([unit])
    if output_target is not None and single > output_target:
        raise _invalid(
            "Một khối hoặc hàng bảng vượt mức lập kế hoạch đầu ra; cần ngân sách "
            "đầu ra lớn hơn hoặc nguồn có cấu trúc chi tiết hơn, không cắt nội dung.",
            "compilation_segment_output_too_large",
        )
    context = _merge_context(meter.documents, [unit], meter.layouts)
    if meter.input([unit], context) > capacity:
        raise _invalid(
            "Một khối hoặc hàng bảng vượt ngân sách model; không cắt nội dung.",
            "compilation_segment_too_large",
        )


def finalize_plans(
    plans: list[SegmentPlan],
    documents: list[dict],
    topic: str,
    *,
    capacity: int,
    structured: bool,
    projection: str = PROJECTION_V4,
    selected_units: list[Unit] | None = None,
) -> list[SegmentPlan]:
    """Rebuild every part with its final index/total and the exact request bound.

    The packing loop uses an estimate. Here the real ``input_tokens`` decides: a part
    that still exceeds capacity is split in half at a unit boundary, never cropped.
    """
    meter = Budget(documents, projection=projection)
    groups = [list(plan.units) for plan in plans]
    for plan in plans:
        if plan.projection != projection:
            raise _invalid(
                "Kế hoạch biên soạn trộn nhiều phiên bản projection.",
                "compilation_plan_invalid",
            )
    finalized: list[SegmentPlan] = []
    for _ in range(32):  # Each pass strictly grows the group count, so this ends.
        total = len(groups)
        finalized = [
            build_plan(
                index=position,
                units=units,
                documents=documents,
                topic=topic,
                structured=structured,
                total_estimate=total,
                projection=projection,
                budget=meter,
            )
            for position, units in enumerate(groups, start=1)
        ]
        overflow = [index for index, plan in enumerate(finalized) if plan.input_tokens > capacity]
        if not overflow:
            break
        for index in reversed(overflow):
            units = groups[index]
            if len(units) <= 1:
                raise _invalid(
                    "Một khối hoặc hàng bảng vượt ngân sách model; không cắt nội dung.",
                    "compilation_segment_too_large",
                )
            middle = len(units) // 2
            groups[index : index + 1] = [units[:middle], units[middle:]]
    else:
        raise _invalid(
            "Không chốt được kế hoạch biên soạn trong ngân sách model.",
            "compilation_segment_too_large",
        )
    expected_units = build_units(documents) if selected_units is None else selected_units
    expected = [ref for unit in expected_units for ref in owned_refs([unit])]
    actual = [ref for plan in finalized for ref in plan.owned]

    def atoms(refs):
        result = []
        for ref in refs:
            base = (ref["ocr_run_id"], ref["page"], ref["evidence_id"])
            result.extend((*base, row) for row in ref.get("rows", [None]))
        return result

    owned = atoms(actual)
    if len(owned) != len(set(owned)) or set(owned) != set(atoms(expected)):
        raise _invalid("Kế hoạch biên soạn thiếu hoặc trùng nguồn.", "compilation_plan_invalid")
    return finalized


def manifest_for(
    run,
    plans: list[SegmentPlan],
    documents: list[dict],
    *,
    capacity: int,
    output_tokens: int,
) -> dict:
    return {
        "schema_version": MANIFEST_VERSION,
        "planner_version": PLANNER_VERSION,
        "projection_version": plans[0].projection if plans else PROJECTION_V4,
        "run_id": run.id,
        "input_sha256": run.input_sha256,
        "topic": run.topic,
        "budget": {
            "input_capacity_tokens": capacity,
            "output_tokens": output_tokens,
            "target_ratio": TARGET_RATIO,
            "output_content_share": OUTPUT_CONTENT_SHARE,
            "output_bytes_per_token": OUTPUT_BYTES_PER_TOKEN,
            "output_content_bytes": output_content_bytes(output_tokens),
            "output_estimate_kind": "estimated_written_bytes_heuristic",
            "row_interpretation_bytes": ROW_INTERPRETATION_BYTES,
        },
        "segments": [plan.scope_dict() for plan in plans],
        "source": {
            "documents": [
                {
                    "ocr_run_id": document["ocr_run_id"],
                    "identity": document["identity"],
                    "canonical_sha256": document["canonical_sha256"],
                    "manifest_sha256": document["manifest_sha256"],
                    "page_count": len(document["pages"]),
                    "block_count": sum(len(page["blocks"]) for page in document["pages"]),
                    "table_count": sum(
                        1
                        for page in document["pages"]
                        for block in page["blocks"]
                        if block.get("table") is not None
                    ),
                    "cell_count": sum(
                        len(row)
                        for page in document["pages"]
                        for block in page["blocks"]
                        if block.get("table") is not None
                        for row in block["table"].get("rows", [])
                    ),
                }
                for document in documents
            ]
        },
    }


def plan_from_scope(scope: dict) -> SegmentPlan:
    return SegmentPlan(
        index=scope["index"],
        owned=tuple(scope.get("owned", [])),
        context=tuple(scope.get("context", [])),
        scope=scope.get("scope", ""),
        input_sha256=scope["input_sha256"],
        input_tokens=scope.get("input_tokens", 0),
        schema_sha256=scope.get("schema_sha256"),
        output_size_estimate=scope.get("output_size_estimate", 0),
        projection=scope.get("projection_version", PROJECTION_V2),
    )


def _parse_supplement(content: str) -> tuple[SupplementPart, int]:
    try:
        return SupplementPart.model_validate_json(content), 0
    except ValidationError as exc:
        rejected = set()
        for issue in exc.errors(include_input=False, include_context=False, include_url=False):
            location = issue["loc"]
            if len(location) < 2 or location[0] != "metadata" or not isinstance(location[1], int):
                raise
            rejected.add(location[1])
        payload = json.loads(content)
        payload["metadata"] = [
            item for index, item in enumerate(payload["metadata"]) if index not in rejected
        ]
        return SupplementPart.model_validate_json(json_bytes(payload)), len(rejected)


def parse_segment_draft(
    content: str, allowed_citations: set[str], projection: str = PROJECTION_V4
) -> dict:
    is_supplement = projection in SUPPLEMENT_PROJECTIONS
    try:
        if is_supplement:
            value, rejected = _parse_supplement(content)
        else:
            value, rejected = SegmentDraftContent.model_validate_json(content), 0
    except (ValidationError, ValueError) as exc:
        raise AppException(
            "LLM trả phần bản nháp sai schema.",
            code="compilation_draft_invalid",
            status_code=502,
        ) from exc
    for section in value.sections:
        for paragraph in section.paragraphs:
            if not paragraph.text.strip() or any(
                ref not in allowed_citations for ref in paragraph.citations
            ):
                raise AppException(
                    "Phần bản nháp có citation không thuộc nguồn của phần.",
                    code="compilation_citation_invalid",
                    status_code=502,
                )
    if isinstance(value, SupplementPart) and any(
        event.citation not in allowed_citations for event in value.events
    ):
        raise AppException(
            "Phần bản nháp có citation không thuộc nguồn của phần.",
            code="compilation_citation_invalid",
            status_code=502,
        )
    draft = value.model_dump(mode="json")
    if rejected:
        draft["rejected_metadata_proposals"] = rejected
    return draft


def _merge_sections(parts: list[dict]) -> list[dict]:
    sections: list[dict] = []
    by_heading: dict[str, dict] = {}
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for part in parts:
        for section in part.get("sections", []):
            target = by_heading.get(section["heading"])
            if target is None:
                target = {"heading": section["heading"], "paragraphs": []}
                by_heading[section["heading"]] = target
                sections.append(target)
            for paragraph in section["paragraphs"]:
                key = (
                    target["heading"],
                    paragraph["text"],
                    tuple(paragraph["citations"]),
                )
                if key in seen:
                    continue
                seen.add(key)
                target["paragraphs"].append(
                    {"text": paragraph["text"], "citations": list(paragraph["citations"])}
                )
    return [section for section in sections if section["paragraphs"]]


def merge_parts_in_order(
    parts: list[tuple[int, dict]],
    topic: str,
    documents: list[dict],
    run_id: str,
    *,
    partial: bool,
    segmentation: dict,
) -> dict:
    """Merge by source index, never by completion order."""
    ordered = [part for _, part in sorted(parts, key=lambda item: item[0])]
    return merge_drafts(
        ordered,
        topic,
        documents,
        run_id,
        partial=partial,
        segmentation=segmentation,
    )


def merge_drafts(
    parts: list[dict],
    topic: str,
    documents: list[dict],
    run_id: str,
    *,
    partial: bool,
    segmentation: dict,
) -> dict:
    """Backend-only merge: no second LLM call, no rewritten cells, full citations kept."""
    title = next(
        (part["title"].strip() for part in parts if (part.get("title") or "").strip()),
        "",
    )
    if not title:
        title = topic.strip()[:500] or "Bản nháp biên soạn"
    sections = _merge_sections(parts)
    unknowns: list[str] = []
    seen_unknowns: set[str] = set()
    for part in parts:
        for unknown in part.get("unknowns", []):
            if unknown not in seen_unknowns:
                seen_unknowns.add(unknown)
                unknowns.append(unknown)
    if not sections and not partial:
        raise AppException(
            "Các phần không tạo được nội dung có căn cứ.",
            code="compilation_draft_empty",
            status_code=502,
        )
    content = {"title": title, "sections": sections, "unknowns": unknowns}
    if sections:
        from qnu.domains.knowledge.compilation.schemas import DraftContent

        try:
            retained = retain_limitations(DraftContent.model_validate(content), documents)
        except AppException:
            raise
        except Exception as exc:
            raise AppException(
                "Không giữ được cấu trúc bản nháp đã ghép.",
                code="compilation_draft_invalid",
                status_code=502,
            ) from exc
        content = retained.model_dump()
    result = {
        "schema_version": "qnu.compiler.draft/v1",
        "compilation_run_id": run_id,
        "publication_status": "draft",
        "requires_review": True,
        "topic": topic,
        **content,
        "citations": citation_index(documents),
        "source_tables": literal_tables(documents),
        "sources": [
            {key: value for key, value in document.items() if key not in {"pages", "evidence"}}
            for document in documents
        ],
        "validation": {
            "schema": "passed",
            "citation_membership": "passed",
            "semantic_faithfulness": "not_evaluated",
            "unread_source_blocks": "retained",
            "segmentation": segmentation,
            "quality": quality_validation(
                source_binding=NOT_CHECKED,
                coverage=(
                    NO_ERROR_FOUND
                    if segmentation.get("state") == "completed" and not partial
                    else PARTIALLY_CHECKED
                ),
            ),
        },
    }
    if partial:
        result["partial"] = True
    return result


def partial_markdown(draft: dict) -> bytes:
    from qnu.domains.knowledge.compilation.drafting import markdown_for

    body = markdown_for(draft)
    coverage = draft.get("validation", {}).get("segmentation", {})
    note = (
        f"> Bản nháp một phần: {coverage.get('segments_completed', 0)}/"
        f"{coverage.get('segments_total', 0)} phần đã hoàn tất; chưa đủ để duyệt/xuất bản.\n\n"
    )
    return (body.split("\n", 1)[0] + "\n\n" + note + body.split("\n", 1)[1]).encode("utf-8")
