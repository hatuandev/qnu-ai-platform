#!/usr/bin/env python3
"""Unified PostgreSQL and Qdrant Snapshot Backup Tool for QNU AI Platform.

Complies with AGENTS.md:
- Preserves audit trails, checksums, and source integrity.
- Does not modify RAG/OCR pipelines or live production data.
- Provides non-destructive, verified backups with SHA-256 integrity checks.
- Supports retention policies (--retention-days and --retention-keep).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backendV1"

# Ensure root and backend directory are in sys.path
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_env_defaults() -> dict[str, str]:
    """Parse environment variables from root or backendV1 .env files."""
    env: dict[str, str] = {}
    for path in [ROOT / ".env", BACKEND_DIR / ".env"]:
        if path.is_file():
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            except Exception:
                pass
    return env


def compute_sha256(file_path: Path) -> str:
    """Compute hex SHA-256 digest of a file in streaming 64KB blocks."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_bytes_sha256(data: bytes) -> str:
    """Compute hex SHA-256 digest of in-memory bytes."""
    return hashlib.sha256(data).hexdigest()


def resolve_qdrant_api_key(env: dict[str, str] | None = None) -> str | None:
    """Resolve optional QDRANT_API_KEY from process environment or .env defaults."""
    key = os.environ.get("QDRANT_API_KEY")
    if not key and env:
        key = env.get("QDRANT_API_KEY")
    if key:
        key = key.strip()
    return key or None


def qdrant_headers(api_key: str | None) -> dict[str, str]:
    """Build Qdrant HTTP headers including api-key when configured."""
    return {"api-key": api_key} if api_key else {}


async def backup_postgres_native(
    db_dsn: str, out_file: Path
) -> dict[str, Any]:
    """Export all public PostgreSQL tables into a compressed tar.gz archive using asyncpg."""
    import asyncpg

    raw_dsn = db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(raw_dsn)
    try:
        # Use a single REPEATABLE READ read-only transaction for cross-table snapshot consistency
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            # Get Alembic revision
            alembic_head = None
            try:
                alembic_head = await conn.fetchval(
                    "SELECT version_num FROM alembic_version_backendv1 LIMIT 1"
                )
            except Exception:
                pass

            # Query list of base tables
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            table_names = [r["table_name"] for r in tables]

            table_stats: dict[str, int] = {}
            total_rows = 0

            # Create tar.gz archive streaming to file
            with tarfile.open(out_file, "w:gz") as tar:
                now_dt = datetime.datetime.now(datetime.UTC)
                schema_info: dict[str, Any] = {
                    "alembic_head": alembic_head,
                    "exported_at": now_dt.isoformat(),
                    "tables": {},
                }

                for tbl in table_names:
                    # Get column schema info
                    cols = await conn.fetch(
                        """
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = $1
                        ORDER BY ordinal_position
                        """,
                        tbl,
                    )
                    col_defs = [
                        {
                            "name": c["column_name"],
                            "type": c["data_type"],
                            "nullable": c["is_nullable"] == "YES",
                        }
                        for c in cols
                    ]
                    schema_info["tables"][tbl] = col_defs

                    # Stream table data to buffer
                    buf = io.BytesIO()
                    await conn.copy_from_table(tbl, output=buf, format="csv", header=True)
                    csv_bytes = buf.getvalue()
                    buf.close()

                    # Row count within the same consistent snapshot
                    row_count = await conn.fetchval(f'SELECT count(*) FROM "{tbl}"')
                    table_stats[tbl] = row_count
                    total_rows += row_count

                    # Add to tar archive
                    tarinfo = tarfile.TarInfo(name=f"tables/{tbl}.csv")
                    tarinfo.size = len(csv_bytes)
                    tarinfo.mtime = int(now_dt.timestamp())
                    tar.addfile(tarinfo, io.BytesIO(csv_bytes))

                # Add schema metadata JSON to tar
                meta_bytes = json.dumps(
                    {
                        "schema_version": "qnu.postgres-dump/v1",
                        "alembic_head": alembic_head,
                        "table_count": len(table_names),
                        "total_rows": total_rows,
                        "table_stats": table_stats,
                        "columns": schema_info["tables"],
                    },
                    indent=2,
                    ensure_ascii=False,
                ).encode("utf-8")

                meta_info = tarfile.TarInfo(name="schema_metadata.json")
                meta_info.size = len(meta_bytes)
                meta_info.mtime = int(now_dt.timestamp())
                tar.addfile(meta_info, io.BytesIO(meta_bytes))

        size_bytes = out_file.stat().st_size
        if size_bytes == 0:
            raise RuntimeError("PostgreSQL dump file is empty (0 bytes).")

        return {
            "tool": "asyncpg_native",
            "format": "tar_gz",
            "output_file": str(out_file),
            "alembic_head": alembic_head,
            "table_count": len(table_names),
            "total_rows": total_rows,
            "table_stats": table_stats,
            "size_bytes": size_bytes,
            "sha256": compute_sha256(out_file),
        }
    finally:
        await conn.close()


def backup_postgres_pg_dump(
    db_dsn: str, out_file: Path
) -> dict[str, Any]:
    """Export database using pg_dump CLI if installed."""
    import urllib.parse

    raw_dsn = db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urllib.parse.urlparse(raw_dsn)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "127.0.0.1",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/") or "postgres",
        "-Fc",  # Custom format
        "-f", str(out_file),
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed (exit {result.returncode}): {result.stderr}")

    size_bytes = out_file.stat().st_size
    if size_bytes == 0:
        raise RuntimeError("pg_dump output file is empty (0 bytes).")

    return {
        "tool": "pg_dump_custom",
        "format": "pg_dump_custom",
        "output_file": str(out_file),
        "size_bytes": size_bytes,
        "sha256": compute_sha256(out_file),
    }


def _resolve_pg_output_path(out_target: Path, use_pg_dump: bool) -> Path:
    """Ensure the output filename extension strictly matches the export format."""
    if out_target.is_dir() or not out_target.suffix:
        return out_target / ("database_dump.dump" if use_pg_dump else "database_dump.tar.gz")
    name = out_target.name
    if use_pg_dump:
        if name.endswith(".tar.gz"):
            return out_target.with_name(name[:-7] + ".dump")
        return out_target if name.endswith(".dump") else out_target.with_suffix(".dump")
    if name.endswith(".dump"):
        return out_target.with_name(name[:-5] + ".tar.gz")
    return out_target if name.endswith(".tar.gz") else out_target.with_name(out_target.stem + ".tar.gz")


async def backup_postgres(
    db_dsn: str, out_file: Path, tool_preference: str = "auto"
) -> dict[str, Any]:
    """Execute PostgreSQL backup using preferred or available tool."""
    has_pg_dump = shutil.which("pg_dump") is not None
    use_pg_dump = (tool_preference == "pg_dump") or (
        tool_preference == "auto" and has_pg_dump
    )

    if use_pg_dump:
        dump_file = _resolve_pg_output_path(out_file, use_pg_dump=True)
        dump_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            return backup_postgres_pg_dump(db_dsn, dump_file)
        except Exception as e:
            if dump_file.exists():
                dump_file.unlink(missing_ok=True)
            if tool_preference == "pg_dump":
                raise
            print(f"[WARN] pg_dump failed ({e}), falling back to native asyncpg export...")

    native_file = _resolve_pg_output_path(out_file, use_pg_dump=False)
    native_file.parent.mkdir(parents=True, exist_ok=True)
    return await backup_postgres_native(db_dsn, native_file)


async def backup_qdrant_collections(
    qdrant_url: str, out_dir: Path, api_key: str | None = None
) -> list[dict[str, Any]]:
    """Discover all Qdrant collections, snapshot them, and download snapshot files."""
    import httpx

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    headers = qdrant_headers(api_key)

    async with httpx.AsyncClient(timeout=120.0, headers=headers) as client:
        # List all collections
        resp = await client.get(f"{qdrant_url}/collections")
        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch Qdrant collections ({resp.status_code}): {resp.text}"
            )

        data = resp.json()
        collections = [
            c["name"] for c in data.get("result", {}).get("collections", [])
        ]

        for col in collections:
            print(f"  -> Snapshotting Qdrant collection: {col}...")
            # 1. Trigger snapshot creation
            snap_resp = await client.post(f"{qdrant_url}/collections/{col}/snapshots")
            if snap_resp.status_code != 200:
                raise RuntimeError(
                    f"Failed to create snapshot for collection '{col}' ({snap_resp.status_code}): {snap_resp.text}"
                )

            snap_result = snap_resp.json().get("result", {})
            snap_name = snap_result.get("name")
            expected_size = snap_result.get("size")
            if not snap_name:
                raise RuntimeError(f"Snapshot creation returned no name for collection '{col}'")

            target_file = out_dir / f"{col}.snapshot"

            # 2. Download snapshot file
            try:
                async with client.stream(
                    "GET", f"{qdrant_url}/collections/{col}/snapshots/{snap_name}"
                ) as stream_resp:
                    if stream_resp.status_code != 200:
                        raise RuntimeError(
                            f"Failed to download snapshot '{snap_name}' ({stream_resp.status_code})"
                        )
                    with target_file.open("wb") as f:
                        async for chunk in stream_resp.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
            finally:
                # 3. Clean up server-side snapshot to save Qdrant disk space
                try:
                    await client.delete(
                        f"{qdrant_url}/collections/{col}/snapshots/{snap_name}"
                    )
                except Exception as del_err:
                    print(f"    [WARN] Failed to delete temporary snapshot on server: {del_err}")

            size_bytes = target_file.stat().st_size
            if size_bytes == 0:
                raise RuntimeError(f"Downloaded snapshot for '{col}' is empty (0 bytes).")

            sha256 = compute_sha256(target_file)
            results.append(
                {
                    "collection": col,
                    "snapshot_file": target_file.relative_to(out_dir.parent).as_posix(),
                    "size_bytes": size_bytes,
                    "expected_size": expected_size,
                    "sha256": sha256,
                }
            )

    return results


def apply_retention(
    backups_root: Path, retention_days: int | None, retention_keep: int | None
) -> list[str]:
    """Purge outdated backup folders based on day threshold or keep count."""
    removed: list[str] = []
    if not backups_root.is_dir():
        return removed

    # Identify valid backup directories
    backup_dirs: list[tuple[Path, float]] = []
    for entry in backups_root.iterdir():
        if entry.is_dir() and (entry / "manifest.json").is_file():
            backup_dirs.append((entry, entry.stat().st_mtime))

    # Sort descending by mtime (newest first)
    backup_dirs.sort(key=lambda x: x[1], reverse=True)

    # 1. Retention by age (days)
    if retention_days is not None and retention_days > 0:
        now = datetime.datetime.now(datetime.UTC).timestamp()
        cutoff = now - (retention_days * 86400)
        remaining_dirs: list[tuple[Path, float]] = []
        for d, mtime in backup_dirs:
            if mtime < cutoff:
                try:
                    shutil.rmtree(d)
                    removed.append(str(d.name))
                    print(f"  [RETENTION] Removed backup older than {retention_days} days: {d.name}")
                except Exception as e:
                    print(f"  [WARN] Failed to remove {d.name}: {e}")
            else:
                remaining_dirs.append((d, mtime))
        backup_dirs = remaining_dirs

    # 2. Retention by count (keep top K)
    if retention_keep is not None and retention_keep > 0 and len(backup_dirs) > retention_keep:
        to_remove = backup_dirs[retention_keep:]
        for d, _ in to_remove:
            try:
                shutil.rmtree(d)
                removed.append(str(d.name))
                print(f"  [RETENTION] Removed backup exceeding keep={retention_keep}: {d.name}")
            except Exception as e:
                print(f"  [WARN] Failed to remove {d.name}: {e}")

    return removed


def verify_backup(backup_dir: Path) -> dict[str, Any]:
    """Verify integrity, file sizes, and SHA-256 checksums of an existing backup."""
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing manifest.json in {backup_dir}")

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    if manifest.get("schema_version") != "qnu.system-backup/v1":
        raise ValueError(
            f"Unsupported manifest schema version: {manifest.get('schema_version')}"
        )

    verified_items: list[dict[str, Any]] = []
    total_bytes = 0

    for item in manifest.get("items", []):
        rel_path = item.get("path")
        expected_sha = item.get("sha256")
        expected_size = item.get("size_bytes")

        target_file = backup_dir / rel_path
        if not target_file.is_file():
            raise FileNotFoundError(f"Backup artifact missing: {rel_path}")

        actual_size = target_file.stat().st_size
        if actual_size != expected_size:
            raise ValueError(
                f"Size mismatch for {rel_path}: expected {expected_size}, got {actual_size}"
            )

        actual_sha = compute_sha256(target_file)
        if actual_sha != expected_sha:
            raise ValueError(
                f"Checksum mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}"
            )

        # Format-specific integrity check
        item_tool = item.get("tool")
        if target_file.name.endswith(".tar.gz"):
            with tarfile.open(target_file, "r:gz") as tar:
                members = tar.getnames()
                if not members:
                    raise ValueError(f"Tar archive {rel_path} has no members.")
                if item.get("kind") == "postgres" and "schema_metadata.json" not in members:
                    raise ValueError(
                        f"PostgreSQL tar archive {rel_path} is missing schema_metadata.json."
                    )
        elif target_file.name.endswith(".dump") or item_tool == "pg_dump_custom":
            with target_file.open("rb") as f:
                magic = f.read(5)
            if magic != b"PGDMP":
                raise ValueError(
                    f"PostgreSQL custom dump {rel_path} has invalid header (expected PGDMP)."
                )

        total_bytes += actual_size
        verified_items.append(
            {
                "kind": item.get("kind"),
                "path": rel_path,
                "size_bytes": actual_size,
                "sha256": actual_sha,
                "verified": True,
            }
        )

    return {
        "status": "verified",
        "backup_id": manifest.get("backup_id"),
        "created_at": manifest.get("created_at"),
        "alembic_head": manifest.get("alembic_head"),
        "verified_items_count": len(verified_items),
        "total_bytes": total_bytes,
        "items": verified_items,
    }


async def run_backup(
    target: str = "all",
    out_root: Path = ROOT / "backups",
    retention_days: int | None = None,
    retention_keep: int | None = None,
    pg_tool: str = "auto",
    verify_immediately: bool = True,
) -> dict[str, Any]:
    """Execute complete system backup workflow for PostgreSQL and Qdrant."""
    env = load_env_defaults()
    db_dsn = (
        os.environ.get("DATABASE_URL")
        or env.get("DATABASE_URL")
        or "postgresql+asyncpg://qnu:qnu_password_secure_2026@127.0.0.1:5432/qnu_ai_platform"
    )
    qdrant_url = (
        os.environ.get("QDRANT_URL")
        or env.get("QDRANT_URL")
        or "http://127.0.0.1:6333"
    )
    qdrant_api_key = resolve_qdrant_api_key(env)

    now_utc = datetime.datetime.now(datetime.UTC)
    timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")
    backup_id = f"backup_{timestamp_str}"
    current_backup_dir = out_root / timestamp_str
    current_backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== QNU AI Platform · System Backup [{backup_id}] ===")
    print(f"Output directory: {current_backup_dir}")
    print(f"Target scope:     {target}")

    manifest_items: list[dict[str, Any]] = []
    alembic_head = None

    try:
        # 1. PostgreSQL Backup
        if target in {"all", "postgres"}:
            print("\n--- 1. PostgreSQL Backup ---")
            pg_dir = current_backup_dir / "postgres"
            pg_info = await backup_postgres(db_dsn, pg_dir, tool_preference=pg_tool)
            pg_file = Path(pg_info["output_file"])
            alembic_head = pg_info.get("alembic_head")
            manifest_items.append(
                {
                    "kind": "postgres",
                    "path": pg_file.relative_to(current_backup_dir).as_posix(),
                    "tool": pg_info.get("tool"),
                    "format": pg_info.get("format"),
                    "size_bytes": pg_info.get("size_bytes"),
                    "sha256": pg_info.get("sha256"),
                    "table_count": pg_info.get("table_count"),
                    "total_rows": pg_info.get("total_rows"),
                }
            )
            print(
                f"[OK] PostgreSQL backup completed ({pg_info.get('tool')}): "
                f"{pg_info.get('size_bytes', 0):,} bytes | "
                f"{pg_info.get('table_count', 0)} tables | {pg_info.get('total_rows', 0)} rows"
            )

        # 2. Qdrant Backup
        if target in {"all", "qdrant"}:
            print("\n--- 2. Qdrant Snapshot Backup ---")
            qdrant_dir = current_backup_dir / "qdrant"
            qdrant_items = await backup_qdrant_collections(
                qdrant_url, qdrant_dir, api_key=qdrant_api_key
            )
            for item in qdrant_items:
                manifest_items.append(
                    {
                        "kind": "qdrant",
                        "collection": item["collection"],
                        "path": item["snapshot_file"],
                        "size_bytes": item["size_bytes"],
                        "sha256": item["sha256"],
                    }
                )
            print(f"[OK] Qdrant backup completed: {len(qdrant_items)} collections snapshot.")

        # 3. Create Manifest
        manifest = {
            "schema_version": "qnu.system-backup/v1",
            "backup_id": backup_id,
            "created_at": now_utc.isoformat(),
            "target": target,
            "alembic_head": alembic_head,
            "platform_version": "v1",
            "items": manifest_items,
            "status": "completed",
        }
        manifest_file = current_backup_dir / "manifest.json"
        with manifest_file.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Manifest written to: {manifest_file}")

        # 4. Immediate Integrity Verification
        if verify_immediately:
            print("\n--- 3. Verifying Integrity ---")
            report = verify_backup(current_backup_dir)
            print(
                f"[OK] Integrity verification PASSED: {report['verified_items_count']} items verified, "
                f"total {report['total_bytes']:,} bytes."
            )
    except BaseException:
        if not (current_backup_dir / "manifest.json").is_file():
            shutil.rmtree(current_backup_dir, ignore_errors=True)
        raise

    # 5. Apply Retention
    if retention_days is not None or retention_keep is not None:
        print("\n--- 4. Applying Retention Policy ---")
        removed = apply_retention(out_root, retention_days, retention_keep)
        if not removed:
            print("  No expired backups met retention purge criteria.")

    print(f"\n=== BACKUP SUCCESSFUL: {current_backup_dir} ===")
    return {
        "backup_id": backup_id,
        "backup_dir": str(current_backup_dir),
        "manifest": manifest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Unified PostgreSQL and Qdrant Backup for QNU AI Platform"
    )
    parser.add_argument(
        "--target",
        choices=["all", "postgres", "qdrant"],
        default="all",
        help="Target subsystem to backup (default: all)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "backups",
        help="Base directory for storing backups (default: backups/)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help="Purge backups older than N days",
    )
    parser.add_argument(
        "--retention-keep",
        type=int,
        default=None,
        help="Retain only the K newest backups",
    )
    parser.add_argument(
        "--pg-tool",
        choices=["auto", "native", "pg_dump"],
        default="auto",
        help="PostgreSQL export mechanism (default: auto)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip post-backup integrity verification",
    )
    parser.add_argument(
        "--verify-dir",
        type=Path,
        default=None,
        help="Verify an existing backup directory and exit",
    )

    args = parser.parse_args(argv)

    if args.verify_dir:
        target_dir = args.verify_dir
        if not (target_dir / "manifest.json").is_file():
            # If pointing to backups root, pick the latest backup subdirectory
            sub_backups = [
                d for d in target_dir.iterdir()
                if d.is_dir() and (d / "manifest.json").is_file()
            ]
            if not sub_backups:
                print(f"[FAIL] No backups with manifest.json found in {target_dir}", file=sys.stderr)
                return 1
            sub_backups.sort(key=lambda d: d.name, reverse=True)
            target_dir = sub_backups[0]
            print(f"Verifying latest backup found: {target_dir.name}")

        try:
            report = verify_backup(target_dir)
            print(json.dumps(report, indent=2))
            return 0
        except Exception as e:
            print(f"[FAIL] Integrity verification failed: {e}", file=sys.stderr)
            return 1

    try:
        asyncio.run(
            run_backup(
                target=args.target,
                out_root=args.out_dir,
                retention_days=args.retention_days,
                retention_keep=args.retention_keep,
                pg_tool=args.pg_tool,
                verify_immediately=not args.no_verify,
            )
        )
        return 0
    except Exception as e:
        print(f"\n[ERROR] Backup failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
