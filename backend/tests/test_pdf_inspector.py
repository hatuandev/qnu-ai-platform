"""Unit Tests for Firecrawl PDFInspector Adapter (Rust Core)."""

from __future__ import annotations

import io

import pymupdf as fitz
from PIL import Image

from app.modules.knowledge.parsers.pdf_inspector import PDFInspectionResult, PDFInspector


def create_text_pdf(text: str = "Truong Dai hoc Quy Nhon - Thong tin tuyen sinh dai hoc chinh quy nam 2026") -> bytes:
    """Helper to create a standard text-based PDF in-memory."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_scanned_image_pdf() -> bytes:
    """Helper to create a scanned/image-only PDF with zero digital text."""
    doc = fitz.open()
    page = doc.new_page()
    # Create a 200x200 solid color image (simulating a scanned paper photo)
    img = Image.new("RGB", (200, 200), color=(240, 240, 240))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()
    page.insert_image(fitz.Rect(50, 50, 250, 250), stream=img_bytes)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_inspector_text_based():
    """Verify clean digital text PDF is classified as text_based in milliseconds."""
    pdf_bytes = create_text_pdf()
    res = PDFInspector.inspect_bytes(pdf_bytes)

    assert isinstance(res, PDFInspectionResult)
    assert res.pdf_type == "text_based"
    assert res.is_text_based is True
    assert res.is_scanned is False
    assert res.is_mixed is False
    assert res.can_skip_ocr is True
    assert res.page_count == 1
    assert res.markdown is not None
    assert "Quy Nhon" in res.markdown or "tuyen sinh" in res.markdown.lower()
    assert res.processing_time_ms >= 0


def test_pdf_inspector_scanned_image():
    """Verify an image-only PDF is classified as scanned or image_based."""
    pdf_bytes = create_scanned_image_pdf()
    res = PDFInspector.inspect_bytes(pdf_bytes)

    assert isinstance(res, PDFInspectionResult)
    assert res.pdf_type in ("scanned", "image_based")
    assert res.is_scanned is True
    assert res.can_skip_ocr is False


def test_pdf_inspector_multi_page():
    """Verify multi-page PDF inspection extracts per-page breakdowns."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 72), "Trang 1: Quy chế đào tạo tín chỉ Trường Đại học Quy Nhơn")
    p2 = doc.new_page()
    p2.insert_text((50, 72), "Trang 2: Điều kiện tốt nghiệp và xét học bổng khuyến khích")
    pdf_bytes = doc.tobytes()
    doc.close()

    res = PDFInspector.inspect_bytes(pdf_bytes)
    assert res.page_count == 2
    assert res.is_text_based is True
    assert len(res.page_markdowns) >= 1
    assert len(res.pages_detail) >= 1


def test_pdf_inspector_malformed_bytes_graceful_fallback():
    """Verify malformed bytes never crash the server and return graceful unknown result."""
    bad_bytes = b"%PDF-1.4 malformed corrupt data not a valid structure"
    res = PDFInspector.inspect_bytes(bad_bytes)

    assert isinstance(res, PDFInspectionResult)
    assert res.pdf_type == "unknown"
    assert res.can_skip_ocr is False


def test_pdf_inspector_empty_bytes():
    """Verify empty bytes return safe default result."""
    res = PDFInspector.inspect_bytes(b"")

    assert isinstance(res, PDFInspectionResult)
    assert res.pdf_type == "unknown"
    assert res.page_count == 0
    assert res.can_skip_ocr is False
