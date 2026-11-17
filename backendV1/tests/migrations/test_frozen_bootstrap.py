"""Exercise the migration launcher on disposable loopback PostgreSQL databases."""

import os
import re
import subprocess
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url

from qnu.platform.schema import SCHEMA_HEAD
from scripts.test_database import connection

BOOTSTRAP = ("upgrade", "head", "--tag", "qnu-bootstrap")


@asynccontextmanager
async def empty_database():
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("Isolated PostgreSQL test database not configured")
    url = make_url(test_url)
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    assert re.fullmatch(r"qnu_v1_test_[0-9a-f]{16}", url.database or "")
    name = f"qnu_v1_test_{uuid4().hex[:16]}"
    admin = await connection(url, "postgres")
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        try:
            db = await connection(url, name)
            try:
                yield db, url.set(database=name).render_as_string(hide_password=False)
            finally:
                await db.close()
        finally:
            await admin.execute(f'DROP DATABASE "{name}"')
    finally:
        await admin.close()


def alembic(url, *args):
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        env=dict(os.environ, DATABASE_URL=url),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


@pytest.mark.asyncio
async def test_check_does_not_create_or_widen_the_version_table():
    async with empty_database() as (db, url):
        result = alembic(url, "current")
        assert result.returncode == 0, result.stderr
        assert await db.fetchval("SELECT to_regclass('alembic_version_backendv1')") is None

        await db.execute(
            "CREATE TABLE alembic_version_backendv1 (version_num varchar(32) PRIMARY KEY);"
            "INSERT INTO alembic_version_backendv1 VALUES ('0001_initial_schema')"
        )
        result = alembic(url, "current")
        assert result.returncode == 0, result.stderr
        assert "0001_initial_schema" in result.stdout
        assert (
            await db.fetchval(
                "SELECT character_maximum_length FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='alembic_version_backendv1' "
                "AND column_name='version_num'"
            )
            == 32
        )


@pytest.mark.asyncio
async def test_bootstrap_is_atomic_and_preserves_legacy():
    async with empty_database() as (db, url):
        await db.execute(
            "CREATE TABLE legacy_sentinel (id int, value text);"
            "INSERT INTO legacy_sentinel VALUES (1, 'preserved');"
            "CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY);"
            "INSERT INTO alembic_version VALUES ('legacy_head');"
            "CREATE TABLE ocr_spelling_defaults (id int)"
        )
        result = alembic(url, *BOOTSTRAP)
        assert result.returncode != 0
        assert "no automatic adoption" in result.stderr
        assert await db.fetchval("SELECT to_regclass('alembic_version_backendv1')") is None
        await db.execute(
            "DROP TABLE ocr_spelling_defaults;"
            "CREATE INDEX ix_app_api_keys_app_id ON legacy_sentinel (id)"
        )
        result = alembic(url, *BOOTSTRAP)
        assert result.returncode != 0
        assert "ix_app_api_keys_app_id" in result.stderr
        assert await db.fetchval("SELECT to_regclass('app_api_keys')") is None
        assert await db.fetchval("SELECT to_regclass('alembic_version_backendv1')") is None
        await db.execute("DROP INDEX ix_app_api_keys_app_id")

        result = alembic(url, *BOOTSTRAP)
        assert result.returncode == 0, result.stderr
        assert "Initialized empty V1 schema" in result.stderr
        result = alembic(url, *BOOTSTRAP)
        assert result.returncode == 0, result.stderr
        assert "Initialized empty V1 schema" not in result.stderr
        assert await db.fetchval("SELECT version_num FROM alembic_version_backendv1") == SCHEMA_HEAD
        assert await db.fetchval("SELECT version_num FROM alembic_version") == "legacy_head"
        assert await db.fetchval("SELECT value FROM legacy_sentinel") == "preserved"


@pytest.mark.asyncio
async def test_bootstrap_command_upgrades_versioned_data_with_historical_migration():
    async with empty_database() as (db, url):
        result = alembic(url, "upgrade", "0004_application_api_keys")
        assert result.returncode == 0, result.stderr
        await db.execute(
            "INSERT INTO providers (id, name, provider_type, base_url, model_name) "
            "VALUES ('existing-model', 'Existing model', 'openai_compatible', "
            "'https://example.invalid/v1', 'test-model');"
            "INSERT INTO provider_keys (id, provider_id, name, secret_encrypted, masked_hint) "
            "VALUES ('existing-key', 'existing-model', 'Test key', 'test-ciphertext', 'test')"
        )
        result = alembic(url, *BOOTSTRAP)
        assert result.returncode == 0, result.stderr
        assert "0005_provider_connections" in result.stderr
        assert "Initialized empty V1 schema" not in result.stderr
        assert await db.fetchval("SELECT version_num FROM alembic_version_backendv1") == SCHEMA_HEAD
        assert (
            await db.fetchval(
                "SELECT p.is_connection AND k.model_ids = '[\"existing-model\"]'::jsonb "
                "AND k.secret_encrypted = 'test-ciphertext' "
                "FROM providers p JOIN providers m ON m.parent_id=p.id "
                "JOIN provider_keys k ON k.provider_id=p.id "
                "WHERE m.id='existing-model' AND k.id='existing-key'"
            )
            is True
        )
