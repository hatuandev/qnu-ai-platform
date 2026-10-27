"""HTTP middleware: correlation id, timing and CORS."""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from qnu.platform.config import Settings
from qnu.platform.correlation import new_correlation_id, set_correlation_id
from qnu.platform.logging import get_logger
from qnu.platform.metrics import observe_request

logger = get_logger(__name__)


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id") or new_correlation_id()
        set_correlation_id(correlation_id)
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["x-correlation-id"] = correlation_id
        observe_request(request.method, request.url.path, response.status_code, duration_ms)
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response


def setup_middlewares(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(CorrelationMiddleware)
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
