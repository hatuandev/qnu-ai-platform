"""Hybrid Retriever — Orchestrating Dense Vector (Qdrant) + Sparse Lexical (PostgreSQL FTS)."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.rag.fusion import FusionCandidate, reciprocal_rank_fusion
from app.modules.rag.reranker import reranker_client
from app.modules.rag.vector_indexer import vector_indexer

logger = logging.getLogger(__name__)

# Generic Vietnamese syllables that dilute lexical search when used as ILIKE patterns.
# Stripped so distinctive tokens (subjects, majors, codes) drive matching instead of
# ultra-common words like "các / ngành / xét / tuyển" (phiên #184).
ILIKE_STOP_SYLLABLES: frozenset[str] = frozenset(
    {
        "cách", "trong", "được", "những", "thực", "hiện", "theo", "nào", "như", "thế",
        "các", "ngành", "xét", "tuyển", "hợp", "môn", "nhung", "một", "này",
        "kia", "đó", "với", "của", "và", "cho", "là", "có", "không", "cần", "để",
        "bạn", "tôi", "trường", "đại", "học", "quy", "nhơn", "biết", "bao", "nhiêu",
    }
)


def select_ilike_tokens(query: str, limit: int = 6) -> list[str]:
    """Pick distinctive word tokens for the ILIKE fallback, stripping punctuation."""
    tokens = re.findall(r"\w+", (query or "").lower())
    meaningful = [t for t in tokens if len(t) > 2 and t not in ILIKE_STOP_SYLLABLES]
    return meaningful[:limit] or [t for t in tokens if len(t) > 2][:limit]


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
    ) -> list[dict[str, Any]]:
        """Perform lexical keyword search in PostgreSQL using full-text search with ts_rank and ILIKE fallback."""
        from app.modules.knowledge.models import KnowledgeCollection

        fts_chunks: list[KnowledgeChunk] = []

        # 1. Try PostgreSQL Full-Text Search with ts_rank ranking
        try:
            ts_query = func.plainto_tsquery("simple", query.strip())
            ts_vector = func.to_tsvector("simple", KnowledgeChunk.content)
            rank_expr = func.ts_rank_cd(ts_vector, ts_query)

            stmt = (
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
                stmt = stmt.where(KnowledgeCollection.tenant_id == tenant_id)
            if workspace_id:
                stmt = stmt.where(KnowledgeCollection.workspace_id == workspace_id)
            stmt = stmt.order_by(desc(rank_expr)).limit(top_k)
            res = await db.execute(stmt)
            scalars = res.scalars()
            fts_chunks = list(scalars.all()) if hasattr(scalars, "all") else []
        except Exception as e:
            logger.debug("PostgreSQL FTS ts_rank skipped or unsupported: %s", e)
            fts_chunks = []

        # 2. If FTS yielded candidates, use them; supplement with keyword ILIKE when needed
        seen_ids = {c.id for c in fts_chunks}
        chunks = list(fts_chunks)

        if len(chunks) < top_k:
            meaningful_tokens = select_ilike_tokens(query)

            if meaningful_tokens:
                if not fts_chunks and len(meaningful_tokens) >= 2:
                    from sqlalchemy import and_

                    match_expr = and_(
                        KnowledgeChunk.content.ilike(f"%{meaningful_tokens[0]}%"),
                        KnowledgeChunk.content.ilike(f"%{meaningful_tokens[1]}%"),
                    )
                else:
                    conditions = [KnowledgeChunk.content.ilike(f"%{token}%") for token in meaningful_tokens]
                    match_expr = or_(*conditions)

                stmt_ilike = (
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
                    stmt_ilike = stmt_ilike.where(KnowledgeCollection.tenant_id == tenant_id)
                if workspace_id:
                    stmt_ilike = stmt_ilike.where(KnowledgeCollection.workspace_id == workspace_id)
                stmt_ilike = stmt_ilike.limit(top_k)

                try:
                    res_ilike = await db.execute(stmt_ilike)
                    scalars_ilike = res_ilike.scalars()
                    for c in list(scalars_ilike.all()) if hasattr(scalars_ilike, "all") else []:
                        if c.id not in seen_ids:
                            chunks.append(c)
                            seen_ids.add(c.id)
                            if len(chunks) >= top_k:
                                break
                except Exception as e_ilike:
                    logger.debug("Sparse ILIKE fallback query failed: %s", e_ilike)

        # 3. Unaccented fallback for queries typed without diacritics.
        # Requires the PostgreSQL unaccent extension; skipped gracefully when unavailable.
        if len(chunks) < top_k and is_unaccented_query(query):
            try:
                uni_tokens = select_ilike_tokens(strip_vietnamese_accents(query))[:3]
                if uni_tokens:
                    uni_conds = [
                        func.unaccent(KnowledgeChunk.content).ilike(f"%{token}%")
                        for token in uni_tokens
                    ]
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
                    stmt_uni = stmt_uni.limit(top_k)
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

        results: list[dict[str, Any]] = []
        for idx, c in enumerate(chunks, start=1):
            results.append(
                {
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "content": c.content,
                    "section": c.section,
                    "page_number": c.page_number,
                    "score": 1.0 / idx,
                    "metadata": c.chunk_metadata,
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
        reranked = await reranker_client.rerank(
            query=query,
            candidates=fused,
            top_k=rerank_top_k,
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
