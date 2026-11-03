"""Upload → durable worker → real native MD/JSON; OCR uses loopback only."""

import io
import json
import zipfile

import pytest
from sqlalchemy import func, select

from qnu.domains.knowledge.compilation.evidence import load_documents
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.service import processing_service
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    OUTSIDER,
    PLATFORM,
    as_actor,
    create_collection,
    upload_source,
    workspace_with_editor,
)
from tests.integration.ocr_support import (
    FakeJobQueue,
    FakeNemotron,
    docx_with_table,
    execute_now,
    real_pdf,
    runs_url,
    setup_ocr_provider,
    use_queue,
)
from tests.unit.test_native_extraction_710 import pdf


def setup(client, data=None, filename="source.pdf", *, failing=False):
    ws = workspace_with_editor(client, "auto-710")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Automatic extraction")
    queue = FakeJobQueue(failing=failing)
    use_queue(queue)
    # Omit auto_extract to exercise the public default, not the legacy fixture opt-out.
    response = client.post(
        f"{API}/workspaces/{ws['id']}/collections/{col['id']}/sources",
        files={
            "file": (filename, data or real_pdf(["Source 2023: 0 -"]), "application/octet-stream")
        },
        headers={"Idempotency-Key": "upload-auto-710"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    url = runs_url(ws["id"], col["id"], body["source"]["id"], body["revision"]["id"])
    run = body["source"]["processing"]
    assert run["strategy"] == "auto"
    return ws, col, body, run, url + "/" + run["id"], queue


def test_default_upload_is_durable_and_native_without_model_or_quota(client):
    ws, col, body, run, url, queue = setup(client)
    assert run["status"] == "queued" and len(queue.jobs) == 1
    assert not run["results_ready"]
    assert client.get(url + "/document").status_code == 409
    assert execute_now(client, run["id"]).status == "completed"
    result = client.get(url + "/document")
    assert result.status_code == 200, result.text
    doc = result.json()
    assert doc["processing"]["provider"] is None
    assert doc["pages"][0]["extraction_method"] == "native"
    assert "Source 2023: 0 -" in client.get(url + "/markdown").text
    assert all(v["artifact"] == "native_page" for v in doc["evidence"].values())
    detail = client.get(
        f"{API}/workspaces/{ws['id']}/collections/{col['id']}/sources/{body['source']['id']}"
    )
    assert detail.json()["processing"]["results_ready"]
    listing = client.get(f"{API}/workspaces/{ws['id']}/collections/{col['id']}/sources")
    assert listing.json()["items"][0]["processing"]["id"] == run["id"]
    assert execute_now(client, run["id"]).status == "not_claimed"

    async def compiler_evidence():
        async with AsyncSessionFactory() as db:
            return await load_documents(
                db, app.state.container.blob_store, ws["id"], col["id"], [run["id"]]
            )

    evidence = client.portal.call(compiler_evidence)
    assert evidence[0]["identity"]["revision_id"] == body["revision"]["id"]
    exported = client.get(url + "/bundle")
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert json.loads(archive.read("document.json")) == doc
        assert "Source 2023" in archive.read("document.md").decode()


def test_docx_table_has_real_structure_and_original_is_unchanged(client):
    data = docx_with_table()
    _, _, body, run, url, _ = setup(client, data, "source.docx")
    assert execute_now(client, run["id"]).status == "completed"
    doc = client.get(url + "/document").json()
    tables = [b["table"] for p in doc["pages"] for b in p["blocks"] if b.get("table")]
    assert tables and tables[0]["status"] == "parsed"
    cells = [c for t in tables for row in t["rows"] for c in row]
    assert any(c["text"] == "0" for c in cells)
    assert any(c["text"] == "-" for c in cells)
    assert any(c["col_span"] > 1 for c in cells)
    assert any(c["row_span"] > 1 for c in cells)
    assert any(c["header"] for c in cells)
    assert "Ghi chú" in client.get(url + "/markdown").text
    content_url = url.split("/processing-runs/")[0] + "/content"
    assert client.get(content_url).content == data
    assert body["source"]["status"] == "stored"


def test_mixed_page_preserves_native_text_image_and_raw_ocr(client):
    ws, _, _, run, url, _ = setup(client, pdf(image=True))
    with FakeNemotron() as provider:
        provider.responses = ["<x_0.11><y_0.25>Image text<x_0.25><y_0.32><class_Text>"]
        setup_ocr_provider(client, ws["id"], provider.base_url)
        assert execute_now(client, run["id"]).status == "completed"
        assert len(provider.requests) == 1
    doc = client.get(url + "/document").json()
    assert doc["pages"][0]["extraction_method"] == "hybrid"
    md = client.get(url + "/markdown").text
    assert "Source text 2023: 0 -" in md and "Image text" in md
    image = next(b["image"] for b in doc["pages"][0]["blocks"] if b.get("image"))
    assert image["filename"] in md
    download = client.get(url + f"/images/{image['asset_no']}")
    assert download.status_code == 200 and download.content.startswith(b"\x89PNG")
    with zipfile.ZipFile(io.BytesIO(client.get(url + "/bundle").content)) as archive:
        assert archive.read(image["filename"]) == download.content
    assert client.get(url + "/pages/1/raw").status_code == 200


def test_queue_outage_keeps_run_and_replay_does_not_duplicate(client):
    payload = real_pdf(["Source 2023: 0 -"])
    ws, col, _, run, url, _ = setup(client, payload, failing=True)
    assert run["dispatch_pending"] and run["status"] == "queued"
    replay = upload_source(
        client,
        ws["id"],
        col["id"],
        payload=payload,
        filename="source.pdf",
        idempotency_key="upload-auto-710",
        auto_extract=True,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["source"]["processing"]["id"] == run["id"]
    assert len(client.get(url.rsplit("/", 1)[0]).json()["items"]) == 1
    changed = upload_source(
        client,
        ws["id"],
        col["id"],
        payload=payload,
        filename="source.pdf",
        idempotency_key="upload-auto-710",
        auto_extract=False,
    )
    assert changed.status_code == 409


def test_source_and_processing_intent_rollback_together(client, monkeypatch):
    ws = workspace_with_editor(client, "auto-rollback")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Rollback")

    async def fail(*args, **kwargs):
        raise RuntimeError("synthetic intent persistence failure")

    monkeypatch.setattr(processing_service, "request_run", fail)
    with pytest.raises(RuntimeError, match="synthetic"):
        upload_source(
            client, ws["id"], col["id"], payload=real_pdf(["Rollback"]), auto_extract=True
        )
    listing = client.get(f"{API}/workspaces/{ws['id']}/collections/{col['id']}/sources").json()
    assert listing["meta"]["total"] == 0

    async def count():
        async with AsyncSessionFactory() as db:
            return await db.scalar(select(func.count()).select_from(OcrProcessingRun))

    assert client.portal.call(count) == 0


def test_revoked_membership_blocks_worker_and_export(client):
    ws, _, _, run, url, _ = setup(client)
    as_actor(PLATFORM)
    members = client.get(f"{API}/workspaces/{ws['id']}/members").json()["items"]
    member_id = next(m["id"] for m in members if m["actor_ref"] == EDITOR.actor_id)
    removed = client.delete(f"{API}/workspaces/{ws['id']}/members/{member_id}")
    assert removed.status_code in (200, 204), removed.text
    assert execute_now(client, run["id"]).status == "failed"
    as_actor(EDITOR)
    assert client.get(url + "/bundle").status_code == 404
    as_actor(OUTSIDER)
    assert client.get(url + "/document").status_code == 404


def test_scan_without_model_reports_failure_and_keeps_original(client):
    _, _, _, run, url, _ = setup(client, pdf(text="", image=True))
    assert execute_now(client, run["id"]).status == "failed"
    assert not client.get(url).json()["results_ready"]
    assert client.get(url + "/document").status_code == 409
    assert client.get(url.split("/processing-runs/")[0] + "/content").status_code == 200


def test_member_cannot_start_automatic_upload(client):
    ws = workspace_with_editor(client, "auto-role")
    as_actor(EDITOR)
    col = create_collection(client, ws["id"], "Permission")
    as_actor(MEMBER)
    result = upload_source(
        client, ws["id"], col["id"], payload=real_pdf(["Denied"]), auto_extract=True
    )
    assert result.status_code == 403


def test_new_revision_has_its_own_result_and_old_export_stays_pinned(client):
    ws, col, body, run, url, _ = setup(client)
    assert execute_now(client, run["id"]).status == "completed"
    endpoint = f"{API}/workspaces/{ws['id']}/collections/{col['id']}/sources/{body['source']['id']}"
    created = client.post(
        endpoint + "/revisions",
        files={"file": ("source.pdf", real_pdf(["Second revision"]), "application/pdf")},
    )
    assert created.status_code == 201, created.text
    second = created.json()["source"]["processing"]
    assert second["id"] != run["id"] and second["revision_no"] == 2
    assert execute_now(client, second["id"]).status == "completed"
    assert "Source 2023" in client.get(url + "/markdown").text
    assert client.get(endpoint).json()["processing"]["id"] == second["id"]


def test_auto_result_reuse_does_not_resolve_an_unneeded_model(client):
    _, _, _, run, url, _ = setup(client)
    assert execute_now(client, run["id"]).status == "completed"
    response = client.post(url.rsplit("/", 1)[0], json={"strategy": "auto"})
    assert response.status_code == 200, response.text
    assert response.json()["run"]["id"] == run["id"]
    forced = client.post(url.rsplit("/", 1)[0], json={"strategy": "auto", "force": True})
    assert forced.status_code == 201, forced.text
    assert execute_now(client, forced.json()["run"]["id"]).status == "completed"


def test_source_images_cannot_be_read_from_another_workspace(client):
    ws, _, _, run, url, _ = setup(client, pdf(image=True))
    with FakeNemotron() as provider:
        provider.responses = ["<x_0.11><y_0.25>Image text<x_0.25><y_0.32><class_Text>"]
        setup_ocr_provider(client, ws["id"], provider.base_url)
        assert execute_now(client, run["id"]).status == "completed"
    as_actor(OUTSIDER)
    assert client.get(url + "/images/10001").status_code == 404
    assert client.get(url + "/bundle").status_code == 404


def test_mixed_document_only_calls_ocr_for_image_page(client):
    import pymupdf

    doc = pymupdf.open(stream=real_pdf(["Native page"]), filetype="pdf")
    image_doc = pymupdf.open(stream=pdf(text="", image=True), filetype="pdf")
    doc.insert_pdf(image_doc)
    data = doc.tobytes()
    doc.close()
    image_doc.close()
    ws, _, _, run, url, _ = setup(client, data)
    with FakeNemotron() as provider:
        provider.responses = ["<x_0.11><y_0.25>Scan text<x_0.25><y_0.32><class_Text>"]
        setup_ocr_provider(client, ws["id"], provider.base_url)
        assert execute_now(client, run["id"]).status == "completed"
        assert len(provider.requests) == 1
    pages = client.get(url + "/document").json()["pages"]
    assert [p["extraction_method"] for p in pages] == ["native", "ocr"]
    assert [p["used_ocr"] for p in client.get(url).json()["pages"]] == [False, True]
    assert pages[0]["usage_tokens"] == 0


def test_native_worker_is_blocked_when_source_is_deleted(client):
    ws, _, body, run, _, _ = setup(client)
    from qnu.domains.lifecycle.models import ResourceState

    async def hide_source():
        async with AsyncSessionFactory() as db:
            # Exercise the server's lifecycle guard, not a client-provided state.
            db.add(
                ResourceState(
                    workspace_id=ws["id"],
                    kind="source",
                    resource_id=body["source"]["id"],
                    status="deleted",
                )
            )
            await db.commit()

    client.portal.call(hide_source)
    assert execute_now(client, run["id"]).status == "failed"


def test_unknown_ocr_usage_is_not_reported_as_zero_from_native_pages(client, monkeypatch):
    import pymupdf

    doc = pymupdf.open(stream=real_pdf(["Native page"]), filetype="pdf")
    scan = pymupdf.open(stream=pdf(text="", image=True), filetype="pdf")
    doc.insert_pdf(scan)
    data = doc.tobytes()
    doc.close()
    scan.close()
    ws, _, _, run, url, _ = setup(client, data)
    with FakeNemotron() as provider:
        original = provider._respond

        def without_usage(index):
            status, data = original(index)
            payload = json.loads(data)
            payload.pop("usage", None)
            return status, json.dumps(payload).encode()

        monkeypatch.setattr(provider, "_respond", without_usage)
        setup_ocr_provider(client, ws["id"], provider.base_url)
        assert execute_now(client, run["id"]).status == "completed"
    assert client.get(url).json()["usage_tokens"] is None
