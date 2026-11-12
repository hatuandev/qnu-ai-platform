"""Scoped PostgreSQL simple FTS + dense reciprocal rank fusion; never mix raw score scales."""

import re
import time
import uuid
from collections import defaultdict
from itertools import pairwise

from sqlalchemy import func, literal_column, select

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.index.presentation import PRESENTATION_VERSION, rerank_text
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops import rerank as runtime_service
from qnu.domains.modelops.usage.service import usage_service
from qnu.platform.errors import AppException, Conflict
from qnu.ports.provider_execution import bind_usage
from qnu.ports.vector_store import VectorHit


def lexical_expression(query: str, *, phrases: bool = False) -> str:
    tokens = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
    units = (
        ['"' + first + " " + second + '"' for first, second in pairwise(tokens)]
        if phrases
        else ['"' + token + '"' for token in tokens]
    )
    return " OR ".join(dict.fromkeys(units))


async def lexical(
    db,
    run,
    allowed,
    query: str,
    count: int,
    chunk_ids: list[str] | None = None,
    *,
    phrases: bool = False,
) -> list[VectorHit]:
    expression = lexical_expression(query, phrases=phrases)
    if not expression:
        return []
    # Literal, not a bind parameter: the planner only matches the expression
    # index when the regconfig appears as a constant in the statement.
    configuration = literal_column("'simple'::regconfig")
    document = func.to_tsvector(configuration, IndexChunk.text)
    query_expr = func.websearch_to_tsquery(configuration, expression)
    rank = func.ts_rank_cd(document, query_expr)
    rows = (
        await db.execute(
            select(IndexChunk, rank.label("rank"))
            .where(
                IndexChunk.workspace_id == run.workspace_id,
                IndexChunk.collection_id == run.collection_id,
                IndexChunk.run_id == run.id,
                IndexChunk.input_id.in_([b.id for b in allowed]),
                *([IndexChunk.id.in_(chunk_ids)] if chunk_ids is not None else []),
                document.op("@@")(query_expr),
            )
            .order_by(rank.desc(), IndexChunk.id)
            .limit(count)
        )
    ).all()
    bindings = {b.id: b for b in allowed}
    return [
        VectorHit(
            c.point_id,
            float(score),
            {
                "run_id": run.id,
                "workspace_id": run.workspace_id,
                "collection_id": run.collection_id,
                "version_id": bindings[c.input_id].version_id,
                "chunk_id": c.id,
                "text_sha256": c.text_sha256,
            },
        )
        for c, score in rows
    ]


RERANK_WEIGHT = 2.0
# Smaller k than base fusion so the cross-encoder outweighs the rank-only prior.
RERANK_RRF_K = 30


def fuse(branches, count: int, k: int, weights: list[float] | None = None):
    """Weighted RRF; every branch keeps its candidates instead of replacing them."""
    scores, hits = defaultdict(float), {}
    weights = weights or [1.0] * len(branches)
    for weight, branch in zip(weights, branches):
        for rank, hit in enumerate(branch, 1):
            scores[hit.chunk_id] += weight / (k + rank)
            hits.setdefault(hit.chunk_id, hit)
    ranked = sorted(hits, key=lambda key: (-scores[key], key))[:count]
    return [hits[key].model_copy(update={"score": scores[key]}) for key in ranked]


async def rerank(db, actor, workspace_id, req, hits, model, trace, checkpoint):
    runtime = await runtime_service.resolve(db, workspace_id, req.rerank_provider_id)
    proof = await checkpoint()
    documents = [rerank_text(h) for h in hits]
    trace["rerank_presentation"] = PRESENTATION_VERSION
    reserved = runtime_service.budget(runtime, req.query, documents)
    usage = await usage_service.reserve(
        db,
        actor,
        workspace_id,
        "rerank",
        "rerank:" + uuid.uuid4().hex,
        digest(
            {
                "query": req.query,
                "chunks": [h.chunk_id for h in hits],
                "config": runtime.configuration_hash,
                "presentation": PRESENTATION_VERSION,
            }
        ),
        reserved,
        runtime.provider_id,
    )
    started = time.monotonic()
    try:
        if proof != await checkpoint():
            raise Conflict("Nguồn thay đổi trước khi rerank.", code="rerank_evidence_changed")
        current = await runtime_service.resolve(db, workspace_id, runtime.provider_id)
        if current.configuration_hash != runtime.configuration_hash:
            raise Conflict("Provider rerank đã thay đổi.", code="rerank_configuration_changed")
        await db.commit()
    except BaseException:
        await usage_service.settle(db, usage.id, total_tokens=0, failed=True)
        raise
    try:
        result = await model.rerank(
            req.query,
            documents,
            len(hits),
            bind_usage(runtime_service.request(runtime), usage.id),
        )
    except BaseException as exc:
        tokens = getattr(exc, "usage_tokens", None) if isinstance(exc, AppException) else None
        measured = tokens if type(tokens) is int and 0 <= tokens <= 10**15 else None
        await usage_service.settle(db, usage.id, total_tokens=measured, failed=True)
        raise
    await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
    current = await runtime_service.resolve(db, workspace_id, runtime.provider_id)
    if current.configuration_hash != runtime.configuration_hash:
        raise Conflict("Provider rerank đã thay đổi.", code="rerank_configuration_changed")
    reranked = [hits[h.index].model_copy(update={"score": h.score}) for h in result.hits]
    fused = fuse(
        [hits, reranked],
        req.top_k,
        RERANK_RRF_K,
        weights=[1.0, RERANK_WEIGHT],
    )
    trace["ranking"]["rerank"] = [
        {"chunk_id": h.chunk_id, "score": h.score} for h in reranked
    ]
    trace["score_kinds"]["rerank"] = "model_relevance"
    trace["ranking"]["rerank_fused"] = [
        {"chunk_id": h.chunk_id, "score": h.score} for h in fused
    ]
    trace["score_kinds"]["rerank_fusion"] = "weighted_rrf"
    trace["rerank_ranked_ids"] = [h.chunk_id for h in reranked]
    trace["rerank_fused_ids"] = [h.chunk_id for h in fused]
    trace["rerank_candidate_count"] = len(hits)
    trace["rerank_count"] = len(reranked)
    trace["rerank_weight"] = RERANK_WEIGHT
    trace["rerank_rrf_k"] = RERANK_RRF_K
    trace.update(
        {
            "rerank_provider": runtime.public_dict(),
            "rerank_usage_id": usage.id,
            "rerank_tokens": result.total_tokens,
            "rerank_ms": round((time.monotonic() - started) * 1000, 3),
        }
    )
    return fused
