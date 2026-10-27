"""Structured logging with correlation id propagation."""

from __future__ import annotations

import logging

import structlog

from qnu.platform.correlation import current_correlation_id
from qnu.platform.redaction import redact


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_correlation,
            _redact_event,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def _add_correlation(_logger: object, _method: str, event_dict: dict) -> dict:
    correlation_id = current_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def get_logger(name: str):
    return structlog.get_logger(name)


def _redact_event(_logger: object, _method: str, event_dict: dict) -> dict:
    sensitive = {
        "secret",
        "password",
        "authorization",
        "api_key",
        "access_token",
        "secret_encrypted",
        "prompt",
        "messages",
        "image_url",
    }

    def clean(value):
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if str(key).lower() in sensitive else clean(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        return redact(value) if isinstance(value, str) else value

    return clean(event_dict)
