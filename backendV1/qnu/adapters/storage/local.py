"""Local filesystem blob store for development and tests."""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from qnu.platform.errors import Conflict
from qnu.ports.blob_store import BlobObject

# Fixed stripes avoid an ever-growing per-path lock registry. Blocking work stays in to_thread.
_WRITE_LOCKS = tuple(threading.Lock() for _ in range(64))


def _read_with_sharing_retry(path: Path) -> bytes:
    """Bounded sharing-violation tolerance; permanent denial still raises."""
    for attempt in range(6):
        try:
            return path.read_bytes()
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.005 * (2**attempt))
    raise AssertionError("unreachable")


def _comparison_path(path: Path) -> Path:
    # Windows resolve() can add the extended prefix as a long path is created.
    if os.name == "nt":
        value = str(path)
        if value.startswith("\\\\?\\UNC\\"):
            return Path("\\\\" + value[8:])
        return Path(value.removeprefix("\\\\?\\"))
    return path


class LocalBlobStore:
    driver = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key.lstrip("/")).resolve()
        if not _comparison_path(candidate).is_relative_to(_comparison_path(self.root)):
            raise ValueError("Blob key escapes the storage root.")
        return candidate

    @property
    def target_hash(self) -> str:
        return hashlib.sha256((self.driver + ":" + str(self.root)).encode()).hexdigest()

    async def list_objects(self, prefix: str, limit: int = 10000) -> list[BlobObject]:
        def scan():
            base, result = self._path(prefix), []
            if not base.exists():
                return result
            for path in sorted(base.rglob("*")):
                if path.is_symlink() or not path.is_file():
                    continue
                key = path.relative_to(self.root).as_posix()
                if self._path(key) != path.resolve():
                    raise ValueError("Storage inventory path changed.")
                stat = path.stat()
                result.append(
                    BlobObject(
                        key,
                        stat.st_size,
                        datetime.fromtimestamp(stat.st_mtime, UTC),
                        f"{stat.st_mtime_ns}:{stat.st_size}",
                    )
                )
                if len(result) > limit:
                    raise Conflict(
                        "Quá nhiều tệp; chưa dọn phần inventory không đầy đủ.",
                        code="storage_inventory_limit",
                    )
            return result

        return await asyncio.to_thread(scan)

    async def delete_if_unchanged(self, item: BlobObject, sha256: str) -> str:
        path = self._path(item.key)

        def remove():
            normalized = os.path.normcase(str(_comparison_path(path)))
            with _WRITE_LOCKS[hash(normalized) % len(_WRITE_LOCKS)]:
                if not path.exists():
                    return "absent"
                stat = path.stat()
                if (
                    f"{stat.st_mtime_ns}:{stat.st_size}" != item.version
                    or hashlib.sha256(path.read_bytes()).hexdigest() != sha256
                ):
                    return "changed"
                path.unlink()
                return "deleted"

        return await asyncio.to_thread(remove)

    async def put_bytes(self, key: str, payload: bytes, content_type: str | None = None) -> str:
        path = self._path(key)

        def _publish() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Same directory/filesystem: publish only after the staged write closes.
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix=".upload-", suffix=".tmp", delete=False
            ) as staging:
                temporary = Path(staging.name)
            try:
                if temporary.write_bytes(payload) != len(payload):
                    raise OSError("Incomplete staged blob write.")
                try:
                    os.replace(temporary, path)
                except PermissionError:
                    # Concurrent Windows renames may reject the losing writer.
                    # Success requires proof that the complete payload is present.
                    if _read_with_sharing_retry(path) != payload:
                        raise
            finally:
                temporary.unlink(missing_ok=True)

        def _write() -> None:
            normalized = os.path.normcase(str(_comparison_path(path)))
            with _WRITE_LOCKS[hash(normalized) % len(_WRITE_LOCKS)]:
                _publish()

        await asyncio.to_thread(_write)
        return key

    async def get_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(_read_with_sharing_retry, self._path(key))

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._path(key).exists)

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if await asyncio.to_thread(path.exists):
            await asyncio.to_thread(path.unlink)

    async def purge(self, key: str) -> None:
        path = self._path(key)
        await asyncio.to_thread(path.unlink, missing_ok=True)
