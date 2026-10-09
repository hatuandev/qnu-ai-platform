"""Update vector_indexer.py with strict dimension invariance and remove runtime hardcodes."""
from pathlib import Path

path = Path("app/modules/rag/vector_indexer.py")
text = path.read_text(encoding="utf-8")

# 1. Update ensure_collection
target_ensure = '''    async def ensure_collection(self, collection_id: str, vector_size: int | None = None) -> str:
        """Create collection on Qdrant if it does not already exist."""
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
        except Exception as exc:
            logger.warning("Could not ensure Qdrant collection %s: %s", cname, exc)
        return cname'''

repl_ensure = '''    async def ensure_collection(self, collection_id: str, vector_size: int | None = None) -> str:
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
            logger.warning("Could not ensure Qdrant collection %s: %s", cname, exc)
        return cname'''

assert target_ensure in text, "target_ensure not found"
text = text.replace(target_ensure, repl_ensure, 1)

# 2. Update _fit_dim to reject mismatch in production
target_fit = '''    def _fit_dim(self, vec: list[float], target_dim: int | None = None) -> list[float]:
        """Pad/truncate a model vector to the configured Qdrant dimension."""
        dim = target_dim or self.vector_size
        if len(vec) == dim:
            return [round(float(x), 6) for x in vec]
        if len(vec) > dim:
            return [round(float(x), 6) for x in vec[:dim]]
        return [round(float(x), 6) for x in vec] + [0.0] * (dim - len(vec))'''

repl_fit = '''    def _fit_dim(self, vec: list[float], target_dim: int | None = None) -> list[float]:
        """Validate vector dimension; strictly reject truncate/pad in production ingestion."""
        dim = target_dim or self.vector_size
        if len(vec) != dim:
            raise AppException(
                f"Độ dài vector ({len(vec)}) không khớp số chiều quy định ({dim}). Hệ thống từ chối padding/truncate âm thầm.",
                code="VECTOR_DIMENSION_MISMATCH",
                status_code=409,
                details={"actual_dimension": len(vec), "expected_dimension": dim},
            )
        return [round(float(x), 6) for x in vec]'''

assert target_fit in text, "target_fit not found"
text = text.replace(target_fit, repl_fit, 1)

# 3. Clean hardcoded Ollama URL and model name in _embed_texts_ollama
target_ollama_base = '''        raw_base = (
            getattr(runtime, "api_base_url", None)
            or getattr(runtime, "base_url", None)
            or getattr(settings, "OLLAMA_BASE_URL", "")
            or "http://tormemrtxproto.tail0924dd.ts.net:11434"
        ).rstrip("/")
        resolved_base = resolve_ollama_network_url(raw_base).rstrip("/")
        clean_base = resolved_base.removesuffix("/v1")
        model_name = (runtime.model_name or "bge-m3:latest").strip()'''

repl_ollama_base = '''        raw_base = (
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
        model_name = runtime.model_name.strip()'''

assert target_ollama_base in text, "target_ollama_base not found"
text = text.replace(target_ollama_base, repl_ollama_base, 1)

# 4. Update embed_texts signature and calls to pass target_dim
target_embed_sig = '''    async def embed_texts(
        self,
        texts: list[str],
        runtime: ModelRuntimeConfig | None = None,
    ) -> list[list[float]]:'''

repl_embed_sig = '''    async def embed_texts(
        self,
        texts: list[str],
        runtime: ModelRuntimeConfig | None = None,
        target_dim: int | None = None,
    ) -> list[list[float]]:'''

assert target_embed_sig in text, "target_embed_sig not found"
text = text.replace(target_embed_sig, repl_embed_sig, 1)

target_fit_call1 = 'return [self._fit_dim(v) for v in vectors]'
repl_fit_call1 = 'return [self._fit_dim(v, target_dim=target_dim) for v in vectors]'
text = text.replace(target_fit_call1, repl_fit_call1)

# 5. Update index_chunks to receive vector_generation
target_index_chunks = '''    async def index_chunks(
        self,
        collection_id: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Upload vectorized chunks into Qdrant collection with payload filtering."""
        cname = await self.ensure_collection(collection_id)
        points: list[qmodels.PointStruct] = []

        # Reject malformed payloads before making any paid/remote embedding call.
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

        missing = [str(c["content"]) for c in chunks if not c.get("vector")]
        embedding_runtime = (
            await self._resolve_embedding_runtime(collection_id=collection_id)
            if missing
            else None
        )
        encoded = await self.embed_texts(missing, embedding_runtime) if missing else []'''

repl_index_chunks = '''    async def index_chunks(
        self,
        collection_id: str,
        chunks: list[dict[str, Any]],
        vector_generation: Any | None = None,
    ) -> int:
        """Upload vectorized chunks into Qdrant collection with payload filtering."""
        target_size = vector_generation.embedding_dimension if vector_generation else self.vector_size
        cname = await self.ensure_collection(collection_id, vector_size=target_size)
        points: list[qmodels.PointStruct] = []

        # Reject malformed payloads before making any paid/remote embedding call.
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
        )'''

assert target_index_chunks in text, "target_index_chunks not found"
text = text.replace(target_index_chunks, repl_index_chunks, 1)

path.write_text(text, encoding="utf-8")
print("Successfully updated vector_indexer.py")
