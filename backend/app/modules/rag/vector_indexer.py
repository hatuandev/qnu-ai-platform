"""Qdrant Vector Database Indexer & Dense Search Service."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import logging
import math
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)
settings = get_settings()

_embedding_model: Any = None
_embedding_model_failed = False


def is_embedding_model_installed() -> bool:
    """Check sentence-transformers availability without importing torch."""
    return importlib.util.find_spec("sentence_transformers") is not None


def _load_model_sync() -> Any:
    """Load SentenceTransformer with local_files_only preference to avoid remote delays."""
    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer(settings.EMBEDDING_MODEL, local_files_only=True)
    except Exception:
        return SentenceTransformer(settings.EMBEDDING_MODEL)


def _get_embedding_model() -> Any | None:
    """Lazily load the shared BGE-M3 encoder (sync entrypoint for tests/callers)."""
    global _embedding_model, _embedding_model_failed
    if _embedding_model is not None:
        return _embedding_model
    if _embedding_model_failed or not is_embedding_model_installed():
        return None
    try:
        _embedding_model = _load_model_sync()
        logger.info("Loaded embedding model: %s", settings.EMBEDDING_MODEL)
    except Exception as exc:
        _embedding_model_failed = True
        logger.warning("Embedding model unavailable, using mock vectors: %s", exc)
    return _embedding_model


async def _get_embedding_model_async() -> Any | None:
    """Asynchronously load model offloaded to thread so event loop never freezes."""
    global _embedding_model, _embedding_model_failed
    if _embedding_model is not None:
        return _embedding_model
    if _embedding_model_failed or not is_embedding_model_installed():
        return None
    try:
        _embedding_model = await asyncio.to_thread(_load_model_sync)
        logger.info("Loaded embedding model asynchronously: %s", settings.EMBEDDING_MODEL)
    except Exception as exc:
        _embedding_model_failed = True
        logger.warning("Embedding model async load failed, using mock vectors: %s", exc)
    return _embedding_model


class VectorIndexer:
    """Manages collection provisioning, vector indexing and dense vector retrieval."""

    def __init__(self, qdrant_url: str | None = None):
        self.url = qdrant_url or settings.QDRANT_URL
        self.client = AsyncQdrantClient(url=self.url, api_key=settings.QDRANT_API_KEY)
        self.vector_size = settings.VECTOR_SIZE

    def _get_collection_name(self, collection_id: str) -> str:
        clean_id = collection_id.replace("-", "_").lower()
        if clean_id.startswith("col_"):
            return clean_id
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
    def mock_embedding(text: str, dim: int = 1024) -> list[float]:
        """Deterministic vector simulation for testing & offline mode."""
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        vec = [math.sin(seed + i) for i in range(dim)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 6) for x in vec]

    @staticmethod
    def generate_embedding(text: str, dim: int = 1024) -> list[float]:
        """Legacy sync entrypoint: deterministic mock vector (tests/offline)."""
        return VectorIndexer.mock_embedding(text, dim)

    def _fit_dim(self, vec: list[float]) -> list[float]:
        """Pad/truncate a model vector to the configured Qdrant dimension."""
        if len(vec) == self.vector_size:
            return [round(float(x), 6) for x in vec]
        if len(vec) > self.vector_size:
            return [round(float(x), 6) for x in vec[: self.vector_size]]
        return [round(float(x), 6) for x in vec] + [0.0] * (self.vector_size - len(vec))

    async def _embed_texts_cloudflare(self, texts: list[str]) -> list[list[float]]:
        """Batch encode texts using Cloudflare Workers AI @cf/baai/bge-m3."""
        import httpx

        account_id = settings.CLOUDFLARE_ACCOUNT_ID
        token = settings.CLOUDFLARE_API_TOKEN or settings.CLOUDFLARE_API_KEY
        if not account_id or not token:
            raise ValueError("Cloudflare credentials not configured.")

        model = settings.EMBEDDING_MODEL if "@cf/" in settings.EMBEDDING_MODEL else "@cf/baai/bge-m3"
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        all_vectors: list[list[float]] = []
        batch_size = 16
        async with httpx.AsyncClient(timeout=20.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                resp = await client.post(url, headers=headers, json={"text": batch})
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"Cloudflare embedding error (HTTP {resp.status_code}): {resp.text[:200]}"
                    )
                data = resp.json().get("result", {})
                vecs = data.get("data") if isinstance(data, dict) else data
                if not vecs:
                    raise RuntimeError(f"No vector data returned from Cloudflare: {resp.text[:200]}")
                all_vectors.extend([[float(x) for x in v] for v in vecs])

        return all_vectors

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch-encode texts with BGE-M3 (Cloudflare Workers AI preferred, local fallback)."""
        if not texts:
            return []

        # 1. Cloudflare Workers AI Edge Embedding (ultra-fast serverless GPU)
        if (
            getattr(settings, "EMBEDDING_PROVIDER", "").lower() == "cloudflare"
            and (settings.CLOUDFLARE_API_TOKEN or settings.CLOUDFLARE_API_KEY)
            and settings.CLOUDFLARE_ACCOUNT_ID
        ):
            try:
                vectors = await self._embed_texts_cloudflare(texts)
                if len(vectors) == len(texts):
                    return [self._fit_dim(v) for v in vectors]
            except Exception as exc:
                logger.warning(
                    "Cloudflare embedding unavailable (%s), falling back to local model.", exc
                )

        # 2. Local SentenceTransformer BGE-M3 (with timeout & thread offload)
        model = await _get_embedding_model_async()
        if model is None:
            if settings.ENVIRONMENT not in ("test", "testing"):
                raise AppException(
                    "Mô hình embedding (BGE-M3/Cloudflare) không khả dụng. Hệ thống từ chối nạp dữ liệu giả mạo.",
                    code="EMBEDDING_UNAVAILABLE",
                    status_code=503,
                )
            return [self.mock_embedding(t, self.vector_size) for t in texts]
        try:
            # Protect event loop with thread offload and timeout guard (30s)
            vectors = await asyncio.wait_for(
                asyncio.to_thread(
                    model.encode,
                    texts,
                    batch_size=8,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                ),
                timeout=30.0,
            )
            return [self._fit_dim([float(x) for x in row]) for row in vectors]
        except Exception as exc:
            if settings.ENVIRONMENT not in ("test", "testing"):
                logger.error("Embedding inference failed or timed out: %s", exc)
                raise AppException(
                    f"Trích xuất vector embedding thất bại: {exc}",
                    code="EMBEDDING_FAILED",
                    status_code=500,
                )
            logger.warning("Embedding inference failed or timed out, using mock vectors: %s", exc)
            return [self.mock_embedding(t, self.vector_size) for t in texts]

    async def index_chunks(
        self,
        collection_id: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Upload vectorized chunks into Qdrant collection with payload filtering."""
        cname = await self.ensure_collection(collection_id)
        points: list[qmodels.PointStruct] = []

        missing = [str(c["content"]) for c in chunks if not c.get("vector")]
        encoded = await self.embed_texts(missing) if missing else []
        encoded_iter = iter(encoded)

        for c in chunks:
            chunk_id = str(c.get("id") or c.get("chunk_id", ""))
            raw_point_id = c.get("point_id") or chunk_id
            if isinstance(raw_point_id, int):
                point_id: Any = raw_point_id
            else:
                try:
                    uuid.UUID(str(raw_point_id))
                    point_id = str(raw_point_id)
                except (ValueError, TypeError):
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection_id}:{chunk_id}"))
            content = str(c.get("content", ""))
            vector = c.get("vector") or next(encoded_iter)

            tenant_id = c.get("tenant_id")
            workspace_id = c.get("workspace_id")
            document_id = c.get("document_id")
            document_revision = c.get("document_revision")
            document_status = c.get("document_status")
            is_retrievable = c.get("is_retrievable")
            content_hash = c.get("content_hash")
            embedding_model = c.get("embedding_model") or settings.EMBEDDING_MODEL
            payload_schema_version = c.get("payload_schema_version") or "v1"

            missing_fields = []
            if not tenant_id:
                missing_fields.append("tenant_id")
            if not workspace_id:
                missing_fields.append("workspace_id")
            if not collection_id:
                missing_fields.append("collection_id")
            if not document_id:
                missing_fields.append("document_id")
            if document_revision is None:
                missing_fields.append("document_revision")
            if not chunk_id:
                missing_fields.append("chunk_id")
            if not document_status:
                missing_fields.append("document_status")
            if is_retrievable is None:
                missing_fields.append("is_retrievable")
            if not content_hash:
                missing_fields.append("content_hash")

            if missing_fields:
                raise AppException(
                    f"Thiếu các trường metadata bắt buộc cho chunk '{chunk_id}': {', '.join(missing_fields)}.",
                    code="INVALID_POINT_PAYLOAD",
                    status_code=400,
                    details={"chunk_id": chunk_id, "missing_fields": missing_fields},
                )

            payload = {
                "chunk_id": chunk_id,
                "document_id": str(document_id),
                "collection_id": collection_id,
                "tenant_id": str(tenant_id),
                "workspace_id": str(workspace_id),
                "document_revision": int(document_revision),
                "document_status": str(document_status),
                "is_retrievable": bool(is_retrievable),
                "content_hash": str(content_hash),
                "embedding_model": str(embedding_model),
                "payload_schema_version": str(payload_schema_version),
                "content": content,
                "section": c.get("section"),
                "page_number": c.get("page_number"),
                "is_active": bool(c.get("is_active", True)),
            }
            if "metadata" in c and isinstance(c["metadata"], dict):
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

    async def delete_by_document(self, collection_id: str, document_id: str) -> int:
        """Delete all Qdrant points of a document (prevents ghost citations)."""
        cname = self._get_collection_name(collection_id)
        try:
            await self.client.delete(
                collection_name=cname,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            logger.info("Deleted Qdrant points of document %s", document_id)
            return 1
        except Exception as exc:
            logger.warning("Qdrant delete failed for document %s: %s", document_id, exc)
            return 0

    async def delete_collection(self, collection_id: str) -> bool:
        """Delete an entire Qdrant vector collection to prevent ghost vector collections."""
        cname = self._get_collection_name(collection_id)
        try:
            exists = await self.client.collection_exists(cname)
            if exists:
                await self.client.delete_collection(collection_name=cname)
                logger.info("Deleted Qdrant collection %s", cname)
                return True
            return False
        except Exception as exc:
            logger.warning("Qdrant delete collection failed for %s: %s", cname, exc)
            return False

    async def count_points(self, collection_id: str) -> int:
        """Get total point count in collection, returning 0 if collection missing or offline."""
        cname = self._get_collection_name(collection_id)
        try:
            exists = await self.client.collection_exists(cname)
            if not exists:
                return 0
            info = await self.client.get_collection(cname)
            return info.points_count or 0
        except Exception as exc:
            logger.debug("Could not count points for Qdrant collection %s: %s", cname, exc)
            return 0

    async def search_dense(
        self,
        collection_id: str,
        query: str,
        top_k: int = 8,
        query_vector: list[float] | None = None,
        score_threshold: float = 0.35,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform dense cosine similarity search in Qdrant with positive allowlist lifecycle, tenant, and score threshold filtering."""
        cname = self._get_collection_name(collection_id)
        try:
            if query_vector is not None:
                vec = query_vector
            else:
                embedded = await self.embed_texts([query])
                if not embedded:
                    return []
                vec = embedded[0]

            must_conditions: list[Any] = [
                qmodels.FieldCondition(
                    key="is_active",
                    match=qmodels.MatchValue(value=True),
                ),
                qmodels.FieldCondition(
                    key="is_retrievable",
                    match=qmodels.MatchValue(value=True),
                ),
                qmodels.FieldCondition(
                    key="document_status",
                    match=qmodels.MatchAny(any=["ready", "approved"]),
                ),
            ]
            if tenant_id:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="tenant_id",
                        match=qmodels.MatchValue(value=tenant_id),
                    )
                )
            if workspace_id:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="workspace_id",
                        match=qmodels.MatchValue(value=workspace_id),
                    )
                )

            qfilter = qmodels.Filter(must=must_conditions)

            if hasattr(self.client, "query_points"):
                res = await self.client.query_points(
                    collection_name=cname,
                    query=vec,
                    limit=top_k,
                    query_filter=qfilter,
                )
                hits = res.points
            else:
                hits = await self.client.search(
                    collection_name=cname,
                    query_vector=vec,
                    limit=top_k,
                    query_filter=qfilter,
                )
            results: list[dict[str, Any]] = []
            for hit in hits:
                score = float(hit.score)
                if score < score_threshold:
                    continue
                payload = hit.payload or {}
                results.append(
                    {
                        "chunk_id": payload.get("chunk_id", str(hit.id)),
                        "document_id": payload.get("document_id", ""),
                        "content": payload.get("content", ""),
                        "score": score,
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
