"""Partition a complete keyed response into reusable checks and units to reassess."""

from dataclasses import dataclass

from qnu.domains.knowledge.compilation.review import parts, report
from qnu.domains.knowledge.compilation.review.schemas import ReviewContent


@dataclass(frozen=True, slots=True)
class RepairPlan:
    accepted: ReviewContent
    ignored_context: int
    children: tuple[parts.ReviewPartPlan, parts.ReviewPartPlan] | None = None


def _contexts(material, parent, sources, drafts):
    # Keep the original opposite-side evidence. Trim same-side context to the
    # structural neighbours of the targets, always within the parent's scope.
    source_order = {unit["id"]: i for i, unit in enumerate(material["source_units"])}
    draft_order = {unit["id"]: i for i, unit in enumerate(material["draft_units"])}
    source_context = (
        parent.payload["allowed_source_ids"]
        if drafts
        else parts._source_context(material, set(sources), set(), source_order)
    )
    draft_context = (
        parent.payload["allowed_draft_ids"]
        if sources
        else parts._draft_context(material, set(drafts), draft_order, set())
    )
    return (
        sorted(
            set(source_context) & set(parent.payload["allowed_source_ids"]) - set(sources),
            key=source_order.__getitem__,
        ),
        sorted(
            set(draft_context) & set(parent.payload["allowed_draft_ids"]) - set(drafts),
            key=draft_order.__getitem__,
        ),
    )


def plan_repair(
    material: dict,
    parent: parts.ReviewPartPlan,
    content: str,
    *,
    next_index: int,
    total: int,
    reasoning_shares_budget: bool,
) -> RepairPlan | None:
    result = report.reusable_keyed(content, parent.payload)
    if result is None:
        return None
    accepted, ignored = result
    good_sources = {item.source_id for item in accepted.source_assessments}
    good_drafts = {item.draft_id for item in accepted.draft_assessments}
    if not (good_sources or good_drafts):
        return None
    retry_sources = [key for key in parent.source_ids if key not in good_sources]
    retry_drafts = [key for key in parent.draft_ids if key not in good_drafts]
    if not (retry_sources or retry_drafts):
        return RepairPlan(accepted, ignored)

    source_context, draft_context = _contexts(material, parent, retry_sources, retry_drafts)
    options = {
        "total": total,
        "structured": True,
        "projection": parent.projection,
        "capacity": parent.input_budget_tokens,
        "output_tokens": parent.max_output_tokens,
        "reasoning_shares_budget": reasoning_shares_budget,
        "prompt_version": parent.prompt_version,
    }
    retry = parts.build_part(
        material,
        index=next_index + 1,
        source_ids=retry_sources,
        draft_ids=retry_drafts,
        context_source_ids=source_context,
        context_draft_ids=draft_context,
        **options,
    )
    if (
        retry.input_tokens > parent.input_budget_tokens
        or retry.output_tokens_estimate > retry.output_budget_tokens
    ):
        return None

    reused = parts.build_part(
        material,
        index=next_index,
        source_ids=[key for key in parent.source_ids if key in good_sources],
        draft_ids=[key for key in parent.draft_ids if key in good_drafts],
        context_source_ids=list(
            dict.fromkeys(
                ref
                for item in accepted.draft_assessments
                for ref in item.source_ids
                if ref not in good_sources
            )
        ),
        context_draft_ids=list(
            dict.fromkeys(
                ref
                for item in accepted.source_assessments
                for ref in item.draft_ids
                if ref not in good_drafts
            )
        ),
        **options,
    )
    return RepairPlan(accepted, ignored, (reused, retry))
