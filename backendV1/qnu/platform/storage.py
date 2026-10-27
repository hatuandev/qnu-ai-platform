"""Blob storage selection (delegates to adapters)."""

from __future__ import annotations

from qnu.ports.blob_store import BlobStore


def resolve_driver(store: BlobStore) -> str:
    """Expose the driver name for health and diagnostics."""
    return getattr(store, "driver", "unknown")
