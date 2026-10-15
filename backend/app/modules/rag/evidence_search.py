"""Constraint-anchored query variants and fusion of genuine published hits."""

import re

from app.modules.knowledge.normalization.retrieval_models import temporal_is_compatible
from app.modules.rag.evidence_bm25 import rank_blocks
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.evidence_validation import number_values
from app.modules.rag.fusion import FusionCandidate, reciprocal_rank_fusion


def search_queries(question: str, plan: QueryPlan, missing: list[str] | None = None) -> list[str]:
    fields = [plan.target_institution, plan.entity, plan.attribute, plan.education_level, plan.method, plan.round,
              plan.event, plan.exam_organizer, *map(str, plan.years + plan.document_years + plan.event_years)]
    constraints = " · ".join(dict.fromkeys(value for value in fields if value))
    allowed = number_values(f"{question} {constraints}")
    variants = []
    for variant in [question, plan.query, *plan.search_queries]:
        if number_values(variant) - allowed:
            continue  # A rewrite must not introduce an answer number/code/year.
        if variant not in variants:
            variants.append(variant)
    if missing:
        # Feedback is not new scope or evidence. Reject injected numbers, and
        # always retain the original question and all independently resolved roles.
        focus = " · ".join(value[:200] for value in missing[:3] if not number_values(value) - allowed)
        if focus:
            variants = [f"{question} · {focus}", *variants]
    return [f"{query} · {constraints}" if constraints else query for query in variants[:4]]


def _anchor_blocks(blocks: list[EvidenceBlock], hits: list[FusionCandidate], query: str,
                   years: list[int]) -> list[EvidenceBlock]:
    result = []
    for hit in hits:
        same = [block for block in blocks if (block.binding_id, block.index_revision_id) ==
                (hit.binding_id, hit.index_revision_id) and block.page_number == hit.page_number and not block.is_container]
        unit = (hit.metadata or {}).get("source_unit") or {}
        exact = [block for block in same if (block.unit_id and block.unit_id == (hit.metadata or {}).get("source_unit_id"))
            or (isinstance(unit.get("start"), int) and isinstance(unit.get("end"), int)
                and block.start < unit["end"] and unit["start"] < block.end)
            or re.sub(r"\s+", " ", block.text) in re.sub(r"\s+", " ", hit.content)]
        result.extend(exact or rank_blocks(same, [query], 2, years))
    return list({block.id: block for block in result}.values())


def fuse_blocks(blocks: list[EvidenceBlock], queries: list[str], rankings: list[list[FusionCandidate]],
                years: list[int], limit: int) -> list[EvidenceBlock]:
    def entries(selected):
        return [{"chunk_id": b.id, "document_id": b.binding_id, "binding_id": b.binding_id,
                 "index_revision_id": b.index_revision_id, "page_number": b.page_number, "content": b.text}
                for b in selected]
    lists = []
    for index, query in enumerate(queries):
        weight = 1.0 if index == 0 else 0.7
        lists.append((entries(rank_blocks(blocks, [query], limit, years)), weight))
        lists.append((entries(_anchor_blocks(blocks, rankings[index], query, years)), weight))
    fused = reciprocal_rank_fusion([], [], extra_lists=lists)
    by_id = {block.id: block for block in blocks}
    compatible = [by_id[candidate.chunk_id] for candidate in fused if
        temporal_is_compatible(by_id[candidate.chunk_id].temporal_scope, years) and
        not (years and by_id[candidate.chunk_id].scope_years and not set(years).intersection(by_id[candidate.chunk_id].scope_years))]
    return compatible[:limit]
