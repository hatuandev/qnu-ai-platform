"""FastAPI Main Application Entrypoint — Production Lifecycle & Health Checks."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response, status

from app.core.config import get_settings
from app.core.database import check_db_health, engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import setup_middlewares
from app.core.redis import check_redis_health

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and graceful shutdown."""
    # Startup
    configure_logging()
    logger.info(
        "Starting QNU.AI Platform Backend",
        environment=settings.ENVIRONMENT,
        service=settings.SERVICE_NAME,
        port=settings.PORT,
    )
    yield
    # Graceful Shutdown
    logger.info("Shutting down QNU.AI Platform Backend...")
    await engine.dispose()
    logger.info("Database connection pool closed.")


def create_app() -> FastAPI:
    """Create and configure the production FastAPI application instance."""
    app = FastAPI(
        title="QNU.AI Platform API",
        description="Nền tảng Điều phối Trợ lý AI & Động cơ RAG Trung gian — Trường Đại học Quy Nhơn",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 1. Setup Middlewares (CORS, Request Timing, Correlation ID)
    setup_middlewares(app)

    # 2. Register Global RFC 7807 Exception Handlers
    register_exception_handlers(app)

    # 3. Root Information Endpoint
    @app.get("/", tags=["General"])
    async def root_info() -> dict[str, Any]:
        return {
            "name": "QNU.AI Platform API",
            "version": "0.1.0",
            "status": "online",
            "environment": settings.ENVIRONMENT,
            "docs_url": "/docs",
            "api_prefix": settings.API_PREFIX,
        }

    # 4. Liveness Probe (Lightweight check for Kubernetes / Docker)
    @app.get("/health/live", tags=["Health"])
    async def health_liveness() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.SERVICE_NAME,
            "version": "0.1.0",
        }

    # 5. Readiness Probe (Checks actual PostgreSQL & Redis connectivity)
    @app.get("/health/ready", tags=["Health"])
    @app.get("/health", tags=["Health"])
    async def health_readiness(response: Response) -> dict[str, Any]:
        db_ok = await check_db_health()
        redis_ok = await check_redis_health()

        degraded: dict[str, str] = {}
        if not db_ok:
            degraded["database"] = "PostgreSQL connection failed"
        if not redis_ok:
            degraded["redis"] = "Redis connection failed"

        if degraded:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            logger.error("Health check degraded", degraded=degraded)
            return {
                "status": "degraded",
                "service": settings.SERVICE_NAME,
                "degraded_services": degraded,
            }

        return {
            "status": "ok",
            "service": settings.SERVICE_NAME,
            "dependencies": {
                "database": "connected",
                "redis": "connected",
            },
        }

    # 6. Mount Feature Modules Routers
    from app.modules.assistants import assistants_router
    from app.modules.evaluation import evaluation_router
    from app.modules.knowledge import knowledge_router
    from app.modules.modelops import modelops_router
    from app.modules.ocr import ocr_router
    from app.modules.rag import rag_router
    from app.modules.tools import tools_router
    from app.modules.workflows import workflow_router

    app.include_router(knowledge_router, prefix=settings.API_PREFIX)
    app.include_router(rag_router, prefix=settings.API_PREFIX)
    app.include_router(modelops_router, prefix=settings.API_PREFIX)
    app.include_router(workflow_router, prefix=settings.API_PREFIX)
    app.include_router(assistants_router, prefix=settings.API_PREFIX)
    app.include_router(tools_router, prefix=settings.API_PREFIX)
    app.include_router(ocr_router, prefix=settings.API_PREFIX)
    app.include_router(evaluation_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
