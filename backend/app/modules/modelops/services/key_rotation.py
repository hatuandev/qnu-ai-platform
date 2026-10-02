"""Provider API-key rotation policies and HTTP failure classification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal

import httpx

from app.core.exceptions import AppException

KeyFailureState = Literal["rate_limited", "exhausted", "invalid"]

DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 60
MAX_RATE_LIMIT_COOLDOWN_SECONDS = 86_400

_HARD_QUOTA_CODES = {
    "billing_hard_limit_reached",
    "credit_balance_exhausted",
    "insufficient_quota",
    "monthly_quota_exceeded",
    "out_of_credits",
    "payment_required",
    "quota_exceeded",
    "quota_exhausted",
}
_INVALID_CREDENTIAL_CODES = {
    "api_key_invalid",
    "authentication_error",
    "invalid_api_key",
    "invalid_authentication",
    "unauthenticated",
}


@dataclass(frozen=True, slots=True)
class KeyFailure:
    """Normalized provider failure used by the key-pool state machine."""

    state: KeyFailureState | None
    status_code: int | None
    retry_after_seconds: int | None
    reason: str


def _walk_error_payload(value: Any) -> list[tuple[str, Any]]:
    """Flatten structured provider error data without depending on one vendor shape."""
    flattened: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            flattened.append((str(key).lower(), nested))
            flattened.extend(_walk_error_payload(nested))
    elif isinstance(value, list):
        for nested in value:
            flattened.extend(_walk_error_payload(nested))
    return flattened


def _parse_duration_seconds(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return max(1, min(int(value), MAX_RATE_LIMIT_COOLDOWN_SECONDS))
    if not isinstance(value, str):
        return None

    raw = value.strip().lower()
    try:
        if raw.endswith("ms"):
            return max(
                1,
                min(round(float(raw[:-2]) / 1000), MAX_RATE_LIMIT_COOLDOWN_SECONDS),
            )
        if raw.endswith("s"):
            return max(1, min(round(float(raw[:-1])), MAX_RATE_LIMIT_COOLDOWN_SECONDS))
        return max(1, min(round(float(raw)), MAX_RATE_LIMIT_COOLDOWN_SECONDS))
    except ValueError:
        return None


def _parse_retry_after(value: str | None) -> int | None:
    seconds = _parse_duration_seconds(value)
    if seconds is not None:
        return seconds
    if not value:
        return None
    try:
        retry_at = parsedate_to_datetime(value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        delta = round((retry_at - datetime.now(UTC)).total_seconds())
        return max(1, min(delta, MAX_RATE_LIMIT_COOLDOWN_SECONDS))
    except (TypeError, ValueError, OverflowError):
        return None


def _extract_response(exc: Exception) -> httpx.Response | None:
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, httpx.HTTPStatusError):
            return current.response
        current = current.__cause__ or current.__context__
    return None


def classify_key_failure(exc: Exception) -> KeyFailure:
    """Map provider exceptions to durable key states and retry timing."""
    response = _extract_response(exc)
    status_code = response.status_code if response is not None else None
    retry_after: int | None = None
    payload: Any = None

    if response is not None:
        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        try:
            payload = response.json()
        except (ValueError, TypeError):
            payload = None
    elif isinstance(exc, AppException):
        status_code = exc.status_code
        payload = exc.details

    flattened = _walk_error_payload(payload)
    structured_codes = {
        str(value).strip().lower()
        for key, value in flattened
        if key in {"code", "reason", "status", "type"} and value is not None
    }
    if retry_after is None:
        for key, value in flattened:
            if key in {"retryafter", "retry_after", "retrydelay", "retry_delay"}:
                retry_after = _parse_duration_seconds(value)
                if retry_after is not None:
                    break

    payload_texts = [
        str(value).lower()
        for key, value in flattened
        if key in {"message", "detail", "error", "description"} and isinstance(value, str)
    ]
    message_corpus = " ".join([str(exc).lower(), *payload_texts])
    if status_code is None and "429" in message_corpus:
        status_code = 429
    hard_quota = (
        status_code == 402
        or bool(structured_codes & _HARD_QUOTA_CODES)
        or any(
            marker in message_corpus
            for marker in (
                "insufficient_quota",
                "billing hard limit",
                "credit balance",
                "quota exceeded",
                "quota_exhausted",
                "out of credit",
                "credit expired",
            )
        )
        or (
            status_code == 403
            and any(
                marker in message_corpus
                for marker in ("quota", "credit", "balance", "billing", "exceeded")
            )
        )
    )
    invalid_credential = bool(structured_codes & _INVALID_CREDENTIAL_CODES)

    if hard_quota:
        return KeyFailure("exhausted", status_code, None, "provider_quota_exhausted")

    if status_code == 429 or (
        isinstance(exc, AppException) and exc.code == "rate_limit_exceeded"
    ):
        return KeyFailure(
            "rate_limited",
            status_code,
            retry_after or DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS,
            "provider_rate_limited",
        )
    if status_code == 401 or invalid_credential:
        return KeyFailure("invalid", status_code, None, "provider_key_invalid")
    return KeyFailure(None, status_code, None, "provider_request_failed")


def describe_provider_failure(exc: Exception) -> str:
    """Return a log-safe failure description without URLs, credentials or payloads."""
    failure = classify_key_failure(exc)
    status = f" HTTP {failure.status_code}" if failure.status_code is not None else ""
    return f"{type(exc).__name__}{status} ({failure.reason})"
