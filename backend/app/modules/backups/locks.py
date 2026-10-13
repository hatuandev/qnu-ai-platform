"""OS-released catalogue/process locks, so offline verification needs no DB/Redis."""

import asyncio
import os
from contextlib import asynccontextmanager, contextmanager

from app.core.exceptions import AppException
from app.modules.backups.catalogue import backup_root
from app.modules.backups.errors import BackupIntegrityError


@contextmanager
def filesystem_lock(name: str):
    if name not in ("reservation", "operation"):
        raise BackupIntegrityError("Unsupported lock")
    path = backup_root() / ("." + name + ".lock")
    if path.is_symlink():
        raise BackupIntegrityError("Unsafe lock path")
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise AppException(
                "Một thao tác sao lưu khác đang chạy.", code="BACKUP_BUSY", status_code=409
            ) from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@asynccontextmanager
async def catalogue_lock(name: str):
    lock = filesystem_lock(name)
    await asyncio.to_thread(lock.__enter__)
    try:
        yield
    finally:
        await asyncio.to_thread(lock.__exit__, None, None, None)
