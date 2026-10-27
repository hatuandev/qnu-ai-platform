"""Request/job correlation id stored in a context variable."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def new_correlation_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def current_correlation_id() -> str | None:
    return _correlation_id.get()
