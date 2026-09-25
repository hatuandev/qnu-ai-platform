"""Tests for CLI database migrate fail-loud verification (phiên #226)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.cli import run_db_migrate


def _patch_migrate_env(
    upgrade_side_effect=None,
    schema_ok: bool = True,
):
    upgrade_mock = MagicMock(side_effect=upgrade_side_effect)
    command_mock = MagicMock()
    command_mock.upgrade = upgrade_mock
    return (
        patch("app.cli.command", command_mock),
        patch(
            "app.cli.ensure_postgres_database_exists",
            new_callable=AsyncMock,
        ),
        patch("app.cli.check_db_schema", new_callable=AsyncMock, return_value=schema_ok),
    )


def test_run_db_migrate_succeeds_when_schema_verified():
    """Happy path: upgrade runs and post-migration check passes."""
    patches = _patch_migrate_env(schema_ok=True)
    for p in patches:
        p.start()
    try:
        assert run_db_migrate() == 0
    finally:
        for p in patches:
            p.stop()


def test_run_db_migrate_fails_loud_when_tables_missing():
    """Silent no-op upgrades must NOT exit 0: missing core tables fail the migrate step."""
    patches = _patch_migrate_env(schema_ok=False)
    for p in patches:
        p.start()
    try:
        assert run_db_migrate() == 1
    finally:
        for p in patches:
            p.stop()


def test_run_db_migrate_fails_when_upgrade_raises():
    """Upgrade exceptions keep failing loudly (existing behavior preserved)."""
    patches = _patch_migrate_env(
        upgrade_side_effect=RuntimeError("alembic boom"), schema_ok=True
    )
    for p in patches:
        p.start()
    try:
        assert run_db_migrate() == 1
    finally:
        for p in patches:
            p.stop()
