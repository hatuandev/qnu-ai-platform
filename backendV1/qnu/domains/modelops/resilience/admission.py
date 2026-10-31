"""Redis-backed chat admission shared by workers, workspaces and model aliases.

One lease covers a managed request (including credential retries). No DB session
is held here. A cancelled/uncertain call keeps its lease until the bounded TTL;
the server may still be generating after a lost HTTP connection.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from qnu.platform.cache import get_redis, namespaced
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.platform.logging import get_logger
from qnu.ports.chat_model import ChatRequest, ChatResponseError

logger = get_logger(__name__)

ACQUIRE = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + tonumber(t[2]) / 1000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[3])
local last = redis.call('ZRANGE', KEYS[1], -1, -1, 'WITHSCORES')
redis.call('PEXPIRE', KEYS[1], math.ceil(tonumber(last[2]) - now) + 1000)
return 1
"""


def resource_key(endpoint: str, model: str) -> str:
    url = urlsplit(endpoint)
    port = url.port or (443 if url.scheme.lower() == "https" else 80)
    identity = f"{url.scheme.lower()}://{url.hostname}:{port}{url.path.rstrip('/')}\0{model}"
    digest = hashlib.sha256(identity.encode()).hexdigest()
    return namespaced(f"modelops:chat-admission:{digest}")


def _not_dispatched(code: str, detail: str, status: int) -> ChatResponseError:
    # Known zero usage: the provider was never contacted, so release quota safely.
    return ChatResponseError(AppException(detail, code=code, status_code=status), b"", 0)


@asynccontextmanager
async def chat_slot(request: ChatRequest) -> AsyncIterator[None]:
    settings = get_settings()
    try:
        client = get_redis()
    except Exception as exc:
        raise _not_dispatched(
            "chat_admission_unavailable", "Không kiểm tra được giới hạn model.", 503
        ) from exc
    key, token = resource_key(request.endpoint, request.model), uuid.uuid4().hex
    ttl_ms = max(1, int((request.timeout_seconds + 30) * 1000))
    deadline = time.monotonic() + settings.MODEL_CHAT_QUEUE_TIMEOUT_SECONDS
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _not_dispatched(
                "chat_admission_timeout", "Model đang bận; chưa gửi yêu cầu đến provider.", 429
            )
        try:
            async with asyncio.timeout(min(5, remaining)):
                accepted = await client.eval(
                    ACQUIRE, 1, key, settings.MODEL_CHAT_CONCURRENCY, ttl_ms, token
                )
        except Exception as exc:
            raise _not_dispatched(
                "chat_admission_unavailable", "Không kiểm tra được giới hạn model.", 503
            ) from exc
        if accepted:
            break
        remaining = deadline - time.monotonic()
        if remaining > 0:
            await asyncio.sleep(min(0.25, remaining))
    release = True
    try:
        yield
    except BaseException as exc:
        # A definite response/rejection frees a slot. Ambiguous outcomes retain
        # it until expiry, and never cause a duplicate model call here.
        release = isinstance(exc, AppException) and exc.code not in {
            "chat_provider_uncertain", "chat_provider_timeout",
        }
        raise
    finally:
        if release:
            # Token membership is the ownership fence; cannot remove another call.
            try:
                async with asyncio.timeout(5):
                    await asyncio.shield(client.zrem(key, token))
            except Exception:
                # Keep the TTL lease if Redis is unavailable; never lose measured
                # provider output because a capacity-slot cleanup failed.
                logger.warning("chat_admission_release_failed")
