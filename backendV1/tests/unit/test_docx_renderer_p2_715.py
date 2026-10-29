"""Document converter isolation, render scheduling and sanitized error regressions."""

import asyncio
import threading
import traceback
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest

from qnu.domains.ocr.artifacts import render
from qnu.domains.ocr.config import ProcessingConfig
from qnu.platform.errors import DependencyUnavailable

pytestmark = pytest.mark.usefixtures("offline_document_conversion")

CONFIG = ProcessingConfig(
    dpi=144,
    max_pages=10,
    max_page_bytes=8388608,
    max_output_tokens=8192,
    prompt_version="nemotron-parse/v1",
    processor_version="qnu-ocr/v1",
    table_layout_version="nemotron-tabular/v1",
    docx_converter="gotenberg-libreoffice",
    gotenberg_url="http://converter.test:3000",
    pin_renderer=True,
)


@pytest.mark.asyncio
async def test_pdf_render_can_finish_while_gotenberg_is_waiting(monkeypatch):
    started, release = threading.Event(), threading.Event()
    lock = asyncio.Lock()
    monkeypatch.setattr(render, "_render_lock", lock)

    def conversion(payload, config):
        assert not lock.locked()
        started.set()
        if not release.wait(timeout=3):
            raise AssertionError("Test did not release the fake converter")
        return b"converted-pdf", {"converter": "gotenberg-libreoffice"}, []

    def rasterize_docx(pdf, stats, warnings, config):
        assert lock.locked()
        assert pdf == b"converted-pdf"
        return "docx-result"

    def rasterize_pdf(payload, extension, config):
        assert lock.locked()
        assert extension == ".pdf"
        return "pdf-result"

    monkeypatch.setattr(render, "_docx_to_pdf_gotenberg", conversion)
    monkeypatch.setattr(render, "_render_converted_docx", rasterize_docx)
    monkeypatch.setattr(render, "render_document", rasterize_pdf)
    docx = asyncio.create_task(render.render_async(b"docx", ".docx", CONFIG))
    try:
        assert await asyncio.to_thread(started.wait, 1)
        result = await asyncio.wait_for(render.render_async(b"pdf", ".pdf", CONFIG), 1)
        assert result == "pdf-result"
        assert not docx.done()
        release.set()
        assert await asyncio.wait_for(docx, 1) == "docx-result"
    finally:
        release.set()
        await asyncio.gather(docx, return_exceptions=True)


@pytest.mark.asyncio
async def test_conversion_failure_never_enters_mupdf_lock(monkeypatch):
    lock = asyncio.Lock()
    monkeypatch.setattr(render, "_render_lock", lock)

    def failed_conversion(*args):
        assert not lock.locked()
        raise DependencyUnavailable("Converter offline", code="docx_converter_unavailable")

    rasterize = Mock(side_effect=AssertionError("Must not rasterize failed conversion"))
    monkeypatch.setattr(render, "_docx_to_pdf_gotenberg", failed_conversion)
    monkeypatch.setattr(render, "_render_converted_docx", rasterize)
    with pytest.raises(DependencyUnavailable):
        await render.render_async(b"docx", ".docx", CONFIG)
    assert not lock.locked()
    rasterize.assert_not_called()


def test_http_error_logs_only_status_and_not_document_content(monkeypatch):
    class ErrorResponse:
        status_code = 503

        @property
        def text(self):
            raise AssertionError("Must not read converter error body")

    client = MagicMock()
    client.__enter__.return_value = client
    client.post.return_value = ErrorResponse()
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    logger = Mock()
    monkeypatch.setattr(render, "logger", logger)
    with pytest.raises(DependencyUnavailable) as caught:
        render._docx_to_pdf_gotenberg(b"private-document", CONFIG)
    assert caught.value.code == "docx_conversion_failed"
    logger.warning.assert_called_once_with("docx_conversion_failed", status_code=503)


def test_transport_error_hides_raw_exception_and_logs_only_type(monkeypatch):
    private = "private-credential-and-document-fragment"
    client = MagicMock()
    client.__enter__.return_value = client
    client.post.side_effect = httpx.ConnectError(private)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    logger = Mock()
    monkeypatch.setattr(render, "logger", logger)
    with pytest.raises(DependencyUnavailable) as caught:
        render._docx_to_pdf_gotenberg(b"private-document", CONFIG)
    assert private not in "".join(traceback.format_exception(caught.value))
    logger.warning.assert_called_once_with("docx_converter_unavailable", error_type="ConnectError")


def test_story_config_never_constructs_converter_http_client(monkeypatch):
    story = replace(CONFIG, docx_converter="docx-story", gotenberg_url="")
    convert = Mock(side_effect=AssertionError("Story must not call Gotenberg"))
    monkeypatch.setattr(render, "_docx_to_pdf_gotenberg", convert)
    monkeypatch.setattr(
        render,
        "convert_docx_to_html",
        lambda payload: SimpleNamespace(
            html="<p>Source text</p>",
            paragraphs=1,
            tables=0,
            table_rows=0,
            footnotes=0,
            images=0,
            skipped_images=0,
            warnings=[],
        ),
    )
    result = render.render_document(b"docx", ".docx", story)
    assert result.renderer["converter"] == "docx-story"
    convert.assert_not_called()


def test_unit_fixture_rejects_unmocked_http_clients():
    with pytest.raises(AssertionError, match="explicitly mock converter HTTP"):
        httpx.Client()
    with pytest.raises(AssertionError, match="explicitly mock converter HTTP"):
        httpx.AsyncClient()
