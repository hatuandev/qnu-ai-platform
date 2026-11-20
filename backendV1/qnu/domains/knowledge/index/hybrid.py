"""Scoped PostgreSQL simple FTS + dense reciprocal rank fusion; never mix raw score scales."""

import re
import time
import unicodedata
import uuid
from collections import defaultdict
from itertools import pairwise
from typing import Any

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
        if identifier or re.fullmatch(r"0\d{3,}", term) or re.fullmatch(r"\d{7}", term):
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


SINGLE_DOC_CANDIDATE_K = 15
MULTI_DOC_CANDIDATE_K = 30

COMPARISON_KEYWORDS = re.compile(
    r"\b(?:so sánh|đối chiếu|khác nhau|phân biệt|giữa\s+.+\s+và|các văn bản|tất cả văn bản|toàn bộ kế hoạch|văn bản nào.+văn bản nào|cả hai)\b",
    re.IGNORECASE,
)
DOC_CODE_PATTERN = re.compile(r"\b\d+/[A-ZĐa-zđ]+(?:-[A-ZĐa-zđ]+)*\b")
DOC_NUM_PATTERN = re.compile(r"\b(?:QĐ|Quyết định|KH|Kế hoạch|TT|Thông tư)\s*(\d{1,5})\b", re.IGNORECASE)
TUYEN_SINH_PATTERN = re.compile(
    r"\b(?:tuyển sinh|xét tuyển|đề án tuyển sinh|chỉ tiêu|tổ hợp môn|điểm chuẩn|ngành sư phạm|mã xét tuyển|7140\d{3})\b",
    re.IGNORECASE,
)


def is_single_document_scope(
    query: str,
    document_ids: list[str] | None = None,
    metadata_filter: Any = None,
) -> bool:
    """Determine whether the query targets a single specific document scope or is open/cross-doc."""
    if document_ids and len(document_ids) == 1:
        return True
    if metadata_filter and getattr(metadata_filter, "document_ids", None) and len(metadata_filter.document_ids) == 1:
        return True

    norm = " ".join(unicodedata.normalize("NFC", query or "").split()).casefold()
    if COMPARISON_KEYWORDS.search(norm):
        return False

    matched_buckets: set[str] = set()

    # Doc codes (e.g. 4740/QĐ-BGDĐT, 130/KH-ĐHQN, 07/KH-AM)
    codes = [c.upper() for c in DOC_CODE_PATTERN.findall(query)]
    for c in codes:
        if "4740" in c or "BGDĐT" in c or "BGĐĐT" in c:
            matched_buckets.add("4740")
        elif "130" in c or "ĐHQN" in c or "DHQN" in c:
            matched_buckets.add("130")
        elif "07" in c or "AM" in c:
            matched_buckets.add("07")
        else:
            matched_buckets.add(c)

    # Doc numbers (e.g. QĐ 4740, KH 130, KH 07)
    for num in DOC_NUM_PATTERN.findall(query):
        if num == "4740":
            matched_buckets.add("4740")
        elif num == "130":
            matched_buckets.add("130")
        elif num in ("07", "7"):
            matched_buckets.add("07")
        else:
            matched_buckets.add(num)

    # Bare document number tokens (e.g. 'theo QĐ 4740', 'trong KH 130')
    if not matched_buckets:
        for bare in re.findall(r"(?<!\d)(4740|130|07)(?!\d)", query):
            matched_buckets.add(bare)

    # Standalone domain if no doc code matched (e.g. Tuyển sinh)
    if not matched_buckets and TUYEN_SINH_PATTERN.search(norm):
        matched_buckets.add("tuyensinh")

    return len(matched_buckets) == 1


def apply_source_diversity(
    candidates: list,
    count: int,
    *,
    is_single_doc_target: bool = False,
) -> list:
    """Select top `count` hits while preventing a single document from starving others in open multi-doc queries."""
    if len(candidates) <= count:
        return candidates

    docs_in_candidates = {h.document_id for h in candidates if getattr(h, "document_id", None)}
    if len(docs_in_candidates) <= 1 or is_single_doc_target:
        return candidates[:count]

    max_per_doc = max(2, int(count * 0.5))
    selected = []
    seen_chunk_ids = set()
    doc_counts: dict[str, int] = {}
    deferred = []

    top_score = getattr(candidates[0], "score", None)
    min_score_threshold = (
        top_score * 0.2 if (isinstance(top_score, (int, float)) and top_score > 0.4) else None
    )

    for hit in candidates:
        if hit.chunk_id in seen_chunk_ids:
            continue
        doc_id = getattr(hit, "document_id", "") or ""
        curr_count = doc_counts.get(doc_id, 0)

        # Relevance threshold check: don't give immediate quota slot to negligible score
        hit_score = getattr(hit, "score", None)
        if (
            min_score_threshold is not None
            and isinstance(hit_score, (int, float))
            and hit_score < min_score_threshold
            and hit_score < 0.15
        ):
            deferred.append(hit)
            continue

        if curr_count < max_per_doc and len(selected) < count:
            selected.append(hit)
            seen_chunk_ids.add(hit.chunk_id)
            doc_counts[doc_id] = curr_count + 1
        else:
            deferred.append(hit)

    for hit in deferred:
        if len(selected) >= count:
            break
        if hit.chunk_id not in seen_chunk_ids:
            hit_score = getattr(hit, "score", None)
            if (
                min_score_threshold is not None
                and isinstance(hit_score, (int, float))
                and hit_score < min_score_threshold
                and hit_score < 0.15
            ):
                continue
            selected.append(hit)
            seen_chunk_ids.add(hit.chunk_id)

    if len(selected) < count:
        for hit in deferred:
            if len(selected) >= count:
                break
            if hit.chunk_id not in seen_chunk_ids:
                selected.append(hit)
                seen_chunk_ids.add(hit.chunk_id)

    return selected


def select_reranked(
    hits,
    reranked,
    count: int,
    *,
    is_single_doc_target: bool = False,
):
    """Cross-encoder order is authoritative; base fusion only built the pool."""
    known = {hit.chunk_id for hit in hits}
    candidates, seen = [], set()
    for hit in reranked:
        if hit.chunk_id in seen or hit.chunk_id not in known:
            continue
        seen.add(hit.chunk_id)
        candidates.append(hit)
    return apply_source_diversity(candidates, count, is_single_doc_target=is_single_doc_target)


async def rerank(
    db,
    actor,
    workspace_id,
    req,
    hits,
    model,
    trace,
    checkpoint,
    prepared=None,
    *,
    is_single_doc_target: bool = False,
):
    runtime = await runtime_service.resolve(db, workspace_id, req.rerank_provider_id)
    proof = await checkpoint()
    documents = [(prepared or {}).get(h.chunk_id) or rerank_text(h) for h in hits]
    trace["rerank_presentation"] = PRESENTATION_VERSION
    trace["rerank_input"] = runtime_service.measure(runtime, req.query, documents)
    documents, truncation = runtime_service.fit(runtime, req.query, documents)
    if truncation:
        trace["rerank_input"].update(truncation)
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
    selected = select_reranked(hits, reranked, req.top_k, is_single_doc_target=is_single_doc_target)
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
