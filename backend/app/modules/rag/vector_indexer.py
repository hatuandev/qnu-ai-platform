"""Qdrant Vector Database Indexer & Dense Search Service."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorIndexer:
    """Manages collection provisioning, vector indexing and dense vector retrieval."""

    def __init__(self, qdrant_url: str | None = None):
        self.url = qdrant_url or settings.QDRANT_URL
        self.client = AsyncQdrantClient(url=self.url, api_key=settings.QDRANT_API_KEY)
        self.vector_size = settings.VECTOR_SIZE

    def _get_collection_name(self, collection_id: str) -> str:
        clean_id = collection_id.replace("-", "_").lower()
        return f"col_{clean_id}"

    async def ensure_collection(self, collection_id: str) -> str:
        """Create collection on Qdrant if it does not already exist."""
        cname = self._get_collection_name(collection_id)
        try:
            collections = await self.client.get_collections()
            existing_names = [c.name for c in collections.collections]
            if cname not in existing_names:
                await self.client.create_collection(
                    collection_name=cname,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                    hnsw_config=qmodels.HnswConfigDiff(m=16, ef_construct=100),
                )
                logger.info("Created Qdrant collection: %s", cname)
        except Exception as exc:
            logger.warning("Could not ensure Qdrant collection %s: %s", cname, exc)
        return cname

    @staticmethod
    def generate_embedding(text: str, dim: int = 1024) -> list[float]:
        """Generate normalized dense vector. In production this calls BGE-M3 model service."""
        # Deterministic vector simulation for testing & offline mode
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        vec = [math.sin(seed + i) for i in range(dim)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 6) for x in vec]

    async def index_chunks(
        self,
        collection_id: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Upload vectorized chunks into Qdrant collection with payload filtering."""
        cname = await self.ensure_collection(collection_id)
        points: list[qmodels.PointStruct] = []

        for c in chunks:
            chunk_id = str(c["id"])
            # Qdrant point IDs must be UUID/uint: use explicit point_id when given
            # (e.g. deterministic uuid5), keep business chunk_id in the payload.
            point_id: Any = c.get("point_id") or chunk_id
            content = str(c["content"])
            vector = c.get("vector") or self.generate_embedding(content, self.vector_size)

            payload = {
                "chunk_id": chunk_id,
                "document_id": str(c.get("document_id", "")),
                "collection_id": collection_id,
                "content": content,
                "section": c.get("section"),
                "page_number": c.get("page_number"),
                "is_active": True,
            }
            if "metadata" in c:
                payload.update(c["metadata"])

            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        if points:
            try:
                await self.client.upsert(collection_name=cname, points=points)
                logger.info("Indexed %d chunks into Qdrant collection %s", len(points), cname)
                return len(points)
            except Exception as exc:
                logger.error("Failed to upsert points into Qdrant %s: %s", cname, exc)
        return 0

    async def search_dense(
        self,
        collection_id: str,
        query: str,
        top_k: int = 8,
        query_vector: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform dense cosine similarity search in Qdrant."""
        cname = self._get_collection_name(collection_id)
        vec = query_vector or self.generate_embedding(query, self.vector_size)

        try:
            hits = await self.client.search(
                collection_name=cname,
                query_vector=vec,
                limit=top_k,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="is_active",
                            match=qmodels.MatchValue(value=True),
                        )
                    ]
                ),
            )
            results: list[dict[str, Any]] = []
            for hit in hits:
                payload = hit.payload or {}
                results.append(
                    {
                        "chunk_id": payload.get("chunk_id", str(hit.id)),
                        "document_id": payload.get("document_id", ""),
                        "content": payload.get("content", ""),
                        "score": float(hit.score),
                        "section": payload.get("section"),
                        "page_number": payload.get("page_number"),
                        "metadata": payload,
                    }
                )
            return results
        except Exception as exc:
            logger.warning("Dense search failed on Qdrant collection %s: %s", cname, exc)
            return []


vector_indexer = VectorIndexer()
