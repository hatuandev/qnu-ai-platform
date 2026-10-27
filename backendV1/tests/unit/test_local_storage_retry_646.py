"""A transient Windows sharing violation must not turn a complete matching blob into failure."""

import os
from pathlib import Path

import pytest

from qnu.adapters.storage.local import LocalBlobStore


@pytest.mark.asyncio
async def test_denied_replace_rechecks_matching_bytes_after_transient_read_denial(
    tmp_path, monkeypatch
):
    store = LocalBlobStore(str(tmp_path))
    await store.put_bytes("original", b"same")
    original_read = Path.read_bytes
    reads = 0

    def denied_replace(source, destination):
        raise PermissionError("Simulated sharing violation")

    def read_after_release(path):
        nonlocal reads
        if path.name == "original":
            reads += 1
            if reads == 1:
                raise PermissionError("Simulated concurrent destination handle")
        return original_read(path)

    monkeypatch.setattr(os, "replace", denied_replace)
    monkeypatch.setattr(Path, "read_bytes", read_after_release)
    assert await store.put_bytes("original", b"same") == "original"
    assert reads >= 2


@pytest.mark.asyncio
async def test_permanent_read_denial_does_not_report_success(tmp_path, monkeypatch):
    from qnu.adapters.storage import local

    store = LocalBlobStore(str(tmp_path))
    await store.put_bytes("original", b"same")
    attempts = 0

    def denied_read(path):
        nonlocal attempts
        attempts += 1
        raise PermissionError("permanent denial")

    monkeypatch.setattr(Path, "read_bytes", denied_read)
    monkeypatch.setattr(local.time, "sleep", lambda _: None)
    with pytest.raises(PermissionError, match="permanent denial"):
        await store.get_bytes("original")
    assert attempts == 6


@pytest.mark.asyncio
async def test_separate_local_adapters_publish_identical_bytes_concurrently(tmp_path):
    import asyncio

    stores = [LocalBlobStore(str(tmp_path)) for _ in range(12)]
    payload = b"original" * 10000
    assert (
        await asyncio.gather(*(store.put_bytes("nested/key", payload) for store in stores))
        == ["nested/key"] * 12
    )
    assert await stores[0].get_bytes("nested/key") == payload
    assert len(list((tmp_path / "nested").iterdir())) == 1
