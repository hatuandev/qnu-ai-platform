"""Dense retrieval with publication scope before TopK and SQL/manifest-backed citations."""

from __future__ import annotations

import hashlib
import json
import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.models import IndexChunk, IndexInput, IndexRun
from qnu.domains.knowledge.index.schemas import SearchHit, SearchRequest, SearchResponse
from qnu.domains.knowledge.index.scope import metadata_chunk_ids
from qnu.domains.knowledge.index.snapshots import publication_identity, published_versions
from qnu.domains.knowledge.publication.access import authorize
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.knowledge.publication.reading import read_published
from qnu.domains.modelops.embedding.runtime import resolve_embedding_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import AppException, Conflict, DependencyUnavailable
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorHit, VectorStore

logger = get_logger(__name__)


async def manifest(db: AsyncSession, blob: BlobStore, run: IndexRun) -> dict:
    if not run.manifest_key or not run.manifest_sha256:
        raise Conflict("Index chưa có manifest.", code="index_manifest_not_ready")
    try:
        payload = await blob.get_bytes(run.manifest_key)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được index manifest.", code="index_manifest_missing"
        ) from exc
    if hashlib.sha256(payload).hexdigest() != run.manifest_sha256:
        raise DependencyUnavailable(
            "Index manifest không khớp checksum.", code="index_manifest_invalid"
        )
    data = json.loads(payload)
    if (
        data.get("run_id") != run.id
        or data.get("config") != run.config
        or data.get("dimension") != run.dimension
    ):
        raise DependencyUnavailable(
            "Index manifest không khớp generation.", code="index_manifest_invalid"
        )
    return data


async def _eligible(db, blob, actor, run, document_ids) -> tuple[list[IndexInput], list[dict]]:
    current = await published_versions(db, run.workspace_id, run.collection_id, document_ids)
    inputs = list((await db.scalars(select(IndexInput).where(IndexInput.run_id == run.id))).all())
    selected = {
        r.document_id: r for r in inputs if document_ids is None or r.document_id in document_ids
    }
    for version in current:
        binding = selected.get(version.document_id)
        if binding is None or binding.version_id != version.id:
            raise Conflict(
                "Có phiên bản xuất bản chưa được index; cần generation mới.", code="index_outdated"
            )
    allowed, skipped = [], []
    current_ids = {v.document_id for v in current}
    for doc_id, binding in sorted(selected.items()):
        if doc_id not in current_ids:
            skipped.append({"document_id": doc_id, "reason": "not_published"})
            continue
        try:
            published = await read_published(
                db, blob, actor, run.workspace_id, run.collection_id, doc_id
            )
        except AppException as exc:
            if exc.code in {
                "publication_source_stale",
                "published_compilation_not_found",
                "resource_unavailable",
            }:
                skipped.append({"document_id": doc_id, "reason": exc.code})
                continue
            raise
        if publication_identity(published) != {
            k: getattr(binding, k)
            for k in (
                "document_id",
                "version_id",
                "publication_decision_id",
                "bundle_sha256",
                "version_state",
            )
        }:
            raise Conflict("Quyết định publication thay đổi; cần index mới.", code="index_outdated")
        allowed.append(binding)
    return allowed, skipped


async def _query_vector(db, actor, run, query, model: EmbeddingModel):
    runtime = await resolve_embedding_runtime(db, run.workspace_id, run.provider_id)
    if runtime.configuration_hash != run.config["provider"]["configuration_hash"]:
        raise Conflict(
            "Embedding model/config không tương thích index.", code="index_configuration_changed"
        )
    usage = await usage_service.reserve(
        db,
        actor,
        run.workspace_id,
        "embedding",
        "search:" + uuid.uuid4().hex,
        digest({"query": query, "config": runtime.configuration_hash}),
        runtime.budget([query]),
        runtime.provider_id,
    )
    try:
        result = await model.embed([query], runtime.request())
    except Exception:
        await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
        raise
    await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
    if result.dimension != run.dimension or len(result.vectors) != 1:
        raise DependencyUnavailable(
            "Query embedding không khớp dimension.", code="embedding_dimension_mismatch"
        )
    return result.vectors[0]


async def _hits(
    db: AsyncSession,
    run: IndexRun,
    allowed: list[IndexInput],
    raw: list[VectorHit],
    index_manifest: dict,
) -> list[SearchHit]:
    bindings = {b.id: b for b in allowed}
    loaded = await db.scalars(
        select(IndexChunk).where(
            IndexChunk.run_id == run.id, IndexChunk.point_id.in_([h.point_id for h in raw])
        )
    )
    rows = list(loaded.all())
    chunks = {c.point_id: c for c in rows}
    sealed = {c["id"]: c for c in index_manifest["chunks"]}
    result = []
    seen = set()
    for hit in raw:
        chunk = chunks.get(hit.point_id)
        if chunk is None or chunk.input_id not in bindings or hit.point_id in seen:
            raise DependencyUnavailable(
                "Vector hit nằm ngoài scope/index.", code="vector_response_invalid"
            )
        binding = bindings[chunk.input_id]
        proof = sealed.get(chunk.id, {})
        expected = {
            "run_id": run.id,
            "workspace_id": run.workspace_id,
            "collection_id": run.collection_id,
            "version_id": binding.version_id,
            "chunk_id": chunk.id,
            "text_sha256": chunk.text_sha256,
        }
        if (
            any(hit.payload.get(k) != v for k, v in expected.items())
            or hashlib.sha256(chunk.text.encode()).hexdigest() != proof.get("text_sha256")
            or digest(chunk.citations) != proof.get("citations_sha256")
            or digest(chunk.structure) != proof.get("structure_sha256")
            or chunk.point_id != proof.get("point_id")
        ):
            raise DependencyUnavailable(
                "Vector/chunk không khớp manifest.", code="vector_response_invalid"
            )
        seen.add(hit.point_id)
        result.append(
            SearchHit(
                chunk_id=chunk.id,
                document_id=binding.document_id,
                version_id=binding.version_id,
                publication_decision_id=binding.publication_decision_id,
                score=hit.score,
                kind=chunk.kind,
                text=chunk.text,
                citations=chunk.citations,
                structure=chunk.structure,
            )
        )
    return result


async def search(
    db: AsyncSession,
    blob: BlobStore,
    model: EmbeddingModel,
    vectors: VectorStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    req: SearchRequest,
    *,
    reranker: Reranker | None = None,
) -> SearchResponse:
    # All publication writers acquire workspace before document/source locks.
    await resolve_workspace_access(db, actor, workspace_id, for_update=True)
    await authorize(db, actor, workspace_id, collection_id)
    run = await db.scalar(
        select(IndexRun).where(
            IndexRun.workspace_id == workspace_id,
            IndexRun.collection_id == collection_id,
            IndexRun.is_active.is_(True),
            IndexRun.status == "completed",
        )
    )
    if run is None:
        raise Conflict("Chưa có index đang hoạt động.", code="index_not_ready")
    if vectors.target_hash != run.config["vector_target_hash"]:
        raise Conflict("Vector target không khớp index.", code="index_configuration_changed")
    sealed = await manifest(db, blob, run)
    allowed, skipped = await _eligible(db, blob, actor, run, req.document_ids)
    if not allowed:
        return SearchResponse(
            index_run_id=run.id,
            generation=run.generation,
            status="no_eligible_content",
            hits=[],
            eligible_documents=0,
            skipped_documents=skipped,
            trace={
                "mode": req.mode,
                "metadata_filter": req.metadata_filter.model_dump(mode="json", exclude_none=True),
            },
        )
    chunk_ids = await metadata_chunk_ids(db, run, allowed, req.metadata_filter, sealed)
    if chunk_ids == []:
        return SearchResponse(
            index_run_id=run.id,
            generation=run.generation,
            status="no_match",
            hits=[],
            eligible_documents=len(allowed),
            skipped_documents=skipped,
            trace={
                "mode": req.mode,
                "metadata_filter": req.metadata_filter.model_dump(mode="json", exclude_none=True),
                "metadata_eligible_chunks": 0,
            },
        )
    started = time.monotonic()
    query = await _query_vector(db, actor, run, req.query, model)
    embedding_ms = round((time.monotonic() - started) * 1000, 3)
    # Recheck after the embedding request releases quota/source locks. Keep this read
    # transaction locked through Qdrant retrieval so withdrawals cannot slip between checks.
    await resolve_workspace_access(db, actor, workspace_id, for_update=True)
    await authorize(db, actor, workspace_id, collection_id)
    active = await db.scalar(
        select(IndexRun.id).where(
            IndexRun.collection_id == collection_id, IndexRun.is_active.is_(True)
        )
    )
    if active != run.id:
        raise Conflict("Index đã đổi trong khi tìm kiếm.", code="index_changed")
    runtime = await resolve_embedding_runtime(db, workspace_id, run.provider_id)
    if runtime.configuration_hash != run.config["provider"]["configuration_hash"]:
        raise Conflict("Model đã đổi trong khi tìm kiếm.", code="index_configuration_changed")
    allowed, skipped = await _eligible(db, blob, actor, run, req.document_ids)
    if not allowed:
        return SearchResponse(
            index_run_id=run.id,
            generation=run.generation,
            status="no_eligible_content",
            hits=[],
            eligible_documents=0,
            skipped_documents=skipped,
        )
    sealed = await manifest(db, blob, run)
    chunk_ids = await metadata_chunk_ids(db, run, allowed, req.metadata_filter, sealed)
    if chunk_ids == []:
        return SearchResponse(
            index_run_id=run.id,
            generation=run.generation,
            status="no_match",
            hits=[],
            eligible_documents=len(allowed),
            skipped_documents=skipped,
            trace={
                "mode": req.mode,
                "metadata_filter": req.metadata_filter.model_dump(mode="json", exclude_none=True),
                "metadata_eligible_chunks": 0,
            },
        )
    dense_started = time.monotonic()
    raw = await vectors.search(
        run.vector_collection,
        query,
        req.top_k if req.mode == "dense" else req.candidate_k,
        {
            "run_id": run.id,
            "workspace_id": workspace_id,
            "collection_id": collection_id,
            "version_id": [b.version_id for b in allowed],
            **({"chunk_id": chunk_ids} if chunk_ids is not None else {}),
        },
    )
    hits = await _hits(db, run, allowed, raw, sealed)
    metadata_ids = set(chunk_ids) if chunk_ids is not None else None
    if metadata_ids is not None and any(h.chunk_id not in metadata_ids for h in hits):
        raise DependencyUnavailable(
            "Vector trả chunk ngoài phạm vi metadata.", code="vector_response_invalid"
        )
    trace = {
        "mode": req.mode,
        "dense_count": len(hits),
        "manifest_sha256": run.manifest_sha256,
        "dense_ranked_ids": [h.chunk_id for h in hits],
        "top_k": req.top_k,
        "query_embedding_ms": embedding_ms,
        "dense_ms": round((time.monotonic() - dense_started) * 1000, 3),
        "ranking": {"dense": [{"chunk_id": h.chunk_id, "score": h.score} for h in hits]},
        "score_kinds": {"dense": "vector_similarity"},
        "metadata_filter": req.metadata_filter.model_dump(mode="json", exclude_none=True),
        "metadata_eligible_chunks": len(chunk_ids) if chunk_ids is not None else None,
    }
    if req.mode != "dense":
        from qnu.domains.knowledge.index import hybrid

        lexical_started = time.monotonic()
        sparse = await hybrid.lexical(db, run, allowed, req.query, req.candidate_k, chunk_ids)
        sparse_hits = await _hits(db, run, allowed, sparse, sealed)
        trace["lexical_ms"] = round((time.monotonic() - lexical_started) * 1000, 3)
        trace["ranking"]["lexical"] = [
            {"chunk_id": h.chunk_id, "score": h.score} for h in sparse_hits
        ]
        trace["score_kinds"]["lexical"] = "postgres_ts_rank_cd"
        hits = hybrid.fuse(hits, sparse_hits, req.candidate_k, req.rrf_k)
        trace["ranking"]["fusion"] = [{"chunk_id": h.chunk_id, "score": h.score} for h in hits]
        trace["score_kinds"]["fusion"] = "rrf"
        trace.update(
            {
                "lexical": "postgres_simple_fts",
                "lexical_count": len(sparse_hits),
                "lexical_ranked_ids": [h.chunk_id for h in sparse_hits],
                "fusion_ranked_ids": [h.chunk_id for h in hits],
                "fusion": "rrf",
                "candidate_k": req.candidate_k,
                "rrf_k": req.rrf_k,
            }
        )
        if req.mode == "hybrid_rerank" and hits:
            from qnu.domains.knowledge.index.validation import validate_results

            if reranker is None:
                raise DependencyUnavailable("Chưa có adapter rerank.", code="reranker_unavailable")
            candidates = SearchResponse(
                index_run_id=run.id,
                generation=run.generation,
                status="results",
                hits=hits,
                eligible_documents=len(allowed),
                skipped_documents=skipped,
            )

            async def checkpoint():
                return await validate_results(
                    db,
                    blob,
                    vectors,
                    actor,
                    workspace_id,
                    collection_id,
                    candidates,
                    req.document_ids,
                )

            hits = await hybrid.rerank(
                db, actor, workspace_id, req, hits, reranker, trace, checkpoint
            )
            trace["ranking"]["rerank"] = [{"chunk_id": h.chunk_id, "score": h.score} for h in hits]
            trace["score_kinds"]["rerank"] = "model_relevance"
        else:
            hits = hits[: req.top_k]
    logger.info(
        "dense_search_completed",
        run_id=run.id,
        hits=len(hits),
        eligible_documents=len(allowed),
        skipped=len(skipped),
    )
    result = SearchResponse(
        index_run_id=run.id,
        generation=run.generation,
        status="results" if hits else "no_match",
        hits=hits,
        eligible_documents=len(allowed),
        skipped_documents=skipped,
        trace={**trace, "retrieval_ms": round((time.monotonic() - started) * 1000, 3)},
    )
    if req.mode == "hybrid_rerank" and hits:
        from qnu.domains.knowledge.index.validation import validate_results

        await validate_results(
            db, blob, vectors, actor, workspace_id, collection_id, result, req.document_ids
        )
    return result
