"""Minimal Prometheus metrics."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter("qnu_v1_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("qnu_v1_http_request_duration_ms", "HTTP latency in ms", ["method", "path"])


def observe_request(method: str, path: str, status_code: int, duration_ms: int) -> None:
    REQUESTS.labels(method=method, path=path, status=str(status_code)).inc()
    LATENCY.labels(method=method, path=path).observe(duration_ms)


def render_metrics() -> bytes:
    return generate_latest()


__all__ = ["CONTENT_TYPE_LATEST", "observe_request", "render_metrics"]
