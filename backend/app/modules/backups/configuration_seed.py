"""Encrypted configuration-only recovery; never a replacement for full backup.

Local administrator CLI only. Restore is preview-first and requires empty target
configuration tables. No document, index, conversation, or publication is restored.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, MetaData, Table, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.crypto import decrypt_secret, encrypt_secret, is_encrypted
from app.core.exceptions import AppException
from app.core.storage import StorageDriver

FORMAT = "qnu-configuration-seed-v1"
# Ordered for FK insertion, not arbitrary tables supplied by the archive/client.
TABLE_NAMES = (
    "model_provider_configs", "provider_api_keys", "knowledge_collections",
    "workflow_definitions", "workflow_drafts", "workflow_versions",
    "assistants", "assistant_versions", "tool_definitions", "platform_document_types",
    "knowledge_glossary_terms", "knowledge_glossary_settings", "knowledge_glossary_audits",
)
REQUIRED = {"assistants", "model_provider_configs", "knowledge_collections"}
COLLECTION_RUNTIME_KEYS = {
    "active_vector_generation_id", "embedding_dimension", "document_count", "chunk_count", "fact_count",
    "score_conversion_registry", "score_conversion_rules",
}


def _json(value: Any) -> str:
    def encode(item: Any) -> str:
        if isinstance(item, datetime):
            return item.isoformat()
        raise TypeError("Unsupported configuration value")

    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=encode)


def _invalid() -> AppException:
    return AppException("Gói cấu hình không hợp lệ hoặc không đúng khóa mã hóa.",
                        code="CONFIG_SEED_INVALID", status_code=422)


def seal(payload: dict) -> bytes:
    return encrypt_secret(_json(payload)).encode("utf-8")


def unseal(data: bytes) -> dict:
    try:
        token = data.decode("utf-8")
        if not is_encrypted(token):
            raise ValueError("Plaintext configuration packages are not allowed")
        value = json.loads(decrypt_secret(token) or "null")
        if (not isinstance(value, dict) or value.get("format") != FORMAT
                or set(value) != {"format", "created_at", "actor", "schema_revision", "tables", "columns"}
                or not isinstance(value["tables"], dict) or not REQUIRED <= value["tables"].keys()
                or not value["tables"].keys() <= set(TABLE_NAMES)
                or set(value["columns"]) != set(value["tables"])):
            raise ValueError("Invalid package shape")
        for name, rows in value["tables"].items():
            columns = value["columns"][name]
            if (not isinstance(columns, list) or not all(isinstance(col, str) for col in columns)
                    or not isinstance(rows, list) or any(not isinstance(row, dict) or set(row) != set(columns) for row in rows)):
                raise ValueError("Invalid table shape")
        return value
    except (UnicodeError, ValueError, TypeError, KeyError, AttributeError) as error:
        raise _invalid() from error


def restore_row(name: str, original: dict) -> dict:
    """Keep the encrypted original intact; omit stale publication/source bindings."""
    row = deepcopy(original)
    if name == "knowledge_collections":
        row["index_epoch"] = 1
        metadata = row.get("collection_metadata") or {}
        row["collection_metadata"] = {key: value for key, value in metadata.items() if key not in COLLECTION_RUNTIME_KEYS}
        archived = {key: metadata[key] for key in ("score_conversion_registry", "score_conversion_rules") if key in metadata}
        if archived:
            row["collection_metadata"]["configuration_recovery_archive"] = {
                "status": "requires_source_rebind", "score_rules": archived,
            }
    elif name == "provider_api_keys":
        row["lease_token"] = row["lease_until"] = None
    elif name == "knowledge_glossary_settings":
        row["is_enabled"] = False  # Source scopes need review after document reload.
    return row


async def _tables(conn: AsyncConnection) -> dict[str, Table]:
    def reflect(sync):
        available = set(inspect(sync).get_table_names(schema="public"))
        if not REQUIRED <= available:
            raise AppException("Thiếu bảng cấu hình; chạy migration trước.", code="CONFIG_SEED_SCHEMA_MISSING", status_code=409)
        metadata = MetaData()
        return {name: Table(name, metadata, schema="public", autoload_with=sync, resolve_fks=False)
                for name in TABLE_NAMES if name in available}

    return await conn.run_sync(reflect)


async def capture(engine: AsyncEngine, storage: StorageDriver, actor: str) -> dict:
    if not actor.strip():
        raise AppException("Cần định danh người vận hành.", code="CONFIG_SEED_ACTOR_REQUIRED", status_code=422)
    async with engine.connect() as conn:
        await conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        tables = await _tables(conn)
        revision = (await conn.execute(text("SELECT version_num FROM public.alembic_version"))).scalars().all()
        rows = {name: [dict(row) for row in (await conn.execute(select(table))).mappings().all()]
                for name, table in tables.items()}
        payload = {"format": FORMAT, "created_at": datetime.now(UTC).isoformat(), "actor": actor,
                   "schema_revision": sorted(revision), "tables": rows,
                   "columns": {name: list(table.columns.keys()) for name, table in tables.items()}}
    encrypted = await asyncio.to_thread(seal, payload)
    checksum = hashlib.sha256(encrypted).hexdigest()
    path = f"snapshots/configuration-seed/{datetime.now(UTC):%Y%m%dT%H%M%SZ}_{uuid4().hex}.enc"
    await storage.ensure_bucket()
    await storage.save(path, encrypted)
    readback = await storage.get(path)
    if readback != encrypted:
        raise AppException("Đối soát tệp sao lưu thất bại.", code="CONFIG_SEED_STORAGE_MISMATCH", status_code=503)
    # Verify decryption as well, not merely successful upload.
    await asyncio.to_thread(unseal, readback)
    return {"path": path, "sha256": checksum, "counts": {name: len(items) for name, items in rows.items()},
            "schema_revision": sorted(revision), "encrypted": True}


async def load(storage: StorageDriver, path: str, expected_sha256: str) -> dict:
    if not path.startswith("snapshots/configuration-seed/") or ".." in path or "\\" in path:
        raise _invalid()
    data = await storage.get(path)
    if not data or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise _invalid()
    return await asyncio.to_thread(unseal, data)


async def restore(engine: AsyncEngine, payload: dict, *, actor: str, apply: bool = False) -> dict:
    if not actor.strip():
        raise AppException("Cần định danh người vận hành.", code="CONFIG_SEED_ACTOR_REQUIRED", status_code=422)
    # Validate even when invoked programmatically without load(). No silent table omissions.
    payload = unseal(seal(payload))
    async with engine.begin() as conn:
        await conn.execute(text("SET LOCAL lock_timeout = '5s'"))
        await conn.execute(text("SET LOCAL statement_timeout = '30s'"))
        # Same lock as startup bootstrap. --apply must run before seed/defaults.
        await conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('qnu-ai-platform-bootstrap'))"))
        tables = await _tables(conn)
        revisions = sorted((await conn.execute(text("SELECT version_num FROM public.alembic_version"))).scalars().all())
        if revisions != payload["schema_revision"] or not payload["tables"].keys() <= tables.keys():
            raise AppException("Schema không khớp gói cấu hình; không tự migrate hoặc sửa gói.", code="CONFIG_SEED_SCHEMA_MISMATCH", status_code=409)
        for name, columns in payload["columns"].items():
            if set(columns) != set(tables[name].columns.keys()):
                raise AppException("Cột cấu hình đã thay đổi.", code="CONFIG_SEED_SCHEMA_MISMATCH", status_code=409)
        occupied = []
        # Lock target tables as well: administrators/API writers need not use advisory lock.
        if apply:
            for name in TABLE_NAMES:
                if name in tables:
                    target = conn.dialect.identifier_preparer.format_table(tables[name])
                    await conn.execute(text(f"LOCK TABLE {target} IN EXCLUSIVE MODE"))
        for name, table in tables.items():
            if (await conn.execute(select(table).limit(1))).first() is not None:
                occupied.append(name)
        summary = {"apply": apply, "target_empty": not occupied, "occupied_tables": occupied,
                   "counts": {name: len(rows) for name, rows in payload["tables"].items()},
                   "runtime_pointers_restored": False, "score_rules_require_rebind": True,
                   "glossary_enabled_after_restore": False}
        if not apply:
            return summary
        if occupied:
            raise AppException("DB đã có cấu hình; dừng để tránh ghi đè. Không tự xóa hoặc merge.",
                               code="CONFIG_SEED_TARGET_NOT_EMPTY", status_code=409)
        for name in TABLE_NAMES:
            if name not in payload["tables"]:
                continue
            table = tables[name]
            for original in payload["tables"][name]:
                row = restore_row(name, original)
                if name == "knowledge_collections":
                    row["collection_metadata"]["configuration_recovery"] = {
                        "actor": actor, "restored_at": datetime.now(UTC).isoformat(),
                        "snapshot_created_at": payload["created_at"], "format": FORMAT,
                    }
                for column in table.columns:
                    if isinstance(column.type, DateTime) and isinstance(row.get(column.name), str):
                        row[column.name] = datetime.fromisoformat(row[column.name])
                await conn.execute(table.insert().values(**row))
        return summary
