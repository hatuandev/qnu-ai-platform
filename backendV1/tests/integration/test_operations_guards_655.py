"""Recovery and backup approvals remain bound to current state, membership and evidence."""

from datetime import timedelta

import pytest

from tests.integration.compiler_support import FakeChat, chat_provider, request_compile
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.test_operations_655 import backup, execute_backup, operations
from tests.integration.workflow_support import mutate


@pytest.mark.parametrize("status", ["failed", "uncertain", "running"])
def test_recovery_never_resubmits_terminal_or_leased_model_jobs(client, status):
    from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow

    data = operations(client)
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue(failing=True))
        run = request_compile(client, data).json()["run"]["id"]
        mutate(
            client,
            CompilationRun,
            run,
            status=status,
            lease_expires_at=utcnow() + timedelta(minutes=5),
        )
        response = client.post(
            data["ops"] + "/jobs/compiler/" + run + "/recovery-preview", json={"reason": "Recover"}
        )
        assert response.status_code == 409, response.text
        assert not chat.requests


@pytest.mark.parametrize("change", ["hash", "state", "expiry", "actor"])
def test_recovery_accept_rejects_stale_or_foreign_approval(client, change):
    from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
    from qnu.domains.operations.models import OperationAction

    data = operations(client)
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue(failing=True))
        run = request_compile(client, data).json()["run"]["id"]
        p = client.post(
            data["ops"] + "/jobs/compiler/" + run + "/recovery-preview", json={"reason": "Recover"}
        ).json()
        if change == "hash":
            p["preview_sha256"] = "0" * 64
        elif change == "state":
            mutate(client, CompilationRun, run, attempt_count=1)
        elif change == "expiry":
            mutate(client, OperationAction, p["id"], expires_at=utcnow() - timedelta(seconds=1))
        else:
            as_actor(PLATFORM)
        response = client.post(
            data["ops"] + "/actions",
            json={"preview_id": p["id"], "preview_sha256": p["preview_sha256"]},
            headers={"Idempotency-Key": "accept"},
        )
        assert response.status_code == (404 if change == "actor" else 409), response.text
        assert not chat.requests


def test_revoked_backup_creator_cannot_publish_archive(client):
    data = operations(client)
    row = backup(client, data)
    members = client.get(f"{API}/workspaces/{data['workspace']['id']}/members").json()["items"]
    member = next(m for m in members if m["actor_ref"] == PLATFORM.actor_id)
    assert (
        client.delete(
            f"{API}/workspaces/{data['workspace']['id']}/members/{member['id']}"
        ).status_code
        == 200
    )
    assert execute_backup(client, row["id"]) == "failed"
    assert client.get(data["ops"] + "/backups/" + row["id"] + "/download").status_code == 409


def test_backup_includes_both_saved_post_ocr_artifacts(client):
    import io
    import json
    import zipfile

    data = operations(client)
    text_url = data["url"].replace(
        "/compilation-runs",
        "/sources/"
        + data["source"]["id"]
        + "/revisions/"
        + data["revision"]["id"]
        + "/processing-runs/"
        + data["ocr_run_id"]
        + "/text-review",
    )
    text = client.get(text_url).json()
    unit = next(u for u in text["units"] if u["kind"] != "table_cell" and u["text"].strip())
    saved = client.post(
        text_url,
        json={
            "expected_version": text["version"],
            "expected_sha256": text["canonical_sha256"],
            "changes": [
                {
                    "evidence_id": unit["evidence_id"],
                    "before": unit["text"],
                    "after": unit["text"] + "\n",
                }
            ],
        },
        headers={"Idempotency-Key": "text-backup"},
    )
    assert saved.status_code == 200, saved.text
    row = backup(client, data)
    assert execute_backup(client, row["id"]) == "completed"
    response = client.get(data["ops"] + "/backups/" + row["id"] + "/download")
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        corrected = [
            item
            for item in manifest["objects"]
            if item["key"].startswith("ocr-text/" + data["workspace"]["id"] + "/")
        ]
        assert len(corrected) == 2
        assert {item["key"].rsplit(".", 1)[-1] for item in corrected} == {"json", "md"}


@pytest.mark.parametrize(
    "body",
    [
        {"retrieval_mode": "hybrid", "candidate_k": 1, "top_k": 5},
        {"retrieval_mode": "dense", "rerank_provider_id": "unused"},
    ],
)
def test_answer_retrieval_options_fail_as_request_validation(client, body):
    data = operations(client)
    as_actor(EDITOR)
    base = f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
    assert client.post(base + "/answers", json={"question": "Câu hỏi", **body}).status_code == 422
