"""Read compiled pages belonging to an exact source revision; never compile on GET."""

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunkSet,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.services.scope_helper import get_scoped_collection
from app.modules.knowledge.services.wiki_compiler import source_units, validate_wiki_bundle


async def read_revision_pages(db: AsyncSession, collection_id: str, binding_id: str,
                              revision_id: str, actor: Any) -> dict:
    await get_scoped_collection(db, collection_id, actor=actor)
    source = (await db.execute(select(KnowledgeSourceRevision)
        .join(KnowledgeBinding, KnowledgeBinding.id == KnowledgeSourceRevision.binding_id)
        .where(KnowledgeBinding.collection_id == collection_id, KnowledgeBinding.id == binding_id,
               KnowledgeBinding.status != "deleting", KnowledgeSourceRevision.id == revision_id))).scalar_one_or_none()
    if source is None:
        raise EntityNotFoundError("Không tìm thấy bản nguồn trong kho tri thức này.")
    indexes = (await db.execute(select(KnowledgeIndexRevision).where(
        KnowledgeIndexRevision.binding_id == binding_id, KnowledgeIndexRevision.source_revision_v2_id == revision_id,
        KnowledgeIndexRevision.status.in_(["ready", "active", "archived"])
    ).order_by(KnowledgeIndexRevision.revision_no.desc()))).scalars().all()
    for index in indexes:
        bundle = (index.parity_report or {}).get("knowledge_wiki")
        if not bundle:
            continue
        return await bundle_view(bundle, source, collection_id, index.id)
    chunk_sets = (await db.execute(select(KnowledgeChunkSet).where(
        KnowledgeChunkSet.source_revision_id == revision_id, KnowledgeChunkSet.status == "ready"
    ).order_by(KnowledgeChunkSet.created_at.desc()))).scalars().all()
    for chunk_set in chunk_sets:
        bundle = (chunk_set.chunk_config or {}).get("_knowledge_wiki")
        if bundle is None:
            continue
        return await bundle_view(bundle, source, collection_id, None)
    return {"status": "pending" if (source.parse_provenance or {}).get("knowledge_wiki_policy") else "not_requested",
            "collection_id": collection_id, "binding_id": binding_id,
            "source_revision_id": source.id, "index_revision_id": None, "pages": [], "failure_code": None}


async def bundle_view(bundle: dict, source: Any, collection_id: str, index_id: str | None) -> dict:
    await asyncio.to_thread(validate_wiki_bundle, bundle, source, collection_id)
    manifest = await asyncio.to_thread(source_units, source)
    units = {unit.id: unit for unit in manifest}
    return {"status": bundle["status"], "collection_id": collection_id, "binding_id": source.binding_id,
        "source_revision_id": source.id, "index_revision_id": index_id,
        "pages": [page_view(page, units) for page in bundle["pages"]], "failure_code": bundle.get("failure_code")}


def page_view(page: dict, units: dict) -> dict:
    ids = dict.fromkeys(ref["unit_id"] for section in page["sections"] for ref in [
        *section["references"], *(ref for scope in section["temporal"] for ref in scope["references"])])
    return {**{key: page[key] for key in ("id", "kind", "title", "markdown")}, "references": [
        {"unit_id": uid, "page_number": units[uid].page_number, "quote": units[uid].text} for uid in ids]}
