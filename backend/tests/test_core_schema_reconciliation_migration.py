"""Regression tests for the forward-only core schema reconciliation migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa


def _load_migration_module() -> ModuleType:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260926_reconcile_core_schema.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_reconcile_core_schema_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_table_is_created_without_touching_existing_tables() -> None:
    module = _load_migration_module()
    delegate = MagicMock()
    delegate.create_table.return_value = "created"
    inspector = MagicMock()
    inspector.has_table.return_value = False

    with patch.object(module.sa, "inspect", return_value=inspector):
        reconciler = module._SchemaReconciler(delegate)
        result = reconciler.create_table(
            "assistants",
            sa.Column("id", sa.String(36), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    assert result == "created"
    delegate.create_table.assert_called_once()


def test_compatible_existing_table_is_preserved() -> None:
    module = _load_migration_module()
    delegate = MagicMock()
    inspector = MagicMock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{"name": "id", "type": sa.String(36), "nullable": False}]
    inspector.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
    inspector.get_foreign_keys.return_value = []

    with patch.object(module.sa, "inspect", return_value=inspector):
        reconciler = module._SchemaReconciler(delegate)
        result = reconciler.create_table(
            "assistants",
            sa.Column("id", sa.String(36), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    assert result is None
    delegate.create_table.assert_not_called()
    delegate.create_foreign_key.assert_not_called()


def test_incompatible_existing_table_fails_without_mutation() -> None:
    module = _load_migration_module()
    delegate = MagicMock()
    inspector = MagicMock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = []

    with (
        patch.object(module.sa, "inspect", return_value=inspector),
        pytest.raises(RuntimeError, match="missing required columns: id"),
    ):
        module._SchemaReconciler(delegate).create_table(
            "assistants",
            sa.Column("id", sa.String(36), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    delegate.create_table.assert_not_called()


def test_missing_index_is_added_and_conflicting_index_fails() -> None:
    module = _load_migration_module()
    delegate = MagicMock()
    inspector = MagicMock()
    inspector.get_indexes.return_value = []

    with patch.object(module.sa, "inspect", return_value=inspector):
        reconciler = module._SchemaReconciler(delegate)
        reconciler.create_index(
            "ix_assistants_code",
            "assistants",
            ["code"],
            unique=True,
        )

    delegate.create_index.assert_called_once_with(
        "ix_assistants_code",
        "assistants",
        ["code"],
        unique=True,
    )

    inspector.get_indexes.return_value = [
        {
            "name": "ix_assistants_code",
            "column_names": ["name"],
            "unique": False,
        }
    ]
    with (
        patch.object(module.sa, "inspect", return_value=inspector),
        pytest.raises(RuntimeError, match="Existing index 'ix_assistants_code'"),
    ):
        reconciler.create_index(
            "ix_assistants_code",
            "assistants",
            ["code"],
            unique=True,
        )


def test_reconciliation_downgrade_is_blocked() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="forward-only"):
        module.downgrade()
