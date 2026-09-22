"""FastAPI Main Application Entrypoint — Production Lifecycle & Health Checks."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Response, status

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, check_db_health, engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import setup_middlewares
from app.core.redis import check_redis_health

# Sanitize no_proxy on Windows: httpx crashes when parsing IPv6 '::1'
for _env_var in ("no_proxy", "NO_PROXY"):
    _val = os.environ.get(_env_var)
    if _val:
        _cleaned = [item.strip() for item in _val.split(",") if not item.strip().startswith("::")]
        os.environ[_env_var] = ",".join(_cleaned)

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

    # Verify database schema readiness & storage bucket
    from app.core.storage import storage_service

    await storage_service.ensure_bucket()

    try:
        from sqlalchemy import inspect, text

        async with engine.connect() as conn:
            # 1. Connection check
            await conn.execute(text("SELECT 1"))

            # 2. Schema readiness check (Alembic & Core tables)
            has_alembic = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).has_table("alembic_version")
            )
            tables = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )
            required_tables = {
                "assistants",
                "knowledge_documents",
                "workflow_definitions",
                "model_provider_configs",
            }
            missing = required_tables - tables

            if not has_alembic or missing:
                err_msg = (
                    f"Database schema is not ready. Missing tables: {missing or 'alembic_version'}. "
                    "Run 'python -m app.cli db migrate' to initialize schema."
                )
                if settings.ENVIRONMENT == "production":
                    logger.error(err_msg)
                    raise RuntimeError(err_msg)

                if settings.DEV_AUTO_MIGRATE:
                    logger.info("DEV_AUTO_MIGRATE is enabled. Running migrations...")
                    from app.cli import run_db_migrate
                    run_db_migrate()
                else:
                    logger.warning(err_msg)
            else:
                logger.info("Database schema readiness verified: OK")

        # Optional dev auto-seed (default disabled in production)
        if settings.DEV_AUTO_SEED:
            logger.info("DEV_AUTO_SEED is enabled. Running seed...")
            from app.cli import run_db_seed
            await run_db_seed(seed_all=True)

        # Synchronize active AI model provider credentials into runtime settings
        try:
            from app.modules.modelops.service import modelops_service
            async with AsyncSessionFactory() as session:
                synced = await modelops_service.sync_active_providers_to_runtime(session)
                logger.info("Synchronized %d active model provider credentials into runtime settings", synced)
        except Exception as exc:
            logger.warning("Model provider credentials sync warning: %s", exc)

    except Exception as exc:
        if settings.ENVIRONMENT == "production":
            raise
        logger.warning("Database schema check warning: %s", exc)

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

    # 5.1 Prometheus Metrics Endpoint
    from app.core.observability import metrics_registry

    @app.get("/metrics", tags=["Observability"])
    async def get_metrics(format: str | None = None) -> Response:
        if format == "json":
            import json

            return Response(
                content=json.dumps(metrics_registry.get_summary(), indent=2),
                media_type="application/json",
            )
        return Response(
            content=metrics_registry.export_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # 6. Mount Feature Modules Routers
    from app.modules.assistants import assistant_chat_router, assistants_router
    from app.modules.auth import auth_router
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.conversations.router import router as conversations_router
    from app.modules.document_types.router import router as document_types_router
    from app.modules.evaluation import evaluation_router
    from app.modules.jobs import jobs_router
    from app.modules.knowledge import knowledge_router
    from app.modules.modelops import modelops_router
    from app.modules.node_catalog import node_catalog_router
    from app.modules.ocr import ocr_router
    from app.modules.rag import rag_router
    from app.modules.tools import tools_router
    from app.modules.workflows import workflow_router

    # Public Routes (Auth, Health, and Public Chat Widget)
    app.include_router(auth_router, prefix=settings.API_PREFIX)
    app.include_router(assistant_chat_router, prefix=settings.API_PREFIX)

    # Secured Admin Routes (Protected by Dev Access Gate)
    auth_guard = [Depends(get_current_actor)]
    app.include_router(jobs_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(document_types_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(knowledge_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(rag_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(modelops_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(node_catalog_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(workflow_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(assistants_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(conversations_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(tools_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(ocr_router, prefix=settings.API_PREFIX, dependencies=auth_guard)
    app.include_router(evaluation_router, prefix=settings.API_PREFIX, dependencies=auth_guard)

    return app


app = create_app()
