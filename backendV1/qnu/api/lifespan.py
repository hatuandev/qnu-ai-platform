"""Startup and shutdown of shared resources."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from qnu.api.wiring import build_container, close_container
from qnu.platform.cache import close_redis
from qnu.platform.config import get_settings
from qnu.platform.database import engine
from qnu.platform.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.ENVIRONMENT in ("production", "prod") and settings.DEV_AUTH_ENABLED:
        raise RuntimeError("DEV_AUTH_ENABLED must be false in production.")

    app.state.container = build_container(settings)
    logger.info("backend_v1_started", environment=settings.ENVIRONMENT, port=settings.PORT)
    try:
        yield
    finally:
        await close_container(app.state.container)
        await close_redis()
        await engine.dispose()
        logger.info("backend_v1_stopped")
