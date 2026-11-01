"""Bounded independent question clauses share the same authorized publication scope."""

import re

from qnu.domains.knowledge.index.search import search as search_single
from qnu.platform.errors import Conflict


def question_facets(query: str) -> list[str]:
    """Split explicit independent interrogatives; never invent a topic/year/filter.

    Keep any introductory clause with each question. No LLM planning, synonyms,
    benchmark vocabulary or retries. Ambiguous conjunctions remain one query.
    """
    prefix, sep, body = query.partition(":")
    lead = prefix + ": " if sep and len(prefix) <= 200 else ""
    text = body if lead else query
    parts = [
        p.strip(" ?;\n")
        for p in re.split(r"[?;]+\s*|\s+(?:và|còn|and)\s+", text, flags=re.IGNORECASE)
        if p.strip(" ?;\n")
    ]
    interrogative = r"bao nhiêu|như thế nào|\b(gì|nào|mấy|what|which|how)\b"
    if not 2 <= len(parts) <= 3 or not all(
        len(p.split()) >= 4 and re.search(interrogative, p, re.IGNORECASE) for p in parts
    ):
        return [query]
    # Retain the original antecedent for referential clauses, without guessing
    # entities, years or scope. Keep the existing search request size bound.
    facets = [
        f"{lead}{p}\nContext: {query}"
        if i and re.search(r"\b(?:này|đó|this|that|same|its|their)\b", p, re.IGNORECASE)
        else lead + p
        for i, p in enumerate(parts)
    ]
    return facets if all(len(p) <= 8000 for p in facets) else [query]


def interleave(results, limit):
    """Bound the final context while retaining top evidence for every question clause."""
    seen, hits = set(), []
    for rank in range(max((len(r.hits) for r in results), default=0)):
        for result in results:
            if rank < len(result.hits) and result.hits[rank].chunk_id not in seen:
                hit = result.hits[rank]
                hits.append(hit)
                seen.add(hit.chunk_id)
                if len(hits) == limit:
                    return hits
    return hits


async def search(
    db, blob, model, vectors, actor, workspace_id, collection_id, req, *, reranker=None
):
    facets = question_facets(req.query)
    if len(facets) == 1 or req.top_k < len(facets):
        return await search_single(
            db, blob, model, vectors, actor, workspace_id, collection_id, req, reranker=reranker
        )
    results = []
    for query in facets:
        result = await search_single(
            db,
            blob,
            model,
            vectors,
            actor,
            workspace_id,
            collection_id,
            req.model_copy(update={"query": query}),
            reranker=reranker,
        )
        if results and (result.index_run_id, result.generation) != (
            results[0].index_run_id,
            results[0].generation,
        ):
            raise Conflict("Index đổi giữa các ý hỏi.", code="answer_evidence_changed")
        if results and any(
            result.trace.get(key) != results[0].trace.get(key)
            for key in ("manifest_sha256", "rerank_provider")
        ):
            raise Conflict("Cấu hình tìm kiếm đổi giữa các ý hỏi.", code="answer_evidence_changed")
        results.append(result)
    hits = interleave(results, req.top_k)
    trace = {
        **results[0].trace,
        "query_plan": "explicit_interrogative_clauses/v2",
        "facets": [r.trace for r in results],
        "selected_ids": [h.chunk_id for h in hits],
    }
    return results[0].model_copy(
        update={
            "hits": hits,
            "status": "results" if hits else results[0].status,
            "trace": trace,
        }
    )
