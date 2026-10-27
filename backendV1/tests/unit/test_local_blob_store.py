"""A failed staging write or publish cannot damage an existing local blob."""

import os
from pathlib import Path

import pytest

from qnu.adapters.storage.local import LocalBlobStore


def test_local_key_cannot_escape_to_sibling_with_same_prefix(tmp_path):
    store = LocalBlobStore(str(tmp_path / "blobs"))
    with pytest.raises(ValueError, match="escapes"):
        store._path("../blobs-other/original")


@pytest.mark.skipif(os.name != "nt", reason="Windows paths are case-insensitive")
def test_local_key_accepts_windows_path_casing(tmp_path):
    store = LocalBlobStore(str(tmp_path))
    store.root = Path(str(store.root).swapcase())
    assert store._path("original").is_relative_to(tmp_path)


@pytest.mark.skipif(os.name != "nt", reason="Windows extended path prefix")
def test_extended_windows_key_inside_root_is_accepted(tmp_path):
    store = LocalBlobStore(str(tmp_path))
    key = "\\\\?\\" + str(tmp_path / "original")
    assert store._path(key) == Path(key)


@pytest.mark.skipif(os.name != "nt", reason="Windows extended path prefix")
def test_extended_windows_key_outside_root_is_rejected(tmp_path):
    store = LocalBlobStore(str(tmp_path / "blobs"))
    key = "\\\\?\\" + str(tmp_path / "blobs-other/original")
    with pytest.raises(ValueError, match="escapes"):
        store._path(key)


@pytest.mark.asyncio
async def test_successful_local_write_publishes_complete_bytes(tmp_path):
    store = LocalBlobStore(str(tmp_path))
    await store.put_bytes("nested/original", b"first")
    await store.put_bytes("nested/original", b"replacement")
    assert await store.get_bytes("nested/original") == b"replacement"
    assert list((tmp_path / "nested").iterdir()) == [tmp_path / "nested/original"]


@pytest.mark.asyncio
async def test_partial_staging_write_preserves_old_blob_and_removes_temp(tmp_path, monkeypatch):
    store = LocalBlobStore(str(tmp_path))
    await store.put_bytes("original", b"committed-original")
    write = Path.write_bytes

    def interrupt(path, payload):
        write(path, payload[:3])
        raise OSError("Injected disk failure")

    monkeypatch.setattr(Path, "write_bytes", interrupt)
    with pytest.raises(OSError, match="Injected disk failure"):
        await store.put_bytes("original", b"new-payload")
    assert await store.get_bytes("original") == b"committed-original"
    assert list(tmp_path.iterdir()) == [tmp_path / "original"]


@pytest.mark.asyncio
async def test_failed_publish_preserves_old_blob_and_removes_temp(tmp_path, monkeypatch):
    store = LocalBlobStore(str(tmp_path))
    await store.put_bytes("original", b"committed-original")

    def failed_replace(source, destination):
        assert Path(source).read_bytes() == b"new-payload"
        assert Path(destination).read_bytes() == b"committed-original"
        raise OSError("Injected publish failure")

    monkeypatch.setattr(os, "replace", failed_replace)
    with pytest.raises(OSError, match="Injected publish failure"):
        await store.put_bytes("original", b"new-payload")
    assert await store.get_bytes("original") == b"committed-original"
    assert list(tmp_path.iterdir()) == [tmp_path / "original"]


@pytest.mark.asyncio
@pytest.mark.parametrize("existing", [b"same-payload", b"different-payload"])
async def test_denied_replace_only_succeeds_if_destination_matches(tmp_path, monkeypatch, existing):
    store = LocalBlobStore(str(tmp_path))
    await store.put_bytes("original", existing)

    def denied_replace(source, destination):
        assert Path(source).read_bytes() == b"same-payload"
        raise PermissionError("Injected concurrent rename denial")

    monkeypatch.setattr(os, "replace", denied_replace)
    if existing == b"same-payload":
        assert await store.put_bytes("original", b"same-payload") == "original"
    else:
        with pytest.raises(PermissionError, match="concurrent rename"):
            await store.put_bytes("original", b"same-payload")
    assert await store.get_bytes("original") == existing
    assert list(tmp_path.iterdir()) == [tmp_path / "original"]
