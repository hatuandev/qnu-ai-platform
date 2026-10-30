"""Plan, project and merge structural compilation parts within a model budget.

The immutable input snapshot keeps every block, table cell and citation. A model
request only receives the projected blocks/rows owned by one part plus structural
context. Nothing is cropped: if one row cannot fit, the part is rejected.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.drafting import SYSTEM_PROMPT
from qnu.domains.knowledge.compilation.evidence import citation_index, literal_tables
from qnu.domains.knowledge.compilation.limitations import retain_limitations
from qnu.domains.knowledge.compilation.schemas import DraftSection
from qnu.domains.modelops.inference.service import (
    available_input_tokens,
    request_input_tokens,
)
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage

PROMPT_VERSION = "qnu.compiler.segment.prompt/v2"
PLANNER_VERSION = "qnu.compiler.plan/v2"
MANIFEST_VERSION = "qnu.compiler.segment-manifest/v1"
TARGET_RATIO = 0.6
# Planning heuristic, not a tokenizer or a guarantee about model reasoning. Keep
# most of the generation allowance for reasoning and JSON/citation expansion.
OUTPUT_CONTENT_RATIO = 0.25
CONTEXT_TYPES = {"title", "header", "caption", "footnote"}


class SegmentDraftContent(BaseModel):
    """A part may be context-only, hence an optional title and empty sections."""

    model_config = ConfigDict(extra="forbid", strict=True)
    title: str | None = Field(None, max_length=500)
    sections: list[DraftSection] = Field(default_factory=list, max_length=100)
    unknowns: list[str] = Field(default_factory=list, max_length=100)


@dataclass(frozen=True, slots=True)
class Unit:
    document_index: int
    page_index: int
    page_number: int
    block_index: int
    ocr_run_id: str
    evidence_id: str
    kind: str
    row_index: int | None = None
    header_rows: tuple[int, ...] = ()


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
        }


def _invalid(detail: str, code: str) -> AppException:
    return AppException(detail, code=code, status_code=422)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def input_capacity(limits, output_tokens: int) -> int | None:
    """Backward-compatible name; the shared ModelOps helper owns the math."""
    return available_input_tokens(limits, output_tokens)


def header_row_indexes(rows: list[list[dict]]) -> tuple[int, ...]:
    leading = 0
    for row in rows:
        if not row or not all(cell.get("header") for cell in row):
            break
        leading += 1
    if leading == len(rows):
        return ()
    return tuple(range(leading))


def build_units(documents: list[dict]) -> list[Unit]:
    """One unit per text block, or per data row of a parsed table; never a half row."""
    units: list[Unit] = []
    for document_index, document in enumerate(documents):
        for page_index, page in enumerate(document["pages"]):
            for block_index, block in enumerate(page["blocks"]):
                table = block.get("table")
                rows = table.get("rows") if table and table.get("status") == "parsed" else None
                headers = header_row_indexes(rows) if rows else ()
                data_rows = [index for index in range(len(rows or [])) if index not in headers]
                common = {
                    "document_index": document_index,
                    "page_index": page_index,
                    "page_number": page["page_number"],
                    "block_index": block_index,
                    "ocr_run_id": document["ocr_run_id"],
                    "evidence_id": block["evidence_id"],
                }
                if data_rows:
                    units.extend(
                        Unit(**common, kind="table_row", row_index=row, header_rows=headers)
                        for row in data_rows
                    )
                else:
                    units.append(Unit(**common, kind="block"))
    return units


def _block_ref(unit: Unit) -> dict:
    return {
        "kind": "block",
        "ocr_run_id": unit.ocr_run_id,
        "page": unit.page_number,
        "evidence_id": unit.evidence_id,
    }


def owned_refs(units: list[Unit]) -> tuple[dict, ...]:
    """Group consecutive table-row units; ownership stays per source row."""
    refs: list[dict] = []
    table: dict | None = None
    for unit in units:
        if unit.kind == "block":
            table = None
            refs.append(_block_ref(unit))
            continue
        key = (unit.ocr_run_id, unit.page_number, unit.evidence_id)
        if table is None or table["_key"] != key:
            table = {
                "_key": key,
                "kind": "table_rows",
                "ocr_run_id": unit.ocr_run_id,
                "page": unit.page_number,
                "evidence_id": unit.evidence_id,
                "rows": [],
                "header_rows": list(unit.header_rows),
            }
            refs.append(table)
        table["rows"].append(unit.row_index)
    for ref in refs:
        ref.pop("_key", None)
    return tuple(refs)


def _adjacent_context(documents: list[dict], unit: Unit) -> list[dict]:
    page = documents[unit.document_index]["pages"][unit.page_index]
    refs = []
    for offset in (-2, -1, 1, 2):
        index = unit.block_index + offset
        if not 0 <= index < len(page["blocks"]):
            continue
        block = page["blocks"][index]
        if block.get("table") is not None or block.get("type") not in CONTEXT_TYPES:
            continue
        refs.append(
            {
                "kind": "block",
                "ocr_run_id": unit.ocr_run_id,
                "page": unit.page_number,
                "evidence_id": block["evidence_id"],
            }
        )
    return refs


def structural_context(documents: list[dict], unit: Unit) -> list[dict]:
    """Preserve document headings/notes and candidate headers without guessing joins.

    Non-table blocks form the shared context of tabular documents. This includes
    conditions printed after the last table. A text-only document carries its
    preceding heading and explicit captions/footnotes instead of the whole text.
    Oversized required context fails the budget check rather than being cropped.
    """
    document = documents[unit.document_index]
    has_tables = any(b.get("table") for p in document["pages"] for b in p["blocks"])
    refs = []
    heading = None
    for page in document["pages"]:
        for block in page["blocks"]:
            table = block.get("table")
            base = {
                "ocr_run_id": unit.ocr_run_id,
                "page": page["page_number"],
                "evidence_id": block["evidence_id"],
            }
            if table and table.get("status") == "parsed":
                rows = header_row_indexes(table.get("rows") or [])
                if rows:
                    refs.append({**base, "kind": "table_header_rows", "rows": list(rows)})
            elif has_tables or block.get("type") in {"caption", "footnote"}:
                refs.append({**base, "kind": "block"})
            if block.get("type") in {"title", "header"}:
                heading = {**base, "kind": "block"}
            if block["evidence_id"] == unit.evidence_id and heading:
                refs.append(heading)
    return refs


def context_refs(documents: list[dict], units: list[Unit]) -> tuple[dict, ...]:
    """Repeat table headers and nearby title/caption/footnote blocks as context only."""
    owned = {_ref_key(ref) for ref in owned_refs(units)}
    refs: list[dict] = []
    seen: set[tuple] = set()
    for unit in units:
        candidates = []
        if unit.kind == "table_row" and unit.header_rows:
            candidates.append(
                {
                    "kind": "table_header_rows",
                    "ocr_run_id": unit.ocr_run_id,
                    "page": unit.page_number,
                    "evidence_id": unit.evidence_id,
                    "rows": list(unit.header_rows),
                }
            )
        candidates.extend(_adjacent_context(documents, unit))
        candidates.extend(structural_context(documents, unit))
        for ref in candidates:
            key = _ref_key(ref)
            if key in owned or key in seen:
                continue
            seen.add(key)
            refs.append(ref)
    return tuple(refs)


def _ref_key(ref: dict) -> tuple:
    return (
        ref["ocr_run_id"],
        ref["page"],
        ref["evidence_id"],
        ref["kind"],
        tuple(ref.get("rows", ())),
    )


def _block_index(documents: list[dict]) -> dict[tuple[str, str], tuple[int, int, int, dict]]:
    index = {}
    for document_index, document in enumerate(documents):
        for page_index, page in enumerate(document["pages"]):
            for block_index, block in enumerate(page["blocks"]):
                index[(document["ocr_run_id"], block["evidence_id"])] = (
                    document_index,
                    page_index,
                    block_index,
                    block,
                )
    return index


def _project_block(block: dict) -> dict:
    """Allowlist fields; never forward inline Base64 images or the evidence map."""
    payload = {
        "evidence_id": block["evidence_id"],
        "type": block["type"],
        "label": block.get("label"),
        "text": block.get("text", ""),
        "bbox": block.get("bbox"),
        "requires_review": bool(block.get("requires_review")),
    }
    if block.get("origin"):
        payload["origin"] = block["origin"]
    table = block.get("table")
    if table is not None:
        payload["table"] = {
            "evidence_id": table["evidence_id"],
            "status": table["status"],
            "reason": table.get("reason"),
            "column_count": table["column_count"],
            "row_count": table["row_count"],
            "rows": table["rows"],
        }
    return payload


def _project_table_block(block: dict, rows: list[int]) -> dict:
    table = block["table"]
    payload = _project_block({**block, "table": None})
    payload["table"] = {
        "evidence_id": table["evidence_id"],
        "status": table["status"],
        "reason": table.get("reason"),
        "column_count": table["column_count"],
        "row_count": table["row_count"],
        "rows": [table["rows"][index] for index in rows],
        "row_numbers": [index + 1 for index in rows],
    }
    return payload


def project_documents(
    documents: list[dict], owned: tuple[dict, ...] | list[dict], context: tuple[dict, ...] | list[dict]
) -> list[dict]:
    """Rebuild exactly the owned blocks/rows plus repeated context from the snapshot."""
    index = _block_index(documents)
    selection: dict[tuple[int, int, int], dict] = {}
    for ref in [*owned, *context]:
        key = (ref["ocr_run_id"], ref["evidence_id"])
        if key not in index:
            raise AppException(
                "Phần biên soạn tham chiếu khối không có trong snapshot.",
                code="compilation_segment_manifest_mismatch",
                status_code=409,
            )
        document_index, page_index, block_index, block = index[key]
        page = documents[document_index]["pages"][page_index]
        if page["page_number"] != ref["page"]:
            raise AppException(
                "Phần biên soạn tham chiếu sai trang nguồn.",
                code="compilation_segment_manifest_mismatch",
                status_code=409,
            )
        entry = selection.setdefault(
            (document_index, page_index, block_index), {"block": False, "rows": set()}
        )
        if ref["kind"] == "block":
            entry["block"] = True
        else:
            rows = ref.get("rows", [])
            table = block.get("table") or {}
            source_rows = table.get("rows") or []
            if any(not isinstance(row, int) or not 0 <= row < len(source_rows) for row in rows):
                raise AppException(
                    "Phần biên soạn tham chiếu hàng bảng không hợp lệ.",
                    code="compilation_segment_manifest_mismatch",
                    status_code=409,
                )
            entry["rows"].update(rows)

    projected = []
    for document_index, document in enumerate(documents):
        pages = []
        for page_index, page in enumerate(document["pages"]):
            blocks = []
            for block_index, block in enumerate(page["blocks"]):
                entry = selection.get((document_index, page_index, block_index))
                if entry is None:
                    continue
                table = block.get("table")
                if entry["block"]:
                    blocks.append(_project_block(block))
                elif table is not None and table.get("status") == "parsed":
                    blocks.append(_project_table_block(block, sorted(entry["rows"])))
            if blocks:
                pages.append(
                    {
                        "page_number": page["page_number"],
                        "status": page["status"],
                        "blocks": blocks,
                    }
                )
        if pages:
            projected.append(
                {
                    "ocr_run_id": document["ocr_run_id"],
                    "identity": document["identity"],
                    "pages": pages,
                }
            )
    return projected


def citations_in(documents: list[dict]) -> list[str]:
    citations: list[str] = []
    seen: set[str] = set()
    for document in documents:
        run_id = document["ocr_run_id"]
        for page in document["pages"]:
            for block in page["blocks"]:
                refs = [block["evidence_id"]]
                table = block.get("table")
                if table is not None:
                    refs.append(table["evidence_id"])
                    refs.extend(cell["evidence_id"] for row in table["rows"] for cell in row)
                for evidence_id in refs:
                    ref = f"{run_id}:{evidence_id}"
                    if ref not in seen:
                        seen.add(ref)
                        citations.append(ref)
    return citations


def document_structure(documents: list[dict]) -> dict:
    """Small structural outline only: counts, table shapes and heading text."""
    payload = []
    for document in documents:
        pages = []
        outline = []
        for page in document["pages"]:
            tables = []
            for block in page["blocks"]:
                if block.get("type") in {"title", "header"} and block.get("text"):
                    outline.append(
                        {"page": page["page_number"], "text": block["text"][:300]}
                    )
                table = block.get("table")
                if table is not None:
                    tables.append(
                        {
                            "page": page["page_number"],
                            "evidence_id": block["evidence_id"],
                            "status": table["status"],
                            "row_count": table["row_count"],
                            "column_count": table["column_count"],
                        }
                    )
            pages.append(
                {
                    "page": page["page_number"],
                    "status": page["status"],
                    "block_count": len(page["blocks"]),
                    "tables": tables,
                }
            )
        payload.append(
            {
                "ocr_run_id": document["ocr_run_id"],
                "identity": document["identity"],
                "page_count": len(document["pages"]),
                "pages": pages,
                "outline": outline[:80],
            }
        )
    return {"documents": payload}


def build_projection(
    topic: str,
    documents: list[dict],
    owned: tuple[dict, ...] | list[dict],
    context: tuple[dict, ...] | list[dict],
    index: int,
) -> tuple[dict, list[str]]:
    projected = project_documents(documents, owned, context)
    citations = citations_in(projected)
    payload = {
        "topic": topic,
        "segment": {
            "index": index,
            "has_previous": index > 1,
            "owned": list(owned),
            "context_only": list(context),
            "note": (
                "Chỉ biên soạn các refs trong owned; context_only chỉ dùng đối chiếu "
                "điều kiện/header, không biên soạn lại. rows của refs bắt đầu từ 0; "
                "row_numbers trong bảng bắt đầu từ 1. Không suy nội dung phần khác."
            ),
        },
        "structure": document_structure(documents),
        "documents": projected,
        "allowed_citations": citations,
    }
    return payload, citations


def segment_system(index: int, total: int) -> str:
    return SYSTEM_PROMPT + (
        f"\nĐây là phần {index}/{total} của một tài liệu dài. Chỉ trả nội dung thuộc phần "
        "này; giữ tiêu đề mục ngắn và không lặp lại nội dung đã viết ở phần khác. "
        "Nếu phần này không đủ căn cứ, trả sections rỗng và ghi unknowns. "
        "Tuyệt đối không tạo lại bảng và không trích dẫn ID ngoài allowed_citations. "
        "Hệ thống ghép đủ hàng/ô bảng nguyên gốc ở cuối; không diễn giải tuần tự "
        "mọi ô thành đoạn văn. Chỉ viết ghi chú cần thiết về phạm vi, điều kiện, "
        "ngoại lệ của owned; chỉ dùng context_only khi cần xác định các ghi chú đó. "
        "Không cần soạn cả tài liệu hoặc kiểm kê toàn bộ citation trong phản hồi."
    )


def segment_schema(citations: list[str]) -> dict:
    schema = SegmentDraftContent.model_json_schema()
    schema["$defs"]["DraftParagraph"]["properties"]["citations"]["items"]["enum"] = citations
    return schema


def segment_messages(payload: dict, index: int, total: int) -> list[ChatMessage]:
    return [
        ChatMessage("system", segment_system(index, total)),
        ChatMessage(
            "user",
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        ),
    ]


def build_plan(
    *,
    index: int,
    units: list[Unit],
    documents: list[dict],
    topic: str,
    structured: bool,
    total_estimate: int,
) -> SegmentPlan:
    owned = owned_refs(units)
    context = context_refs(documents, units)
    payload, citations = build_projection(topic, documents, owned, context, index)
    user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    schema = segment_schema(citations) if structured else None
    messages = [
        ChatMessage("system", segment_system(index, total_estimate)),
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
        output_size_estimate=estimate_output_size(documents, units),
    )


def estimate_output_size(documents: list[dict], units: list[Unit]) -> int:
    """UTF-8 copy-size proxy for owned content plus JSON and citation overhead.

    Context is read-only; including its repeated bytes would prevent splitting.
    Literal tables are attached by the backend, but their owned rows still count
    here to limit how many facts the model must consider in one generation.
    """
    size = 256
    for unit in units:
        block = documents[unit.document_index]["pages"][unit.page_index]["blocks"][unit.block_index]
        cells = block["table"]["rows"][unit.row_index] if unit.kind == "table_row" else [block]
        size += 96  # Paragraph/section JSON framing.
        for cell in cells:
            text = cell.get("text") or ""
            citation = f"{unit.ocr_run_id}:{cell['evidence_id']}"
            size += len(json.dumps([text, citation], ensure_ascii=False).encode("utf-8"))
    return size


def _scope_text(units: list[Unit], documents: list[dict]) -> str:
    pages = sorted({unit.page_number for unit in units})
    blocks = sum(1 for unit in units if unit.kind == "block")
    rows = sum(1 for unit in units if unit.kind == "table_row")
    tables = len({(unit.ocr_run_id, unit.evidence_id) for unit in units if unit.kind == "table_row"})
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
) -> list[SegmentPlan]:
    """Pack units in reading order; split only at block boundaries or whole rows."""
    units = build_units(documents)
    if not units:
        raise _invalid("Nguồn không có khối để biên soạn.", "compilation_source_empty")
    target = max(1, min(capacity, max(1024, int(capacity * target_ratio))))
    output_target = int(output_tokens * OUTPUT_CONTENT_RATIO) if output_tokens else None
    plans: list[SegmentPlan] = []
    current: list[Unit] = []
    for unit in units:
        candidate = [*current, unit]
        plan = build_plan(
            index=len(plans) + 1,
            units=candidate,
            documents=documents,
            topic=topic,
            structured=structured,
            total_estimate=max(2, len(plans) + 1),
        )
        if not current:
            if plan.input_tokens > capacity:
                raise _invalid(
                    "Một khối hoặc hàng bảng vượt ngân sách model; không cắt nội dung.",
                    "compilation_segment_too_large",
                )
            _check_output_size(plan, output_target)
            current = candidate
            continue
        if plan.input_tokens <= target and (
            output_target is None or plan.output_size_estimate <= output_target
        ):
            current = candidate
            continue
        plans.append(
            build_plan(
                index=len(plans) + 1,
                units=current,
                documents=documents,
                topic=topic,
                structured=structured,
                total_estimate=max(2, len(plans) + 1),
            )
        )
        current = [unit]
        single = build_plan(
            index=len(plans) + 1,
            units=current,
            documents=documents,
            topic=topic,
            structured=structured,
            total_estimate=max(2, len(plans) + 1),
        )
        if single.input_tokens > capacity:
            raise _invalid(
                "Một khối hoặc hàng bảng vượt ngân sách model; không cắt nội dung.",
                "compilation_segment_too_large",
            )
        _check_output_size(single, output_target)
    if current:
        plans.append(
            build_plan(
                index=len(plans) + 1,
                units=current,
                documents=documents,
                topic=topic,
                structured=structured,
                total_estimate=max(2, len(plans) + 1),
            )
        )
    return plans


def _check_output_size(plan: SegmentPlan, target: int | None) -> None:
    if target is not None and plan.output_size_estimate > target:
        raise _invalid(
            "Một khối hoặc hàng bảng vượt mức lập kế hoạch đầu ra; cần ngân sách "
            "đầu ra lớn hơn hoặc nguồn có cấu trúc chi tiết hơn, không cắt nội dung.",
            "compilation_segment_output_too_large",
        )


def finalize_plans(
    plans: list[SegmentPlan],
    documents: list[dict],
    topic: str,
    *,
    capacity: int,
    structured: bool,
) -> list[SegmentPlan]:
    """Recompute the exact bound with the real part count before persistence."""
    total = len(plans)
    finalized = []
    for plan in plans:
        rebuilt = build_plan(
            index=plan.index,
            units=list(plan.units),
            documents=documents,
            topic=topic,
            structured=structured,
            total_estimate=total,
        )
        if rebuilt.input_tokens > capacity:
            raise _invalid(
                "Phần biên soạn vượt ngân sách model sau khi chốt kế hoạch.",
                "compilation_segment_too_large",
            )
        finalized.append(rebuilt)
    expected = [ref for unit in build_units(documents) for ref in owned_refs([unit])]
    actual = [ref for plan in finalized for ref in plan.owned]
    def atoms(refs):
        result = []
        for ref in refs:
            base = (ref["ocr_run_id"], ref["page"], ref["evidence_id"])
            result.extend(
                (*base, row) for row in ref.get("rows", [None])
            )
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
        "run_id": run.id,
        "input_sha256": run.input_sha256,
        "topic": run.topic,
        "budget": {
            "input_capacity_tokens": capacity,
            "output_tokens": output_tokens,
            "target_ratio": TARGET_RATIO,
            "output_content_ratio": OUTPUT_CONTENT_RATIO,
            "output_estimate_kind": "owned_utf8_copy_size_heuristic",
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
    )


def parse_segment_draft(content: str, allowed_citations: set[str]) -> dict:
    try:
        value = SegmentDraftContent.model_validate_json(content)
    except Exception as exc:  # Pydantic validation is reported as one stable contract
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
    return value.model_dump()


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
