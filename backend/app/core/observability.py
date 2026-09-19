"""Observability & Metrics Collector — In-Memory Metrics Registry & Prometheus Exporter."""

from __future__ import annotations

import threading
import time
from typing import Any


class MetricsRegistry:
    """Thread-safe in-memory metrics registry for QNU AI Platform."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.start_time = time.time()
        self.total_requests = 0
        self.total_process_time_ms = 0.0
        self.slow_requests = 0
        self.requests_by_status: dict[str, int] = {}
        self.requests_by_method: dict[str, int] = {}
        self.requests_by_path: dict[str, int] = {}

    def record_request(
        self, method: str, path: str, status_code: int, duration_ms: float
    ) -> None:
        """Record an HTTP request execution metrics."""
        with self._lock:
            self.total_requests += 1
            self.total_process_time_ms += duration_ms

            status_str = str(status_code)
            self.requests_by_status[status_str] = (
                self.requests_by_status.get(status_str, 0) + 1
            )

            m = method.upper()
            self.requests_by_method[m] = self.requests_by_method.get(m, 0) + 1

            # Normalize path (keep top 2 segments to avoid cardinality explosion)
            parts = [p for p in path.strip("/").split("/") if p]
            norm_path = "/" + "/".join(parts[:3]) if parts else "/"
            self.requests_by_path[norm_path] = (
                self.requests_by_path.get(norm_path, 0) + 1
            )

            if duration_ms > 3000:
                self.slow_requests += 1

    def get_summary(self) -> dict[str, Any]:
        """Return a structured JSON dictionary of collected metrics."""
        with self._lock:
            uptime_seconds = round(time.time() - self.start_time, 1)
            avg_latency = (
                round(self.total_process_time_ms / self.total_requests, 2)
                if self.total_requests > 0
                else 0.0
            )
            return {
                "uptime_seconds": uptime_seconds,
                "total_requests": self.total_requests,
                "avg_latency_ms": avg_latency,
                "slow_requests": self.slow_requests,
                "requests_by_status": dict(self.requests_by_status),
                "requests_by_method": dict(self.requests_by_method),
                "requests_by_path": dict(self.requests_by_path),
            }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text exposition format."""
        with self._lock:
            uptime = time.time() - self.start_time
            lines = [
                "# HELP qnu_app_uptime_seconds Total application uptime in seconds.",
                "# TYPE qnu_app_uptime_seconds counter",
                f"qnu_app_uptime_seconds {uptime:.1f}",
                "# HELP qnu_http_requests_total Total HTTP requests processed.",
                "# TYPE qnu_http_requests_total counter",
                f"qnu_http_requests_total {self.total_requests}",
                "# HELP qnu_http_slow_requests_total Total HTTP requests with latency > 3s.",
                "# TYPE qnu_http_slow_requests_total counter",
                f"qnu_http_slow_requests_total {self.slow_requests}",
            ]

            # By status
            if self.requests_by_status:
                lines.append(
                    "# HELP qnu_http_requests_by_status_total HTTP requests partitioned by status code."
                )
                lines.append("# TYPE qnu_http_requests_by_status_total counter")
                for st, count in sorted(self.requests_by_status.items()):
                    lines.append(f'qnu_http_requests_by_status_total{{status="{st}"}} {count}')

            # By method
            if self.requests_by_method:
                lines.append(
                    "# HELP qnu_http_requests_by_method_total HTTP requests partitioned by HTTP method."
                )
                lines.append("# TYPE qnu_http_requests_by_method_total counter")
                for meth, count in sorted(self.requests_by_method.items()):
                    lines.append(f'qnu_http_requests_by_method_total{{method="{meth}"}} {count}')

            return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
