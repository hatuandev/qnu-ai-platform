"""Unit Tests for Document OCR Recognition, Adapters & Fallback Policy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest

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
