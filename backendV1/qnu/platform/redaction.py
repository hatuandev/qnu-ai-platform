"""Remove secrets and sensitive identifiers from logs and error text."""

from __future__ import annotations

import re

PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?:Bearer\s+)[\w.\-+/=]+", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"\b(?:sk|pk|rk)[-_][A-Za-z0-9_\-]{8,}"), "[REDACTED_KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}"), "[REDACTED_KEY]"),
    (re.compile(r"enc:v1:[A-Za-z0-9_\-+/=]+"), "[REDACTED_SECRET]"),
    (re.compile(r"[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b0\d{9,10}\b"), "[REDACTED_PHONE]"),
)


def redact(text: str) -> str:
    """Return text with credentials, emails and phone numbers masked."""
    if not text:
        return text
    cleaned = text
    for pattern, replacement in PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def redact_exception(exc: BaseException) -> str:
    return redact(f"{type(exc).__name__}: {exc}")
