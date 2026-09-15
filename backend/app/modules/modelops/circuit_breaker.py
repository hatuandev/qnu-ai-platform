"""Circuit Breaker Pattern for Resilient LLM Provider Invocation."""

from __future__ import annotations

import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"  # Hoạt động bình thường
    OPEN = "OPEN"  # Bị ngắt do lỗi liên tiếp, từ chối request
    HALF_OPEN = "HALF_OPEN"  # Đang thử nghiệm phục hồi


class CircuitBreaker:
    """Manages failure tracking and fault tolerance for a single LLM provider."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0

    def can_execute(self) -> bool:
        """Check if request can pass through this provider circuit."""
        now = time.time()
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            if now - self.last_failure_time >= self.recovery_timeout_seconds:
                logger.info(
                    "Circuit Breaker [%s] transitioning from OPEN to HALF_OPEN (probing)",
                    self.name,
                )
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False

        # Allow single probe request when HALF_OPEN
        return self.state == CircuitBreakerState.HALF_OPEN

    def record_success(self) -> None:
        """Record successful call, resetting state to CLOSED."""
        if self.state in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN):
            logger.info("Circuit Breaker [%s] recovered successfully -> CLOSED", self.name)
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0

    def record_failure(self, error: Exception | None = None) -> None:
        """Record failure, potentially tripping circuit to OPEN."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(
            "Circuit Breaker [%s] recorded failure #%d: %s",
            self.name,
            self.failure_count,
            str(error) if error else "Unknown error",
        )

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.error(
                "Circuit Breaker [%s] TRIPPED -> OPEN (tripped for %ds)",
                self.name,
                int(self.recovery_timeout_seconds),
            )


class CircuitBreakerRegistry:
    """Registry managing circuit breakers per provider name."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name)
        return self._breakers[name]


circuit_breaker_registry = CircuitBreakerRegistry()
