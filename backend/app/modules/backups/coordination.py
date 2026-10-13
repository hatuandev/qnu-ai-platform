"""Cross-process quiescence, independent of Redis; lock lifetime includes SSE/background tasks."""

import asyncio
from contextlib import asynccontextmanager
from functools import wraps

import asyncpg
from arq import Retry
from sqlalchemy.engine import make_url
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException

MAINTENANCE_LOCK = 7261842914051
OPERATION_LOCK = 7261842914052


def postgres_dsn() -> str:
    return (
        make_url(settings.DATABASE_URL)
        .set(drivername="postgresql")
        .render_as_string(hide_password=False)
    )


@asynccontextmanager
async def database_connection(dsn: str | None = None):
    conn = await asyncpg.connect(dsn or postgres_dsn(), timeout=10)
    try:
        yield conn
    finally:
        await conn.close(timeout=5)


@asynccontextmanager
async def shared_access():
    async with database_connection() as conn:
        if not await conn.fetchval("SELECT pg_try_advisory_lock_shared($1)", MAINTENANCE_LOCK):
            raise AppException(
                "Hệ thống đang sao lưu. Vui lòng thử lại sau.",
                code="BACKUP_MAINTENANCE",
                status_code=503,
            )
        yield


@asynccontextmanager
async def exclusive_access():
    async with database_connection() as conn:
        if not await conn.fetchval("SELECT pg_try_advisory_lock($1)", OPERATION_LOCK):
            raise AppException(
                "Một bản sao lưu khác đang chụp dữ liệu.", code="BACKUP_BUSY", status_code=409
            )
        # A queued exclusive lock also prevents starvation from new shared locks.
        await asyncio.wait_for(
            conn.execute("SELECT pg_advisory_lock($1)", MAINTENANCE_LOCK),
            settings.BACKUP_DRAIN_SECONDS,
        )
        yield conn


def guard_worker(function, *, periodic: bool = False):
    @wraps(function)
    async def guarded(*args, **kwargs):
        try:
            async with shared_access():
                return await function(*args, **kwargs)
        except AppException as exc:
            if exc.code != "BACKUP_MAINTENANCE":
                raise
            if periodic:
                return {"skipped": "backup_maintenance"}
            raise Retry(defer=15) from exc

    return guarded


class BackupMaintenanceMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        exempt = (settings.API_PREFIX + "/backups", settings.API_PREFIX + "/auth")
        if (
            scope["type"] != "http"
            or scope.get("method") == "OPTIONS"
            or not path.startswith(settings.API_PREFIX + "/")
            or any(path == prefix or path.startswith(prefix + "/") for prefix in exempt)
        ):
            return await self.app(scope, receive, send)
        # Every API request can indirectly write (e.g. model synchronisation on GET).
        # No process-local flags: multiple API/worker replicas share the PG barrier.
        try:
            async with shared_access():
                await self.app(scope, receive, send)
        except AppException as exc:
            if exc.code != "BACKUP_MAINTENANCE":
                raise
            response = JSONResponse(
                status_code=503,
                headers={"Retry-After": "15"},
                content={
                    "type": "https://errors.qnu.ai/BACKUP_MAINTENANCE",
                    "title": exc.message,
                    "detail": exc.message,
                    "status": 503,
                    "code": exc.code,
                    "instance": path,
                    "correlation_id": scope.get("state", {}).get("correlation_id", "unknown"),
                },
            )
            await response(scope, receive, send)
