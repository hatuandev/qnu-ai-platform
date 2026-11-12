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


ANCHOR_SLOTS = 2
_ANCHOR_TOKEN = re.compile(r"[^\s,;:!?()\[\]{}\"'\u201c\u201d\u2018\u2019]+")


def exact_anchors(query: str) -> list[str]:
    """Alphanumeric identifiers and leading-zero codes are exact, low-ambiguity keys.

    A year alone is not an anchor: it is shared column scope. The rule is
    query-derived, not a vocabulary or a per-document special case.
    """
    anchors = []
    for token in _ANCHOR_TOKEN.findall(query):
        term = token.strip(".").casefold()
        identifier = bool(re.search(r"[^\W\d_]", term)) and bool(re.search(r"\d", term))
        if identifier or re.fullmatch(r"0\d{3,}", term):
            anchors.append(term)
    return list(dict.fromkeys(anchors))


def anchor_match(hit, anchors: tuple[str, ...]) -> bool:
    text = hit.text.casefold()
    return any(
        re.search(r"(?<!\w)" + re.escape(anchor) + r"(?!\w)", text) for anchor in anchors
    )


def fuse(
    branches,
    count: int,
    k: int,
    weights: list[float] | None = None,
    anchors: tuple[str, ...] | list[str] = (),
):
    """Weighted RRF with a bounded guarantee for exact-identifier candidates.

    Fusion is a candidate selector, not the final answer ranking. A candidate
    proven by an identifier in the question may sit just below the RRF cut while
    three-branch prose occupies every slot. Reserve a small tail so the reranker
    can still judge it; never raise candidate_k or duplicate a selected hit.
    """
    scores, hits, best = defaultdict(float), {}, {}
    weights = weights or [1.0] * len(branches)
    for weight, branch in zip(weights, branches):
        for rank, hit in enumerate(branch, 1):
            scores[hit.chunk_id] += weight / (k + rank)
            hits.setdefault(hit.chunk_id, hit)
            best.setdefault(hit.chunk_id, rank)
    ranked = sorted(hits, key=lambda key: (-scores[key], key))[:count]
    if anchors and len(hits) > len(ranked):
        chosen = set(ranked)
        extra = sorted(
            (best[key], key)
            for key, hit in hits.items()
            if key not in chosen and anchor_match(hit, tuple(anchors))
        )
        if extra:
            slots = min(ANCHOR_SLOTS, count, len(extra))
            ranked = ranked[: count - slots] + [key for _, key in extra[:slots]]
    return [hits[key].model_copy(update={"score": scores[key]}) for key in ranked]


def select_reranked(hits, reranked, count: int):
    """Cross-encoder order is authoritative; base fusion only built the pool."""
    known = {hit.chunk_id for hit in hits}
    selected, seen = [], set()
    for hit in reranked:
        if hit.chunk_id in seen or hit.chunk_id not in known:
            continue
        seen.add(hit.chunk_id)
        selected.append(hit)
        if len(selected) == count:
            break
    return selected


async def rerank(db, actor, workspace_id, req, hits, model, trace, checkpoint):
    runtime = await runtime_service.resolve(db, workspace_id, req.rerank_provider_id)
    proof = await checkpoint()
    documents = [rerank_text(h) for h in hits]
    trace["rerank_presentation"] = PRESENTATION_VERSION
    trace["rerank_input"] = runtime_service.measure(runtime, req.query, documents)
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
    selected = select_reranked(hits, reranked, req.top_k)
    trace["ranking"]["rerank"] = [
        {"chunk_id": h.chunk_id, "score": h.score} for h in reranked
    ]
    trace["score_kinds"]["rerank"] = "model_relevance"
    trace["ranking"]["rerank_selected"] = [
        {"chunk_id": h.chunk_id, "score": h.score} for h in selected
    ]
    trace["score_kinds"]["rerank_selection"] = "model_relevance"
    trace["rerank_ranked_ids"] = [h.chunk_id for h in reranked]
    trace["rerank_fused_ids"] = [h.chunk_id for h in selected]
    trace["rerank_candidate_count"] = len(hits)
    trace["rerank_count"] = len(reranked)
    trace.update(
        {
            "rerank_provider": runtime.public_dict(),
            "rerank_usage_id": usage.id,
            "rerank_tokens": result.total_tokens,
            "rerank_ms": round((time.monotonic() - started) * 1000, 3),
        }
    )
    return selected
