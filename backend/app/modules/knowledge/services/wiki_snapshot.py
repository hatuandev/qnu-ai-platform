"""Read-only wiki projections of a server-resolved collection snapshot."""

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.services.source_artifact import get_source_artifact
from app.modules.knowledge.services.wiki_compiler import source_units, validate_wiki_bundle
from app.modules.knowledge.services.wiki_links import build_page_links, page_references


async def snapshot_records(db: AsyncSession, snapshot: Any, candidate_mode: bool) -> list:
    if not snapshot.binding_revisions:
        return []
    query = (select(KnowledgeSourceRevision, KnowledgeIndexRevision, KnowledgeBinding)
        .join(KnowledgeIndexRevision, KnowledgeIndexRevision.source_revision_v2_id == KnowledgeSourceRevision.id)
        .join(KnowledgeBinding, KnowledgeBinding.id == KnowledgeIndexRevision.binding_id)
        .join(KnowledgeCollection, KnowledgeCollection.id == KnowledgeBinding.collection_id)
        .where(KnowledgeIndexRevision.id.in_(snapshot.binding_revisions.values()),
            KnowledgeBinding.collection_id == snapshot.collection_id, KnowledgeBinding.status == "active",
            KnowledgeCollection.is_active.is_(True), KnowledgeSourceRevision.status == "ready",
            KnowledgeCollection.index_epoch == getattr(snapshot, "collection_epoch", 1),
            KnowledgeIndexRevision.status.in_(["ready", "active"] if candidate_mode else ["active"])))
    if not candidate_mode:
        query = query.where(KnowledgeBinding.active_index_revision_id == KnowledgeIndexRevision.id)
    try:
        rows = (await db.execute(query.execution_options(populate_existing=True))).all()
    except SQLAlchemyError as exc:
        raise AppException("Không đọc được dữ liệu trang tri thức.",
                           code="KNOWLEDGE_WIKI_STORE_UNAVAILABLE", status_code=503) from exc
    return [(source, index, binding) for source, index, binding in rows
        if snapshot.binding_revisions.get(binding.id) == index.id and source.binding_id == binding.id
        and (not snapshot.vector_generations.get(binding.id)
             or snapshot.vector_generations[binding.id] == index.vector_generation_id)]


def snapshot_page(page: dict, source: Any, index_id: str | None, units: dict | None = None) -> dict:
    units = units if units is not None else {u.id: u for u in source_units(source)}
    ids = {ref["unit_id"] for ref in page_references(page)}
    facts = get_source_artifact(source).get("facts", [])
    mentions = []
    for fact in facts:
        raw = fact.get("raw_data") or {}
        uid, code, name = raw.get("source_unit_id"), raw.get("entity_code"), fact.get("entity_name")
        if (uid in ids and isinstance(code, str) and code and isinstance(name, str) and name
                and code in units[uid].text and name in units[uid].text):
            mentions.append({"code": code, "name": name, "unit_id": uid})
    return {**page, "binding_id": source.binding_id, "source_revision_id": source.id,
        "source_revision_no": source.revision_no, "index_revision_id": index_id,
        "canonical_hash": source.canonical_hash,
        "source_title": str((source.snapshot_metadata or {}).get("title") or source.binding_id),
        "mentions": list({(m["code"], m["name"], m["unit_id"]): m for m in mentions}.values()),
        "reference_locations": {uid: {"start": units[uid].start, "end": units[uid].end,
            "quote": units[uid].text, "page_number": units[uid].page_number,
            "source_locations": units[uid].source_locations} for uid in ids}}


async def load_snapshot_pages(db: AsyncSession, snapshot: Any, *, candidate_mode: bool = False,
                              review: bool = False) -> list[dict]:
    pages = []
    rows = await snapshot_records(db, snapshot, candidate_mode)
    if {binding.id for _, _, binding in rows} != set(snapshot.binding_revisions):
        raise AppException("Phạm vi phục vụ đã thay đổi; hãy tải lại bản nguồn.",
                           code="STALE_RETRIEVAL_SNAPSHOT", status_code=409)
    for source, index, _binding in rows:
        bundle = (index.parity_report or {}).get("knowledge_wiki")
        if bundle is None:
            continue
        try:
            await asyncio.to_thread(validate_wiki_bundle, bundle, source, snapshot.collection_id)
        except (AppException, ValueError, KeyError, TypeError) as exc:
            if not review:
                if isinstance(exc, AppException):
                    raise
                raise AppException("Trang tri thức không còn khớp nguồn.",
                    code="KNOWLEDGE_WIKI_LINK_INVALID", status_code=409) from exc
            continue  # Advanced Review returns the explicit integrity finding below.
        if bundle["status"] == "ready":
            pages.extend(await asyncio.to_thread(bundle_pages, bundle, source, index.id))
    return pages


def bundle_pages(bundle: dict, source: Any, index_id: str | None) -> list[dict]:
    units = {u.id: u for u in source_units(source)}
    return [snapshot_page({**page, "collection_id": bundle["collection_id"]}, source, index_id, units)
            for page in bundle["pages"]]


def require_wiki_permission(actor: Any, permission: str) -> None:
    if not actor or not actor.authenticated or not actor.has_permission(permission):
        raise AppException("Bạn không có quyền xem nội dung này.", code="forbidden", status_code=403)


async def read_collection_map(db: AsyncSession, collection_id: str, actor: Any, *, review: bool = False) -> dict:
    from app.modules.knowledge.services.wiki_consistency import check_snapshot_consistency
    from app.modules.rag.retriever import hybrid_retriever

    require_wiki_permission(actor, "ai.knowledge.review" if review else "ai.knowledge.view")
    snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, collection_id)
    pages = await load_snapshot_pages(db, snapshot, review=review)
    graph = await asyncio.to_thread(build_page_links, pages, snapshot.cache_fingerprint())
    nodes = [{key: page[key] for key in ("id", "kind", "title", "binding_id", "source_revision_id",
        "source_revision_no", "index_revision_id", "canonical_hash", "source_title")}
        | {"temporal": [{"role": scope["role"], "years": scope["years"]}
            for section in page["sections"] for scope in section["temporal"]]} for page in pages]
    visible = graph if review else {**graph,
        "links": [link for link in graph["links"] if link["status"] == "structural"]}
    # Public projection has its own seal and adjacency; no hidden candidate IDs.
    if not review:
        from app.modules.knowledge.services.wiki_compiler import digest

        allowed = {link["id"] for link in visible["links"]}
        for direction in ("outgoing", "backlinks"):
            visible[direction] = {pid: [eid for eid in ids if eid in allowed]
                                  for pid, ids in graph[direction].items()}
        visible.pop("sha256")
        visible["sha256"] = digest(visible)
    issues = await check_snapshot_consistency(db, snapshot, pages, graph) if review else []
    # A publication switch during this read must not return a partially old graph.
    epoch = await db.scalar(select(KnowledgeCollection.index_epoch).where(
        KnowledgeCollection.id == collection_id, KnowledgeCollection.is_active.is_(True)))
    if epoch != snapshot.collection_epoch:
        raise AppException("Phạm vi phục vụ đã thay đổi; hãy tải lại.", code="STALE_RETRIEVAL_SNAPSHOT", status_code=409)
    return {"collection_id": collection_id, "snapshot": snapshot.model_dump(mode="json"),
        "pages": nodes, "graph": visible,
        "issues": issues}
