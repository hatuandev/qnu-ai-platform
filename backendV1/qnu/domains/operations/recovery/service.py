"""Quiescent v1 data backup and restore into a new DB/storage/vector namespace."""

import asyncio
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import asyncpg
from sqlalchemy import Date, DateTime, Numeric, Table, insert, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.index.models import IndexChunk, IndexInput, IndexRun
from qnu.domains.knowledge.index.search import manifest as checked_manifest
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.operations.backups.snapshot import freeze
from qnu.domains.operations.jobs.catalog import job_union
from qnu.domains.operations.models import EvidenceBackup
from qnu.domains.operations.recovery import archive
from qnu.domains.workspaces.access import require_platform_admin, resolve_workspace_access
from qnu.domains.workspaces.models import Workspace
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.database import Base
from qnu.platform.errors import Conflict, DependencyUnavailable
from qnu.platform.ownership import V1_TABLES
from qnu.platform.schema import SCHEMA_HEAD as HEAD
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorStore

ROOT = Path(__file__).resolve().parents[4]


async def capture(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, encryption_key: str
) -> bytes:
    require_platform_admin(actor)
    await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    if await db.scalar(text("SELECT version_num FROM alembic_version_backendv1")) != HEAD:
        raise Conflict("DB nguồn chưa ở schema được hỗ trợ.", code="recovery_schema_mismatch")
    if not get_settings().PROVIDER_ENCRYPTION_KEY:
        raise Conflict(
            "Cần master key ModelOps từ cấu hình máy chủ.", code="recovery_provider_key_mismatch"
        )
    # All workspace writers serialize on these locks. Jobs release locks for HTTP,
    # so their durable running states are checked too, before any source is copied.
    workspaces = list(
        (await db.scalars(select(Workspace).order_by(Workspace.id).with_for_update())).all()
    )
    references = {}
    for workspace in workspaces:
        await resolve_workspace_access(
            db, actor, workspace.id, for_update=True, allow_suspended=True
        )
        jobs = job_union(workspace.id, None, None, None)
        if await db.scalar(
            select(jobs.c.id).where(jobs.c.status.in_(("queued", "running", "deleting"))).limit(1)
        ):
            raise Conflict(
                "Dừng nhận việc và chờ tác vụ kết thúc trước khi backup.",
                code="recovery_jobs_active",
            )
        _, refs = await freeze(db, workspace.id)
        references.update(refs)
    for backup in (
        await db.scalars(select(EvidenceBackup).where(EvidenceBackup.status == "completed"))
    ).all():
        if backup.blob_key:
            references[backup.blob_key] = backup.sha256
    tables = {}
    for table in Base.metadata.sorted_tables:
        if table.name not in V1_TABLES:
            continue
        rows = list((await db.execute(select(table).limit(100001))).mappings())
        if len(rows) > 100000:
            raise Conflict("Quá nhiều bản ghi cho bundle này.", code="recovery_limit")
        tables[table.name] = json.loads(
            json.dumps([dict(row) for row in rows], default=str, ensure_ascii=False)
        )
    objects = {}
    for name, expected in sorted(references.items()):
        if expected is None and not await blob.exists(name):
            continue
        value = await blob.get_bytes(name)
        if expected and hashlib.sha256(value).hexdigest() != expected:
            raise Conflict("Nguồn backup sai checksum.", code="recovery_source_integrity")
        objects[name] = value
        if sum(map(len, objects.values())) > archive.MAX_BYTES:
            raise Conflict("Bundle vượt giới hạn dung lượng.", code="recovery_limit")
    snapshot = {
        "head": HEAD,
        "tables": tables,
        "blob_target_hash": blob.target_hash,
        "provider_key_fingerprint": hashlib.sha256(
            get_settings().PROVIDER_ENCRYPTION_KEY.encode()
        ).hexdigest(),
    }
    result = await asyncio.to_thread(archive.pack, snapshot, objects, encryption_key)
    for workspace in workspaces:
        await record_workspace_event(
            db,
            workspace_id=workspace.id,
            actor=actor,
            action="recovery.backup_created",
            detail={"bundle_sha256": hashlib.sha256(result).hexdigest()},
        )
    await db.commit()
    return result


def plan(
    payload: bytes, encryption_key: str, database_url: str, blob: BlobStore, vectors: VectorStore
) -> dict:
    url = make_url(database_url)
    if not re.fullmatch(r"qnu_v1_restore_[a-f0-9]{16}", url.database or ""):
        raise Conflict(
            "Chỉ phục hồi vào DB mới qnu_v1_restore_<16 ký tự hex>.",
            code="recovery_target_forbidden",
        )
    snapshot, objects = archive.unpack(payload, encryption_key)
    if snapshot.get("head") != HEAD or set(snapshot.get("tables", {})) != set(V1_TABLES):
        raise Conflict(
            "Schema recovery không khớp phiên bản đang chạy.", code="recovery_schema_mismatch"
        )
    if (
        snapshot.get("provider_key_fingerprint")
        != hashlib.sha256(get_settings().PROVIDER_ENCRYPTION_KEY.encode()).hexdigest()
    ):
        raise Conflict(
            "Cần master key ModelOps gốc từ nơi lưu bí mật riêng.",
            code="recovery_provider_key_mismatch",
        )
    if snapshot["blob_target_hash"] == blob.target_hash:
        raise Conflict(
            "Chọn kho đích mới, không ghi vào kho nguồn.", code="recovery_target_forbidden"
        )
    workspace_ids = {row["id"] for row in snapshot["tables"]["workspaces"]}
    for key in objects:
        if (
            "\\" in key
            or ".." in key.split("/")
            or not any(
                key.startswith((f"v1/workspaces/{ws}/", f"ocr-text/{ws}/", f"ocr-spelling/{ws}/"))
                for ws in workspace_ids
            )
        ):
            raise Conflict("Tệp ngoài phạm vi recovery.", code="recovery_object_scope")
    identity = {
        "bundle_sha256": hashlib.sha256(payload).hexdigest(),
        "database": url.database,
        "database_host": url.host,
        "database_port": url.port,
        "blob_target_hash": blob.target_hash,
        "vector_target_hash": vectors.target_hash,
    }
    return {
        **identity,
        "confirmation_sha256": digest(identity),
        "tables": len(snapshot["tables"]),
        "objects": len(objects),
        "credentials": "encrypted_ciphertext_only; original_master_key_required",
    }


async def connection(url: URL, database: str) -> asyncpg.Connection:
    return await asyncpg.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=database,
        timeout=15,
    )


def decode_row(table: Table, row: dict) -> dict:
    if set(row) != set(table.columns.keys()):
        raise Conflict("Cột dữ liệu recovery không khớp schema.", code="recovery_schema_mismatch")
    result = dict(row)
    for column in table.columns:
        value = result[column.name]
        if value is not None:
            if isinstance(column.type, DateTime):
                result[column.name] = datetime.fromisoformat(value)
            elif isinstance(column.type, Date):
                result[column.name] = date.fromisoformat(value)
            elif isinstance(column.type, Numeric):
                result[column.name] = Decimal(value)
    return result


async def restore(
    payload: bytes,
    encryption_key: str,
    database_url: str,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    confirmation: str,
) -> dict:
    require_platform_admin(actor)
    preview = plan(payload, encryption_key, database_url, blob, vectors)
    if confirmation != preview["confirmation_sha256"]:
        raise Conflict(
            "Cần xác nhận đúng đích và bundle đã xem trước.", code="recovery_confirmation_mismatch"
        )
    if await blob.list_objects("", limit=1):
        raise Conflict("Kho đích phải trống.", code="recovery_target_not_empty")
    url = make_url(database_url)
    admin = await connection(url, "postgres")
    try:
        if await admin.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", url.database):
            raise Conflict("DB đích đã tồn tại; không ghi đè.", code="recovery_target_not_empty")
        await admin.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await admin.close()
    # A freshly created, strictly named DB only. Credentials stay in subprocess env.
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.communicate()
    if process.returncode:
        raise DependencyUnavailable(
            "Không khởi tạo được schema recovery; giữ DB để kiểm tra.",
            code="recovery_migration_failed",
        )
    snapshot, objects = await asyncio.to_thread(archive.unpack, payload, encryption_key)
    engine = create_async_engine(database_url)
    created_vectors = []
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            for table in Base.metadata.sorted_tables:
                if table.name not in V1_TABLES:
                    continue
                for start in range(0, len(snapshot["tables"][table.name]), 500):
                    rows = [
                        decode_row(table, row)
                        for row in snapshot["tables"][table.name][start : start + 500]
                    ]
                    await db.execute(insert(table), rows)
            for key, value in objects.items():
                await blob.put_bytes(key, value)
                if (
                    hashlib.sha256(await blob.get_bytes(key)).hexdigest()
                    != hashlib.sha256(value).hexdigest()
                ):
                    raise Conflict(
                        "Tệp recovery không khớp checksum.", code="recovery_storage_integrity"
                    )
            for run in (await db.scalars(select(IndexRun))).all():
                sealed = await checked_manifest(db, blob, run) if run.manifest_key else None
                name = "qnu_v1_idx_" + uuid.uuid4().hex
                if await vectors.collection_exists(name):
                    raise Conflict("Vector đích đã tồn tại.", code="recovery_target_not_empty")
                if not run.is_active:
                    await remap_manifest(blob, vectors, run, sealed, name, preview["bundle_sha256"])
                    continue
                if sealed is None:
                    raise Conflict(
                        "Thiếu manifest của index đang phục vụ.", code="recovery_vectors_invalid"
                    )
                rows = list(
                    (
                        await db.execute(
                            select(IndexChunk, IndexInput)
                            .join(IndexInput, IndexChunk.input_id == IndexInput.id)
                            .where(IndexChunk.run_id == run.id)
                            .order_by(IndexChunk.ordinal)
                        )
                    ).all()
                )
                proofs = {item["id"]: item for item in sealed["chunks"]}
                if len(rows) != run.chunks_total or len(rows) != len(proofs):
                    raise Conflict(
                        "Thiếu chunk cho recovery index.", code="recovery_vectors_invalid"
                    )
                await vectors.ensure_collection(name, run.dimension)
                created_vectors.append(name)
                points = []
                for chunk, binding in rows:
                    proof = proofs.get(chunk.id, {})
                    if (
                        chunk.vector is None
                        or len(chunk.vector) != run.dimension
                        or digest(chunk.vector) != proof.get("vector_sha256")
                        or hashlib.sha256(chunk.text.encode()).hexdigest()
                        != proof.get("text_sha256")
                        or digest(chunk.citations) != proof.get("citations_sha256")
                        or digest(chunk.structure) != proof.get("structure_sha256")
                        or chunk.point_id != proof.get("point_id")
                    ):
                        raise Conflict(
                            "Vector DB không khớp manifest gốc.", code="recovery_vectors_invalid"
                        )
                    points.append(
                        {
                            "id": chunk.point_id,
                            "vector": chunk.vector,
                            "payload": {
                                "run_id": run.id,
                                "workspace_id": run.workspace_id,
                                "collection_id": run.collection_id,
                                "version_id": binding.version_id,
                                "chunk_id": chunk.id,
                                "text_sha256": chunk.text_sha256,
                            },
                        }
                    )
                for start in range(0, len(points), 64):
                    await vectors.upsert(name, points[start : start + 64])
                if await vectors.count(name) != len(points):
                    raise Conflict("Vector đích chưa đủ số điểm.", code="recovery_vectors_invalid")
                await remap_manifest(blob, vectors, run, sealed, name, preview["bundle_sha256"])
            for workspace in (await db.scalars(select(Workspace))).all():
                await resolve_workspace_access(
                    db, actor, workspace.id, for_update=True, allow_suspended=True
                )
                await record_workspace_event(
                    db,
                    workspace_id=workspace.id,
                    actor=actor,
                    action="recovery.restored",
                    detail={"bundle_sha256": preview["bundle_sha256"], "database": url.database},
                )
            await db.commit()
        return {
            "status": "restored",
            "database": url.database,
            "objects_verified": len(objects),
            "vector_collections": created_vectors,
            "workers_started": False,
            "bundle_sha256": preview["bundle_sha256"],
        }
    finally:
        await engine.dispose()


async def remap_manifest(
    blob: BlobStore,
    vectors: VectorStore,
    run: IndexRun,
    sealed: dict | None,
    name: str,
    bundle_sha256: str,
) -> None:
    """Every generation gets a new owned target, including inactive/cleaned ones."""
    run.vector_collection = name
    run.config = {**run.config, "vector_target_hash": vectors.target_hash}
    if sealed is None:
        return
    sealed.update(
        vector_collection=name,
        config=run.config,
        recovery={"source_manifest_sha256": run.manifest_sha256, "bundle_sha256": bundle_sha256},
    )
    content = json_bytes(sealed)
    run.manifest_sha256 = hashlib.sha256(content).hexdigest()
    run.manifest_key = (
        f"v1/workspaces/{run.workspace_id}/index/{run.id}/manifest/{run.manifest_sha256}.json"
    )
    await blob.put_bytes(run.manifest_key, content, "application/json")
