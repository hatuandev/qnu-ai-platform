"""Hybrid Retriever — Orchestrating Dense Vector (Qdrant) + Sparse Lexical (PostgreSQL FTS)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.rag.fusion import FusionCandidate, reciprocal_rank_fusion
from app.modules.rag.reranker import reranker_client
from app.modules.rag.vector_indexer import vector_indexer

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Executes multi-stage hybrid retrieval with RRF fusion and reranking."""

    async def search_sparse_fts(
        self,
        db: AsyncSession,
        collection_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Perform lexical keyword search in PostgreSQL using text matching."""
        # Simple tokenized ILIKE match or FTS matching active documents only
        tokens = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]
        if not tokens:
            tokens = [query.strip()]

        conditions = [KnowledgeChunk.content.ilike(f"%{token}%") for token in tokens[:5]]

        stmt = (
            select(KnowledgeChunk)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeChunk.collection_id == collection_id,
                KnowledgeDocument.is_active.is_(True),
                or_(*conditions),
            )
            .limit(top_k)
        )
        try:
            res = await db.execute(stmt)
            scalars = res.scalars()
            chunks = list(scalars.all()) if hasattr(scalars, "all") else []
        except Exception as e:
            logger.debug("Sparse FTS query skipped or failed: %s", e)
            chunks = []

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

    async def retrieve(
        self,
        db: AsyncSession,
        collection_id: str,
        query: str,
        top_k: int = 8,
        rerank_top_k: int = 5,
    ) -> list[FusionCandidate]:
        """Run full Hybrid Retrieval pipeline: Dense + Sparse FTS + RRF + Reranker."""
        # 1. Concurrent Dense & Sparse Search
        dense_hits = await vector_indexer.search_dense(
            collection_id=collection_id,
            query=query,
            top_k=top_k,
        )

        sparse_hits = await self.search_sparse_fts(
            db=db,
            collection_id=collection_id,
            query=query,
            top_k=top_k,
        )

        # 2. Reciprocal Rank Fusion (RRF)
        fused = reciprocal_rank_fusion(
            dense_results=dense_hits,
            sparse_results=sparse_hits,
            k=60,
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
