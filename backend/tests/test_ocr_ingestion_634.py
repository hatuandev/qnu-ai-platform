"""OCR selections and table evidence must survive repository-to-knowledge ingestion."""

import hashlib
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from zipfile import ZipFile

import pymupdf
import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.parsers.base import ParsedContent
from app.modules.knowledge.schemas import KnowledgeImportBatchCreateRequest
from app.modules.knowledge.services.import_batch_service import ImportBatchService
from app.modules.knowledge.services.source_artifact import add_layout_issues, build_source_artifact
from app.modules.knowledge.services.source_extraction import align_office_markdown, extract_source
from app.modules.ocr.schemas import OCRExtractResponse, OCRPageResult

ROWS = [["Program", "Year", "Seats", "Fee"], ["Software engineering", "2025", "120", "15000000"],
        ["Data science", "2026", "135", "16500000"], ["Digital archives", "2026", "0", "—"]]
HTML = "<table>" + "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in ROWS) + "</table>"
MARKDOWN = "\n".join(["| " + " | ".join(ROWS[0]) + " |", "| --- | --- | --- | --- |",
                      *("| " + " | ".join(row) + " |" for row in ROWS[1:])])


def test_office_alignment_compares_html_cells_without_markup_tokens():
    pages = [{"page_number": 1, "extracted_text": HTML, "engine_used": "nemotron_parse"}]
    ranges = align_office_markdown(MARKDOWN, pages)
    assert ranges == [(1, 0, len(MARKDOWN))]
    assert "2025" in pages[0]["extracted_text"]
    assert "| Digital archives | 2026 | 0 | — |" in pages[0]["extracted_text"]


def test_unrelated_html_is_still_rejected_by_office_alignment():
    with pytest.raises(AppException, match="PDF") as error:
        align_office_markdown("Entirely unrelated content", [{"page_number": 1, "extracted_text": HTML}])
    assert error.value.code == "DOCX_LAYOUT_ALIGNMENT_FAILED"


def test_office_alignment_decodes_html_entities_without_changing_source():
    markdown = "| Café | Niño |\n| --- | --- |\n| Français | économie |"
    html = "<table><tr><th>Caf&eacute;</th><th>Ni&ntilde;o</th></tr><tr><td>Fran&ccedil;ais</td><td>&eacute;conomie</td></tr></table>"
    pages = [{"page_number": 1, "extracted_text": html, "engine_used": "nemotron_parse"}]
    assert align_office_markdown(markdown, pages) == [(1, 0, len(markdown))]


@pytest.mark.asyncio
async def test_pdf_ocr_derivative_has_table_but_raw_response_stays_unchanged():
    with pymupdf.open() as document:
        document.new_page().insert_text((60, 60), "Digital archives")
        content = document.tobytes()
    page = OCRPageResult(page_number=1, extracted_text=HTML, confidence=0,
                         word_count=20, line_count=4, has_tables=True, blocks=[
                             {"type": "table", "text": HTML, "order": 0,
                              "coordinates": {"left": 10, "top": 10, "width": 80, "height": 25}}])
    raw = {"engine_used": "nemotron_parse", "raw_text": HTML, "pages": [page.model_dump()]}
    response = OCRExtractResponse(filename="test.pdf", success=True, engine_used="nemotron_parse",
                                  total_pages=1, overall_confidence=0, latency_ms=1, raw_text=HTML,
                                  pages=[page], raw_evidence=raw)
    parser = SimpleNamespace(parse=AsyncMock(return_value=ParsedContent("Digital archives", page_count=1)))
    with (patch("app.modules.knowledge.services.source_extraction.get_document_parser", return_value=parser),
          patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", AsyncMock(return_value=response)) as ocr):
        result = await extract_source(AsyncMock(), content, "test.pdf", "pdf", "vision_ocr", "nemotron-parse", "tenant")
    assert ocr.call_args.kwargs["engine_name"] == "nemotron-parse"
    assert MARKDOWN in result.raw_text
    assert "<table>" not in result.raw_text
    assert result.pdf_evidence["ocr"]["raw_text"] == HTML
    assert result.pdf_evidence["ocr"]["pages"][0]["extracted_text"] == HTML
    artifact = build_source_artifact(result.raw_text, 1, {})
    add_layout_issues(artifact, result.pages)
    assert len(artifact["tables"]) == 1
    assert not any(issue["code"] == "TABLES_NOT_MATERIALIZED" for issue in artifact["issues"])


def test_batch_schema_accepts_explicit_ocr_selection():
    request = KnowledgeImportBatchCreateRequest(document_ids=["doc"], ocr_engine="nemotron-parse")
    assert request.ocr_engine == "nemotron-parse"
    assert KnowledgeImportBatchCreateRequest(document_ids=["doc"]).ocr_engine is None


@pytest.mark.parametrize("retry_count", [0, 1])
def test_import_job_keeps_ocr_selection_on_initial_dispatch_and_retry(retry_count):
    item = SimpleNamespace(id="item", origin_document_id="doc", retry_count=retry_count,
                           origin_metadata={"_ocr_engine": "nemotron-parse"})
    batch = SimpleNamespace(id="batch", collection_id="col", tenant_id="t", workspace_id="w")
    jobs = ImportBatchService._create_jobs(Mock(), batch, [item])
    assert jobs[0].payload["ocr_engine"] == "nemotron-parse"


def test_old_import_job_payload_stays_compatible_without_ocr_override():
    item = SimpleNamespace(id="item", origin_document_id="doc", retry_count=0, origin_metadata={})
    batch = SimpleNamespace(id="batch", collection_id="col", tenant_id="t", workspace_id="w")
    jobs = ImportBatchService._create_jobs(Mock(), batch, [item])
    assert jobs[0].payload == {"item_id": "item", "batch_id": "batch"}


@pytest.mark.asyncio
async def test_docx_resource_archive_preserves_raw_ocr_alongside_original_images():
    from app.modules.knowledge.services.qnu_docx_artifacts import _save_office_resources

    image = b"original Office resource bytes"
    evidence = {"version": "office-preview-ocr/v1", "ocr": {"raw_text": HTML}}
    resource = {"member": "word/media/image1.png", "data": image,
                "sha256": hashlib.sha256(image).hexdigest(), "source_ref": "image1"}
    save = AsyncMock()
    with (patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.exists", AsyncMock(return_value=False)),
          patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.save", save)):
        reference = await _save_office_resources(SimpleNamespace(blocks=[]), [resource], "snapshot.docx",
                                                 ocr_evidence=evidence)
    payload = save.call_args.args[1]
    assert hashlib.sha256(payload).hexdigest() == reference["sha256"]
    with ZipFile(BytesIO(payload)) as archive:
        assert archive.read("word/media/image1.png") == image
        assert json.loads(archive.read("ocr/preview.json")) == evidence
