"""FastAPI Main Application Entrypoint — Production Lifecycle & Health Checks."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import check_db_health, engine
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

    # Automatically ensure PostgreSQL schema exists on startup
    try:
        import app.modules.assistants.models
        import app.modules.document_types.models
        import app.modules.evaluation.models
        import app.modules.knowledge.models
        import app.modules.modelops.models
        import app.modules.node_catalog.models
        import app.modules.ocr.models
        import app.modules.tools.models
        import app.modules.workflows.models  # noqa: F401
        from app.core.database import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text(
                    "ALTER TABLE IF EXISTS knowledge_documents "
                    "ADD COLUMN IF NOT EXISTS document_type_code VARCHAR(64)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_knowledge_documents_document_type_code "
                    "ON knowledge_documents (document_type_code)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE IF EXISTS workflow_definitions "
                    "ADD COLUMN IF NOT EXISTS published_version_id VARCHAR(36)"
                )
            )
            for column_definition in (
                "workflow_version_id VARCHAR(36)",
                "assistant_id VARCHAR(36)",
                "assistant_revision VARCHAR(64)",
                "correlation_id VARCHAR(128)",
                "runtime_profile JSONB",
            ):
                await conn.execute(
                    text(
                        "ALTER TABLE IF EXISTS workflow_executions "
                        f"ADD COLUMN IF NOT EXISTS {column_definition}"
                    )
                )
        from app.core.database import AsyncSessionFactory
        from app.modules.assistants.seeder import seed_standard_assistants
        from app.modules.document_types.service import document_types_service
        from app.modules.knowledge.service import knowledge_service
        from app.modules.modelops.service import modelops_service

        async with AsyncSessionFactory() as db:
            await document_types_service.sync_from_catalog(db)
            await seed_standard_assistants(db)
            await modelops_service.get_system_model_defaults(db)
            await knowledge_service.sync_ingestion_job_records(db)
        logger.info(
            "Database schema, assistants, system model defaults, and ingestion jobs initialized."
        )
    except Exception as exc:
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

    # 6. Mount Feature Modules Routers
    from app.modules.assistants import assistants_router
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

    app.include_router(jobs_router, prefix=settings.API_PREFIX)
    app.include_router(document_types_router, prefix=settings.API_PREFIX)
    app.include_router(knowledge_router, prefix=settings.API_PREFIX)
    app.include_router(rag_router, prefix=settings.API_PREFIX)
    app.include_router(modelops_router, prefix=settings.API_PREFIX)
    app.include_router(node_catalog_router, prefix=settings.API_PREFIX)
    app.include_router(workflow_router, prefix=settings.API_PREFIX)
    app.include_router(assistants_router, prefix=settings.API_PREFIX)
    app.include_router(tools_router, prefix=settings.API_PREFIX)
    app.include_router(ocr_router, prefix=settings.API_PREFIX)
    app.include_router(evaluation_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
