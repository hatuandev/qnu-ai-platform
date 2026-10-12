"""Cross-process capacity leases; Redis failures never bypass the AI limit."""

import asyncio
import hashlib
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from redis.asyncio import Redis

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def get_redis_client() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)

ACQUIRE = """
local t = redis.call('TIME'); local now = tonumber(t[1]) + tonumber(t[2])/1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[3])
local last = redis.call('ZRANGE', KEYS[1], -1, -1, 'WITHSCORES')
redis.call('EXPIRE', KEYS[1], math.ceil(tonumber(last[2]) - now))
return 1
"""

RENEW = """
if not redis.call('ZSCORE', KEYS[1], ARGV[1]) then return 0 end
local t = redis.call('TIME'); local now = tonumber(t[1]) + tonumber(t[2])/1000000
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[1])
local last = redis.call('ZRANGE', KEYS[1], -1, -1, 'WITHSCORES')
redis.call('EXPIRE', KEYS[1], math.ceil(tonumber(last[2]) - now))
return 1
"""


@asynccontextmanager
async def provider_slot(kind: str, provider_id: str, timeout: float, redis: Redis | None = None) -> AsyncIterator[None]:
    limit = settings.OCR_MAX_CONCURRENT if kind == "ocr" else settings.EMBEDDING_MAX_CONCURRENT
    key = f"qnu:ai-capacity:{kind}:{hashlib.sha256(provider_id.encode()).hexdigest()[:24]}"
    token = uuid.uuid4().hex
    client = redis or get_redis_client()
    acquired = False
    pulse = None
    ttl = max(timeout or 60, 1) + 60
    owner = asyncio.current_task()

    async def renew() -> None:
        try:
            while True:
                await asyncio.sleep(min(15, ttl / 3))
                if not await client.eval(RENEW, 1, key, token, ttl):
                    raise RuntimeError("Provider capacity lease lost")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Provider capacity renewal failed")
            if owner:
                owner.cancel()
    deadline = time.monotonic() + settings.PROVIDER_QUEUE_TIMEOUT_SECONDS
    reported_wait = False
    try:
        while not acquired:
            acquired = bool(await client.eval(ACQUIRE, 1, key, limit, ttl, token))
            if acquired:
                break
            if not reported_wait:
                from app.modules.jobs.ingestion_progress import report_progress

                await report_progress(f"waiting_{kind}", 0)
                reported_wait = True
            if time.monotonic() >= deadline:
                raise AppException("Server AI đang bận; tác vụ sẽ thử lại.", code="PROVIDER_CAPACITY_TIMEOUT", status_code=503)
            await asyncio.sleep(0.5)
        pulse = asyncio.create_task(renew())
        if reported_wait:
            await report_progress("parse" if kind == "ocr" else "embed", 0)
        yield
    except AppException:
        raise
    except Exception as exc:
        # Transport/inference exceptions must retain their original meaning.
        if acquired:
            raise
        raise AppException("Không kiểm tra được giới hạn server AI.", code="PROVIDER_CAPACITY_UNAVAILABLE", status_code=503) from exc
    finally:
        if pulse:
            pulse.cancel()
            with suppress(asyncio.CancelledError):
                await pulse
        if acquired:
            try:
                await client.zrem(key, token)
            except Exception:
                logger.warning("Provider capacity release failed; lease will expire")
        if redis is None:
            await client.aclose()
