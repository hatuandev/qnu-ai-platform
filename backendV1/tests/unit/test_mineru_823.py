"""Protocol and evidence regressions; fake HTTP does not prove OCR quality."""

import hashlib
import io
import json
import zipfile
from dataclasses import replace

import httpx
import pytest

from qnu.adapters.providers.mineru import MineruOcrEngine
from qnu.domains.ocr.mineru_layout import VERSION, archive_pages, parse_mineru_page, parse_table
from qnu.platform.errors import AppException
from qnu.ports.ocr_engine import OcrDocumentRequest

PDF = b"%PDF-1.4 example fixture"
REQUEST = OcrDocumentRequest("https://ocr.example/mineru", "mineru", 1, "private-key")


def page(index=0):
    return {
        "page_idx": index,
        "blocks": [
            {
                "type": "text",
                "bbox": [0.1, 0.1, 0.9, 0.9],
                "content": [{"type": "text", "content": "Dữ liệu gốc 12,67"}],
            }
        ],
    }


def archive(pages=None, name="middle_json.json", full=True):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as file:
        file.writestr(
            name, json.dumps({"pages": pages or [page()], "is_full_document": full}).encode()
        )
    return stream.getvalue()


@pytest.mark.asyncio
async def test_whole_pdf_once_and_checkpoint_before_side_effects():
    calls, saved = [], []
    receipt = {
        "task_id": "job-1",
        "files": [{"file_id": "file-1", "status": "completed"}],
        "status": "completed",
    }

    def handler(req):
        calls.append(req)
        assert req.headers["authorization"] == "Bearer private-key"
        if req.method == "POST":
            assert saved[-1]["phase"] == "creating"
            data = json.loads(req.content)
            assert data["files"][0]["bytes"] == len(PDF)
            assert "max_tokens" not in data
            return httpx.Response(202, json=receipt)
        if req.method == "PUT":
            assert saved[-1]["phase"] == "uploading"
            assert req.content == PDF
            return httpx.Response(200, json={})
        return (
            httpx.Response(200, content=archive())
            if req.url.path.endswith("/content")
            else httpx.Response(200, json=receipt)
        )

    async def save(state):
        saved.append(state)

    async def guard():
        return None

    engine = MineruOcrEngine(transport=httpx.MockTransport(handler), poll_seconds=0)
    result = await engine.extract_document(PDF, REQUEST, checkpoint={}, save=save, guard=guard)
    assert result.usage_tokens is None
    assert [x.method for x in calls] == ["POST", "PUT", "GET", "GET"]
    assert saved[-1]["phase"] == "uploaded"
    calls.clear()
    await engine.extract_document(PDF, REQUEST, checkpoint=saved[-1], save=save, guard=guard)
    assert [x.method for x in calls] == ["GET", "GET"]
    assert "private-key" not in str(saved)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["creating", "uploading"])
async def test_ambiguous_submission_never_repeated(phase):
    calls = []

    def handler(req):
        calls.append(req.method)
        raise httpx.ReadTimeout("uncertain")

    async def noop(*args):
        return None

    state = {"phase": phase, "input_sha256": hashlib.sha256(PDF).hexdigest()}
    if phase == "uploading":
        state.update(task_id="job-1", file_id="file-1")
    with pytest.raises(AppException, match="MinerU") as caught:
        await MineruOcrEngine(transport=httpx.MockTransport(handler)).extract_document(
            PDF, REQUEST, checkpoint=state, save=noop, guard=noop
        )
    assert caught.value.code == "ocr_provider_timeout"
    assert calls == ([] if phase == "creating" else ["GET"])


@pytest.mark.asyncio
async def test_authority_failure_stops_before_upload():
    calls, checkpoints = [], []

    def handler(req):
        calls.append(req.method)
        return httpx.Response(202, json={"task_id": "job", "files": [{"file_id": "file"}]})

    async def save(state):
        checkpoints.append(state)

    async def guard():
        if checkpoints and checkpoints[-1].get("task_id"):
            raise AppException("Revoked", code="workspace_forbidden", status_code=403)

    with pytest.raises(AppException) as caught:
        await MineruOcrEngine(transport=httpx.MockTransport(handler)).extract_document(
            PDF, REQUEST, checkpoint={}, save=save, guard=guard
        )
    assert caught.value.code == "workspace_forbidden"
    assert calls == ["POST"]


@pytest.mark.asyncio
async def test_redirect_does_not_forward_credentials():
    calls = []

    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(307, headers={"location": "https://outside.example/steal"})

    async def noop(*args):
        return None

    with pytest.raises(AppException):
        await MineruOcrEngine(transport=httpx.MockTransport(handler)).extract_document(
            PDF, REQUEST, checkpoint={}, save=noop, guard=noop
        )
    assert len(calls) == 1 and "outside" not in calls[0]


@pytest.mark.asyncio
async def test_changed_pdf_and_blocked_endpoint_have_no_http():
    async def noop(*args):
        return None

    for req, state in (
        (REQUEST, {"input_sha256": "0" * 64}),
        (replace(REQUEST, endpoint="http://169.254.169.254/mineru"), {}),
    ):
        with pytest.raises(AppException):
            await MineruOcrEngine(
                transport=httpx.MockTransport(lambda _: pytest.fail("No network"))
            ).extract_document(PDF, req, checkpoint=state, save=noop, guard=noop)


@pytest.mark.parametrize(
    "payload,count",
    [
        (b"not zip", 1),
        (archive([page(0), page(0)]), 2),
        (archive([page(1)]), 1),
        (archive(full=False), 1),
        (archive(name="../middle_json.json"), 1),
        (archive([page(0)]), 2),
    ],
    ids=["not_zip", "duplicate_page", "wrong_page", "partial", "traversal", "missing_page"],
)
def test_invalid_archive_refused(payload, count):
    with pytest.raises(AppException) as caught:
        archive_pages(payload, count)
    assert caught.value.code == "mineru_layout_invalid"


def test_layout_keeps_vietnamese_literal_bbox_and_empty_cells():
    raw = archive_pages(archive(), 1)[1]
    layout = parse_mineru_page(raw)
    assert layout.text == "Dữ liệu gốc 12,67"
    assert layout.blocks[0].bbox == (0.1, 0.1, 0.9, 0.9)
    table = parse_table(
        '<table><tr><th rowspan="2">Ngành</th><th colspan="2">Năm</th></tr><tr><td>2025</td><td>2026</td></tr><tr><td>Giáo dục</td><td></td><td>0</td></tr></table>'
    )
    assert table.status == "parsed" and table.column_count == 3
    assert table.rows[0][0].row_span == 2 and table.rows[0][1].col_span == 2
    assert table.rows[2][1].text == "" and table.rows[2][2].text == "0"
    nested = {"format": VERSION, "page": {"blocks": [{
        "type": "table", "bbox": [0.1, 0.1, 0.9, 0.9], "content": [
            {"type": "table_caption", "content": "Kết quả năm 2024"},
            {"type": "table_body", "content": "<table><tr><td>0</td></tr></table>"},
            {"type": "table_footnote", "content": "Ghi chú: số liệu gốc."},
        ],
    }]}}
    projected = parse_mineru_page(nested)
    assert [b.kind for b in projected.blocks] == ["caption", "table", "footnote"]
    assert projected.blocks[0].text == "Kết quả năm 2024"
    assert projected.blocks[2].text == "Ghi chú: số liệu gốc."


@pytest.mark.parametrize("bbox", [[-1, 0, 1, 1], [0, 0, 0, 0], [0, 0, 2, 1]])
def test_invalid_bbox_is_not_clamped(bbox):
    block = page()["blocks"][0]
    block["bbox"] = bbox
    with pytest.raises(AppException):
        parse_mineru_page({"format": VERSION, "page": {"blocks": [block]}})
