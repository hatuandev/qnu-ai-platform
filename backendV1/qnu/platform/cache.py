"""Redis access with an explicit namespace per deployment."""

from __future__ import annotations

from typing import Any

from redis.asyncio import Redis, from_url

from qnu.platform.config import get_settings

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = from_url(get_settings().REDIS_URL, decode_responses=True)
    return _client


def namespaced(key: str) -> str:
    return f"{get_settings().CACHE_NAMESPACE}{key}"


async def ping_redis() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


async def get_json(key: str) -> Any | None:
    raw = await get_redis().get(namespaced(key))
    if raw is None:
        return None
    import json

    return json.loads(raw)


async def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    import json

    await get_redis().set(namespaced(key), json.dumps(value, ensure_ascii=False), ex=ttl_seconds)


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
