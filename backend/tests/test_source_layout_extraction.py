"""Layout metadata must survive the public OCR DTO boundary."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pymupdf
import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.services.layout_text import reconstruct_layout_text
from app.modules.knowledge.services.source_extraction import (
    SourceExtraction,
    align_office_markdown,
    extract_source,
    normalize_layout_block,
    save_source_preview,
)
from app.modules.knowledge.services.source_pages import normalize_source_pages
from app.modules.ocr.schemas import OCRExtractResponse, OCRPageResult


def test_ocr_dimensions_survive_dto_serialization():
    page = OCRPageResult(page_number=1, extracted_text="text", confidence=0,
                         word_count=1, line_count=1, dimensions={"width": 100, "height": 200})
    assert page.model_dump().get("dimensions") == {"width": 100, "height": 200}


def make_pdf(*types: str) -> bytes:
    with pymupdf.open() as document:
        for kind in types:
            page = document.new_page()
            if kind == "text":
                page.insert_text((70, 80), "Digital admission document with readable text.")
            elif kind == "scan":
                with pymupdf.open() as image_source:
                    image_page = image_source.new_page()
                    image_page.insert_text((70, 80), "Scanned admission document.")
                    page.insert_image(page.rect, stream=image_page.get_pixmap().tobytes("png"))
        return document.tobytes()


def ocr_response(count: int = 1) -> OCRExtractResponse:
    return OCRExtractResponse(filename="selected.pdf", success=True, engine_used="configured-paddle",
                              total_pages=count, overall_confidence=0, latency_ms=1, raw_text="Scan recognized",
                              pages=[OCRPageResult(page_number=i + 1, extracted_text="Scan recognized",
                                                   confidence=0, word_count=2, line_count=1,
                                                   dimensions={"width": 800, "height": 1100},
                                                   blocks=[{"type": "text", "text": "Scan recognized",
                                                            "coordinates": {"left": 10, "top": 20, "width": 30, "height": 5}}])
                                     for i in range(count)])


@pytest.mark.asyncio
async def test_native_pdf_keeps_real_geometry_and_never_calls_ocr():
    with patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", new_callable=AsyncMock) as ocr:
        result = await extract_source(AsyncMock(), make_pdf("text"), "digital.pdf", "pdf", "standard", None, "tenant")
    assert result.engine_used == "native"
    assert result.pages[0]["blocks"]
    block = result.pages[0]["blocks"][0]
    assert block["coordinates"]["is_valid"] and block["text"]
    assert "left" in block["coordinates"] and "x" not in block["coordinates"]
    assert block.get("text_confidence") is None
    _, manifest = normalize_source_pages(result.raw_text, result.page_count, result.pages)
    assert manifest[0]["blocks"] and manifest[0]["dimensions"]["width"] > 0
    ocr.assert_not_awaited()


@pytest.mark.asyncio
async def test_native_layout_reaches_studio_response_without_reparse():
    from app.modules.knowledge.services.source_ingestion_service import SourceIngestionService

    extraction = await extract_source(AsyncMock(), make_pdf("text"), "digital.pdf", "pdf", "standard", None, "tenant")
    markdown, manifest = normalize_source_pages(extraction.raw_text, extraction.page_count, extraction.pages)
    revision = SimpleNamespace(id="revision", canonical_markdown=markdown, page_manifest=manifest,
                               snapshot_metadata={"file_name": "digital.pdf"}, parse_provenance={"ocr_engine": "native"},
                               status="ready")
    binding = SimpleNamespace(id="source", active_source_revision=revision, status="active")
    service = SourceIngestionService()
    with patch.object(service, "get_source", AsyncMock(return_value=binding)):
        data = await service.get_source_studio_data(AsyncMock(), "collection", "source")
    assert data.pages[0].bounding_boxes[0].coordinates["is_valid"] is True
    assert data.pages[0].regions[0].details
    assert data.pages[0].regions[0].id == data.pages[0].bounding_boxes[0].id
    assert data.pages[0].dimensions["width"] > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["standard", "vision_ocr"])
async def test_mixed_pdf_only_sends_scan_page_and_preserves_blank_page(profile):
    with patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", new_callable=AsyncMock,
               return_value=ocr_response()) as ocr:
        result = await extract_source(AsyncMock(), make_pdf("blank", "text", "scan"), "mixed.pdf", "pdf", profile, None, "tenant")
    with pymupdf.open(stream=ocr.call_args.kwargs["content"], filetype="pdf") as request:
        assert len(request) == 1
    assert ocr.call_args.kwargs["engine_name"] == "paddleocr"
    assert [p["page_number"] for p in result.pages] == [1, 2, 3]
    assert result.pages[0]["extracted_text"] == ""
    assert "Digital admission" in result.pages[1]["extracted_text"]
    assert result.pages[2]["extracted_text"] == "Scan recognized"
    assert result.pages[2]["dimensions"]["width"] == 800


@pytest.mark.asyncio
async def test_explicit_layout_does_not_take_native_shortcut():
    with patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", new_callable=AsyncMock,
               return_value=ocr_response()) as ocr:
        result = await extract_source(AsyncMock(), make_pdf("text"), "digital.pdf", "pdf", "layout_analysis", None, "tenant")
    ocr.assert_awaited_once()
    assert result.engine_used == "configured-paddle"


@pytest.mark.asyncio
async def test_missing_ocr_pages_is_not_silently_successful():
    with patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", new_callable=AsyncMock,
               return_value=ocr_response(0)), pytest.raises(AppException) as error:
        await extract_source(AsyncMock(), make_pdf("scan"), "scan.pdf", "pdf", "standard", None, "tenant")
    assert error.value.code == "OCR_PAGE_COUNT_MISMATCH"


@pytest.mark.asyncio
async def test_ocr_error_propagates_instead_of_accepting_partial_document():
    with patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", new_callable=AsyncMock,
               side_effect=AppException("Unavailable", code="OCR_PROVIDER_UNAVAILABLE", status_code=503)), pytest.raises(AppException) as error:
        await extract_source(AsyncMock(), make_pdf("text", "scan"), "mixed.pdf", "pdf", "standard", None, "tenant")
    assert error.value.code == "OCR_PROVIDER_UNAVAILABLE"


def test_docling_markdown_alignment_preserves_content_and_real_pages():
    pages = [{"page_number": 1, "extracted_text": "Heading First paragraph"},
             {"page_number": 2, "extracted_text": "Second paragraph"}]
    align_office_markdown("# Heading\nFirst paragraph\n\nSecond paragraph", pages)
    assert pages[0]["extracted_text"] == "# Heading\nFirst paragraph"
    assert pages[1]["extracted_text"] == "Second paragraph"


def test_font_fallback_glyphs_are_reassembled_by_baseline_not_dictionary():
    spans = []
    for text, start in [("Tr", 0), ("ng", 20), ("ườ", 10), ("  ", 10), ("Đại", 35)]:
        chars = [{"c": char, "origin": (start + index * 5, 20),
                  "bbox": (start + index * 5, 10, start + index * 5 + 5, 23)}
                 for index, char in enumerate(text)]
        spans.append({"spans": [{"chars": chars}]})
    blocks = [{"lines": spans}]
    assert reconstruct_layout_text(blocks) == "Trường Đại"
    assert reconstruct_layout_text(blocks, (0, 0, 30, 30)) == "Trường"


def test_unrelated_office_preview_never_invents_page_mapping():
    with pytest.raises(AppException) as error:
        align_office_markdown("Actual office document", [{"page_number": 1, "extracted_text": "Unrelated content"}])
    assert error.value.code == "DOCX_LAYOUT_ALIGNMENT_FAILED"


@pytest.mark.asyncio
async def test_office_converter_failure_is_visible_not_fake_layout():
    from app.modules.knowledge.parsers.base import ParsedContent

    parser = SimpleNamespace(parse=AsyncMock(return_value=ParsedContent("Office document")))
    with (patch("app.modules.knowledge.services.source_extraction.get_document_parser", return_value=parser),
          patch("app.modules.knowledge.services.ingestion_service.IngestionService._convert_office_to_pdf",
                AsyncMock(side_effect=AppException("Converter offline", code="gotenberg_unreachable", status_code=503))),
          pytest.raises(AppException) as error):
        await extract_source(AsyncMock(), b"docx fixture", "office.docx", "docx", "standard", None, "tenant")
    assert error.value.code == "gotenberg_unreachable"


def test_scan_only_office_page_keeps_recognized_embedded_content():
    pages = [{"page_number": 1, "extracted_text": "Office text", "engine_used": "native"},
             {"page_number": 2, "extracted_text": "Embedded scan text", "engine_used": "paddleocr_vl"}]
    align_office_markdown("Office text", pages)
    assert pages[1]["extracted_text"] == "Embedded scan text"


def test_scan_first_office_page_is_not_erased_by_docling_mapping():
    pages = [{"page_number": 1, "extracted_text": "Embedded scan text", "engine_used": "paddleocr_vl"},
             {"page_number": 2, "extracted_text": "Office text", "engine_used": "native"}]
    align_office_markdown("Office text", pages)
    assert pages[0]["extracted_text"] == "Embedded scan text"
    assert pages[1]["extracted_text"] == "Office text"


def test_layout_without_coordinates_is_invalid_not_fabricated():
    block = normalize_layout_block({"text": "No geometry"}, 1, 0)
    assert block["coordinates"]["is_valid"] is False
    assert "left" not in block["coordinates"]


def test_nonfinite_layout_coordinates_cannot_reach_json_response():
    block = normalize_layout_block({"coordinates": {"left": float("nan"), "top": 0, "width": 20, "height": 10}}, 1, 0)
    assert block["coordinates"]["is_valid"] is False
    assert "left" not in block["coordinates"]


@pytest.mark.asyncio
async def test_image_ocr_without_page_is_rejected():
    with (patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", AsyncMock(return_value=ocr_response(0))),
          pytest.raises(AppException) as error):
        await extract_source(AsyncMock(), b"image fixture", "scan.png", "png", "standard", "auto", "tenant")
    assert error.value.code == "OCR_PAGE_COUNT_MISMATCH"


@pytest.mark.asyncio
async def test_preview_path_is_content_addressed_and_knowledge_scoped():
    with patch("app.modules.knowledge.services.source_extraction.storage_service.save", new_callable=AsyncMock) as save:
        one = await save_source_preview("snapshots/col/bnd/file.docx", SourceExtraction("", 0, preview_pdf=b"preview-one"))
        two = await save_source_preview("snapshots/col/bnd/file.docx", SourceExtraction("", 0, preview_pdf=b"preview-two"))
    assert one != two and one.startswith("snapshots/col/bnd/")
    assert save.await_count == 2
