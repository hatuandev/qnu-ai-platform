"""Scoped PostgreSQL simple FTS + dense reciprocal rank fusion; never mix raw score scales."""

import re
import time
import uuid
from collections import defaultdict

from sqlalchemy import cast, func, literal, select
from sqlalchemy.dialects.postgresql import REGCONFIG

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops import rerank as runtime_service
from qnu.domains.modelops.usage.service import usage_service
from qnu.platform.errors import Conflict
from qnu.ports.vector_store import VectorHit


async def lexical(
    db, run, allowed, query: str, count: int, chunk_ids: list[str] | None = None
) -> list[VectorHit]:
    tokens = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
    if not tokens:
        return []
    expression = " OR ".join('"' + t + '"' for t in tokens)
    configuration = cast(literal("simple"), REGCONFIG)
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


def fuse(dense, sparse, count: int, k: int):
    scores, hits = defaultdict(float), {}
    for branch in (dense, sparse):
        for rank, hit in enumerate(branch, 1):
            scores[hit.chunk_id] += 1 / (k + rank)
            hits[hit.chunk_id] = hit
    ranked = sorted(hits, key=lambda key: (-scores[key], key))[:count]
    return [hits[key].model_copy(update={"score": scores[key]}) for key in ranked]


async def rerank(db, actor, workspace_id, req, hits, model, trace, checkpoint):
    runtime = await runtime_service.resolve(db, workspace_id, req.rerank_provider_id)
    proof = await checkpoint()
    documents = [h.text for h in hits]
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
            req.query, documents, min(req.top_k, len(hits)), runtime_service.request(runtime)
        )
    except BaseException:
        await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
        raise
    await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
    current = await runtime_service.resolve(db, workspace_id, runtime.provider_id)
    if current.configuration_hash != runtime.configuration_hash:
        raise Conflict("Provider rerank đã thay đổi.", code="rerank_configuration_changed")
    trace.update(
        {
            "rerank_provider": runtime.public_dict(),
            "rerank_usage_id": usage.id,
            "rerank_tokens": result.total_tokens,
            "rerank_ms": round((time.monotonic() - started) * 1000, 3),
        }
    )
    return [hits[h.index].model_copy(update={"score": h.score}) for h in result.hits]
