"""Canonical provider-key states shared by persistence and API boundaries."""

from typing import Final

PROVIDER_KEY_STATUSES: Final[frozenset[str]] = frozenset(
    {"active", "rate_limited", "exhausted", "invalid", "inactive"}
)

_LEGACY_STATUS_ALIASES: Final[dict[str, str]] = {"disabled": "inactive"}


def normalize_provider_key_status(value: object) -> str:
    """Return a canonical, fail-closed status for persisted legacy values."""
    if value is None:
        return "active"
    normalized = str(value).strip().lower()
    normalized = _LEGACY_STATUS_ALIASES.get(normalized, normalized)
    return normalized if normalized in PROVIDER_KEY_STATUSES else "inactive"
