"""PostgreSQL restore drill in an isolated schema rolled back in full."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.backups import configuration_seed as seed


@pytest.mark.asyncio
async def test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import():
    engine = create_async_engine(settings.DATABASE_URL)
    schema = f"config_drill_{uuid4().hex}"
    try:
        async with engine.connect() as conn:
            outer = await conn.begin()
            try:
                # Fixed prefix + hex UUID, transactional DDL; never delete or alter app tables.
                await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
                metadata = MetaData(schema=schema)
                tables = {
                    "model_provider_configs": Table("model_provider_configs", metadata,
                        Column("id", String, primary_key=True), Column("extra_config", JSONB)),
                    "knowledge_collections": Table("knowledge_collections", metadata,
                        Column("id", String, primary_key=True), Column("index_epoch", Integer), Column("collection_metadata", JSONB)),
                    "assistants": Table("assistants", metadata, Column("id", String, primary_key=True),
                        Column("system_prompt", String), Column("config", JSONB), Column("created_at", DateTime(timezone=True))),
                }
                await conn.run_sync(metadata.create_all)
                revisions = sorted((await conn.execute(text("SELECT version_num FROM public.alembic_version"))).scalars().all())
                payload = {"format": seed.FORMAT, "actor": "fixture", "created_at": "2026-10-17T00:00:00+00:00",
                    "schema_revision": revisions, "columns": {name: list(table.columns.keys()) for name, table in tables.items()},
                    "tables": {
                        "model_provider_configs": [{"id": "provider", "extra_config": {"custom": True}}],
                        "knowledge_collections": [{"id": "collection", "index_epoch": 99,
                            "collection_metadata": {"active_vector_generation_id": "old", "custom": True}}],
                        "assistants": [{"id": "assistant", "system_prompt": "Fixture private prompt", "config": {"context_top_k": 17},
                            "created_at": "2026-10-17T00:00:00+00:00"}],
                    }}

                @asynccontextmanager
                async def begin():
                    async with conn.begin_nested():
                        yield conn

                bridge = SimpleNamespace(begin=begin)
                with patch.object(seed, "_tables", AsyncMock(return_value=tables)):
                    preview = await seed.restore(bridge, payload, actor="fixture")
                    assert preview["target_empty"]
                    await seed.restore(bridge, seed.unseal(seed.seal(payload)), actor="fixture", apply=True)
                    record = (await conn.execute(select(tables["assistants"]))).mappings().one()
                    assert record["system_prompt"] == "Fixture private prompt" and record["config"] == {"context_top_k": 17}
                    collection = (await conn.execute(select(tables["knowledge_collections"]))).mappings().one()
                    assert collection["index_epoch"] == 1 and "active_vector_generation_id" not in collection["collection_metadata"]
                    assert collection["collection_metadata"]["configuration_recovery"]["actor"] == "fixture"
                    with pytest.raises(AppException) as failure:
                        await seed.restore(bridge, payload, actor="fixture", apply=True)
                    assert failure.value.code == "CONFIG_SEED_TARGET_NOT_EMPTY"
                # Start another savepoint drill on empty fixture tables, then force
                # a duplicate at the last table: earlier inserts must roll back too.
                for table in tables.values():
                    await conn.execute(table.delete())
                payload["tables"]["assistants"] *= 2
                with patch.object(seed, "_tables", AsyncMock(return_value=tables)), pytest.raises(IntegrityError):
                    await seed.restore(bridge, payload, actor="fixture", apply=True)
                for table in tables.values():
                    assert (await conn.execute(select(func.count()).select_from(table))).scalar_one() == 0
            finally:
                await outer.rollback()
    finally:
        await engine.dispose()
