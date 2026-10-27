"""ARQ adapter bound to the backendV1 queue namespace only."""

from __future__ import annotations

import hashlib
import json

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from qnu.platform.errors import DependencyUnavailable


class ArqJobQueue:
    """Lazy pool: a Redis outage must not prevent the API process from starting."""

    def __init__(self, redis_url: str, queue_name: str) -> None:
        self._redis_url = redis_url
        self._queue_name = queue_name
        self._pool: ArqRedis | None = None

    async def _get_pool(self) -> ArqRedis:
        if self._pool is None:
            self._pool = await create_pool(
                RedisSettings.from_dsn(self._redis_url), default_queue_name=self._queue_name
            )
        return self._pool

    async def enqueue(self, function: str, *args: object, job_id: str | None = None) -> bool:
        try:
            pool = await self._get_pool()
            job = await pool.enqueue_job(
                function, *args, _job_id=job_id, _queue_name=self._queue_name
            )
        except Exception as exc:
            # Drop a broken pool so the next call reconnects instead of reusing it.
            self._pool = None
            raise DependencyUnavailable(
                "Không kết nối được hàng đợi công việc.", code="queue_unavailable"
            ) from exc
        return job is not None

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None

    async def health(self) -> dict:
        from qnu.platform.config import get_settings
        from qnu.platform.schema import SCHEMA_HEAD

        try:
            pool = await self._get_pool()
            connected = bool(await pool.ping())
            prefix = (
                get_settings().CACHE_NAMESPACE
                + "worker:"
                + hashlib.sha256(self._queue_name.encode()).hexdigest()[:16]
                + ":"
            )
            heads = []
            async for key in pool.scan_iter(match=prefix + "*", count=50):
                value = await pool.get(key)
                if value:
                    worker = json.loads(value)
                    if worker.get("code_head") == SCHEMA_HEAD:
                        heads.append(worker.get("schema_head"))
            return {
                "ok": connected,
                "worker_schema_head": SCHEMA_HEAD if SCHEMA_HEAD in heads else None,
            }
        except Exception as exc:
            raise DependencyUnavailable(
                "Không kiểm tra được hàng đợi/worker.", code="queue_unavailable"
            ) from exc
