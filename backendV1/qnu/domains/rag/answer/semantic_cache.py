"""Semantic Cache tied strictly to (workspace_id, active_index_run_id).

Prevents repetitive LLM calls for semantically equivalent queries during
peak admission seasons, automatically invalidated upon index re-runs.
"""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field

from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform import cache
from qnu.platform.config import get_settings
from qnu.platform.logging import get_logger

logger = get_logger(__name__)

VERSION = "qnu.rag.semantic-cache/v1"

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
) -> str:
    """Generate a cache key bound strictly to (workspace_id, collection_id, index_run_id)."""
    payload = f"{workspace_id}:{collection_id}:{index_run_id}:{normalized_query}"
    return f"sem_cache:{digest(payload)}"


class SemanticCacheEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: str = VERSION
    workspace_id: str
    collection_id: str
    index_run_id: str
    normalized_query: str
    raw_answer: str
    statements: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    reasoning: dict = Field(default_factory=dict)
    saved_tokens: int | None = None


# In-memory fast cache layer for tests or when Redis is absent
_LOCAL_SEMANTIC_CACHE: dict[str, dict] = {}


async def get_semantic_cache(cache_key: str) -> SemanticCacheEntry | None:
    if cache_key in _LOCAL_SEMANTIC_CACHE:
        data = _LOCAL_SEMANTIC_CACHE[cache_key]
        return SemanticCacheEntry.model_validate(data)

    try:
        raw = await cache.get_json(cache_key)
        if raw is not None:
            return SemanticCacheEntry.model_validate(raw)
    except Exception as exc:
        logger.warning("semantic_cache_read_failed", error=str(exc))
    return None


async def store_semantic_cache(
    cache_key: str, entry: SemanticCacheEntry, ttl_seconds: int = 3600
) -> None:
    _LOCAL_SEMANTIC_CACHE[cache_key] = entry.model_dump()
    try:
        await cache.set_json(cache_key, entry.model_dump(), ttl_seconds)
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
    for k, v in _LOCAL_SEMANTIC_CACHE.items():
        if v.get("workspace_id") == workspace_id and (
            index_run_id is None or v.get("index_run_id") == index_run_id
        ):
            to_delete.append(k)
    for k in to_delete:
        del _LOCAL_SEMANTIC_CACHE[k]
        cleared += 1
        try:
            await cache.get_redis().delete(cache.namespaced(k))
        except Exception:
            pass
    return cleared
