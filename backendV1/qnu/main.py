"""Application entrypoint for backendV1."""

from __future__ import annotations

from fastapi import FastAPI

from qnu.api.handlers import register_exception_handlers
from qnu.api.lifespan import lifespan
from qnu.api.routes import register_routes
from qnu.platform.config import get_settings
from qnu.platform.logging import configure_logging
from qnu.platform.middleware import setup_middlewares


def create_app() -> FastAPI:
    """Build the FastAPI application from explicit, testable pieces."""
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="QNU.AI Platform - Backend v1",
        description="Modular monolith for unit-scoped chatbots and evidence-first RAG.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    setup_middlewares(app, settings)
    register_exception_handlers(app)
    register_routes(app, settings)
    return app


app = create_app()
