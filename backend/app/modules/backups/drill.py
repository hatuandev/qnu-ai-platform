"""Restore ONLY into new disposable containers. No input accepts a live target."""

import asyncio
import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from uuid import uuid4

import asyncpg
import httpx

from app.core.config import settings
from app.core.crypto import _derive_fernet
from app.core.exceptions import AppException
from app.modules.backups.capture import database_inventory
from app.modules.backups.coordination import database_connection
from app.modules.backups.errors import BackupIntegrityError
from app.modules.backups.offload import finish_thread
from app.modules.backups.processes import run_command


class DrillContainers:
    def __init__(self):
        self.token = uuid4().hex
        self.ids: list[str] = []
        self.target_ids: list[str] = []
        self.network_id: str | None = None

    async def start(self, image: str, port: int, variables: dict[str, str]) -> int:
        label = "qnu.backup.drill=" + self.token
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", settings.BACKUP_DRILL_RELAY_IMAGE):
            raise AppException(
                "Cần image relay cố định để khôi phục trong mạng nội bộ cô lập.",
                code="BACKUP_RELAY_REQUIRED",
            )
        if self.network_id is None:
            network_id = (
                (
                    await run_command(
                        [
                            "docker",
                            "network",
                            "create",
                            "--internal",
                            "--label",
                            label,
                            "qnu-backup-net-" + self.token,
                        ]
                    )
                )
                .decode()
                .strip()
            )
            if not re.fullmatch(r"[a-f0-9]{64}", network_id):
                raise BackupIntegrityError("Docker không trả network ID hợp lệ.")
            self.network_id = network_id
        container_id = (
            (
                await run_command(
                    [
                        "docker",
                        "run",
                        "--pull=never",
                        "--detach",
                        "--network",
                        self.network_id,
                        "--label",
                        label,
                        "--name",
                        "qnu-backup-drill-" + uuid4().hex,
                        "--cap-drop=NET_RAW",
                        "--cap-drop=NET_ADMIN",
                        "--security-opt=no-new-privileges:true",
                        *[arg for name in variables for arg in ("-e", name)],
                        image,
                        *(["server", "/data"] if port == 9000 else []),
                    ],
                    env={**os.environ, **variables},
                )
            )
            .decode()
            .strip()
        )
        if not re.fullmatch(r"[a-f0-9]{64}", container_id):
            raise BackupIntegrityError("Docker không trả container ID hợp lệ.")
        self.ids.append(container_id)
        self.target_ids.append(container_id)
        listing = json.loads(await run_command(["docker", "inspect", container_id]))[0]
        address = next(iter(listing["NetworkSettings"]["Networks"].values()))["IPAddress"]
        relay_id = (
            (
                await run_command(
                    [
                        "docker",
                        "run",
                        "--pull=never",
                        "--detach",
                        "--label",
                        label,
                        "--cap-drop=ALL",
                        "--security-opt=no-new-privileges:true",
                        "--publish",
                        f"127.0.0.1::{port}",
                        "--read-only",
                        "--pids-limit=64",
                        "-e",
                        "TARGET_HOST",
                        "-e",
                        "TARGET_PORT",
                        "-e",
                        "LISTEN_PORT",
                        settings.BACKUP_DRILL_RELAY_IMAGE,
                    ],
                    env={
                        **os.environ,
                        "TARGET_HOST": address,
                        "TARGET_PORT": str(port),
                        "LISTEN_PORT": str(port),
                    },
                )
            )
            .decode()
            .strip()
        )
        if not re.fullmatch(r"[a-f0-9]{64}", relay_id):
            raise BackupIntegrityError("Docker không trả relay ID hợp lệ.")
        self.ids.append(relay_id)
        await run_command(["docker", "network", "connect", self.network_id, relay_id])
        listing = json.loads(await run_command(["docker", "inspect", relay_id]))[0]
        binding = listing["NetworkSettings"]["Ports"][f"{port}/tcp"][0]
        if binding["HostIp"] != "127.0.0.1":
            raise BackupIntegrityError("Sandbox không được công khai cổng ra mạng.")
        return int(binding["HostPort"])

    async def cleanup(self) -> None:
        # Never remove user containers/volumes; validate the exact ID and ownership label.
        for container_id in reversed(self.ids):
            info = json.loads(await run_command(["docker", "inspect", container_id]))[0]
            if (
                info["Id"] != container_id
                or info["Config"]["Labels"].get("qnu.backup.drill") != self.token
            ):
                raise BackupIntegrityError("Từ chối dọn container không thuộc phiên khôi phục thử.")
            await run_command(["docker", "rm", "--force", "--volumes", container_id])
        if self.network_id:
            info = json.loads(await run_command(["docker", "network", "inspect", self.network_id]))[
                0
            ]
            if (
                info["Id"] != self.network_id
                or info["Labels"].get("qnu.backup.drill") != self.token
                or not info["Internal"]
            ):
                raise BackupIntegrityError("Từ chối dọn network không thuộc phiên khôi phục thử.")
            await run_command(["docker", "network", "rm", self.network_id])


async def image_from_container(name: str) -> str:
    # Resolve an immutable image ID, not the compose ':latest' tag.
    image = (
        (await run_command(["docker", "inspect", "--format", "{{.Image}}", name])).decode().strip()
    )
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise BackupIntegrityError("Không xác định được image sandbox.")
    return image


async def wait_http(url: str) -> None:
    async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
        for _ in range(60):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return
            except (httpx.HTTPError, OSError):
                await asyncio.sleep(0.5)
    raise AppException("Sandbox không khởi động kịp.", code="BACKUP_DRILL_UNAVAILABLE")


async def wait_postgres(dsn: str) -> None:
    for _ in range(60):
        try:
            async with database_connection(dsn) as conn:
                await conn.fetchval("SELECT 1")
            return
        except (OSError, ConnectionError, asyncpg.CannotConnectNowError):
            await asyncio.sleep(0.5)
    raise AppException("PostgreSQL sandbox không khởi động kịp.", code="BACKUP_DRILL_UNAVAILABLE")


def encrypted_tokens(value):
    if isinstance(value, str):
        if value.startswith("enc:v1:"):
            yield value[7:]
    elif isinstance(value, dict):
        for item in value.values():
            yield from encrypted_tokens(item)
    elif isinstance(value, list):
        for item in value:
            yield from encrypted_tokens(item)


async def verify_provider_keys(conn, restored_secrets: dict) -> int:
    from cryptography.fernet import InvalidToken

    keys = [
        restored_secrets.get("PROVIDER_ENCRYPTION_KEY") or restored_secrets["SECRET_KEY"],
        *restored_secrets.get("OLD_PROVIDER_ENCRYPTION_KEYS", []),
    ]
    ciphers = [_derive_fernet(key) for key in keys]
    checked = 0
    for row in await conn.fetch("SELECT to_jsonb(p) AS data FROM model_provider_configs p"):
        for token in encrypted_tokens(json.loads(row["data"])):
            for cipher in ciphers:
                try:
                    cipher.decrypt(token.encode())
                    checked += 1
                    break
                except InvalidToken:
                    continue
            else:
                raise BackupIntegrityError("Không giải mã được khóa ModelOps từ bản sao lưu.")
    # Relational provider key pools are authoritative, so verify them too.
    exists = await conn.fetchval("SELECT to_regclass('public.provider_api_keys')")
    if exists:
        for row in await conn.fetch("SELECT to_jsonb(p) AS data FROM provider_api_keys p"):
            for token in encrypted_tokens(json.loads(row["data"])):
                if not any_can_decrypt(ciphers, token):
                    raise BackupIntegrityError("Không giải mã được khóa trong key pool ModelOps.")
                checked += 1
    return checked


def any_can_decrypt(ciphers, token: str) -> bool:
    from cryptography.fernet import InvalidToken

    for cipher in ciphers:
        try:
            cipher.decrypt(token.encode())
            return True
        except InvalidToken:
            continue
    return False


async def restore_vectors(url: str, manifest: dict, scratch: Path) -> None:
    await wait_http(url + "/")
    async with httpx.AsyncClient(base_url=url, timeout=120, trust_env=False) as client:
        info = await client.get("/")
        info.raise_for_status()
        if info.json()["version"] != manifest["qdrant"]["version"]:
            raise BackupIntegrityError("Image Qdrant sandbox khác phiên bản trong backup.")
        from urllib.parse import quote

        for collection in manifest["qdrant"]["collections"]:
            path = scratch / collection["entry"]
            # Qdrant creates a new collection from the uploaded snapshot.
            with path.open("rb") as stream:
                response = await client.post(
                    "/collections/" + quote(collection["name"], safe="") + "/snapshots/upload",
                    params={"priority": "snapshot", "wait": "true"},
                    files={"snapshot": (path.name, stream, "application/octet-stream")},
                )
            response.raise_for_status()
            count = await client.post(
                "/collections/" + quote(collection["name"], safe="") + "/points/count",
                json={"exact": True},
            )
            count.raise_for_status()
            if count.json()["result"]["count"] != collection["points_count"]:
                raise BackupIntegrityError("Số vector khôi phục không khớp.")
        if manifest["qdrant"]["aliases"]:
            response = await client.post(
                "/collections/aliases",
                json={
                    "actions": [{"create_alias": alias} for alias in manifest["qdrant"]["aliases"]]
                },
            )
            response.raise_for_status()


def restore_s3(url: str, access_key: str, secret_key: str, manifest: dict, scratch: Path) -> None:
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    bucket = "qnu-backup-drill"
    client.create_bucket(Bucket=bucket)
    for key, obj in manifest["s3"]["objects"].items():
        path = scratch / obj["entry"]
        client.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={
                "Metadata": obj["metadata"],
                "ContentType": obj["content_type"] or "application/octet-stream",
            },
        )
        data = client.get_object(Bucket=bucket, Key=key)
        digest = hashlib.sha256()
        try:
            for block in data["Body"].iter_chunks(chunk_size=1024 * 1024):
                digest.update(block)
        finally:
            data["Body"].close()
        if digest.hexdigest() != manifest["inventory"][obj["entry"]]["sha256"]:
            raise BackupIntegrityError("Object khôi phục thử không khớp checksum.")


async def run_drill(manifest: dict, scratch: Path, update) -> dict:
    from app.modules.backups.compatibility import check_restore_compatibility

    check_restore_compatibility(manifest)
    if not settings.BACKUP_DRILL_ENABLED:
        raise AppException(
            "Khôi phục thử cần bật BACKUP_DRILL_ENABLED trên máy có Docker; không gắn Docker socket vào backend production.",
            code="BACKUP_DRILL_DISABLED",
        )
    owned = DrillContainers()
    password = secrets.token_urlsafe(32)
    try:
        update("Khởi động PostgreSQL tách biệt", 40)
        pg_port = await owned.start(
            "postgres:" + str(manifest["database"]["major"]), 5432, {"POSTGRES_PASSWORD": password}
        )
        pg_id = owned.target_ids[-1]
        dsn = f"postgresql://postgres:{password}@127.0.0.1:{pg_port}/postgres"
        await wait_postgres(dsn)
        await run_command(
            [
                "docker",
                "exec",
                "-i",
                pg_id,
                "pg_restore",
                "-U",
                "postgres",
                "-d",
                "postgres",
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
            ],
            source=scratch / "database.dump",
            timeout=settings.BACKUP_TIMEOUT_SECONDS,
        )
        async with database_connection(dsn) as conn:
            actual = await database_inventory(conn)
            if actual != {
                key: manifest["database"][key] for key in ("tables", "schema", "file_references")
            }:
                raise BackupIntegrityError(
                    "Schema, số hàng hoặc tham chiếu file khôi phục không khớp."
                )
            checked = await verify_provider_keys(
                conn, json.loads((scratch / "secrets.json").read_text(encoding="utf-8"))
            )
        update("Khôi phục Qdrant tách biệt", 65)
        image = await image_from_container("qnu_qdrant")
        port = await owned.start(image, 6333, {})
        await restore_vectors(f"http://127.0.0.1:{port}", manifest, scratch)
        if manifest["storage_driver"] == "s3":
            update("Khôi phục và đối soát object storage tách biệt", 85)
            access = "qnu-drill"
            image = await image_from_container("qnu_minio")
            port = await owned.start(
                image, 9000, {"MINIO_ROOT_USER": access, "MINIO_ROOT_PASSWORD": password}
            )
            endpoint = f"http://127.0.0.1:{port}"
            await wait_http(endpoint + "/minio/health/live")
            await finish_thread(restore_s3, endpoint, access, password, manifest, scratch)
        return {
            "tables": len(actual["tables"]),
            "provider_keys_checked": checked,
            "vector_collections": len(manifest["qdrant"]["collections"]),
            "files_verified": len(manifest["inventory"]),
            "rag_chat_tested": False,
            "live_restore": False,
        }
    finally:
        await owned.cleanup()
