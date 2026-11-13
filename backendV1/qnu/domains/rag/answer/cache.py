"""Exact-answer cache: reuse a stored generation only while every input is unchanged."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform import cache
from qnu.platform.config import get_settings
from qnu.platform.logging import get_logger

logger = get_logger(__name__)

VERSION = "qnu.rag.answer-cache/v1"


class Entry(BaseModel):
    """The provider output and its observed contract; every derived value is rebuilt."""

    model_config = ConfigDict(extra="ignore")
    version: str
    content: str = Field(min_length=1)
    contract: dict = Field(default_factory=dict)
    usage_id: str | None = None
    total_tokens: int | None = None


def ttl_seconds() -> int:
    return get_settings().ANSWER_CACHE_TTL_SECONDS


def key(material: dict[str, Any]) -> str:
    return "answer:" + digest(material)


async def load(cache_key: str) -> Entry | None:
    try:
        raw = await cache.get_json(cache_key)
    except Exception as exc:
        logger.warning("rag_answer_cache_read_failed", error=str(exc))
        return None
    if raw is None:
        return None
    try:
        entry = Entry.model_validate(raw)
    except (ValidationError, TypeError):
        await discard(cache_key)
        return None
    if entry.version != VERSION:
        return None
    return entry


async def store(cache_key: str, entry: Entry, ttl: int) -> None:
    try:
        await cache.set_json(cache_key, entry.model_dump(), ttl)
    except Exception as exc:
        logger.warning("rag_answer_cache_write_failed", error=str(exc))


async def discard(cache_key: str) -> None:
    try:
        await cache.get_redis().delete(cache.namespaced(cache_key))
    except Exception as exc:
        logger.warning("rag_answer_cache_discard_failed", error=str(exc))
