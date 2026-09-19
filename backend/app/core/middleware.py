"""HTTP Middlewares: Correlation ID, Request Timing, Rate Limiting & CORS."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.observability import metrics_registry

settings = get_settings()
logger = structlog.get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Ensures every incoming request has an X-Correlation-ID for end-to-end tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        corr_id = request.headers.get("X-Correlation-ID") or f"corr_{uuid.uuid4().hex[:12]}"
        request.state.correlation_id = corr_id

        # Bind correlation_id to structlog context vars for this request's execution context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=corr_id,
            path=request.url.path,
            method=request.method,
        )

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Calculates request latency and attaches X-Process-Time-Ms header."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)

        metrics_registry.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=process_time_ms,
        )

        # Log slow requests (> 3.0 seconds) for observability
        if process_time_ms > 3000:
            logger.warning("Slow request detected", duration_ms=process_time_ms)

        return response


def setup_middlewares(app: FastAPI) -> None:
    """Setup all core HTTP middlewares onto the FastAPI application."""
    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request Latency Timing
    app.add_middleware(RequestTimingMiddleware)

    # 3. Correlation ID Tracing
    app.add_middleware(CorrelationIdMiddleware)
