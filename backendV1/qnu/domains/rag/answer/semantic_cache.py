"""Semantic Cache tied strictly to (workspace_id, active_index_run_id).

Prevents repetitive LLM calls for semantically equivalent queries during
peak admission seasons, automatically invalidated upon index re-runs.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections import OrderedDict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform import cache
from qnu.platform.config import get_settings
from qnu.platform.logging import get_logger

logger = get_logger(__name__)

VERSION = "qnu.rag.semantic-cache/v2"
LOCAL_CACHE_MAX_ENTRIES = 256

_FILLER_PHRASES = [
    "thầy cô cho em hỏi",
    "thầy cô cho tôi hỏi",
    "dạ cho em hỏi",
    "cho em hỏi",
    "cho tôi hỏi",
    "cho mình hỏi",
    "xin cho hỏi",
    "xin hỏi",
    "làm phiền bạn",
    "vui lòng cho biết",
    "vui lòng cho em hỏi",
    "nhờ bot tư vấn",
    "nhờ ad tư vấn",
    "nhờ tư vấn",
    "giúp em với",
    "giúp mình với",
    "được không ạ",
    "có đúng không ạ",
    "thế ạ",
    "vậy ạ",
    "với ạ",
    "xin chào",
    "chào bạn",
    "chào bot",
    "chào ad",
    "dạ",
    "ạ",
    "nhỉ",
    "hả",
    "nhé",
    "nha",
]

_PUNCTUATION_RE = re.compile(r"(?<!\d)\.|\.(?!\d)|[?!,:;\"'()\[\]{}–—\-]+")


def ttl_seconds() -> int:
    """Get configured TTL for semantic cache (default 3600 seconds = 1 hour)."""
    settings = get_settings()
    if not getattr(settings, "SEMANTIC_CACHE_ENABLED", True):
        return 0
    return getattr(settings, "SEMANTIC_CACHE_TTL_SECONDS", 3600)


def normalize_for_semantic_cache(query: str) -> str:
    """Normalize a natural query into a canonical semantic query representation.

    Strips polite conversational fillers and punctuation while strictly preserving:
    - Condition keywords (ví dụ 'chính quy', 'liên thông', 'ngoại lệ', 'không áp dụng')
    - Years and historical periods ('2024', '2025', '2026')
    - Decimal numbers and scales ('6.0', '7.0', '25.5')
    - Entity codes and identifiers ('0012', '7480201', 'AM-0007').
    """
    normalized = unicodedata.normalize("NFC", query).casefold()
    for phrase in sorted(_FILLER_PHRASES, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
        normalized = re.sub(pattern, " ", normalized, flags=re.IGNORECASE)
    # Convert decimal comma between digits to dot (6,0 -> 6.0)
    normalized = re.sub(r"(?<=\d),(?=\d)", ".", normalized)
    # Strip punctuation except decimal dots
    normalized = _PUNCTUATION_RE.sub(" ", normalized)
    tokens = [t for t in normalized.split() if t]
    return " ".join(tokens)


def semantic_cache_key(
    workspace_id: str,
    collection_id: str,
    index_run_id: str,
    normalized_query: str,
    *,
    collection_ids: list[str] | None = None,
    document_ids: list[str] | None = None,
    metadata_filter: dict[str, Any] | None = None,
    scope_resolution: str | None = None,
    persona: str = "",
    provider_id: str | None = None,
    model_name: str | None = None,
    prompt_version: str | None = None,
    collection_manifests: dict[str, Any] | None = None,
) -> str:
    """Generate a cache key bound strictly to full isolation and generation scope."""
    material: dict[str, Any] = {
        "version": VERSION,
        "workspace_id": workspace_id,
        "collection_id": collection_id,
        "collection_ids": sorted(dict.fromkeys(collection_ids or [collection_id])),
        "index_run_id": index_run_id,
        "normalized_query": normalized_query,
        "document_ids": sorted(dict.fromkeys(document_ids or [])),
        "metadata_filter": metadata_filter or {},
        "scope_resolution": scope_resolution or "",
        "persona": persona or "",
        "provider_id": provider_id or "",
        "model_name": model_name or "",
        "prompt_version": prompt_version or "",
    }
    if collection_manifests:
        material["collection_manifests"] = sorted(collection_manifests.items())
    return f"sem_cache:{digest(material)}"


class SemanticCacheEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: str = VERSION
    workspace_id: str
    collection_id: str
    index_run_id: str
    normalized_query: str
    raw_answer: str
    contract: dict = Field(default_factory=dict)
    statements: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    reasoning: dict = Field(default_factory=dict)
    saved_tokens: int | None = None


# Bounded in-memory LRU+TTL cache layer: key -> (expires_at_monotonic, entry_dict)
_LOCAL_SEMANTIC_CACHE: OrderedDict[str, tuple[float, dict]] = OrderedDict()


def _local_get(cache_key: str) -> dict | None:
    item = _LOCAL_SEMANTIC_CACHE.get(cache_key)
    if item is None:
        return None
    expires_at, data = item
    if time.monotonic() >= expires_at:
        _LOCAL_SEMANTIC_CACHE.pop(cache_key, None)
        return None
    _LOCAL_SEMANTIC_CACHE.move_to_end(cache_key)
    return data


def _local_set(cache_key: str, data: dict, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        _LOCAL_SEMANTIC_CACHE.pop(cache_key, None)
        return
    now = time.monotonic()
    # Evict expired entries opportunistically before enforcing size cap
    expired = [k for k, (exp, _) in _LOCAL_SEMANTIC_CACHE.items() if now >= exp]
    for k in expired:
        _LOCAL_SEMANTIC_CACHE.pop(k, None)
    _LOCAL_SEMANTIC_CACHE[cache_key] = (now + ttl_seconds, data)
    _LOCAL_SEMANTIC_CACHE.move_to_end(cache_key)
    while len(_LOCAL_SEMANTIC_CACHE) > LOCAL_CACHE_MAX_ENTRIES:
        _LOCAL_SEMANTIC_CACHE.popitem(last=False)


async def get_semantic_cache(cache_key: str) -> SemanticCacheEntry | None:
    local_data = _local_get(cache_key)
    if local_data is not None:
        try:
            entry = SemanticCacheEntry.model_validate(local_data)
            if entry.version == VERSION:
                return entry
        except (ValidationError, TypeError):
            pass
        await discard_semantic_cache(cache_key)
        return None

    try:
        raw = await cache.get_json(cache_key)
        if raw is not None:
            try:
                entry = SemanticCacheEntry.model_validate(raw)
            except (ValidationError, TypeError):
                await discard_semantic_cache(cache_key)
                return None
            if entry.version != VERSION:
                await discard_semantic_cache(cache_key)
                return None
            return entry
    except Exception as exc:
        logger.warning("semantic_cache_read_failed", error=str(exc))
    return None


async def store_semantic_cache(
    cache_key: str, entry: SemanticCacheEntry, ttl_seconds: int = 3600
) -> None:
    payload = entry.model_dump()
    _local_set(cache_key, payload, ttl_seconds)
    try:
        await cache.set_json(cache_key, payload, ttl_seconds)
    except Exception as exc:
        logger.warning("semantic_cache_write_failed", error=str(exc))


async def discard_semantic_cache(cache_key: str) -> None:
    """Explicitly delete a single semantic cache key from both local and remote caches."""
    _LOCAL_SEMANTIC_CACHE.pop(cache_key, None)
    try:
        await cache.get_redis().delete(cache.namespaced(cache_key))
    except Exception:
        pass


async def invalidate_semantic_cache(
    workspace_id: str,
    index_run_id: str | None = None,
) -> int:
    """Purge cache entries for a specific index run or workspace."""
    cleared = 0
    to_delete = []
    for k, (_, v) in list(_LOCAL_SEMANTIC_CACHE.items()):
        if v.get("workspace_id") == workspace_id and (
            index_run_id is None or v.get("index_run_id") == index_run_id
        ):
            to_delete.append(k)
    for k in to_delete:
        _LOCAL_SEMANTIC_CACHE.pop(k, None)
        cleared += 1
        try:
            await cache.get_redis().delete(cache.namespaced(k))
        except Exception:
            pass
    return cleared
