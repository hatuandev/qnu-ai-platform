"""Offline verification/recovery drill; no API, live database, Redis or worker required."""

import argparse
import asyncio
import getpass
import json
import shutil
import tempfile
from pathlib import Path

from app.modules.backups.archive import extract_verified
from app.modules.backups.catalogue import backup_root
from app.modules.backups.drill import run_drill
from app.modules.backups.locks import catalogue_lock
from app.modules.backups.offload import finish_thread


async def inspect_archive(path: Path, password: str, drill: bool):
    root = backup_root()
    async with catalogue_lock("operation"):
        with tempfile.TemporaryDirectory(prefix=".backup-offline-", dir=root) as directory:
            scratch = Path(directory)
            manifest = await finish_thread(
                extract_verified, path, scratch, password, shutil.disk_usage(root).free
            )
            summary = {
                "backup_id": manifest["backup_id"],
                "schema": manifest["database"]["schema"],
                "tables": len(manifest["database"]["tables"]),
                "files": len(manifest["inventory"]),
                "vector_collections": len(manifest["qdrant"]["collections"]),
                "integrity": "verified",
                "restore_drill": "not_run",
            }
            if drill:
                summary["restore_drill"] = await run_drill(
                    manifest,
                    scratch,
                    lambda stage, progress: print(f"{progress}% {stage}", flush=True),
                )
            print(json.dumps(summary, ensure_ascii=True, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Offline encrypted backup verification; never restores to live targets"
    )
    parser.add_argument("action", choices=["verify", "drill"])
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    if not args.archive.is_file() or args.archive.is_symlink():
        parser.error("Archive must be an existing regular encrypted file")
    password = getpass.getpass("Backup password (not stored): ")
    asyncio.run(inspect_archive(args.archive.resolve(), password, args.action == "drill"))


if __name__ == "__main__":
    main()
