"""Plan review parts over owned source/draft units without losing exhaustive coverage.

The immutable review snapshot keeps every unit and excerpt. Each model request only
receives the units it must assess plus a small cross-part context. A merged report is
accepted only when every full unit was assessed exactly once by the part that owns it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.review import report
from qnu.domains.modelops.inference.service import request_input_tokens
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage

SEGMENT_PROMPT_VERSION = "qnu.compiler.review.part.prompt/v1"
PLANNER_VERSION = "qnu.compiler.review.plan/v1"
MANIFEST_VERSION = "qnu.compiler.review.segment-manifest/v1"
TARGET_RATIO = 0.45
MAX_CONTEXT_SOURCES = 16
MAX_CONTEXT_DRAFTS = 4


@dataclass(frozen=True, slots=True)
class ReviewPartPlan:
    index: int
    source_ids: tuple[str, ...]
    draft_ids: tuple[str, ...]
    context_source_ids: tuple[str, ...]
    context_draft_ids: tuple[str, ...]
    input_sha256: str
    input_tokens: int
    schema_sha256: str | None
    payload: dict = field(default_factory=dict, compare=False, repr=False)

    def scope_dict(self) -> dict:
        return {
            "index": self.index,
            "source_ids": list(self.source_ids),
            "draft_ids": list(self.draft_ids),
            "context_source_ids": list(self.context_source_ids),
            "context_draft_ids": list(self.context_draft_ids),
            "input_sha256": self.input_sha256,
            "input_tokens": self.input_tokens,
            "schema_sha256": self.schema_sha256,
        }


def _invalid(detail: str, code: str) -> AppException:
    return AppException(detail, code=code, status_code=422)


def _sha(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def _unit_bytes(unit: dict) -> int:
    return len(json.dumps(unit, ensure_ascii=False).encode("utf-8"))


def payload_for(
    material: dict,
    source_ids: tuple[str, ...] | list[str],
    draft_ids: tuple[str, ...] | list[str],
    context_source_ids: tuple[str, ...] | list[str] = (),
    context_draft_ids: tuple[str, ...] | list[str] = (),
) -> dict:
    """Allowlisted units only; full documents and the source map stay server-side."""
    sources = {unit["id"]: unit for unit in material["source_units"]}
    drafts = {unit["id"]: unit for unit in material["draft_units"]}
    owned_sources = [sources[key] for key in source_ids]
    owned_drafts = [drafts[key] for key in draft_ids]
    context_sources = [sources[key] for key in context_source_ids if key not in source_ids]
    context_drafts = [drafts[key] for key in context_draft_ids if key not in draft_ids]
    payload = {
        "topic": material["topic"],
        "source_units": owned_sources,
        "draft_units": owned_drafts,
        "allowed_source_ids": [unit["id"] for unit in [*owned_sources, *context_sources]],
        "allowed_draft_ids": [unit["id"] for unit in [*owned_drafts, *context_drafts]],
        "documents": [
            {key: value for key, value in document.items() if key not in {"pages", "evidence"}}
            for document in material["documents"]
        ],
    }
    if context_sources:
        payload["context_source_units"] = context_sources
    if context_drafts:
        payload["context_draft_units"] = context_drafts
    return payload


def messages_for(
    payload: dict, *, structured: bool, index: int, total: int
) -> list[ChatMessage]:
    return report.messages_for(
        payload, structured=structured, segment=(index, total)
    )


def build_part(
    material: dict,
    *,
    index: int,
    total: int,
    source_ids: tuple[str, ...] | list[str],
    draft_ids: tuple[str, ...] | list[str],
    context_source_ids: tuple[str, ...] | list[str] = (),
    context_draft_ids: tuple[str, ...] | list[str] = (),
    structured: bool,
) -> ReviewPartPlan:
    payload = payload_for(
        material, source_ids, draft_ids, context_source_ids, context_draft_ids
    )
    messages = messages_for(payload, structured=structured, index=index, total=total)
    schema = report.output_schema(payload) if structured else None
    return ReviewPartPlan(
        index=index,
        source_ids=tuple(source_ids),
        draft_ids=tuple(draft_ids),
        context_source_ids=tuple(context_source_ids),
        context_draft_ids=tuple(context_draft_ids),
        input_sha256=_sha(messages[-1].content),
        input_tokens=request_input_tokens(messages, schema),
        schema_sha256=_sha(json_bytes(schema)) if schema is not None else None,
        payload=payload,
    )


def _refs(unit: dict, source_ids: set[str]) -> list[str]:
    refs = []
    if unit.get("kind") == "table_cell" and unit.get("source_id"):
        refs.append(unit["source_id"])
    refs.extend(unit.get("citations") or [])
    return [ref for ref in dict.fromkeys(refs) if ref in source_ids]


def _source_context(
    material: dict,
    owned_ids: set[str],
    cited_ids: set[str],
    order: dict[str, int],
) -> list[str]:
    """Repeat cited rows and one neighbour; sources owned earlier stay read-only context."""
    units = material["source_units"]
    context: list[str] = []
    seen: set[str] = set(owned_ids)

    def add(key: str) -> None:
        if key in seen or len(context) >= MAX_CONTEXT_SOURCES:
            return
        seen.add(key)
        context.append(key)

    # A draft in this part may cite a source already owned by an earlier part.
    # It remains reportable there, but the model must be able to see it here.
    for key in sorted(cited_ids, key=order.__getitem__):
        if key in order:
            if key not in seen:
                seen.add(key)
                context.append(key)
    for key in sorted(owned_ids | cited_ids, key=order.__getitem__):
        position = order[key]
        for offset in (-1, 1):
            neighbour = position + offset
            if 0 <= neighbour < len(units):
                add(units[neighbour]["id"])
    tables: dict[str, list[dict]] = {}
    units_by_id: dict[str, dict] = {}
    for unit in units:
        units_by_id[unit["id"]] = unit
        if unit.get("table_id"):
            tables.setdefault(unit["table_id"], []).append(unit)
    for key in sorted(owned_ids, key=order.__getitem__):
        unit = units_by_id.get(key)
        if unit is None or not unit.get("table_id"):
            continue
        cells = tables.get(unit["table_id"], [])
        header = [cell for cell in cells if cell.get("header")]
        row = [
            cell
            for cell in cells
            if cell.get("row") == unit.get("row") and cell["id"] != unit["id"]
        ]
        for cell in [*header, *row]:
            if cell["id"] not in seen:
                seen.add(cell["id"])
                context.append(cell["id"])
    # Closing conditions may be ordinary text, not a detected footnote. Keep
    # them available to every review part of a tabular document.
    tabular_runs = {unit.get("ocr_run_id") for unit in units if unit.get("table_id")}
    for unit in units:
        if (
            unit.get("ocr_run_id") in tabular_runs
            and (not unit.get("table_id") or unit.get("header"))
            and unit["id"] not in seen
        ):
            seen.add(unit["id"])
            context.append(unit["id"])
    return context


def _source_row_groups(material: dict, keys: list[str]) -> list[list[str]]:
    """Keep every table row together; a text block is its own group."""
    units = {unit["id"]: unit for unit in material["source_units"]}
    groups: list[list[str]] = []
    current: list[str] = []
    last: tuple[str, int] | None = None
    for key in keys:
        unit = units[key]
        row_key = (
            (unit["table_id"], int(unit.get("row") or 0)) if unit.get("table_id") else None
        )
        if row_key is None:
            if current:
                groups.append(current)
                current = []
            groups.append([key])
            last = None
            continue
        if last is not None and row_key != last:
            groups.append(current)
            current = []
        last = row_key
        current.append(key)
    if current:
        groups.append(current)
    return groups



def _draft_context(
    material: dict, owned_ids: set[str], order: dict[str, int], cited: set[str]
) -> list[str]:
    units = material["draft_units"]
    context: list[str] = []
    seen: set[str] = set(owned_ids) | set(cited)
    for key in sorted(owned_ids, key=order.__getitem__):
        position = order[key]
        for offset in (-1, 1):
            neighbour = position + offset
            if 0 <= neighbour < len(units) and len(context) < MAX_CONTEXT_DRAFTS:
                neighbour_id = units[neighbour]["id"]
                if neighbour_id not in seen:
                    seen.add(neighbour_id)
                    context.append(neighbour_id)
    return context


def _chunks(units: list[dict], target_bytes: int) -> list[list[dict]]:
    chunks: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    for unit in units:
        width = _unit_bytes(unit)
        if current and size + width > target_bytes:
            chunks.append(current)
            current, size = [], 0
        current.append(unit)
        size += width
    if current:
        chunks.append(current)
    return chunks


def _build_group(
    material: dict,
    draft_ids: list[str],
    owned_sources: set[str],
    *,
    index: int,
    total: int,
    structured: bool,
    capacity: int,
) -> tuple[list[ReviewPartPlan], set[str]]:
    """Build one part or split its draft list until every part fits the envelope."""
    drafts = {unit["id"]: unit for unit in material["draft_units"]}
    source_ids = {unit["id"] for unit in material["source_units"]}
    source_order = {unit["id"]: i for i, unit in enumerate(material["source_units"])}
    draft_order = {unit["id"]: i for i, unit in enumerate(material["draft_units"])}
    new_owned: list[str] = []
    cited: list[str] = []
    for key in draft_ids:
        for ref in _refs(drafts[key], source_ids):
            if ref in owned_sources:
                if ref not in cited:
                    cited.append(ref)
            elif ref not in new_owned:
                new_owned.append(ref)
    context_sources = _source_context(
        material, set(new_owned), set(cited), source_order
    )
    context_drafts = _draft_context(
        material, set(draft_ids), draft_order, set()
    )

    def attempt(source_context: list[str], draft_context: list[str]) -> ReviewPartPlan:
        return build_part(
            material,
            index=index,
            total=total,
            source_ids=new_owned,
            draft_ids=draft_ids,
            context_source_ids=source_context,
            context_draft_ids=draft_context,
            structured=structured,
        )

    plan = attempt(context_sources, context_drafts)
    if plan.input_tokens <= capacity:
        return [plan], owned_sources | set(new_owned)
    if len(draft_ids) == 1:
        raise _invalid(
            "Một đơn vị review vượt ngân sách model; không cắt nội dung.",
            "compilation_review_segment_too_large",
        )
    middle = len(draft_ids) // 2
    left, owned_after_left = _build_group(
        material,
        draft_ids[:middle],
        owned_sources,
        index=index,
        total=total,
        structured=structured,
        capacity=capacity,
    )
    right, owned_after_right = _build_group(
        material,
        draft_ids[middle:],
        owned_after_left,
        index=index + len(left),
        total=total,
        structured=structured,
        capacity=capacity,
    )
    return [*left, *right], owned_after_right


def _source_groups(units: list[dict]) -> list[list[str]]:
    """Keep a table row together; a text block stays a single review group."""
    groups: list[list[str]] = []
    current: list[str] = []
    key: tuple[str, int] | None = None
    for unit in units:
        row_key = (
            (unit["table_id"], int(unit.get("row") or 0)) if unit.get("table_id") else None
        )
        if row_key is None:
            if current:
                groups.append(current)
                current = []
            groups.append([unit["id"]])
            key = None
            continue
        if key is not None and row_key != key:
            groups.append(current)
            current = []
        key = row_key
        current.append(unit["id"])
    if current:
        groups.append(current)
    return groups


def _build_source_group(
    material: dict,
    keys: list[str],
    *,
    index: int,
    total: int,
    structured: bool,
    capacity: int,
) -> list[ReviewPartPlan]:
    source_order = {unit["id"]: i for i, unit in enumerate(material["source_units"])}
    groups = _source_row_groups(material, keys)
    context = _source_context(material, set(keys), set(), source_order)
    plan = build_part(
        material,
        index=index,
        total=total,
        source_ids=keys,
        draft_ids=[],
        context_source_ids=context,
        structured=structured,
    )
    if plan.input_tokens <= capacity:
        return [plan]
    if len(groups) == 1:
        raise _invalid(
            "Một hàng bảng hoặc đơn vị nguồn review vượt ngân sách model; không cắt nội dung.",
            "compilation_review_segment_too_large",
        )
    middle = len(groups) // 2
    left_keys = [key for group in groups[:middle] for key in group]
    right_keys = [key for group in groups[middle:] for key in group]
    left = _build_source_group(
        material,
        left_keys,
        index=index,
        total=total,
        structured=structured,
        capacity=capacity,
    )
    right = _build_source_group(
        material,
        right_keys,
        index=index + len(left),
        total=total,
        structured=structured,
        capacity=capacity,
    )
    return [*left, *right]


def plan_parts(
    material: dict, *, capacity: int, structured: bool
) -> list[ReviewPartPlan]:
    if not material["source_units"] and not material["draft_units"]:
        raise _invalid("Bản nháp không có đơn vị để review.", "compilation_review_empty")
    target_bytes = max(2048, int(capacity * TARGET_RATIO))
    total_estimate = max(2, len(material["draft_units"]))
    plans: list[ReviewPartPlan] = []
    owned_sources: set[str] = set()
    for chunk in _chunks(list(material["draft_units"]), target_bytes):
        group, owned_sources = _build_group(
            material,
            [unit["id"] for unit in chunk],
            owned_sources,
            index=len(plans) + 1,
            total=total_estimate,
            structured=structured,
            capacity=capacity,
        )
        plans.extend(group)
    remaining = [
        unit for unit in material["source_units"] if unit["id"] not in owned_sources
    ]
    for group in _groups_by_bytes(_source_groups(remaining), remaining, target_bytes):
        plans.extend(
            _build_source_group(
                material,
                group,
                index=len(plans) + 1,
                total=total_estimate,
                structured=structured,
                capacity=capacity,
            )
        )
    return finalize_parts(plans, material, capacity=capacity, structured=structured)


def _groups_by_bytes(
    groups: list[list[str]], units: list[dict], target_bytes: int
) -> list[list[str]]:
    sizes = {unit["id"]: _unit_bytes(unit) for unit in units}
    chunks: list[list[str]] = []
    current: list[str] = []
    size = 0
    for group in groups:
        width = sum(sizes.get(key, 0) for key in group)
        if current and size + width > target_bytes:
            chunks.append(current)
            current, size = [], 0
        current.extend(group)
        size += width
    if current:
        chunks.append(current)
    return chunks


def finalize_parts(
    plans: list[ReviewPartPlan],
    material: dict,
    *,
    capacity: int,
    structured: bool,
) -> list[ReviewPartPlan]:
    """Recompute exact messages with the real part count and prove full coverage."""
    total = len(plans)
    finalized = []
    for plan in plans:
        rebuilt = build_part(
            material,
            index=plan.index,
            total=total,
            source_ids=plan.source_ids,
            draft_ids=plan.draft_ids,
            context_source_ids=plan.context_source_ids,
            context_draft_ids=plan.context_draft_ids,
            structured=structured,
        )
        if rebuilt.input_tokens > capacity:
            raise _invalid(
                "Phần review vượt ngân sách model sau khi chốt kế hoạch.",
                "compilation_review_segment_too_large",
            )
        finalized.append(rebuilt)
    owned_sources = [key for plan in finalized for key in plan.source_ids]
    owned_drafts = [key for plan in finalized for key in plan.draft_ids]
    if len(owned_sources) != len(set(owned_sources)):
        raise _invalid(
            "Kế hoạch review giao trùng đơn vị nguồn.",
            "compilation_review_plan_invalid",
        )
    if len(owned_drafts) != len(set(owned_drafts)):
        raise _invalid(
            "Kế hoạch review giao trùng đơn vị bản nháp.",
            "compilation_review_plan_invalid",
        )
    if set(owned_sources) != {unit["id"] for unit in material["source_units"]}:
        raise _invalid(
            "Kế hoạch review bỏ sót đơn vị nguồn.",
            "compilation_review_plan_invalid",
        )
    if set(owned_drafts) != {unit["id"] for unit in material["draft_units"]}:
        raise _invalid(
            "Kế hoạch review bỏ sót đơn vị bản nháp.",
            "compilation_review_plan_invalid",
        )
    return finalized


def manifest_for(
    review,
    plans: list[ReviewPartPlan],
    material: dict,
    *,
    capacity: int,
    output_tokens: int,
) -> dict:
    return {
        "schema_version": MANIFEST_VERSION,
        "planner_version": PLANNER_VERSION,
        "review_id": review.id,
        "compilation_run_id": review.compilation_run_id,
        "bundle_sha256": review.bundle_sha256,
        "topic": material["topic"],
        "budget": {
            "input_capacity_tokens": capacity,
            "output_tokens": output_tokens,
            "target_ratio": TARGET_RATIO,
        },
        "segments": [plan.scope_dict() for plan in plans],
        "coverage": {
            "source_unit_count": len(material["source_units"]),
            "draft_unit_count": len(material["draft_units"]),
        },
    }


def plan_from_scope(scope: dict) -> ReviewPartPlan:
    return ReviewPartPlan(
        index=scope["index"],
        source_ids=tuple(scope.get("source_ids", [])),
        draft_ids=tuple(scope.get("draft_ids", [])),
        context_source_ids=tuple(scope.get("context_source_ids", [])),
        context_draft_ids=tuple(scope.get("context_draft_ids", [])),
        input_sha256=scope["input_sha256"],
        input_tokens=scope.get("input_tokens", 0),
        schema_sha256=scope.get("schema_sha256"),
    )


def rebuild_part(
    material: dict, scope: dict, *, total: int, structured: bool
) -> tuple[ReviewPartPlan, list[ChatMessage], dict | None]:
    """Rebuild exactly the planned payload for resume; hashes must still match."""
    plan = plan_from_scope(scope)
    rebuilt = build_part(
        material,
        index=plan.index,
        total=total,
        source_ids=plan.source_ids,
        draft_ids=plan.draft_ids,
        context_source_ids=plan.context_source_ids,
        context_draft_ids=plan.context_draft_ids,
        structured=structured,
    )
    if rebuilt.input_sha256 != plan.input_sha256 or rebuilt.schema_sha256 != plan.schema_sha256:
        raise AppException(
            "Phần review không còn khớp kế hoạch đã lưu.",
            code="compilation_review_segment_mismatch",
            status_code=409,
        )
    schema = report.output_schema(rebuilt.payload) if structured else None
    return (
        rebuilt,
        messages_for(rebuilt.payload, structured=structured, index=plan.index, total=total),
        schema,
    )
