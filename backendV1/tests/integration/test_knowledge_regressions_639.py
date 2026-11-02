"""Independent review probes; synthetic files and a disposable PostgreSQL database only."""

import asyncio
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from qnu.adapters.storage.local import LocalBlobStore
from qnu.domains.knowledge.artifacts.files import build_storage_key
from qnu.domains.knowledge.sources.service import source_service
from qnu.domains.workspaces.models import Workspace
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.schema import SCHEMA_HEAD
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    as_actor,
    create_collection,
    pdf_bytes,
    upload_source,
    workspace_with_editor,
)


def test_changed_title_is_a_different_idempotent_request(client):
    ws = workspace_with_editor(client, "review-title")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Review title")
    first = upload_source(
        client, ws["id"], col["id"], title="Original title", idempotency_key="review-title-key"
    )
    assert first.status_code == 201
    second = upload_source(
        client, ws["id"], col["id"], title="Different title", idempotency_key="review-title-key"
    )
    assert second.status_code == 409, (
        f"Changed title accepted as replay: status={second.status_code}, "
        f"returned_title={second.json().get('source', {}).get('title')}"
    )


def test_failed_concurrent_writer_cannot_damage_committed_original(client, monkeypatch):
    ws = workspace_with_editor(client, "review-atomic")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Review atomic writes")
    payload = pdf_bytes("atomic-original")
    target = (
        Path(get_settings().LOCAL_STORAGE_PATH)
        / build_storage_key(ws["id"], col["id"], hashlib.sha256(payload).hexdigest())
    ).resolve()
    original_write = Path.write_bytes
    writes = 0

    def interrupted_write(path, data):
        nonlocal writes
        if path.parent.samefile(target.parent) and data == payload:
            writes += 1
            if writes == 2:
                original_write(path, data[:8])
                raise OSError("Injected interrupted disk write")
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", interrupted_write)

    async def scenario():
        first_written = asyncio.Event()
        second_waiting = asyncio.Event()
        release_second = asyncio.Event()

        class OrderedStore(LocalBlobStore):
            calls = 0

            async def put_bytes(self, key, data, content_type=None):
                self.calls += 1
                call = self.calls
                if call == 1:
                    await super().put_bytes(key, data, content_type)
                    first_written.set()
                    await second_waiting.wait()
                else:
                    second_waiting.set()
                    await release_second.wait()
                    await super().put_bytes(key, data, content_type)
                return key

        store = OrderedStore(get_settings().LOCAL_STORAGE_PATH)

        async def upload(key):
            async with AsyncSessionFactory() as db:
                workspace = await db.get(Workspace, ws["id"])
                return await source_service.upload(
                    db,
                    store,
                    workspace,
                    col["id"],
                    file_name="original.pdf",
                    title=None,
                    payload=payload,
                    max_bytes=10000,
                    actor=EDITOR,
                    idempotency_key=key,
                )

        first = asyncio.create_task(upload("atomic-first-key"))
        await asyncio.wait_for(first_written.wait(), 10)
        second = asyncio.create_task(upload("atomic-second-key"))
        result = await asyncio.wait_for(first, 10)
        release_second.set()
        error = (await asyncio.gather(second, return_exceptions=True))[0]
        assert getattr(error, "code", None) == "storage_unavailable"
        return result.source.id, result.revision.id

    source_id, revision_id = client.portal.call(scenario)
    response = client.get(
        f"{API}/workspaces/{ws['id']}/collections/{col['id']}"
        f"/sources/{source_id}/revisions/{revision_id}/content"
    )
    assert response.status_code == 200 and response.content == payload, (
        f"Previously committed original damaged by second writer: "
        f"HTTP={response.status_code}, error={response.json().get('code')}, "
        f"file_bytes={len(target.read_bytes())}, original_bytes={len(payload)}"
    )


def test_downgrade_cannot_mark_success_and_block_next_upgrade(client):
    ws = workspace_with_editor(client, "rollback-evidence")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Rollback evidence")
    payload = pdf_bytes("keep-original")
    uploaded = upload_source(client, ws["id"], col["id"], payload=payload).json()

    def alembic(command, revision):
        return subprocess.run(
            [sys.executable, "-m", "alembic", command, revision],
            capture_output=True,
            text=True,
            check=False,
        )

    async def current_version():
        from sqlalchemy import text

        async with AsyncSessionFactory() as db:
            return await db.scalar(text("SELECT version_num FROM alembic_version_backendv1"))

    head_before = client.portal.call(current_version)
    rollback = alembic("downgrade", "base")
    assert rollback.returncode != 0, (
        "Downgrade must not silently change history while keeping tables"
    )
    # Whichever migration owns the head must refuse to drop stored evidence.
    assert "evidence must be preserved" in rollback.stderr.lower()

    # The failed downgrade must leave the recorded revision untouched, not half-applied.
    assert client.portal.call(current_version) == head_before
    assert head_before == SCHEMA_HEAD

    upgraded = alembic("upgrade", "head")
    assert upgraded.returncode == 0, (
        "Successful no-op downgrade left knowledge tables and made next upgrade fail: "
        + upgraded.stderr[-500:]
    )
    original = client.get(
        f"{API}/workspaces/{ws['id']}/collections/{col['id']}"
        f"/sources/{uploaded['source']['id']}"
        f"/revisions/{uploaded['revision']['id']}/content"
    )
    assert original.status_code == 200 and original.content == payload


@pytest.mark.parametrize(
    "first_title, replay_title", [("  Original  ", "Original"), (None, "de-an.pdf")]
)
def test_title_fingerprint_uses_effective_persisted_metadata(client, first_title, replay_title):
    ws = workspace_with_editor(client, "normalized-title")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Normalized title")
    first = upload_source(
        client, ws["id"], col["id"], title=first_title, idempotency_key="normalize-title-key"
    )
    assert first.status_code == 201
    replay = upload_source(
        client, ws["id"], col["id"], title=replay_title, idempotency_key="normalize-title-key"
    )
    assert replay.status_code == 200
    assert replay.json()["source"]["id"] == first.json()["source"]["id"]


def test_old_fingerprint_replays_matching_title_without_rewriting_ledger(client):
    from sqlalchemy import select

    from qnu.domains.knowledge.models import KBUploadRequest

    ws = workspace_with_editor(client, "old-fingerprint")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Old fingerprint")
    uploaded = upload_source(
        client, ws["id"], col["id"], title="Original", idempotency_key="legacy-title-key"
    ).json()
    revision = uploaded["revision"]
    material = "|".join(
        [
            ws["id"],
            col["id"],
            "",
            revision["file_name"],
            revision["sha256"],
            str(revision["size_bytes"]),
        ]
    )
    legacy_hash = hashlib.sha256(material.encode()).hexdigest()

    async def ledger_hash(replace=False):
        async with AsyncSessionFactory() as db:
            row = (
                await db.execute(
                    select(KBUploadRequest).where(
                        KBUploadRequest.workspace_id == ws["id"],
                        KBUploadRequest.idempotency_key == "legacy-title-key",
                    )
                )
            ).scalar_one()
            if replace:
                row.request_hash = legacy_hash
                await db.commit()
            return row.request_hash

    client.portal.call(ledger_hash, True)
    replay = upload_source(
        client, ws["id"], col["id"], title="Original", idempotency_key="legacy-title-key"
    )
    assert replay.status_code == 200
    conflict = upload_source(
        client, ws["id"], col["id"], title="Changed", idempotency_key="legacy-title-key"
    )
    assert conflict.status_code == 409
    assert client.portal.call(ledger_hash) == legacy_hash


def test_revision_endpoint_rejects_title_instead_of_silently_ignoring_it(client):
    ws = workspace_with_editor(client, "revision-metadata")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Revision metadata")
    first = upload_source(client, ws["id"], col["id"], title="Original").json()
    url = f"{API}/workspaces/{ws['id']}/collections/{col['id']}/sources/{first['source']['id']}"
    response = client.post(
        url + "/revisions",
        data={"title": "Ignored metadata"},
        files={"file": ("new.pdf", pdf_bytes("v2"), "application/pdf")},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "revision_title_not_supported"
    detail = client.get(url).json()
    assert detail["title"] == "Original" and detail["revision_count"] == 1


def test_same_key_writers_do_not_fail_storage_under_contention(client):
    from qnu.domains.knowledge.sources.service import UploadOutcome
    from qnu.platform.errors import Conflict
    from tests.integration.test_knowledge_concurrency import _two_uploads

    ws = workspace_with_editor(client, "contended-uploads")
    as_actor(EDITOR)
    for attempt in range(8):
        col = create_collection(client, ws["id"], f"Concurrent {attempt}")
        results = _two_uploads(
            client,
            ws["id"],
            col["id"],
            payload=pdf_bytes(str(attempt)),
            keys=(f"round-{attempt}-key", f"round-{attempt}-key"),
        )
        for result in results:
            if isinstance(result, BaseException) and not isinstance(result, Conflict):
                raise result
        assert all(isinstance(result, (UploadOutcome, Conflict)) for result in results), results
