"""Mixed-page OCR persists image tasks and source-mapped evidence through the worker."""

import hashlib
import io
import json
from dataclasses import replace

import httpx
import pymupdf
import pytest

from qnu.adapters.providers.mineru import MineruOcrEngine
from qnu.domains.ocr.execution import read_artifact_bytes
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    compiler_url,
    execute_compile,
    request_compile,
)
from tests.integration.knowledge_support import API, EDITOR, OUTSIDER, PLATFORM, as_actor
from tests.integration.ocr_support import FakeJobQueue, execute_now, set_quota, use_queue
from tests.integration.publication_review_support import acknowledgement
from tests.integration.test_auto_extraction_710 import setup
from tests.integration.test_ocr_text_review_651 import FakeSpeller
from tests.unit.test_mineru_823 import archive
from tests.unit.test_native_source_870 import panel_picture


def mixed_pdf():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((60, 60), "Original native source 0012")
        page.insert_image(pymupdf.Rect(60, 120, 540, 264), stream=panel_picture())
        return document.tobytes()


def duplicate_pdf():
    picture = panel_picture()
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((60, 60), "Original native source 0012")
        page.insert_image(pymupdf.Rect(60, 120, 300, 264), stream=picture)
        page.insert_image(pymupdf.Rect(320, 120, 560, 264), stream=picture)
        return document.tobytes(), picture


def variant_picture():
    with pymupdf.open() as document:
        page = document.new_page(width=600, height=180)
        for left, label in [(20, "THIRD PANEL"), (320, "FOURTH PANEL")]:
            page.draw_rect(pymupdf.Rect(left, 20, left + 220, 130), width=2)
            page.insert_text((left + 25, 55), label, fontsize=16)
            page.insert_text((left + 25, 90), "Literal 0120 - 1", fontsize=12)
        return page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")


def distinct_images_pdf():
    first, second = panel_picture(), variant_picture()
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((60, 60), "Original native source 0012")
        page.insert_image(pymupdf.Rect(60, 120, 540, 264), stream=first)
        page.insert_image(pymupdf.Rect(60, 300, 540, 444), stream=second)
        return document.tobytes(), first, second


def test_duplicate_embedded_image_uses_one_provider_call_and_keeps_each_asset(client):
    payload, picture = duplicate_pdf()
    ws, _, _, run, url, _ = setup(client, payload)
    provider(client, ws["id"])
    engine = ImageEngine()

    assert execute_now(client, run["id"], engine=engine).status == "completed"
    assert engine.input_pages == [3] and engine.modes == ["ocr"]
    blocks = client.get(url + "/document").json()["pages"][0]["blocks"]
    figures = [block for block in blocks if block.get("image")]
    assert len(figures) == 2
    assets = {block["image"]["asset_no"] for block in figures}
    assert len(assets) == 2
    for figure in figures:
        asset = figure["image"]["asset_no"]
        crops = [block for block in blocks if block.get("source_image_asset_no") == asset]
        assert len(crops) == 3
        assert all(block["bbox"]["units"] == "normalized_0_1" for block in crops)
        outer = figure["bbox"]
        assert all(
            outer["x0"] <= block["bbox"]["x0"] < block["bbox"]["x1"] <= outer["x1"]
            and outer["y0"] <= block["bbox"]["y0"] < block["bbox"]["y1"] <= outer["y1"]
            for block in crops
        )

    async def inspect():
        async with AsyncSessionFactory() as db:
            stored = await db.get(OcrProcessingRun, run["id"])
            assert stored.config["mineru_image_aliases"][hashlib.sha256(picture).hexdigest()]
            for asset in assets:
                record, data = await read_artifact_bytes(
                    db, client.app.state.container.blob_store, stored, "provider_document", asset
                )
                assert record.sha256 == hashlib.sha256(data).hexdigest()

    client.portal.call(inspect)


def test_distinct_embedded_images_get_parallel_tasks_and_their_own_evidence(client):
    payload, first, second = distinct_images_pdf()
    ws, _, _, run, url, _ = setup(client, payload)
    provider(client, ws["id"])
    engine = ImageEngine()

    assert execute_now(client, run["id"], engine=engine).status == "completed"
    assert engine.input_pages == [3, 3] and engine.modes == ["ocr", "ocr"]
    blocks = client.get(url + "/document").json()["pages"][0]["blocks"]
    figures = [block for block in blocks if block.get("image")]
    assert len(figures) == 2
    shas = {figure["image"]["sha256"] for figure in figures}
    assert shas == {hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest()}
    assets = {figure["image"]["asset_no"] for figure in figures}
    assert len(assets) == 2
    for figure in figures:
        asset = figure["image"]["asset_no"]
        crops = [block for block in blocks if block.get("source_image_asset_no") == asset]
        assert len(crops) == 3
        outer = figure["bbox"]
        assert all(
            outer["x0"] <= block["bbox"]["x0"] < block["bbox"]["x1"] <= outer["x1"]
            and outer["y0"] <= block["bbox"]["y0"] < block["bbox"]["y1"] <= outer["y1"]
            for block in crops
        )

    async def inspect():
        async with AsyncSessionFactory() as db:
            stored = await db.get(OcrProcessingRun, run["id"])
            aliases = stored.config["mineru_image_aliases"]
            assert {
                aliases[hashlib.sha256(first).hexdigest()],
                aliases[hashlib.sha256(second).hexdigest()],
            } == assets
            assert set(stored.config["mineru_image_tasks"]) == {str(asset) for asset in assets}
            assert all(
                state["phase"] == "uploaded"
                for state in stored.config["mineru_image_tasks"].values()
            )
            records = {}
            for asset in assets:
                record, data = await read_artifact_bytes(
                    db, client.app.state.container.blob_store, stored, "provider_document", asset
                )
                assert record.sha256 == hashlib.sha256(data).hexdigest()
                records[asset] = record.sha256
            _, raw = await read_artifact_bytes(
                db, client.app.state.container.blob_store, stored, "raw_response", 1
            )
            regions = json.loads(raw)["image_ocr"]
            assert len(regions) == 6
            assert {region["image_asset_no"] for region in regions} == assets
            for asset in assets:
                assert {
                    region["archive_sha256"]
                    for region in regions
                    if region["image_asset_no"] == asset
                } == {records[asset]}

    client.portal.call(inspect)


def test_word_sends_only_the_original_embedded_image_to_mineru(client):
    from docx import Document

    picture = panel_picture()
    doc = Document()
    doc.add_paragraph("Original native source 0012")
    doc.add_picture(io.BytesIO(picture))
    doc.add_paragraph("Text after image")
    source = io.BytesIO()
    doc.save(source)
    ws, _, _, run, url, _ = setup(client, source.getvalue(), "mixed.docx")
    provider(client, ws["id"])
    engine = ImageEngine()
    assert execute_now(client, run["id"], engine=engine).status == "completed"
    assert engine.input_pages == [3] and engine.modes == ["ocr"]
    blocks = client.get(url + "/document").json()["pages"][0]["blocks"]
    [figure] = [block for block in blocks if block.get("image")]
    assert figure["image"]["sha256"] == hashlib.sha256(picture).hexdigest()
    asset = figure["image"]["asset_no"]
    assert client.get(url + f"/images/{asset}").content == picture
    assert blocks[0]["text"] == "Original native source 0012"
    assert blocks[-1]["text"] == "Text after image"
    crops = [b for b in blocks if b.get("source_image_asset_no") == asset]
    assert len(crops) == 3 and all(b["bbox"]["units"] == "normalized_image_0_1" for b in crops)
    pdf = client.get(url + "/pdf")
    assert pdf.status_code == 409 and pdf.json()["code"] == "run_not_ready"


def provider(client, workspace):
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "Image OCR",
            "provider_type": "mineru",
            "base_url": "https://ocr.example/mineru",
            "model_name": "mineru",
            "capabilities": ["ocr"],
            "timeout_seconds": 60,
        },
    )
    assert response.status_code == 201, response.text
    identity = response.json()["id"]
    assert (
        client.post(
            f"{API}/modelops/providers/{identity}/keys",
            json={"name": "test", "secret": "protected-test-key"},
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"{API}/workspaces/{workspace}/allowed-providers",
            json={
                "provider_ids": [identity],
                "defaults": {"ocr": identity},
            },
        ).status_code
        == 200
    )
    as_actor(EDITOR)
    return identity


class ImageEngine:
    def __init__(self, fail_image=False, reject_image=False):
        self.requests, self.input_pages, self.modes = [], [], []
        self.fail_image = fail_image
        self.reject_image = reject_image

    async def extract_document(self, pdf, request, **kwargs):
        with pymupdf.open(stream=pdf, filetype="pdf") as document:
            count = len(document)
        crop = request.ocr_mode == "ocr"
        self.input_pages.append(count)
        self.modes.append(request.ocr_mode)
        task = "image" if crop else "document"
        receipt = {
            "task_id": task,
            "status": "completed",
            "files": [{"file_id": task, "status": "completed"}],
        }

        def handler(req):
            self.requests.append((task, req.method))
            if req.method == "POST":
                assert json.loads(req.content)["ocr_mode"] == request.ocr_mode
                if crop and self.reject_image:
                    return httpx.Response(422, json={"error": "image not supported"})
                return httpx.Response(202, json=receipt)
            if req.method == "PUT":
                if crop and self.fail_image:
                    raise httpx.ReadTimeout("unknown upload result")
                assert req.content == pdf
                return httpx.Response(200, json={})
            pages = [
                {
                    "page_idx": i,
                    "blocks": [
                        {
                            "type": "text",
                            "bbox": [0.1, 0.1, 0.9, 0.9],
                            "content": f"Image panel {i}: 0012"
                            if crop
                            else "Original native source 0012",
                        }
                    ],
                }
                for i in range(count)
            ]
            return (
                httpx.Response(200, content=archive(pages))
                if req.url.path.endswith("/content")
                else httpx.Response(200, json=receipt)
            )

        return await MineruOcrEngine(transport=httpx.MockTransport(handler)).extract_document(
            pdf, replace(request, execution=None), **kwargs
        )


@pytest.mark.parametrize("fail_image", [False, True])
def test_worker_image_evidence_or_uncertain_checkpoint_is_durable(client, fail_image):
    payload = mixed_pdf()
    ws, _, _, run, url, _ = setup(client, payload)
    provider(client, ws["id"])
    engine = ImageEngine(fail_image)
    result = execute_now(client, run["id"], engine=engine)
    assert result.status == ("uncertain" if fail_image else "completed"), result
    assert engine.input_pages == [3] and engine.modes == ["ocr"]

    async def inspect():
        async with AsyncSessionFactory() as db:
            stored = await db.get(OcrProcessingRun, run["id"])
            state = stored.config["mineru_image_tasks"]["10001"]
            assert state["ocr_mode"] == "ocr"
            assert state["phase"] == ("uploading" if fail_image else "uploaded")
            assert state["input_sha256"] and "protected-test-key" not in json.dumps(stored.config)
            if not fail_image:
                record, data = await read_artifact_bytes(
                    db, client.app.state.container.blob_store, stored, "provider_document", 10001
                )
                assert record.sha256 == hashlib.sha256(data).hexdigest()
                _, raw = await read_artifact_bytes(
                    db, client.app.state.container.blob_store, stored, "raw_response", 1
                )
                regions = json.loads(raw)["image_ocr"]
                assert len(regions) == 3
                assert all(r["archive_sha256"] == record.sha256 for r in regions)
                assert regions[1]["bbox"][2] < regions[2]["bbox"][0]

    client.portal.call(inspect)
    before = list(engine.requests)
    assert execute_now(client, run["id"], engine=engine).status == "not_claimed"
    assert engine.requests == before  # Never re-submit an uncertain upload or a finished run.
    assert client.get(url.split("/processing-runs/")[0] + "/content").content == payload
    if not fail_image:
        body = client.get(url + "/document").json()
        assert "Original native source 0012" in client.get(url + "/markdown").text
        crops = [b for b in body["pages"][0]["blocks"] if b.get("source_image_asset_no")]
        assert len(crops) == 3
        assert all(b["source_image_asset_no"] == 10001 and b["requires_review"] for b in crops)
        assert all(body["evidence"][b["evidence_id"]]["artifact"] == "raw_response" for b in crops)
    else:
        assert client.get(url + "/document").status_code == 409
    as_actor(OUTSIDER)
    assert client.get(url + "/bundle").status_code == 404


def test_pdf_sends_only_scan_pages_and_maps_result_to_original_page(client):
    with pymupdf.open() as document:
        document.new_page().insert_text((60, 60), "Native first page 0012")
        scan = document.new_page()
        scan.insert_image(scan.rect, stream=panel_picture(), keep_proportion=False)
        document.new_page().insert_text((60, 60), "Native third page 0120")
        payload = document.tobytes()
    ws, _, _, run, url, _ = setup(client, payload)
    provider(client, ws["id"])
    engine = ImageEngine()

    assert execute_now(client, run["id"], engine=engine).status == "completed"
    assert engine.input_pages == [1] and engine.modes == ["auto"]
    pages = client.get(url + "/document").json()["pages"]
    assert [page["page_number"] for page in pages] == [1, 2, 3]
    assert pages[0]["blocks"][0]["text"] == "Native first page 0012"
    assert pages[2]["blocks"][0]["text"] == "Native third page 0120"
    assert any(block["text"] == "Original native source 0012" for block in pages[1]["blocks"])

    async def inspect():
        async with AsyncSessionFactory() as db:
            stored = await db.get(OcrProcessingRun, run["id"])
            _, data = await read_artifact_bytes(
                db, client.app.state.container.blob_store, stored, "raw_response", 2
            )
            assert (json.loads(data)["source_page"], json.loads(data)["transport_page"]) == (2, 1)

    client.portal.call(inspect)


def partial_pdf_run(client):
    ws, col, body, run, url, _ = setup(client, mixed_pdf())
    ocr_provider = provider(client, ws["id"])
    set_quota(client, ws["id"], 1_000_000)
    engine = ImageEngine(reject_image=True)
    executed = execute_now(client, run["id"], engine=engine)
    assert executed.status == "completed_with_warnings", executed
    return ws, col, body, run, url, ocr_provider, engine


def test_rejected_supplemental_image_keeps_native_text_with_warnings(client):
    _, _, _, run, url, _, engine = partial_pdf_run(client)
    assert engine.input_pages == [3] and engine.modes == ["ocr"]
    detail = client.get(url).json()
    assert detail["status"] == "completed_with_warnings" and detail["results_ready"]
    assert detail["error_code"] is None

    body = client.get(url + "/document").json()
    (failure,) = body["image_ocr_failures"]
    assert failure["error_code"] == "ocr_provider_rejected"
    assert failure["page"] == 1 and failure["attempts"] == 1
    asset = failure["image_asset_no"]
    page = body["pages"][0]
    assert page["status"] == "completed" and page["image_ocr_failures"] == [failure]
    assert page["blocks"][0]["text"] == "Original native source 0012"
    assert not [b for b in page["blocks"] if b.get("source_image_asset_no") == asset]
    markdown = client.get(url + "/markdown").text
    assert "Original native source 0012" in markdown
    assert f"image_ocr_failed: asset={asset}" in markdown

    review = client.get(url + "/text-review").json()
    assert review["image_ocr_failures"] == [failure]
    assert review["image_ocr_acknowledged"] is False

    async def inspect():
        async with AsyncSessionFactory() as db:
            stored = await db.get(OcrProcessingRun, run["id"])
            assert stored.status == "completed_with_warnings"
            state = stored.config["mineru_image_tasks"][str(asset)]
            assert state["phase"] == "creating"
            assert "protected-test-key" not in json.dumps(stored.config)
            _, raw = await read_artifact_bytes(
                db, client.app.state.container.blob_store, stored, "raw_response", 1
            )
            payload = json.loads(raw)
            assert "image_ocr" not in payload
            assert payload["image_ocr_failures"] == [failure]

    client.portal.call(inspect)
    before = list(engine.requests)
    assert execute_now(client, run["id"], engine=engine).status == "not_claimed"
    assert engine.requests == before
    as_actor(OUTSIDER)
    assert client.get(url + "/bundle").status_code == 404


def test_partial_images_continue_into_spelling_review(client):
    from qnu.workers.tasks.ocr import spelling_check_job

    ws, col, body, run, url, ocr_provider, _ = partial_pdf_run(client)
    data = {
        "workspace": ws,
        "collection": col,
        "source": body["source"],
        "revision": body["revision"],
        "ocr_provider": {"id": ocr_provider},
    }
    with FakeSpeller() as speller:
        chat_provider(client, data, speller.base_url)
        context = {"container": app.state.container}
        assert client.portal.call(spelling_check_job, context, run["id"]) == "completed"
        assert speller.requests
    checks = client.get(url + "/text-review/checks").json()
    assert [check["status"] for check in checks] == ["completed"]


def test_word_with_only_an_image_stays_fatal(client):
    from docx import Document

    doc = Document()
    doc.add_picture(io.BytesIO(panel_picture()))
    source = io.BytesIO()
    doc.save(source)
    ws, _, _, run, url, _ = setup(client, source.getvalue(), "image-only.docx")
    provider(client, ws["id"])
    engine = ImageEngine(reject_image=True)

    assert execute_now(client, run["id"], engine=engine).status == "failed"
    detail = client.get(url).json()
    assert detail["status"] == "failed" and detail["error_code"] == "ocr_provider_rejected"
    assert client.get(url + "/document").status_code == 409


def test_publication_of_partial_images_requires_admin_acknowledgement(client):
    ws, col, body, run, url, ocr_provider, _ = partial_pdf_run(client)
    data = {
        "workspace": ws,
        "collection": col,
        "source": body["source"],
        "revision": body["revision"],
        "ocr_provider": {"id": ocr_provider},
        "ocr_run_id": run["id"],
        "url": compiler_url(ws["id"], col["id"]),
    }
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        use_queue(FakeJobQueue())
        created = request_compile(client, data)
        assert created.status_code == 201, created.text
        data["run_id"] = created.json()["run"]["id"]
        assert execute_compile(client, data["run_id"]) == "completed"

        base = f"{API}/workspaces/{ws['id']}/collections/{col['id']}/compiled-documents"
        registered = client.post(
            base,
            headers={"Idempotency-Key": "partial-register"},
            json={
                "document_key": "partial",
                "title": "Nguồn có ảnh lỗi",
                "compilation_run_id": data["run_id"],
            },
        )
        assert registered.status_code == 201, registered.text
        document_url = base + "/" + registered.json()["document"]["id"]
        version_url = document_url + "/versions/" + registered.json()["version"]["id"]

        as_actor(PLATFORM)
        blocked = client.post(
            version_url + "/decision-preview",
            json={
                "action": "approve",
                "reason": "Kiểm tra trước khi duyệt.",
                "review_ack": acknowledgement(client, version_url),
            },
        )
        assert blocked.status_code == 409, blocked.text
        assert blocked.json()["code"] == "publication_evidence_incomplete"

        as_actor(EDITOR)
        editor_ack = client.post(
            url + "/warnings/acknowledge", json={"reason": "Chấp nhận thiếu nội dung ảnh."}
        )
        assert editor_ack.status_code == 403, editor_ack.text

        as_actor(PLATFORM)
        acknowledged = client.post(
            url + "/warnings/acknowledge", json={"reason": "Chấp nhận thiếu nội dung ảnh."}
        )
        assert acknowledged.status_code == 200, acknowledged.text
        assert acknowledged.json()["created"] is True
        assert acknowledged.json()["acknowledged"]["images_failed"] == 1
        replay = client.post(
            url + "/warnings/acknowledge", json={"reason": "Xác nhận lặp lại."}
        )
        assert replay.status_code == 200 and replay.json()["created"] is False
        events = client.get(f"{API}/workspaces/{ws['id']}/events").json()
        assert any(
            row["action"] == "source.ocr_warnings_acknowledged" for row in events["items"]
        )

        preview = client.post(
            version_url + "/decision-preview",
            json={
                "action": "approve",
                "reason": "Đã xác nhận cảnh báo.",
                "review_ack": acknowledgement(client, version_url),
            },
        )
        assert preview.status_code == 200, preview.text
        decided = client.post(
            version_url + "/decisions",
            headers={"Idempotency-Key": "partial-approve"},
            json={
                "preview_id": preview.json()["id"],
                "preview_sha256": preview.json()["preview_sha256"],
            },
        )
        assert decided.status_code == 200, decided.text
        publish = client.post(
            version_url + "/decision-preview",
            json={"action": "publish", "reason": "Xuất bản sau khi đã xác nhận."},
        )
        assert publish.status_code == 200, publish.text
        published = client.post(
            version_url + "/decisions",
            headers={"Idempotency-Key": "partial-publish"},
            json={
                "preview_id": publish.json()["id"],
                "preview_sha256": publish.json()["preview_sha256"],
            },
        )
        assert published.status_code == 200, published.text
        assert client.get(document_url + "/published").status_code == 200
