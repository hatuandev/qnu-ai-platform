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

# v2 embeds "index/total" in the hashed instruction and is kept only to replay old plans.
LEGACY_SEGMENT_PROMPT_VERSION = "qnu.compiler.review.part.prompt/v2"
# v3 states ownership explicitly and does not depend on the sibling count.
SEGMENT_PROMPT_VERSION = "qnu.compiler.review.part.prompt/v3"
PLANNER_VERSION = "qnu.compiler.review.plan/v2"
MANIFEST_VERSION = "qnu.compiler.review.segment-manifest/v2"
TARGET_RATIO = 0.45
# A part that fills the whole envelope cannot finish inside the provider timeout:
# prefill plus a full assessment set then runs for minutes and the call is cut off.
MAX_PART_RATIO = 0.85
MAX_CONTEXT_SOURCES = 16
MAX_CONTEXT_DRAFTS = 4
DEFAULT_MAX_OUTPUT_TOKENS = 4096
REASONING_RESERVE_RATIO = 0.40
REASONING_DISABLED_RESERVE_RATIO = 0.12
OUTPUT_FRAMING_RATIO = 0.15
OUTPUT_BYTES_PER_TOKEN = 3
BASE_OUTPUT_TOKENS = 24


@dataclass(frozen=True, slots=True)
class ReviewOutputBudget:
    max_output_tokens: int
    reasoning_reserve_tokens: int
    framing_reserve_tokens: int
    usable_output_tokens: int
    reasoning_shares_budget: bool = True

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "max_output_tokens": self.max_output_tokens,
            "reasoning_reserve_tokens": self.reasoning_reserve_tokens,
            "framing_reserve_tokens": self.framing_reserve_tokens,
            "usable_output_tokens": self.usable_output_tokens,
            "reasoning_shares_budget": self.reasoning_shares_budget,
        }


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
    projection: str = "compact/v3"
    output_tokens_estimate: int = 0
    output_bytes_estimate: int = 0
    input_budget_tokens: int = 0
    input_headroom_tokens: int = 0
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    output_budget_tokens: int = 0
    output_headroom_tokens: int = 0
    reasoning_reserve_tokens: int = 0
    framing_reserve_tokens: int = 0
    planner_version: str = PLANNER_VERSION
    prompt_version: str = SEGMENT_PROMPT_VERSION
    schema_version: str = report.VERSION
    prompt_sha256: str = ""
    request_total: int = 1

    def scope_dict(self) -> dict:
        return {
            **({"projection": self.projection} if self.projection != "full" else {}),
            "index": self.index,
            "request_total": self.request_total,
            "source_ids": list(self.source_ids),
            "draft_ids": list(self.draft_ids),
            "context_source_ids": list(self.context_source_ids),
            "context_draft_ids": list(self.context_draft_ids),
            "input_sha256": self.input_sha256,
            "input_tokens": self.input_tokens,
            "schema_sha256": self.schema_sha256,
            "output_tokens_estimate": self.output_tokens_estimate,
            "output_bytes_estimate": self.output_bytes_estimate,
            "budget": {
                "input_budget_tokens": self.input_budget_tokens,
                "input_headroom_tokens": self.input_headroom_tokens,
                "max_output_tokens": self.max_output_tokens,
                "output_budget_tokens": self.output_budget_tokens,
                "output_headroom_tokens": self.output_headroom_tokens,
                "reasoning_reserve_tokens": self.reasoning_reserve_tokens,
                "framing_reserve_tokens": self.framing_reserve_tokens,
            },
            "replay": {
                "planner_version": self.planner_version,
                "prompt_version": self.prompt_version,
                "schema_version": self.schema_version,
                "prompt_sha256": self.prompt_sha256,
                "input_sha256": self.input_sha256,
                "schema_sha256": self.schema_sha256,
            },
        }


def _invalid(detail: str, code: str) -> AppException:
    return AppException(detail, code=code, status_code=422)


def _ceiling(capacity: int) -> int:
    """Highest input a planned part may use; the rest of the envelope is headroom.

    The planner knows the model envelope but not its throughput, so a part never
    fills it: a part at the limit spends minutes in prefill and assessment output
    and the provider timeout cuts the call, leaving the review uncertain with no
    usable result. Splitting further only for this ceiling keeps the part count
    close to the minimum instead of duplicating cross-part context many times.
    """
    return max(1, int(capacity * MAX_PART_RATIO))


def _sha(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def _unit_bytes(unit: dict) -> int:
    return len(json.dumps(unit, ensure_ascii=False).encode("utf-8"))


def output_budget(
    max_output_tokens: int | None = None,
    *,
    reasoning_shares_budget: bool = True,
) -> ReviewOutputBudget:
    """Compute usable JSON assessment token budget after reserving reasoning and framing headroom."""
    limit = max(1, int(max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS))
    reasoning_ratio = (
        REASONING_RESERVE_RATIO
        if reasoning_shares_budget
        else REASONING_DISABLED_RESERVE_RATIO
    )
    reasoning_reserve = int(limit * reasoning_ratio)
    framing_reserve = min(
        max(16, int(limit * OUTPUT_FRAMING_RATIO)),
        max(0, limit - reasoning_reserve - 1),
    )
    usable = max(1, limit - reasoning_reserve - framing_reserve)
    return ReviewOutputBudget(
        max_output_tokens=limit,
        reasoning_reserve_tokens=reasoning_reserve,
        framing_reserve_tokens=framing_reserve,
        usable_output_tokens=usable,
        reasoning_shares_budget=reasoning_shares_budget,
    )


def estimate_unit_output_tokens(
    unit: dict,
    *,
    role: str,
    structured: bool = False,
) -> int:
    """Estimate output tokens for a single owned unit assessment based on schema and complexity."""
    unit_id = str(unit.get("id") or "")
    id_tokens = (len(unit_id.encode("utf-8")) + 2) // 3
    text_bytes = len(str(unit.get("text") or "").encode("utf-8"))
    kind = unit.get("kind")
    framing = 4 if structured else 2
    if role == "source":
        if kind == "table_cell":
            return 36 + id_tokens + min(12, text_bytes // 48) + framing
        return 52 + id_tokens + min(24, text_bytes // 40) + framing
    refs = unit.get("citations") or ([unit["source_id"]] if unit.get("source_id") else [])
    ref_count = max(1, len(refs))
    if kind == "table_cell":
        return 36 + id_tokens + min(12, text_bytes // 48) + framing
    if kind in {"title", "heading"}:
        return 44 + id_tokens + min(16, text_bytes // 48) + framing
    return 62 + id_tokens + 6 * ref_count + min(28, text_bytes // 32) + framing


def estimate_part_output_tokens(
    material: dict,
    source_ids: tuple[str, ...] | list[str],
    draft_ids: tuple[str, ...] | list[str],
    *,
    structured: bool = False,
) -> int:
    """Estimate total JSON assessment tokens for owned units only (context is reference-only)."""
    sources = {unit["id"]: unit for unit in material["source_units"]}
    drafts = {unit["id"]: unit for unit in material["draft_units"]}
    total = BASE_OUTPUT_TOKENS
    for key in source_ids:
        if key in sources:
            total += estimate_unit_output_tokens(
                sources[key], role="source", structured=structured
            )
    for key in draft_ids:
        if key in drafts:
            total += estimate_unit_output_tokens(
                drafts[key], role="draft", structured=structured
            )
    return total


def requires_output_segmentation(
    material: dict,
    *,
    output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    structured: bool = False,
    reasoning_shares_budget: bool = True,
) -> bool:
    """Return True when the full review output estimate exceeds safe single-call output budget."""
    budget = output_budget(output_tokens, reasoning_shares_budget=reasoning_shares_budget)
    estimated = estimate_part_output_tokens(
        material,
        [unit["id"] for unit in material["source_units"]],
        [unit["id"] for unit in material["draft_units"]],
        structured=structured,
    )
    if estimated > budget.usable_output_tokens:
        return True
    total_units = len(material["source_units"]) + len(material["draft_units"])
    return budget.max_output_tokens <= DEFAULT_MAX_OUTPUT_TOKENS and total_units > 2


def payload_for(
    material: dict,
    source_ids: tuple[str, ...] | list[str],
    draft_ids: tuple[str, ...] | list[str],
    context_source_ids: tuple[str, ...] | list[str] = (),
    context_draft_ids: tuple[str, ...] | list[str] = (),
    *,
    projection: str = "compact/v3",
) -> dict:
    """Allowlisted units only; full documents and the source map stay server-side."""
    sources = {unit["id"]: unit for unit in material["source_units"]}
    drafts = {unit["id"]: unit for unit in material["draft_units"]}
    owned_sources = [sources[key] for key in source_ids]
    owned_drafts = [drafts[key] for key in draft_ids]
    context_sources = [sources[key] for key in context_source_ids if key not in source_ids]
    if projection in {"compact/v1", "compact/v2", "compact/v3"}:
        fields = {
            "id",
            "text",
            "kind",
            "ocr_run_id",
            "page",
            "table_id",
            "row",
            "column",
            "row_span",
            "col_span",
            "header",
            "origin",
            "requires_review",
            "label",
        }
        owned_sources = [
            {key: value for key, value in unit.items() if key in fields} for unit in owned_sources
        ]
        context_sources = [
            {key: value for key, value in unit.items() if key in fields} for unit in context_sources
        ]
    elif projection != "full":
        raise _invalid(
            "Projection review không được hỗ trợ.", "compilation_review_projection_invalid"
        )
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
    payload: dict,
    *,
    structured: bool,
    index: int,
    total: int,
    prompt_version: str = SEGMENT_PROMPT_VERSION,
) -> list[ChatMessage]:
    """Only the legacy prompt embeds ``total``; v3 is independent of sibling count."""
    legacy = prompt_version == LEGACY_SEGMENT_PROMPT_VERSION
    return report.messages_for(
        payload, structured=structured, segment=(index, total if legacy else None)
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
    projection: str = "compact/v3",
    capacity: int = 0,
    output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    reasoning_shares_budget: bool = True,
    prompt_version: str = SEGMENT_PROMPT_VERSION,
) -> ReviewPartPlan:
    payload = payload_for(
        material,
        source_ids,
        draft_ids,
        context_source_ids,
        context_draft_ids,
        projection=projection,
    )
    messages = messages_for(
        payload, structured=structured, index=index, total=total, prompt_version=prompt_version
    )
    schema = (
        report.output_schema(
            payload,
            require_references=2 if projection == "compact/v3" else int(projection == "compact/v2"),
        )
        if structured
        else None
    )
    in_tokens = request_input_tokens(messages, schema)
    out_est = estimate_part_output_tokens(
        material,
        source_ids,
        draft_ids,
        structured=structured,
    )
    out_budget = output_budget(output_tokens, reasoning_shares_budget=reasoning_shares_budget)
    in_budget = _ceiling(capacity) if capacity > 0 else in_tokens
    in_headroom = max(0, capacity - in_budget) if capacity > 0 else 0
    return ReviewPartPlan(
        index=index,
        source_ids=tuple(source_ids),
        draft_ids=tuple(draft_ids),
        context_source_ids=tuple(context_source_ids),
        context_draft_ids=tuple(context_draft_ids),
        input_sha256=_sha(messages[-1].content),
        input_tokens=in_tokens,
        schema_sha256=_sha(json_bytes(schema)) if schema is not None else None,
        payload=payload,
        projection=projection,
        output_tokens_estimate=out_est,
        output_bytes_estimate=out_est * OUTPUT_BYTES_PER_TOKEN,
        input_budget_tokens=in_budget,
        input_headroom_tokens=in_headroom,
        max_output_tokens=out_budget.max_output_tokens,
        output_budget_tokens=out_budget.usable_output_tokens,
        output_headroom_tokens=max(0, out_budget.usable_output_tokens - out_est),
        reasoning_reserve_tokens=out_budget.reasoning_reserve_tokens,
        framing_reserve_tokens=out_budget.framing_reserve_tokens,
        planner_version=PLANNER_VERSION,
        prompt_version=prompt_version,
        schema_version=report.VERSION,
        prompt_sha256=_sha(messages[0].content),
        request_total=total,
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
    """Repeat cited rows, parent headings, table headers/notes and one neighbour as read-only context."""
    units = material["source_units"]
    context: list[str] = []
    seen: set[str] = set(owned_ids)

    def add(key: str, *, required: bool = False) -> None:
        if key in seen or (not required and len(context) >= MAX_CONTEXT_SOURCES):
            return
        seen.add(key)
        context.append(key)

    # A draft in this part may cite a source already owned by an earlier part.
    # It remains reportable there, but the model must be able to see it here.
    for key in sorted(cited_ids, key=order.__getitem__):
        if key in order and key not in seen:
            seen.add(key)
            context.append(key)
    tables: dict[str, list[dict]] = {}
    table_bounds: dict[str, tuple[int, int]] = {}
    units_by_id: dict[str, dict] = {}
    for idx, unit in enumerate(units):
        units_by_id[unit["id"]] = unit
        table_id = unit.get("table_id")
        if table_id:
            tables.setdefault(table_id, []).append(unit)
            if table_id not in table_bounds:
                table_bounds[table_id] = (idx, idx)
            else:
                table_bounds[table_id] = (table_bounds[table_id][0], idx)
    active_tables: set[str] = set()
    active_pages: set[tuple[str | None, int | None]] = set()
    for key in sorted(owned_ids | cited_ids, key=order.__getitem__):
        unit = units_by_id.get(key)
        if unit is None:
            continue
        active_pages.add((unit.get("ocr_run_id"), unit.get("page")))
        table_id = unit.get("table_id")
        if not table_id:
            continue
        active_tables.add(table_id)
        cells = tables.get(table_id, [])
        header = [cell for cell in cells if cell.get("header")]
        target_row = int(unit.get("row") or 0)
        target_end = target_row + max(1, int(unit.get("row_span") or 1)) - 1
        row_and_spanning = [
            cell
            for cell in cells
            if cell["id"] != unit["id"]
            and (
                cell.get("row") == unit.get("row")
                or (
                    int(cell.get("row") or 0) <= target_end
                    and int(cell.get("row") or 0)
                    + max(1, int(cell.get("row_span") or 1))
                    - 1
                    >= target_row
                )
            )
        ]
        for cell in [*header, *row_and_spanning]:
            add(cell["id"], required=True)
    # Preserve parent headings, table titles/units and footnotes for active tables/pages.
    for table_id in sorted(active_tables):
        first_idx, last_idx = table_bounds[table_id]
        run_id = units[first_idx].get("ocr_run_id")
        for candidate_idx in (first_idx - 1, last_idx + 1):
            if 0 <= candidate_idx < len(units):
                candidate = units[candidate_idx]
                if (
                    candidate.get("ocr_run_id") == run_id
                    and not candidate.get("table_id")
                    and _unit_bytes(candidate) <= 1024
                ):
                    add(candidate["id"], required=True)
    if active_tables:
        for unit in units:
            if (
                not unit.get("table_id")
                and (unit.get("ocr_run_id"), unit.get("page")) in active_pages
                and unit.get("kind")
                in {"title", "heading", "section_header", "page_header", "caption", "footnote", "note"}
                and _unit_bytes(unit) <= 1024
            ):
                add(unit["id"], required=True)
    for key in sorted(owned_ids | cited_ids, key=order.__getitem__):
        position = order[key]
        for offset in (-1, 1):
            neighbour = position + offset
            if 0 <= neighbour < len(units):
                add(units[neighbour]["id"])
    # Closing conditions may be ordinary text, not a detected footnote. Keep a
    # bounded tail available to every review part of a tabular document: the
    # nearest-to-the-end notes first, never every prose block of the run.
    tabular_runs = {unit.get("ocr_run_id") for unit in units if unit.get("table_id")}
    closing = [
        unit["id"]
        for unit in units
        if unit.get("ocr_run_id") in tabular_runs
        and (not unit.get("table_id") or unit.get("header"))
    ]
    for key in reversed(closing):
        if len(context) >= MAX_CONTEXT_SOURCES:
            break
        add(key)
    return context


def _source_row_groups(material: dict, keys: list[str]) -> list[list[str]]:
    """Keep every table row (and rowspan-linked rows) together; a text block is its own group."""
    units = {unit["id"]: unit for unit in material["source_units"]}
    groups: list[list[str]] = []
    current: list[str] = []
    current_table: str | None = None
    current_header: bool | None = None
    span_end = 0
    for key in keys:
        unit = units[key]
        table_id = unit.get("table_id") if unit.get("kind") == "table_cell" else None
        row_no = int(unit.get("row") or 0) if table_id else 0
        if not table_id or row_no <= 0:
            if current:
                groups.append(current)
                current = []
            groups.append([key])
            current_table = None
            current_header = None
            span_end = 0
            continue
        is_header = bool(unit.get("header"))
        row_end = row_no + max(1, int(unit.get("row_span") or 1)) - 1
        if current and (
            table_id != current_table or is_header != current_header or row_no > span_end
        ):
            groups.append(current)
            current = []
            span_end = 0
        current_table = table_id
        current_header = is_header
        span_end = max(span_end, row_end)
        current.append(key)
    if current:
        groups.append(current)
    return groups


def _draft_table_key(unit: dict) -> str | None:
    if unit.get("kind") != "table_cell":
        return None
    if unit.get("table_id"):
        return str(unit["table_id"])
    unit_id = str(unit.get("id") or "")
    if ":row:" in unit_id:
        return unit_id.split(":row:", 1)[0]
    return "draft_table"


def _draft_row_groups(material: dict, keys: list[str]) -> list[list[str]]:
    """Keep every draft table row (and rowspan-linked rows) together; non-table units stay individual."""
    units = {unit["id"]: unit for unit in material["draft_units"]}
    groups: list[list[str]] = []
    current: list[str] = []
    current_table: str | None = None
    current_header: bool | None = None
    span_end = 0
    for key in keys:
        unit = units[key]
        table_key = _draft_table_key(unit)
        row_no = int(unit.get("row") or 0) if table_key else 0
        if not table_key or row_no <= 0:
            if current:
                groups.append(current)
                current = []
            groups.append([key])
            current_table = None
            current_header = None
            span_end = 0
            continue
        is_header = bool(unit.get("header"))
        row_end = row_no + max(1, int(unit.get("row_span") or 1)) - 1
        if current and (
            table_key != current_table or is_header != current_header or row_no > span_end
        ):
            groups.append(current)
            current = []
            span_end = 0
        current_table = table_key
        current_header = is_header
        span_end = max(span_end, row_end)
        current.append(key)
    if current:
        groups.append(current)
    return groups


def _draft_context(
    material: dict, owned_ids: set[str], order: dict[str, int], cited: set[str]
) -> list[str]:
    units = material["draft_units"]
    units_by_id = {unit["id"]: unit for unit in units}
    context: list[str] = []
    seen: set[str] = set(owned_ids) | set(cited)

    def add(key: str, *, required: bool = False) -> None:
        if key not in order or key in seen:
            return
        if not required and len(context) >= MAX_CONTEXT_DRAFTS:
            return
        seen.add(key)
        context.append(key)

    # Preserve parent section headings and draft table headers for owned draft units.
    active_tables: set[str] = set()
    for key in sorted(owned_ids, key=order.__getitem__):
        parts_key = key.split(":")
        if len(parts_key) >= 2 and parts_key[0] == "section":
            add(f"section:{parts_key[1]}:heading", required=True)
        unit = units_by_id.get(key)
        if unit is not None and (table_key := _draft_table_key(unit)):
            active_tables.add(table_key)
    if active_tables:
        for unit in units:
            if _draft_table_key(unit) in active_tables and unit.get("header"):
                add(unit["id"], required=True)
    for key in sorted(owned_ids, key=order.__getitem__):
        position = order[key]
        for offset in (-1, 1):
            neighbour = position + offset
            if 0 <= neighbour < len(units):
                add(units[neighbour]["id"])
    return context


def _source_draft_context(material: dict, source_keys: set[str]) -> list[str]:
    """Provide read-only draft context for source-only parts when draft units cite these sources."""
    if not material.get("draft_units"):
        return []
    sources_by_id = {unit["id"]: unit for unit in material["source_units"]}
    active_tables = {
        sources_by_id[key]["table_id"]
        for key in source_keys
        if key in sources_by_id and sources_by_id[key].get("table_id")
    }
    selected: list[str] = []
    for unit in material["draft_units"]:
        citations = set(unit.get("citations") or [])
        source_id = unit.get("source_id")
        if (
            (source_id and source_id in source_keys)
            or (citations & source_keys)
            or (citations & active_tables)
        ):
            selected.append(unit["id"])
    return selected


def _chunks(
    material: dict,
    units: list[dict],
    target_bytes: int,
    target_output_tokens: int,
    *,
    structured: bool = False,
) -> list[list[dict]]:
    """Group draft units along atomic row boundaries within both byte and output token targets."""
    units_by_id = {unit["id"]: unit for unit in units}
    groups = _draft_row_groups(material, [unit["id"] for unit in units])
    chunks: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    out_tokens = BASE_OUTPUT_TOKENS
    for group_ids in groups:
        group_units = [units_by_id[key] for key in group_ids]
        width = sum(_unit_bytes(unit) for unit in group_units)
        group_out = sum(
            estimate_unit_output_tokens(unit, role="draft", structured=structured)
            for unit in group_units
        )
        # Account for newly cited source units that will be co-owned by this draft group.
        cited_count = sum(
            len(unit.get("citations") or ([unit["source_id"]] if unit.get("source_id") else []))
            for unit in group_units
        )
        estimated_step_out = group_out + cited_count * (
            48 if group_units[0].get("kind") == "table_cell" else 76
        )
        if current and (
            size + width > target_bytes
            or out_tokens + estimated_step_out > target_output_tokens
        ):
            chunks.append(current)
            current, size, out_tokens = [], 0, BASE_OUTPUT_TOKENS
        current.extend(group_units)
        size += width
        out_tokens += estimated_step_out
    if current:
        chunks.append(current)
    return chunks


def _expand_source_rows(material: dict, candidate_ids: list[str], owned_sources: set[str]) -> list[str]:
    """Expand any cited table cell to its full unowned atomic source row group."""
    all_source_ids = [unit["id"] for unit in material["source_units"] if unit["id"] not in owned_sources]
    row_groups = _source_row_groups(material, all_source_ids)
    group_by_member: dict[str, list[str]] = {}
    for group in row_groups:
        for member in group:
            group_by_member[member] = group
    expanded: list[str] = []
    seen: set[str] = set()
    for key in candidate_ids:
        for member in group_by_member.get(key, [key]):
            if member not in owned_sources and member not in seen:
                seen.add(member)
                expanded.append(member)
    return expanded


def _build_group(
    material: dict,
    draft_ids: list[str],
    owned_sources: set[str],
    *,
    index: int,
    total: int,
    structured: bool,
    capacity: int,
    output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    reasoning_shares_budget: bool = True,
) -> tuple[list[ReviewPartPlan], set[str]]:
    """Build one part or split its draft list until every part fits both input and output budgets."""
    drafts = {unit["id"]: unit for unit in material["draft_units"]}
    source_ids = {unit["id"] for unit in material["source_units"]}
    source_order = {unit["id"]: i for i, unit in enumerate(material["source_units"])}
    draft_order = {unit["id"]: i for i, unit in enumerate(material["draft_units"])}
    out_budget = output_budget(output_tokens, reasoning_shares_budget=reasoning_shares_budget)
    raw_owned: list[str] = []
    cited: list[str] = []
    for key in draft_ids:
        # Table-level citations refer to a block, while assessment IDs identify cells.
        # They are mandatory read-only context; ownership stays with cell assessments.
        table_refs = set(drafts[key].get("citations") or [])
        cited.extend(
            unit["id"]
            for unit in material["source_units"]
            if unit.get("table_id") in table_refs and unit["id"] not in cited
        )
        for ref in _refs(drafts[key], source_ids):
            if ref in owned_sources:
                if ref not in cited:
                    cited.append(ref)
            elif ref not in raw_owned:
                raw_owned.append(ref)
    new_owned = _expand_source_rows(material, raw_owned, owned_sources)

    def attempt(candidate_owned: list[str], extra_cited: list[str]) -> ReviewPartPlan:
        all_cited = set(cited) | set(extra_cited)
        context_sources = _source_context(
            material, set(candidate_owned), all_cited, source_order
        )
        context_drafts = _draft_context(material, set(draft_ids), draft_order, set())
        return build_part(
            material,
            index=index,
            total=total,
            source_ids=candidate_owned,
            draft_ids=draft_ids,
            context_source_ids=context_sources,
            context_draft_ids=context_drafts,
            structured=structured,
            capacity=capacity,
            output_tokens=output_tokens,
            reasoning_shares_budget=reasoning_shares_budget,
        )

    plan = attempt(new_owned, [])
    if (
        plan.input_tokens <= _ceiling(capacity)
        and plan.output_tokens_estimate <= out_budget.usable_output_tokens
    ):
        return [plan], owned_sources | set(new_owned)
    draft_groups = _draft_row_groups(material, draft_ids)
    if len(draft_groups) == 1:
        # Single atomic draft group: if co-owned sources push input or output over budget,
        # keep those cited sources as read-only context and defer their ownership to source parts.
        if new_owned:
            source_groups = _source_row_groups(material, new_owned)
            for keep_count in range(len(source_groups) - 1, -1, -1):
                kept = [key for grp in source_groups[:keep_count] for key in grp]
                deferred = [key for grp in source_groups[keep_count:] for key in grp]
                trimmed = attempt(kept, deferred)
                limit_in = _ceiling(capacity) if keep_count > 0 else capacity
                if (
                    trimmed.input_tokens <= limit_in
                    and trimmed.output_tokens_estimate <= out_budget.usable_output_tokens
                ):
                    return [trimmed], owned_sources | set(kept)
        if (
            plan.input_tokens <= capacity
            and plan.output_tokens_estimate <= out_budget.usable_output_tokens
        ):
            return [plan], owned_sources | set(new_owned)
        raise _invalid(
            "Một đơn vị review vượt ngân sách model; không cắt nội dung.",
            "compilation_review_segment_too_large",
        )
    middle = len(draft_groups) // 2
    left_ids = [key for grp in draft_groups[:middle] for key in grp]
    right_ids = [key for grp in draft_groups[middle:] for key in grp]
    left, owned_after_left = _build_group(
        material,
        left_ids,
        owned_sources,
        index=index,
        total=total,
        structured=structured,
        capacity=capacity,
        output_tokens=output_tokens,
        reasoning_shares_budget=reasoning_shares_budget,
    )
    right, owned_after_right = _build_group(
        material,
        right_ids,
        owned_after_left,
        index=index + len(left),
        total=total,
        structured=structured,
        capacity=capacity,
        output_tokens=output_tokens,
        reasoning_shares_budget=reasoning_shares_budget,
    )
    return [*left, *right], owned_after_right


def _source_groups(units: list[dict]) -> list[list[str]]:
    """Keep a table row (and rowspan-linked rows) together; a text block stays a single review group."""
    return _source_row_groups({"source_units": units}, [unit["id"] for unit in units])


def _build_source_group(
    material: dict,
    keys: list[str],
    *,
    index: int,
    total: int,
    structured: bool,
    capacity: int,
    output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    reasoning_shares_budget: bool = True,
) -> list[ReviewPartPlan]:
    source_order = {unit["id"]: i for i, unit in enumerate(material["source_units"])}
    out_budget = output_budget(output_tokens, reasoning_shares_budget=reasoning_shares_budget)
    groups = _source_row_groups(material, keys)
    context = _source_context(material, set(keys), set(), source_order)
    draft_context = _source_draft_context(material, set(keys))
    plan = build_part(
        material,
        index=index,
        total=total,
        source_ids=keys,
        draft_ids=[],
        context_source_ids=context,
        context_draft_ids=draft_context,
        structured=structured,
        capacity=capacity,
        output_tokens=output_tokens,
        reasoning_shares_budget=reasoning_shares_budget,
    )
    if (
        plan.input_tokens <= _ceiling(capacity)
        and plan.output_tokens_estimate <= out_budget.usable_output_tokens
    ):
        return [plan]
    if len(groups) == 1:
        if (
            plan.input_tokens <= capacity
            and plan.output_tokens_estimate <= out_budget.usable_output_tokens
        ):
            return [plan]
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
        output_tokens=output_tokens,
        reasoning_shares_budget=reasoning_shares_budget,
    )
    right = _build_source_group(
        material,
        right_keys,
        index=index + len(left),
        total=total,
        structured=structured,
        capacity=capacity,
        output_tokens=output_tokens,
        reasoning_shares_budget=reasoning_shares_budget,
    )
    return [*left, *right]


def plan_parts(
    material: dict,
    *,
    capacity: int,
    structured: bool,
    output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    reasoning_shares_budget: bool = True,
) -> list[ReviewPartPlan]:
    if not material["source_units"] and not material["draft_units"]:
        raise _invalid("Bản nháp không có đơn vị để review.", "compilation_review_empty")
    out_budget = output_budget(output_tokens, reasoning_shares_budget=reasoning_shares_budget)
    target_bytes = max(2048, int(capacity * TARGET_RATIO))
    target_output_tokens = max(1, int(out_budget.usable_output_tokens * 0.75))
    total_estimate = max(2, len(material["draft_units"]))
    plans: list[ReviewPartPlan] = []
    owned_sources: set[str] = set()
    # A copied table must not share ownership with prose: exact cell checks then
    # remain local, while prose gets the full mandatory citation context.
    batches: list[list[dict]] = []
    for unit in material["draft_units"]:
        if not batches or (unit.get("kind") == "table_cell") != (
            batches[-1][-1].get("kind") == "table_cell"
        ):
            batches.append([])
        batches[-1].append(unit)
    chunks = [
        chunk
        for batch in batches
        for chunk in _chunks(
            material,
            batch,
            target_bytes,
            target_output_tokens,
            structured=structured,
        )
    ]
    for chunk in chunks:
        group, owned_sources = _build_group(
            material,
            [unit["id"] for unit in chunk],
            owned_sources,
            index=len(plans) + 1,
            total=total_estimate,
            structured=structured,
            capacity=capacity,
            output_tokens=output_tokens,
            reasoning_shares_budget=reasoning_shares_budget,
        )
        plans.extend(group)
    remaining = [unit for unit in material["source_units"] if unit["id"] not in owned_sources]
    for group in _groups_by_bytes(
        _source_groups(remaining),
        remaining,
        target_bytes,
        target_output_tokens=target_output_tokens,
        structured=structured,
    ):
        plans.extend(
            _build_source_group(
                material,
                group,
                index=len(plans) + 1,
                total=total_estimate,
                structured=structured,
                capacity=capacity,
                output_tokens=output_tokens,
                reasoning_shares_budget=reasoning_shares_budget,
            )
        )
    return finalize_parts(
        plans,
        material,
        capacity=capacity,
        structured=structured,
        output_tokens=output_tokens,
        reasoning_shares_budget=reasoning_shares_budget,
    )


def _groups_by_bytes(
    groups: list[list[str]],
    units: list[dict],
    target_bytes: int,
    *,
    target_output_tokens: int | None = None,
    structured: bool = False,
) -> list[list[str]]:
    units_by_id = {unit["id"]: unit for unit in units}
    sizes = {unit["id"]: _unit_bytes(unit) for unit in units}
    chunks: list[list[str]] = []
    current: list[str] = []
    size = 0
    out_tokens = BASE_OUTPUT_TOKENS
    for group in groups:
        width = sum(sizes.get(key, 0) for key in group)
        group_out = sum(
            estimate_unit_output_tokens(
                units_by_id[key], role="source", structured=structured
            )
            for key in group
            if key in units_by_id
        )
        if current and (
            size + width > target_bytes
            or (
                target_output_tokens is not None
                and out_tokens + group_out > target_output_tokens
            )
        ):
            chunks.append(current)
            current, size, out_tokens = [], 0, BASE_OUTPUT_TOKENS
        current.extend(group)
        size += width
        out_tokens += group_out
    if current:
        chunks.append(current)
    return chunks


def finalize_parts(
    plans: list[ReviewPartPlan],
    material: dict,
    *,
    capacity: int,
    structured: bool,
    output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    reasoning_shares_budget: bool = True,
) -> list[ReviewPartPlan]:
    """Recompute exact messages with the real part count and prove full coverage."""
    total = len(plans)
    out_budget = output_budget(output_tokens, reasoning_shares_budget=reasoning_shares_budget)
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
            projection=plan.projection,
            capacity=capacity,
            output_tokens=output_tokens,
            reasoning_shares_budget=reasoning_shares_budget,
        )
        if (
            rebuilt.input_tokens > capacity
            or rebuilt.output_tokens_estimate > out_budget.usable_output_tokens
        ):
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
    reasoning_shares_budget: bool = True,
) -> dict:
    out_budget = output_budget(output_tokens, reasoning_shares_budget=reasoning_shares_budget)
    return {
        "schema_version": MANIFEST_VERSION,
        "planner_version": PLANNER_VERSION,
        "prompt_version": SEGMENT_PROMPT_VERSION,
        "review_schema_version": report.VERSION,
        "review_id": review.id,
        "compilation_run_id": review.compilation_run_id,
        "bundle_sha256": review.bundle_sha256,
        "topic": material["topic"],
        "budget": {
            "input_capacity_tokens": capacity,
            "input_ceiling_tokens": _ceiling(capacity),
            "input_headroom_tokens": max(0, capacity - _ceiling(capacity)),
            "output_tokens": output_tokens,
            "usable_output_tokens": out_budget.usable_output_tokens,
            "reasoning_reserve_tokens": out_budget.reasoning_reserve_tokens,
            "framing_reserve_tokens": out_budget.framing_reserve_tokens,
            "reasoning_shares_budget": out_budget.reasoning_shares_budget,
            "target_ratio": TARGET_RATIO,
        },
        "segments": [plan.scope_dict() for plan in plans],
        "coverage": {
            "source_unit_count": len(material["source_units"]),
            "draft_unit_count": len(material["draft_units"]),
        },
    }


def plan_from_scope(scope: dict) -> ReviewPartPlan:
    budget_info = scope.get("budget") or {}
    replay_info = scope.get("replay") or {}
    return ReviewPartPlan(
        index=scope["index"],
        source_ids=tuple(scope.get("source_ids", [])),
        draft_ids=tuple(scope.get("draft_ids", [])),
        context_source_ids=tuple(scope.get("context_source_ids", [])),
        context_draft_ids=tuple(scope.get("context_draft_ids", [])),
        input_sha256=scope["input_sha256"],
        input_tokens=scope.get("input_tokens", 0),
        schema_sha256=scope.get("schema_sha256"),
        projection=scope.get("projection", "full"),
        output_tokens_estimate=scope.get("output_tokens_estimate", 0),
        output_bytes_estimate=scope.get("output_bytes_estimate", 0),
        input_budget_tokens=budget_info.get("input_budget_tokens", 0),
        input_headroom_tokens=budget_info.get("input_headroom_tokens", 0),
        max_output_tokens=budget_info.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS),
        output_budget_tokens=budget_info.get("output_budget_tokens", 0),
        output_headroom_tokens=budget_info.get("output_headroom_tokens", 0),
        reasoning_reserve_tokens=budget_info.get("reasoning_reserve_tokens", 0),
        framing_reserve_tokens=budget_info.get("framing_reserve_tokens", 0),
        planner_version=replay_info.get("planner_version", PLANNER_VERSION),
        prompt_version=replay_info.get("prompt_version", LEGACY_SEGMENT_PROMPT_VERSION),
        schema_version=replay_info.get("schema_version", report.VERSION),
        prompt_sha256=replay_info.get("prompt_sha256", ""),
        request_total=int(scope.get("request_total") or 1),
    )


def rebuild_part(
    material: dict, scope: dict, *, total: int, structured: bool
) -> tuple[ReviewPartPlan, list[ChatMessage], dict | None]:
    """Rebuild exactly the planned request; the returned messages are the hashed ones.

    ``total`` only applies to legacy scopes without a stored ``request_total``. The
    stored scope always wins, and the hash check below runs on the very messages and
    schema handed back, so what is sent can never differ from what was verified.
    """
    plan = plan_from_scope(scope)
    effective_total = int(scope.get("request_total") or total)
    rebuilt = build_part(
        material,
        index=plan.index,
        total=effective_total,
        source_ids=plan.source_ids,
        draft_ids=plan.draft_ids,
        context_source_ids=plan.context_source_ids,
        context_draft_ids=plan.context_draft_ids,
        structured=structured,
        projection=plan.projection,
        capacity=plan.input_budget_tokens,
        output_tokens=plan.max_output_tokens,
        prompt_version=plan.prompt_version,
    )
    messages = messages_for(
        rebuilt.payload,
        structured=structured,
        index=plan.index,
        total=effective_total,
        prompt_version=plan.prompt_version,
    )
    schema = (
        report.output_schema(
            rebuilt.payload,
            require_references=2
            if plan.projection == "compact/v3"
            else int(plan.projection == "compact/v2"),
        )
        if structured
        else None
    )
    schema_sha = _sha(json_bytes(schema)) if schema is not None else None
    if (
        _sha(messages[-1].content) != plan.input_sha256
        or schema_sha != plan.schema_sha256
        or (plan.prompt_sha256 and _sha(messages[0].content) != plan.prompt_sha256)
    ):
        raise AppException(
            "Phần review không còn khớp kế hoạch đã lưu.",
            code="compilation_review_segment_mismatch",
            status_code=409,
        )
    return rebuilt, messages, schema
