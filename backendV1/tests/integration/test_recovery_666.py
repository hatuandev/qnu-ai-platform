# ruff: noqa: F811
"""An encrypted bundle restores real DB rows, original bytes, keys and searchable vectors."""

import hashlib
import json
import os
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from qnu.adapters.storage.local import LocalBlobStore
from qnu.domains.knowledge.index.schemas import SearchRequest
from qnu.domains.knowledge.index.search import search
from qnu.domains.modelops.models import ProviderKey
from qnu.domains.operations.recovery import archive, service
from qnu.platform.config import get_settings
from qnu.platform.crypto import decrypt
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import Conflict, Forbidden
from tests.integration.index_support import execute_index
from tests.integration.knowledge_support import API, EDITOR, MEMBER, PLATFORM, as_actor
from tests.integration.test_answers_api_648 import ready  # noqa: F401
from tests.integration.test_index_api_647 import indexed  # noqa: F401
from tests.integration.test_lifecycle_659 import accept, preview

KEY = "test-infrastructure-recovery-" + "x" * 40


def quiesce(client, data):
    as_actor(PLATFORM)
    base = f"{API}/workspaces/{data['workspace']['id']}/operations"
    jobs = client.get(base + "/jobs?limit=100").json()["items"]
    for job in jobs:
        if job["status"] in {"queued", "running"}:
            result = accept(
                client,
                data["workspace"],
                preview(
                    client, data["workspace"], "job", job["id"], "cancel", job_kind=job["kind"]
                ),
                key="quiesce-" + job["id"],
            )
            assert result.status_code == 200, result.text


def capture(client, data):
    from qnu.main import app

    async def run():
        async with AsyncSessionFactory() as db:
            return await service.capture(db, app.state.container.blob_store, PLATFORM, KEY)

    return client.portal.call(run)


def test_full_recovery_into_new_targets_keeps_originals_credentials_and_search(
    client, indexed, tmp_path, monkeypatch
):
    from qnu.main import app

    data = indexed
    assert execute_index(client, data["index_run"]["id"]) == "completed"
    as_actor(EDITOR)
    replacement = client.post(
        data["base"] + "/indexing-runs", json={}, headers={"Idempotency-Key": "second-for-recovery"}
    )
    assert replacement.status_code == 201, replacement.text
    active_run_id = replacement.json()["run"]["id"]
    assert execute_index(client, active_run_id) == "completed"

    async def source_names():
        from qnu.domains.knowledge.index.models import IndexRun

        async with AsyncSessionFactory() as db:
            return {
                row.id: row.vector_collection for row in (await db.scalars(select(IndexRun))).all()
            }

    source_rows = client.portal.call(source_names)
    original_vector_name = source_rows[data["index_run"]["id"]]
    source_vector_names = set(source_rows.values())
    quiesce(client, data)
    # Exercise an upgraded installation: pre-existing model rows precede their
    # newly created connection parents, while model IDs and keys stay unchanged.
    import importlib.util
    from pathlib import Path

    from qnu.platform.database import engine

    spec = importlib.util.spec_from_file_location(
        "recovery_provider_migration", Path("alembic/versions/0005_provider_connections.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    async def convert_connections():
        async with engine.begin() as conn:
            await conn.run_sync(migration.convert_legacy_providers)

    client.portal.call(convert_connections)
    bundle = capture(client, data)
    _snapshot, objects = archive.unpack(bundle, KEY)
    assert b"embedding-test-secret" not in bundle
    assert any(name.startswith("v1/workspaces/") for name in objects)
    restored_blob = LocalBlobStore(str(tmp_path / "restored"))
    name = "qnu_v1_restore_" + uuid.uuid4().hex[:16]
    url = make_url(get_settings().DATABASE_URL).set(database=name)
    rendered = url.render_as_string(hide_password=False)
    vectors = app.state.container.vector_store
    created = []
    ensure = vectors.ensure_collection

    async def track(collection, *args, **kwargs):
        created.append(collection)
        return await ensure(collection, *args, **kwargs)

    monkeypatch.setattr(vectors, "ensure_collection", track)
    plan = service.plan(bundle, KEY, rendered, restored_blob, vectors)
    assert plan["objects"] == len(objects)

    async def run():
        engine = None
        try:
            result = await service.restore(
                bundle, KEY, rendered, restored_blob, vectors, PLATFORM, plan["confirmation_sha256"]
            )
            assert result["status"] == "restored" and not result["workers_started"]
            for key, original in objects.items():
                assert (
                    hashlib.sha256(await restored_blob.get_bytes(key)).hexdigest()
                    == hashlib.sha256(original).hexdigest()
                )
            engine = create_async_engine(rendered)
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                from qnu.domains.knowledge.index.models import IndexRun

                restored_runs = list((await db.scalars(select(IndexRun))).all())
                assert not {row.vector_collection for row in restored_runs} & source_vector_names
                from qnu.domains.lifecycle import service as lifecycle
                from qnu.domains.lifecycle.schemas import AcceptRequest, PreviewRequest

                receipt = await lifecycle.preview(
                    db,
                    restored_blob,
                    PLATFORM,
                    data["workspace"]["id"],
                    PreviewRequest(
                        kind="index",
                        resource_id=data["index_run"]["id"],
                        action="cleanup",
                        reason="Cleanup restored inactive generation only",
                    ),
                )
                await lifecycle.accept(
                    db,
                    restored_blob,
                    vectors,
                    None,
                    PLATFORM,
                    data["workspace"]["id"],
                    AcceptRequest(preview_id=receipt.id, preview_sha256=receipt.preview_sha256),
                    "restored-cleanup",
                )
                assert await vectors.collection_exists(original_vector_name)
                keys = list((await db.scalars(select(ProviderKey))).all())
                assert keys and all(decrypt(row.secret_encrypted) for row in keys)
                found = await search(
                    db,
                    restored_blob,
                    app.state.container.embedding_model,
                    vectors,
                    EDITOR,
                    data["workspace"]["id"],
                    data["collection"]["id"],
                    SearchRequest(query="Chỉ tiêu năm 2024"),
                )
                assert found.hits and all(hit.citations for hit in found.hits)
            with pytest.raises(Conflict):
                await service.restore(
                    bundle,
                    KEY,
                    rendered,
                    restored_blob,
                    vectors,
                    PLATFORM,
                    plan["confirmation_sha256"],
                )
        finally:
            if engine:
                await engine.dispose()
            for collection in created:
                await vectors.delete_collection(collection)
            admin = await service.connection(url, "postgres")
            try:
                assert name.startswith("qnu_v1_restore_") and len(name) == 31
                if await admin.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", name):
                    await admin.execute(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=$1 AND pid<>pg_backend_pid()",
                        name,
                    )
                    await admin.execute(f'DROP DATABASE "{name}"')
            finally:
                await admin.close()

    client.portal.call(run)
    assert client.get(data["base"] + "/indexing-runs/" + active_run_id).json()["is_active"]


def test_recovery_rejects_serving_target_wrong_confirmation_and_non_admin(
    client, indexed, tmp_path
):
    from qnu.main import app

    data = indexed
    assert execute_index(client, data["index_run"]["id"]) == "completed"
    quiesce(client, data)
    bundle = capture(client, data)
    blob = LocalBlobStore(str(tmp_path / "new-target"))
    vectors = app.state.container.vector_store
    with pytest.raises(Conflict):
        service.plan(bundle, KEY, get_settings().DATABASE_URL, blob, vectors)
    url = (
        make_url(get_settings().DATABASE_URL)
        .set(database="qnu_v1_restore_" + uuid.uuid4().hex[:16])
        .render_as_string(hide_password=False)
    )
    plan = service.plan(bundle, KEY, url, blob, vectors)

    async def checks():
        with pytest.raises(Conflict):
            await service.restore(bundle, KEY, url, blob, vectors, PLATFORM, "0" * 64)
        with pytest.raises(Forbidden):
            await service.restore(
                bundle, KEY, url, blob, vectors, MEMBER, plan["confirmation_sha256"]
            )
        admin = await service.connection(make_url(url), "postgres")
        try:
            assert not await admin.fetchval(
                "SELECT 1 FROM pg_database WHERE datname=$1", make_url(url).database
            )
        finally:
            await admin.close()

    client.portal.call(checks)


def test_recovery_backup_refuses_active_jobs_and_missing_sources(client, indexed):
    from qnu.main import app

    async def busy():
        async with AsyncSessionFactory() as db:
            with pytest.raises(Conflict) as error:
                await service.capture(db, app.state.container.blob_store, PLATFORM, KEY)
            assert error.value.code == "recovery_jobs_active"

    client.portal.call(busy)


def test_operator_cli_backup_and_preview_use_authenticated_complete_schema(
    client, indexed, tmp_path
):
    from qnu.domains.identity.dev_gate import issue_dev_token
    from qnu.platform.ownership import V1_TABLES

    data = indexed
    assert execute_index(client, data["index_run"]["id"]) == "completed"
    quiesce(client, data)
    token, _actor = issue_dev_token(get_settings().DEV_ACCESS_PASSWORD)
    url = make_url(get_settings().DATABASE_URL).set(
        database="qnu_v1_restore_" + uuid.uuid4().hex[:16]
    )
    env = {
        **os.environ,
        "RECOVERY_ACCESS_TOKEN": token,
        "RECOVERY_ENCRYPTION_KEY": KEY,
        "RECOVERY_DATABASE_URL": url.render_as_string(hide_password=False),
    }
    bundle = tmp_path / "operator.qnu"
    result = subprocess.run(
        [sys.executable, "scripts/recovery_bundle.py", "backup", "--bundle", str(bundle)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    snapshot, _objects = archive.unpack(bundle.read_bytes(), KEY)
    assert set(snapshot["tables"]) == set(V1_TABLES)
    assert snapshot["tables"]["chat_assistants"] == []
    preview_result = subprocess.run(
        [
            sys.executable,
            "scripts/recovery_bundle.py",
            "preview",
            "--bundle",
            str(bundle),
            "--target-storage",
            str(tmp_path / "new-cli-target"),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert preview_result.returncode == 0, preview_result.stdout + preview_result.stderr
    preview_body = json.loads(preview_result.stdout)
    assert preview_body["tables"] == len(V1_TABLES) and preview_body["confirmation_sha256"]
