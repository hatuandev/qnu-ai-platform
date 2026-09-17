"""Unit Tests for Document OCR Recognition, Adapters & Fallback Policy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest

from app.core.exceptions import AppException
from app.modules.ocr.adapters.docling_adapter import DoclingOCRAdapter
from app.modules.ocr.adapters.easyocr_adapter import EasyOCRAdapter
from app.modules.ocr.adapters.mock_adapter import MockOCRAdapter
from app.modules.ocr.adapters.pymupdf_adapter import PyMuPDFOCRAdapter
from app.modules.ocr.service import OCRService


@pytest.mark.asyncio
async def test_mock_ocr_adapter():
    adapter = MockOCRAdapter()
    assert adapter.name == "mock_ocr"
    assert adapter.is_available() is True

    res = await adapter.extract(b"dummy_bytes", "qd_2699.pdf")
    assert res["engine_used"] == "mock_ocr"
    assert res["total_pages"] == 2
    assert res["overall_confidence"] >= 0.95
    assert len(res["pages"]) == 2
    assert "Điều 1" in res["raw_text"]


@pytest.mark.asyncio
async def test_pymupdf_ocr_adapter():
    # Create an in-memory PDF with 1 page
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Truong Dai hoc Quy Nhon - Quy che Dao tao tin chi QNU", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    adapter = PyMuPDFOCRAdapter()
    assert adapter.name == "pymupdf_ocr"
    res = await adapter.extract(pdf_bytes, "test_doc.pdf")

    assert res["engine_used"] == "pymupdf_ocr"
    assert res["total_pages"] == 1
    assert "Quy che Dao tao tin chi" in res["raw_text"]
    assert res["pages"][0]["confidence"] >= 0.90


@pytest.mark.asyncio
async def test_ocr_service_successful_extraction():
    service = OCRService()
    engines = service.list_engines()
    assert len(engines) >= 2

    # Create dummy PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Quyet dinh ban hanh ke hoach giang day QNU 2026", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    resp = await service.extract_document(
        session=mock_session,
        content=pdf_bytes,
        filename="ke_hoach_2026.pdf",
        engine_name="pymupdf_ocr",
    )

    assert resp.success is True
    assert resp.fallback_triggered is False
    assert resp.total_pages == 1
    assert "ke hoach giang day" in resp.raw_text
    assert resp.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_heavy_adapters_report_unavailable_without_deps():
    """Docling/EasyOCR adapters must report unavailable (not crash) when uninstalled."""
    docling = DoclingOCRAdapter()
    easyocr = EasyOCRAdapter()
    assert docling.name == "docling"
    assert easyocr.name == "easyocr"
    assert docling.is_available() is False
    assert easyocr.is_available() is False


@pytest.mark.asyncio
async def test_list_engines_reflects_real_availability():
    """Engine catalog must expose 4 engines with honest active flags."""
    service = OCRService()
    engines = service.list_engines()
    by_name = {e.name: e for e in engines}
    assert set(by_name) == {"pymupdf_ocr", "docling", "easyocr", "mock_ocr"}
    assert by_name["pymupdf_ocr"].is_active is True
    assert by_name["docling"].is_active is False
    assert by_name["easyocr"].is_active is False


@pytest.mark.asyncio
async def test_explicit_unavailable_engine_raises_clear_error():
    """Requesting an uninstalled engine must fail loudly, never silently mock."""
    service = OCRService()
    mock_session = AsyncMock()
    with pytest.raises(AppException) as exc_info:
        await service.extract_document(
            session=mock_session,
            content=b"%PDF-1.4 dummy",
            filename="scan.pdf",
            engine_name="docling",
        )
    assert exc_info.value.code == "ocr_engine_unavailable"
    assert exc_info.value.status_code == 400


def _blank_pdf_bytes() -> bytes:
    """Build a scanned-like PDF page with no extractable text."""
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_auto_routing_blank_scan_returns_honest_empty():
    """Auto mode on a blank scan must return empty text, not invented content."""
    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    resp = await service.extract_document(
        session=mock_session,
        content=_blank_pdf_bytes(),
        filename="blank_scan.pdf",
        engine_name="auto",
    )
    assert resp.success is True
    assert resp.raw_text == ""
    assert resp.engine_used == "pymupdf_ocr"
    assert resp.fallback_triggered is False


@pytest.mark.asyncio
async def test_auto_routing_upgrades_to_docling_when_available():
    """Auto mode must upgrade blank scans to Docling when it is installed."""
    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    class FakeDocling:
        name = "docling"

        def is_available(self) -> bool:
            return True

        async def extract(self, content: bytes, filename: str) -> dict:
            return {
                "engine_used": "docling",
                "total_pages": 1,
                "overall_confidence": 0.97,
                "pages": [
                    {
                        "page_number": 1,
                        "extracted_text": "Noi dung quet tu ban scan",
                        "confidence": 0.97,
                        "word_count": 5,
                        "line_count": 1,
                        "has_tables": False,
                    }
                ],
                "raw_text": "Noi dung quet tu ban scan",
            }

    with patch.dict(service._adapters, {"docling": FakeDocling()}):
        resp = await service.extract_document(
            session=mock_session,
            content=_blank_pdf_bytes(),
            filename="blank_scan.pdf",
            engine_name="auto",
        )
    assert resp.success is True
    assert resp.engine_used == "docling"
    assert resp.fallback_triggered is True
    assert "ban scan" in resp.raw_text


@pytest.mark.asyncio
async def test_ocr_service_graceful_fallback():
    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    # Intentionally corrupt or make primary adapter raise an exception
    with patch.object(service._adapters["pymupdf_ocr"], "extract", side_effect=RuntimeError("Engine Out Of Memory")):
        resp = await service.extract_document(
            session=mock_session,
            content=b"corrupted_pdf_data",
            filename="corrupt.pdf",
            engine_name="pymupdf_ocr",
        )

        # Fallback should kick in seamlessly
        assert resp.success is True
        assert resp.fallback_triggered is True
        assert resp.engine_used == "mock_ocr"
        assert resp.total_pages >= 1
        assert resp.overall_confidence > 0.90
