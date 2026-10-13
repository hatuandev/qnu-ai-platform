"""Capture database, referenced objects and application-owned Qdrant namespaces."""

import asyncio
import hashlib
import shutil
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.paths import get_configs_dir
from app.modules.backups.archive import safe_name
from app.modules.backups.errors import BackupIntegrityError
from app.modules.backups.offload import finish_thread
from app.modules.backups.processes import dump_database


def quoted_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def database_inventory(conn) -> dict:
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    counts = {}
    for row in tables:
        counts[row["tablename"]] = await conn.fetchval(
            f"SELECT count(*) FROM public.{quoted_identifier(row['tablename'])}"
        )
    columns = await conn.fetch(
        "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND column_name LIKE '%storage_path' AND data_type IN ('character varying','text')"
    )
    references = set()
    for row in columns:
        values = await conn.fetch(
            f"SELECT DISTINCT {quoted_identifier(row['column_name'])} AS path FROM public.{quoted_identifier(row['table_name'])} WHERE {quoted_identifier(row['column_name'])} IS NOT NULL"
        )
        references.update(item["path"] for item in values if item["path"])
    schema = await conn.fetch("SELECT version_num FROM alembic_version")
    return {
        "tables": counts,
        "schema": [row["version_num"] for row in schema],
        "file_references": sorted(references),
    }


def local_files() -> dict[str, Path]:
    root = Path(settings.LOCAL_STORAGE_PATH).resolve()
    files = {}
    for prefix in settings.BACKUP_LOCAL_PREFIXES:
        safe_name(prefix)
        directory = root / prefix
        if directory.is_symlink():
            raise BackupIntegrityError("Không sao lưu thư mục local dạng symlink.")
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise BackupIntegrityError("Không sao lưu file local dạng symlink.")
            if path.is_file():
                if not path.resolve().is_relative_to(root):
                    raise BackupIntegrityError("File local nằm ngoài thư mục lưu trữ.")
                files["local/" + safe_name(path.relative_to(root).as_posix())] = path
    return files


def capture_s3(scratch: Path) -> tuple[dict[str, Path], dict]:
    from app.core.storage import S3StorageDriver

    driver = S3StorageDriver(
        settings.S3_ENDPOINT,
        settings.S3_ACCESS_KEY,
        settings.S3_SECRET_KEY,
        settings.S3_BUCKET,
        settings.S3_SECURE,
        settings.S3_REGION,
    )
    client = driver.s3_client
    objects, files = {}, {}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=settings.S3_BUCKET):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            token = hashlib.sha256(key.encode("utf-8")).hexdigest()
            name = "objects/" + token
            path = scratch / token
            response = client.get_object(Bucket=settings.S3_BUCKET, Key=key, IfMatch=obj["ETag"])
            try:
                with path.open("xb") as target:
                    for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
                        target.write(chunk)
            finally:
                response["Body"].close()
            if path.stat().st_size != obj["Size"]:
                raise BackupIntegrityError("Object S3 không đủ nội dung.")
            files[name] = path
            objects[key] = {
                "entry": name,
                "content_type": response.get("ContentType"),
                "metadata": response.get("Metadata", {}),
                "version_id": response.get("VersionId"),
            }
    return files, {
        "bucket": settings.S3_BUCKET,
        "objects": objects,
        "scope": "Current object versions; immutable source revision keys are included",
    }


async def capture_vectors(conn, scratch: Path) -> tuple[dict[str, Path], dict]:
    headers = {"api-key": settings.QDRANT_API_KEY} if settings.QDRANT_API_KEY else {}
    async with httpx.AsyncClient(
        base_url=settings.QDRANT_URL.rstrip("/"), headers=headers, timeout=120, trust_env=False
    ) as client:
        response = await client.get("/")
        response.raise_for_status()
        version = response.json()["version"]
        topology = await client.get("/cluster")
        topology.raise_for_status()
        topology_info = topology.json()["result"]
        if topology_info.get("status") == "enabled":
            raise AppException(
                "Đợt 1 chỉ hỗ trợ Qdrant single-node; cluster phân tán cần chụp đủ shard/peer.",
                code="BACKUP_DISTRIBUTED_UNSUPPORTED",
            )
        listing = await client.get("/collections")
        listing.raise_for_status()
        existing = {item["name"] for item in listing.json()["result"]["collections"]}
        generations = [
            dict(row)
            for row in await conn.fetch(
                "SELECT id, collection_id, embedding_model, provider_id, embedding_dimension, qdrant_collection_name, status FROM knowledge_vector_generations"
            )
        ]
        collection_ids = [
            row["id"] for row in await conn.fetch("SELECT id FROM knowledge_collections")
        ]
        names = {
            settings.QDRANT_COLLECTION,
            *(row["qdrant_collection_name"] for row in generations),
        }
        for collection_id in collection_ids:
            normalized = collection_id.replace("-", "_").lower()
            names.add(normalized if normalized.startswith("col_") else "col_" + normalized)
        required = {
            row["qdrant_collection_name"] for row in generations if row["status"] == "active"
        }
        if required - existing:
            raise AppException(
                "Thiếu namespace vector đang hoạt động; không thể tạo backup đầy đủ.",
                code="BACKUP_VECTOR_MISSING",
            )
        collections, files = [], {}
        for name in sorted(names & existing):
            route = "/collections/" + quote(name, safe="")
            details = await client.get(route)
            details.raise_for_status()
            info = details.json()["result"]
            created = await client.post(route + "/snapshots", params={"wait": "true"})
            created.raise_for_status()
            snapshot = created.json()["result"]["name"]
            path = scratch / (hashlib.sha256(name.encode()).hexdigest() + ".snapshot")
            try:
                async with client.stream(
                    "GET", route + "/snapshots/" + quote(snapshot, safe="")
                ) as data:
                    data.raise_for_status()
                    with path.open("xb") as target:
                        async for block in data.aiter_bytes(1024 * 1024):
                            await asyncio.to_thread(target.write, block)
            finally:
                removed = await client.delete(
                    route + "/snapshots/" + quote(snapshot, safe=""), params={"wait": "true"}
                )
                removed.raise_for_status()
            entry = "vectors/" + path.name
            files[entry] = path
            collections.append(
                {
                    "name": name,
                    "entry": entry,
                    "points_count": info["points_count"],
                    "config": info["config"],
                }
            )
        aliases_response = await client.get("/aliases")
        aliases_response.raise_for_status()
        aliases = [
            alias
            for alias in aliases_response.json()["result"]["aliases"]
            if alias["collection_name"] in names & existing
        ]
    return files, {
        "version": version,
        "collections": collections,
        "aliases": aliases,
        "generations": generations,
    }


async def capture_all(conn, scratch: Path, update) -> tuple[dict, dict]:
    update("Sao lưu PostgreSQL", 15)
    database = await database_inventory(conn)
    if "job_records" in database["tables"]:
        active = await conn.fetchval(
            "SELECT count(*) FROM job_records WHERE status IN ('queued','running') OR (status='failed' AND result->>'retryable'='true')"
        )
        if active:
            raise AppException(
                "Còn job chờ/chạy/thử lại. Hãy để worker xử lý xong rồi sao lưu; không tự hủy hoặc phát lại job.",
                code="BACKUP_JOBS_PENDING",
            )
    if "workflow_executions" in database["tables"]:
        active = await conn.fetchval(
            "SELECT count(*) FROM workflow_executions WHERE status='running'"
        )
        if active:
            raise AppException(
                "Còn workflow đang chạy; hãy chờ hoàn tất hoặc đối soát execution bị gián đoạn trước khi sao lưu.",
                code="BACKUP_WORKFLOW_RUNNING",
            )
    database_size = await conn.fetchval("SELECT pg_database_size(current_database())")
    if shutil.disk_usage(scratch).free < database_size * 3 + settings.BACKUP_MIN_FREE_BYTES:
        raise AppException(
            "Không đủ chỗ cho DB dump, archive và khôi phục kiểm tra.", code="BACKUP_DISK_FULL"
        )
    dump = scratch / "database.dump"
    database.update(await dump_database(dump, conn))
    files = {"database.dump": dump}
    # Runtime node/template manifests can be edited independently of DB rows.
    config_root = get_configs_dir()
    if not config_root.is_dir():
        raise AppException(
            "Thiếu thư mục cấu hình runtime; kiểm tra CONFIGS_DIR.", code="BACKUP_CONFIG_MISSING"
        )
    if config_root.exists():
        for path in config_root.rglob("*"):
            if path.is_symlink() or not path.resolve().is_relative_to(config_root.resolve()):
                raise BackupIntegrityError("Đường dẫn cấu hình không an toàn.")
            if path.is_file():
                files["configs/" + safe_name(path.relative_to(config_root).as_posix())] = path
    update("Sao lưu tài liệu và bản hiệu đính", 35)
    local = await finish_thread(local_files)
    files.update(local)
    objects = {"objects": {}}
    if settings.STORAGE_DRIVER.lower() == "s3":
        captured, objects = await finish_thread(capture_s3, scratch)
        files.update(captured)
    references = set(database["file_references"])
    available = (
        set(objects["objects"])
        if settings.STORAGE_DRIVER.lower() == "s3"
        else {name.removeprefix("local/") for name in local}
    )
    if references - available:
        raise AppException(
            "Có file được DB tham chiếu nhưng thiếu trong kho file/phạm vi local; kiểm tra BACKUP_LOCAL_PREFIXES và storage.",
            code="BACKUP_FILE_MISSING",
        )
    update("Tạo snapshot chỉ mục vector", 55)
    vectors, vector_metadata = await capture_vectors(conn, scratch)
    files.update(vectors)
    return files, {
        "format": "qnu-backup-v1",
        "database": database,
        "storage_driver": settings.STORAGE_DRIVER,
        "local_prefixes": settings.BACKUP_LOCAL_PREFIXES,
        "s3": objects,
        "qdrant": vector_metadata,
        "redis": "Recreate cache/locks; reconcile durable jobs before starting workers",
    }
