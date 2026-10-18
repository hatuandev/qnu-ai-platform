"""Whole reviewed rows from the exact published manifest, ranked rather than guessed."""

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeCollection, KnowledgeFact
from app.modules.knowledge.normalization.qnu_projection import VERSION as PROJECTION_VERSION
from app.modules.knowledge.normalization.retrieval_models import TemporalScope
from app.modules.knowledge.services.source_context import (
    fact_temporal_context,
    reviewed_human_temporal,
)
from app.modules.rag.evidence_blocks import rank_blocks
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.evidence_validation import evidence_digest
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

SCOPE_LEVELS = {"unknown", "block", "row", "column", "field"}
SCOPE_ROLES = {"data", "effective", "event"}


def fact_location(blocks: list[EvidenceBlock], index_id: str, raw: dict) -> tuple[str, str, list[str]]:
    """Never borrow the last paragraph's section for a reviewed table row."""
    page = raw.get("header_page_number") or raw.get("page_number")
    location = [b for b in blocks if b.index_revision_id == index_id
                and page is not None and b.page_number == page]
    sections = list(dict.fromkeys(b.section for b in sorted(location, key=lambda b: b.start) if b.section))
    return (" / ".join(sections), "\n".join(dict.fromkeys(b.header_context for b in location)), sections)


def _year_values(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return sorted({year for year in value if isinstance(year, int) and not isinstance(year, bool)})


def _verified_years(raw: dict) -> list[int]:
    context = fact_temporal_context(raw)
    basis = context.get("basis_quote")
    if (context.get("status") == "verified" and context.get("role") == "data"
            and ((isinstance(basis, str) and basis.strip()) or reviewed_human_temporal(raw) is not None)):
        return _year_values(context.get("years"))
    return []


def _declared_years(raw: dict) -> list[int]:
    """Even unverified declared years exclude a mismatching explicit request."""
    context = fact_temporal_context(raw)
    years = _year_values(context.get("years"))
    year = context.get("year")
    return years or ([year] if isinstance(year, int) and not isinstance(year, bool) else [])


def _cell_scope(row: EvidenceBlock, raw: dict) -> tuple[TemporalScope, list[int]]:
    """Cell scope stays at its declared level; only review can mark it verified."""
    context = fact_temporal_context(raw)
    status = context.get("status") if context.get("status") in {"unknown", "proposed", "verified", "ambiguous"} else "unknown"
    basis = context.get("basis_quote") if isinstance(context.get("basis_quote"), str) and context.get("basis_quote").strip() else None
    if status == "verified" and not basis and reviewed_human_temporal(raw) is None:
        status = "ambiguous"
    role = context.get("role") if status == "verified" and context.get("role") in SCOPE_ROLES else "unknown"
    years = _year_values(context.get("years"))
    data_years = years if status == "verified" and role == "data" else []
    scope_level = context.get("scope_level") if context.get("scope_level") in SCOPE_LEVELS else "unknown"
    milestones = {key: context[key] for key in ("effective_from", "effective_to", "event_from", "event_to")
                  if isinstance(context.get(key), dict)}
    scope = TemporalScope(
        issued_date=row.temporal_scope.issued_date,
        mentioned_years=years,
        data_years=data_years,
        basis_quote=basis,
        scope_level=scope_level,
        status=status,
        role=role,
        evidence_quote=basis if status == "verified" else None,
        **milestones,
    )
    return scope, data_years


def _canonical_units(blocks: list[EvidenceBlock]) -> dict[tuple[str, str], EvidenceBlock]:
    seen: dict[tuple[str, str], dict[str, EvidenceBlock]] = defaultdict(dict)
    for block in blocks:
        if block.origin == "canonical" and block.unit_id:
            seen[(block.index_revision_id, block.unit_id)][block.id] = block
    # An ambiguous duplicate unit can never prove a required dependency.
    return {key: next(iter(value.values())) for key, value in seen.items() if len(value) == 1}


def _exact_unit(index: dict[tuple[str, str], EvidenceBlock], index_id: str, unit_id: Any,
                identity: tuple[str, str, str, str]) -> EvidenceBlock | None:
    if not isinstance(unit_id, str) or not unit_id:
        return None
    block = index.get((index_id, unit_id))
    if block is None:
        return None
    if (block.binding_id, block.index_revision_id, block.source_revision_id, block.canonical_hash) != identity:
        return None
    return block


def _standard_fact(raw: dict, index: dict, fact: KnowledgeFact,
                   snapshot: RetrievalSnapshot) -> EvidenceBlock | None:
    """Resolve one fact to its exact canonical row and verified dependency closure."""
    if raw.get("projection_version") != PROJECTION_VERSION or raw.get("field_state") != "present":
        return None
    if (raw.get("context_ambiguous") or snapshot.binding_revisions.get(fact.binding_id) != fact.index_revision_id
            or (raw.get("context_review") and raw["context_review"].get("status") != "verified")):
        return None
    unit_id = raw.get("source_unit_id")
    manifest_hash = raw.get("unit_manifest_hash")
    refs = raw.get("context_unit_ids")
    if not isinstance(manifest_hash, str) or not manifest_hash or not isinstance(refs, list) \
            or any(not isinstance(ref, str) for ref in refs):
        return None
    if not refs:
        return None  # A table fact without its header chain is not self-contained.
    row = index.get((fact.index_revision_id, unit_id)) if isinstance(unit_id, str) else None
    if row is None or row.binding_id != fact.binding_id:
        return None
    parent = index.get((fact.index_revision_id, row.parent_id)) if isinstance(row.parent_id, str) else None
    if row.is_container or row.text == row.header_context or parent is None \
            or not parent.is_container or parent.fact_context.get("source_kind") != "table":
        return None
    if row.unit_manifest_hash != manifest_hash:
        return None
    block_id = raw.get("qnu_block_id")
    if not isinstance(block_id, str) or block_id != row.fact_context.get("qnu_block_id"):
        return None
    recorded = row.fact_context.get("context_unit_ids")
    if not isinstance(recorded, list) or list(recorded) != list(refs):
        return None
    locations = raw.get("source_locations")
    if not isinstance(locations, list) or locations != list(row.fact_context.get("source_locations") or []):
        return None
    identity = (row.binding_id, row.index_revision_id, row.source_revision_id, row.canonical_hash)
    pending, seen = list(dict.fromkeys(refs)), set()
    while pending:
        ref = pending.pop(0)
        if ref in seen or ref == unit_id:
            continue
        seen.add(ref)
        dependency = _exact_unit(index, fact.index_revision_id, ref, identity)
        if dependency is None:
            return None
        extra = dependency.fact_context.get("context_unit_ids") if isinstance(dependency.fact_context, dict) else None
        if extra is not None:
            if not isinstance(extra, list) or any(not isinstance(item, str) for item in extra):
                return None
            pending.extend(item for item in extra if item not in seen)
    return row


async def reviewed_fact_blocks(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot,
                               plan: QueryPlan, blocks: list[EvidenceBlock], *, exhaustive: bool = False) -> list[EvidenceBlock]:
    if not snapshot.binding_revisions:
        return []
    query = (select(KnowledgeFact).join(KnowledgeBinding, KnowledgeFact.binding_id == KnowledgeBinding.id)
        .join(KnowledgeCollection, KnowledgeBinding.collection_id == KnowledgeCollection.id)
        .where(KnowledgeFact.collection_id == req.collection_id,


               KnowledgeBinding.status == "active",
               KnowledgeFact.index_revision_id.in_(snapshot.binding_revisions.values()))
        .order_by(KnowledgeFact.id))
    try:
        facts = []
        cursor = None
        while True:
            page_query = query.where(KnowledgeFact.id > cursor) if cursor else query
            page = list((await db.execute(page_query.limit(500 if exhaustive else 5001))).scalars().all())
            facts.extend(page)
            if not exhaustive or len(page) < 500:
                break
            cursor = page[-1].id
    except Exception as exc:
        raise AppException("Không thể tải hàng bảng đã xuất bản.", code="EVIDENCE_FACT_UNAVAILABLE", status_code=503) from exc
    if not exhaustive and len(facts) > 5000:
        raise AppException("Bảng số liệu vượt ngân sách đối soát; cần phân vùng nguồn.", code="EVIDENCE_FACT_BUDGET", status_code=422)
    sources = {b.index_revision_id: b for b in blocks if b.origin == "canonical"}
    canonical = _canonical_units(blocks)
    groups, standard = {}, {}
    for fact in facts:
        raw = fact.raw_data or {}
        if raw.get("projection_version") == PROJECTION_VERSION:
            row = _standard_fact(raw, canonical, fact, snapshot)
            if not row:
                continue
            verified_years = _verified_years(raw)
            if plan.years and verified_years and not set(plan.years).intersection(verified_years):
                continue
            declared_years = _declared_years(raw)
            if plan.years and declared_years and not set(plan.years).intersection(declared_years):
                continue
            if fact.applicability_year is not None and fact.applicability_year not in verified_years:
                continue
            key = (fact.index_revision_id, raw["source_unit_id"], tuple(verified_years), fact.entity_name)
            standard.setdefault(key, {"row": row, "facts": []})["facts"].append(fact)
            continue
        source = sources.get(fact.index_revision_id)
        fact_year = fact.applicability_year or (raw.get("temporal_context") or {}).get("year")
        if fact_year and plan.years and fact_year not in plan.years:
            continue
        if (not source or raw.get("context_ambiguous") or snapshot.binding_revisions.get(fact.binding_id) != fact.index_revision_id
                or (raw.get("context_review") and raw["context_review"].get("status") != "verified")):
            continue
        key = (fact.index_revision_id, raw.get("table_id"), raw.get("row_index"), fact_year)
        if key[1] is None or key[2] is None:
            key = (fact.index_revision_id, fact.id, None, fact_year)
        if exhaustive:
            key = (*key, fact.entity_name)  # Independent identities in a side-by-side row stay separate.
        groups.setdefault(key, []).append(fact)
    result = []
    for entry in standard.values():
        members = sorted(entry["facts"], key=lambda f: ((f.raw_data or {}).get("column_index", 0), f.id))
        first, row = members[0], entry["row"]
        raw = first.raw_data or {}
        scope, verified_years = _cell_scope(row, raw)
        row_id = "facts:" + evidence_digest([{"id": f.id} for f in members])[:20]
        text = first.entity_name + "\n" + "\n".join(f"{f.attribute_name}: {f.attribute_value}" for f in members)
        refs = sorted({ref for f in members for ref in ((f.raw_data or {}).get("context_unit_ids") or [])})
        result.append(EvidenceBlock(id=row_id, binding_id=row.binding_id,
            index_revision_id=row.index_revision_id, source_revision_id=row.source_revision_id,
            title=row.title, page_number=row.page_number, section=row.section,
            header_context=row.header_context, source_context=row.source_context, text=text, start=-1, end=-1,
            scope_years=verified_years, temporal_scope=scope, canonical_hash=row.canonical_hash,
            unit_manifest_hash=row.unit_manifest_hash, origin="reviewed_fact", fact_id=first.id,
            parent_id=row.parent_id,
            fact_context={"entity_name": first.entity_name, "entity_code": getattr(first, "entity_code", None),
                "source_sections": [row.section] if row.section else [],
                "source_unit_id": raw["source_unit_id"],
                "source_locations": list(row.fact_context.get("source_locations") or []),
                "context_unit_ids": refs,
                "unit_manifest_hash": raw["unit_manifest_hash"], "projection_version": PROJECTION_VERSION,
                "verified_dependencies": True, "location_ambiguous": False,
                "row_context": raw.get("row_context") or [],
                "cells": [{"fact_id": f.id, "attribute": f.attribute_name, "value": f.attribute_value,
                "state": (f.raw_data or {}).get("field_state"),
                "temporal_context": fact_temporal_context(f.raw_data or {}),
                **{k: (f.raw_data or {}).get(k) for k in ("qualifiers", "attribute_code", "relation")}}
                for f in members]}))
    for members in groups.values():
        members.sort(key=lambda f: ((f.raw_data or {}).get("column_index", 0), f.id))
        first = members[0]
        source = sources[first.index_revision_id]
        raw = first.raw_data or {}
        section, header_context, sections = fact_location(blocks, first.index_revision_id, raw)
        row_id = "facts:" + evidence_digest([{"id": f.id} for f in members])[:20]
        text = first.entity_name + "\n" + "\n".join(f"{f.attribute_name}: {f.attribute_value}" for f in members)
        result.append(EvidenceBlock(id=row_id, binding_id=source.binding_id,
            index_revision_id=source.index_revision_id, source_revision_id=source.source_revision_id,
            title=source.title, page_number=raw.get("page_number"), section=section,
            header_context=header_context, source_context=source.source_context, text=text, start=-1, end=-1,
            scope_years=[fact_year] if (fact_year := first.applicability_year or (raw.get("temporal_context") or {}).get("year")) else [],
            temporal_scope=TemporalScope(issued_date=source.temporal_scope.issued_date,
                mentioned_years=[fact_year] if fact_year else [], data_years=[fact_year] if fact_year else [],
                role="data" if fact_year else "unknown", status="verified" if fact_year else "unknown",
                evidence_quote=text if fact_year else None), canonical_hash=source.canonical_hash,
            origin="reviewed_fact", fact_id=first.id,
            fact_context={"entity_name": first.entity_name, "entity_code": getattr(first, "entity_code", None), "source_sections": sections,
                "source_unit_id": raw.get("source_unit_id"),
                "location_ambiguous": len(sections) != 1, "row_context": raw.get("row_context") or [],
                "cells": [{"fact_id": f.id, "attribute": f.attribute_name, "value": f.attribute_value,
                **{k: (f.raw_data or {}).get(k) for k in ("temporal_context", "qualifiers", "attribute_code", "relation")}}
                for f in members]}))
    if exhaustive:
        return result
    queries = [req.question, plan.query, *plan.search_queries,
               *([plan.entity] if plan.entity else []), *([plan.attribute] if plan.attribute else [])]
    selected = [b for query in queries for b in rank_blocks(result, [query], 6, plan.years)]
    return list({b.id: b for b in selected}.values())
