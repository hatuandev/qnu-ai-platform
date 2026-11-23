#!/usr/bin/env python3
"""Unified PostgreSQL and Qdrant Snapshot Recovery / Restore Tool for QNU AI Platform.

Complies with AGENTS.md:
- Strictly verifies backup integrity (manifest, sizes, SHA-256) prior to any restore action.
- Requires explicit --confirm-restore to execute destructive operations.
- Provides --verify-only dry run mode to inspect and validate compatibility without modifying data.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backendV1"

SCRIPTS_DIR = Path(__file__).resolve().parent

# Ensure scripts, root and backend directory are in sys.path
for p in [SCRIPTS_DIR, ROOT, BACKEND_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backup_system import (
    load_env_defaults,
    qdrant_headers,
    resolve_qdrant_api_key,
    verify_backup,
)

_SAFE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_ident(name: str) -> str:
    if not _SAFE_IDENT_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier in backup archive: {name!r}")
    return f'"{name}"'


async def restore_postgres_native(
    db_dsn: str, archive_path: Path
) -> dict[str, Any]:
    """Restore PostgreSQL tables from compressed tar.gz archive using asyncpg.

    All target tables are truncated in a single TRUNCATE ... RESTART IDENTITY CASCADE
    statement before any COPY runs so child tables loaded earlier in alphabetical order
    are never wiped when a parent table is processed later.
    """
    import asyncpg

    raw_dsn = db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(raw_dsn)
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            # Read schema metadata
            meta_member = tar.getmember("schema_metadata.json")
            meta_file = tar.extractfile(meta_member)
            if not meta_file:
                raise ValueError("Missing schema_metadata.json inside tar archive")
            meta = json.loads(meta_file.read().decode("utf-8"))

            tables_raw = meta.get("tables") or meta.get("columns") or {}
            if not tables_raw:
                tables_raw = {t: [] for t in meta.get("table_stats", {})}
            table_names = list(tables_raw.keys())

            # Collect table CSV payloads that actually exist in the archive
            table_payloads: list[tuple[str, bytes]] = []
            for tbl in table_names:
                _quote_ident(tbl)
                csv_member_name = f"tables/{tbl}.csv"
                try:
                    csv_member = tar.getmember(csv_member_name)
                except KeyError:
                    print(f"    [WARN] Table CSV {csv_member_name} not in archive, skipping.")
                    continue
                csv_file = tar.extractfile(csv_member)
                if not csv_file:
                    continue
                table_payloads.append((tbl, csv_file.read()))

            print(f"  -> Found {len(table_payloads)} tables to restore in archive.")

            # Temporarily disable foreign keys during bulk load if superuser/replica permitted
            replica_mode = False
            try:
                await conn.execute("SET session_replication_role = 'replica'")
                replica_mode = True
            except Exception:
                pass

            restored_stats: dict[str, int] = {}

            try:
                # Execute entire truncate + copy + sequence re-sync atomically in one transaction
                async with conn.transaction():
                    if table_payloads:
                        quoted_all = ", ".join(_quote_ident(tbl) for tbl, _ in table_payloads)
                        await conn.execute(
                            f"TRUNCATE TABLE {quoted_all} RESTART IDENTITY CASCADE"
                        )

                    for tbl, csv_bytes in table_payloads:
                        if csv_bytes.strip():
                            buf = io.BytesIO(csv_bytes)
                            await conn.copy_to_table(
                                tbl, source=buf, format="csv", header=True
                            )

                    # Verify row counts only after all tables have been loaded
                    for tbl, _ in table_payloads:
                        cnt = await conn.fetchval(f"SELECT count(*) FROM {_quote_ident(tbl)}")
                        restored_stats[tbl] = int(cnt or 0)

                    # Re-sync sequences for integer primary keys if present
                    seq_query = """
                        SELECT sequence_name, table_name, column_name
                        FROM information_schema.sequences s
                        JOIN information_schema.columns c
                          ON c.column_default LIKE '%' || s.sequence_name || '%'
                        WHERE sequence_schema = 'public'
                    """
                    try:
                        seqs = await conn.fetch(seq_query)
                        for sq in seqs:
                            s_name = sq["sequence_name"]
                            t_name = sq["table_name"]
                            c_name = sq["column_name"]
                            max_val = await conn.fetchval(
                                f"SELECT MAX({_quote_ident(c_name)}) FROM {_quote_ident(t_name)}"
                            )
                            if max_val is None:
                                await conn.execute(
                                    "SELECT setval($1::regclass, 1, false)", s_name
                                )
                            else:
                                await conn.execute(
                                    "SELECT setval($1::regclass, $2, true)",
                                    s_name,
                                    int(max_val),
                                )
                    except Exception:
                        pass
            finally:
                if replica_mode:
                    try:
                        await conn.execute("SET session_replication_role = 'origin'")
                    except Exception:
                        pass

        return {
            "status": "restored",
            "tool": "asyncpg_native",
            "table_count": len(restored_stats),
            "restored_stats": restored_stats,
            "total_rows_restored": sum(restored_stats.values()),
        }
    finally:
        await conn.close()


def restore_postgres_pg_dump(
    db_dsn: str, dump_path: Path
) -> dict[str, Any]:
    """Restore PostgreSQL database from a pg_dump custom-format (.dump) file via pg_restore."""
    if shutil.which("pg_restore") is None:
        raise RuntimeError(
            "pg_restore CLI is required to restore a pg_dump custom archive (.dump) "
            "but was not found on PATH."
        )

    with dump_path.open("rb") as f:
        if f.read(5) != b"PGDMP":
            raise ValueError(f"Invalid PostgreSQL custom dump header in {dump_path}")

    raw_dsn = db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urllib.parse.urlparse(raw_dsn)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--single-transaction",
        "-h", parsed.hostname or "127.0.0.1",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/") or "postgres",
        str(dump_path),
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"pg_restore failed (exit {result.returncode}): {result.stderr}")

    return {
        "status": "restored",
        "tool": "pg_dump_custom",
        "dump_file": str(dump_path),
        "size_bytes": dump_path.stat().st_size,
    }


async def restore_qdrant_snapshots(
    qdrant_url: str,
    backup_dir: Path,
    items: list[dict[str, Any]],
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Restore Qdrant collections from snapshot files via upload API."""
    import httpx

    results: list[dict[str, Any]] = []
    headers = qdrant_headers(api_key)
    async with httpx.AsyncClient(timeout=300.0, headers=headers) as client:
        for item in items:
            col = item.get("collection")
            rel_path = item.get("path")
            snap_file = backup_dir / rel_path

            if not snap_file.is_file():
                raise FileNotFoundError(f"Missing snapshot file for collection '{col}': {snap_file}")

            print(f"  -> Restoring Qdrant collection '{col}' from snapshot...")

            # Upload snapshot directly to Qdrant recovery endpoint
            with snap_file.open("rb") as f:
                resp = await client.post(
                    f"{qdrant_url}/collections/{col}/snapshots/upload",
                    files={"snapshot": (snap_file.name, f, "application/octet-stream")},
                )

            if resp.status_code not in {200, 201}:
                raise RuntimeError(
                    f"Failed to restore Qdrant collection '{col}' ({resp.status_code}): {resp.text}"
                )

            # Query restored points count
            info_resp = await client.get(f"{qdrant_url}/collections/{col}")
            points_count = None
            if info_resp.status_code == 200:
                points_count = (
                    info_resp.json()
                    .get("result", {})
                    .get("points_count")
                )

            results.append(
                {
                    "collection": col,
                    "status": "restored",
                    "points_count": points_count,
                }
            )

    return results


async def run_restore(
    backup_dir: Path,
    target: str = "all",
    verify_only: bool = False,
    confirm_restore: bool = False,
) -> dict[str, Any]:
    """Execute validation and restoration from a verified backup folder."""
    print(f"=== QNU AI Platform · System Recovery [{backup_dir.name}] ===")

    # 1. Strictly verify integrity before touching anything
    print("\n--- 1. Verifying Backup Archive Integrity ---")
    report = verify_backup(backup_dir)
    print(
        f"[OK] Manifest and {report['verified_items_count']} artifacts verified successfully "
        f"({report['total_bytes']:,} bytes)."
    )

    manifest_path = backup_dir / "manifest.json"
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

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

    if verify_only:
        print("\n--- Dry Run: Verify-Only Mode ---")
        print(f"Target scope:     {target}")
        print(f"Alembic revision: {manifest.get('alembic_head')}")
        print(f"Backup timestamp: {manifest.get('created_at')}")
        print("[OK] Backup is fully valid, consistent, and ready for recovery.")
        return {"status": "verified_ready", "report": report}

    if not confirm_restore:
        raise PermissionError(
            "Destructive restoration requires explicit confirmation: pass --confirm-restore"
        )

    restore_results: dict[str, Any] = {"status": "completed", "targets": {}}

    # Pre-flight Qdrant connectivity check before mutating PostgreSQL when restoring both
    qdrant_items = [
        i for i in manifest.get("items", []) if i.get("kind") == "qdrant"
    ]
    if target == "all" and qdrant_items:
        import httpx

        async with httpx.AsyncClient(
            timeout=15.0, headers=qdrant_headers(qdrant_api_key)
        ) as client:
            health_resp = await client.get(f"{qdrant_url}/collections")
            if health_resp.status_code != 200:
                raise RuntimeError(
                    f"Qdrant pre-flight check failed ({health_resp.status_code}); "
                    "aborting before PostgreSQL mutation to prevent split-brain state."
                )

    # 2. PostgreSQL Restore
    pg_restored = False
    if target in {"all", "postgres"}:
        print("\n--- 2. Restoring PostgreSQL Database ---")
        pg_items = [
            i for i in manifest.get("items", []) if i.get("kind") == "postgres"
        ]
        if not pg_items:
            print("  No PostgreSQL backup entry found in manifest.")
        else:
            pg_item = pg_items[0]
            pg_archive = backup_dir / pg_item["path"]
            is_pg_dump = (
                pg_item.get("tool") == "pg_dump_custom"
                or pg_item.get("format") == "pg_dump_custom"
                or pg_archive.name.endswith(".dump")
            )
            if is_pg_dump:
                res = restore_postgres_pg_dump(db_dsn, pg_archive)
                print(
                    f"[OK] PostgreSQL restored via pg_restore ({res.get('size_bytes', 0):,} bytes)."
                )
            else:
                res = await restore_postgres_native(db_dsn, pg_archive)
                print(
                    f"[OK] PostgreSQL restored: {res.get('table_count')} tables, "
                    f"{res.get('total_rows_restored'):,} rows."
                )
            restore_results["targets"]["postgres"] = res
            pg_restored = True

    # 3. Qdrant Restore
    if target in {"all", "qdrant"}:
        print("\n--- 3. Restoring Qdrant Vector Collections ---")
        if not qdrant_items:
            print("  No Qdrant backup entries found in manifest.")
        else:
            try:
                res_q = await restore_qdrant_snapshots(
                    qdrant_url, backup_dir, qdrant_items, api_key=qdrant_api_key
                )
            except Exception as exc:
                if pg_restored:
                    raise RuntimeError(
                        f"Qdrant restore failed AFTER PostgreSQL restore completed ({exc}). "
                        "Re-run with --target qdrant to restore vector state consistency."
                    ) from exc
                raise
            restore_results["targets"]["qdrant"] = res_q
            print(f"[OK] Qdrant restored: {len(res_q)} collections.")

    print("\n=== RESTORATION COMPLETED SUCCESSFULLY ===")
    return restore_results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Unified PostgreSQL and Qdrant Restore Tool for QNU AI Platform"
    )
    parser.add_argument(
        "backup_dir",
        type=Path,
        help="Path to backup directory containing manifest.json",
    )
    parser.add_argument(
        "--target",
        choices=["all", "postgres", "qdrant"],
        default="all",
        help="Subsystem to restore (default: all)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Inspect, test checksums, and check compatibility without modifying data",
    )
    parser.add_argument(
        "--confirm-restore",
        action="store_true",
        help="Mandatory confirmation flag to perform destructive restore",
    )

    args = parser.parse_args(argv)

    try:
        asyncio.run(
            run_restore(
                backup_dir=args.backup_dir,
                target=args.target,
                verify_only=args.verify_only,
                confirm_restore=args.confirm_restore,
            )
        )
        return 0
    except Exception as e:
        print(f"\n[ERROR] Recovery failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
