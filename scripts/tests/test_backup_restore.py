"""Unit tests for Unified PostgreSQL & Qdrant Backup and Recovery tools.

Ensures:
- Deterministic SHA-256 calculation.
- Retention policy handles age thresholds and keep counts accurately.
- Integrity verification detects missing files, modified contents, and corrupt archives.
- Restore safety gates prevent accidental restoration without confirmation.
"""

from __future__ import annotations

import datetime
import io
import json
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"

for p in [SCRIPTS_DIR, ROOT, ROOT / "backendV1"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backup_system import (
    apply_retention,
    compute_bytes_sha256,
    compute_sha256,
    verify_backup,
)
from restore_system import run_restore


class BackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="qnu_test_backup_")
        self.root_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compute_sha256(self):
        test_file = self.root_path / "test.txt"
        test_file.write_bytes(b"hello world QNU AI Platform 2026")
        expected = compute_bytes_sha256(b"hello world QNU AI Platform 2026")
        self.assertEqual(compute_sha256(test_file), expected)

    def _create_mock_backup(self, backup_dir: Path, corrupt_file: bool = False) -> Path:
        backup_dir.mkdir(parents=True, exist_ok=True)
        pg_dir = backup_dir / "postgres"
        pg_dir.mkdir(parents=True, exist_ok=True)
        pg_tar = pg_dir / "database_dump.tar.gz"

        # Create valid tar.gz
        with tarfile.open(pg_tar, "w:gz") as tar:
            content = b"col1,col2\nval1,val2\n"
            info = tarfile.TarInfo(name="tables/sample_table.csv")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))

            meta = json.dumps({"schema_version": "qnu.postgres-dump/v1", "tables": {}}).encode("utf-8")
            meta_info = tarfile.TarInfo(name="schema_metadata.json")
            meta_info.size = len(meta)
            tar.addfile(meta_info, io.BytesIO(meta))

        qdrant_dir = backup_dir / "qdrant"
        qdrant_dir.mkdir(parents=True, exist_ok=True)
        qdrant_snap = qdrant_dir / "test_col.snapshot"
        qdrant_snap.write_bytes(b"mock snapshot data bytes" * 10)

        pg_sha = compute_sha256(pg_tar)
        qdrant_sha = compute_sha256(qdrant_snap)

        manifest = {
            "schema_version": "qnu.system-backup/v1",
            "backup_id": f"backup_{backup_dir.name}",
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "target": "all",
            "alembic_head": "0040_test_rev",
            "platform_version": "v1",
            "items": [
                {
                    "kind": "postgres",
                    "path": "postgres/database_dump.tar.gz",
                    "size_bytes": pg_tar.stat().st_size,
                    "sha256": pg_sha,
                },
                {
                    "kind": "qdrant",
                    "collection": "test_col",
                    "path": "qdrant/test_col.snapshot",
                    "size_bytes": qdrant_snap.stat().st_size,
                    "sha256": qdrant_sha,
                },
            ],
            "status": "completed",
        }

        if corrupt_file:
            # Corrupt qdrant file after manifest calculation
            qdrant_snap.write_bytes(b"corrupted contents")

        manifest_file = backup_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return backup_dir

    def test_verify_backup_passes_for_intact_archive(self):
        backup_dir = self.root_path / "20261122_120000"
        self._create_mock_backup(backup_dir, corrupt_file=False)

        report = verify_backup(backup_dir)
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["verified_items_count"], 2)
        self.assertTrue(report["total_bytes"] > 0)

    def test_verify_backup_fails_on_corrupted_checksum(self):
        backup_dir = self.root_path / "20261122_120001"
        self._create_mock_backup(backup_dir, corrupt_file=True)

        with self.assertRaises(ValueError) as ctx:
            verify_backup(backup_dir)
        self.assertIn("mismatch", str(ctx.exception).lower())

    def test_verify_backup_fails_on_missing_file(self):
        backup_dir = self.root_path / "20261122_120002"
        self._create_mock_backup(backup_dir, corrupt_file=False)

        # Remove postgres tar
        (backup_dir / "postgres" / "database_dump.tar.gz").unlink()

        with self.assertRaises(FileNotFoundError):
            verify_backup(backup_dir)

    def test_apply_retention_by_keep_count(self):
        # Create 5 mock backups
        for i in range(5):
            d = self.root_path / f"20261122_12000{i}"
            self._create_mock_backup(d)

        # Keep top 2
        removed = apply_retention(self.root_path, retention_days=None, retention_keep=2)
        self.assertEqual(len(removed), 3)

        remaining = [
            d for d in self.root_path.iterdir()
            if d.is_dir() and (d / "manifest.json").is_file()
        ]
        self.assertEqual(len(remaining), 2)

    def test_apply_retention_preserves_non_backup_directories(self):
        non_backup = self.root_path / "custom_folder"
        non_backup.mkdir()
        (non_backup / "notes.txt").write_text("should not be deleted", encoding="utf-8")

        for i in range(3):
            d = self.root_path / f"20261122_13000{i}"
            self._create_mock_backup(d)

        removed = apply_retention(self.root_path, retention_days=None, retention_keep=1)
        self.assertEqual(len(removed), 2)
        self.assertTrue(non_backup.is_dir())
        self.assertTrue((non_backup / "notes.txt").is_file())

    def test_restore_requires_confirmation_flag(self):
        backup_dir = self.root_path / "20261122_140000"
        self._create_mock_backup(backup_dir, corrupt_file=False)

        import asyncio

        # Running without confirm_restore and without verify_only must raise PermissionError
        with self.assertRaises(PermissionError) as ctx:
            asyncio.run(run_restore(backup_dir, confirm_restore=False, verify_only=False))
        self.assertIn("--confirm-restore", str(ctx.exception))

    def test_restore_verify_only_succeeds_without_modifying_data(self):
        backup_dir = self.root_path / "20261122_140001"
        self._create_mock_backup(backup_dir, corrupt_file=False)

        import asyncio

        result = asyncio.run(run_restore(backup_dir, verify_only=True))
        self.assertEqual(result["status"], "verified_ready")

    def test_verify_backup_supports_pg_dump_custom_and_rejects_bad_magic(self):
        backup_dir = self.root_path / "20261122_140002"
        pg_dir = backup_dir / "postgres"
        pg_dir.mkdir(parents=True, exist_ok=True)
        dump_file = pg_dir / "database_dump.dump"
        dump_file.write_bytes(b"PGDMP\x01\x0e\x00dummy_custom_dump")

        manifest = {
            "schema_version": "qnu.system-backup/v1",
            "backup_id": "backup_pg_dump",
            "created_at": "2026-11-22T14:00:02+00:00",
            "target": "postgres",
            "alembic_head": None,
            "items": [
                {
                    "kind": "postgres",
                    "path": "postgres/database_dump.dump",
                    "tool": "pg_dump_custom",
                    "format": "pg_dump_custom",
                    "size_bytes": dump_file.stat().st_size,
                    "sha256": compute_sha256(dump_file),
                }
            ],
        }
        (backup_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        report = verify_backup(backup_dir)
        self.assertEqual(report["status"], "verified")

        # Corrupt magic bytes while updating sha256/size to test PGDMP header check
        dump_file.write_bytes(b"NOTPG_bad_header")
        manifest["items"][0]["size_bytes"] = dump_file.stat().st_size
        manifest["items"][0]["sha256"] = compute_sha256(dump_file)
        (backup_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            verify_backup(backup_dir)
        self.assertIn("PGDMP", str(ctx.exception))

    def test_restore_postgres_native_truncates_all_tables_once_before_copy(self):
        import asyncio
        from unittest.mock import patch

        from restore_system import restore_postgres_native

        archive_path = self.root_path / "native.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            meta = json.dumps(
                {
                    "schema_version": "qnu.postgres-dump/v1",
                    "table_stats": {"a_child": 1, "b_parent": 1},
                }
            ).encode("utf-8")
            mi = tarfile.TarInfo("schema_metadata.json")
            mi.size = len(meta)
            tar.addfile(mi, io.BytesIO(meta))

            for tbl, body in [
                ("a_child", b"id,parent_id\n1,10\n"),
                ("b_parent", b"id\n10\n"),
            ]:
                ci = tarfile.TarInfo(f"tables/{tbl}.csv")
                ci.size = len(body)
                tar.addfile(ci, io.BytesIO(body))

        executed_sql: list[str] = []
        copied_tables: list[str] = []

        class FakeTx:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class FakeConn:
            def transaction(self):
                return FakeTx()

            async def execute(self, sql: str, *args):
                executed_sql.append(sql)

            async def copy_to_table(self, tbl: str, source, format: str, header: bool):
                copied_tables.append(tbl)

            async def fetchval(self, sql: str):
                return 1

            async def fetch(self, sql: str):
                return []

            async def close(self):
                pass

        async def fake_connect(dsn: str):
            return FakeConn()

        with patch("asyncpg.connect", side_effect=fake_connect):
            res = asyncio.run(restore_postgres_native("postgresql://u:p@127.0.0.1/db", archive_path))

        truncates = [s for s in executed_sql if s.startswith("TRUNCATE TABLE")]
        self.assertEqual(len(truncates), 1)
        self.assertIn('"a_child"', truncates[0])
        self.assertIn('"b_parent"', truncates[0])
        self.assertEqual(copied_tables, ["a_child", "b_parent"])
        self.assertEqual(res["table_count"], 2)
        self.assertEqual(res["total_rows_restored"], 2)

    def test_qdrant_headers_include_api_key_when_configured(self):
        from backup_system import qdrant_headers

        self.assertEqual(qdrant_headers(None), {})
        self.assertEqual(qdrant_headers(""), {})
        self.assertEqual(qdrant_headers("secret-qdrant-key"), {"api-key": "secret-qdrant-key"})


if __name__ == "__main__":
    unittest.main()
