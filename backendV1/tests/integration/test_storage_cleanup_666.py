"""GC is opt-in, scoped, delayed and conditional; originals/raw never qualify."""

import hashlib
import os
from datetime import timedelta

import pytest

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.ocr.models import OcrRunArtifact
from qnu.domains.operations.models import StorageCleanupAction
from qnu.platform.database import AsyncSessionFactory
from tests.integration.compiler_support import processed_input
from tests.integration.knowledge_support import API, EDITOR, OUTSIDER, PLATFORM, as_actor


def setup(client):
    from qnu.main import app

    data = processed_input(client, code="gc-666")
    ws = data["workspace"]["id"]
    blob = app.state.container.blob_store
    key = f"v1/workspaces/{ws}/ocr/{data['ocr_run_id']}/markdown/orphan.md"
    client.portal.call(blob.put_bytes, key, b"orphan", "text/markdown")
    path = blob._path(key)
    old = (utcnow() - timedelta(hours=48)).timestamp()
    os.utime(path, (old, old))
    as_actor(PLATFORM)
    return {
        **data,
        "ops": f"{API}/workspaces/{ws}/operations/storage-cleanups",
        "blob": blob,
        "key": key,
        "old": old,
    }


def preview(client, data):
    return client.post(
        data["ops"] + "/previews", json={"reason": "Remove unreferenced derived data"}
    )


def accept(client, data, response, key="gc-one"):
    p = response.json()
    return client.post(
        data["ops"] + "/actions",
        json={"preview_id": p["id"], "preview_sha256": p["preview_sha256"]},
        headers={"Idempotency-Key": key},
    )


def test_gc_deletes_only_old_unreferenced_derivative_and_replay_is_stable(client):
    data = setup(client)
    blob = data["blob"]
    raw = data["key"].replace("/markdown/", "/raw_response/")
    fresh = data["key"].replace("orphan.md", "fresh.md")
    for key in [raw, fresh]:
        client.portal.call(blob.put_bytes, key, b"keep", None)
    os.utime(blob._path(raw), (data["old"], data["old"]))
    p = preview(client, data)
    assert p.status_code == 200, p.text
    assert len(p.json()["files"]) == 1 and p.json()["total_bytes"] == len(b"orphan")
    result = accept(client, data, p)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "completed"
    assert not client.portal.call(blob.exists, data["key"])
    assert client.portal.call(blob.exists, raw) and client.portal.call(blob.exists, fresh)
    assert accept(client, data, p).json() == result.json()
    # Every referenced original/raw/canonical object remains readable and unchanged.
    from qnu.domains.operations.backups.snapshot import freeze

    async def refs():
        async with AsyncSessionFactory() as db:
            _, references = await freeze(db, data["workspace"]["id"])
            return references

    for key, expected in client.portal.call(refs).items():
        if expected:
            assert hashlib.sha256(client.portal.call(blob.get_bytes, key)).hexdigest() == expected


@pytest.mark.parametrize("change", ["bytes", "reference", "expiry"])
def test_gc_rechecks_bytes_references_and_expiry(client, change):
    data = setup(client)
    p = preview(client, data)
    assert p.status_code == 200, p.text
    if change == "bytes":
        client.portal.call(data["blob"].put_bytes, data["key"], b"new bytes", None)
    else:

        async def mutate():
            async with AsyncSessionFactory() as db:
                if change == "reference":
                    db.add(
                        OcrRunArtifact(
                            id="art_gc_reference",
                            run_id=data["ocr_run_id"],
                            kind="markdown",
                            page_no=42,
                            blob_key=data["key"],
                            sha256=hashlib.sha256(b"orphan").hexdigest(),
                            size_bytes=6,
                            content_type="text/markdown",
                        )
                    )
                else:
                    row = await db.get(StorageCleanupAction, p.json()["id"])
                    row.expires_at = utcnow() - timedelta(seconds=1)
                await db.commit()

        client.portal.call(mutate)
    result = accept(client, data, p)
    assert result.status_code == 409, result.text
    assert client.portal.call(data["blob"].exists, data["key"])


def test_gc_requires_admin_and_the_original_approver(client):
    data = setup(client)
    p = preview(client, data)
    as_actor(EDITOR)
    assert preview(client, data).status_code == 403
    assert accept(client, data, p).status_code == 403
    as_actor(OUTSIDER)
    assert accept(client, data, p).status_code == 404
    assert client.portal.call(data["blob"].exists, data["key"])


def test_gc_storage_outage_keeps_pending_intent_for_same_key_retry(client, monkeypatch):
    from qnu.platform.errors import DependencyUnavailable

    data = setup(client)
    p = preview(client, data)
    original = data["blob"].delete_if_unchanged

    async def fail(*args):
        raise DependencyUnavailable("Synthetic outage", code="storage_unavailable")

    monkeypatch.setattr(data["blob"], "delete_if_unchanged", fail)
    assert accept(client, data, p).status_code == 503
    status = client.get(data["ops"] + "/actions/" + p.json()["id"])
    assert status.json()["status"] == "pending"
    monkeypatch.setattr(data["blob"], "delete_if_unchanged", original)
    assert accept(client, data, p).json()["status"] == "completed"
