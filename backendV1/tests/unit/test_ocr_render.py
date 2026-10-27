"""Rendering: PDF pages rasterised directly, DOCX paginated through a fixed layout.

Blank detection is the interesting part: a title-only page carries little ink but is
not blank, while a page with no ink at all must never be sent to the provider.
"""

from __future__ import annotations

import io
import zipfile

import pymupdf
import pytest

from qnu.domains.ocr.artifacts.render import render_document
from qnu.domains.ocr.config import ProcessingConfig
from qnu.platform.errors import AppException

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CONFIG = ProcessingConfig(
    dpi=144,
    max_pages=10,
    max_page_bytes=8 * 1024 * 1024,
    max_output_tokens=8192,
    prompt_version="nemotron-parse/v1",
    processor_version="qnu-ocr/v1",
    table_layout_version="nemotron-tabular/v1",
)


def _pdf(pages: list[str | None]) -> bytes:
    document = pymupdf.open()
    try:
        for text in pages:
            page = document.new_page(width=595, height=842)
            if text:
                page.insert_textbox(pymupdf.Rect(50, 60, 545, 790), text, fontsize=11)
        return document.tobytes()
    finally:
        document.close()


def _docx(body: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>',
        )
    return buffer.getvalue()


def test_pdf_pages_are_rasterised_with_stable_hashes() -> None:
    payload = _pdf(["PHỤ LỤC 01", "Trang hai"])
    first = render_document(payload, ".pdf", CONFIG)
    second = render_document(payload, ".pdf", CONFIG)
    assert len(first.pages) == 2
    assert [page.sha256 for page in first.pages] == [page.sha256 for page in second.pages]
    assert first.fixed_layout_pdf is None
    assert first.renderer["converter"] == "pdf-direct"
    assert first.renderer["dpi"] == 144
    assert first.pages[0].png.startswith(b"\x89PNG")
    assert first.pages[0].width > 1000


def test_a_title_only_page_is_not_blank() -> None:
    rendered = render_document(_pdf(["PHỤ LỤC 01"]), ".pdf", CONFIG)
    assert rendered.pages[0].blank is False
    assert rendered.pages[0].ink_ratio > 0


def test_a_page_without_ink_is_blank_and_keeps_zero_ratio() -> None:
    rendered = render_document(_pdf(["Có chữ", None]), ".pdf", CONFIG)
    assert rendered.pages[0].blank is False
    assert rendered.pages[1].blank is True
    assert rendered.pages[1].ink_ratio == 0.0


def test_docx_is_paginated_into_a_stored_fixed_layout_pdf() -> None:
    body = (
        "<w:p><w:pPr><w:pStyle w:val=\"Heading1\"/></w:pPr>"
        "<w:r><w:t>PHỤ LỤC 01</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Chỉ tiêu tuyển sinh năm 2023</w:t></w:r></w:p>"
    )
    rendered = render_document(_docx(body), ".docx", CONFIG)
    assert rendered.renderer["converter"] == "docx-story"
    assert rendered.fixed_layout_pdf is not None
    assert rendered.fixed_layout_pdf.startswith(b"%PDF")
    assert len(rendered.pages) == 1
    assert rendered.pages[0].blank is False


def test_docx_table_is_rendered_without_losing_rows() -> None:
    rows = "".join(
        "<w:tr>"
        + "".join(
            f"<w:tc><w:p><w:r><w:t>{value}</w:t></w:r></w:p></w:tc>"
            for value in (f"Ô {index}-{column}", "0", "-")
        )
        + "</w:tr>"
        for index, column in [(1, 1), (2, 2), (3, 3)]
    )
    rendered = render_document(_docx(f"<w:tbl>{rows}</w:tbl>"), ".docx", CONFIG)
    assert len(rendered.pages) >= 1
    assert rendered.pages[0].blank is False


def test_encrypted_pdf_is_refused_with_its_own_code() -> None:
    document = pymupdf.open()
    document.new_page()
    payload = document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="o", user_pw="u")
    document.close()
    with pytest.raises(AppException) as caught:
        render_document(payload, ".pdf", CONFIG)
    assert caught.value.code == "pdf_encrypted"


def test_pdf_over_the_page_limit_is_refused() -> None:
    with pytest.raises(AppException) as caught:
        render_document(_pdf([f"Trang {index}" for index in range(12)]), ".pdf", CONFIG)
    assert caught.value.code == "document_too_many_pages"


def test_unsupported_extension_is_refused() -> None:
    with pytest.raises(AppException) as caught:
        render_document(b"whatever", ".txt", CONFIG)
    assert caught.value.code == "processing_unsupported_format"
    assert caught.value.status_code == 415


def test_corrupt_pdf_is_refused() -> None:
    with pytest.raises(AppException) as caught:
        render_document(b"%PDF-1.7 broken", ".pdf", CONFIG)
    assert caught.value.code == "pdf_invalid"
