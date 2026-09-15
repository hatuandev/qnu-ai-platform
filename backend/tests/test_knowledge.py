"""Unit & Integration Tests for Knowledge Base, Parsers, Cleaners and Chunkers."""

import io

import docx
import fitz
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.knowledge.chunker import ClauseBasedChunker, SemanticChunker
from app.modules.knowledge.cleaner import clean_markdown_text, extract_sections_metadata
from app.modules.knowledge.parsers import DocxParser, PlainTextParser, PyMuPdfParser


def test_clean_markdown_text():
    """Verify document cleaning strips page numbers and collapses excess spaces."""
    raw = "Cộng hòa xã hội chủ nghĩa Việt Nam\n\n  — 15 —  \n\nQuy chế đào tạo tín chỉ.\n\n\n\nĐiều 1.   Phạm vi áp dụng"
    cleaned = clean_markdown_text(raw)
    assert "— 15 —" not in cleaned
    assert "Điều 1. Phạm vi áp dụng" in cleaned
    assert "\n\n\n\n" not in cleaned


def test_extract_sections_metadata():
    """Verify legal section extraction regex."""
    text = "Điều 1. Phạm vi\nNội dung điều 1...\nĐiều 2. Đối tượng\nNội dung điều 2..."
    sections = extract_sections_metadata(text)
    assert len(sections) == 2
    assert sections[0]["number"] == "1"
    assert sections[1]["number"] == "2"


def test_clause_based_chunker():
    """Verify ClauseBasedChunker splits text on legal articles (Điều) and preserves preamble."""
    text = (
        "QUY CHẾ ĐÀO TẠO ĐẠI HỌC\n\n"
        "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng\n"
        "1. Quy chế này quy định về đào tạo trình độ đại học theo hệ thống tín chỉ...\n\n"
        "Điều 2. Chương trình đào tạo và thời gian học tập\n"
        "1. Chương trình đào tạo được xây dựng theo đơn vị tín chỉ...\n"
    )
    chunker = ClauseBasedChunker()
    chunks = chunker.chunk(text)
    assert len(chunks) == 3
    assert chunks[1].section is not None
    assert "Điều 1" in chunks[1].section
    assert "Điều 2" in chunks[2].section
    assert chunks[1].chunk_hash != chunks[2].chunk_hash


def test_semantic_chunker():
    """Verify SemanticChunker splits on paragraphs within max token limit."""
    text = "Đoạn văn thứ nhất nói về chỉ tiêu tuyển sinh năm 2026.\n\n" * 20
    chunker = SemanticChunker(max_tokens=100)
    chunks = chunker.chunk(text)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 120


@pytest.mark.asyncio
async def test_pymupdf_parser_in_memory():
    """Create an in-memory PDF and verify PyMuPdfParser extracts text accurately."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "QNU Admissions 2026 - Information Guide")
    pdf_bytes = doc.write()
    doc.close()

    parser = PyMuPdfParser()
    parsed = await parser.parse(pdf_bytes, "test_tuyensinh.pdf")
    assert parsed.page_count == 1
    assert "QNU Admissions 2026 - Information Guide" in parsed.raw_text


@pytest.mark.asyncio
async def test_docx_parser_in_memory():
    """Create an in-memory DOCX and verify DocxParser extracts headings and paragraphs."""
    doc = docx.Document()
    doc.add_heading("QUY CHẾ HỌC VỤ", level=1)
    doc.add_paragraph("Điều 1. Đăng ký học phần trong học kỳ chính.")

    # Add table
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Học kỳ"
    table.rows[0].cells[1].text = "Số tín chỉ tối đa"
    table.rows[1].cells[0].text = "Học kỳ 1"
    table.rows[1].cells[1].text = "24"

    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    parser = DocxParser()
    parsed = await parser.parse(docx_bytes, "quyche.docx")
    assert "QUY CHẾ HỌC VỤ" in parsed.raw_text
    assert "Điều 1. Đăng ký học phần" in parsed.raw_text
    assert len(parsed.tables) == 1
    assert "Số tín chỉ tối đa" in parsed.tables[0].markdown_repr


@pytest.mark.asyncio
async def test_plain_text_parser():
    """Verify PlainTextParser handles text files."""
    content = "Khoa Công nghệ thông tin - Trường Đại học Quy Nhơn".encode()
    parser = PlainTextParser()
    parsed = await parser.parse(content, "sample.txt")
    assert parsed.raw_text == "Khoa Công nghệ thông tin - Trường Đại học Quy Nhơn"


@pytest.mark.asyncio
async def test_api_parse_preview():
    """Verify POST /platform/v1alpha1/knowledge/collections/{id}/parse-preview endpoint."""
    sample_txt = (
        "Điều 1. Giới thiệu chung về ngành CNTT.\n\nĐiều 2. Chuẩn đầu ra tốt nghiệp.".encode()
    )
    files = {"file": ("demo.txt", sample_txt, "text/plain")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/platform/v1alpha1/knowledge/collections/col_demo/parse-preview?strategy=clause",
            files=files,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == "demo.txt"
    assert data["chunk_count"] == 2
    assert len(data["preview_chunks"]) == 2
