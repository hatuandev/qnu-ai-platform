"""In-memory bounded LRU cache for immutable artifacts, canonical JSON, and version bundles.

Provides sub-millisecond repeated reading for compiled documents, canonical OCR structures,
and immutable revisions while bounding memory consumption. Thread-safe and async-safe.
Invalidation occurs naturally as keys include immutable content hashes (sha256).
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any


class BoundedLRUCache:
    """Thread-safe bounded Least Recently Used (LRU) memory cache."""

    def __init__(self, maxsize: int = 64) -> None:
        self.maxsize = maxsize
        self._cache: OrderedDict[Any, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"size": len(self._cache), "maxsize": self.maxsize}


# Specialized bounded caches for knowledge artifacts
CANONICAL_JSON_CACHE = BoundedLRUCache(maxsize=32)
ARTIFACT_PAYLOAD_CACHE = BoundedLRUCache(maxsize=64)
REVISION_PAYLOAD_CACHE = BoundedLRUCache(maxsize=16)
VERSION_BUNDLE_CACHE = BoundedLRUCache(maxsize=32)
INDEX_MANIFEST_CACHE = BoundedLRUCache(maxsize=16)


def get_index_manifest(manifest_key: str, sha256: str) -> dict | None:
    return INDEX_MANIFEST_CACHE.get((manifest_key, sha256))


def set_index_manifest(manifest_key: str, sha256: str, data: dict) -> None:
    INDEX_MANIFEST_CACHE.set((manifest_key, sha256), data)


def get_canonical_json(run_id: str, sha256: str) -> dict | None:
    return CANONICAL_JSON_CACHE.get((run_id, sha256))


def set_canonical_json(run_id: str, sha256: str, data: dict) -> None:
    CANONICAL_JSON_CACHE.set((run_id, sha256), data)


def get_artifact_payload(blob_key: str, sha256: str) -> bytes | None:
    return ARTIFACT_PAYLOAD_CACHE.get((blob_key, sha256))


def set_artifact_payload(blob_key: str, sha256: str, payload: bytes) -> None:
    ARTIFACT_PAYLOAD_CACHE.set((blob_key, sha256), payload)


def get_revision_bytes(storage_key: str, sha256: str) -> bytes | None:
    return REVISION_PAYLOAD_CACHE.get((storage_key, sha256))


def set_revision_bytes(storage_key: str, sha256: str, payload: bytes) -> None:
    REVISION_PAYLOAD_CACHE.set((storage_key, sha256), payload)


def get_version_bundle(run_id: str, input_sha256: str) -> Any | None:
    return VERSION_BUNDLE_CACHE.get((run_id, input_sha256))


def set_version_bundle(run_id: str, input_sha256: str, bundle: Any) -> None:
    VERSION_BUNDLE_CACHE.set((run_id, input_sha256), bundle)


def clear_all_artifact_caches() -> None:
    CANONICAL_JSON_CACHE.clear()
    ARTIFACT_PAYLOAD_CACHE.clear()
    REVISION_PAYLOAD_CACHE.clear()
    VERSION_BUNDLE_CACHE.clear()
    INDEX_MANIFEST_CACHE.clear()
