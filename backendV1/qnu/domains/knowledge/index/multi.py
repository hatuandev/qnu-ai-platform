"""Rank-fuse independent collection indexes; an unusable collection stays visible."""

from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.hybrid import exact_anchors, fuse
from qnu.domains.knowledge.index.hybrid import rerank as rerank_hits
from qnu.domains.knowledge.index.schemas import SearchRequest, SearchResponse
from qnu.domains.knowledge.index.search import search
from qnu.domains.knowledge.index.validation import validate_results
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.knowledge.publication.models import CompiledDocument
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import Conflict, DependencyUnavailable, EntityNotFound
from qnu.ports.blob_store import BlobStore
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorStore

# An index that cannot serve its collection is excluded with a named warning;
# provider, storage and permission failures are never converted into "no data".
EXCLUDED_CODES = frozenset({"index_not_ready", "index_outdated", "index_configuration_changed"})

# Per-collection search keeps its own candidate pool; SearchRequest caps top_k at 50.
MAX_POOL = 50


def _outcome(result: SearchResponse, collection_id: str) -> dict:
    return {
        "collection_id": collection_id,
        "status": "served",
        "index_run_id": result.index_run_id,
        "generation": result.generation,
        "eligible_documents": result.eligible_documents,
        "skipped_documents": result.skipped_documents,
        "hits": len(result.hits),
        "manifest_sha256": result.trace.get("manifest_sha256"),
    }


async def _document_owners(
    db: AsyncSession, workspace_id: str, collection_ids: list[str], document_ids: list[str]
) -> dict[str, str]:
    rows = await db.execute(
        select(CompiledDocument.id, CompiledDocument.collection_id).where(
            CompiledDocument.workspace_id == workspace_id,
            CompiledDocument.collection_id.in_(collection_ids),
            CompiledDocument.id.in_(document_ids),
        )
    )
    return {document_id: collection_id for document_id, collection_id in rows.all()}


def _pinned_for(owners: dict[str, str], collection_id: str, document_ids: list[str]) -> list[str]:
    return [document_id for document_id in document_ids if owners.get(document_id) == collection_id]


async def pinned_by_collection(
    db: AsyncSession, workspace_id: str, collection_ids: list[str], document_ids: list[str] | None
) -> dict[str, list[str]] | None:
    """Split a pinned document scope across the collections that own each document."""
    if not document_ids:
        return None
    owners = await _document_owners(db, workspace_id, collection_ids, document_ids)
    return {
        collection_id: _pinned_for(owners, collection_id, document_ids)
        for collection_id in collection_ids
    }


def _groups(hits: list, scope: dict[str, str], served: dict[str, dict]) -> dict[str, list]:
    groups: dict[str, list] = {}
    for hit in hits:
        collection_id = scope.get(hit.chunk_id)
        if collection_id is None or collection_id not in served:
            raise Conflict("Bằng chứng thiếu phạm vi kho.", code="answer_evidence_changed")
        groups.setdefault(collection_id, []).append(hit)
    return groups


async def validate_collections(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    workspace_id: str,
    result: SearchResponse,
    document_ids: list[str] | None,
    scope: dict[str, str],
) -> str:
    """Revalidate every source collection of a merged evidence set."""
    served = _served(result)
    owners = (
        await _document_owners(db, workspace_id, list(served), document_ids) if document_ids else {}
    )
    proofs = {}
    for collection_id, hits in sorted(_groups(result.hits, scope, served).items()):
        outcome = served[collection_id]
        pinned = _pinned_for(owners, collection_id, document_ids) if document_ids else None
        if document_ids and not pinned:
            raise Conflict("Bằng chứng thiếu tài liệu đã ghim.", code="answer_evidence_changed")
        proofs[collection_id] = await validate_results(
            db,
            blob,
            vectors,
            actor,
            workspace_id,
            collection_id,
            SearchResponse(
                index_run_id=outcome["index_run_id"],
                generation=outcome["generation"],
                status="results",
                hits=hits,
                eligible_documents=outcome["eligible_documents"],
                skipped_documents=[],
            ),
            pinned,
        )
    return digest(proofs)


def _served(result: SearchResponse) -> dict[str, dict]:
    return {
        item["collection_id"]: item
        for item in result.trace.get("collections") or []
        if item.get("status") == "served"
    }


async def search_collections(
    db: AsyncSession,
    blob: BlobStore,
    model: EmbeddingModel,
    vectors: VectorStore,
    actor: AuthActor,
    workspace_id: str,
    collection_ids: list[str],
    req: SearchRequest,
    *,
    reranker: Reranker | None = None,
    verify: bool = True,
) -> SearchResponse:
    ids = list(dict.fromkeys(collection_ids))
    if not ids:
        raise Conflict("Chưa chọn kho tri thức.", code="index_not_ready")
    if len(ids) == 1:
        return await search(
            db,
            blob,
            model,
            vectors,
            actor,
            workspace_id,
            ids[0],
            req,
            reranker=reranker,
            verify=verify,
        )
    started = time.monotonic()
    # One cross-collection rerank follows the merge, so each collection search
    # only builds its own hybrid candidate pool.
    pool = min(req.candidate_k, MAX_POOL) if req.mode == "hybrid_rerank" else req.top_k
    sub_req = req.model_copy(
        update={
            "mode": "hybrid" if req.mode == "hybrid_rerank" else req.mode,
            "top_k": pool,
            "rerank_provider_id": None,
        }
    )
    await resolve_workspace_access(db, actor, workspace_id, for_update=True)
    # A pinned document only constrains the collection that owns it.
    pinned = await pinned_by_collection(db, workspace_id, ids, req.document_ids)
    if pinned is not None:
        owned = {document_id for subset in pinned.values() for document_id in subset}
        if any(document_id not in owned for document_id in req.document_ids):
            raise EntityNotFound(
                "Document không thuộc scope đã chọn.", code="compiled_document_not_found"
            )
    served: list[tuple[str, SearchResponse]] = []
    excluded, failures, records = [], [], {}
    for collection_id in ids:
        await authorize(db, actor, workspace_id, collection_id)
        if pinned is not None and not pinned[collection_id]:
            records[collection_id] = {
                "collection_id": collection_id,
                "status": "excluded",
                "reason": "document_scope_excludes",
            }
            continue
        scoped = (
            sub_req.model_copy(update={"document_ids": pinned[collection_id]})
            if pinned is not None
            else sub_req
        )
        try:
            result = await search(
                db, blob, model, vectors, actor, workspace_id, collection_id, scoped, verify=False
            )
        except Conflict as exc:
            if exc.code not in EXCLUDED_CODES:
                raise
            records[collection_id] = {
                "collection_id": collection_id,
                "status": "excluded",
                "reason": exc.code,
            }
            excluded.append(records[collection_id])
            failures.append(exc)
            continue
        served.append((collection_id, result))
        records[collection_id] = _outcome(result, collection_id)
    if not served:
        raise failures[0]
    served_ids = [collection_id for collection_id, _ in served]
    scope = {hit.chunk_id: collection_id for collection_id, r in served for hit in r.hits}
    branches = [r.hits for _, r in served if r.hits]
    if len(branches) > 1:
        hits = fuse(branches, req.candidate_k, req.rrf_k, anchors=exact_anchors(req.query))
    else:
        hits = list(branches[0]) if branches else []
    trace = {
        "mode": req.mode,
        "fusion": "rrf_collections" if len(branches) > 1 else "single_collection",
        "score_kinds": {"fusion": "rrf" if len(branches) > 1 else "single_collection"},
        "ranking": {},
        "rrf_k": req.rrf_k,
        "candidate_k": req.candidate_k,
        "top_k": req.top_k,
        "metadata_filter": req.metadata_filter.model_dump(mode="json", exclude_none=True),
        "collections": [
            records[collection_id] for collection_id in ids if collection_id in records
        ],
        "excluded_collections": excluded,
        "hit_scope": scope,
        "manifests": {
            collection_id: result.trace.get("manifest_sha256") for collection_id, result in served
        },
        "collection_traces": {collection_id: result.trace for collection_id, result in served},
        "collection_scopes": [
            result.trace["scope_resolution"]
            for _, result in served
            if "scope_resolution" in result.trace
        ],
        "fusion_ranked_ids": [hit.chunk_id for hit in hits],
    }
    if req.mode == "hybrid_rerank" and hits:
        if reranker is None:
            raise DependencyUnavailable("Chưa có adapter rerank.", code="reranker_unavailable")
        candidates = list(hits)

        async def checkpoint() -> str:
            return await validate_collections(
                db,
                blob,
                vectors,
                actor,
                workspace_id,
                SearchResponse(
                    index_run_id=served[0][1].index_run_id,
                    generation=served[0][1].generation,
                    status="results",
                    hits=candidates,
                    eligible_documents=sum(
                        records[cid]["eligible_documents"] for cid in served_ids
                    ),
                    trace={"collections": [records[cid] for cid in served_ids]},
                ),
                req.document_ids,
                scope,
            )

        try:
            hits = await rerank_hits(
                db, actor, workspace_id, req, hits, reranker, trace, checkpoint
            )
        except Conflict as exc:
            # Only "no rerank model configured" degrades to fusion ranking.
            if exc.code != "model_not_configured":
                raise
            trace["rerank_skipped"] = "model_not_configured"
            hits = hits[: req.top_k]
    elif hits:
        hits = hits[: req.top_k]
    result = SearchResponse(
        index_run_id=served[0][1].index_run_id,
        generation=served[0][1].generation,
        status="results" if hits else "no_match",
        hits=hits,
        eligible_documents=sum(records[cid]["eligible_documents"] for cid in served_ids),
        skipped_documents=[
            {**skipped, "collection_id": collection_id}
            for collection_id, r in served
            for skipped in r.skipped_documents
        ],
        trace={**trace, "retrieval_ms": round((time.monotonic() - started) * 1000, 3)},
    )
    if verify and req.mode == "hybrid_rerank" and hits:
        await validate_collections(
            db, blob, vectors, actor, workspace_id, result, req.document_ids, scope
        )
    return result
