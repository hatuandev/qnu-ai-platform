"""Encrypted backup, explicit preview and restore to a new isolated target only."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from starlette.requests import Request

from qnu.adapters.storage.local import LocalBlobStore
from qnu.adapters.storage.s3 import S3BlobStore
from qnu.adapters.vector.qdrant import QdrantVectorStore
from qnu.domains.identity.service import resolve_actor
from qnu.domains.operations.recovery import service
from qnu.domains.workspaces.access import require_platform_admin
from qnu.main import (
    app as _registered_models,  # noqa: F401 - register every owned table; no lifespan/I/O
)
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException


async def main(args):
    token = os.environ.get("RECOVERY_ACCESS_TOKEN", "")
    actor = await resolve_actor(
        Request({"type": "http", "headers": [(b"authorization", ("Bearer " + token).encode())]})
    )
    require_platform_admin(actor)
    key = os.environ.get("RECOVERY_ENCRYPTION_KEY", "")
    settings = get_settings()
    if args.command == "backup":
        blob = (
            LocalBlobStore(settings.LOCAL_STORAGE_PATH)
            if settings.STORAGE_DRIVER == "local"
            else S3BlobStore(settings)
        )
        destination = Path(args.bundle).resolve()
        if destination.exists():
            raise ValueError("Bundle đích đã tồn tại; không ghi đè.")
        async with AsyncSessionFactory() as db:
            payload = await service.capture(db, blob, actor, key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(payload)
        return {"status": "backed_up", "bytes": len(payload), "encrypted": True}
    if not args.target_storage:
        raise ValueError(
            "Cần --target-storage mới; CLI restore hiện hỗ trợ local. S3 dùng cùng service/port riêng."
        )
    blob = LocalBlobStore(args.target_storage)
    vectors = QdrantVectorStore(args.target_qdrant or settings.QDRANT_URL)
    url = os.environ.get("RECOVERY_DATABASE_URL", "")
    payload = Path(args.bundle).read_bytes()
    preview = service.plan(payload, key, url, blob, vectors)
    if args.command == "preview":
        return preview
    return await service.restore(payload, key, url, blob, vectors, actor, args.confirm_hash)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["backup", "preview", "restore"])
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--target-storage")
    parser.add_argument("--target-qdrant")
    parser.add_argument("--confirm-hash", default="")
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(main(args)), ensure_ascii=False))
    except AppException as exc:
        print(json.dumps({"status": "failed", "code": exc.code}, ensure_ascii=False))
        raise SystemExit(1)
    except Exception:
        print(json.dumps({"status": "failed", "code": "recovery_operator_error"}))
        raise SystemExit(1)
