"""Run migration diagnostics only in newly created, isolated Docker resources."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path

PG_IMAGE = (
    "postgres:16-bookworm@sha256:0ea6700a3b4f0ae6ce746519073558aed4d88a79d8d07622a9a644946c7319c4"
)
APP_IMAGE = "qnu-deployment-check:456-backend"
PROBE = r'''
import asyncio
import json
import os

import asyncpg
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.config import Config
from alembic.script import ScriptDirectory

import app.modules.assistants.models
import app.modules.conversations.models
import app.modules.document_types.models
import app.modules.documents.models
import app.modules.evaluation.models
import app.modules.knowledge.models
import app.modules.modelops.models
import app.modules.node_catalog.models
import app.modules.ocr.models
import app.modules.tools.models
import app.modules.workflows.models
from app.core.database import Base

ROOT_URL = "postgresql://postgres:migration_probe_only@postgres:5432/"
ASYNC_URL = "postgresql+asyncpg://postgres:migration_probe_only@postgres:5432/"

async def migrate(name, revision):
    environment = dict(os.environ, DATABASE_URL=ASYNC_URL+name)
    process = await asyncio.create_subprocess_exec(
        "alembic", "upgrade", revision, env=environment,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=90)
    return {"exit": process.returncode, "log_tail": (stdout+stderr).decode("utf-8", errors="replace")[-5000:]}

async def schema(name):
    engine = create_async_engine(ASYNC_URL+name)
    async with engine.connect() as connection:
        def compare(sync):
            inspector = inspect(sync)
            present = set(inspector.get_table_names())
            missing_tables = sorted(set(Base.metadata.tables)-present)
            missing_columns = {}
            for table_name, table in Base.metadata.tables.items():
                if table_name in present:
                    actual = {c["name"] for c in inspector.get_columns(table_name)}
                    missing = sorted(set(table.columns.keys())-actual)
                    if missing:
                        missing_columns[table_name] = missing
            return {"table_count": len(present), "missing_tables": missing_tables, "missing_columns": missing_columns}
        result = await connection.run_sync(compare)
    await engine.dispose()
    return result

async def main():
    admin = await asyncpg.connect(ROOT_URL+"postgres")
    config = Config("/app/alembic.ini")
    scripts = ScriptDirectory.from_config(config)
    report = {"heads": scripts.get_heads(), "revision_count": len(list(scripts.walk_revisions())), "cases": []}
    for name in ("probe_empty", "probe_old", "probe_other_version", "probe_collision"):
        await admin.execute('CREATE DATABASE "'+name+'"')
        connection = await asyncpg.connect(ROOT_URL+name)
        await connection.execute("CREATE TABLE external_app_sentinel(id integer PRIMARY KEY, value text NOT NULL)")
        await connection.execute("INSERT INTO external_app_sentinel VALUES(1, 'keep_other_app_data')")
        await connection.close()
        case = {"case": name}
        if name == "probe_old":
            case["baseline"] = await migrate(name, "20260926_reconcile_core_schema")
            if case["baseline"]["exit"] == 0:
                connection = await asyncpg.connect(ROOT_URL+name)
                await connection.execute("""INSERT INTO model_provider_configs
                    (id, name, provider_type, priority, timeout_seconds, is_active, extra_config, created_at, updated_at)
                    VALUES ('probe_provider_458', 'migration sentinel', 'custom',
                    1, 15, true, '{}'::jsonb, now(), now())""")
                await connection.close()
        if name == "probe_other_version":
            connection = await asyncpg.connect(ROOT_URL+name)
            await connection.execute("CREATE TABLE alembic_version(version_num varchar(64) PRIMARY KEY)")
            await connection.execute("INSERT INTO alembic_version VALUES('other_application_revision_458')")
            await connection.close()
        if name == "probe_collision":
            connection = await asyncpg.connect(ROOT_URL+name)
            await connection.execute("CREATE TABLE assistants(other_app_id integer PRIMARY KEY, content text)")
            await connection.execute("INSERT INTO assistants VALUES(1, 'other_application_owned_table')")
            await connection.close()
        case["upgrade"] = await migrate(name, "head")
        connection = await asyncpg.connect(ROOT_URL+name)
        case["external_sentinel"] = await connection.fetchval("SELECT value FROM external_app_sentinel WHERE id=1")
        if await connection.fetchval("SELECT to_regclass('public.alembic_version') IS NOT NULL"):
            case["version"] = await connection.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
        if name == "probe_old" and case["baseline"]["exit"] == 0:
            case["provider_sentinel"] = await connection.fetchval("SELECT name FROM model_provider_configs WHERE id='probe_provider_458'")
        if name == "probe_collision":
            case["collision_sentinel"] = await connection.fetchval("SELECT content FROM assistants WHERE other_app_id=1")
        await connection.close()
        if case["upgrade"]["exit"] == 0:
            case["schema"] = await schema(name)
            case["repeat_upgrade"] = await migrate(name, "head")
        report["cases"].append(case)
    await admin.close()
    print(json.dumps(report, ensure_ascii=False))

asyncio.run(main())
'''


def docker(
    *args: str, input_text: str | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=420,
        check=check,
    )


def main() -> None:
    suffix = uuid.uuid4().hex[:10]
    network = f"qnu-migration458-{suffix}"
    postgres = f"{network}-pg"
    app = f"{network}-app"
    created_network = False
    try:
        docker("network", "create", "--internal", "--label", "qnu.audit=458", network)
        created_network = True
        docker(
            "run",
            "--rm",
            "-d",
            "--name",
            postgres,
            "--label",
            "qnu.audit=458",
            "--network",
            network,
            "--network-alias",
            "postgres",
            "--tmpfs",
            "/var/lib/postgresql/data",
            "-e",
            "POSTGRES_PASSWORD=migration_probe_only",
            PG_IMAGE,
        )
        for _ in range(40):
            if (
                docker("exec", postgres, "pg_isready", "-U", "postgres", check=False).returncode
                == 0
            ):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Disposable PostgreSQL did not become ready")
        result = docker(
            "run",
            "--rm",
            "-i",
            "--name",
            app,
            "--label",
            "qnu.audit=458",
            "--network",
            network,
            "--no-healthcheck",
            "--entrypoint",
            "python",
            "-e",
            "ENVIRONMENT=production",
            "-e",
            "DEV_AUTH_ENABLED=false",
            "-e",
            "DEV_ACCESS_PASSWORD=",
            "-e",
            "SSO_AUTHORITY=https://identity.example.test",
            "-e",
            "SECRET_KEY=migration-test-only",
            "-e",
            "PROVIDER_ENCRYPTION_KEY=migration-test-only",
            "-e",
            "INTERNAL_API_KEY=migration-test-only",
            "-e",
            "S3_SECRET_KEY=migration-test-only",
            "-e",
            "QDRANT_URL=http://127.0.0.1:9",
            "-e",
            "DATABASE_URL=postgresql+asyncpg://postgres:migration_probe_only@postgres:5432/postgres",
            APP_IMAGE,
            "-",
            input_text=PROBE,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr[-5000:] + result.stdout[-5000:])
        report = json.loads(result.stdout)
        destination = Path(__file__).resolve().parents[1] / "storage/migration_audit458.json"
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Report: {destination}")
        for case in report["cases"]:
            print(case["case"], "upgrade_exit=", case["upgrade"]["exit"], case.get("schema", {}))
    finally:
        for name in (app, postgres):
            record = docker(
                "inspect", name, "--format", '{{index .Config.Labels "qnu.audit"}}', check=False
            )
            if record.returncode == 0 and record.stdout.strip() == "458":
                docker("rm", "-f", name, check=False)
        if created_network:
            docker("network", "rm", network, check=False)


if __name__ == "__main__":
    main()
