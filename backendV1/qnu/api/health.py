"""Liveness, readiness and metrics endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from qnu.platform.cache import ping_redis
from qnu.platform.config import get_settings
from qnu.platform.database import engine
from qnu.platform.metrics import render_metrics

router = APIRouter(tags=["Health"])


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "service": settings.SERVICE_NAME, "version": "0.1.0"}


async def _check_database() -> bool:
    try:
        async with engine.connect() as connection:
            await asyncio.wait_for(connection.execute(text("SELECT 1")), timeout=2.0)
        return True
    except Exception:
        return False


@router.get("/health/ready")
@router.get("/health")
async def health_ready(response: Response) -> dict[str, object]:
    settings = get_settings()
    db_ok, redis_ok = await asyncio.gather(_check_database(), ping_redis())
    degraded: dict[str, str] = {}
    if not db_ok:
        degraded["database"] = "PostgreSQL connection failed"
    if not redis_ok:
        degraded["redis"] = "Redis connection failed"
    if degraded:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "service": settings.SERVICE_NAME, "degraded": degraded}
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "dependencies": {"database": "connected", "redis": "connected"},
    }


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4; charset=utf-8")
