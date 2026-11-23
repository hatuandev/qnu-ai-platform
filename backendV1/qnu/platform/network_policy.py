"""Outbound network policy for provider endpoints."""

from __future__ import annotations

import socket
from ipaddress import IPv4Address, IPv6Address, ip_address
from urllib.parse import urlparse

from qnu.platform.errors import AppException

BLOCKED_HOSTS = {"0.0.0.0", "169.254.169.254", "metadata.google.internal"}
ALLOWED_SCHEMES = {"http", "https"}


def _unwrap_ip(address: IPv4Address | IPv6Address) -> IPv4Address | IPv6Address:
    """Normalize IPv4-mapped IPv6 addresses (e.g. ::ffff:169.254.169.254) to IPv4."""
    mapped = getattr(address, "ipv4_mapped", None)
    return mapped if mapped is not None else address


def _check_ip(address: IPv4Address | IPv6Address, *, allow_private: bool) -> None:
    addr = _unwrap_ip(address)
    if addr.is_link_local or addr.is_unspecified or addr.is_multicast:
        raise AppException("Endpoint không được phép.", code="ENDPOINT_BLOCKED", status_code=400)
    if not allow_private and not addr.is_global:
        raise AppException(
            "Endpoint nội bộ bị chặn ở chế độ công khai.",
            code="ENDPOINT_PRIVATE_BLOCKED",
            status_code=400,
        )


def assert_allowed_endpoint(url: str, *, allow_private: bool = False) -> str:
    """Reject non-HTTP schemes, metadata hosts, IPv4-mapped IPv6, and resolved SSRF targets."""
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
    if host in BLOCKED_HOSTS or "169.254.169.254" in host:
        raise AppException("Endpoint không được phép.", code="ENDPOINT_BLOCKED", status_code=400)
    try:
        address = ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        _check_ip(address, allow_private=allow_private)
    else:
        if not allow_private and (host == "localhost" or host.endswith(".localhost")):
            raise AppException(
                "Endpoint nội bộ bị chặn ở chế độ công khai.",
                code="ENDPOINT_PRIVATE_BLOCKED",
                status_code=400,
            )
        try:
            infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except OSError:
            infos = []
        for info in infos:
            sockaddr = info[4]
            if not sockaddr:
                continue
            try:
                resolved_ip = ip_address(sockaddr[0])
            except ValueError:
                continue
            _check_ip(resolved_ip, allow_private=allow_private)
    return url
