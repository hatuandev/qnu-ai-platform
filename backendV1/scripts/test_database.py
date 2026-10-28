"""Disposable PostgreSQL test database; never copy application rows or credentials."""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

import asyncpg
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


async def connection(url, database):
    return await asyncpg.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=database,
    )


def main() -> int:
    from qnu.platform.config import get_settings

    url = make_url(get_settings().DATABASE_URL)
    if url.host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Only loopback PostgreSQL is allowed by this test harness.")
    name = "qnu_v1_test_" + uuid.uuid4().hex[:16]
    assert re.fullmatch(r"qnu_v1_test_[0-9a-f]{16}", name)
    runtime = ROOT / "storage" / "context636" / name
    runtime.mkdir(parents=True)
    env = dict(
        os.environ,
        DATABASE_URL=url.set(database=name).render_as_string(hide_password=False),
        TEST_DATABASE_URL=url.set(database=name).render_as_string(hide_password=False),
        ENVIRONMENT="test",
        STORAGE_DRIVER="local",
        LOCAL_STORAGE_PATH=str(runtime / "objects"),
        SECRET_KEY=secrets.token_urlsafe(48),
        PROVIDER_ENCRYPTION_KEY=secrets.token_urlsafe(48),
        DEV_AUTH_ENABLED="true",
        SSO_ENABLED="false",
        PYTHONIOENCODING="utf-8",
    )
    guard = runtime / "guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import socket\n_old=socket.socket.connect\n"
        "def connect(self,address):\n"
        " if isinstance(address,tuple) and address[0] not in {'127.0.0.1','localhost','::1'}:"
        " raise RuntimeError('External test network blocked')\n"
        " return _old(self,address)\nsocket.socket.connect=connect\n",
        encoding="utf-8",
    )
    env["PYTHONPATH"] = str(guard) + os.pathsep + str(ROOT)

    async def prepare():
        admin = await connection(url, "postgres")
        try:
            await admin.execute(f'CREATE DATABASE "{name}"')
        finally:
            await admin.close()
        db = await connection(url, name)
        try:
            await db.execute(
                "CREATE TABLE legacy_sentinel (id integer PRIMARY KEY, value text);"
                "INSERT INTO legacy_sentinel VALUES (1,'preserved');"
                "CREATE TABLE alembic_version (version_num varchar(64) PRIMARY KEY);"
                "INSERT INTO alembic_version VALUES ('legacy_head_preserved');"
            )
        finally:
            await db.close()

    async def cleanup():
        db = await connection(url, name)
        try:
            assert await db.fetchval("SELECT value FROM legacy_sentinel WHERE id=1") == "preserved"
            assert (
                await db.fetchval("SELECT version_num FROM alembic_version")
                == "legacy_head_preserved"
            )
        finally:
            await db.close()
        admin = await connection(url, "postgres")
        try:
            await admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname=$1 AND pid<>pg_backend_pid()",
                name,
            )
            await admin.execute(f'DROP DATABASE "{name}"')
        finally:
            await admin.close()

    started = time.monotonic()
    asyncio.run(prepare())
    receipt = {"database": name, "db_dropped": False, "legacy_sentinel_preserved": False}
    try:
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        (runtime / "migration.log").write_text(
            migration.stdout + migration.stderr, encoding="utf-8"
        )
        if migration.returncode:
            print("Migration failed; see local migration.log.")
            receipt["migration_exit"] = migration.returncode
            return migration.returncode
        args = sys.argv[1:] or ["tests", "-v"]
        command = [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "pytest",
            *args,
            "--basetemp=" + str(runtime / "pytest-temp"),
            "-o",
            "faulthandler_timeout=30",
            "--junitxml=" + str(runtime / "result.xml"),
        ]
        with (runtime / "pytest.log").open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False
            )
        receipt["pytest_exit"] = result.returncode
        print((runtime / "pytest.log").read_text(encoding="utf-8")[-6500:])
        return result.returncode
    finally:
        asyncio.run(cleanup())
        receipt.update(
            db_dropped=True,
            legacy_sentinel_preserved=True,
            seconds=round(time.monotonic() - started, 2),
        )
        (runtime / "receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(receipt))


if __name__ == "__main__":
    raise SystemExit(main())
