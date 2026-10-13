"""Opt-in real PG/S3/Qdrant backup + restore; exclusively disposable labelled containers."""

import asyncio
import os
from uuid import uuid4

import httpx
import pytest

from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.core.exceptions import AppException
from app.modules.backups import service
from app.modules.backups.catalogue import load_record
from app.modules.backups.coordination import (
    MAINTENANCE_LOCK,
    BackupMaintenanceMiddleware,
    database_connection,
    exclusive_access,
    guard_worker,
    shared_access,
)
from app.modules.backups.drill import (
    DrillContainers,
    image_from_container,
    wait_http,
    wait_postgres,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("QNU_TEST_BACKUP_DOCKER") != "1",
        reason="Opt-in disposable Docker data stores; no live data changed",
    ),
]


async def wait_terminal(backup_id: str):
    for _ in range(450):
        entry = await asyncio.to_thread(load_record, backup_id)
        if entry.status in ("completed", "failed"):
            return entry
        await asyncio.sleep(0.2)
    raise TimeoutError("Independent backup runner exceeded test deadline")


async def test_internal_target_has_no_default_route(monkeypatch):
    import json

    from app.modules.backups.processes import run_command

    relay_image = (
        (
            await run_command(
                ["docker", "image", "inspect", "--format", "{{.Id}}", "qnu-backup-relay:424"]
            )
        )
        .decode()
        .strip()
    )
    monkeypatch.setattr(settings, "BACKUP_DRILL_RELAY_IMAGE", relay_image)
    owned = DrillContainers()
    try:
        port = await owned.start(
            "postgres:16", 5432, {"POSTGRES_PASSWORD": "fixture-isolation-only"}
        )
        await wait_postgres(
            f"postgresql://postgres:fixture-isolation-only@127.0.0.1:{port}/postgres"
        )
        target = owned.target_ids[-1]
        routes = (await run_command(["docker", "exec", target, "cat", "/proc/net/route"])).decode()
        assert all(
            line.split()[1] != "00000000" for line in routes.splitlines()[1:] if line.split()
        )
        info = json.loads(await run_command(["docker", "inspect", target]))[0]
        assert len(info["NetworkSettings"]["Networks"]) == 1
        assert not any(info["NetworkSettings"]["Ports"].values())
        network = json.loads(await run_command(["docker", "network", "inspect", owned.network_id]))[
            0
        ]
        assert network["Internal"] and network["Labels"]["qnu.backup.drill"] == owned.token
    finally:
        await owned.cleanup()


async def test_real_encrypted_backup_and_isolated_restore(tmp_path, monkeypatch):
    from app.modules.backups.processes import run_command

    relay_image = (
        (
            await run_command(
                ["docker", "image", "inspect", "--format", "{{.Id}}", "qnu-backup-relay:424"]
            )
        )
        .decode()
        .strip()
    )
    monkeypatch.setattr(settings, "BACKUP_DRILL_RELAY_IMAGE", relay_image)
    monkeypatch.setenv("BACKUP_DRILL_RELAY_IMAGE", relay_image)
    owned = DrillContainers()
    secret = "fixture-" + uuid4().hex
    try:
        pg_port = await owned.start("postgres:16", 5432, {"POSTGRES_PASSWORD": secret})
        pg_id = owned.target_ids[-1]
        routes = (await run_command(["docker", "exec", pg_id, "cat", "/proc/net/route"])).decode()
        assert all(
            line.split()[1] != "00000000" for line in routes.splitlines()[1:] if line.split()
        )
        dsn = f"postgresql://postgres:{secret}@127.0.0.1:{pg_port}/postgres"
        await wait_postgres(dsn)
        image = await image_from_container("qnu_qdrant")
        vector_port = await owned.start(image, 6333, {})
        vector_url = f"http://127.0.0.1:{vector_port}"
        await wait_http(vector_url + "/")
        image = await image_from_container("qnu_minio")
        s3_port = await owned.start(
            image, 9000, {"MINIO_ROOT_USER": "fixture-admin", "MINIO_ROOT_PASSWORD": secret}
        )
        s3_url = f"http://127.0.0.1:{s3_port}"
        await wait_http(s3_url + "/minio/health/live")
        configuration = {
            "DATABASE_URL": dsn.replace("postgresql://", "postgresql+asyncpg://"),
            "BACKUP_PG_CONTAINER": pg_id,
            "BACKUP_DIRECTORY": str(tmp_path / "backups"),
            "LOCAL_STORAGE_PATH": str(tmp_path / "local"),
            "STORAGE_DRIVER": "s3",
            "S3_ENDPOINT": s3_url,
            "S3_ACCESS_KEY": "fixture-admin",
            "S3_SECRET_KEY": secret,
            "S3_BUCKET": "fixture-documents",
            "S3_SECURE": False,
            "QDRANT_URL": vector_url,
            "QDRANT_API_KEY": None,
            "SECRET_KEY": "fixture-secret-key-only",
            "PROVIDER_ENCRYPTION_KEY": "fixture-modelops-key-only",
            "OLD_PROVIDER_ENCRYPTION_KEYS": [],
            "BACKUP_DRILL_ENABLED": True,
        }
        for key, value in configuration.items():
            monkeypatch.setattr(settings, key, value)
            if isinstance(value, list):
                import json

                env_value = json.dumps(value)
            else:
                env_value = "" if value is None else str(value)
            monkeypatch.setenv(key, env_value)
        (tmp_path / "local" / "artifacts").mkdir(parents=True)
        (tmp_path / "local" / "artifacts" / "reviewed.md").write_text(
            "Bản Markdown đã duyệt – dữ liệu Việt Nam.", encoding="utf-8"
        )
        async with database_connection() as conn:
            await conn.execute(
                "CREATE TABLE alembic_version(version_num text); INSERT INTO alembic_version VALUES ('fixture_418')"
            )
            await conn.execute(
                "CREATE TABLE knowledge_collections(id text PRIMARY KEY); INSERT INTO knowledge_collections VALUES ('col_fixture_backup')"
            )
            await conn.execute(
                "CREATE TABLE knowledge_vector_generations(id text, collection_id text, embedding_model text, provider_id text, embedding_dimension int, qdrant_collection_name text, status text)"
            )
            await conn.execute(
                "INSERT INTO knowledge_vector_generations VALUES ('vg_fixture','col_fixture_backup','fixture-embedding','fixture-provider',4,'col_fixture_backup','active')"
            )
            await conn.execute(
                "CREATE TABLE repository_documents(storage_path text, review_status text); INSERT INTO repository_documents VALUES ('documents/originals/nguồn.pdf','reviewed')"
            )
            await conn.execute(
                "CREATE TABLE model_provider_configs(api_key_encrypted text); CREATE TABLE provider_api_keys(api_key_encrypted text)"
            )
            await conn.execute(
                "INSERT INTO model_provider_configs VALUES($1)",
                encrypt_secret("fixture-provider-api-key"),
            )
            await conn.execute(
                "INSERT INTO provider_api_keys VALUES($1)",
                encrypt_secret("fixture-key-pool-api-key"),
            )
        async with httpx.AsyncClient(base_url=vector_url, trust_env=False) as client:
            response = await client.put(
                "/collections/col_fixture_backup",
                json={"vectors": {"size": 4, "distance": "Cosine"}},
            )
            response.raise_for_status()
            response = await client.put(
                "/collections/col_fixture_backup/points?wait=true",
                json={
                    "points": [
                        {
                            "id": str(uuid4()),
                            "vector": [0.1, 0.2, 0.3, 0.4],
                            "payload": {"text": "Đã duyệt", "source_revision": "fixture"},
                        }
                    ]
                },
            )
            response.raise_for_status()

        def seed_s3():
            from app.core.storage import S3StorageDriver

            driver = S3StorageDriver(s3_url, "fixture-admin", secret, "fixture-documents")
            driver.s3_client.create_bucket(Bucket="fixture-documents")
            driver.s3_client.put_object(
                Bucket="fixture-documents",
                Key="documents/originals/nguồn.pdf",
                Body="Tài liệu gốc Unicode".encode(),
                ContentType="application/pdf",
            )

        await asyncio.to_thread(seed_s3)
        # The actual PG barrier blocks concurrent writers and is released after failure.
        async with exclusive_access():
            with pytest.raises(AppException) as error:
                async with shared_access():
                    raise AssertionError("Unexpected shared access")
            assert error.value.code == "BACKUP_MAINTENANCE"
        async with shared_access():
            pass
        stream_started, finish_stream = asyncio.Event(), asyncio.Event()

        async def streaming_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"token", "more_body": True})
            stream_started.set()
            await finish_stream.wait()
            await send({"type": "http.response.body", "body": b"done", "more_body": False})

        from httpx import ASGITransport

        async with httpx.AsyncClient(
            transport=ASGITransport(app=BackupMaintenanceMiddleware(streaming_app)),
            base_url="http://test",
        ) as client:
            streamed = asyncio.create_task(client.get(settings.API_PREFIX + "/fixture-stream"))
            await stream_started.wait()
            async with database_connection() as conn:
                assert not await conn.fetchval("SELECT pg_try_advisory_lock($1)", MAINTENANCE_LOCK)
            finish_stream.set()
            assert (await streamed).content == b"tokendone"

        async def failed_job(*args):
            raise ValueError("fixture worker failure")

        with pytest.raises(ValueError):
            await guard_worker(failed_job)({})
        async with exclusive_access():
            assert (await guard_worker(failed_job, periodic=True)({}))[
                "skipped"
            ] == "backup_maintenance"
        entry = await service.start_backup(
            "fixture-backup-password-only", "fixture-admin", "fixture-418"
        )
        completed = await wait_terminal(entry.id)
        assert completed.status == "completed", completed.error
        assert completed.verified_at and not completed.drill_at
        assert (
            completed.components["objects"] == 1 and completed.components["vector_collections"] == 1
        )
        # Phase two: real encrypted S3 copy/readback; credentials are provisioned externally.
        import json

        from app.modules.backups.catalogue import record_path
        from app.modules.backups.policy import BackupPolicy, save_policy

        credential_file = tmp_path / "external-s3-secret.json"
        credential_file.write_text(
            json.dumps({"access_key": "fixture-admin", "secret_key": secret}), encoding="utf-8"
        )
        credential_file.chmod(0o600)
        monkeypatch.setattr(
            settings, "BACKUP_REMOTE_CREDENTIALS_FILE", str(credential_file.resolve())
        )
        monkeypatch.setenv("BACKUP_REMOTE_CREDENTIALS_FILE", str(credential_file.resolve()))

        def prepare_remote_bucket():
            from app.core.storage import S3StorageDriver

            driver = S3StorageDriver(s3_url, "fixture-admin", secret, "fixture-backups")
            driver.s3_client.create_bucket(Bucket="fixture-backups")

        await asyncio.to_thread(prepare_remote_bucket)
        save_policy(BackupPolicy(remote_enabled=True, endpoint=s3_url, bucket="fixture-backups"))
        await service.start_recovery(entry.id, "", "copy", "fixture-admin", "fixture-424-copy")
        copied = await wait_terminal(entry.id)
        assert copied.status == "completed" and copied.remote_status == "verified", (
            copied.remote_error
        )
        assert copied.remote_sha256 == copied.sha256 and copied.remote_verified_at
        # Import the fixture archive through HTTP; then the independent runner verifies and drills it.
        from fastapi import FastAPI

        from app.modules.auth.dependencies import get_current_actor
        from app.modules.auth.schemas import AuthActor
        from app.modules.backups.router import router

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_actor] = lambda: AuthActor(
            username="fixture", roles=["AI.Admin"]
        )
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            uploaded = await client.post(
                "/backups/import",
                content=record_path(entry.id, ".qnubak").read_bytes(),
                headers={"Authorization": "Bearer fixture"},
            )
            assert uploaded.status_code == 201, uploaded.text
        imported_id = uploaded.json()["id"]
        assert uploaded.json()["status"] == "unverified"
        await service.start_recovery(
            imported_id,
            "fixture-backup-password-only",
            "drill",
            "fixture-admin",
            "fixture-424-import-drill",
        )
        imported = await wait_terminal(imported_id)
        assert imported.status == "completed" and imported.drill_at, imported.error
        failed = await service.start_recovery(
            entry.id, "wrong-fixture-password", "verify", "fixture-admin", "fixture-418-wrong"
        )
        failed = await wait_terminal(failed.id)
        assert failed.status == "failed" and "Mật khẩu" in failed.error
        await service.start_recovery(
            entry.id, "fixture-backup-password-only", "drill", "fixture-admin", "fixture-418-drill"
        )
        restored = await wait_terminal(entry.id)
        assert restored.status == "completed", restored.error
        assert restored.drill_at and restored.components["drill"]["provider_keys_checked"] == 2
        # No restore target can be submitted: source state remains intact.
        async with database_connection() as conn:
            assert (
                await conn.fetchval("SELECT review_status FROM repository_documents") == "reviewed"
            )
            assert await conn.fetchval("SELECT count(*) FROM knowledge_vector_generations") == 1
            await conn.execute(
                "CREATE TABLE job_records(status text, result jsonb); INSERT INTO job_records VALUES('queued','{}')"
            )
        pending = await service.start_backup(
            "fixture-backup-password-only", "fixture-admin", "fixture-418-pending"
        )
        failed = await wait_terminal(pending.id)
        assert failed.status == "failed" and "Còn job" in failed.error
        async with database_connection() as conn:
            await conn.execute("UPDATE job_records SET status='completed'")

        def remove_fixture_object():
            from app.core.storage import S3StorageDriver

            driver = S3StorageDriver(s3_url, "fixture-admin", secret, "fixture-documents")
            driver.s3_client.delete_object(
                Bucket="fixture-documents", Key="documents/originals/nguồn.pdf"
            )

        await asyncio.to_thread(remove_fixture_object)
        missing = await service.start_backup(
            "fixture-backup-password-only", "fixture-admin", "fixture-418-missing-file"
        )
        failed = await wait_terminal(missing.id)
        assert failed.status == "failed" and "thiếu" in failed.error
        # A due schedule defers while jobs are pending, then concurrent ticks dispatch at most once.
        from datetime import UTC, datetime, timedelta

        from app.modules.backups.policy import load_policy
        from app.modules.backups.scheduler import task_backup_schedule

        password_file = tmp_path / "external-backup-password.txt"
        password_file.write_text("fixture-backup-password-only", encoding="utf-8")
        password_file.chmod(0o600)
        monkeypatch.setattr(settings, "BACKUP_SCHEDULE_SECRET_FILE", str(password_file.resolve()))
        monkeypatch.setenv("BACKUP_SCHEDULE_SECRET_FILE", str(password_file.resolve()))
        async with database_connection() as conn:
            await conn.execute(
                "CREATE TABLE workflow_executions(status text); UPDATE job_records SET status='queued'"
            )
        policy = load_policy()
        policy.schedule_enabled = True
        policy.next_run_at = datetime.now(UTC) - timedelta(seconds=10)
        save_policy(policy)
        assert (await task_backup_schedule({}))["deferred"]
        assert load_policy().next_run_at < datetime.now(UTC)
        async with database_connection() as conn:
            await conn.execute("UPDATE job_records SET status='completed'")

        def replace_fixture_object():
            from app.core.storage import S3StorageDriver

            driver = S3StorageDriver(s3_url, "fixture-admin", secret, "fixture-documents")
            driver.s3_client.put_object(
                Bucket="fixture-documents",
                Key="documents/originals/nguồn.pdf",
                Body="Tài liệu gốc Unicode".encode(),
            )

        await asyncio.to_thread(replace_fixture_object)
        ticks = await asyncio.gather(task_backup_schedule({}), task_backup_schedule({}))
        dispatched = [tick["backup_id"] for tick in ticks if "backup_id" in tick]
        assert len(dispatched) == 1
        scheduled = await wait_terminal(dispatched[0])
        assert scheduled.status == "completed" and scheduled.remote_status == "verified", (
            scheduled.error or scheduled.remote_error
        )
        assert scheduled.origin == "schedule" and load_policy().last_backup_id == scheduled.id
    finally:
        await owned.cleanup()
