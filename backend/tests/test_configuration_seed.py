"""Configuration recovery must never overwrite managed settings or expose keys."""

from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Column, MetaData, String, Table

from app.core.exceptions import AppException
from app.modules.backups import configuration_seed as seed


def payload():
    names = sorted(seed.REQUIRED)
    return {"format": seed.FORMAT, "actor": "fixture", "created_at": datetime.now(UTC).isoformat(),
            "schema_revision": ["fixture-head"], "tables": {name: [] for name in names},
            "columns": {name: ["id"] for name in names}}


def test_package_is_encrypted_and_roundtrips_private_prompt_and_keys():
    value = payload()
    value["tables"]["assistants"] = [{"id": "private-prompt-fixture"}]
    value["tables"]["model_provider_configs"] = [{"id": "private-key-fixture"}]
    data = seed.seal(value)
    assert b"private-prompt-fixture" not in data and b"private-key-fixture" not in data
    assert seed.unseal(data) == value


@pytest.mark.parametrize("data", [b'{}', b'enc:v1:not-a-fernet-token', b'\xff'])
def test_plaintext_corrupt_or_wrong_key_cannot_be_restored(data):
    with pytest.raises(AppException) as failure:
        seed.unseal(data)
    assert failure.value.code == "CONFIG_SEED_INVALID"


def test_unknown_table_and_unknown_shape_are_rejected():
    value = payload()
    value["tables"]["repository_documents"] = []
    value["columns"]["repository_documents"] = ["id"]
    with pytest.raises(AppException):
        seed.unseal(seed.seal(value))
    value = payload()
    value["tables"]["assistants"] = [{"id": "a", "unknown_column": "value"}]
    with pytest.raises(AppException):
        seed.unseal(seed.seal(value))


def test_collection_config_keeps_settings_but_not_stale_pointers_or_active_rules():
    original = {"id": "collection", "index_epoch": 50, "collection_metadata": {
        "active_vector_generation_id": "gone", "document_count": 22,
        "data_processing": {"chunk_strategy": "operator-choice"},
        "score_conversion_registry": {"items": [{"status": "active", "source_revision_id": "old"}]},
    }}
    before = deepcopy(original)
    restored = seed.restore_row("knowledge_collections", original)
    assert original == before
    assert restored["index_epoch"] == 1
    meta = restored["collection_metadata"]
    assert "active_vector_generation_id" not in meta and "score_conversion_registry" not in meta
    assert meta["data_processing"] == original["collection_metadata"]["data_processing"]
    assert meta["configuration_recovery_archive"]["score_rules"]["score_conversion_registry"] == original["collection_metadata"]["score_conversion_registry"]


def test_credentials_do_not_reuse_old_leases_and_glossary_requires_enable():
    assert seed.restore_row("provider_api_keys", {"lease_token": "busy", "lease_until": "future"}) == {
        "lease_token": None, "lease_until": None,
    }
    assert seed.restore_row("knowledge_glossary_settings", {"is_enabled": True})["is_enabled"] is False
    assistant = {"system_prompt": "custom", "config": {"context_top_k": 17}}
    assert seed.restore_row("assistants", assistant) == assistant


def db_fixture(occupied=False, schema="fixture-head"):
    engine, conn = MagicMock(), AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    engine.begin.return_value = cm
    tables = {name: Table(name, MetaData(), Column("id", String, primary_key=True), schema="public") for name in seed.REQUIRED}
    revision = MagicMock()
    revision.scalars.return_value.all.return_value = [schema]
    target = MagicMock()
    target.first.return_value = ("existing",) if occupied else None

    async def execute(statement, *args, **kwargs):
        return revision if "alembic_version" in str(statement) else target

    conn.execute.side_effect = execute
    return engine, conn, cm, tables


@pytest.mark.asyncio
async def test_restore_preview_does_not_insert_or_lock_tables():
    engine, conn, _, tables = db_fixture(occupied=True)
    with patch.object(seed, "_tables", AsyncMock(return_value=tables)):
        result = await seed.restore(engine, payload(), actor="fixture", apply=False)
    assert result["target_empty"] is False
    assert not any("INSERT" in str(call.args[0]) or "LOCK TABLE" in str(call.args[0]) for call in conn.execute.call_args_list)


@pytest.mark.asyncio
async def test_restore_into_populated_db_fails_without_any_write():
    engine, conn, cm, tables = db_fixture(occupied=True)
    with patch.object(seed, "_tables", AsyncMock(return_value=tables)), pytest.raises(AppException) as failure:
        await seed.restore(engine, payload(), actor="fixture", apply=True)
    assert failure.value.code == "CONFIG_SEED_TARGET_NOT_EMPTY"
    assert not any("INSERT" in str(call.args[0]) for call in conn.execute.call_args_list)
    assert cm.__aexit__.call_args.args[0] is AppException


@pytest.mark.asyncio
async def test_schema_mismatch_is_not_silently_migrated():
    engine, _, _, tables = db_fixture(schema="new-head")
    with patch.object(seed, "_tables", AsyncMock(return_value=tables)), pytest.raises(AppException) as failure:
        await seed.restore(engine, payload(), actor="fixture", apply=True)
    assert failure.value.code == "CONFIG_SEED_SCHEMA_MISMATCH"


@pytest.mark.asyncio
async def test_valid_empty_target_inserts_only_allowlisted_configuration():
    engine, conn, cm, tables = db_fixture()
    value = payload()
    value["tables"]["assistants"] = [{"id": "custom-assistant"}]
    with patch.object(seed, "_tables", AsyncMock(return_value=tables)):
        result = await seed.restore(engine, value, actor="fixture", apply=True)
    inserts = [call.args[0] for call in conn.execute.call_args_list if str(call.args[0]).startswith("INSERT")]
    assert len(inserts) == 1 and inserts[0].table.name == "assistants"
    assert result["runtime_pointers_restored"] is False
    assert cm.__aexit__.call_args.args == (None, None, None)


@pytest.mark.asyncio
async def test_storage_checksum_mismatch_is_rejected_before_restore():
    storage = AsyncMock()
    storage.get.return_value = seed.seal(payload())
    with pytest.raises(AppException):
        await seed.load(storage, "snapshots/configuration-seed/fixture.enc", "wrong-hash")


@pytest.mark.asyncio
async def test_capture_verifies_encrypted_storage_readback():
    engine, conn, _, tables = db_fixture()
    cm = engine.begin.return_value
    engine.connect.return_value = cm
    query = MagicMock()
    query.mappings.return_value.all.return_value = []
    revisions = MagicMock()
    revisions.scalars.return_value.all.return_value = ["fixture-head"]

    async def execute(statement, *args):
        return revisions if "alembic_version" in str(statement) else query

    conn.execute.side_effect = execute
    storage = AsyncMock()

    async def save(path, data):
        storage.get.return_value = data

    storage.save.side_effect = save
    with patch.object(seed, "_tables", AsyncMock(return_value=tables)):
        result = await seed.capture(engine, storage, "fixture")
    assert result["encrypted"] and result["path"].startswith("snapshots/configuration-seed/")
    assert len(result["sha256"]) == 64
    storage.save.assert_awaited_once()
    storage.get.assert_awaited_once()
