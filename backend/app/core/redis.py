"""Redis Connection & Caching Utilities."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global Redis client connection pool
_redis_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


def get_redis_client() -> aioredis.Redis:
    """Get an asynchronous Redis client instance."""
    return aioredis.Redis(connection_pool=get_redis_pool())


async def check_redis_health() -> bool:
    """Readiness probe function for Redis connection."""
    try:
        client = get_redis_client()
        res = await client.ping()
        return bool(res)
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        return False


class SemanticCache:
    """Semantic & Exact Caching Layer for RAG answers to minimize LLM inference latency and cost."""

    def __init__(self, client: aioredis.Redis | None = None, ttl_seconds: int = 86400):
        self.client = client or get_redis_client()
        self.ttl = ttl_seconds

    def _make_key(
        self,
        collection_id: str,
        query: str,
        preferred_model: str = "default",
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        policy_version: str = "v1",
        history_hash: str | None = None,
    ) -> str:
        h = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        model_part = preferred_model.replace(":", "_").replace("/", "_") if preferred_model else "default"
        hist_part = history_hash or "nohist"
        return (
            f"rag:cache:{tenant_id}:{workspace_id}:{collection_id}:"
            f"{model_part}:{policy_version}:{h}:{hist_part}"
        )

    @staticmethod
    def hash_history(history: list[dict[str, Any]] | None) -> str | None:
        """Hash normalized recent turns so short follow-ups with different context never collide."""
        if not history:
            return None
        parts: list[str] = []
        for msg in history[-4:]:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "")).strip().lower()
            content = str(msg.get("content", "")).strip().lower()
            if role in ("user", "assistant") and content:
                parts.append(f"{role}:{content[:300]}")
        if not parts:
            return None
        return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]

    async def get(
        self,
        collection_id: str,
        query: str,
        preferred_model: str = "default",
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        policy_version: str = "v1",
        history_hash: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            key = self._make_key(
                collection_id,
                query,
                preferred_model,
                tenant_id,
                workspace_id,
                policy_version,
                history_hash,
            )
            val = await self.client.get(key)
            if val:
                return json.loads(val)
        except Exception as exc:
            logger.warning("Failed to read from SemanticCache: %s", exc)
        return None

    async def set(
        self,
        collection_id: str,
        query: str,
        data: dict[str, Any],
        preferred_model: str = "default",
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
        policy_version: str = "v1",
        history_hash: str | None = None,
    ) -> None:
        try:
            key = self._make_key(
                collection_id,
                query,
                preferred_model,
                tenant_id,
                workspace_id,
                policy_version,
                history_hash,
            )
            await self.client.setex(key, self.ttl, json.dumps(data, ensure_ascii=False))
        except Exception as exc:
            logger.warning("Failed to write to SemanticCache: %s", exc)

    async def invalidate_collection(self, collection_id: str) -> None:
        """Invalidate all cached queries for a modified collection across all tenants and workspaces."""
        try:
            pattern_v1 = f"rag:cache:*:*:{collection_id}:*"
            pattern_legacy = f"rag:cache:*:{collection_id}:*"
            keys_v1 = await self.client.keys(pattern_v1)
            keys_legacy = await self.client.keys(pattern_legacy)
            all_keys = list(set(keys_v1 + keys_legacy))
            if all_keys:
                await self.client.delete(*all_keys)
                logger.info("Invalidated %d cache keys for collection %s", len(all_keys), collection_id)
        except Exception as exc:
            logger.warning("Failed to invalidate cache for collection %s: %s", collection_id, exc)

    async def clear(self) -> None:
        """Clear all RAG semantic cache entries."""
        try:
            keys = await self.client.keys("rag:cache:*")
            if keys:
                await self.client.delete(*keys)
                logger.info("Cleared %d RAG cache keys", len(keys))
        except Exception as exc:
            logger.warning("Failed to clear SemanticCache: %s", exc)


semantic_cache = SemanticCache()
