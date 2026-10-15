"""Whole reviewed rows from the exact published manifest, ranked rather than guessed."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeCollection, KnowledgeFact
from app.modules.knowledge.normalization.retrieval_models import TemporalScope
from app.modules.rag.evidence_blocks import rank_blocks
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.evidence_validation import evidence_digest
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def fact_location(blocks: list[EvidenceBlock], index_id: str, raw: dict) -> tuple[str, str, list[str]]:
    """Never borrow the last paragraph's section for a reviewed table row."""
    page = raw.get("header_page_number") or raw.get("page_number")
    location = [b for b in blocks if b.index_revision_id == index_id
                and page is not None and b.page_number == page]
    sections = list(dict.fromkeys(b.section for b in sorted(location, key=lambda b: b.start) if b.section))
    return (" / ".join(sections), "\n".join(dict.fromkeys(b.header_context for b in location)), sections)


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
    sources = {b.index_revision_id: b for b in blocks}
    groups = {}
    for fact in facts:
        source = sources.get(fact.index_revision_id)
        raw = fact.raw_data or {}
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
