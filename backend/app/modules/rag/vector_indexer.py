"""Qdrant Vector Database Indexer & Dense Search Service."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory
from app.core.exceptions import AppException
from app.modules.modelops.services.model_runtime_resolver import (
    ModelRuntimeConfig,
    model_runtime_resolver,
)
from app.modules.modelops.services.provider_key_rotation_service import (
    provider_key_rotation_service,
)

logger = logging.getLogger(__name__)
settings = get_settings()

class VectorIndexer:
    """Manages collection provisioning, vector indexing and dense vector retrieval."""

    def __init__(self, qdrant_url: str | None = None):
        self.url = qdrant_url or settings.QDRANT_URL
        self.client = AsyncQdrantClient(url=self.url, api_key=settings.QDRANT_API_KEY or None)
        self.vector_size = settings.VECTOR_SIZE

    def _get_collection_name(self, collection_id: str) -> str:
        clean_id = collection_id.replace("-", "_").lower()
        if clean_id.startswith("col_"):
            return clean_id
        return f"col_{clean_id}"

    async def ensure_collection(self, collection_id: str, vector_size: int | None = None) -> str:
        """Create collection on Qdrant if not exist, or strictly verify dimension compatibility."""
        cname = self._get_collection_name(collection_id)
        target_size = vector_size or self.vector_size
        try:
            collections = await self.client.get_collections()
            existing_names = [c.name for c in collections.collections]
            if cname not in existing_names:
                await self.client.create_collection(
                    collection_name=cname,
                    vectors_config=qmodels.VectorParams(
                        size=target_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                    hnsw_config=qmodels.HnswConfigDiff(m=16, ef_construct=100),
                )
                logger.info("Created Qdrant collection: %s (dim=%d)", cname, target_size)
            else:
                col_info = await self.client.get_collection(cname)
                cfg = getattr(col_info, "config", None)
                params = getattr(cfg, "params", None)
                vectors = getattr(params, "vectors", None)
                existing_size = None
                if isinstance(vectors, qmodels.VectorParams):
                    existing_size = vectors.size
                elif isinstance(vectors, dict):
                    default_v = vectors.get("") or next(iter(vectors.values()), None)
                    existing_size = getattr(default_v, "size", None)
                elif hasattr(vectors, "size"):
                    existing_size = getattr(vectors, "size", None)

                if existing_size is not None and existing_size != target_size:
                    raise AppException(
                        f"Collection '{cname}' trên Qdrant có số chiều vector ({existing_size}) không khớp với cấu hình thế hệ ({target_size}).",
                        code="VECTOR_DIMENSION_MISMATCH",
                        status_code=409,
                        details={"collection_name": cname, "existing_size": existing_size, "target_size": target_size},
                    )
        except AppException:
            raise
        except Exception as exc:
            logger.error("Could not ensure Qdrant collection %s: %s", cname, exc)
            raise AppException(
                f"Không thể kết nối hoặc khởi tạo collection '{cname}' trên Qdrant: {exc}",
                code="QDRANT_UNAVAILABLE",
                status_code=503,
                details={"collection_name": cname, "error": str(exc)},
            ) from exc
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

    def _fit_dim(self, vec: list[float], target_dim: int | None = None) -> list[float]:
        """Validate vector dimension; strictly reject truncate/pad in production ingestion."""
        dim = target_dim or self.vector_size
        if len(vec) != dim:
            raise AppException(
                f"Độ dài vector ({len(vec)}) không khớp số chiều quy định ({dim}). Hệ thống từ chối padding/truncate âm thầm.",
                code="VECTOR_DIMENSION_MISMATCH",
                status_code=409,
                details={"actual_dimension": len(vec), "expected_dimension": dim},
            )
        return [round(float(x), 6) for x in vec]

    async def _resolve_embedding_runtime(
        self,
        *,
        collection_id: str | None = None,
        preferred_provider_id: str | None = None,
        preferred_model_name: str | None = None,
        excluded_key_ids: set[str] | None = None,
        estimated_tokens: int = 0,
    ) -> ModelRuntimeConfig:
        """Load embedding provider and model from Collection metadata or ModelOps."""
        if collection_id and not preferred_model_name:
            try:
                from sqlalchemy import select

                from app.modules.knowledge.models import KnowledgeCollection

                async with AsyncSessionFactory() as db:
                    stmt = select(KnowledgeCollection).where(
                        (KnowledgeCollection.id == collection_id)
                        | (KnowledgeCollection.module_code == collection_id)
                    )
                    res = await db.execute(stmt)
                    col = res.scalar_one_or_none()
                    if col and col.collection_metadata:
                        dp = col.collection_metadata.get("data_processing") or {}
                        if dp.get("embedding_model"):
                            preferred_model_name = dp.get("embedding_model")
                        if dp.get("embedding_provider_id"):
                            preferred_provider_id = dp.get("embedding_provider_id")
            except Exception as exc:
                logger.warning(
                    "Could not load data_processing config for collection %s: %s",
                    collection_id,
                    exc,
                )

        async with AsyncSessionFactory() as db:
            return await model_runtime_resolver.resolve(
                db,
                "embedding",
                preferred_provider_id=preferred_provider_id,
                preferred_model_name=preferred_model_name,
                excluded_key_ids=excluded_key_ids,
                estimated_tokens=estimated_tokens,
            )


    @staticmethod
    async def _finish_runtime_key(
        runtime: ModelRuntimeConfig,
        *,
        total_tokens: int = 0,
        error: Exception | None = None,
    ) -> None:
        lease = runtime.key_lease()
        if lease is None:
            return
        async with AsyncSessionFactory() as db:
            if error is None:
                await provider_key_rotation_service.complete_success(
                    db, lease, total_tokens=total_tokens
                )
            else:
                await provider_key_rotation_service.complete_failure(db, lease, error)

    async def _embed_texts_cloudflare(
        self,
        texts: list[str],
        runtime: ModelRuntimeConfig,
    ) -> list[list[float]]:
        """Batch encode texts using Cloudflare Workers AI @cf/baai/bge-m3."""
        import httpx

        account_id = runtime.account_id
        token = runtime.api_key
        if not account_id or not token:
            raise ValueError("Cloudflare credentials not configured.")

        raw_model = runtime.model_name.strip()
        if raw_model.startswith("@cf/"):
            model = raw_model
        elif "/" in raw_model:
            model = f"@cf/{raw_model}"
        else:
            model = f"@cf/baai/{raw_model}"
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Partition texts dynamically based on item count and character budget.
        # Cloudflare Workers AI limits total request context to 60,000 tokens.
        # Keeping MAX_BATCH_CHARS <= 16,000 and MAX_BATCH_ITEMS <= 6 guarantees safe margins for multilingual/table text.
        MAX_BATCH_CHARS = 16000
        MAX_BATCH_ITEMS = 6

        batches: list[list[str]] = []
        current_batch: list[str] = []
        current_chars = 0

        for t in texts:
            clean_t = t[:16000] if len(t) > 16000 else t
            t_len = len(clean_t)
            if current_batch and (len(current_batch) >= MAX_BATCH_ITEMS or (current_chars + t_len > MAX_BATCH_CHARS)):
                batches.append(current_batch)
                current_batch = [clean_t]
                current_chars = t_len
            else:
                current_batch.append(clean_t)
                current_chars += t_len
        if current_batch:
            batches.append(current_batch)

        all_vectors: list[list[float]] = []

        async with httpx.AsyncClient(timeout=float(runtime.timeout_seconds)) as client:
            async def _send_batch(batch_items: list[str]) -> list[list[float]]:
                resp = await client.post(url, headers=headers, json={"text": batch_items})
                if resp.status_code == 200:
                    data = resp.json().get("result", {})
                    vecs = data.get("data") if isinstance(data, dict) else data
                    if not vecs:
                        raise RuntimeError(f"No vector data returned from Cloudflare: {resp.text[:200]}")
                    return [[float(x) for x in v] for v in vecs]

                err_text = resp.text
                # Adaptive recovery: if batch exceeded context window, recursively split into halves
                if ("Max context reached" in err_text or "3030" in err_text) and len(batch_items) > 1:
                    mid = len(batch_items) // 2
                    logger.warning(
                        "Cloudflare embedding context exceeded for batch (%d chunks). Splitting batch...",
                        len(batch_items),
                    )
                    left = await _send_batch(batch_items[:mid])
                    right = await _send_batch(batch_items[mid:])
                    return left + right

                # If single oversized chunk exceeded context window, truncate and retry once
                if ("Max context reached" in err_text or "3030" in err_text) and len(batch_items) == 1:
                    logger.warning("Single chunk exceeded Cloudflare context window. Truncating to 6,000 chars...")
                    truncated = [batch_items[0][:6000]]
                    trunc_resp = await client.post(url, headers=headers, json={"text": truncated})
                    if trunc_resp.status_code == 200:
                        trunc_data = trunc_resp.json().get("result", {})
                        trunc_vecs = trunc_data.get("data") if isinstance(trunc_data, dict) else trunc_data
                        if trunc_vecs:
                            return [[float(x) for x in v] for v in trunc_vecs]

                raise RuntimeError(
                    f"Cloudflare embedding error (HTTP {resp.status_code}): {err_text[:250]}"
                )

            for batch in batches:
                batch_vecs = await _send_batch(batch)
                all_vectors.extend(batch_vecs)

        return all_vectors

    async def _embed_texts_ollama(
        self,
        texts: list[str],
        runtime: ModelRuntimeConfig,
    ) -> list[list[float]]:
        """Batch encode texts using Ollama API (/api/embed or /v1/embeddings)."""
        import httpx

        from app.core.config import resolve_ollama_network_url

        raw_base = (
            getattr(runtime, "api_base_url", None)
            or getattr(runtime, "base_url", None)
            or getattr(settings, "OLLAMA_BASE_URL", "")
        )
        if not raw_base:
            raise AppException(
                f"Chưa cấu hình API endpoint cho embedding provider '{runtime.provider_id}'.",
                code="PROVIDER_ENDPOINT_NOT_CONFIGURED",
                status_code=503,
            )
        resolved_base = resolve_ollama_network_url(raw_base).rstrip("/")
        clean_base = resolved_base.removesuffix("/v1")
        if not runtime.model_name or not runtime.model_name.strip():
            raise AppException(
                f"Chưa cấu hình model_name cho embedding provider '{runtime.provider_id}'.",
                code="EMBEDDING_MODEL_NOT_CONFIGURED",
                status_code=503,
            )
        model_name = runtime.model_name.strip()

        batch_size = 16
        all_vectors: list[list[float]] = []

        async with httpx.AsyncClient(timeout=float(runtime.timeout_seconds or 60.0), trust_env=False) as client:
            for i in range(0, len(texts), batch_size):
                chunk_texts = texts[i : i + batch_size]
                # 1. Try native Ollama /api/embed endpoint (only for Ollama providers)
                if runtime.provider_type in ("ollama", "ollama_local", "local"):
                    try:
                        resp = await client.post(
                            f"{clean_base}/api/embed",
                            json={"model": model_name, "input": chunk_texts},
                        )
                        if resp.status_code == 200:
                            embeddings = resp.json().get("embeddings", [])
                            if embeddings:
                                all_vectors.extend([[float(x) for x in v] for v in embeddings])
                                continue
                    except Exception as exc:
                        logger.debug("Ollama /api/embed attempt failed: %s", exc)

                # 2. Native vLLM / OpenAI-compatible /v1/embeddings
                headers = {"Content-Type": "application/json"}
                if runtime.api_key and runtime.api_key.strip() and runtime.api_key.lower() not in ("none", "null"):
                    headers["Authorization"] = f"Bearer {runtime.api_key}"

                resp = await client.post(
                    f"{clean_base}/v1/embeddings",
                    headers=headers,
                    json={"model": model_name, "input": chunk_texts},
                )
                resp.raise_for_status()
                raw_json = resp.json()
                data = await raw_json if asyncio.iscoroutine(raw_json) else raw_json
                items = data.get("data", [])
                items.sort(key=lambda x: x.get("index", 0))
                all_vectors.extend([[float(x) for x in item["embedding"]] for item in items])

        return all_vectors

    async def embed_texts(
        self,
        texts: list[str],
        runtime: ModelRuntimeConfig | None = None,
        target_dim: int | None = None,
    ) -> list[list[float]]:
        """Batch-encode texts with the explicitly configured embedding provider."""
        if not texts:
            return []

        estimated_tokens = max(1, sum(len(text) for text in texts) // 4)
        runtime = runtime or await self._resolve_embedding_runtime(
            estimated_tokens=estimated_tokens
        )
        provider = runtime.provider_type
        if provider in ("ollama", "ollama_local", "local", "vllm", "custom", "openai", "tei"):
            try:
                vectors = await self._embed_texts_ollama(texts, runtime)
                if len(vectors) != len(texts):
                    raise RuntimeError(
                        f"Embedding provider '{provider}' returned {len(vectors)} vectors for {len(texts)} texts."
                    )
                await self._finish_runtime_key(
                    runtime, total_tokens=estimated_tokens
                )
                return [self._fit_dim(v, target_dim=target_dim) for v in vectors]
            except Exception as exc:
                await self._finish_runtime_key(runtime, error=exc)
                logger.error("Embedding provider '%s' unavailable: %s", provider, exc)
                raise AppException(
                    f"Embedding provider '{provider}' không khả dụng: {exc}",
                    code="EMBEDDING_PROVIDER_UNAVAILABLE",
                    status_code=503,
                    details={"provider": provider},
                ) from exc

        if provider == "cloudflare":
            excluded: set[str] = set()
            while True:
                if not runtime.api_key or not runtime.account_id:
                    raise AppException(
                        "Provider Cloudflare thiếu Account ID hoặc API token.",
                        code="EMBEDDING_PROVIDER_NOT_CONFIGURED",
                        status_code=503,
                        details={
                            "provider_id": runtime.provider_id,
                            "required_fields": ["account_id", "api_key"],
                        },
                    )
                try:
                    vectors = await self._embed_texts_cloudflare(texts, runtime)
                    if len(vectors) != len(texts):
                        raise RuntimeError(
                            f"Cloudflare returned {len(vectors)} vectors for {len(texts)} texts."
                        )
                    await self._finish_runtime_key(
                        runtime, total_tokens=estimated_tokens
                    )
                    return [self._fit_dim(v, target_dim=target_dim) for v in vectors]
                except asyncio.CancelledError:
                    if runtime.key_lease() is not None:
                        async with AsyncSessionFactory() as db:
                            await provider_key_rotation_service.release(db, runtime.key_lease())
                    raise
                except Exception as exc:
                    await self._finish_runtime_key(runtime, error=exc)
                    if runtime.key_id:
                        excluded.add(runtime.key_id)
                        try:
                            runtime = await self._resolve_embedding_runtime(
                                excluded_key_ids=excluded,
                                estimated_tokens=estimated_tokens,
                            )
                            continue
                        except AppException:
                            pass
                    logger.error("Cloudflare embedding unavailable: %s", exc)
                    raise AppException(
                        f"Cloudflare Workers AI không khả dụng: {exc}",
                        code="EMBEDDING_PROVIDER_UNAVAILABLE",
                        status_code=503,
                        details={"provider": provider},
                    ) from exc

        raise AppException(
            f"Nhà cung cấp embedding API không được hỗ trợ: {runtime.provider_type}",
            code="EMBEDDING_PROVIDER_UNSUPPORTED",
            status_code=503,
            details={"provider": runtime.provider_id},
        )
    async def index_chunks(
        self,
        collection_id: str,
        chunks: list[dict[str, Any]],
        vector_generation: Any | None = None,
    ) -> int:
        """Upload vectorized chunks into Qdrant collection with payload filtering."""
        target_size = vector_generation.embedding_dimension if vector_generation else self.vector_size

        # Reject malformed payloads before making any paid/remote embedding or network call.
        for chunk in chunks:
            chunk_id = str(chunk.get("id") or chunk.get("chunk_id", ""))
            required_values = {
                "tenant_id": chunk.get("tenant_id"),
                "workspace_id": chunk.get("workspace_id"),
                "collection_id": collection_id,
                "document_id": chunk.get("document_id"),
                "document_revision": chunk.get("document_revision"),
                "chunk_id": chunk_id,
                "document_status": chunk.get("document_status"),
                "is_retrievable": chunk.get("is_retrievable"),
                "content_hash": chunk.get("content_hash"),
            }
            missing_fields = [
                field
                for field, value in required_values.items()
                if value is None or value == ""
            ]
            if missing_fields:
                raise AppException(
                    f"Thiếu các trường metadata bắt buộc cho chunk '{chunk_id}': "
                    f"{', '.join(missing_fields)}.",
                    code="INVALID_POINT_PAYLOAD",
                    status_code=400,
                    details={"chunk_id": chunk_id, "missing_fields": missing_fields},
                )

        cname = await self.ensure_collection(collection_id, vector_size=target_size)
        points: list[qmodels.PointStruct] = []

        missing = [str(c["content"]) for c in chunks if not c.get("vector")]
        pref_provider = vector_generation.provider_id if vector_generation else None
        pref_model = vector_generation.embedding_model if vector_generation else None
        embedding_runtime = (
            await self._resolve_embedding_runtime(
                collection_id=collection_id,
                preferred_provider_id=pref_provider,
                preferred_model_name=pref_model,
            )
            if missing
            else None
        )
        encoded = (
            await self.embed_texts(missing, embedding_runtime, target_dim=target_size)
            if missing
            else []
        )
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
            raw_vector = c.get("vector") or next(encoded_iter)
            vector = self._fit_dim(raw_vector, target_dim=target_size)

            tenant_id = c.get("tenant_id")
            workspace_id = c.get("workspace_id")
            document_id = c.get("document_id")
            document_revision = c.get("document_revision")
            document_status = c.get("document_status")
            is_retrievable = c.get("is_retrievable")
            content_hash = c.get("content_hash")
            embedding_model = (
                c.get("embedding_model")
                if c.get("vector")
                else embedding_runtime.model_name if embedding_runtime else None
            )
            payload_schema_version = c.get("payload_schema_version") or "v1"

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
            if c.get("binding_id"):
                payload["binding_id"] = str(c["binding_id"])
            if c.get("index_revision_id"):
                payload["index_revision_id"] = str(c["index_revision_id"])

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
            except AppException:
                raise
            except Exception as exc:
                logger.error("Failed to upsert points into Qdrant %s: %s", cname, exc)
                raise AppException(
                    f"Ghi điểm vector vào Qdrant collection '{cname}' thất bại: {exc}",
                    code="QDRANT_UPSERT_FAILED",
                    status_code=500,
                    details={"collection_name": cname, "points_count": len(points), "error": str(exc)},
                ) from exc
        return 0

    async def delete_by_document(self, collection_id: str, document_id: str) -> int:
        """Delete all Qdrant points of a document (prevents ghost citations and duplicate vectors)."""
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

    async def verify_revision_parity(
        self,
        collection_id: str,
        document_id: str,
        target_revision: int,
        expected_count: int,
    ) -> tuple[bool, str]:
        """Verify that indexed points count and revision metadata in Qdrant match PostgreSQL chunks exactly before activation."""
        cname = self._get_collection_name(collection_id)
        try:
            exists = await self.client.collection_exists(cname)
            if not exists:
                return False, f"Bộ sưu tập Qdrant '{cname}' không tồn tại."

            parity_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=str(document_id)),
                    ),
                    qmodels.FieldCondition(
                        key="document_revision",
                        match=qmodels.MatchValue(value=int(target_revision)),
                    ),
                ]
            )

            count_res = await self.client.count(
                collection_name=cname,
                count_filter=parity_filter,
                exact=True,
            )
            actual_count = count_res.count

            if actual_count != expected_count:
                reason = (
                    f"Lệch số lượng point Qdrant: tìm thấy {actual_count} points, "
                    f"kỳ vọng {expected_count} chunks (document_id='{document_id}', revision={target_revision})."
                )
                logger.warning(reason)
                return False, reason

            logger.info(
                "Revision parity verified: %d/%d points match for document %s (rev %d) in collection %s",
                actual_count,
                expected_count,
                document_id,
                target_revision,
                cname,
            )
            return True, f"Parity verified: {actual_count}/{expected_count} points match."
        except Exception as exc:
            reason = f"Lỗi kiểm tra tính toàn vẹn revision Qdrant ({cname}): {exc}"
            logger.error(reason)
            return False, reason

    async def verify_index_revision_parity(
        self,
        collection_id: str,
        index_revision_id: str,
        expected_points: dict[str, str],
    ) -> tuple[bool, str, int]:
        """Verify exact point IDs, revision scope and content hashes for one index artifact."""
        cname = self._get_collection_name(collection_id)
        expected_count = len(expected_points)
        try:
            exists = await self.client.collection_exists(cname)
            if not exists:
                return False, f"Bộ sưu tập Qdrant '{cname}' không tồn tại.", 0

            revision_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="index_revision_id",
                        match=qmodels.MatchValue(value=index_revision_id),
                    )
                ]
            )
            count_res = await self.client.count(
                collection_name=cname,
                count_filter=revision_filter,
                exact=True,
            )
            actual_count = int(count_res.count or 0)
            if actual_count != expected_count:
                return (
                    False,
                    f"Qdrant có {actual_count} points, PostgreSQL kỳ vọng {expected_count}.",
                    actual_count,
                )

            points = await self.client.retrieve(
                collection_name=cname,
                ids=list(expected_points),
                with_payload=True,
                with_vectors=False,
            )
            actual_ids = {str(point.id) for point in points}
            missing_ids = set(expected_points) - actual_ids
            if missing_ids:
                return False, f"Thiếu {len(missing_ids)} point IDs trong Qdrant.", actual_count

            for point in points:
                payload = point.payload or {}
                point_id = str(point.id)
                if payload.get("index_revision_id") != index_revision_id:
                    return False, f"Point {point_id} sai index_revision_id.", actual_count
                if payload.get("content_hash") != expected_points[point_id]:
                    return False, f"Point {point_id} sai content_hash.", actual_count
            return True, "Đối chiếu point ID, revision và content hash thành công.", actual_count
        except Exception as exc:
            logger.error("Strict parity verification failed for %s: %s", index_revision_id, exc)
            return False, f"Không thể xác minh parity Qdrant: {exc}", 0

    async def activate_index_revision(
        self,
        collection_id: str,
        index_revision_id: str,
        expected_count: int,
    ) -> int:
        """Make exactly one immutable index artifact retrievable and verify the affected count."""
        cname = self._get_collection_name(collection_id)
        revision_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="index_revision_id",
                    match=qmodels.MatchValue(value=index_revision_id),
                )
            ]
        )
        try:
            await self.client.set_payload(
                collection_name=cname,
                payload={"is_retrievable": True, "document_status": "ready"},
                points=revision_filter,
            )
            count_res = await self.client.count(
                collection_name=cname,
                count_filter=revision_filter,
                exact=True,
            )
            activated_count = int(count_res.count or 0)
            if activated_count != expected_count:
                raise AppException(
                    f"Kích hoạt Qdrant không đủ points ({activated_count}/{expected_count}).",
                    code="REVISION_ACTIVATION_PARITY_MISMATCH",
                    status_code=409,
                )
            return activated_count
        except AppException:
            raise
        except Exception as exc:
            raise AppException(
                f"Kích hoạt index revision trong Qdrant thất bại: {exc}",
                code="REVISION_ACTIVATION_FAILED",
                status_code=503,
            ) from exc

    async def deactivate_index_revision(
        self,
        collection_id: str,
        index_revision_id: str,
    ) -> None:
        """Close an old artifact after the PostgreSQL pointer has moved."""
        revision_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="index_revision_id",
                    match=qmodels.MatchValue(value=index_revision_id),
                )
            ]
        )
        try:
            await self.client.set_payload(
                collection_name=self._get_collection_name(collection_id),
                payload={"is_retrievable": False, "document_status": "archived"},
                points=revision_filter,
            )
        except Exception as exc:
            logger.warning("Could not deactivate old index revision %s: %s", index_revision_id, exc)

    async def activate_document_revision(
        self,
        collection_id: str,
        document_id: str,
        target_revision: int,
    ) -> int:
        """Atomically activate document revision by setting is_retrievable=True and document_status='ready'."""
        cname = self._get_collection_name(collection_id)
        try:
            activation_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=str(document_id)),
                    ),
                    qmodels.FieldCondition(
                        key="document_revision",
                        match=qmodels.MatchValue(value=int(target_revision)),
                    ),
                ]
            )

            await self.client.set_payload(
                collection_name=cname,
                payload={
                    "is_retrievable": True,
                    "document_status": "ready",
                },
                points=activation_filter,
            )
            logger.info(
                "Activated revision %d for document %s in Qdrant collection %s",
                target_revision,
                document_id,
                cname,
            )
            count_res = await self.client.count(
                collection_name=cname,
                count_filter=activation_filter,
                exact=True,
            )
            return count_res.count
        except Exception as exc:
            logger.error(
                "Failed to activate revision %d for document %s in %s: %s",
                target_revision,
                document_id,
                cname,
                exc,
            )
            raise AppException(
                f"Kích hoạt revision {target_revision} trong Qdrant thất bại: {exc}",
                code="REVISION_ACTIVATION_FAILED",
                status_code=500,
            )

    async def purge_stale_revisions(
        self,
        collection_id: str,
        document_id: str,
        current_revision: int,
    ) -> int:
        """Safely purge older revision points of a document (strictly < current_revision) to prevent ghost chunks."""
        cname = self._get_collection_name(collection_id)
        try:
            stale_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=str(document_id)),
                    ),
                    qmodels.FieldCondition(
                        key="document_revision",
                        range=qmodels.Range(lt=int(current_revision)),
                    ),
                ]
            )

            count_res = await self.client.count(
                collection_name=cname,
                count_filter=stale_filter,
                exact=True,
            )
            stale_count = count_res.count

            if stale_count > 0:
                await self.client.delete(
                    collection_name=cname,
                    points_selector=qmodels.FilterSelector(filter=stale_filter),
                )
                logger.info(
                    "Purged %d stale Qdrant points of document %s (older than revision %d) in collection %s",
                    stale_count,
                    document_id,
                    current_revision,
                    cname,
                )
            return stale_count
        except Exception as exc:
            logger.warning(
                "Failed to purge stale revisions for document %s in %s: %s",
                document_id,
                cname,
                exc,
            )
            return 0

    async def count_points_by_document(
        self,
        collection_id: str,
        document_id: str,
    ) -> int:
        """Count exact points belonging to a document in Qdrant."""
        cname = self._get_collection_name(collection_id)
        try:
            doc_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )
                ]
            )
            count_res = await self.client.count(
                collection_name=cname,
                count_filter=doc_filter,
                exact=True,
            )
            return count_res.count
        except Exception as exc:
            raise AppException(
                f"Không thể đếm Qdrant points của document '{document_id}': {exc}",
                code="QDRANT_AUDIT_UNAVAILABLE",
                status_code=503,
            ) from exc

    async def delete_points_by_index_revision(
        self,
        collection_id: str,
        index_revision_id: str,
    ) -> int:
        """Safely delete all Qdrant vector points associated with a specific index_revision_id."""
        cname = self._get_collection_name(collection_id)
        try:
            rev_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="index_revision_id",
                        match=qmodels.MatchValue(value=str(index_revision_id)),
                    ),
                ]
            )

            count_res = await self.client.count(
                collection_name=cname,
                count_filter=rev_filter,
                exact=True,
            )
            count = count_res.count

            if count > 0:
                await self.client.delete(
                    collection_name=cname,
                    points_selector=qmodels.FilterSelector(filter=rev_filter),
                )
                logger.info(
                    "Deleted %d Qdrant points for index_revision %s in collection %s",
                    count,
                    index_revision_id,
                    cname,
                )
            return count
        except Exception as exc:
            logger.error(
                "Failed to delete points for index_revision %s in %s: %s",
                index_revision_id,
                cname,
                exc,
            )
            raise AppException(
                f"Không thể xóa points của index revision '{index_revision_id}': {exc}",
                code="QDRANT_GC_DELETE_FAILED",
                status_code=503,
            ) from exc


    async def search_dense(
        self,
        collection_id: str,
        query: str,
        top_k: int = 8,
        query_vector: list[float] | None = None,
        score_threshold: float = 0.35,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        snapshot: Any | None = None,
    ) -> list[dict[str, Any]]:
        """Perform dense cosine similarity search in Qdrant with positive allowlist lifecycle, tenant, score threshold and snapshot isolation filtering."""
        cname = self._get_collection_name(collection_id)
        try:
            if snapshot is not None and not getattr(snapshot, "binding_revisions", None):
                return []
            if query_vector is not None:
                vec = query_vector
            else:
                embedding_runtime = await self._resolve_embedding_runtime(collection_id=collection_id)
                embedded = await self.embed_texts([query], runtime=embedding_runtime)
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

            if snapshot and getattr(snapshot, "binding_revisions", None):
                revision_pairs = [
                    qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="binding_id",
                                match=qmodels.MatchValue(value=binding_id),
                            ),
                            qmodels.FieldCondition(
                                key="index_revision_id",
                                match=qmodels.MatchValue(value=revision_id),
                            ),
                        ]
                    )
                    for binding_id, revision_id in snapshot.binding_revisions.items()
                ]
                must_conditions.append(qmodels.Filter(should=revision_pairs))

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
                if (
                    payload.get("is_active") is not True
                    or payload.get("is_retrievable") is not True
                    or payload.get("document_status") not in ("ready", "approved")
                ):
                    logger.warning("Qdrant returned a point outside the lifecycle allowlist: %s", hit.id)
                    continue
                point_binding = payload.get("binding_id")
                point_rev = payload.get("index_revision_id")
                if snapshot is not None:
                    expected_revision = snapshot.binding_revisions.get(point_binding)
                    if expected_revision is None or point_rev != expected_revision:
                        logger.warning(
                            "Qdrant returned a point outside retrieval snapshot %s: binding=%s revision=%s",
                            snapshot.snapshot_id,
                            point_binding,
                            point_rev,
                        )
                        continue

                results.append(
                    {
                        "chunk_id": payload.get("chunk_id", str(hit.id)),
                        "document_id": payload.get("document_id", ""),
                        "content": payload.get("content", ""),
                        "score": score,
                        "section": payload.get("section"),
                        "page_number": payload.get("page_number"),
                        "metadata": payload,
                        "binding_id": point_binding,
                        "index_revision_id": point_rev,
                        "document_revision": payload.get("document_revision"),
                    }
                )
            return results
        except Exception as exc:
            logger.warning("Dense search failed on Qdrant collection %s: %s", cname, exc)
            return []


vector_indexer = VectorIndexer()
