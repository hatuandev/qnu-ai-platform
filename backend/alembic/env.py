"""Alembic Environment Script — Configured for Async SQLAlchemy & PostgreSQL."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

import sqlalchemy as sa
from alembic.ddl.impl import DefaultImpl
from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, String, Table, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all module models to register on Base.metadata for autogenerate
import app.modules.assistants.models
import app.modules.conversations.models
import app.modules.document_types.models
import app.modules.evaluation.models
import app.modules.knowledge.models
import app.modules.modelops.models
import app.modules.node_catalog.models
import app.modules.ocr.models
import app.modules.tools.models
import app.modules.workflows.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.core.database import Base


# Ensure Alembic creates version_num as VARCHAR(64) to support descriptive revision IDs
def _custom_version_table_impl(
    self: DefaultImpl,
    *,
    version_table: str,
    version_table_schema: str | None,
    version_table_pk: bool,
    **kw: Any,
) -> Table:
    vt = Table(
        version_table,
        MetaData(),
        Column("version_num", String(64), nullable=False),
        schema=version_table_schema,
    )
    if version_table_pk:
        vt.append_constraint(PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc"))
    return vt


DefaultImpl.version_table_impl = _custom_version_table_impl

config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Overwrite sqlalchemy.url with project settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_num_length=64,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    try:
        connection.execute(
            sa.text("ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")
        )
    except Exception:
        pass

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_num_length=64,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
