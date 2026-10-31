"""Hierarchical refinement and recovery for truncated review segments.

Only a review segment that fails with measured ``chat_output_truncated`` is split into
smaller child segments. Completed sibling segments are never re-executed, parent
ownership is partitioned losslessly across children, and strict depth/node/request/
token/time caps prevent unbounded splitting.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.compilation.refinement import diagnose as diagnose_truncation
from qnu.domains.knowledge.compilation.review import parts
from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
)
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.ocr.ids import new_id
from qnu.platform.errors import AppException

REFINEMENT_VERSION = "qnu.compiler.review.refinement/v1"
DEFAULT_MAX_DEPTH = 4
DEFAULT_MAX_SECONDS = 3600

__all__ = [
    "REFINEMENT_VERSION",
    "ReviewRefinementLimits",
    "assert_progress",
    "check_limits",
    "create_child_segments",
    "is_refinable_truncation",
    "limits_for",
    "ordered_leaves",
    "parent_ids_for",
    "request_usage",
    "segment_depth",
    "split_segment_plans",
    "total_usage",
    "verify_parent_child_coverage",
]


@dataclass(frozen=True, slots=True)
class ReviewRefinementLimits:
    max_depth: int = DEFAULT_MAX_DEPTH
    max_nodes: int = 31
    max_requests: int = 31
    max_tokens: int | None = None
    max_seconds: int = DEFAULT_MAX_SECONDS
    version: str = REFINEMENT_VERSION

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "version": self.version,
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
            "max_requests": self.max_requests,
            "max_tokens": self.max_tokens,
            "max_seconds": self.max_seconds,
        }


def is_refinable_truncation(exc: BaseException) -> bool:
    """Return True only when a segment response deterministically stopped due to output length."""
    if not isinstance(exc, AppException) or exc.code != "chat_output_truncated":
        return False
    raw = getattr(exc, "raw_body", None)
    if not raw:
        return True
    if diagnose_truncation(raw):
        return True
    try:
        choice = json.loads(raw)["choices"][0]
        return choice.get("finish_reason") == "length"
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return True


def limits_for(
    trace: dict,
    root_count: int,
    *,
    default_max_tokens: int | None = None,
) -> ReviewRefinementLimits:
    raw = (trace or {}).get("refinement_policy") or (trace or {}).get("refinement") or {}
    roots = max(1, int(root_count))
    default_nodes = max(7, roots * 15)
    max_output = int((trace or {}).get("max_output_tokens") or parts.DEFAULT_MAX_OUTPUT_TOKENS)
    fallback_tokens = default_max_tokens or (default_nodes * max_output * 4)
    return ReviewRefinementLimits(
        max_depth=max(0, int(raw.get("max_depth", DEFAULT_MAX_DEPTH))),
        max_nodes=max(1, int(raw.get("max_nodes", default_nodes))),
        max_requests=max(1, int(raw.get("max_requests", default_nodes))),
        max_tokens=(
            int(raw["max_tokens"])
            if raw.get("max_tokens") is not None
            else fallback_tokens
        ),
        max_seconds=max(1, int(raw.get("max_seconds", DEFAULT_MAX_SECONDS))),
    )


def segment_depth(segment: CompilationReviewSegment) -> int:
    cfg = segment.config or {}
    scope = segment.scope or {}
    return int(cfg.get("depth", scope.get("depth", 0)) or 0)


def parent_ids_for(segments: list[CompilationReviewSegment]) -> set[str]:
    return {seg.parent_segment_id for seg in segments if seg.parent_segment_id}


def ordered_leaves(
    segments: list[CompilationReviewSegment],
) -> list[CompilationReviewSegment]:
    """Return active leaf segments in deterministic DFS hierarchy order."""
    by_parent: dict[str | None, list[CompilationReviewSegment]] = {}
    for seg in sorted(
        segments,
        key=lambda item: (
            int((item.scope or {}).get("child_order", 0) or 0),
            item.segment_index,
        ),
    ):
        by_parent.setdefault(seg.parent_segment_id, []).append(seg)
    leaves: list[CompilationReviewSegment] = []
    visited: set[str] = set()

    def visit(node: CompilationReviewSegment) -> None:
        if node.id in visited:
            return
        visited.add(node.id)
        children = by_parent.get(node.id)
        if not children:
            leaves.append(node)
            return
        for child in children:
            visit(child)

    for root in sorted(by_parent.get(None, []), key=lambda item: item.segment_index):
        visit(root)
    for seg in sorted(segments, key=lambda item: item.segment_index):
        if seg.id not in visited and seg.id not in by_parent:
            leaves.append(seg)
    return leaves


def request_usage(segment: CompilationReviewSegment) -> tuple[bool, int | None]:
    """Return (did_call_model, observed_tokens) for a single review segment."""
    cfg = segment.config or {}
    if cfg.get("refined"):
        if cfg.get("refined_usage_unknown"):
            return True, None
        if "refined_usage_tokens" in cfg:
            val = cfg.get("refined_usage_tokens")
            return True, (int(val) if val is not None else None)
    if cfg.get("literal_assessed") and segment.usage_id is None:
        return False, 0
    called = (
        segment.attempt_count > 0
        or segment.usage_id is not None
        or segment.request_started_at is not None
    )
    if not called:
        return False, 0
    return True, segment.usage_tokens


def total_usage(segments: list[CompilationReviewSegment]) -> int | None:
    """Sum observed tokens across all executed requests (including truncated parents); keep unknown as None."""
    total = 0
    for seg in segments:
        called, tokens = request_usage(seg)
        if not called:
            continue
        if tokens is None:
            return None
        total += int(tokens)
    return total


def _executed_request_count(segments: list[CompilationReviewSegment]) -> int:
    count = 0
    for seg in segments:
        called, _ = request_usage(seg)
        if called:
            count += max(1, int(seg.attempt_count or 1))
    return count


def _observed_tokens_sum(segments: list[CompilationReviewSegment]) -> int:
    total = 0
    for seg in segments:
        called, tokens = request_usage(seg)
        if called and tokens is not None:
            total += int(tokens)
    return total


def check_limits(
    review: CompilationReview,
    segments: list[CompilationReviewSegment],
    parent: CompilationReviewSegment,
    limits: ReviewRefinementLimits,
) -> None:
    now = utcnow()
    if review.expires_at <= now:
        raise AppException(
            "Phiên review đã quá thời hạn thực thi khi chia nhỏ phần lỗi.",
            code="compilation_review_refinement_time_limit_exceeded",
            status_code=422,
        )
    if review.created_at is not None:
        elapsed = (now - review.created_at).total_seconds()
        if elapsed > limits.max_seconds:
            raise AppException(
                "Review vượt trần thời gian refinement cho phép.",
                code="compilation_review_refinement_time_limit_exceeded",
                status_code=422,
            )
    next_depth = segment_depth(parent) + 1
    if next_depth > limits.max_depth:
        raise AppException(
            "Phần review vượt độ sâu chia nhỏ tối đa.",
            code="compilation_review_refinement_depth_exceeded",
            status_code=422,
        )
    if len(segments) + 2 > limits.max_nodes:
        raise AppException(
            "Review vượt tổng số node phần con tối đa.",
            code="compilation_review_refinement_node_limit_exceeded",
            status_code=422,
        )
    if _executed_request_count(segments) + 2 > limits.max_requests:
        raise AppException(
            "Review vượt tổng số lượt gọi model tối đa.",
            code="compilation_review_refinement_request_limit_exceeded",
            status_code=422,
        )
    if limits.max_tokens is not None:
        observed = _observed_tokens_sum(segments)
        step_budget = int(
            (parent.config or {}).get("max_output_tokens")
            or (review.trace or {}).get("max_output_tokens")
            or parts.DEFAULT_MAX_OUTPUT_TOKENS
        )
        if observed + 2 * step_budget > limits.max_tokens:
            raise AppException(
                "Review vượt tổng ngân sách token refinement.",
                code="compilation_review_refinement_token_budget_exceeded",
                status_code=422,
            )


def _balanced_split(
    groups: list[list[str]], weights: dict[str, int]
) -> tuple[list[list[str]], list[list[str]]]:
    if len(groups) < 2:
        raise ValueError("Need at least two atomic groups to split")
    group_weights = [max(1, sum(weights.get(key, 1) for key in grp)) for grp in groups]
    total_weight = sum(group_weights)
    running = 0
    best_index = 1
    best_diff = total_weight
    for idx in range(1, len(groups)):
        running += group_weights[idx - 1]
        diff = abs(total_weight - 2 * running)
        if diff < best_diff:
            best_diff = diff
            best_index = idx
    return groups[:best_index], groups[best_index:]


def assert_progress(
    parent_source_ids: list[str] | tuple[str, ...],
    parent_draft_ids: list[str] | tuple[str, ...],
    children: list[parts.ReviewPartPlan] | tuple[parts.ReviewPartPlan, ...],
) -> None:
    if len(children) < 2:
        raise AppException(
            "Chia phần review phải tạo ít nhất hai phần con.",
            code="compilation_review_refinement_no_progress",
            status_code=422,
        )
    parent_total = len(parent_source_ids) + len(parent_draft_ids)
    for child in children:
        child_total = len(child.source_ids) + len(child.draft_ids)
        if child_total <= 0 or child_total >= parent_total:
            raise AppException(
                "Chia phần review không làm giảm số đơn vị sở hữu.",
                code="compilation_review_refinement_no_progress",
                status_code=422,
            )
    child_sources = [key for child in children for key in child.source_ids]
    child_drafts = [key for child in children for key in child.draft_ids]
    if Counter(child_sources) != Counter(parent_source_ids) or Counter(child_drafts) != Counter(
        parent_draft_ids
    ):
        raise AppException(
            "Phần con review không bảo toàn đúng quyền sở hữu đơn vị của phần cha.",
            code="compilation_review_plan_invalid",
            status_code=422,
        )


def split_segment_plans(
    material_payload: dict,
    parent: CompilationReviewSegment,
    *,
    next_index: int,
    total_estimate: int,
) -> tuple[parts.ReviewPartPlan, parts.ReviewPartPlan]:
    """Partition a truncated review segment along atomic row/unit boundaries into two smaller plans."""
    scope = parent.scope or {}
    cfg = parent.config or {}
    source_ids = list(scope.get("source_ids", []))
    draft_ids = list(scope.get("draft_ids", []))
    draft_groups = parts._draft_row_groups(material_payload, draft_ids)
    source_groups = parts._source_row_groups(material_payload, source_ids)
    if len(draft_groups) + len(source_groups) <= 1:
        raise AppException(
            "Đơn vị review nhỏ nhất vẫn vượt giới hạn đầu ra; không thể chia nhỏ hơn.",
            code="compilation_review_refinement_atomic_limit",
            status_code=422,
        )
    structured = bool(cfg.get("structured_output"))
    sources_by_id = {u["id"]: u for u in material_payload["source_units"]}
    drafts_by_id = {u["id"]: u for u in material_payload["draft_units"]}
    weights: dict[str, int] = {}
    for key in source_ids:
        if key in sources_by_id:
            weights[key] = parts.estimate_unit_output_tokens(
                sources_by_id[key], role="source", structured=structured
            )
    for key in draft_ids:
        if key in drafts_by_id:
            weights[key] = parts.estimate_unit_output_tokens(
                drafts_by_id[key], role="draft", structured=structured
            )

    if len(draft_groups) >= 2:
        left_d_groups, right_d_groups = _balanced_split(draft_groups, weights)
        left_drafts = [key for grp in left_d_groups for key in grp]
        right_drafts = [key for grp in right_d_groups for key in grp]
        left_refs: set[str] = set()
        right_refs: set[str] = set()
        all_source_set = set(source_ids)
        for key in left_drafts:
            left_refs.update(parts._refs(drafts_by_id[key], all_source_set))
        for key in right_drafts:
            right_refs.update(parts._refs(drafts_by_id[key], all_source_set))
        left_sources: list[str] = []
        right_sources: list[str] = []
        for s_grp in source_groups:
            grp_set = set(s_grp)
            in_left = bool(grp_set & left_refs)
            in_right = bool(grp_set & right_refs)
            if in_left and not in_right:
                left_sources.extend(s_grp)
            elif in_right and not in_left:
                right_sources.extend(s_grp)
            elif len(left_drafts) + len(left_sources) <= len(right_drafts) + len(right_sources):
                left_sources.extend(s_grp)
            else:
                right_sources.extend(s_grp)
    elif len(draft_groups) == 1 and len(source_groups) >= 1:
        left_drafts = list(draft_ids)
        left_sources = []
        right_drafts = []
        right_sources = list(source_ids)
    else:
        left_s_groups, right_s_groups = _balanced_split(source_groups, weights)
        left_sources = [key for grp in left_s_groups for key in grp]
        right_sources = [key for grp in right_s_groups for key in grp]
        left_drafts = []
        right_drafts = []

    source_order = {u["id"]: i for i, u in enumerate(material_payload["source_units"])}
    draft_order = {u["id"]: i for i, u in enumerate(material_payload["draft_units"])}
    all_source_ids = {u["id"] for u in material_payload["source_units"]}
    parent_ctx_sources = set(scope.get("context_source_ids", []))
    parent_ctx_drafts = set(scope.get("context_draft_ids", []))
    projection = scope.get("projection", "compact/v3")
    capacity = int((scope.get("budget") or {}).get("input_budget_tokens") or 0)
    max_output_tokens = int(
        cfg.get("max_output_tokens")
        or (scope.get("budget") or {}).get("max_output_tokens")
        or parts.DEFAULT_MAX_OUTPUT_TOKENS
    )
    reasoning_cfg = cfg.get("reasoning") or {}
    reasoning_shares = reasoning_cfg.get("level") != "off"

    def build_child(
        child_index: int,
        owned_s: list[str],
        owned_d: list[str],
        sibling_s: list[str],
        sibling_d: list[str],
    ) -> parts.ReviewPartPlan:
        cited_s: set[str] = set()
        for d_key in owned_d:
            unit = drafts_by_id[d_key]
            table_refs = set(unit.get("citations") or [])
            for s_unit in material_payload["source_units"]:
                if s_unit.get("table_id") in table_refs:
                    cited_s.add(s_unit["id"])
            cited_s.update(parts._refs(unit, all_source_ids))
        # Preserve any parent context sources and sibling sources cited by this child's drafts.
        cited_s |= (parent_ctx_sources | set(sibling_s)) & cited_s
        if not owned_d:
            cited_s |= parent_ctx_sources
        ctx_sources = parts._source_context(
            material_payload, set(owned_s), cited_s - set(owned_s), source_order
        )
        if owned_d:
            ctx_drafts = parts._draft_context(
                material_payload, set(owned_d), draft_order, set()
            )
            for key in parent_ctx_drafts:
                if key not in owned_d and key not in ctx_drafts:
                    ctx_drafts.append(key)
        else:
            ctx_drafts = parts._source_draft_context(material_payload, set(owned_s))
            for key in [*sibling_d, *parent_ctx_drafts]:
                if key not in ctx_drafts:
                    ctx_drafts.append(key)
        return parts.build_part(
            material_payload,
            index=child_index,
            total=total_estimate,
            source_ids=owned_s,
            draft_ids=owned_d,
            context_source_ids=ctx_sources,
            context_draft_ids=ctx_drafts,
            structured=structured,
            projection=projection,
            capacity=capacity,
            output_tokens=max_output_tokens,
            reasoning_shares_budget=reasoning_shares,
        )

    left_plan = build_child(
        next_index, left_sources, left_drafts, right_sources, right_drafts
    )
    right_plan = build_child(
        next_index + 1, right_sources, right_drafts, left_sources, left_drafts
    )
    assert_progress(source_ids, draft_ids, (left_plan, right_plan))
    return left_plan, right_plan


def create_child_segments(
    review: CompilationReview,
    parent: CompilationReviewSegment,
    children_plans: tuple[parts.ReviewPartPlan, parts.ReviewPartPlan],
    *,
    request_total: int,
    split_reason: str = "chat_output_truncated",
) -> list[CompilationReviewSegment]:
    """Create durable child CompilationReviewSegment rows linked to parent."""
    next_depth = segment_depth(parent) + 1
    parent_path = str((parent.scope or {}).get("path") or parent.segment_index)
    parent_cfg = parent.config or {}
    created: list[CompilationReviewSegment] = []
    for order_no, plan in enumerate(children_plans, start=1):
        child_scope = {
            **plan.scope_dict(),
            "parent_segment_id": parent.id,
            "parent_segment_index": parent.segment_index,
            "depth": next_depth,
            "child_order": order_no,
            "path": f"{parent_path}.{order_no}",
            "split_reason": split_reason,
            "request_total": request_total,
        }
        child_config = {
            **parent_cfg,
            "depth": next_depth,
            "parent_segment_id": parent.id,
            "parent_segment_index": parent.segment_index,
            "child_order": order_no,
            "split_reason": split_reason,
            "request_total": request_total,
        }
        child_config.pop("refined", None)
        child_config.pop("refined_reason", None)
        child_config.pop("refined_usage_tokens", None)
        child_config.pop("refined_usage_unknown", None)
        child_config.pop("child_segment_ids", None)
        created.append(
            CompilationReviewSegment(
                id=new_id("rvs"),
                review_id=review.id,
                parent_segment_id=parent.id,
                segment_index=plan.index,
                status="pending",
                attempt_count=0,
                scope=child_scope,
                input_sha256=plan.input_sha256,
                prompt_version=parts.SEGMENT_PROMPT_VERSION,
                schema_sha256=plan.schema_sha256,
                config=child_config,
                request_hash=digest(
                    {
                        "review_id": review.id,
                        "parent_segment_id": parent.id,
                        "segment_index": plan.index,
                        "input_sha256": plan.input_sha256,
                        "schema_sha256": plan.schema_sha256,
                        "configuration_hash": child_config.get("configuration_hash"),
                        "max_output_tokens": child_config.get("max_output_tokens"),
                        "structured_output": bool(child_config.get("structured_output")),
                    }
                ),
            )
        )
    parent.config = {
        **parent_cfg,
        "refined": True,
        "refined_reason": split_reason,
        "refined_usage_tokens": parent.usage_tokens,
        "refined_usage_unknown": parent.usage_tokens is None,
        "child_segment_ids": [child.id for child in created],
    }
    limits = limits_for(review.trace or {}, 1)
    remaining_seconds = max(
        60,
        int(
            limits.max_seconds
            - ((utcnow() - review.created_at).total_seconds() if review.created_at else 0)
        ),
    )
    review.expires_at = max(
        review.expires_at,
        utcnow() + timedelta(seconds=min(remaining_seconds, 1800)),
    )
    return created


def verify_parent_child_coverage(
    segments: list[CompilationReviewSegment],
) -> None:
    """Verify every refined parent segment's owned units match the disjoint union of its children."""
    by_parent: dict[str, list[CompilationReviewSegment]] = {}
    for seg in segments:
        if seg.parent_segment_id:
            by_parent.setdefault(seg.parent_segment_id, []).append(seg)
    for parent in segments:
        children = by_parent.get(parent.id)
        if not children:
            if (parent.config or {}).get("refined"):
                raise AppException(
                    "Phần review đã đánh dấu chia nhỏ nhưng thiếu phần con.",
                    code="compilation_review_segment_incomplete",
                    status_code=409,
                )
            continue
        p_sources = list((parent.scope or {}).get("source_ids", []))
        p_drafts = list((parent.scope or {}).get("draft_ids", []))
        c_sources = [
            key
            for child in children
            for key in (child.scope or {}).get("source_ids", [])
        ]
        c_drafts = [
            key
            for child in children
            for key in (child.scope or {}).get("draft_ids", [])
        ]
        if Counter(p_sources) != Counter(c_sources) or Counter(p_drafts) != Counter(
            c_drafts
        ):
            raise AppException(
                "Phần con review không khớp toàn vẹn phạm vi sở hữu của phần cha.",
                code="compilation_review_plan_invalid",
                status_code=502,
            )
