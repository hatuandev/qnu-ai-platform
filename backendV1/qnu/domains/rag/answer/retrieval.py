"""Bounded independent question clauses share the same authorized publication scope."""

import re

from qnu.domains.knowledge.index.multi import search_collections
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


def run_identity(result) -> tuple:
    """Active index identity that must not change between clauses of one question."""
    served = [
        item for item in result.trace.get("collections") or [] if item.get("status") == "served"
    ]
    if not served:
        return result.index_run_id, result.generation
    return tuple(sorted((c["collection_id"], c["index_run_id"], c["generation"]) for c in served))


def config_identity(result) -> tuple:
    served = [
        item for item in result.trace.get("collections") or [] if item.get("status") == "served"
    ]
    manifests = (
        tuple(sorted((c["collection_id"], c.get("manifest_sha256")) for c in served))
        if served
        else result.trace.get("manifest_sha256")
    )
    return manifests, result.trace.get("rerank_provider")


async def search(
    db,
    blob,
    model,
    vectors,
    actor,
    workspace_id,
    collection_ids,
    req,
    *,
    reranker=None,
    verify=True,
):
    from qnu.domains.rag.answer.decomposition import decompose_query, needs_decomposition

    decomposed = needs_decomposition(req.query)
    if decomposed:
        facets = decompose_query(req.query)
    else:
        facets = question_facets(req.query)
    if isinstance(collection_ids, str):
        ids = [collection_ids]
    else:
        ids = list(dict.fromkeys(collection_ids))

    async def run(query):
        scoped = req.model_copy(update={"query": query})
        if len(ids) == 1:
            return await search_single(
                db,
                blob,
                model,
                vectors,
                actor,
                workspace_id,
                ids[0],
                scoped,
                reranker=reranker,
                verify=verify,
            )
        return await search_collections(
            db,
            blob,
            model,
            vectors,
            actor,
            workspace_id,
            ids,
            scoped,
            reranker=reranker,
            verify=verify,
        )

    if len(facets) == 1 or req.top_k < len(facets):
        return await run(req.query)
    results = []
    for query in facets:
        result = await run(query)
        if results and run_identity(result) != run_identity(results[0]):
            raise Conflict("Index đổi giữa các ý hỏi.", code="answer_evidence_changed")
        if results and config_identity(result) != config_identity(results[0]):
            raise Conflict("Cấu hình tìm kiếm đổi giữa các ý hỏi.", code="answer_evidence_changed")
        results.append(result)
    # Each clause keeps its own retrieved top_k; the shared context budget,
    # not a global cap, bounds what reaches the prompt.
    hits = interleave(results, req.top_k * len(results))
    trace = {
        **results[0].trace,
        "query_plan": "query_decomposition/v1" if decomposed else "explicit_interrogative_clauses/v2",
        "facets": [r.trace for r in results],
        "selected_ids": [h.chunk_id for h in hits],
    }
    if any("hit_scope" in r.trace for r in results):
        trace["hit_scope"] = {
            chunk_id: owner
            for result in results
            for chunk_id, owner in (result.trace.get("hit_scope") or {}).items()
        }
    return results[0].model_copy(
        update={
            "hits": hits,
            "status": "results" if hits else results[0].status,
            "trace": trace,
        }
    )
