"""Scoped observed jobs, actor-bound recovery and verifiable evidence archives."""

import io
import json
import zipfile
from datetime import timedelta

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    OUTSIDER,
    PLATFORM,
    add_member,
    as_actor,
)
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.workflow_support import mutate


def operations(client):
    data = processed_input(client, code="operations")
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    as_actor(PLATFORM)
    data["ops"] = f"{API}/workspaces/{data['workspace']['id']}/operations"
    return data


def backup(client, data, **body):
    use_queue(FakeJobQueue())
    result = client.post(
        data["ops"] + "/backups", json=body, headers={"Idempotency-Key": "backup-one"}
    )
    assert result.status_code == 202, result.text
    return result.json()


def execute_backup(client, backup_id):
    from qnu.main import app
    from qnu.workers.tasks.operations import evidence_backup_job

    return client.portal.call(evidence_backup_job, {"container": app.state.container}, backup_id)


def test_jobs_filters_scope_counts_and_actual_progress(client):
    data = operations(client)
    result = client.get(data["ops"] + "/jobs?kind=ocr&status=completed&limit=1")
    assert result.status_code == 200, result.text
    row = result.json()["items"][0]
    assert row["id"] == data["ocr_run_id"] and row["progress_total"] == row["progress_done"] == 1
    assert not row["recovery_allowed"]
    assert client.get(data["ops"] + "/summary").json()["usage"]
    as_actor(OUTSIDER)
    assert client.get(data["ops"] + "/jobs").status_code == 404
    as_actor(MEMBER)
    assert client.get(data["ops"] + "/jobs").status_code == 403
    as_actor(EDITOR)
    assert client.get(data["ops"] + "/backups").status_code == 403


def test_backup_contains_original_raw_and_pinned_metadata_without_keys(client):
    data = operations(client)
    row = backup(client, data)
    assert execute_backup(client, row["id"]) == "completed"
    assert execute_backup(client, row["id"]) == "not_claimed"
    url = data["ops"] + "/backups/" + row["id"]
    response = client.get(url + "/download")
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        snapshot = json.loads(archive.read("snapshot.json"))
        assert "provider_keys" not in snapshot["tables"] and "providers" not in snapshot["tables"]
        assert (
            "kb_source_revisions" in snapshot["tables"]
            and "ocr_run_artifacts" in snapshot["tables"]
        )
        assert all(
            e["key"].startswith("v1/workspaces/" + data["workspace"]["id"] + "/")
            for e in manifest["objects"]
        )
        assert any(archive.read(e["entry"]).startswith(b"%PDF") for e in manifest["objects"])
        assert not manifest["credentials_included"]
    assert client.get(url + "/verify").json()["verified"]
    again = client.post(
        data["ops"] + "/backups", json={}, headers={"Idempotency-Key": "backup-one"}
    )
    assert again.json()["id"] == row["id"]
    assert client.get(data["ops"] + "/retention").json()["automatic_delete"] is False
    assert client.post(url + "/delete-preview", json={"reason": "Delete"}).status_code == 409


def test_recovery_requires_current_preview_and_queue_outage_remains_pending(client):
    from qnu.domains.operations.jobs.actions import dispatch
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    data = operations(client)
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue(failing=True))
        req = request_compile(client, data)
        assert req.status_code == 201
        run_id = req.json()["run"]["id"]
        url = data["ops"] + "/jobs/compiler/" + run_id
        preview = client.post(
            url + "/recovery-preview", json={"reason": "Giao lại khi queue có kết nối"}
        )
        assert preview.status_code == 200, preview.text
        p = preview.json()
        result = client.post(
            data["ops"] + "/actions",
            json={"preview_id": p["id"], "preview_sha256": p["preview_sha256"]},
            headers={"Idempotency-Key": "recover"},
        )
        assert result.status_code == 202 and result.json()["status"] == "pending", result.text
        queue = FakeJobQueue()

        async def deliver():
            async with AsyncSessionFactory() as db:
                return await dispatch(db, p["id"], queue)

        assert client.portal.call(deliver)
        assert not client.portal.call(deliver)
        assert len(chat.requests) == 0
        assert client.get(url).json()["status"] == "queued"
        # Worker retains the original requester's membership, model and checkpoint checks.
        from qnu.workers.tasks.compilation import compile_run

        assert (
            client.portal.call(compile_run, {"container": app.state.container}, run_id)
            == "completed"
        )
        assert len(chat.requests) == 1
        assert client.post(url + "/recovery-preview", json={"reason": "Again"}).status_code == 409


def test_backup_delete_needs_expiry_preview_and_never_deletes_source(client):
    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.operations.models import EvidenceBackup
    from qnu.main import app
    from qnu.workers.tasks.operations import evidence_backup_delete

    data = operations(client)
    row = backup(client, data, retention_days=1)
    assert execute_backup(client, row["id"]) == "completed"
    mutate(client, EvidenceBackup, row["id"], retain_until=utcnow() - timedelta(seconds=1))
    url = data["ops"] + "/backups/" + row["id"]
    p = client.post(url + "/delete-preview", json={"reason": "Đến hạn giữ bản sao"}).json()
    result = client.post(
        data["ops"] + "/actions",
        json={"preview_id": p["id"], "preview_sha256": p["preview_sha256"]},
        headers={"Idempotency-Key": "delete"},
    )
    assert result.status_code == 202, result.text
    assert (
        client.portal.call(
            evidence_backup_delete, {"container": app.state.container}, row["id"], p["id"]
        )
        == "deleted"
    )
    assert client.get(url + "/download").status_code == 409
    source = f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}/sources/{data['source']['id']}/revisions/{data['revision']['id']}/content"
    assert client.get(source).status_code == 200
