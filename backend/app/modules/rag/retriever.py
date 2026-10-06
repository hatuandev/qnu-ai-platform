"""Hybrid Retriever — Orchestrating Dense Vector (Qdrant) + Sparse Lexical (PostgreSQL FTS)."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any

from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.stopwords import (
    extract_collection_domain_stopwords,
    get_vietnamese_stopwords,
)
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.rag.fusion import FusionCandidate, reciprocal_rank_fusion
from app.modules.rag.reranker import reranker_client
from app.modules.rag.vector_indexer import vector_indexer

logger = logging.getLogger(__name__)

# Vietnamese NLP & search stopwords dynamically loaded from configs/stopwords_vi.txt.
# Stripped so distinctive tokens (subjects, majors, codes) drive matching instead of
# ultra-common functional words and administrative boilerplate (phiên #184).
ILIKE_STOP_SYLLABLES: frozenset[str] = get_vietnamese_stopwords()

RE_ALPHANUMERIC: re.Pattern[str] = re.compile(
    r"^(?=.*[a-zà-ỹ])(?=.*\d)[a-zà-ỹ0-9]+$", re.IGNORECASE
)
RE_NUMERIC_CODE: re.Pattern[str] = re.compile(r"^\d{3,8}$")
RE_ACRONYM: re.Pattern[str] = re.compile(r"^[A-ZĐ]{2,}$")


def extract_weighted_tokens(
    query: str,
    limit: int = 12,
    extra_stopwords: set[str] | frozenset[str] | None = None,
) -> list[tuple[str, float]]:
    """Extract distinct search tokens scored by structural information density & morphology."""
    if not query:
        return []
    raw_words = re.findall(r"[A-Za-zÀ-ỹ0-9]+", query)
    scored: dict[str, float] = {}

    stopwords = get_vietnamese_stopwords()
    if extra_stopwords:
        stopwords = stopwords | extra_stopwords

    for raw_word in raw_words:
        token = raw_word.lower()
        if len(token) <= 1:
            continue
        if token in stopwords:
            continue

        if RE_ALPHANUMERIC.match(raw_word):
            weight = 4.0
        elif RE_NUMERIC_CODE.match(raw_word):
            weight = 3.5
        elif RE_ACRONYM.match(raw_word):
            weight = 2.5
        elif re.match(r"^\d{1,2}$", raw_word):
            weight = 1.2
        elif len(token) >= 7:
            weight = 1.8
        elif len(token) >= 5:
            weight = 1.2
        elif len(token) == 4:
            weight = 0.6
        else:
            weight = 0.2

        if token not in scored or weight > scored[token]:
            scored[token] = weight

    sorted_tokens = sorted(scored.items(), key=lambda item: (-item[1], -len(item[0])))
    return sorted_tokens[:limit]


def select_ilike_tokens(
    query: str,
    limit: int = 6,
    extra_stopwords: set[str] | frozenset[str] | None = None,
) -> list[str]:
    """Pick distinctive word tokens for the ILIKE fallback, ordered by information density."""
    weighted = extract_weighted_tokens(query, limit=limit, extra_stopwords=extra_stopwords)
    if weighted:
        return [t for t, _ in weighted]
    tokens = re.findall(r"\w+", (query or "").lower())
    stopwords = get_vietnamese_stopwords()
    if extra_stopwords:
        stopwords = stopwords | extra_stopwords
    return [t for t in tokens if len(t) > 2 and t not in stopwords][:limit]


def strip_vietnamese_accents(text: str) -> str:
    """Remove Vietnamese diacritics so unaccented queries can still match accented content."""
    normalized = unicodedata.normalize("NFD", text or "")
    stripped = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return stripped.replace("đ", "d").replace("Đ", "D")


def is_unaccented_query(query: str) -> bool:
    """Detect queries typed without Vietnamese diacritics (e.g. 'nganh cntt')."""
    if not re.search(r"[a-zA-Z]", query or ""):
        return False
    return strip_vietnamese_accents(query) == query


class HybridRetriever:
    """Executes multi-stage hybrid retrieval with RRF fusion and reranking."""

    async def search_sparse_fts(
        self,
        db: AsyncSession,
        collection_id: str,
        query: str,
        top_k: int = 10,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        collection_name: str | None = None,
        extra_stopwords: set[str] | frozenset[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform lexical keyword search in PostgreSQL using weighted information density scoring & FTS."""
        from app.modules.knowledge.models import KnowledgeCollection

        chunks: list[KnowledgeChunk] = []
        seen_ids: set[str] = set()

        # Dynamic collection-specific stopwords: words in collection title appear in ~100% of chunks
        effective_extra = set(extra_stopwords or set())
        if collection_name:
            effective_extra |= extract_collection_domain_stopwords(collection_name)

        weighted_tokens = extract_weighted_tokens(query, limit=12, extra_stopwords=effective_extra)

        # 1. Primary: Weighted Information Density ILIKE Matching with Document Anchor Scoping
        if weighted_tokens:
            score_cases = []
            conditions = []
            for token, weight in weighted_tokens:
                is_code = (
                    bool(RE_ALPHANUMERIC.match(token))
                    or bool(RE_NUMERIC_CODE.match(token))
                    or bool(RE_ACRONYM.match(token.upper()))
                )
                content_match = KnowledgeChunk.content.ilike(f"%{token}%")
                doc_match = or_(
                    KnowledgeDocument.file_name.ilike(f"%{token}%"),
                    KnowledgeDocument.title.ilike(f"%{token}%"),
                )
                term_match = or_(content_match, doc_match)
                conditions.append(term_match)

                # Document Anchor Scoping: when an exact code or document number (e.g. 123, 1897, BC03)
                # matches document metadata, elevate chunks from that document.
                if is_code:
                    score_cases.append(
                        case(
                            (and_(content_match, doc_match), weight * 1.5),
                            (doc_match, weight * 1.2),
                            (content_match, weight),
                            else_=0.0,
                        )
                    )
                else:
                    score_cases.append(
                        case(
                            (and_(content_match, doc_match), weight * 1.3),
                            (term_match, weight),
                            else_=0.0,
                        )
                    )

            total_score = (
                sum(score_cases[1:], score_cases[0])
                if len(score_cases) > 1
                else score_cases[0]
            )
            match_expr = or_(*conditions)

            stmt_weighted = (
                select(KnowledgeChunk)
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .join(KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id)
                .where(
                    KnowledgeChunk.collection_id == collection_id,
                    KnowledgeDocument.status.in_(["approved", "ready"]),
                    KnowledgeDocument.is_active.is_(True),
                    match_expr,
                )
            )
            if tenant_id:
                stmt_weighted = stmt_weighted.where(KnowledgeCollection.tenant_id == tenant_id)
            if workspace_id:
                stmt_weighted = stmt_weighted.where(KnowledgeCollection.workspace_id == workspace_id)
            stmt_weighted = stmt_weighted.order_by(desc(total_score)).limit(top_k)

            try:
                res_weighted = await db.execute(stmt_weighted)
                scalars_weighted = res_weighted.scalars()
                for c in list(scalars_weighted.all()) if hasattr(scalars_weighted, "all") else []:
                    if c.id not in seen_ids:
                        chunks.append(c)
                        seen_ids.add(c.id)
                        if len(chunks) >= top_k:
                            break
            except Exception as e_weighted:
                logger.debug("Sparse weighted ILIKE search failed: %s", e_weighted)

        # 2. Supplementary: Disjunctive OR-Weighted Full-Text Search with ts_rank_cd
        if len(chunks) < top_k:
            try:
                # Sanitize high-entropy alphanumeric tokens for PostgreSQL tsquery
                safe_ts_tokens = [re.sub(r"[^\w]+", "", t) for t, _ in weighted_tokens[:8]]
                safe_ts_tokens = [t for t in safe_ts_tokens if len(t) >= 2]
                if safe_ts_tokens:
                    or_query_str = " | ".join(safe_ts_tokens)
                    ts_query = func.to_tsquery("simple", or_query_str)
                else:
                    ts_query = func.websearch_to_tsquery("simple", query.strip())

                ts_vector = func.to_tsvector("simple", KnowledgeChunk.content)
                rank_expr = func.ts_rank_cd(ts_vector, ts_query)

                stmt_fts = (
                    select(KnowledgeChunk)
                    .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                    .join(KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id)
                    .where(
                        KnowledgeChunk.collection_id == collection_id,
                        KnowledgeDocument.status.in_(["approved", "ready"]),
                        KnowledgeDocument.is_active.is_(True),
                        ts_vector.op("@@")(ts_query),
                    )
                )
                if tenant_id:
                    stmt_fts = stmt_fts.where(KnowledgeCollection.tenant_id == tenant_id)
                if workspace_id:
                    stmt_fts = stmt_fts.where(KnowledgeCollection.workspace_id == workspace_id)
                stmt_fts = stmt_fts.order_by(desc(rank_expr)).limit(top_k)
                res_fts = await db.execute(stmt_fts)
                scalars_fts = res_fts.scalars()
                for c in list(scalars_fts.all()) if hasattr(scalars_fts, "all") else []:
                    if c.id not in seen_ids:
                        chunks.append(c)
                        seen_ids.add(c.id)
                        if len(chunks) >= top_k:
                            break
            except Exception as e_fts:
                logger.debug("PostgreSQL FTS ts_rank skipped or unsupported: %s", e_fts)

        # 3. Unaccented fallback for queries typed without diacritics
        if len(chunks) < top_k and is_unaccented_query(query):
            try:
                uni_weighted = extract_weighted_tokens(strip_vietnamese_accents(query), limit=8)
                if uni_weighted:
                    uni_cases = []
                    uni_conds = []
                    for token, weight in uni_weighted:
                        u_content = func.unaccent(KnowledgeChunk.content).ilike(f"%{token}%")
                        u_doc = or_(
                            func.unaccent(KnowledgeDocument.file_name).ilike(f"%{token}%"),
                            func.unaccent(KnowledgeDocument.title).ilike(f"%{token}%"),
                        )
                        u_match = or_(u_content, u_doc)
                        uni_conds.append(u_match)
                        uni_cases.append(
                            case(
                                (and_(u_content, u_doc), weight * 1.3),
                                (u_match, weight),
                                else_=0.0,
                            )
                        )
                    uni_total_score = (
                        sum(uni_cases[1:], uni_cases[0])
                        if len(uni_cases) > 1
                        else uni_cases[0]
                    )
                    stmt_uni = (
                        select(KnowledgeChunk)
                        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                        .join(KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id)
                        .where(
                            KnowledgeChunk.collection_id == collection_id,
                            KnowledgeDocument.status.in_(["approved", "ready"]),
                            KnowledgeDocument.is_active.is_(True),
                            or_(*uni_conds),
                        )
                    )
                    if tenant_id:
                        stmt_uni = stmt_uni.where(KnowledgeCollection.tenant_id == tenant_id)
                    if workspace_id:
                        stmt_uni = stmt_uni.where(KnowledgeCollection.workspace_id == workspace_id)
                    stmt_uni = stmt_uni.order_by(desc(uni_total_score)).limit(top_k)
                    res_uni = await db.execute(stmt_uni)
                    scalars_uni = res_uni.scalars()
                    for c in list(scalars_uni.all()) if hasattr(scalars_uni, "all") else []:
                        if c.id not in seen_ids:
                            chunks.append(c)
                            seen_ids.add(c.id)
                            if len(chunks) >= top_k:
                                break
            except Exception as e_uni:
                logger.debug("Unaccent ILIKE fallback skipped: %s", e_uni)

        # Batch-fetch document titles to provide human-friendly citation labels
        doc_ids = {c.document_id for c in chunks if c.document_id}
        doc_title_map: dict[str, str] = {}
        if doc_ids:
            try:
                docs_res = await db.execute(
                    select(KnowledgeDocument.id, KnowledgeDocument.title).where(
                        KnowledgeDocument.id.in_(doc_ids)
                    )
                )
                for d_id, d_title in docs_res.all():
                    if d_title:
                        doc_title_map[d_id] = d_title
            except Exception as e_docs:
                logger.debug("Document title lookup skipped: %s", e_docs)

        results: list[dict[str, Any]] = []
        for idx, c in enumerate(chunks, start=1):
            meta = dict(c.chunk_metadata or {})
            doc_title = doc_title_map.get(c.document_id)
            if doc_title and not meta.get("document_title"):
                meta["document_title"] = doc_title
            results.append(
                {
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "content": c.content,
                    "section": c.section or doc_title,
                    "page_number": c.page_number,
                    "score": 1.0 / idx,
                    "metadata": meta,
                }
            )
        return results

    async def expand_with_neighbors(
        self,
        db: AsyncSession,
        candidates: list[FusionCandidate],
        collection_id: str,
        window: int = 1,
        max_expansions: int = 2,
    ) -> dict[str, list[str]]:
        """Fetch adjacent chunks (parent-style context) for top candidates.

        Neighbors share the candidate's document ordered by chunk_index. Returned
        texts are prompt-only background: never citations, never evidence.
        """
        from app.modules.knowledge.models import KnowledgeCollection

        expansions: dict[str, list[str]] = {}
        if not candidates or window < 1 or max_expansions < 1:
            return expansions
        try:
            for cand in candidates[:max_expansions]:
                neighbor_idx = [cand.metadata.get("chunk_index")] if cand.metadata else [None]
                center = neighbor_idx[0] if neighbor_idx and isinstance(neighbor_idx[0], int) else None
                if center is None:
                    # Fall back to page adjacency when chunk_index is missing
                    if cand.page_number is None:
                        continue
                    stmt = (
                        select(KnowledgeChunk)
                        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                        .join(KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id)
                        .where(
                            KnowledgeChunk.collection_id == collection_id,
                            KnowledgeChunk.document_id == cand.document_id,
                            KnowledgeChunk.page_number.in_([cand.page_number - 1, cand.page_number + 1]),
                            KnowledgeDocument.status.in_(["approved", "ready"]),
                            KnowledgeDocument.is_active.is_(True),
                        )
                        .order_by(KnowledgeChunk.page_number)
                        .limit(window * 2)
                    )
                else:
                    wanted = [center + d for d in range(-window, window + 1) if d != 0]
                    stmt = (
                        select(KnowledgeChunk)
                        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                        .join(KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id)
                        .where(
                            KnowledgeChunk.collection_id == collection_id,
                            KnowledgeChunk.document_id == cand.document_id,
                            KnowledgeChunk.chunk_index.in_(wanted),
                            KnowledgeDocument.status.in_(["approved", "ready"]),
                            KnowledgeDocument.is_active.is_(True),
                        )
                        .order_by(KnowledgeChunk.chunk_index)
                        .limit(window * 2)
                    )
                res = await db.execute(stmt)
                scalars = res.scalars()
                neighbors = list(scalars.all()) if hasattr(scalars, "all") else []
                texts = [n.content for n in neighbors if n.content and n.id != cand.chunk_id]
                if texts:
                    expansions[cand.chunk_id] = texts
        except Exception as exc:
            logger.debug("Neighbor expansion skipped: %s", exc)
        return expansions

    async def retrieve(
        self,
        db: AsyncSession,
        collection_id: str,
        query: str,
        top_k: int = 8,
        rerank_top_k: int = 5,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        dense_weight: float = 1.0,
        sparse_weight: float = 1.0,
        sparse_variants: list[str] | None = None,
        reranker_policy: dict[str, Any] | None = None,
    ) -> list[FusionCandidate]:
        """Run full Hybrid Retrieval pipeline: Dense + Sparse FTS + RRF + Reranker."""
        async def _safe_dense_search() -> list[dict[str, Any]]:
            try:
                return await vector_indexer.search_dense(
                    collection_id=collection_id,
                    query=query,
                    top_k=top_k,
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                )
            except Exception as exc:
                logger.warning("Dense search encountered error, falling back to sparse degraded: %s", exc)
                return []

        async def _safe_variant_search(variant: str) -> list[dict[str, Any]]:
            try:
                return await self.search_sparse_fts(
                    db=db,
                    collection_id=collection_id,
                    query=variant,
                    top_k=max(4, top_k // 2),
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                )
            except Exception as exc:
                logger.debug("Variant sparse search skipped for '%s': %s", variant[:30], exc)
                return []

        # 1. Concurrent Dense & Sparse Search (Non-blocking asyncio.gather)
        variant_queries = [v for v in (sparse_variants or []) if v and v.strip()]
        dense_hits, sparse_hits, *variant_hits = await asyncio.gather(
            _safe_dense_search(),
            self.search_sparse_fts(
                db=db,
                collection_id=collection_id,
                query=query,
                top_k=top_k,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
            ),
            *(_safe_variant_search(v) for v in variant_queries[:2]),
        )

        # 2. Reciprocal Rank Fusion (RRF) with discounted variant lists
        extra_lists = [(hits, 0.5) for hits in variant_hits if hits]
        fused = reciprocal_rank_fusion(
            dense_results=dense_hits,
            sparse_results=sparse_hits,
            k=60,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            extra_lists=extra_lists or None,
        )

        # 3. Cross-Encoder Reranking
        rp = reranker_policy or {}
        reranker_enabled = rp.get("enabled", True)
        if not reranker_enabled:
            reranked = fused[:rerank_top_k]
        else:
            reranked = await reranker_client.rerank(
                query=query,
                candidates=fused,
                top_k=int(rp.get("top_k", rerank_top_k)),
                preferred_provider_id=rp.get("provider_id"),
                preferred_model_name=rp.get("model_name"),
                score_threshold=float(rp.get("score_threshold", 0.0)),
            )

        logger.debug(
            "Hybrid retrieval completed: query='%s', dense=%d, sparse=%d, fused=%d, reranked=%d",
            query[:40],
            len(dense_hits),
            len(sparse_hits),
            len(fused),
            len(reranked),
        )
        return reranked


hybrid_retriever = HybridRetriever()
