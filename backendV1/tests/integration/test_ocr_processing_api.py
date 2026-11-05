"""Acceptance for the PDF/DOCX processing flow: run, worker, artifacts, API reads.

Every test drives the real HTTP stack and a real PostgreSQL database. The OCR provider
is a loopback HTTP server (a mock provider, not a live Nemotron run).
"""

from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from tests.integration.knowledge_support import (
    API,
    EDITOR,
    OUTSIDER,
    PLATFORM,
    REVIEWER,
    add_member,
    add_revision,
    as_actor,
    create_workspace,
    workspace_with_editor,
)
from tests.integration.ocr_support import (
    FakeJobQueue,
    FakeNemotron,
    docx_with_table,
    execute_now,
    ocr_blocks,
    prepare_source,
    real_pdf,
    request_run,
    runs_url,
    set_quota,
    setup_ocr_provider,
    use_queue,
)


def _xlsx_bytes() -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return buffer.getvalue()


def _workspace_with_document(
    client: TestClient,
    code: str,
    payload: bytes | None = None,
    *,
    filename: str = "phu-luc-01.pdf",
):
    workspace = workspace_with_editor(client, code)
    as_actor(EDITOR)
    collection, source, revision = prepare_source(
        client, workspace["id"], f"Kho {code}", payload=payload, filename=filename
    )
    return workspace, collection, source, revision


def test_processing_requires_authentication(client: TestClient) -> None:
    workspace, collection, source, revision = _workspace_with_document(client, "ocr-auth")
    as_actor(None)
    response = client.post(
        runs_url(workspace["id"], collection["id"], source["id"], revision["id"])
    )
    assert response.status_code == 401


def test_reviewer_cannot_request_processing(client: TestClient) -> None:
    workspace, collection, source, revision = _workspace_with_document(client, "ocr-role")
    as_actor(REVIEWER)
    response = request_run(client, workspace["id"], collection["id"], source["id"], revision["id"])
    assert response.status_code == 403
    assert response.json()["code"] == "workspace_forbidden"


def test_unsupported_format_is_reported_explicitly(client: TestClient) -> None:
    # A .txt file is legitimately stored by the knowledge module but cannot be rendered
    # into page images, so processing must say so instead of pretending to work.
    workspace, collection, source, revision = _workspace_with_document(
        client,
        "ocr-txt",
        payload="# Ghi chú\n\nNội dung văn bản thuần.\n".encode(),
        filename="ghi-chu.txt",
    )
    as_actor(EDITOR)
    response = request_run(client, workspace["id"], collection["id"], source["id"], revision["id"])
    assert response.status_code == 415
    assert response.json()["code"] == "processing_unsupported_format"

    runs = client.get(runs_url(workspace["id"], collection["id"], source["id"], revision["id"]))
    assert runs.status_code == 200
    assert runs.json()["meta"]["total"] == 0


def test_pdf_flow_produces_pinned_evidence(client: TestClient) -> None:
    with FakeNemotron() as fake:
        fake.responses = [
            ocr_blocks("PHU LUC 01|Title", "Noi dung trang mot|Text"),
            ocr_blocks("Trang hai|Text"),
        ]
        workspace, collection, source, revision = _workspace_with_document(
            client, "ocr-pdf", payload=real_pdf(["PHU LUC 01", "Trang hai"])
        )
        provider = setup_ocr_provider(client, workspace["id"], fake.base_url)
        as_actor(EDITOR)
        queue = FakeJobQueue()
        created = request_run(
            client,
            workspace["id"],
            collection["id"],
            source["id"],
            revision["id"],
            queue=queue,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        run = body["run"]
        assert run["status"] == "queued"
        assert body["dispatched"] is True
        assert queue.jobs and queue.jobs[0]["job_id"].startswith(f"qnu:v1:ocr:{run['id']}:")

        outcome = execute_now(client, run["id"])
        assert outcome.status == "completed", outcome

        detail = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run['id']}"
        )
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["status"] == "completed"
        assert detail_body["pages_total"] == 2
        assert detail_body["pages_done"] == 2
        assert detail_body["pages_failed"] == 0
        assert detail_body["provider_id"] == provider["id"]
        assert detail_body["usage_tokens"] == 280
        assert [page["status"] for page in detail_body["pages"]] == ["completed", "completed"]

        document = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run['id']}/document"
        )
        assert document.status_code == 200
        canonical = json.loads(document.content)
        assert canonical["schema_version"] == "qnu.ocr.document/v1"
        assert canonical["identity"]["revision_id"] == revision["id"]
        assert canonical["identity"]["source_sha256"] == revision["sha256"]
        assert canonical["identity"]["generation"] == 1
        assert canonical["processing"]["provider"]["provider_id"] == provider["id"]
        assert canonical["processing"]["renderer"]["dpi"] == 144
        assert len(canonical["pages"]) == 2
        first = canonical["pages"][0]
        assert first["blocks"][0]["text"] == "PHU LUC 01"
        assert first["blocks"][0]["bbox"]["units"] == "normalized_0_1"
        assert first["image"]["sha256"]
        assert document.headers["etag"] == f'"{hashlib.sha256(document.content).hexdigest()}"'

        evidence = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run['id']}/evidence"
        )
        assert evidence.status_code == 200
        snapshot = evidence.json()
        assert snapshot["identity"]["run_id"] == run["id"]
        assert snapshot["validation"]["ok"] is True
        assert snapshot["checks"]["pages_completed"] == 2
        kinds = {artifact["kind"] for artifact in snapshot["artifacts"]}
        assert {"page_image", "raw_response", "canonical_json", "markdown", "manifest"} <= kinds
        assert any(key.startswith("ev_p001_b") for key in snapshot["evidence"])

        markdown = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run['id']}/markdown"
        )
        assert markdown.status_code == 200
        assert "<!-- page 1 -->" in markdown.text
        assert "PHU LUC 01" in markdown.text

        image = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}"
            f"/{run['id']}/pages/1/image"
        )
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/png"
        assert hashlib.sha256(image.content).hexdigest() == first["image"]["sha256"]

        assert len(fake.requests) == 2
        assert fake.requests[0]["authorization"] == "Bearer nemotron-test-secret"
        assert fake.requests[0]["path"].endswith("/v1/chat/completions")
        assert fake.requests[0]["body"]["model"] == "nemotron-parse"
        assert canonical["limits"]["max_output_tokens"] is None
        assert all(
            request["body"]["max_tokens"] == provider["token_limits"]["max_output_tokens"]
            for request in fake.requests
        )


def test_docx_table_keeps_spans_values_and_footnote(client: TestClient) -> None:
    with FakeNemotron() as fake:
        workspace = workspace_with_editor(client, "ocr-docx")
        as_actor(EDITOR)
        collection, source, revision = prepare_source(
            client,
            workspace["id"],
            "Kho DOCX",
            payload=docx_with_table(),
            filename="phu-luc-01.docx",
        )
        setup_ocr_provider(client, workspace["id"], fake.base_url)
        created = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        )
        run_id = created.json()["run"]["id"]
        outcome = execute_now(client, run_id)
        assert outcome.status == "completed", outcome
        assert fake.requests == []

        document = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run_id}/document"
        )
        canonical = json.loads(document.content)
        table_block = next(block for block in canonical["pages"][0]["blocks"] if block.get("table"))
        table = table_block["table"]
        assert table["status"] == "parsed"
        assert table["column_count"] == 4
        headers = table["rows"][0]
        assert [cell["header"] for cell in headers] == [True, True, True]
        assert headers[-1]["col_span"] == 2
        assert [cell["text"] for cell in table["rows"][1]][-2:] == ["2023", "2024"]
        assert all(cell["header"] for cell in table["rows"][1])
        values = table["rows"][2]
        assert [cell["text"] for cell in values] == ["1", "Chỉ tiêu tuyển sinh", "0", "-"]
        assert table["rows"][3][2]["text"] == ""
        footnote = next(
            block for block in canonical["pages"][0]["blocks"] if block["type"] == "footnote"
        )
        assert "Ghi chú" in footnote["text"]

        manifest = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run_id}/manifest"
        ).json()
        assert manifest["processing"]["renderer"]["name"] == "docling"
        assert manifest["validation"]["ok"] is True


def test_new_generation_keeps_previous_run_and_revision(client: TestClient) -> None:
    with FakeNemotron() as fake:
        workspace, collection, source, revision = _workspace_with_document(
            client, "ocr-regen", payload=real_pdf(["Ban goc"])
        )
        setup_ocr_provider(client, workspace["id"], fake.base_url)
        as_actor(EDITOR)
        first = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        ).json()["run"]
        assert execute_now(client, first["id"]).status == "completed"

        replay = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        )
        assert replay.status_code == 200
        assert replay.json()["created"] is False
        assert replay.json()["run"]["id"] == first["id"]

        second = request_run(
            client,
            workspace["id"],
            collection["id"],
            source["id"],
            revision["id"],
            body={"force": True},
        )
        # An explicit reprocess creates a new generation even though the old one is complete.
        assert second.status_code == 201
        assert second.json()["run"]["generation"] == 2
        assert second.json()["run"]["id"] != first["id"]

        document = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}"
            f"/{first['id']}/document"
        )
        assert document.status_code == 200
        assert json.loads(document.content)["identity"]["generation"] == 1

        revisions = client.get(
            f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
            f"/sources/{source['id']}/revisions"
        ).json()
        assert len(revisions) == 1
        assert revisions[0]["sha256"] == revision["sha256"]


def test_old_run_stays_pinned_after_a_new_revision(client: TestClient) -> None:
    with FakeNemotron() as fake:
        workspace, collection, source, revision = _workspace_with_document(
            client, "ocr-pin", payload=real_pdf(["Ban goc"])
        )
        setup_ocr_provider(client, workspace["id"], fake.base_url)
        as_actor(EDITOR)
        run = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        ).json()["run"]
        assert execute_now(client, run["id"]).status == "completed"

        added = add_revision(
            client,
            workspace["id"],
            collection["id"],
            source["id"],
            payload=real_pdf(["Ban sua doi"]),
        )
        assert added.status_code == 201
        new_revision = added.json()["revision"]

        document = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}"
            f"/{run['id']}/document"
        )
        canonical = json.loads(document.content)
        assert canonical["identity"]["revision_id"] == revision["id"]
        assert canonical["identity"]["source_sha256"] == revision["sha256"]
        assert canonical["identity"]["revision_no"] == 1
        assert new_revision["sha256"] != revision["sha256"]


def test_cross_workspace_and_collection_are_not_reachable(client: TestClient) -> None:
    with FakeNemotron() as fake:
        owner_ws, owner_collection, owner_source, owner_revision = _workspace_with_document(
            client, "ocr-owner", payload=real_pdf(["Chu so huu"])
        )
        setup_ocr_provider(client, owner_ws["id"], fake.base_url)
        as_actor(EDITOR)
        run = request_run(
            client,
            owner_ws["id"],
            owner_collection["id"],
            owner_source["id"],
            owner_revision["id"],
        ).json()["run"]
        assert execute_now(client, run["id"]).status == "completed"

        as_actor(PLATFORM)
        other_ws = create_workspace(client, "ocr-other")
        add_member(client, other_ws["id"], EDITOR.actor_id, "editor")
        add_member(client, other_ws["id"], OUTSIDER.actor_id, "member")
        as_actor(EDITOR)
        other_collection, other_source, other_revision = prepare_source(
            client, other_ws["id"], "Kho khac", payload=real_pdf(["Don vi khac"])
        )

        as_actor(OUTSIDER)
        crossed_workspace = client.get(
            f"{runs_url(owner_ws['id'], owner_collection['id'], owner_source['id'], owner_revision['id'])}"
            f"/{run['id']}/document"
        )
        assert crossed_workspace.status_code == 404
        assert crossed_workspace.json()["code"] == "workspace_not_found"

        as_actor(EDITOR)
        crossed_collection = client.get(
            f"{runs_url(owner_ws['id'], other_collection['id'], other_source['id'], other_revision['id'])}"
            f"/{run['id']}"
        )
        assert crossed_collection.status_code == 404
        assert crossed_collection.json()["code"] == "collection_not_found"

        wrong_source = client.get(
            f"{runs_url(owner_ws['id'], owner_collection['id'], other_source['id'], owner_revision['id'])}"
            f"/{run['id']}"
        )
        assert wrong_source.status_code == 404
        assert wrong_source.json()["code"] == "source_not_found"


def test_queue_outage_leaves_a_durable_queued_run(client: TestClient) -> None:
    with FakeNemotron() as fake:
        workspace, collection, source, revision = _workspace_with_document(client, "ocr-queue")
        setup_ocr_provider(client, workspace["id"], fake.base_url)
        as_actor(EDITOR)
        broken = FakeJobQueue(failing=True)
        created = request_run(
            client,
            workspace["id"],
            collection["id"],
            source["id"],
            revision["id"],
            queue=broken,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["dispatched"] is False
        assert body["run"]["status"] == "queued"
        assert body["run"]["dispatch_pending"] is True

        healthy = FakeJobQueue()
        use_queue(healthy)
        dispatched = client.post(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}"
            f"/{body['run']['id']}/dispatch"
        )
        assert dispatched.status_code == 202
        assert dispatched.json()["dispatch_pending"] is False
        assert len(healthy.jobs) == 1

        again = client.post(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}"
            f"/{body['run']['id']}/dispatch"
        )
        assert again.status_code == 202
        assert len(healthy.jobs) == 1


def test_disabled_provider_fails_with_its_own_code(client: TestClient) -> None:
    with FakeNemotron() as fake:
        workspace, collection, source, revision = _workspace_with_document(client, "ocr-off")
        setup_ocr_provider(client, workspace["id"], fake.base_url, activate=False)
        as_actor(EDITOR)
        run = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        ).json()["run"]
        outcome = execute_now(client, run["id"])
        assert outcome.status == "failed"
        assert outcome.reason == "provider_inactive"
        assert fake.requests == []


def test_provider_without_ocr_capability_is_rejected(client: TestClient) -> None:
    with FakeNemotron() as fake:
        workspace, collection, source, revision = _workspace_with_document(client, "ocr-cap")
        provider = setup_ocr_provider(client, workspace["id"], fake.base_url)
        as_actor(PLATFORM)
        patched = client.patch(
            f"{API}/modelops/providers/{provider['id']}", json={"capabilities": ["chat"]}
        )
        assert patched.status_code == 200
        as_actor(EDITOR)
        run = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        ).json()["run"]
        outcome = execute_now(client, run["id"])
        assert outcome.status == "failed"
        assert outcome.reason == "provider_capability_mismatch"


def test_legacy_zero_quota_does_not_block_processing(client: TestClient) -> None:
    with FakeNemotron() as fake:
        workspace, collection, source, revision = _workspace_with_document(client, "ocr-quota")
        setup_ocr_provider(client, workspace["id"], fake.base_url)
        assert set_quota(client, workspace["id"], 0).status_code == 200
        as_actor(EDITOR)
        run = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        ).json()["run"]
        outcome = execute_now(client, run["id"])
        assert outcome.status == "completed"
        assert fake.requests


def test_timeout_is_uncertain_and_never_retried(client: TestClient) -> None:
    with FakeNemotron() as fake:
        fake.delay_seconds = 2.0
        workspace, collection, source, revision = _workspace_with_document(client, "ocr-timeout")
        setup_ocr_provider(client, workspace["id"], fake.base_url, timeout_seconds=1)
        as_actor(EDITOR)
        run = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        ).json()["run"]
        outcome = execute_now(client, run["id"])
        assert outcome.status == "uncertain"
        detail = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run['id']}"
        ).json()
        assert detail["pages"][0]["status"] == "uncertain"
        assert detail["pages"][0]["error_code"] == "ocr_provider_timeout"
        assert len(fake.requests) == 1


def test_malformed_response_is_a_failed_page_not_a_success(client: TestClient) -> None:
    with FakeNemotron() as fake:
        fake.mode = "malformed"
        workspace, collection, source, revision = _workspace_with_document(client, "ocr-bad")
        setup_ocr_provider(client, workspace["id"], fake.base_url)
        as_actor(EDITOR)
        run = request_run(
            client, workspace["id"], collection["id"], source["id"], revision["id"]
        ).json()["run"]
        outcome = execute_now(client, run["id"])
        assert outcome.status == "failed"
        detail = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run['id']}"
        ).json()
        assert detail["pages"][0]["status"] == "failed"
        assert detail["pages"][0]["error_code"] == "ocr_response_invalid"

        blocked = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}"
            f"/{run['id']}/document"
        )
        assert blocked.status_code == 409
        assert blocked.json()["code"] == "run_not_completed"

        manifest = client.get(
            f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}"
            f"/{run['id']}/manifest"
        )
        assert manifest.status_code == 200
        assert manifest.json()["validation"]["ok"] is False
