"""Alembic environment for backendV1.

backendV1 owns a separate version table so two migration chains can coexist on
one database. It never stamps or rewrites the legacy chain.
"""

from __future__ import annotations

from logging import getLogger
from logging.config import fileConfig
from pathlib import Path

from alembic.migration import MigrationContext
from sqlalchemy import inspect, pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from qnu.domains.answer_review import models as _answer_review_models  # noqa: F401
from qnu.domains.assistants import models as _assistant_models  # noqa: F401
from qnu.domains.conversations import models as _conversation_models  # noqa: F401
from qnu.domains.knowledge import models as _knowledge_models  # noqa: F401 - register tables
from qnu.domains.knowledge.compilation import models as _compilation_models  # noqa: F401
from qnu.domains.knowledge.compilation.review import models as _review_models  # noqa: F401
from qnu.domains.knowledge.compilation.workflow import models as _workflow_models  # noqa: F401
from qnu.domains.knowledge.index import models as _index_models  # noqa: F401
from qnu.domains.knowledge.preparation import models as _preparation_models  # noqa: F401
from qnu.domains.knowledge.publication import models as _publication_models  # noqa: F401
from qnu.domains.knowledge.review import models as _review_submission_models  # noqa: F401
from qnu.domains.lifecycle import models as _lifecycle_models  # noqa: F401
from qnu.domains.modelops import models as _modelops_models  # noqa: F401 - register tables
from qnu.domains.ocr import models as _ocr_models  # noqa: F401 - register tables
from qnu.domains.ocr.review import defaults as _spelling_defaults  # noqa: F401
from qnu.domains.ocr.review import models as _ocr_review_models  # noqa: F401
from qnu.domains.operations import models as _operations_models  # noqa: F401
from qnu.domains.publications import models as _publication_release_models  # noqa: F401
from qnu.domains.workspaces import models as _workspace_models  # noqa: F401 - register tables
from qnu.platform.config import get_settings
from qnu.platform.database import Base
from qnu.platform.ownership import include_object

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

VERSION_TABLE = "alembic_version_backendv1"
BASELINE_REVISION = "0031_spelling_defaults"
BOOTSTRAP_TAG = "qnu-bootstrap"
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)
target_metadata = Base.metadata
log = getLogger("alembic.runtime.migration")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def ensure_version_table_width(connection: Connection) -> None:
    """Revision ids (e.g. 0028_drop_index_system_default_authorized) exceed the
    VARCHAR(32) Alembic creates by default for the version table."""
    connection.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {VERSION_TABLE} "
            "(version_num VARCHAR(64) NOT NULL PRIMARY KEY)"
        )
    )
    connection.execute(
        text(f"ALTER TABLE {VERSION_TABLE} ALTER COLUMN version_num TYPE VARCHAR(64)")
    )


def bootstrap_empty_v1(connection: Connection, migration: MigrationContext) -> None:
    scripts = context.script
    if (
        context.get_tag_argument() != BOOTSTRAP_TAG
        or migration.opts["destination_rev"] != "head"
        or migration.get_current_heads()
        or connection.scalar(text("SELECT current_schema()")) != "public"
    ):
        return
    if not any(revision.revision == BASELINE_REVISION for revision in scripts.walk_revisions()):
        return

    initial = scripts.get_revision("0001_initial_schema")
    owned = set(initial.module.V1_OWNED) | set(target_metadata.tables)
    existing = owned.intersection(inspect(connection).get_table_names(schema="public"))
    if existing:
        raise RuntimeError(
            "V1 tables already exist outside the migration history; no automatic adoption: "
            + ", ".join(sorted(existing))
        )

    ddl = (Path(__file__).with_name("baselines") / f"{BASELINE_REVISION}.sql").read_text(
        encoding="utf-8"
    )
    # asyncpg can execute the whole frozen script on the migration's existing transaction.
    connection.connection.run_async(lambda driver: driver.execute(ddl))
    migration.stamp(scripts, BASELINE_REVISION)
    log.info("Initialized empty V1 schema at %s", BASELINE_REVISION)


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
        compare_type=True,
        include_object=include_object,
    )
    migration = context.get_context()
    if "destination_rev" in migration.opts:
        connection.execute(text("SELECT pg_advisory_xact_lock(1367258177)"))
        ensure_version_table_width(connection)
        bootstrap_empty_v1(connection, migration)
    else:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        migration.opts["dont_mutate"] = True
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        async with connectable.begin() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
