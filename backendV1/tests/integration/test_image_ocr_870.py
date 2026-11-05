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
from qnu.platform.database import AsyncSessionFactory
from tests.integration.knowledge_support import API, EDITOR, OUTSIDER, PLATFORM, as_actor
from tests.integration.ocr_support import execute_now
from tests.integration.test_auto_extraction_710 import setup
from tests.unit.test_mineru_823 import archive
from tests.unit.test_native_source_870 import panel_picture


def mixed_pdf():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((60, 60), "Original native source 0012")
        page.insert_image(pymupdf.Rect(60, 120, 540, 264), stream=panel_picture())
        return document.tobytes()


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


class ImageEngine:
    def __init__(self, fail_image=False):
        self.requests, self.input_pages, self.modes = [], [], []
        self.fail_image = fail_image

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
