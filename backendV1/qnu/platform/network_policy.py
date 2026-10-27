"""Outbound network policy for provider endpoints."""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlparse

from qnu.platform.errors import AppException

BLOCKED_HOSTS = {"0.0.0.0", "169.254.169.254", "metadata.google.internal"}
ALLOWED_SCHEMES = {"http", "https"}


def assert_allowed_endpoint(url: str, *, allow_private: bool = False) -> str:
    """Reject non-HTTP schemes, metadata hosts and (optionally) private addresses."""
    parsed = urlparse(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AppException(
            "Endpoint không được chứa credential, query hoặc fragment.",
            code="ENDPOINT_CREDENTIALS_BLOCKED",
            status_code=400,
        )
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise AppException(
            f"Giao thức không được phép: {parsed.scheme}",
            code="ENDPOINT_SCHEME_BLOCKED",
            status_code=400,
        )
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise AppException("Endpoint thiếu host.", code="ENDPOINT_HOST_MISSING", status_code=400)
    if host in BLOCKED_HOSTS:
        raise AppException("Endpoint không được phép.", code="ENDPOINT_BLOCKED", status_code=400)
    try:
        address = ip_address(host)
    except ValueError:
        address = None
    if address and (address.is_link_local or address.is_unspecified or address.is_multicast):
        raise AppException("Endpoint không được phép.", code="ENDPOINT_BLOCKED", status_code=400)
    if not allow_private and (
        host == "localhost" or host.endswith(".localhost") or (address and not address.is_global)
    ):
        raise AppException(
            "Endpoint nội bộ bị chặn ở chế độ công khai.",
            code="ENDPOINT_PRIVATE_BLOCKED",
            status_code=400,
        )
    return url
