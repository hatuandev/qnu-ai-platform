"""Attach safe HTTP classification without preserving headers or error body text."""

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from qnu.platform.errors import AppException
from qnu.ports.provider_execution import ProviderFailure


def tag_failure(error: AppException, response: httpx.Response) -> AppException:
    delay = None
    value = response.headers.get("retry-after", "")
    try:
        delay = (
            float(value)
            if value.isdigit()
            else (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        )
        delay = max(0, min(delay, 86400))
    except (ValueError, TypeError, OverflowError):
        pass
    try:
        data = response.json()
        usage = data.get("usage") if isinstance(data, dict) else None
        tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
        error.usage_tokens = tokens if type(tokens) is int and tokens >= 0 else None
    except ValueError:
        error.usage_tokens = None
    error.provider_failure = ProviderFailure(response.status_code, delay)
    return error
